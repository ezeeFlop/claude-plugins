"""`output_path` for the generation tools: write results to disk, return paths.

An MCP client truncates large tool results, so a base64 image of a few hundred
KB is already lost to the agent.  With `output_path`, generate_image /
generate_video / generate_music / tts write every file themselves and answer
with `files: [{path, bytes, mime_type, width/height | duration_s}]` instead of
base64; every other field of the gateway response is kept.

Order of operations, so a long generation is never wasted:
  1. `prepare()` — before calling the gateway: resolve `~`, create the parent
     directories, prove the directory is writable, refuse an existing target
     file unless `overwrite`.
  2. the generation runs.
  3. `extract_media()` + `write()` — decode, identify each file from its bytes
     (spt_media_info), name and write it; no file is ever clobbered without
     `overwrite` (exclusive create).
"""
from __future__ import annotations

import base64
import binascii
import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spt_media_info import describe

# Equivalent spellings of one extension: a user path "photo.jpeg" holding a JPEG
# is not a mismatch.
_SAME_EXT = {"jpeg": "jpg", "jpe": "jpg", "m4v": "mp4", "oga": "ogg", "opus": "ogg", "qt": "mov", "wave": "wav"}

# Keys whose string value is a base64 file.  `data[].b64_json` is the OpenAI
# shape; the flat ones come from custom loaders (TRELLIS `b64_glb`, UniRig
# `b64_fbx`) and from the audio envelopes (`audio`).
_TOP_LEVEL_MEDIA = re.compile(r"^(audio|video|image|b64_[a-z0-9_]+|[a-z0-9_]+_b64)$")
_ITEM_MEDIA = re.compile(r"^(b64_json|b64_[a-z0-9_]+|[a-z0-9_]+_b64|audio|video|image)$")


class OutputPathError(ValueError):
    """The destination cannot be used.  A ValueError so MCP reports it as a tool error."""


@dataclass
class Target:
    raw: str
    path: Path            # absolute; a directory in directory mode
    directory_mode: bool  # True: files are named <slug>-<timestamp>-<index>.<ext>
    overwrite: bool


@dataclass
class Media:
    data: bytes
    declared_type: str | None = None
    duration_hint: float | None = None


def _looks_like_directory(raw: str, path: Path) -> bool:
    if path.is_dir():
        return True
    if raw.endswith(("/", os.sep)):
        return True
    return not path.exists() and path.suffix == ""


def prepare(output_path: str, overwrite: bool = False, expected_count: int = 1) -> Target:
    """Validate the destination BEFORE generating.  Raises OutputPathError."""
    if not output_path or not str(output_path).strip():
        raise OutputPathError("output_path is empty")
    raw = str(output_path).strip()
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    directory_mode = _looks_like_directory(raw, path) or expected_count > 1
    directory = path if _looks_like_directory(raw, path) else path.parent
    if path.exists() and not path.is_dir() and _looks_like_directory(raw, path):
        raise OutputPathError(f"output_path {raw!r} ends with a separator but is an existing file")
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputPathError(f"cannot create directory {str(directory)!r} for output_path {raw!r}: {exc}") from None
    if not directory.is_dir():
        raise OutputPathError(f"{str(directory)!r} is not a directory (output_path {raw!r})")
    try:  # os.access lies on some network and ACL file systems: really write.
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".spt-write-test-", delete=True):
            pass
    except OSError as exc:
        raise OutputPathError(f"directory {str(directory)!r} is not writable (output_path {raw!r}): {exc}") from None
    if not directory_mode and path.exists() and not overwrite:
        raise OutputPathError(f"{str(path)!r} already exists — pass overwrite=true to replace it")
    return Target(raw=raw, path=path if not directory_mode else directory, directory_mode=directory_mode,
                  overwrite=overwrite)


def _decode(value: Any) -> bytes | None:
    if not isinstance(value, str) or len(value) < 16:
        return None
    try:
        return base64.b64decode("".join(value.split()), validate=True)
    except (binascii.Error, ValueError):
        return None


def extract_media(result: dict[str, Any]) -> tuple[dict[str, Any], list[Media]]:
    """Split a gateway response into (fields without base64, decoded files)."""
    kept: dict[str, Any] = {}
    media: list[Media] = []
    meta = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    duration_hint = meta.get("duration_seconds") if isinstance(meta.get("duration_seconds"), (int, float)) else None
    declared_top = result.get("content_type") if isinstance(result.get("content_type"), str) else None
    for key, value in result.items():
        if key == "data" and isinstance(value, list):
            items = []
            for item in value:
                if not isinstance(item, dict):
                    items.append(item)
                    continue
                rest = {}
                for k, v in item.items():
                    decoded = _decode(v) if _ITEM_MEDIA.match(k) else None
                    if decoded is not None:
                        media.append(Media(decoded, item.get("content_type") or declared_top, duration_hint))
                    elif not (k == "url" and v is None):
                        rest[k] = v
                if rest:
                    items.append(rest)
            if items:
                kept["data"] = items
            continue
        decoded = _decode(value) if _TOP_LEVEL_MEDIA.match(key) else None
        if decoded is not None:
            media.append(Media(decoded, declared_top, duration_hint))
        else:
            kept[key] = value
    return kept, media


def _safe_slug(slug: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", slug).strip("-.") or "output"


def _canonical(ext: str) -> str:
    ext = ext.lower().lstrip(".")
    return _SAME_EXT.get(ext, ext)


def write(target: Target, media: list[Media], slug: str) -> list[dict[str, Any]]:
    """Write every file; return their descriptions.  Raises OutputPathError."""
    if not media:
        raise OutputPathError("the response contained no file to write")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    directory_mode = target.directory_mode or len(media) > 1
    directory = target.path if target.directory_mode else target.path.parent
    files: list[dict[str, Any]] = []
    for index, item in enumerate(media, start=1):
        info = describe(item.data, item.declared_type)
        if item.duration_hint is not None and "duration_s" not in info and \
                info["mime_type"].startswith(("audio/", "video/")):
            info["duration_s"] = round(float(item.duration_hint), 3)
        if directory_mode:
            path = directory / f"{_safe_slug(slug)}-{stamp}-{index}.{info['extension']}"
        else:
            path = target.path
        try:
            with open(path, "wb" if target.overwrite else "xb") as fh:
                fh.write(item.data)
        except FileExistsError:
            raise OutputPathError(f"{str(path)!r} already exists — pass overwrite=true to replace it") from None
        except OSError as exc:
            raise OutputPathError(f"cannot write {str(path)!r}: {exc}") from None
        entry: dict[str, Any] = {"path": str(path.resolve()), "bytes": len(item.data), "mime_type": info["mime_type"]}
        for k in ("width", "height", "duration_s"):
            if k in info:
                entry[k] = info[k]
        if not directory_mode and path.suffix and _canonical(path.suffix) != _canonical(info["extension"]):
            entry["warning"] = (f"the content is {info['mime_type']} but the file name ends in "
                                f"{path.suffix}; the bytes were written unchanged")
        files.append(entry)
    return files
