---
name: spongram-setup
description: Configure Spongram after installation in Codex on macOS, change its instance or brain key, verify its connection, or remove its Codex connection.
---

# Configure Spongram

Resolve the plugin root as two directories above this skill directory. Scripts
ship in `<plugin-root>/scripts/`. Requires macOS, Python 3.10+ and a recent local
Codex executable (tested with 0.153.4 and 0.154.0).

For initial setup or a requested URL/key change, run:

```sh
python3 <plugin-root>/scripts/configure.py --gui
```

Explain that this opens macOS dialogs from Codex: instance URL, then reuse of
a matching saved key or a masked brain-key field. These are local system dialogs, not an embedded Codex form or a
browser. The user types directly into the dialog; no key goes through chat.
Setup checks the existing Codex profile and the co-installed Claude Spongram
profile for the same URL before requesting a key. Choosing Réutiliser for a Claude
key copies only that plugin key to a Codex-owned entry; Claude stays unchanged.

For an existing installation or repeated Keychain prompts, run
`python3 <plugin-root>/scripts/configure.py --migrate`. This keeps the endpoint and
key, verifies the server and refreshes the durable header helper. macOS may ask
once to import the legacy key; normal runtime never opens Keychain dialogs.
The bundled native helper is locally signed, installed at a stable path and
shared by the three Codex adapters. Never invoke it directly as an agent tool.
Rotating a Claude key no longer rotates its independent Codex copy.

Use the client's normal approval path if opening the dialogs, writing user config,
accessing Keychain, or testing HTTPS requires it. Never bypass a rejection.
Allow time for the user to complete the dialogs. Keep waiting on the same process;
do not launch duplicate dialogs. Cancellation is a normal outcome.

The script checks MCP initialize/tools/list without reading or writing memories,
stores the key in macOS Keychain, writes non-secret settings to
`~/.spongram/codex/`, and registers the `spongram` HTTP MCP server through Codex's
configuration API. It preserves unrelated config and refuses to replace an
unrelated existing server with that name. After success, start a new Codex session
and inspect `/mcp`. Do not report success if the script fails.

For read-only diagnosis use `python3 <plugin-root>/scripts/check_connection.py`.
For profile presence only use `configure.py --status`; it does not validate the key.
Never invoke `auth_headers.py`, dump Keychain contents, or ask for the brain key
as a tool/command argument. The header helper is exclusively for Codex's MCP runtime.
Never replace this flow with an environment variable or plaintext credential file.

If the user prefers their own terminal, `configure.py --terminal` asks for the URL
and a hidden key there. An agent-run shell does not provide a user-interactive
terminal; use the GUI mode from Codex.

On explicit request to disconnect/remove credentials, run `configure.py --remove`
before uninstalling the plugin. This removes its user-level MCP server, active
profile and active Codex-owned Keychain entry. A referenced Claude key is retained. Uninstalling the skill plugin alone does
not remove the separately registered MCP connection. Claude Code is unaffected.
