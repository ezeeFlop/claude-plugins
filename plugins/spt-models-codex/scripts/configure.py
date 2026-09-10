"""Configure the SPT Models plugin without exposing credentials to the agent."""
import argparse
import getpass
import json
import subprocess
import sys
import httpx
import claude_credentials
from connection import (DEFAULT_INSTANCE, Keychain, SetupError, account, atomic_write,
                        directory, load_profile, normalize_instance, read_secret, validate_key)


def ask(prompt, default="", secret=False, terminal=False):
    if terminal:
        if not sys.stdin.isatty():
            raise SetupError("Use --gui from Codex, or --terminal in your own terminal")
        return getpass.getpass(prompt + ": ") if secret else (input(f"{prompt} [{default}]: ").strip() or default)
    script = '''on run argv
set answer to display dialog (item 1 of argv) with title "SPT Models — Codex" default answer (item 2 of argv) HIDDEN buttons {"Annuler", "Continuer"} default button "Continuer" cancel button "Annuler"
return text returned of answer
end run'''.replace("HIDDEN", "with hidden answer" if secret else "without hidden answer")
    result = subprocess.run(["/usr/bin/osascript", "-e", script, prompt, default], capture_output=True, text=True)
    if result.returncode:
        raise SetupError("Configuration cancelled or dialog unavailable")
    return result.stdout.rstrip("\r\n")


def probe(url, key):
    try:
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            response = client.get(url + "/v1/models", headers={"Authorization": "Bearer " + key})
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise ValueError()
    except (httpx.HTTPError, ValueError):
        raise SetupError("Catalogue verification failed; check gateway URL and API key") from None


def save(url, key, store, source=None, verify=probe):
    url, key = normalize_instance(url), validate_key(key)
    verify(url, key)
    name = account(url)
    source = source or {"kind": "spt-models", "account": name}
    owned = source["kind"] == "spt-models"
    previous = store.read(name) if owned else None
    try:
        if owned:
            store.write(name, key)
        profile = {"instance_url": url, "account": name, "credential": source}
        atomic_write(directory() / "connection.json", (json.dumps(profile, indent=2) + "\n").encode())
    except Exception:
        if owned:
            store.delete(name) if previous is None else store.write(name, previous)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    ui = parser.add_mutually_exclusive_group()
    ui.add_argument("--gui", action="store_true")
    ui.add_argument("--terminal", action="store_true")
    args = parser.parse_args()
    try:
        existing = load_profile()
        default = existing["instance_url"]
    except SetupError:
        existing = None
        known = {p["instance_url"] for p in claude_credentials.profiles()}
        default = next(iter(known)) if len(known) == 1 else DEFAULT_INSTANCE
    url = normalize_instance(ask("URL de la gateway SPT Models", default, terminal=args.terminal))
    candidate = None
    if existing and existing["instance_url"] == url:
        key = read_secret(existing["credential"])
        if key:
            candidate = (existing["credential"], key)
    if candidate is None:
        candidate = claude_credentials.find(url)
    source = None
    if candidate and ask("Réutiliser la clé SPT Models existante du trousseau ? (oui/non)", "oui", terminal=args.terminal).lower() in ("oui", "o", "yes", "y"):
        source, key = candidate
    else:
        key = validate_key(ask("Clé API SPT Models (sans Bearer)", secret=True, terminal=args.terminal))
    save(url, key, Keychain(), source)
    print("SPT Models configured: catalogue verified, key in Keychain. Start a new Codex thread.")


if __name__ == "__main__":
    try:
        main()
    except SetupError as error:
        sys.exit(str(error))
    except (OSError, ValueError, KeyError, TypeError):
        sys.exit("SPT Models setup failed; no credential is logged.")
