#!/usr/bin/env python3
"""Explicit Codex map upload, using the shared extractor and macOS Keychain."""

import argparse
import subprocess
import sys
from pathlib import Path
from connection import credentials, SetupError

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "lib"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "update"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        endpoint, key = credentials()
    except SetupError as error:
        parser.error(str(error))
    path = args.path.resolve()
    try:
        root = Path(
            subprocess.check_output(
                ["git", "-C", str(path), "rev-parse", "--show-toplevel"], text=True
            ).strip()
        )
        git_dir = Path(
            subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "--absolute-git-dir"], text=True
            ).strip()
        )
    except subprocess.CalledProcessError:
        parser.error("Path must be in a Git repository")
    if not endpoint.endswith("/mcp"):
        parser.error("Configured endpoint must end in /mcp")
    # Shared map identity with Claude; separate local state avoids races between clients.
    cli_args = [
        args.action,
        str(root),
        "--base-url",
        endpoint[:-4],
        "--key",
        key,
        "--repo",
        root.name,
        "--state",
        str(git_dir / "spongram-codemap-codex.json"),
    ]
    try:
        from spongram_codemap.cli import main as run
    except ImportError:
        parser.error("Install graphifyy==0.8.35 in this Python environment first")
    return run(cli_args)  # in-process: the secret never enters a subprocess argv


if __name__ == "__main__":
    sys.exit(main())
