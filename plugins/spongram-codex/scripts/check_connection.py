#!/usr/bin/env python3
"""Read-only MCP handshake and tools/list probe; never reads memories or writes them."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def decode(data, content_type):
    text = data.decode("utf-8")
    if "text/event-stream" in content_type:
        for event in text.replace("\r\n", "\n").split("\n\n"):
            payload = "\n".join(
                line[5:].lstrip() for line in event.splitlines() if line.startswith("data:")
            )
            if payload:
                obj = json.loads(payload)
                if "result" in obj or "error" in obj:
                    return obj
        raise ValueError("No JSON-RPC response in SSE stream")
    return json.loads(text)


def probe(url, key, open_url=urllib.request.urlopen):
    session = None
    protocol = "2025-03-26"

    def request(method, ident=None, params=None):
        nonlocal session
        message = {"jsonrpc": "2.0", "method": method}
        if ident is not None:
            message["id"] = ident
        if params is not None:
            message["params"] = params
        headers = {
            "Authorization": "Bearer " + key,
            "X-Spongram-Client": "codex",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if method != "initialize":
            headers["MCP-Protocol-Version"] = protocol
        if session:
            headers["Mcp-Session-Id"] = session
        req = urllib.request.Request(
            url, data=json.dumps(message).encode(), headers=headers, method="POST"
        )
        with open_url(req, timeout=20) as response:
            session = response.headers.get("Mcp-Session-Id") or session
            if ident is None:
                return None
            obj = decode(response.read(), response.headers.get("Content-Type", ""))
        if obj.get("id") != ident or "error" in obj or "result" not in obj:
            raise ValueError("MCP request failed: " + method)
        return obj["result"]

    initialized = request(
        "initialize",
        1,
        {
            "protocolVersion": protocol,
            "capabilities": {},
            "clientInfo": {"name": "spongram-codex-check", "version": "0.5.0"},
        },
    )
    protocol = initialized["protocolVersion"]
    request("notifications/initialized")
    names = set()
    cursor = None
    for page in range(100):
        result = request("tools/list", page + 2, {"cursor": cursor} if cursor else {})
        names.update(tool["name"] for tool in result["tools"])
        cursor = result.get("nextCursor")
        if not cursor:
            break
    else:
        raise ValueError("Too many tools/list pages")
    required = {"add_memory", "search_nodes", "search_memory_facts"}
    if not required <= names:
        raise ValueError("Missing expected Spongram memory tools")
    return sorted(names)


def main():
    key = os.environ.get("SPONGRAM_BRAIN_KEY")
    if not key:
        sys.exit("SPONGRAM_BRAIN_KEY is required in the process environment")
    config = json.loads((Path(__file__).resolve().parents[1] / ".mcp.json").read_text())
    url = config["mcpServers"]["spongram"]["url"]
    try:
        names = probe(url, key)
    except urllib.error.HTTPError as error:
        sys.exit(f"MCP HTTP error {error.code}; check endpoint and brain key")
    except (OSError, ValueError, KeyError):
        sys.exit("MCP check failed; check endpoint, protocol and server availability")
    print(f"MCP initialize + tools/list OK ({len(names)} tools). No memories read or written.")


if __name__ == "__main__":
    main()
