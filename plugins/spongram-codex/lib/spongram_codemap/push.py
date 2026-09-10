# spongram_codemap/push.py
"""POST extraction dicts to the Spongram code-map ingest endpoint."""

from __future__ import annotations

import json
import urllib.request


def push(
    base_url: str,
    brain_key: str,
    repo: str,
    nodes: list[dict],
    edges: list[dict],
    pruned: list[str],
) -> dict:
    """POST {repo, nodes, edges, pruned_files} to /v1/codemap/ingest."""
    payload = json.dumps(
        {
            "repo": repo,
            "nodes": nodes,
            "edges": edges,
            "pruned_files": pruned,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/codemap/ingest",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {brain_key}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (trusted local/own server)
        return json.loads(resp.read().decode("utf-8"))
