#!/usr/bin/env bash
# Clean removal of the spongram code-map post-commit hook from THIS repo.
# Mirror of install-codemap-hook.sh: the installer appends "$MARK" + the hook
# body to .git/hooks/post-commit, so everything from the MARK line onward is
# ours — anything the user had BEFORE the mark is preserved.
set -eu
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="$REPO_ROOT/.git/hooks/post-commit"
STATE="$REPO_ROOT/.git/spongram-codemap.json"
MARK="# spongram-codemap-hook"

if [ ! -f "$HOOK" ] || ! grep -q "$MARK" "$HOOK"; then
  echo "[spongram] code-map hook not installed in this repo — nothing to do"
else
  TMP="$(mktemp)"
  awk -v m="$MARK" '$0==m{exit} {print}' "$HOOK" > "$TMP"
  if [ -s "$TMP" ]; then
    mv "$TMP" "$HOOK"
    chmod +x "$HOOK"
    echo "[spongram] code-map hook removed (pre-existing post-commit content preserved)"
  else
    rm -f "$TMP" "$HOOK"
    echo "[spongram] code-map hook removed"
  fi
fi

if [ -f "$STATE" ]; then
  rm -f "$STATE"
  echo "[spongram] code-map state file removed"
fi
exit 0
