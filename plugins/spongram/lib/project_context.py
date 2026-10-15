"""Client-independent project tags for the Spongram Claude Code and Codex adapters.

The project slug comes from the first rule that yields a value:

1. ``SPONGRAM_PROJECT``, an explicit override (a lowercase slug, else ``ValueError``);
2. the nearest ``.spongram.json`` (``{"project": "<slug>"}``), searched from the
   session directory up to the git root, else up to ``$HOME`` (both inclusive;
   outside both, the session directory alone). The first file found is
   authoritative: an invalid one yields nothing rather than letting a parent's
   file win. Its value is normalized like a directory name, 1 to 64 characters;
3. the main repository's directory name: a linked worktree resolves to the main
   checkout, a submodule keeps its own name;
4. the session directory's name.

This file has three byte-identical copies: the Spongram server repository's
``mcp/claude_code_plugin/lib/`` (the source), its per-instance bundle templates,
and the public marketplace's ``shared/spongram/lib/``.
"""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

SLUG_FILE = ".spongram.json"
MAX_SLUG_FILE_BYTES = 4096
MAX_SLUG_CHARS = 64


def git(cwd, *args):
    try:
        return subprocess.check_output(
            ["git", "-C", str(cwd), *args],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def normalize(name):
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")


def file_slug(cwd, top):
    """Project of the nearest .spongram.json, or None (rule 2)."""
    chain = [cwd, *cwd.parents]
    try:
        stop = Path(top).resolve() if top else Path.home().resolve()
    except (KeyError, RuntimeError):
        stop = cwd
    if stop not in chain:
        stop = cwd
    for directory in chain[: chain.index(stop) + 1]:
        candidate = directory / SLUG_FILE
        if not candidate.is_file():
            continue
        try:
            with candidate.open("rb") as handle:
                raw = handle.read(MAX_SLUG_FILE_BYTES + 1)
            if len(raw) > MAX_SLUG_FILE_BYTES:
                return None
            data = json.loads(raw.decode("utf-8-sig"))
        except (OSError, ValueError, RecursionError):
            # json.loads raises RecursionError, not ValueError, on deep nesting (Python <= 3.11).
            return None
        value = data.get("project") if isinstance(data, dict) else None
        slug = normalize(value) if isinstance(value, str) else ""
        return slug if 0 < len(slug) <= MAX_SLUG_CHARS else None
    return None


def repo_name(cwd, top):
    """Directory name of the main checkout (rule 3); empty outside git."""
    if not top:
        return ""
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not os.path.isabs(common):
        # git < 2.31 rejects --path-format (or echoes it): plain output is relative to cwd.
        plain = git(cwd, "rev-parse", "--git-common-dir")
        common = str(cwd / plain) if plain else ""
    if common:
        path = Path(common).resolve()
        if path.name == ".git":
            return path.parent.name
    return Path(top).name


def context(cwd, client):
    if client not in ("codex", "claude-code"):
        raise ValueError("Unsupported client")
    cwd = Path(cwd).resolve()
    slug = os.environ.get("SPONGRAM_PROJECT", "")
    if slug and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", slug):
        raise ValueError("SPONGRAM_PROJECT must be a lowercase project slug")
    if not slug:
        top = git(cwd, "rev-parse", "--show-toplevel")
        slug = file_slug(cwd, top) or normalize(repo_name(cwd, top)) or normalize(cwd.name)
        slug = slug or "unknown"
    remote = git(cwd, "remote", "get-url", "origin")
    match = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", remote)
    repo = match.group(1) if match else ""
    branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    # Do not leak URL credentials or inject whitespace-delimited source tags.
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        repo = ""
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", branch):
        branch = ""
    tags = [f"project={slug}"]
    tags += [f"{key}={value}" for key, value in (("repo", repo), ("branch", branch)) if value]
    tags.append(f"client={client}")
    return dict(
        project_slug=slug,
        repo=repo,
        branch=branch,
        cwd=str(cwd),
        source_description=" ".join(tags),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--client", required=True, choices=["codex", "claude-code"])
    args = parser.parse_args()
    print(json.dumps(context(args.cwd, args.client)))
