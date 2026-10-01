#!/usr/bin/env python3
"""Manual macOS smoke: synthetic temporary Keychain entry, no production secrets."""
import json
from pathlib import Path
import secrets
import subprocess
import sys
import uuid

SCRIPTS = Path(__file__).resolve().parents[1] / 'plugins/spongram-codex/scripts'
sys.path.insert(0, str(SCRIPTS))
from connection import Keychain, prepare_keychain, owned_source


def main():
    prepare_keychain()
    store = Keychain(interactive=True)
    name = 'spongram-release-smoke-' + uuid.uuid4().hex
    key = secrets.token_urlsafe(32)
    try:
        assert store.read(name) is None
        store.write(name, key)
        assert store.read(name) == key
        result = subprocess.run([sys.executable, str(SCRIPTS / 'auth_headers.py'),
                                 json.dumps(owned_source(name))],
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        assert json.loads(result.stdout)['Authorization'] == 'Bearer ' + key
        for _ in range(8):
            # New process each time, always with Keychain interaction disabled.
            assert Keychain().read(name) == key
        replacement = secrets.token_urlsafe(32)
        store.write(name, replacement)
        assert store.read(name) == replacement
    finally:
        store.delete(name)
    assert store.read(name) is None
    print('Native macOS Keychain create/read/rotate/helper/delete: OK; no credential printed.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.exit('Native Keychain smoke failed (details suppressed to protect credentials).')
