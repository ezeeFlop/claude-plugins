"""Read-only discovery of the co-installed Spongram Claude Code credentials."""
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata
from connection import SetupError, normalize_instance, read_secret

PLUGIN_IDS = ("spongram@sponge-theory", "spongram")


def read_json(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def profiles():
    """Only inspect the normal/explicit Claude config root and Spongram metadata."""
    root = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    settings = read_json(root / "settings.json").get("pluginConfigs", {})
    installed = read_json(root / "plugins/installed_plugins.json").get("plugins", {})
    secure_root = os.environ.get("CLAUDE_SECURESTORAGE_CONFIG_DIR")
    custom = secure_root if secure_root is not None else os.environ.get("CLAUDE_CONFIG_DIR")
    suffix = ("-" + hashlib.sha256(unicodedata.normalize("NFC", custom).encode()).hexdigest()[:8]) if custom else ""
    user = os.environ.get("USER") or getpass.getuser()
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", user):
        user = "claude-code-user"
    result = []
    for plugin in PLUGIN_IDS:
        option = settings.get(plugin, {}).get("options", {}).get("instance_url")
        instances = [option] if option else []
        if not option:
            for entry in installed.get(plugin, []):
                if entry.get("scope") != "user" or not entry.get("installPath"):
                    continue
                manifest = read_json(Path(entry["installPath"]) / ".claude-plugin/plugin.json")
                default = manifest.get("userConfig", {}).get("instance_url", {}).get("default")
                if default:
                    instances.append(default)
        for value in instances:
            try:
                instance = normalize_instance(value)
            except (SetupError, AttributeError):
                continue
            source = {"kind": "claude", "service": "Claude Code-credentials" + suffix,
                      "account": user, "plugin_id": plugin}
            candidate = {"instance_url": instance, "credential": source}
            if candidate not in result:
                result.append(candidate)
    return result


def find(instance):
    candidates = []
    for profile in profiles():
        if profile["instance_url"] != instance:
            continue
        key = read_secret(profile["credential"])
        if key:
            candidates.append((profile["credential"], key))
    if len(candidates) > 1 and len({key for _, key in candidates}) > 1:
        raise SetupError("Several Claude Spongram keys match this URL; enter the intended key in the masked dialog")
    return candidates[0] if candidates else None
