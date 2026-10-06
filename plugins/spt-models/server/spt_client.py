"""Thin httpx client for the SPT Models Gateway.

Two surfaces:
  - /v1/*   — OpenAI-compatible inference, authenticated by SPT_API_KEY
  - /admin/api/*  — admin operations, authenticated by SPT_ADMIN_TOKEN

The MCP server uses /v1/* for everything inference-related and /admin/api/*
only for load/unload + prompting-guide refresh.  Admin tools fail closed
when SPT_ADMIN_TOKEN isn't configured.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _bool_env(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw not in ("0", "false", "no", "off")


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def read_audio_input(
    audio_b64: str | None, audio_path: str | None, content_type: str | None,
) -> tuple[bytes, str, str]:
    """``(bytes, filename, content_type)`` from exactly one of ``audio_b64`` / ``audio_path``.

    ``audio_path`` is a file on the machine running this MCP server, read here —
    a long song never has to travel through the conversation as base64.  Without
    an explicit ``content_type`` a path gets the type of its suffix
    (``application/octet-stream`` when unknown: FFmpeg probes the content anyway)
    and base64 gets ``audio/wav``.
    """
    has_b64, has_path = bool(audio_b64), bool(audio_path)
    if has_b64 == has_path:
        raise ValueError("Pass exactly one of audio_b64 or audio_path")
    if has_path:
        path = Path(audio_path).expanduser()
        if not path.is_file():
            raise ValueError(f"audio_path is not a readable file: {path}")
        guessed = mimetypes.guess_type(path.name)[0]
        return path.read_bytes(), path.name, content_type or guessed or "application/octet-stream"
    try:
        data = base64.b64decode(audio_b64, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("audio_b64 is not valid base64") from None
    return data, "audio", content_type or "audio/wav"


def _raise_for_status(resp: httpx.Response) -> None:
    """`raise_for_status()`, but carrying the gateway's own message.

    A bare "400 Bad Request" leaves an agent guessing; the gateway explains the
    refusal (`{"error": {"message"}}` or `{"detail"}`), so put that in the
    exception text.  Still an httpx.HTTPStatusError with the response attached.
    """
    if not resp.is_error:
        return
    detail = None
    try:
        body = resp.json()
        if isinstance(body, dict):
            err = body.get("error")
            detail = (err.get("message") if isinstance(err, dict) else err) or body.get("detail")
    except Exception:
        detail = (resp.text or "")[:500] or None
    message = f"{resp.status_code} {resp.reason_phrase} for {resp.request.method} {resp.request.url.path}"
    if detail:
        message += f": {detail}"
    raise httpx.HTTPStatusError(message, request=resp.request, response=resp)


class SPTClient:
    """HTTP client wrapper.  Reuses a single AsyncClient across calls."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("SPT_BASE_URL", "").rstrip("/")
        if not self.base_url:
            raise RuntimeError(
                "SPT_BASE_URL is not configured.  Re-install the MCPB bundle "
                "with the Gateway URL in the user_config dialog."
            )
        self.api_key = os.environ.get("SPT_API_KEY", "").strip()
        self.admin_token = os.environ.get("SPT_ADMIN_TOKEN", "").strip()
        # Server-side inference budget is 3600s end-to-end (orchestrator's
        # inference_timeout_seconds, gateway's proxy/admin-router timeouts —
        # video gen can run 28+ min).  Default must clear that budget with
        # margin, or the client gives up on a call the server is about to
        # finish successfully — the worst kind of failure, since it looks
        # like an error when none occurred.
        self.timeout = _float_env("SPT_REQUEST_TIMEOUT", 3900.0)
        self.verify_tls = _bool_env("SPT_VERIFY_TLS", True)

        if not self.api_key:
            logger.warning(
                "SPT_API_KEY is empty.  Inference tools will fail with 401."
            )

        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                verify=self.verify_tls,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _api_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def _admin_headers(self) -> dict[str, str]:
        if not self.admin_token:
            raise PermissionError(
                "SPT_ADMIN_TOKEN is not configured — admin operations are disabled. "
                "Re-install the MCPB bundle and fill in the Admin Token field."
            )
        # gateway/middleware/auth.py:verify_admin_token expects the admin token
        # in the same Authorization: Bearer header as /v1/* (not a custom
        # X-Admin-Token header).
        return {"Authorization": f"Bearer {self.admin_token}"}

    # --- /v1/* -----------------------------------------------------------

    async def list_models(self, verbose: bool = False) -> dict[str, Any]:
        client = await self._get_client()
        params = {"verbose": "true"} if verbose else {}
        resp = await client.get("/v1/models", params=params, headers=self._api_headers())
        _raise_for_status(resp)
        return resp.json()

    async def get_model(self, slug: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"/v1/models/{slug}", headers=self._api_headers())
        _raise_for_status(resp)
        return resp.json()

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/chat/completions",
            json=payload,
            headers=self._api_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/completions",
            json=payload,
            headers=self._api_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def embed(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/embeddings",
            json=payload,
            headers=self._api_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def generate_image(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/images/generations",
            json=payload,
            headers=self._api_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def generate_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/videos/generations",
            json=payload,
            headers=self._api_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def tts(self, payload: dict[str, Any]) -> tuple[bytes, str]:
        """Return (audio_bytes, content_type)."""
        client = await self._get_client()
        resp = await client.post(
            "/v1/audio/speech",
            json=payload,
            headers=self._api_headers(),
        )
        _raise_for_status(resp)
        return resp.content, resp.headers.get("content-type", "audio/mpeg")

    async def generate_music(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/audio/music — sound/music generation.

        Unlike tts() (raw bytes for voice models), sound_gen models return JSON
        ``{created, model, audio: <base64>, format, _compute_time_ms}``, plus the
        optional ``score_abc`` / ``seed`` / ``truncated`` some models report —
        parse and return it whole.
        """
        client = await self._get_client()
        resp = await client.post(
            "/v1/audio/music",
            json=payload,
            headers=self._api_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def transcribe(
        self,
        model: str,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language: str | None = None,
        mode: str | None = None,
        timestamp_granularities: list[str] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        files = {"file": ("audio", audio_bytes, content_type)}
        data: dict[str, Any] = {"model": model}
        if language:
            data["language"] = language
        if mode:
            data["mode"] = mode
        if timestamp_granularities:
            # The Gateway declares this field under its OpenAI name, brackets
            # included; httpx repeats the key once per list entry.
            data["timestamp_granularities[]"] = timestamp_granularities
        resp = await client.post(
            "/v1/audio/transcriptions",
            files=files,
            data=data,
            headers=self._api_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def transcribe_music(
        self,
        model: str,
        audio_bytes: bytes,
        filename: str = "audio",
        content_type: str = "audio/wav",
        task: str | None = None,
        max_seconds: float | None = None,
        include_midi: bool | None = None,
        *,
        poll_interval: float = 5.0,
    ) -> dict[str, Any]:
        """POST /v1/audio/music/transcriptions as a job — the score as JSON.

        A cold load plus a long song can outlast an MCP call, so the request is
        always a job, polled like the generation tools.
        """
        data: dict[str, Any] = {"model": model}
        if task:
            data["task"] = task
        if max_seconds is not None:
            data["max_seconds"] = str(max_seconds)
        if include_midi:
            data["include_midi"] = "true"
        resp = await self.run_multipart_job(
            "/v1/audio/music/transcriptions",
            files={"file": (filename, audio_bytes, content_type)},
            data=data,
            poll_interval=poll_interval,
        )
        return resp.json()

    async def separate_audio(
        self,
        model: str,
        audio_bytes: bytes,
        filename: str = "audio",
        content_type: str = "audio/wav",
        stems: str | None = None,
        *,
        poll_interval: float = 2.0,
    ) -> dict[str, Any]:
        """POST /v1/audio/separations as a job — stems as base64 WAVs.

        Always a job, like transcribe_music: a cold load (venv + weights) can
        outlast an MCP call even though the separation itself takes seconds.
        """
        data: dict[str, Any] = {"model": model}
        if stems:
            data["stems"] = stems
        resp = await self.run_multipart_job(
            "/v1/audio/separations",
            files={"file": (filename, audio_bytes, content_type)},
            data=data,
            poll_interval=poll_interval,
        )
        return resp.json()

    async def classify(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/classifications",
            json=payload,
            headers=self._api_headers(),
        )
        if resp.status_code == 404:
            raise RuntimeError(
                "This SPT gateway does not expose /v1/classifications — typed "
                "decisions need gateway >= 1.8. Upgrade the gateway."
            )
        _raise_for_status(resp)
        return resp.json()

    async def rerank(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        # /v1/rerank is not OpenAI-standard and not every gateway build ships
        # it.  Do NOT fall back to /v1/embeddings: EmbeddingRequest requires
        # an `input` field, so a rerank-shaped payload would 422 — and even a
        # coerced call would return embeddings, not relevance scores.  Fail
        # with a clear message instead.
        resp = await client.post(
            "/v1/rerank",
            json=payload,
            headers=self._api_headers(),
        )
        if resp.status_code == 404:
            raise RuntimeError(
                "This SPT gateway does not expose /v1/rerank — reranking is "
                "not available on this stack yet. Use an embedding model + "
                "cosine similarity as a workaround, or upgrade the gateway."
            )
        _raise_for_status(resp)
        return resp.json()

    # -- Mode job (gateway >= 1.4) ------------------------------------------

    async def run_generation_job(
        self, path: str, payload: dict[str, Any],
        *, poll_interval: float = 5.0, max_wait: float = 3600.0,
    ) -> httpx.Response:
        """Soumet en mode job et polle jusqu'au terme.

        Chaque appel HTTP individuel reste court (<=120 s) — le .plugin
        Claude Code bake SPT_REQUEST_TIMEOUT=300, une génération vidéo de
        28 min ne peut PAS traverser en une requête. Retourne la réponse
        brute de /result (JSON ou binaire). Sur une gateway antérieure au
        mode job, la soumission revient en réponse synchrone complète:
        on la retourne telle quelle (fallback transparent).
        """
        client = await self._get_client()
        resp = await client.post(
            path, json={**payload, "async": True},
            headers=self._api_headers(), timeout=120.0,
        )
        return await self._follow_job(client, resp, poll_interval=poll_interval, max_wait=max_wait)

    async def run_multipart_job(
        self, path: str, files: dict[str, Any], data: dict[str, Any],
        *, poll_interval: float = 5.0, max_wait: float = 3600.0,
    ) -> httpx.Response:
        """Même contrat que :meth:`run_generation_job`, pour une route multipart
        (``async`` voyage comme champ de formulaire)."""
        client = await self._get_client()
        resp = await client.post(
            path, files=files, data={**data, "async": "true"},
            headers=self._api_headers(), timeout=120.0,
        )
        return await self._follow_job(client, resp, poll_interval=poll_interval, max_wait=max_wait)

    async def _follow_job(
        self, client: httpx.AsyncClient, resp: httpx.Response,
        *, poll_interval: float, max_wait: float,
    ) -> httpx.Response:
        _raise_for_status(resp)
        body = resp.json() if "json" in resp.headers.get("content-type", "") else None
        if not (isinstance(body, dict) and body.get("job_id")):
            return resp                      # vieille gateway: réponse synchrone
        job_id = body["job_id"]
        deadline = time.monotonic() + max_wait
        while True:
            j = await client.get(
                f"/v1/jobs/{job_id}",
                headers=self._api_headers(), timeout=60.0,
            )
            _raise_for_status(j)
            status = j.json().get("status")
            if status in ("succeeded", "failed", "interrupted"):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"Generation job {job_id} still '{status}' after {max_wait}s"
                )
            await asyncio.sleep(poll_interval)
        result = await client.get(
            f"/v1/jobs/{job_id}/result",
            headers=self._api_headers(), timeout=120.0,
        )
        _raise_for_status(result)            # rejoue le code d'origine si failed
        return result

    # --- /admin/api/* ----------------------------------------------------

    async def load_model(self, slug: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            f"/admin/api/models/{slug}/load",
            headers=self._admin_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def unload_model(self, slug: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            f"/admin/api/models/{slug}/unload",
            headers=self._admin_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def refresh_prompting_guide(self, slug: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            f"/admin/api/models/{slug}/enrich-prompting-guide",
            headers=self._admin_headers(),
        )
        _raise_for_status(resp)
        return resp.json()
