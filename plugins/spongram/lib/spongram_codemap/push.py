# spongram_codemap/push.py
"""POST extraction dicts to the Spongram code-map ingest endpoint."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

# A production audit found the ingest endpoint's server-side lock (one ingest
# at a time per repo) rejecting concurrent pushes with 409 — e.g. the
# post-commit hook firing while a manual rebuild is still running, or two
# quick commits in a row — and this client had no retry, so every collision
# silently dropped the push. The server-side lock is idempotent and already
# time-bounded, so the right client fix is to honor its ``Retry-After``
# instead of giving up immediately.
_RETRYABLE_STATUSES = (409, 503)
_MAX_ATTEMPTS = 6
_MAX_TOTAL_WAIT_SEC = 600.0  # 10 min
_DEFAULT_RETRY_AFTER_SEC = 15.0
_MAX_RETRY_AFTER_SEC = 120.0


def _retry_after_seconds(err: urllib.error.HTTPError) -> float:
    """Seconds to wait before retrying: the server's ``Retry-After`` header,
    falling back to 15s if absent/unparsable, capped at 120s."""
    raw = ""
    if err.headers is not None:
        raw = err.headers.get("Retry-After", "") or ""
    try:
        sec = float(raw.strip())
    except ValueError:
        sec = _DEFAULT_RETRY_AFTER_SEC
    return max(0.0, min(sec, _MAX_RETRY_AFTER_SEC))


def push(
    base_url: str,
    brain_key: str,
    repo: str,
    nodes: list[dict],
    edges: list[dict],
    pruned: list[str],
    *,
    sleep=time.sleep,
    monotonic=time.monotonic,
) -> dict:
    """POST {repo, nodes, edges, pruned_files} to /v1/codemap/ingest.

    On ``HTTPError`` 409 (an ingest is already running for this repo) or 503
    (upstream unavailable), waits ``Retry-After`` seconds (default 15s,
    capped at 120s) and retries, up to 6 attempts and 10 minutes of REAL
    elapsed time (measured via ``monotonic``, not just the sum of the waits —
    a slow request counts too). Beyond that, raises as before. ``sleep`` and
    ``monotonic`` are injectable (tests) — default to ``time.sleep`` and
    ``time.monotonic``.
    """
    payload = json.dumps(
        {
            "repo": repo,
            "nodes": nodes,
            "edges": edges,
            "pruned_files": pruned,
        }
    ).encode("utf-8")
    url = base_url.rstrip("/") + "/v1/codemap/ingest"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {brain_key}"}

    start = monotonic()
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, data=payload, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 (trusted local/own server)
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code not in _RETRYABLE_STATUSES or attempt >= _MAX_ATTEMPTS:
                raise
            wait = _retry_after_seconds(err)
            if monotonic() - start + wait > _MAX_TOTAL_WAIT_SEC:
                raise
            sleep(wait)
    raise AssertionError("unreachable")  # pragma: no cover
