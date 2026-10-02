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
# A LINKED worktree does not publish the code map — ``update`` REPLACES the
# repo's whole subgraph, so publishing from a worktree would make the repo's
# map follow whichever worktree committed last. ``--git-dir`` (this
# checkout's git directory) differs from ``--git-common-dir`` (the MAIN
# repo's) only in a linked worktree — exit silently in that case, same as any
# other missing-git-repo path (in a real worktree ``.git`` is a FILE, so the
# ``mkdir`` lock below would fail anyway — but we exit before even reaching
# it, cleanly, with no stderr noise).
# ``--path-format`` only exists since git 2.31; an older git rejects it, or
# echoes it back verbatim. Fallback in that case: the relative ``rev-parse``
# output, made absolute via ``cd`` + ``pwd -P`` (same method for both
# --git-dir and --git-common-dir, so they stay comparable). On a recent git
# the output is already absolute: unchanged behavior.
_spongram_git_abs() {
  local out dir
  out="$(git -C "$REPO_ROOT" rev-parse --path-format=absolute "$@" 2>/dev/null)"
  case "$out" in
    /*|[A-Za-z]:/*) printf '%s\n' "$out"; return 0 ;;
  esac
  out="$(git -C "$REPO_ROOT" rev-parse "$@" 2>/dev/null)" || return 0
  [ -n "$out" ] || return 0
  dir="$(cd "$REPO_ROOT" 2>/dev/null && cd "$(dirname "$out")" 2>/dev/null && pwd -P)" || return 0
  printf '%s/%s\n' "$dir" "$(basename "$out")"
}
GIT_DIR_ABS="$(_spongram_git_abs --git-dir)"
GIT_COMMON_DIR="$(_spongram_git_abs --git-common-dir)"
[ -n "$GIT_DIR_ABS" ] && [ -n "$GIT_COMMON_DIR" ] || exit 0
[ "$GIT_DIR_ABS" = "$GIT_COMMON_DIR" ] || exit 0
case "$GIT_COMMON_DIR" in
  */.git) REPO_NAME="$(basename "$(dirname "$GIT_COMMON_DIR")")" ;;
  *) REPO_NAME="$(basename "$REPO_ROOT")" ;;
esac
STATE="$GIT_DIR_ABS/spongram-codemap.json"
LOCK="$GIT_DIR_ABS/spongram-codemap.lock"
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
