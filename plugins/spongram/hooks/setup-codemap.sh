#!/bin/bash
# SessionStart hook: wire + seed the Spongram code map for the current repo.
#
# Idempotent and STRICTLY non-blocking (`set -u`, never `-e`): a SessionStart
# hook must never crash a session, and it fires in EVERY workspace — many are
# not git repos. Mirrors recall-on-start.sh for stdin/cwd parsing.
#
# Public-plugin flavour (SECRET-FREE):
#   • the connection (instance URL + key) comes from the plugin's userConfig
#     (CLAUDE_PLUGIN_OPTION_*) and is persisted to a private 600 file for the
#     git post-commit hook — nothing is baked into the plugin;
#   • the pure-Python extractor is shipped under ../lib and synced to a stable
#     ~/.spongram path; codemap-run.sh bootstraps a venv with the pinned
#     graphifyy extractor on demand. The baked git hook points at that stable
#     launcher, so a plugin update never strands it.
set -u
input=$(cat 2>/dev/null || echo '{}')

source=$(printf '%s' "$input" | python3 -c "import json,sys;print(json.load(sys.stdin).get('source',''))" 2>/dev/null || echo "")
case "$source" in
  startup|resume|clear|compact) ;;
  *) exit 0 ;;
esac

# Opt-out: env var or a marker file under the stable home.
[ -n "${SPONGRAM_CODEMAP_DISABLE:-}" ] && exit 0
[ -f "$HOME/.spongram/codemap/disabled" ] && exit 0

cwd=$(printf '%s' "$input" | python3 -c "import json,sys;print(json.load(sys.stdin).get('cwd','') or '')" 2>/dev/null || echo "")
[ -n "$cwd" ] && [ -d "$cwd" ] || cwd="$PWD"

# Must be a git repo — guard the git-128 exit that would otherwise abort here.
REPO_ROOT=$(cd "$cwd" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$REPO_ROOT" ] || exit 0

# Resolve our own location from $0 — independent of CLAUDE_PLUGIN_ROOT, which
# churns on plugin update.
SELF_DIR=$(cd "$(dirname "$0")" 2>/dev/null && pwd) || exit 0
mkdir -p "$HOME/.spongram/codemap"

# ── Connection from the plugin's userConfig (exported as CLAUDE_PLUGIN_OPTION_*
# to this hook subprocess). ──
SPONGRAM_BASE_URL="${CLAUDE_PLUGIN_OPTION_INSTANCE_URL:-}"
SPONGRAM_BRAIN_KEY="${CLAUDE_PLUGIN_OPTION_BRAIN_KEY:-}"

# Persist the connection to a stable, private file so the git post-commit hook
# — which runs OUTSIDE the plugin (git invokes it, so CLAUDE_PLUGIN_OPTION_* is
# NOT set there) — can source it. This is the only place the key touches disk,
# 600, from the value the user typed into userConfig; it is never in the plugin.
CONN="$HOME/.spongram/codemap/connection.env"
if [ -n "$SPONGRAM_BASE_URL" ]; then
  umask 077
  {
    printf "SPONGRAM_BASE_URL=%q\n" "$SPONGRAM_BASE_URL"
    printf "SPONGRAM_BRAIN_KEY=%q\n" "$SPONGRAM_BRAIN_KEY"
  } >"$CONN"
  chmod 600 "$CONN" 2>/dev/null || true
fi

# Stable launcher that bootstraps the extractor venv on demand.
SPONGRAM_CODEMAP_CMD=("$HOME/.spongram/codemap/codemap-run.sh")

# ── Sync the embedded extractor source + stable launcher to ~/.spongram. ──
BASE="$HOME/.spongram/codemap"
if [ -d "$SELF_DIR/../lib/spongram_codemap" ]; then
  mkdir -p "$BASE/lib"
  rm -rf "$BASE/lib/spongram_codemap"
  cp -R "$SELF_DIR/../lib/spongram_codemap" "$BASE/lib/spongram_codemap"
fi
if [ -f "$SELF_DIR/codemap-run.sh" ]; then
  cp "$SELF_DIR/codemap-run.sh" "$BASE/codemap-run.sh"
  chmod +x "$BASE/codemap-run.sh"
fi

# ── Install the post-commit hook (idempotent), preserving any user content. ──
MARK="# spongram-codemap-hook"
HOOK="$REPO_ROOT/.git/hooks/post-commit"
if ! { [ -f "$HOOK" ] && grep -q "$MARK" "$HOOK"; }; then
  mkdir -p "$REPO_ROOT/.git/hooks"
  { echo "$MARK"; cat "$SELF_DIR/post-commit.sh"; } >>"$HOOK"
  chmod +x "$HOOK"
fi

# ── First build if the map was never seeded for this repo (detached). ──
# Requires a resolved connection; skip silently otherwise.
STATE="$REPO_ROOT/.git/spongram-codemap.json"
LOCK="$REPO_ROOT/.git/spongram-codemap.lock"
if [ -z "${SPONGRAM_CODEMAP_SKIP_BUILD:-}" ] && [ -n "$SPONGRAM_BASE_URL" ] && [ ! -f "$STATE" ]; then
  if command -v "${SPONGRAM_CODEMAP_CMD[0]}" >/dev/null 2>&1 || [ -x "${SPONGRAM_CODEMAP_CMD[0]}" ]; then
    (
      if ! mkdir "$LOCK" 2>/dev/null; then
        [ -n "$(find "$LOCK" -maxdepth 0 -mmin -5 2>/dev/null)" ] && exit 0
        rm -rf "$LOCK"
        mkdir "$LOCK" 2>/dev/null || exit 0
      fi
      trap 'rm -rf "$LOCK"' EXIT
      "${SPONGRAM_CODEMAP_CMD[@]}" build "$REPO_ROOT" \
        --base-url "$SPONGRAM_BASE_URL" --key "${SPONGRAM_BRAIN_KEY:-local}" \
        --repo "$(basename "$REPO_ROOT")" --state "$STATE" \
        >>"$HOME/.spongram/codemap/last.log" 2>&1
    ) &
  fi
fi
exit 0
