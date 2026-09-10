"""Incremental change detection by content hash. Plain stdlib, no graphify dep."""

from __future__ import annotations

import hashlib
from pathlib import Path


def _iter_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in suffixes:
            parts = set(p.parts)
            if parts & {".git", "node_modules", ".venv", "target", "dist", "build", "__pycache__"}:
                continue
            out.append(p)
    return out


def scan_manifest(root: str | Path, suffixes: tuple[str, ...]) -> dict[str, str]:
    """Return {relative_posix_path: sha256_hex} for every supported file."""
    root = Path(root)
    manifest: dict[str, str] = {}
    for p in _iter_files(root, suffixes):
        rel = p.relative_to(root).as_posix()
        manifest[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return manifest


def changed_since(
    root: str | Path, suffixes: tuple[str, ...], previous: dict[str, str]
) -> tuple[list[str], list[str]]:
    """Return (changed_or_new_rel_paths, deleted_rel_paths) vs previous manifest."""
    current = scan_manifest(root, suffixes)
    changed = [rel for rel, h in current.items() if previous.get(rel) != h]
    deleted = [rel for rel in previous if rel not in current]
    return changed, deleted
