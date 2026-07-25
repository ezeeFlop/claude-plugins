#!/usr/bin/env bash
# Out-of-band memory capture (PreCompact + SessionEnd).
#
# WHY THIS IS NOT A NUDGE
#   memory-nudge.sh reminds the MODEL to write, on the two events that can hand
#   context back to it (Stop, PostToolUse). PreCompact and SessionEnd cannot do
#   that at all: per the Claude Code hooks contract PreCompact supports no
#   additionalContext (it can only BLOCK compaction via exit 2) and SessionEnd
#   runs once the session is already over. Yet compaction is exactly when the
#   context is thrown away — the worst case.
#
#   So capture here does not ask the model for anything. This script reads the
#   transcript it is handed, extracts a bounded tail, and posts it to the
#   brain's /v1/memory/distill endpoint, which distils durable facts server-side
#   and queues them. Deterministic: no longer dependent on model compliance.
#
# WHY THE SERVER DOES THE DISTILLING
#   The plugin only ever holds instance_url + brain_key. The inference chokepoint
#   sits behind an internal token a plugin must never carry. Distilling server
#   side keeps every LLM call on the single traced chokepoint and ships no
#   second secret.
#
# COST AND SAFETY
#   Detached (backgrounded) so it never delays a compaction or a session exit.
#   Bounded tail read — real transcripts reach 56 MB. Silent no-op when the
#   endpoint is disabled (503) or unreachable. Off switch:
#   SPONGRAM_CAPTURE_DISABLED=1.
set -u

[ -n "${SPONGRAM_CAPTURE_DISABLED:-}" ] && exit 0

input=$(cat 2>/dev/null || echo '{}')

PROXY="${CLAUDE_PLUGIN_OPTION_INSTANCE_URL:-}"
KEY="${CLAUDE_PLUGIN_OPTION_BRAIN_KEY:-}"
[ -n "$PROXY" ] || exit 0

# Everything below runs detached: a compaction or a session exit must never wait
# on an LLM round trip.
(
  # Same tagging contract as recall-on-start.sh: an episode captured here must
  # be filterable exactly like one written by hand (project + repo + branch).
  hook_cwd=$(printf '%s' "$input" | python3 -c \
    "import json,sys;print(json.load(sys.stdin).get('cwd','') or '')" 2>/dev/null || echo "")
  [ -n "$hook_cwd" ] && [ -d "$hook_cwd" ] || hook_cwd="$PWD"
  SPONGRAM_CAPTURE_REPO=""
  SPONGRAM_CAPTURE_BRANCH=""
  if (cd "$hook_cwd" && git rev-parse --git-dir >/dev/null 2>&1); then
    repo_url=$(cd "$hook_cwd" && git remote get-url origin 2>/dev/null || echo "")
    SPONGRAM_CAPTURE_BRANCH=$(cd "$hook_cwd" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    if [ -n "$repo_url" ]; then
      SPONGRAM_CAPTURE_REPO=$(printf '%s' "$repo_url" \
        | sed -E 's#.*[:/]([^/]+/[^/]+)(\.git)?$#\1#; s#\.git$##')
    fi
  fi
  export SPONGRAM_CAPTURE_REPO SPONGRAM_CAPTURE_BRANCH

  payload=$(python3 - "$input" <<'PY' 2>/dev/null
import json, os, sys

raw = sys.argv[1] if len(sys.argv) > 1 else "{}"
try:
    inp = json.loads(raw)
except Exception:
    sys.exit(1)
if not isinstance(inp, dict):
    sys.exit(1)

event = inp.get("hook_event_name") or ""
source = {"PreCompact": "precompact", "SessionEnd": "sessionend"}.get(event)
if not source:
    sys.exit(1)

transcript = inp.get("transcript_path") or ""
if not transcript or not os.path.isfile(transcript):
    sys.exit(1)


def env_int(name, default):
    try:
        return int(os.environ[name])
    except Exception:
        return default


# Bounded tail: same rationale as memory-nudge.sh. Reading a 56 MB transcript
# whole would be slow and would blow past the model's context anyway.
WINDOW = env_int("SPONGRAM_CAPTURE_WINDOW_BYTES", 1_500_000)
MAX_TURNS = env_int("SPONGRAM_CAPTURE_MAX_TURNS", 300)
MAX_CHARS = 4_000

try:
    size = os.path.getsize(transcript)
except Exception:
    sys.exit(1)
start = 0 if size <= WINDOW else size - WINDOW

turns = []
try:
    with open(transcript, "rb") as fh:
        if start:
            fh.seek(start)
            fh.readline()  # discard the partial line we landed inside
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line.decode("utf-8", "replace"))
            except Exception:
                continue
            if not isinstance(rec, dict) or rec.get("type") not in ("user", "assistant"):
                continue
            content = (rec.get("message") or {}).get("content")
            chunks = []
            if isinstance(content, str):
                chunks.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        chunks.append(block.get("text") or "")
            text = "\n".join(c for c in chunks if c).strip()
            if not text:
                continue
            turns.append({"role": rec["type"], "text": text[:MAX_CHARS]})
except Exception:
    sys.exit(1)

if len(turns) < env_int("SPONGRAM_CAPTURE_MIN_TURNS", 6):
    sys.exit(1)  # too thin to hold anything durable

cwd = inp.get("cwd") or os.getcwd()
slug = os.path.basename(cwd).lower()
slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in slug).strip("-") or "unknown"

out = {
    "source": source,
    "project": slug,
    "turns": turns[-MAX_TURNS:],
}
repo = os.environ.get("SPONGRAM_CAPTURE_REPO") or ""
branch = os.environ.get("SPONGRAM_CAPTURE_BRANCH") or ""
if repo:
    out["repo"] = repo
if branch:
    out["branch"] = branch
print(json.dumps(out))
PY
  ) || exit 0

  [ -n "$payload" ] || exit 0

  auth_args=()
  [ -n "$KEY" ] && auth_args=(-H "Authorization: Bearer $KEY")

  curl -sS --max-time "${SPONGRAM_CAPTURE_TIMEOUT:-240}" \
    -X POST "${PROXY%/}/v1/memory/distill" \
    -H "Content-Type: application/json" \
    ${auth_args[@]+"${auth_args[@]}"} \
    --data-binary "$payload" >/dev/null 2>&1 || true
) >/dev/null 2>&1 &

exit 0
