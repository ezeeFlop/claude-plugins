#!/usr/bin/env python3
"""Select the instance in this plugin checkout; never read or write a brain key."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

PLUGIN = Path(__file__).resolve().parents[1]


def server_config(instance):
    parsed = urlsplit(instance)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Use an HTTPS instance URL without credentials, query or fragment")
    return {
        "url": instance.rstrip("/") + "/mcp",
        "bearer_token_env_var": "SPONGRAM_BRAIN_KEY",
        "http_headers": {"X-Spongram-Client": "codex"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-url", required=True, help="Instance URL without /mcp")
    parser.add_argument(
        "--print-toml",
        action="store_true",
        help="Print standalone MCP config instead of editing the plugin",
    )
    args = parser.parse_args()
    try:
        server = server_config(args.instance_url)
    except ValueError as error:
        parser.error(str(error))
    if args.print_toml:
        print("[mcp_servers.spongram]")
        print("url = " + json.dumps(server["url"]))
        print('bearer_token_env_var = "SPONGRAM_BRAIN_KEY"')
        print('http_headers = { "X-Spongram-Client" = "codex" }')
    else:
        (PLUGIN / ".mcp.json").write_text(
            json.dumps({"mcpServers": {"spongram": server}}, indent=2) + "\n"
        )
        print("Updated plugin endpoint. No secret was read or stored; no plugin was installed.")


if __name__ == "__main__":
    main()
