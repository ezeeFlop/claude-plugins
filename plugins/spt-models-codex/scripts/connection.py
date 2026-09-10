#!/usr/bin/env python3
"""SPT Models profile and macOS Keychain access. Never print credentials."""
import ctypes as c
import hashlib
import json
import os
import re
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit

SERVICE = "ai.sponge-theory.spt-models.codex"
DEFAULT_INSTANCE = "https://models.sponge-theory.dev"


class SetupError(Exception):
    """A deliberately secret-free diagnostic."""


def directory():
    return Path.home() / ".spt-models" / "codex"


def normalize_instance(value):
    value = value.strip().rstrip("/")
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError:
        raise SetupError("Invalid instance URL") from None
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or any(ord(ch) <= 32 or ord(ch) == 127 for ch in value)
            or "\\" in value):
        raise SetupError("Use an HTTPS instance URL without credentials, query or fragment")
    if parsed.path not in ("", "/"):
        raise SetupError("Use the gateway origin without a path")
    return value


def account(instance):
    return hashlib.sha256(normalize_instance(instance).encode()).hexdigest()


def validate_key(key):
    if not key or len(key) > 8192 or any(ord(ch) < 33 or ord(ch) > 126 for ch in key):
        raise SetupError("Enter the API key without spaces or the Bearer prefix")
    return key


def load_profile():
    try:
        profile = json.loads((directory() / "connection.json").read_text())
        instance = normalize_instance(profile["instance_url"])
        if profile["account"] != account(instance):
            raise ValueError()
        return {"instance_url": instance, "account": account(instance),
                "credential": profile.get("credential", {"kind": "spt-models", "account": account(instance)})}
    except (OSError, ValueError, KeyError, TypeError):
        raise SetupError("SPT Models is not configured. Run the spt-models-setup skill.") from None


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


class Keychain:
    """Security.framework directly: no secret in argv, shell or environment."""
    def __init__(self, service=SERVICE):
        self.service = service
        if sys.platform != "darwin":
            raise SetupError("This secure setup currently supports macOS only")
        self.cf = c.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        self.sec = c.CDLL("/System/Library/Frameworks/Security.framework/Security")
        signatures = {
            "CFStringCreateWithCString": ([c.c_void_p, c.c_char_p, c.c_uint32], c.c_void_p),
            "CFDataCreate": ([c.c_void_p, c.c_void_p, c.c_long], c.c_void_p),
            "CFDataGetLength": ([c.c_void_p], c.c_long),
            "CFDataGetBytePtr": ([c.c_void_p], c.c_void_p),
            "CFDictionaryCreate": ([c.c_void_p, c.c_void_p, c.c_void_p, c.c_long,
                                    c.c_void_p, c.c_void_p], c.c_void_p),
            "CFRelease": ([c.c_void_p], None),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.cf, name)
            fn.argtypes, fn.restype = args, result
        for name in ("SecItemCopyMatching", "SecItemAdd", "SecItemUpdate"):
            fn = getattr(self.sec, name)
            fn.argtypes, fn.restype = [c.c_void_p, c.c_void_p], c.c_int32
        self.sec.SecItemDelete.argtypes = [c.c_void_p]
        self.sec.SecItemDelete.restype = c.c_int32

    def constant(self, name):
        library = self.cf if name.startswith("kCF") else self.sec
        return c.c_void_p.in_dll(library, name).value

    def perform(self, operation, name, value=None):
        if self.service != SERVICE and operation != "read":
            raise SetupError("External credential stores are read-only")
        owned = []

        def string(text):
            obj = self.cf.CFStringCreateWithCString(None, text.encode(), 0x08000100)
            owned.append(obj)
            return obj

        def dictionary(items):
            keys = (c.c_void_p * len(items))(*(self.constant(k) for k in items))
            values = (c.c_void_p * len(items))(*items.values())
            obj = self.cf.CFDictionaryCreate(None, keys, values, len(items), None, None)
            owned.append(obj)
            return obj

        try:
            fields = {"kSecClass": self.constant("kSecClassGenericPassword"),
                      "kSecAttrService": string(self.service), "kSecAttrAccount": string(name)}
            if operation == "read":
                fields["kSecReturnData"] = self.constant("kCFBooleanTrue")
                fields["kSecMatchLimit"] = self.constant("kSecMatchLimitOne")
                result = c.c_void_p()
                status = self.sec.SecItemCopyMatching(dictionary(fields), c.byref(result))
                if status == -25300:
                    return None
                if status == 0:
                    owned.append(result.value)
                    return c.string_at(self.cf.CFDataGetBytePtr(result),
                                       self.cf.CFDataGetLength(result)).decode()
            elif operation == "delete":
                status = self.sec.SecItemDelete(dictionary(fields))
                if status == -25300:
                    return None
            elif operation == "write":
                data = validate_key(value).encode()
                blob = self.cf.CFDataCreate(None, data, len(data))
                owned.append(blob)
                query = dictionary(fields)
                updates = dictionary({"kSecValueData": blob})
                status = self.sec.SecItemUpdate(query, updates)
                if status == -25300:
                    fields["kSecValueData"] = blob
                    status = self.sec.SecItemAdd(dictionary(fields), None)
            else:
                raise SetupError("Unknown Keychain operation")
            if status:
                raise SetupError(f"macOS Keychain access failed (status {status})")
        finally:
            for obj in reversed(owned):
                if obj:
                    self.cf.CFRelease(obj)

    def read(self, name):
        return self.perform("read", name)

    def write(self, name, value):
        self.perform("write", name, value)

    def delete(self, name):
        self.perform("delete", name)


def read_secret(source):
    if source.get("kind") == "spt-models":
        key = Keychain().read(source["account"])
    elif source.get("kind") == "claude":
        if (not re.fullmatch(r"Claude Code-credentials(?:-[0-9a-f]{8})?", source["service"])
                or source["plugin_id"] not in ("spt-models@sponge-theory", "spt-models")):
            raise SetupError("Unsupported Claude credential reference")
        raw = Keychain(source["service"]).read(source["account"])
        if raw is None:
            return None
        try:
            # Claude stores one JSON item; extract only the selected plugin's key.
            key = json.loads(raw).get("pluginSecrets", {}).get(source["plugin_id"], {}).get("spt_api_key")
        except (ValueError, AttributeError, TypeError):
            return None
    else:
        raise SetupError("Unsupported credential source")
    return validate_key(key) if key is not None else None
