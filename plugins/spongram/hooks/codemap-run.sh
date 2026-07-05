#!/usr/bin/env bash
# Spongram code-map launcher (cloud plugin).
#
# Bootstraps a throwaway venv with the pinned graphifyy extractor on first use,
# then runs the spongram_codemap CLI. Generic + SECRET-FREE: setup-codemap.sh
# copies it to a STABLE ~/.spongram path on every SessionStart, so a plugin
# update that moves CLAUDE_PLUGIN_ROOT never strands the baked git post-commit
# hook. Build args (--base-url / --key / --repo / --state) are passed by the
# caller (post-commit hook or setup-codemap's first-build kick).
#
# Strictly bash-3.2 safe (macOS default). No GNU-only constructs, no in-place
# stream editing, no `flock` (BSD has none — concurrency uses an atomic mkdir
# lock instead).
set -u

BASE="$HOME/.spongram/codemap"
LIB="$BASE/lib"
VENV="$BASE/venv"
PY="$VENV/bin/python"
READY="$VENV/.ready"
WANT="graphifyy==0.8.35"
LOCK="$BASE/.lock"

log() { printf '[spongram-codemap] %s\n' "$1" >&2; }

# First python >=3.10 on PATH (macOS system python3 is often 3.9 — too old for
# graphifyy). Prints the resolved interpreter path on stdout, nothing else.
find_python() {
  _cand=""
  for c in python3.13 python3.12 python3.11 python3.10 python3; do
    command -v "$c" >/dev/null 2>&1 || continue
    _v=$("$c" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null || echo 0)
    if [ "$_v" -ge 310 ] 2>/dev/null; then _cand=$(command -v "$c"); break; fi
  done
  [ -n "$_cand" ] || return 1
  printf '%s' "$_cand"
}

venv_ready() {
  [ -x "$PY" ] && [ -f "$READY" ] && [ "$(cat "$READY" 2>/dev/null)" = "$WANT" ]
}

ensure_venv() {
  venv_ready && return 0
  mkdir -p "$BASE"
  # Break a stale lock left by a crashed bootstrap (older than 15 minutes).
  if [ -d "$LOCK" ] && [ -z "$(find "$LOCK" -maxdepth 0 -mmin -15 2>/dev/null)" ]; then
    rm -rf "$LOCK"
  fi
  # Atomic lock: exactly one racer wins (two SessionStarts must not corrupt it).
  mkdir "$LOCK" 2>/dev/null || return 1
  _rc=1
  _pybin=$(find_python) || {
    log "no python>=3.10 found — code map disabled (install python 3.10+)"
    rm -rf "$LOCK"
    return 1
  }
  log "installing code-map extractor (~240 MB, one-time)…"
  _tmp="$BASE/venv.tmp.$$"
  rm -rf "$_tmp"
  if "$_pybin" -m venv "$_tmp" >>"$BASE/last.log" 2>&1 &&
    "$_tmp/bin/python" -m pip install -q --disable-pip-version-check "$WANT" >>"$BASE/last.log" 2>&1; then
    printf '%s' "$WANT" >"$_tmp/.ready"
    rm -rf "$VENV"
    mv "$_tmp" "$VENV"
    log "code-map extractor ready"
    _rc=0
  else
    log "code-map extractor install failed (see $BASE/last.log) — will retry"
    rm -rf "$_tmp"
  fi
  rm -rf "$LOCK"
  return $_rc
}

ensure_venv || exit 0
[ -x "$PY" ] || exit 0
exec env PYTHONPATH="$LIB" "$PY" -m spongram_codemap.cli "$@"
