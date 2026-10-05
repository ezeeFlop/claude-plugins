# SPT Models for Codex

Codex adapter for the SPT Models GPU stack. Ships the MCP bundle 1.14.1
(17 tools, with MCP annotations), model prompting guides, and secure macOS setup. The Claude Code
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
in the macOS Keychain under `ai.sponge-theory.spt-models.codex.v2`.
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

Checks the actual stdio handshake, 16 tool names and a catalogue call. It does
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

## Migration 1.13.1 and maintenance

From the installed plugin root, run `uv run --locked scripts/configure.py --migrate`.
The existing key is imported once into a Codex-owned entry, after verifying the
catalogue. Claude's item is never modified. Runtime never reads that item or
opens Keychain dialogs. A locked keychain causes an actionable failure; unlock
it and rerun migration. The native helper uses a stable path and identical,
locally ad-hoc signed bytes across Spongram, Rayonne and SPT Models; it is not
Developer ID signed. Claude key rotations must be applied to Codex separately.

This release vendors the already published `plugins/spt-models/server` 1.13.0
verbatim (including classification and music transcription). Keep server files
and `pyproject.toml` in parity when updating. Run the adapter regression tests,
`python3 scripts/build_codex_keychain.py --check`, and the MCP catalogue check.
Do not rebuild or re-sign the released native helper on ordinary plugin updates.

Uninstall with `codex plugin remove spt-models-codex@sponge-theory-codex`.
The connection profile and Keychain entry are retained for reinstallation.

## Approvals

Every tool declares MCP annotations: `list_models` and `get_model_info` are
read-only, inference tools are neither read-only nor destructive, and
`unload_model` / `refresh_prompting_guide` are destructive. In a session whose
approval policy is `never`, a tool that needs approval is refused outright
("MCP tool call requires approval, but approval policy is never"). To run the
whole catalogue without prompts, add to `~/.codex/config.toml`:

```toml
[plugins."spt-models-codex@sponge-theory-codex".mcp_servers.spt-models]
default_tools_approval_mode = "approve"
```

