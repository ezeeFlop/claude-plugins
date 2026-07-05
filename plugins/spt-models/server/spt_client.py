"""Thin httpx client for the SPT Models Gateway.

Two surfaces:
  - /v1/*   — OpenAI-compatible inference, authenticated by SPT_API_KEY
  - /admin/api/*  — admin operations, authenticated by SPT_ADMIN_TOKEN

The MCP server uses /v1/* for everything inference-related and /admin/api/*
only for load/unload + prompting-guide refresh.  Admin tools fail closed
when SPT_ADMIN_TOKEN isn't configured.
"""

from __future__ import annotations

import logging
import os
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
        self.timeout = _float_env("SPT_REQUEST_TIMEOUT", 300.0)
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
        resp.raise_for_status()
        return resp.json()

    async def get_model(self, slug: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"/v1/models/{slug}", headers=self._api_headers())
        resp.raise_for_status()
        return resp.json()

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/chat/completions",
            json=payload,
            headers=self._api_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/completions",
            json=payload,
            headers=self._api_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def embed(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/embeddings",
            json=payload,
            headers=self._api_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def generate_image(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/images/generations",
            json=payload,
            headers=self._api_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def generate_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            "/v1/videos/generations",
            json=payload,
            headers=self._api_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def tts(self, payload: dict[str, Any]) -> tuple[bytes, str]:
        """Return (audio_bytes, content_type)."""
        client = await self._get_client()
        resp = await client.post(
            "/v1/audio/speech",
            json=payload,
            headers=self._api_headers(),
        )
        resp.raise_for_status()
        return resp.content, resp.headers.get("content-type", "audio/mpeg")

    async def generate_music(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/audio/music — sound/music generation.

        Unlike tts() (raw bytes for voice models), sound_gen models return JSON
        ``{created, model, audio: <base64>, format}`` — parse and return it.
        """
        client = await self._get_client()
        resp = await client.post(
            "/v1/audio/music",
            json=payload,
            headers=self._api_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def transcribe(
        self,
        model: str,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        files = {"file": ("audio", audio_bytes, content_type)}
        data: dict[str, Any] = {"model": model}
        if language:
            data["language"] = language
        resp = await client.post(
            "/v1/audio/transcriptions",
            files=files,
            data=data,
            headers=self._api_headers(),
        )
        resp.raise_for_status()
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
        resp.raise_for_status()
        return resp.json()

    # --- /admin/api/* ----------------------------------------------------

    async def load_model(self, slug: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            f"/admin/api/models/{slug}/load",
            headers=self._admin_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def unload_model(self, slug: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            f"/admin/api/models/{slug}/unload",
            headers=self._admin_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def refresh_prompting_guide(self, slug: str) -> dict[str, Any]:
        client = await self._get_client()
        resp = await client.post(
            f"/admin/api/models/{slug}/enrich-prompting-guide",
            headers=self._admin_headers(),
        )
        resp.raise_for_status()
        return resp.json()
