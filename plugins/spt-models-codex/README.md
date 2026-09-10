# SPT Models for Codex

Codex adapter for the SPT Models GPU stack. Ships the MCP bundle 1.10.0
(14 tools), model prompting guides, and secure macOS setup. The Claude Code
plugin is independent and unchanged.

## Install

Requires `uv` on PATH and Python >=3.10 (resolved by uv).

```sh
codex plugin marketplace add ezeeFlop/claude-plugins
codex plugin add spt-models-codex@sponge-theory-codex
```

If the marketplace was registered previously, refresh it first with
`codex plugin marketplace upgrade sponge-theory-codex`.
Start a new Codex thread, then ask: **Configure SPT Models**.
The setup skill opens a local URL/key dialog. A matching SPT Models credential
already configured in Claude Code can be reused without copying it into chat
or a config file. Otherwise enter the key in the masked dialog; it is saved
in the macOS Keychain under `ai.sponge-theory.spt-models.codex`.
Setup validates `/v1/models` over HTTPS before saving the active profile in
`~/.spt-models/codex/connection.json`. That file contains only the gateway URL
and credential reference. Claude credentials are read-only. No admin token is
imported. API keys and request content are sent to the configured SPT gateway.

The MCP server may report missing configuration immediately after installation;
run setup, then start a new thread to connect it.

## Verify

From the installed plugin root:

```sh
uv run scripts/check_connection.py
```

Checks the actual stdio handshake, 14 tool names and a catalogue call. It does
not run GPU inference, print keys or dump catalogue payloads. In a new Codex
thread, ask **List the models available on my SPT stack** to test host integration.

## Other platforms / environment configuration

Supply both `SPT_BASE_URL` and `SPT_API_KEY` through the environment inherited
by the Codex host. A complete environment pair overrides the macOS profile;
a partial pair is rejected to avoid sending a saved key to an unrelated URL.
`SPT_ADMIN_TOKEN` is optional, for explicitly requested model operations.
Do not put credentials in the public plugin or pass them as command arguments.

HTTP request timeout defaults to 3900 seconds; the bundled MCP tool timeout
is 4000 seconds. The startup timeout is 120 seconds for initial uv setup.
Large media are returned as base64, so client output limits can still matter;
long video/file delivery is not validated by the catalogue smoke test.

## Maintenance

To update the vendored server from an SPT Models checkout:

```sh
python3 scripts/sync_spt_models_codex.py /path/to/spt-models
```

This updates the server, pyproject, and Codex manifest version from mcp-bundle.
Then run `uv lock` in this plugin, the adapter tests, and the MCP smoke check.

```sh
uv run --directory plugins/spt-models-codex python /absolute/path/to/claude-plugins/tests/test_spt_models_codex.py
```

For that test command use an absolute path to the test file, because uv changes
the working directory. Tests use mocked credentials; no production key required.

Uninstall with `codex plugin remove spt-models-codex@sponge-theory-codex`.
Uninstalling the plugin retains the connection profile and Keychain entry so
reinstallation can reuse them. Delete those separately if desired; an imported
Claude credential always remains owned by Claude.
