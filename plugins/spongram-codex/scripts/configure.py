#!/usr/bin/env python3
"""Guided local setup. No key argument, environment variable or chat input."""
import argparse
import getpass
import json
from pathlib import Path
import subprocess
import sys
from connection import (DEFAULT_INSTANCE, Keychain, SetupError, account, atomic_write,
                        directory, load_profile, normalize_instance, validate_key, read_secret)
import claude_credentials
from codex_config import CodexConfig, server_config
from check_connection import probe


def ask(prompt, default="", secret=False, terminal=False):
    if terminal:
        if not sys.stdin.isatty():
            raise SetupError("Terminal setup requires a user-operated terminal; use --gui from Codex")
        if secret:
            return getpass.getpass(prompt + ": ")
        return input(f"{prompt} [{default}]: ").strip() or default
    script = '''on run argv
set answer to display dialog (item 1 of argv) with title "Spongram — Configuration" default answer (item 2 of argv) HIDDEN_ANSWER buttons {"Annuler", "Continuer"} default button "Continuer" cancel button "Annuler"
return text returned of answer
end run'''.replace("HIDDEN_ANSWER", "with hidden answer" if secret else "without hidden answer")
    result = subprocess.run(["/usr/bin/osascript", "-e", script, prompt, default],
                            capture_output=True, text=True)
    if result.returncode:
        raise SetupError("Configuration cancelled or macOS dialog unavailable; no new settings saved")
    return result.stdout.rstrip("\r\n")


def reuse_saved(terminal=False, origin="Spongram"):
    prompt = f"Une clé Spongram utilisée par {origin} existe dans le trousseau pour cette URL. La réutiliser ?"
    if terminal:
        return ask(prompt + " (oui/non)", "oui", terminal=True).lower() in ("oui", "o", "yes", "y")
    script = 'button returned of (display dialog "' + prompt + '" with title "Spongram" buttons {"Annuler", "Autre clé", "Réutiliser"} default button "Réutiliser" cancel button "Annuler")'
    result = subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True, text=True)
    if result.returncode:
        raise SetupError("Configuration cancelled; no new settings saved")
    return result.stdout.strip() == "Réutiliser"


def save(instance, key, store, config, verify=probe, source=None):
    verify(instance + "/mcp", key)
    name = account(instance)
    source = source or {"kind": "spongram", "account": name}
    private_key = source["kind"] == "spongram"
    previous_key = store.read(name) if private_key else None
    path = directory() / "connection.json"
    previous_profile = path.read_bytes() if path.exists() else None
    for filename in ("connection.py", "auth_headers.py"):
        atomic_write(directory() / "runtime" / filename,
                     (Path(__file__).parent / filename).read_bytes())
    try:
        if private_key:
            store.write(name, key)
        atomic_write(path, (json.dumps({"instance_url": instance, "account": name, "credential": source}, indent=2) + "\n").encode())
        config.write(server_config(instance, source))
    except Exception:
        if private_key:
            if previous_key is None:
                store.delete(name)
            else:
                store.write(name, previous_key)
        if previous_profile is None:
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, previous_profile)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    ui = parser.add_mutually_exclusive_group()
    ui.add_argument("--gui", action="store_true", help="macOS dialogs (default)")
    ui.add_argument("--terminal", action="store_true", help="User-operated terminal, hidden key input")
    parser.add_argument("--status", action="store_true", help="Report profile presence without reading the key")
    parser.add_argument("--remove", action="store_true", help="Remove this setup's MCP connection and active key")
    args = parser.parse_args()
    if args.status:
        load_profile()
        print("Spongram profile saved. Run check_connection.py to verify authentication.")
        return
    store = Keychain()
    if args.remove:
        profile = load_profile()
        with CodexConfig() as config:
            config.write(None)
        if profile["credential"]["kind"] == "spongram":
            store.delete(profile["account"])
        (directory() / "connection.json").unlink()
        print("Spongram MCP connection removed; Codex-owned active key removed if present. Claude Code is unchanged.")
        return
    try:
        existing = load_profile()
        default = existing["instance_url"]
    except SetupError:
        existing = None
        known = {p["instance_url"] for p in claude_credentials.profiles()}
        default = next(iter(known)) if len(known) == 1 else DEFAULT_INSTANCE
    instance = normalize_instance(ask("URL de votre instance Spongram", default, terminal=args.terminal))
    found = None
    try:
        if existing and existing["instance_url"] == instance:
            key = read_secret(existing["credential"])
            if key:
                found = (existing["credential"], key)
        if found is None:
            found = claude_credentials.find(instance)
    except SetupError as error:
        print(str(error), file=sys.stderr)
    source = None
    if found and reuse_saved(args.terminal, "Claude Code" if found[0]["kind"] == "claude" else "Codex"):
        source, key = found
    else:
        key = validate_key(ask("Clé du cerveau Spongram (sans le préfixe Bearer)",
                               secret=True, terminal=args.terminal))
    with CodexConfig() as config:
        save(instance, key, store, config, source=source)
    print("Spongram configured: URL saved, key in macOS Keychain, MCP handshake verified. Start a new Codex session.")


if __name__ == "__main__":
    try:
        main()
    except SetupError as error:
        sys.exit(str(error))
    except (OSError, ValueError, KeyError, TypeError):
        sys.exit("Spongram setup failed; check endpoint, brain key and local permissions. No secret is logged.")
