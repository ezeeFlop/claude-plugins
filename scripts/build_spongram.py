#!/usr/bin/env python3
"""Vendor the shared core into each self-contained plugin; --check detects drift."""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "shared/spongram"


def outputs():
    for client, name in [("claude-code", "spongram"), ("codex", "spongram-codex")]:
        plugin = ROOT / "plugins" / name
        for source in sorted((SHARED / "lib").rglob("*.py")):
            yield plugin / "lib" / source.relative_to(SHARED / "lib"), source.read_bytes()
        adapter = (plugin / "instructions.md").read_text()
        header = (
            "---\nname: spongram\ndescription: Use Spongram to remember durable "
            "decisions and preferences, recall project history across clients, "
            "and query the structural code map.\n---\n\n"
        )
        body = header + "# Spongram\n\n" + adapter + "\n" + (SHARED / "memory.md").read_text()
        yield plugin / "skills/spongram/SKILL.md", body.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    drift = []
    for path, body in outputs():
        if args.check:
            if not path.is_file() or path.read_bytes() != body:
                drift.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
    if drift:
        parser.exit(1, "Shared core drift:\n" + "\n".join(drift) + "\n")


if __name__ == "__main__":
    main()
