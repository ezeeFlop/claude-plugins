#!/usr/bin/env bash
set -eu
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="$REPO_ROOT/.git/hooks/post-commit"
SRC="$(dirname "$0")/post-commit.sh"
MARK="# spongram-codemap-hook"
if [ -f "$HOOK" ] && grep -q "$MARK" "$HOOK"; then
  echo "[spongram] code-map hook already installed"; exit 0
fi
mkdir -p "$REPO_ROOT/.git/hooks"
{ echo "$MARK"; cat "$SRC"; } >> "$HOOK"
chmod +x "$HOOK"
echo "[spongram] code-map post-commit hook installed"
