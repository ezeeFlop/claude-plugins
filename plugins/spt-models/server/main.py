"""SPT Models MCP server (stdio).

Bundled as an MCPB extension.  See manifest.json for user_config keys.

The server is a thin proxy: every tool maps to one HTTP call against
the Gateway.  No inference logic lives here — the platform owns scheduling,
LRU eviction, custom loaders, oMLX placement, etc.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Allow `python server/main.py` invocation by ensuring the bundle's own
# server/ directory is on sys.path.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# SDK 2.0 renamed FastMCP to MCPServer and moved it; the decorator API is
# unchanged, so accept either major rather than pinning ourselves to 1.x.
try:
    from mcp.server.mcpserver import MCPServer as _Server  # SDK >= 2
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as _Server  # SDK 1.x
    except ImportError as exc:
        print(
            "ERROR: no usable 'mcp' Python SDK found (looked for "
            "mcp.server.mcpserver, then mcp.server.fastmcp).  The uv runtime "
            "resolves dependencies from pyproject.toml automatically.  If "
            "you're running this server manually: "
            "uv run --directory <bundle-dir> server/main.py",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

from spt_client import SPTClient, read_audio_input
import spt_outputs

logging.basicConfig(
    level=os.environ.get("SPT_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("spt-mcp")


# Single source of truth for the agent workflow guide.  Drives the FastMCP
# `instructions=` text (sent to every connecting client), the `spt://guide`
# resource (re-readable on demand), and the Claude Code plugin's SKILL.md
# (generated server-side by the gateway when it builds a plugin bundle).
# Falls back to a short inline string if guide.md isn't shipped alongside
# this file — should never happen in built bundles.
_GUIDE_PATH = _HERE / "guide.md"
try:
    _AGENT_GUIDE = _GUIDE_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    _AGENT_GUIDE = (
        "SPT Models — workflow: 1) list_models(type=…) 2) get_model_info(slug) "
        "to read the prompting guide and recommended_params 3) call the matching "
        "infer tool — the model auto-loads on first use, NEVER call load_model "
        "first. For image models set resolution via extra={'width':W,'height':H}. "
        "Always cite the model used."
    )


mcp = _Server("spt-models", instructions=_AGENT_GUIDE)


# MCP tool annotations (hints for clients: Codex's "writes" approval mode, ...).
# Wire names are camelCase; SDK 2.x maps them to its snake_case fields.  An SDK
# older than mcp 1.8 has no `annotations` parameter: the tool is then registered
# without hints rather than failing the import.
_READ = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
# Inference changes nothing the caller owns, but it is not read-only: the first
# call may auto-load the model (evicting an idle one), and it consumes GPU.
_INFER = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
_ADMIN_LOAD = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
_ADMIN_OVERWRITE = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False}


def _tool(hints: dict[str, bool]):
    try:
        from mcp.types import ToolAnnotations

        return mcp.tool(annotations=ToolAnnotations.model_validate(hints))
    except (ImportError, TypeError):
        return mcp.tool()


# A single shared client across all tools to keep the connection pool warm.
_client: SPTClient | None = None


def _get_client() -> SPTClient:
    global _client
    if _client is None:
        _client = SPTClient()
    return _client


# ---------------------------------------------------------------------------
# Discovery tools
# ---------------------------------------------------------------------------

@_tool(_READ)
async def list_models(verbose: bool = True) -> dict[str, Any]:
    """List all models registered on the SPT stack.

    With `verbose=True` (default) each entry includes `name`, `type`,
    `vram_required_mb`, `loaded` status, a one-line `description` of what the
    model does, its `capabilities` (short functional tags), and the structured
    `prompting_guide`.  Use `verbose=False` for a stock OpenAI-shape response.

    `description` + `capabilities` are the cheapest way to pick a model: they
    let you shortlist from this one call instead of fetching every model card.

    Entries with `alias_of` are aliases: `id` is a client-facing name an admin
    pointed at the slug in `alias_of`.  Same model, usable wherever a slug is —
    never count the pair as two models.
    """
    return await _get_client().list_models(verbose=verbose)


@_tool(_READ)
async def get_model_info(slug: str) -> dict[str, Any]:
    """Return full info for one model.

    `slug` may also be an alias (see `alias_of` in `list_models`).

    Fields:
      - id, name, type, created
      - alias_of (str | None): set when `slug` was an alias — the canonical
        slug it resolves to.  The other fields describe that target.
      - vram_required_mb
      - loaded (bool)
      - description (str): one-line summary of what the model does.  Empty
        string when nothing is known about it.
      - capabilities (list[str]): short functional tags, e.g.
        ["128k context", "tool calling", "FR/EN"].  Empty list when unknown.
      - prompting_guide (dict): keys may include `system_prompt`, `format`,
        `example_prompts`, `recommended_params`, `limitations`, `do_dont`,
        `notes`.  All keys are optional; empty dict means "no guide captured".

    Call this BEFORE constructing prompts — many models have model-card-stated
    constraints (system prompt, instruction format, supported languages,
    image vs text prompts, etc.) that you'll get wrong without it.
    """
    return await _get_client().get_model(slug)


# ---------------------------------------------------------------------------
# Admin tools (require SPT_ADMIN_TOKEN)
# ---------------------------------------------------------------------------

@_tool(_ADMIN_LOAD)
async def load_model(slug: str) -> dict[str, Any]:
    """Ops tool — pre-load / pin a model onto a GPU node.

    You almost never need this: inference tools (`chat`, `generate_image`, …)
    auto-load the target model on first use, and the platform auto-evicts the
    least-recently-used model when VRAM is tight. Use `load_model` only for
    deliberate ops — pre-warming before a latency-sensitive batch, or pinning.
    Do NOT call it as a prerequisite to inference.

    Returns 202 immediately — the load runs in the background and can take
    30s to 5min depending on model size and whether files are cached locally.
    Poll `get_model_info(slug).loaded` to check completion.
    """
    return await _get_client().load_model(slug)


@_tool(_ADMIN_OVERWRITE)
async def unload_model(slug: str) -> dict[str, Any]:
    """Ops tool — manually free a model's GPU memory.

    Rarely needed: the platform auto-evicts the least-recently-used model when
    it needs room, so you don't unload to "make space" before an inference.
    Pinned (load_on_startup) models stay unloaded until explicitly reloaded —
    the manual unload sticks across worker heartbeats."""
    return await _get_client().unload_model(slug)


@_tool(_ADMIN_OVERWRITE)
async def refresh_prompting_guide(slug: str) -> dict[str, Any]:
    """Re-run AI extraction of the prompting guide for one model.  Useful after
    a model card update.  Requires the admin token."""
    return await _get_client().refresh_prompting_guide(slug)


# ---------------------------------------------------------------------------
# Inference tools
# ---------------------------------------------------------------------------

@_tool(_INFER)
async def chat(
    model: str,
    messages: list[dict[str, Any]],
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
    stop: list[str] | str | None = None,
    tools: list[dict[str, Any]] | None = None,
    response_format: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """OpenAI-compatible chat completion.

    `messages` follows the OpenAI shape: `[{"role": "user", "content": "..."}, ...]`.
    For VLM models, content can be a list of `{type: "text" | "image_url", ...}` parts.

    `tools` enables tool calling on supported models (gemma-4, llama-3 etc.).
    `response_format` triggers structured outputs: `{"type": "json_schema", "json_schema": {...}}`.
    `extra` is forwarded as-is — use it for non-standard params (e.g. `top_k`).
    """
    payload: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if stop is not None:
        payload["stop"] = stop
    if tools is not None:
        payload["tools"] = tools
    if response_format is not None:
        payload["response_format"] = response_format
    if extra:
        payload.update(extra)
    return await _get_client().chat(payload)


@_tool(_INFER)
async def complete(
    model: str,
    prompt: str,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = 256,
    stop: list[str] | str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """OpenAI-compatible text completion (no chat structure).

    Use for raw base/completion models where chat-template formatting would
    add unwanted tokens.  Check `get_model_info(slug).prompting_guide.format`
    — if it's `raw`, use this tool; otherwise prefer `chat`.
    """
    payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if stop is not None:
        payload["stop"] = stop
    if extra:
        payload.update(extra)
    return await _get_client().complete(payload)


@_tool(_INFER)
async def embed(
    model: str,
    input: str | list[str],
    encoding_format: str | None = None,
) -> dict[str, Any]:
    """Generate embeddings for one string or a list of strings."""
    payload: dict[str, Any] = {"model": model, "input": input}
    if encoding_format is not None:
        payload["encoding_format"] = encoding_format
    return await _get_client().embed(payload)


def _deliver(result: dict[str, Any], target: "spt_outputs.Target | None", model: str) -> dict[str, Any]:
    """The gateway response as-is, or — with `output_path` — its files written
    to disk and listed under `files`, every non-base64 field kept."""
    if target is None:
        return result
    fields, media = spt_outputs.extract_media(result)
    return {**fields, "files": spt_outputs.write(target, media, model)}


def _speech_audio(body: bytes, content_type: str) -> tuple[bytes, dict[str, Any]]:
    """/v1/audio/speech answers a JSON envelope `{audio: <base64>, format, ...}`
    (or raw audio on gateways that predate it): the audio bytes and the other
    envelope fields."""
    if "json" in (content_type or ""):
        import json as _json

        envelope = _json.loads(body)
        audio = base64.b64decode(envelope.get("audio") or "")
        return audio, {k: v for k, v in envelope.items() if k != "audio"}
    return body, {}


@_tool(_INFER)
async def generate_image(
    model: str,
    prompt: str,
    n: int = 1,
    size: str = "1024x1024",
    negative_prompt: str | None = None,
    num_inference_steps: int | None = None,
    guidance_scale: float | None = None,
    seed: int | None = None,
    response_format: str = "b64_json",
    extra: dict[str, Any] | None = None,
    output_path: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Generate one or more images from a prompt.

    The model auto-loads on first use — do NOT call `load_model` first.

    Resolution: prefer `extra={"width": W, "height": H}` using a resolution from
    the model's prompting guide — that is the authoritative channel. `size`
    ("WIDTHxHEIGHT") is accepted too, but `extra` width/height always wins; a
    bare `size` with no width/height can fall back to 512x512 on some models.
    Use `extra` for model-specific flags as well (e.g. ErnieImage's `use_pe`).

    Call `get_model_info(slug)` first and apply `recommended_params` (steps,
    guidance, width/height). `response_format="b64_json"` returns base64 PNGs
    (image-to-3D models such as trellis-2-4b return a GLB the same way);
    `response_format="url"` returns `data[i].url` links valid one hour that
    need no API key (gateway >= 1.10.3) — small answers, for handing the file
    to someone else.  With `output_path` the file is always fetched as
    base64 and written locally, whatever `response_format` says.

    `output_path` (RECOMMENDED for agents): the result is written to disk and
    the answer lists `files: [{path, bytes, mime_type, ...}]` instead of base64
    — MCP clients truncate inline base64 beyond a few hundred KB, so without it
    the file can be lost.  A file path is used as-is; a directory (existing, or
    ending with "/", or without extension) or several results get
    `<model>-<YYYYmmdd-HHMMSS>-<index>.<ext>` names, the extension coming from
    the real content.  `~` is expanded, parent directories are created, and the
    destination is checked BEFORE generating.  An existing file is never
    replaced unless `overwrite=True`.  All other response fields are kept.
    Images also report `width` / `height`.
    """
    target = spt_outputs.prepare(output_path, overwrite, expected_count=n) if output_path else None
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
        "response_format": "b64_json" if target is not None else response_format,
    }
    if negative_prompt is not None:
        payload["negative_prompt"] = negative_prompt
    if num_inference_steps is not None:
        payload["num_inference_steps"] = num_inference_steps
    if guidance_scale is not None:
        payload["guidance_scale"] = guidance_scale
    if seed is not None:
        payload["seed"] = seed
    if extra:
        payload.update(extra)
    resp = await _get_client().run_generation_job("/v1/images/generations", payload)
    return _deliver(resp.json(), target, model)


@_tool(_INFER)
async def generate_video(
    model: str,
    prompt: str,
    image_b64: str | None = None,
    last_frame_b64: str | None = None,
    video_b64: str | None = None,
    video_strength: float | None = None,
    negative_prompt: str | None = None,
    num_frames: int | None = None,
    fps: int | None = None,
    width: int | None = None,
    height: int | None = None,
    num_inference_steps: int | None = None,
    guidance_scale: float | None = None,
    seed: int | None = None,
    extra: dict[str, Any] | None = None,
    output_path: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Generate a video from a text prompt (video_gen models).

    The model auto-loads on first use — do NOT call `load_model` first.
    Video generation is SLOW (minutes); the request timeout applies.

    Call `get_model_info(slug)` first: frames, fps, resolution and steps are
    model-specific.  `image_b64` supplies a base64 FIRST-frame image
    (image-to-video).  LTX-2.5 also takes `last_frame_b64` (LAST frame,
    first/last-frame-to-video, combinable with `image_b64` or `video_b64`) and
    `video_b64` (base64 MP4 whose frames guide the output from frame 0:
    video-to-video, or a continuation when `num_frames` exceeds the source;
    `video_strength` 0-1, 1.0 = faithful re-render; exclusive with
    `image_b64`; source audio is regenerated, not kept).  The response
    contains base64-encoded video data (`b64_json`) — decode it and write to
    a file (usually .mp4), or better, pass `output_path`.

    `output_path` (RECOMMENDED for agents): the result is written to disk and
    the answer lists `files: [{path, bytes, mime_type, ...}]` instead of base64
    — MCP clients truncate inline base64 beyond a few hundred KB, so without it
    the file can be lost.  A file path is used as-is; a directory (existing, or
    ending with "/", or without extension) or several results get
    `<model>-<YYYYmmdd-HHMMSS>-<index>.<ext>` names, the extension coming from
    the real content.  `~` is expanded, parent directories are created, and the
    destination is checked BEFORE generating.  An existing file is never
    replaced unless `overwrite=True`.  All other response fields are kept.
    Videos also report `duration_s`.
    """
    target = spt_outputs.prepare(output_path, overwrite) if output_path else None
    payload: dict[str, Any] = {"model": model, "prompt": prompt}
    if image_b64 is not None:
        payload["image"] = image_b64
    if last_frame_b64 is not None:
        payload["last_frame"] = last_frame_b64
    if video_b64 is not None:
        payload["video"] = video_b64
    if video_strength is not None:
        payload["video_strength"] = video_strength
    if negative_prompt is not None:
        payload["negative_prompt"] = negative_prompt
    if num_frames is not None:
        payload["num_frames"] = num_frames
    if fps is not None:
        payload["fps"] = fps
    if width is not None:
        payload["width"] = width
    if height is not None:
        payload["height"] = height
    if num_inference_steps is not None:
        payload["num_inference_steps"] = num_inference_steps
    if guidance_scale is not None:
        payload["guidance_scale"] = guidance_scale
    if seed is not None:
        payload["seed"] = seed
    if extra:
        payload.update(extra)
    resp = await _get_client().run_generation_job("/v1/videos/generations", payload)
    return _deliver(resp.json(), target, model)


@_tool(_INFER)
async def tts(
    model: str,
    input: str,
    voice: str | None = None,
    response_format: str = "mp3",
    speed: float | None = None,
    extra: dict[str, Any] | None = None,
    output_path: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Text-to-speech synthesis.  Returns `{audio_b64, content_type,
    size_bytes}`; `content_type` is read from the audio itself — some models
    answer WAV whatever `response_format` asks, so write the file with the
    extension that matches `content_type`, or pass `output_path`.

    `output_path` (RECOMMENDED for agents): the result is written to disk and
    the answer lists `files: [{path, bytes, mime_type, ...}]` instead of base64
    — MCP clients truncate inline base64 beyond a few hundred KB, so without it
    the file can be lost.  A file path is used as-is; a directory (existing, or
    ending with "/", or without extension) or several results get
    `<model>-<YYYYmmdd-HHMMSS>-<index>.<ext>` names, the extension coming from
    the real content.  `~` is expanded, parent directories are created, and the
    destination is checked BEFORE generating.  An existing file is never
    replaced unless `overwrite=True`.  All other response fields are kept.
    Audio also reports `duration_s`.

    `voice` and `speed` are sent only when given: voices are model-specific
    (read `get_model_info`), and omnivoice refuses OpenAI-style voice IDs — it
    takes `extra={"instruct": "female, middle-aged, british accent"}` (a closed
    vocabulary: an unknown term is refused with the list of valid ones) or
    `extra={"ref_audio": <base64>, "ref_text": ...}` for cloning.  `extra`
    carries any other model-specific field.
    """
    target = spt_outputs.prepare(output_path, overwrite) if output_path else None
    payload: dict[str, Any] = {"model": model, "input": input, "response_format": response_format}
    if voice is not None:
        payload["voice"] = voice
    if speed is not None:
        payload["speed"] = speed
    if extra:
        payload.update(extra)
    body, content_type = await _get_client().tts(payload)
    audio_bytes, fields = _speech_audio(body, content_type)
    if target is not None:
        files = spt_outputs.write(target, [spt_outputs.Media(audio_bytes, content_type)], model)
        return {**fields, "files": files}
    return {
        "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
        "content_type": spt_outputs.describe(audio_bytes, None)["mime_type"],
        "size_bytes": len(audio_bytes),
    }


@_tool(_INFER)
async def generate_music(
    model: str,
    prompt: str,
    audio_end_in_s: float | None = None,
    num_inference_steps: int | None = None,
    guidance_scale: float | None = None,
    negative_prompt: str | None = None,
    seed: int | None = None,
    extra: dict[str, Any] | None = None,
    output_path: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Generate music / sound from a text prompt (sound_gen models:
    stable-audio-*, ace-step, yue2, diffrhythm).  Call `get_model_info(slug)` for
    the prompting guide first — these models want Stable-Audio-style descriptive
    prompts (genre, instruments, BPM, mood, production), not speech text.
    Lyrics-to-song models (minimax-music3, yue2) take the words to sing in
    `extra={"lyrics": ...}`; `prompt` stays the style description.

    Returns `{created, model, audio, format, _compute_time_ms}` where `audio`
    is base64 — decode it and write to a .wav file.  Some models add optional
    metadata (yue2-3b does; read it with `.get()`, absent means no score):
    `score_abc` — the ABC score the song followed (null with cot=off), `seed` —
    the seed used, `truncated` — `{"abc", "semantic"}` token-ceiling flags.  To
    re-render an edited score, pass it back as `extra={"abc": ...}` with the
    same `seed`.  To cover an existing song with yue2-3b: get its score from
    `transcribe_music(task="melody_full")`, review it, then pass
    `extra={"abc": <score>, "cot": "melody", "lyrics": <words that fit>}`.
    `format` is the gateway's label: some models (stable-audio) answer WAV
    under "mp3" — with `output_path` the real type is read from the bytes.

    `output_path` (RECOMMENDED for agents): the result is written to disk and
    the answer lists `files: [{path, bytes, mime_type, ...}]` instead of base64
    — MCP clients truncate inline base64 beyond a few hundred KB, so without it
    the file can be lost.  A file path is used as-is; a directory (existing, or
    ending with "/", or without extension) or several results get
    `<model>-<YYYYmmdd-HHMMSS>-<index>.<ext>` names, the extension coming from
    the real content.  `~` is expanded, parent directories are created, and the
    destination is checked BEFORE generating.  An existing file is never
    replaced unless `overwrite=True`.  All other response fields are kept.
    Audio also reports `duration_s`.
    """
    target = spt_outputs.prepare(output_path, overwrite) if output_path else None
    payload: dict[str, Any] = {"model": model, "input": prompt}
    if audio_end_in_s is not None:
        payload["audio_end_in_s"] = audio_end_in_s
    if num_inference_steps is not None:
        payload["num_inference_steps"] = num_inference_steps
    if guidance_scale is not None:
        payload["guidance_scale"] = guidance_scale
    if negative_prompt is not None:
        payload["negative_prompt"] = negative_prompt
    if seed is not None:
        payload["seed"] = seed
    if extra:
        payload.update(extra)
    resp = await _get_client().run_generation_job("/v1/audio/music", payload)
    ctype = resp.headers.get("content-type", "")
    if "json" in ctype:
        return _deliver(resp.json(), target, model)
    result = {                               # raw audio body (old gateway)
        "created": int(time.time()),
        "model": model,
        "audio": base64.b64encode(resp.content).decode(),
        "format": "wav",
    }
    return _deliver(result, target, model)


@_tool(_INFER)
async def transcribe(
    model: str,
    audio_b64: str,
    content_type: str = "audio/wav",
    language: str | None = None,
    mode: str | None = None,
    timestamp_granularities: list[str] | None = None,
) -> dict[str, Any]:
    """Speech-to-text transcription.  Pass the audio as base64.  Files larger
    than ~50 MB should be chunked client-side — the Gateway rejects >100 MB.

    `mode` selects the transcription policy on models that expose one:
    "verbatim" keeps every filler, stutter and vocal sound, "intended" returns
    the clean readable sentence.  Only CrisperWhisper honours it today; other
    STT backends ignore it.  Omit it to keep the model's own default.

    `timestamp_granularities` mirrors the OpenAI field — ["word"] and/or
    ["segment"].  Asking for word timings roughly doubles the wall time, so
    pass ["segment"] when the text alone is enough."""
    audio_bytes = base64.b64decode(audio_b64)
    return await _get_client().transcribe(
        model=model,
        audio_bytes=audio_bytes,
        content_type=content_type,
        language=language,
        mode=mode,
        timestamp_granularities=timestamp_granularities,
    )


@_tool(_INFER)
async def transcribe_music(
    model: str,
    audio_b64: str | None = None,
    audio_path: str | None = None,
    content_type: str | None = None,
    task: str = "full",
    max_seconds: float | None = None,
    include_midi: bool = False,
) -> dict[str, Any]:
    """Transcribe a song recording into a score (music_transcription models:
    sheetsage2).  Pass the audio as EXACTLY ONE of `audio_b64` (base64) or
    `audio_path` (a file on the machine running this MCP server, read locally —
    prefer it for real songs).  Uploads are limited to 100 MB: send MP3, FLAC or
    M4A for long songs.

    `task`: "full" (melody and chord symbols), "melody_full" (both melodies, no
    chords — the score for a cover), "melody_vocal" (sung melody only).
    `max_seconds` transcribes only the beginning; files longer than 1200 s need it.

    Returns `{abc, abc_error, header, keys, sections, stats, warnings,
    diagnostics, ...}` (+ `midi` base64 parts with `include_midi`).  `abc` CAN
    BE NULL: read `abc_error` then.  A transcription can contain musical errors
    even when its notation is valid — review it before using it.

    Cover recipe: `transcribe_music(task="melody_full")`, write lyrics with one
    section tag per `% verse`/`% chorus` block and about one syllable per sung
    note (`sections[].vocal_notes`), then `generate_music(model="yue2-3b",
    prompt=<new style, tempo = header.tempo>, extra={"abc": abc, "cot":
    "melody", "lyrics": ...})`.  The weights are CC BY-NC 4.0 (non-commercial),
    and transcribing a song grants no right to it.
    """
    audio_bytes, filename, ctype = read_audio_input(audio_b64, audio_path, content_type)
    return await _get_client().transcribe_music(
        model=model,
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=ctype,
        task=task,
        max_seconds=max_seconds,
        include_midi=include_midi,
    )


@_tool(_INFER)
async def separate_audio(
    model: str,
    audio_b64: str | None = None,
    audio_path: str | None = None,
    content_type: str | None = None,
    stems: str = "vocals",
    output_dir: str | None = None,
    return_base64: bool = False,
) -> dict[str, Any]:
    """Split a mixed song into stems (audio_separation models: htdemucs).

    Pass the audio as EXACTLY ONE of `audio_b64` (base64) or `audio_path` (a
    file on the machine running this MCP server).  Up to 90 s and 50 MB.
    `stems`: "vocals" (default), "accompaniment" or "vocals,accompaniment".

    Each stem is a WAV with the INPUT's sample rate, channel count and exact
    number of samples — times measured on the vocal stem (e.g. word timestamps
    from `transcribe` with whisperx-large-v3) apply to the mix unchanged.

    By default the stems are WRITTEN to `output_dir` (a temporary directory when
    omitted) and the result lists their paths: a 40 s stereo stem is ~8 MB, far
    too big to return inline.  `return_base64=True` returns them as base64
    instead.  Returns `{stems: {name: path_or_base64}, sample_rate, channels,
    samples, duration_s, model}`.
    """
    import tempfile

    audio_bytes, filename, ctype = read_audio_input(audio_b64, audio_path, content_type)
    result = await _get_client().separate_audio(
        model=model, audio_bytes=audio_bytes, filename=filename, content_type=ctype, stems=stems,
    )
    if return_base64:
        return result
    target = Path(output_dir).expanduser() if output_dir else Path(tempfile.mkdtemp(prefix="spt-stems-"))
    target.mkdir(parents=True, exist_ok=True)
    base = Path(filename).stem or "audio"
    paths = {}
    for name, b64 in (result.get("stems") or {}).items():
        path = target / f"{base}.{name}.wav"
        path.write_bytes(base64.b64decode(b64))
        paths[name] = str(path)
    return {**{k: v for k, v in result.items() if k != "stems"}, "stems": paths}


@_tool(_INFER)
async def rerank(
    model: str,
    query: str,
    documents: list[str],
    top_n: int | None = None,
) -> dict[str, Any]:
    """Rerank `documents` against `query` using a cross-encoder reranker.
    Returns each document with a relevance score sorted descending."""
    payload: dict[str, Any] = {"model": model, "query": query, "documents": documents}
    if top_n is not None:
        payload["top_n"] = top_n
    return await _get_client().rerank(payload)


@_tool(_INFER)
async def classify(
    model: str,
    questions: dict[str, Any],
    input: str | dict[str, Any] | list[Any] | None = None,
    items: list[dict[str, Any]] | None = None,
    on_truncation: str | None = None,
) -> dict[str, Any]:
    """Ask typed questions of a document with a `classification` model (Laya).

    `input` is ONE document: a text, a JSON object, or a list of conversation
    turns (a list is one structured content, never a batch).  `items` is the
    batch form instead: `[{"id": ..., "input": ...}]`, answered document by
    document with the results under the same ids.  Exactly one of the two.

    `questions` maps an id to `{"type", "instructions", "criteria"}`:
      choice — labels (list) or {label: description}; answer = `choice` +
               `probabilities` per label
      score  — ordered level descriptions (list); answer = expected level
               `score` + `probabilities` per level + `legend`
      noul   — yes/no, optional {"true": ..., "false": ...}; answer = `noul` = P(true)
    `confidence` on choice/score is 1 - normalised entropy (how concentrated
    the distribution is), NOT a probability of being right; on noul it is
    max(P, 1-P).  Nothing is calibrated on your data: read `noul` /
    `probabilities` and decide the threshold yourself.

    Each question sees at most `limits.max_len` tokens (instructions and options
    first, then the document) and option descriptions are cut at 48 tokens.  By
    default a request the model would truncate is refused with the counts;
    `on_truncation="truncate"` answers anyway and fills `truncation`.  The
    response also says which `device` actually ran (cuda / mps / cpu)."""
    if (input is None) == (items is None):
        raise ValueError("pass exactly one of `input` (one document) or `items` (a batch)")
    payload: dict[str, Any] = {"model": model, "questions": questions}
    if input is not None:
        payload["input"] = input
    else:
        payload["items"] = items
    if on_truncation is not None:
        payload["on_truncation"] = on_truncation
    return await _get_client().classify(payload)


# ---------------------------------------------------------------------------
# Resources — structured grounding for the agent
# ---------------------------------------------------------------------------

@mcp.resource("spt://models")
async def models_resource() -> str:
    """All registered models with prompting guides — JSON list."""
    import json
    data = await _get_client().list_models(verbose=True)
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.resource("spt://model/{slug}")
async def model_resource(slug: str) -> str:
    """One model's full info + prompting guide.  URI: `spt://model/<slug>`."""
    import json
    data = await _get_client().get_model(slug)
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.resource("spt://guide")
async def guide_resource() -> str:
    """The agent workflow guide — same content as the FastMCP `instructions`,
    re-readable any time without restarting the session.

    Mirrored as a Claude Code SKILL in the .plugin bundle so the same text
    drives Claude Desktop (this resource) and Claude Code (the SKILL)."""
    return _AGENT_GUIDE


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

async def _shutdown() -> None:
    if _client is not None:
        await _client.close()


def main() -> None:
    try:
        mcp.run()
    finally:
        try:
            asyncio.run(_shutdown())
        except RuntimeError:
            pass


if __name__ == "__main__":
    main()
