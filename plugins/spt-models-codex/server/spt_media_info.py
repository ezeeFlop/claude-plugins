"""Identify a generated file from its bytes: MIME type, extension, image size,
audio / video duration.  Pure Python, no dependency — the MCP server must stay
installable with `mcp` and `httpx` only.

The bytes are the source of truth, never the gateway's declared format: some
models label their output wrongly (omnivoice and stable-audio answer
`"format": "mp3"` with a RIFF/WAVE body).  Every parser is defensive: a
truncated or unusual file yields `None` for the field it cannot read, never an
exception.
"""
from __future__ import annotations

import struct
from typing import Any

# ---------------------------------------------------------------- type detection

_EXT = {
    "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif",
    "audio/wav": "wav", "audio/flac": "flac", "audio/mpeg": "mp3", "audio/ogg": "ogg",
    "audio/mp4": "m4a", "video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm",
    "model/gltf-binary": "glb", "application/vnd.autodesk.fbx": "fbx",
    "application/octet-stream": "bin",
}


def sniff_type(data: bytes) -> str | None:
    """MIME type from the magic bytes, or None when unrecognised."""
    head = data[:64]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if head.startswith(b"fLaC"):
        return "audio/flac"
    if head.startswith(b"OggS"):
        return "audio/ogg"
    if head.startswith(b"ID3") or (len(head) > 1 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return "audio/mpeg"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"M4A ", b"M4B ", b"M4P "):
            return "audio/mp4"
        if brand == b"qt  ":
            return "video/quicktime"
        return "video/mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    if head.startswith(b"glTF"):
        return "model/gltf-binary"
    if head.startswith(b"Kaydara FBX Binary"):
        return "application/vnd.autodesk.fbx"
    return None


def extension_for(mime: str | None) -> str:
    return _EXT.get(mime or "", "bin")


# ---------------------------------------------------------------- images

def image_size(data: bytes, mime: str | None) -> tuple[int, int] | None:
    try:
        if mime == "image/png" and len(data) >= 24:
            return struct.unpack(">II", data[16:24])
        if mime == "image/gif" and len(data) >= 10:
            return struct.unpack("<HH", data[6:10])
        if mime == "image/webp":
            chunk = data[12:16]
            if chunk == b"VP8X" and len(data) >= 30:
                w = 1 + int.from_bytes(data[24:27], "little")
                h = 1 + int.from_bytes(data[27:30], "little")
                return w, h
            if chunk == b"VP8L" and len(data) >= 25:
                b = int.from_bytes(data[21:25], "little")
                return 1 + (b & 0x3FFF), 1 + ((b >> 14) & 0x3FFF)
            if chunk == b"VP8 " and len(data) >= 30:
                w, h = struct.unpack("<HH", data[26:30])
                return w & 0x3FFF, h & 0x3FFF
        if mime == "image/jpeg":
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seg = struct.unpack(">H", data[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                i += 2 + seg
    except (struct.error, IndexError, ValueError):
        return None
    return None


# ---------------------------------------------------------------- audio

def _wav_duration(data: bytes) -> float | None:
    i, byte_rate, data_size = 12, None, None
    while i + 8 <= len(data):
        cid, size = data[i:i + 4], struct.unpack("<I", data[i + 4:i + 8])[0]
        if cid == b"fmt " and i + 16 <= len(data):
            byte_rate = struct.unpack("<I", data[i + 16:i + 20])[0]
        elif cid == b"data":
            # Streaming writers leave 0 or 0xFFFFFFFF here: use what is really there.
            data_size = size if 0 < size < 0xFFFFFFFF and i + 8 + size <= len(data) else len(data) - i - 8
            break
        i += 8 + size + (size & 1)
    if byte_rate and data_size is not None:
        return data_size / byte_rate
    return None


def _flac_duration(data: bytes) -> float | None:
    # STREAMINFO is the first metadata block: 20-bit rate, 36-bit total samples.
    if len(data) < 26:
        return None
    b = data[18:26]
    rate = (b[0] << 12) | (b[1] << 4) | (b[2] >> 4)
    total = ((b[3] & 0x0F) << 32) | int.from_bytes(b[4:8], "big")
    return total / rate if rate and total else None


_MP3_BITRATES = {  # (version_bit, layer) -> kbps table, MPEG-1 / MPEG-2(.5) layer III
    1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0],
    2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0],
}
_MP3_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def _mp3_duration(data: bytes) -> float | None:
    i = 0
    if data.startswith(b"ID3") and len(data) >= 10:
        size = 0
        for byte in data[6:10]:
            size = (size << 7) | (byte & 0x7F)
        i = 10 + size
    while i + 4 <= len(data) and not (data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0):
        i += 1
    if i + 4 > len(data):
        return None
    h = int.from_bytes(data[i:i + 4], "big")
    version = (h >> 19) & 3          # 3 = MPEG-1, 2 = MPEG-2, 0 = MPEG-2.5
    layer = (h >> 17) & 3            # 1 = layer III
    br_idx, sr_idx = (h >> 12) & 0xF, (h >> 10) & 3
    if version == 1 or layer != 1 or sr_idx == 3:
        return None
    rate = _MP3_RATES[version][sr_idx]
    kbps = _MP3_BITRATES[1 if version == 3 else 2][br_idx]
    samples_per_frame = 1152 if version == 3 else 576
    mono = ((h >> 6) & 3) == 3
    side = (17 if mono else 32) if version == 3 else (9 if mono else 17)
    xing = data[i + 4 + side:i + 4 + side + 12]
    if xing[:4] in (b"Xing", b"Info") and int.from_bytes(xing[4:8], "big") & 1:
        frames = int.from_bytes(xing[8:12], "big")
        return frames * samples_per_frame / rate
    if kbps:
        return (len(data) - i) * 8 / (kbps * 1000)   # constant bit rate estimate
    return None


def _ogg_duration(data: bytes) -> float | None:
    rate = None
    if b"OpusHead" in data[:200]:
        rate = 48000
    else:
        k = data.find(b"\x01vorbis", 0, 400)
        if k >= 0 and k + 16 <= len(data):
            rate = struct.unpack("<I", data[k + 12:k + 16])[0]
    last = data.rfind(b"OggS")
    if not rate or last < 0 or last + 14 > len(data):
        return None
    granule = struct.unpack("<q", data[last + 6:last + 14])[0]
    if granule <= 0:
        return None
    if rate == 48000 and b"OpusHead" in data[:200]:
        k = data.find(b"OpusHead")
        pre_skip = struct.unpack("<H", data[k + 10:k + 12])[0] if k + 12 <= len(data) else 0
        granule -= pre_skip
    return granule / rate


def _mp4_duration(data: bytes) -> float | None:
    """mvhd duration / timescale, searched inside the top-level moov box."""
    i = 0
    while i + 8 <= len(data):
        size, kind = struct.unpack(">I", data[i:i + 4])[0], data[i + 4:i + 8]
        header = 8
        if size == 1 and i + 16 <= len(data):
            size, header = struct.unpack(">Q", data[i + 8:i + 16])[0], 16
        elif size == 0:
            size = len(data) - i
        if kind == b"moov":
            j, end = i + header, min(i + size, len(data))
            while j + 8 <= end:
                sub_size, sub_kind = struct.unpack(">I", data[j:j + 4])[0], data[j + 4:j + 8]
                if sub_kind == b"mvhd":
                    version = data[j + 8]
                    if version == 1:
                        timescale, duration = struct.unpack(">IQ", data[j + 28:j + 40])
                    else:
                        timescale, duration = struct.unpack(">II", data[j + 20:j + 28])
                    return duration / timescale if timescale else None
                if sub_size < 8:
                    break
                j += sub_size
            return None
        if size < 8:
            break
        i += size
    return None


def duration_seconds(data: bytes, mime: str | None) -> float | None:
    try:
        if mime == "audio/wav":
            return _wav_duration(data)
        if mime == "audio/flac":
            return _flac_duration(data)
        if mime == "audio/mpeg":
            return _mp3_duration(data)
        if mime == "audio/ogg":
            return _ogg_duration(data)
        if mime in ("video/mp4", "audio/mp4", "video/quicktime"):
            return _mp4_duration(data)
    except (struct.error, IndexError, ValueError, ZeroDivisionError):
        return None
    return None


# ---------------------------------------------------------------- summary

def describe(data: bytes, declared_type: str | None = None) -> dict[str, Any]:
    """`{mime_type, extension, width?, height?, duration_s?}` for these bytes.

    The declared type is only a fallback for formats the sniffer does not know.
    """
    mime = sniff_type(data) or (declared_type.split(";")[0].strip() if declared_type else None) \
        or "application/octet-stream"
    info: dict[str, Any] = {"mime_type": mime, "extension": extension_for(mime)}
    if mime.startswith("image/"):
        size = image_size(data, mime)
        if size:
            info["width"], info["height"] = size
    elif mime.startswith(("audio/", "video/")):
        seconds = duration_seconds(data, mime)
        if seconds is not None:
            info["duration_s"] = round(seconds, 3)
    return info
