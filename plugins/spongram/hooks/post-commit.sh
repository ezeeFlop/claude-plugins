#!/usr/bin/env bash
# graphify-style detached code-map refresh. Installed by setup-codemap.sh into
# .git/hooks/post-commit, removed by uninstall-codemap-hook.sh.
#
# Public-plugin flavour (SECRET-FREE): the connection is read from the private
# ~/.spongram/codemap/connection.env that setup-codemap.sh wrote from the
# plugin's userConfig — no URL or key is stored in the repo or in the plugin.
# The extractor is the stable ~/.spongram launcher (bootstraps a venv on
# demand), so a plugin update never strands this baked hook.
set -u
SPONGRAM_CODEMAP_CMD=("$HOME/.spongram/codemap/codemap-run.sh")

# git runs this hook OUTSIDE the plugin, so CLAUDE_PLUGIN_OPTION_* is unset here.
# setup-codemap.sh persisted the connection (from the plugin's userConfig) to a
# private 600 file when the session started; source it.
SPONGRAM_BASE_URL=""
SPONGRAM_BRAIN_KEY=""
CONN="$HOME/.spongram/codemap/connection.env"
[ -f "$CONN" ] && . "$CONN"

# A post-commit hook must NEVER break a commit: if we can't resolve a connection
# or the extractor is absent, exit silently.
[ -n "$SPONGRAM_BASE_URL" ] || exit 0
command -v "${SPONGRAM_CODEMAP_CMD[0]}" >/dev/null 2>&1 || [ -x "${SPONGRAM_CODEMAP_CMD[0]}" ] || exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
REPO_NAME="$(basename "$REPO_ROOT")"
STATE="$REPO_ROOT/.git/spongram-codemap.json"
LOCK="$REPO_ROOT/.git/spongram-codemap.lock"
# Per-repo debounce via an atomic mkdir lock; the SERVER-side ingest lock is the
# real correctness guarantee, so even a rare stale-break race only wastes a
# redundant run. The background subshell means the commit never waits.
(
  if ! mkdir "$LOCK" 2>/dev/null; then
    [ -n "$(find "$LOCK" -maxdepth 0 -mmin -5 2>/dev/null)" ] && exit 0
    rm -rf "$LOCK"
    mkdir "$LOCK" 2>/dev/null || exit 0
  fi
  trap 'rm -rf "$LOCK"' EXIT
  "${SPONGRAM_CODEMAP_CMD[@]}" update "$REPO_ROOT" \
    --base-url "$SPONGRAM_BASE_URL" --key "${SPONGRAM_BRAIN_KEY:-local}" \
    --repo "$REPO_NAME" --state "$STATE" >/dev/null 2>&1
) &
exit 0
