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
from pathlib import Path
from typing import Any

# Allow `python server/main.py` invocation by ensuring the bundle's own
# server/ directory is on sys.path.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    print(
        "ERROR: 'mcp' Python SDK is not installed.  The uv runtime resolves "
        "dependencies from pyproject.toml automatically.  If you're running "
        "this server manually: uv run --directory <bundle-dir> server/main.py",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

from spt_client import SPTClient

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


mcp = FastMCP("spt-models", instructions=_AGENT_GUIDE)


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

@mcp.tool()
async def list_models(verbose: bool = True) -> dict[str, Any]:
    """List all models registered on the SPT stack.

    With `verbose=True` (default) each entry includes `name`, `type`,
    `vram_required_mb`, `loaded` status, and the structured `prompting_guide`.
    Use `verbose=False` for a stock OpenAI-shape response.
    """
    return await _get_client().list_models(verbose=verbose)


@mcp.tool()
async def get_model_info(slug: str) -> dict[str, Any]:
    """Return full info for one model.

    Fields:
      - id, name, type, created
      - vram_required_mb
      - loaded (bool)
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

@mcp.tool()
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


@mcp.tool()
async def unload_model(slug: str) -> dict[str, Any]:
    """Ops tool — manually free a model's GPU memory.

    Rarely needed: the platform auto-evicts the least-recently-used model when
    it needs room, so you don't unload to "make space" before an inference.
    Pinned (load_on_startup) models stay unloaded until explicitly reloaded —
    the manual unload sticks across worker heartbeats."""
    return await _get_client().unload_model(slug)


@mcp.tool()
async def refresh_prompting_guide(slug: str) -> dict[str, Any]:
    """Re-run AI extraction of the prompting guide for one model.  Useful after
    a model card update.  Requires the admin token."""
    return await _get_client().refresh_prompting_guide(slug)


# ---------------------------------------------------------------------------
# Inference tools
# ---------------------------------------------------------------------------

@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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
) -> dict[str, Any]:
    """Generate one or more images from a prompt.

    The model auto-loads on first use — do NOT call `load_model` first.

    Resolution: prefer `extra={"width": W, "height": H}` using a resolution from
    the model's prompting guide — that is the authoritative channel. `size`
    ("WIDTHxHEIGHT") is accepted too, but `extra` width/height always wins; a
    bare `size` with no width/height can fall back to 512x512 on some models.
    Use `extra` for model-specific flags as well (e.g. ErnieImage's `use_pe`).

    Call `get_model_info(slug)` first and apply `recommended_params` (steps,
    guidance, width/height). `response_format="b64_json"` returns base64 PNGs.
    """
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
        "response_format": response_format,
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
    return await _get_client().generate_image(payload)


@mcp.tool()
async def generate_video(
    model: str,
    prompt: str,
    image_b64: str | None = None,
    negative_prompt: str | None = None,
    num_frames: int | None = None,
    fps: int | None = None,
    width: int | None = None,
    height: int | None = None,
    num_inference_steps: int | None = None,
    guidance_scale: float | None = None,
    seed: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a video from a text prompt (video_gen models).

    The model auto-loads on first use — do NOT call `load_model` first.
    Video generation is SLOW (minutes); the request timeout applies.

    Call `get_model_info(slug)` first: frames, fps, resolution and steps are
    model-specific.  `image_b64` supplies a base64 reference image for
    image-to-video models.  The response contains base64-encoded video data
    (`b64_json`) — decode it and write to a file (usually .mp4).
    """
    payload: dict[str, Any] = {"model": model, "prompt": prompt}
    if image_b64 is not None:
        payload["image"] = image_b64
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
    return await _get_client().generate_video(payload)


@mcp.tool()
async def tts(
    model: str,
    input: str,
    voice: str = "alloy",
    response_format: str = "mp3",
    speed: float = 1.0,
) -> dict[str, Any]:
    """Text-to-speech synthesis.  Returns `{audio_b64, content_type}` —
    decode `audio_b64` with base64 and write to a file with the matching
    extension (mp3, wav, ogg, flac).
    """
    payload = {
        "model": model,
        "input": input,
        "voice": voice,
        "response_format": response_format,
        "speed": speed,
    }
    audio_bytes, content_type = await _get_client().tts(payload)
    return {
        "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
        "content_type": content_type,
        "size_bytes": len(audio_bytes),
    }


@mcp.tool()
async def generate_music(
    model: str,
    prompt: str,
    audio_end_in_s: float | None = None,
    num_inference_steps: int | None = None,
    guidance_scale: float | None = None,
    negative_prompt: str | None = None,
    seed: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate music / sound from a text prompt (sound_gen models:
    stable-audio-*, ace-step, yue, diffrhythm).  Call `get_model_info(slug)` for
    the prompting guide first — these models want Stable-Audio-style descriptive
    prompts (genre, instruments, BPM, mood, production), not speech text.

    Returns `{created, model, audio, format}` where `audio` is base64 — decode it
    and write to a .wav file.
    """
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
    return await _get_client().generate_music(payload)


@mcp.tool()
async def transcribe(
    model: str,
    audio_b64: str,
    content_type: str = "audio/wav",
    language: str | None = None,
) -> dict[str, Any]:
    """Speech-to-text transcription.  Pass the audio as base64.  Files larger
    than ~50 MB should be chunked client-side — the Gateway rejects >100 MB."""
    audio_bytes = base64.b64decode(audio_b64)
    return await _get_client().transcribe(
        model=model,
        audio_bytes=audio_bytes,
        content_type=content_type,
        language=language,
    )


@mcp.tool()
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
