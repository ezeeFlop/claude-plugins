# Spongram for Codex

Use the same Spongram instance and brain as Claude Code. Both clients share
project/global memory; provenance is recorded with `client=codex` or
`client=claude-code`. Claude Code's integration continues to work independently.

## Install and configure on macOS

Requires Python 3.10+, macOS Keychain and a recent local Codex executable supporting
`http_headers_helper` and the config API (tested with CLI 0.154.0 and the app's
0.153.4 runtime). No additional Python package is required for setup or recall.

```sh
codex plugin marketplace add ezeeFlop/claude-plugins
codex plugin add spongram-codex@sponge-theory-codex
```

Start a new session, then ask **“Configure Spongram”** or invoke the
**spongram-setup** skill. Codex launches the bundled `scripts/configure.py --gui`:

1. A local macOS dialog asks for the instance URL. A saved Codex profile or an
   unambiguous installed Claude Spongram profile supplies the default.
2. Setup first checks for an existing Keychain credential for that URL. If found,
   choose **Réutiliser** or **Autre clé**. Otherwise enter the brain key in a masked
   local dialog, without the `Bearer ` prefix.
3. Setup verifies MCP `initialize` and `tools/list` without accessing memories,
   saves the non-secret settings and registers the HTTP MCP server in Codex.
4. Start a new Codex session and inspect `/mcp` for `spongram`.

These are macOS dialogs launched from Codex, not a form embedded in Codex. There
is no browser, secret pasted into chat, shell export, or manual config-file edit.
The client may require approval to run the setup; macOS may ask for Keychain access.
Installation does not silently execute setup. Cancel exits without saving new settings.

For a user-operated terminal, run `python3 <plugin-root>/scripts/configure.py --terminal`.
An agent-run shell is not an interactive user terminal; use `--gui` from Codex.
Linux and Windows secure setup are not implemented in this release.

## Reuse the Claude Code key

Setup reads only the selected Spongram credential from Claude's Keychain JSON
entry. It identifies the instance through Spongram's non-secret user settings or
the installed user-scope plugin manifest default. The normal Claude configuration
root and explicit `CLAUDE_CONFIG_DIR` / `CLAUDE_SECURESTORAGE_CONFIG_DIR` are supported.
If no matching profile/key is accessible, the masked input remains available.
Ambiguous profiles with different keys are not guessed.

When you select **Réutiliser**, Codex stores a reference to Claude's existing
Keychain entry. It does not copy, update or delete Claude's key, settings or plugin.
The header helper reads the current key at connection time, so a rotation in Claude
is picked up on a fresh connection (Codex can cache headers during a connection).
Removing Claude's credential will also disconnect a Codex connection referencing it;
rerun setup to supply an independent key if desired.

Claude stores multiple credentials in a single JSON Keychain item. The helper must
read that item in process to extract `pluginSecrets[spongram@sponge-theory].brain_key`;
other values are neither returned, written, nor logged. This compatibility reader
was checked against Claude Code 2.1.267 and is isolated in `claude_credentials.py`
and `connection.py`. An unknown future storage layout falls back to manual input.
It never reads Claude's plaintext `.credentials.json` or `codemap/connection.env`.

A newly entered key goes into service `ai.sponge-theory.spongram.codex`, under an
account derived from the instance URL. It is never saved in an environment variable,
command argument, plugin cache, repository, or Codex config file.

## Durable configuration and updates

The plugin packages skills and setup scripts. It deliberately has no bundled fixed
MCP URL. Setup registers the **user-level** HTTP MCP server `spongram` through the
Codex config API; this supports a custom URL without modifying the plugin cache.
The API preserves other settings and detects concurrent config changes. An existing
server named `spongram` that was not created by this setup is left untouched.

- `~/.spongram/codex/connection.json`: URL and non-secret credential reference.
- `~/.spongram/codex/runtime/`: private copies of the Keychain reader scripts.
- Codex `config.toml`: URL, `X-Spongram-Client: codex`, and a header-helper command.
- macOS Keychain: the existing Claude entry or the newly entered Codex key.

Runtime/profile files have mode 600, new private directories 700. Keychain is
accessed via Security.framework; the secret is not passed to a subprocess in argv.
Only the MCP runtime invokes `auth_headers.py`: its stdout is the authentication
header and must never be displayed by the agent. Use `check_connection.py` instead.

After a plugin update, run **Configure Spongram** again and choose **Réutiliser**
to refresh the durable helper scripts. No key re-entry is required. Version 0.5.0
users can stop supplying `SPONGRAM_BRAIN_KEY` after successful setup; this version
does not use it. Updating from 0.5.0 removes its bundled MCP connection on a new
session, avoiding duplicate connections.

```sh
codex plugin marketplace upgrade sponge-theory-codex
codex plugin add spongram-codex@sponge-theory-codex
```

## Diagnose or disconnect

```sh
python3 <plugin-root>/scripts/configure.py --status
python3 <plugin-root>/scripts/check_connection.py
```

Status only checks for a saved profile. The connection check authenticates and
lists tools, but does not read/write memories. It refuses HTTP redirects so the
brain key cannot be forwarded to a different endpoint by the setup probe.

Before uninstalling, ask Codex to disconnect Spongram, or run:

```sh
python3 <plugin-root>/scripts/configure.py --remove
```

This removes the user-level MCP registration, profile and active **Codex-owned**
key. It never deletes a referenced Claude key. Because the connection is registered
separately, uninstalling the plugin alone does not disconnect MCP. Private runtime
scripts contain no secrets and can remain for a later reinstall. Previous keys for
other instance URLs are retained in Keychain; remove them explicitly there when
no longer needed.

## Memory and code map

The common policy is `shared/spongram/memory.md`. Project identity retains the
legacy working-directory basename. Use the same `SPONGRAM_PROJECT` override in
both clients if needed to disambiguate repository names (this is not a secret).

Map queries use MCP without an extractor installation. Explicit map uploads require
Python 3.10+ with `graphifyy==0.8.35` installed in a dedicated environment:

```sh
python3 <plugin-root>/scripts/codemap.py build /path/to/repo
python3 <plugin-root>/scripts/codemap.py update /path/to/repo
```

Uploads read the same Keychain reference, run the shared extractor in process,
and store only map state in `.git/spongram-codemap-codex.json`. Map identity matches
Claude. No Git hook or dependency is installed automatically.

Memory reads send content to Codex and its model provider. Authorized writes and
map uploads send content to the configured Spongram server. This adapter has no
automatic transcript capture, session hooks or edits to AGENTS.md. Claude's existing
hooks and their privacy implications remain documented in the Claude README.

## Validation

`python3 scripts/check_spongram_release.py` checks both adapters. Unit/integration
tests cover mocked HTTP JSON/SSE, Keychain reuse/rotation isolation, setup failures,
secret-free files and real isolated Codex config API writes. Manual smoke scripts
exercise a temporary synthetic Keychain credential and auto-closing macOS dialogs.
Live authenticated connectivity and packaging results are recorded in the release
verification file; automated tests do not prove live memory recall.

- [OpenAI MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Claude plugin user configuration](https://code.claude.com/docs/en/plugins-reference#user-configuration)
