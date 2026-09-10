"""Client-independent project tags; preserve the historical Claude basename slug."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path


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


def context(cwd, client):
    if client not in ("codex", "claude-code"):
        raise ValueError("Unsupported client")
    cwd = Path(cwd).resolve()
    override = os.environ.get("SPONGRAM_PROJECT", "")
    if override and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", override):
        raise ValueError("SPONGRAM_PROJECT must be a lowercase project slug")
    slug = override or re.sub(r"[^a-z0-9-]+", "-", cwd.name.lower()).strip("-") or "unknown"
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
        project_slug=slug, repo=repo, branch=branch, cwd=str(cwd), source_description=" ".join(tags)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--client", required=True, choices=["codex", "claude-code"])
    args = parser.parse_args()
    print(json.dumps(context(args.cwd, args.client)))
