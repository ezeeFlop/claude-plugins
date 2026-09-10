#!/usr/bin/env python3
"""Private Codex http_headers_helper. Its stdout is for Codex, never for the model."""
import json
import sys
from connection import SetupError, read_secret


def main():
    # Account bound to the endpoint in config.toml, not to a mutable profile.
    if len(sys.argv) != 2:
        raise SetupError("Missing Spongram credential reference; rerun setup")
    key = read_secret(json.loads(sys.argv[1]))
    if key is None:
        raise SetupError("Spongram key missing from Keychain; rerun setup")
    print(json.dumps({"Authorization": "Bearer " + key}))


if __name__ == "__main__":
    try:
        main()
    except (SetupError, OSError, ValueError, KeyError, TypeError):
        sys.exit("Spongram Keychain authentication unavailable; run spongram-setup.")
