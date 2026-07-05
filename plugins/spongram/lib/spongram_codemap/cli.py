# spongram_codemap/cli.py
"""`spongram-codemap` CLI : build / update / hook install."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .extractor import _SUFFIXES, LANGUAGES, extract_repo
from .manifest import changed_since, scan_manifest
from .push import push  # ré-exporté pour pouvoir le monkeypatcher dans les tests

_SUFFIX_TUPLE = tuple(_SUFFIXES.keys())


def _do_build(args) -> int:
    out = extract_repo(args.path, languages=LANGUAGES)
    push(args.base_url, args.key, args.repo, out["nodes"], out["edges"], [])
    if args.state:
        Path(args.state).write_text(
            json.dumps({"repo": args.repo, "manifest": scan_manifest(args.path, _SUFFIX_TUPLE)}),
            encoding="utf-8",
        )
    print(f"[codemap] build: {len(out['nodes'])} nodes, {len(out['edges'])} edges")
    return 0


def _do_update(args) -> int:
    prev: dict = {}
    state_path = Path(args.state) if args.state else None
    if state_path and state_path.exists():
        prev = json.loads(state_path.read_text(encoding="utf-8")).get("manifest", {})
    _, deleted = changed_since(args.path, _SUFFIX_TUPLE, prev)
    out = extract_repo(args.path, languages=LANGUAGES)
    push(args.base_url, args.key, args.repo, out["nodes"], out["edges"], deleted)
    if state_path:
        state_path.write_text(
            json.dumps({"repo": args.repo, "manifest": scan_manifest(args.path, _SUFFIX_TUPLE)}),
            encoding="utf-8",
        )
    print(f"[codemap] update: {len(out['nodes'])} nodes, {len(deleted)} pruned")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spongram-codemap")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("build", "update"):
        sp = sub.add_parser(name)
        sp.add_argument("path")
        sp.add_argument("--base-url", required=True)
        sp.add_argument("--key", required=True)
        sp.add_argument("--repo", required=True)
        sp.add_argument("--state", default=None)
    args = p.parse_args(argv)
    if args.cmd == "build":
        return _do_build(args)
    if args.cmd == "update":
        return _do_update(args)
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
