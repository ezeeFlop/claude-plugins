# Spongram 0.5.1 verification — 2026-09-10

- 21 unit/integration tests pass. Includes generated shared-core parity, Claude
  hooks, project provenance, setup cancellation/failure rollback, no keys in files
  or command arguments, reference-only Claude reuse, credential rotation and
  actual isolated Codex config API preservation/concurrency checks.
- Official Codex plugin and both skill validators pass.
- Native macOS Keychain smoke passes: create, read, rotate, fetch using the actual
  header helper, delete a unique synthetic credential. No production key modified.
- Native macOS dialog smoke passes: compilation of URL, hidden-key and reuse
  dialogs; an auto-closing synthetic hidden-input dialog was executed.
- Actual MCP startup passes in Codex CLI 0.154.0 and the desktop app's 0.153.4
  runtime: HTTP fixture receives the helper-provided Bearer and Codex provenance
  header; initialize and tools/list succeed. Profiles and server are temporary;
  no model turn is run.
- Live read-only initialize/tools/list succeeds against an existing Spongram
  instance using the co-installed Claude Keychain credential: 21 tools. No memory
  tool invoked; no credential copied or client configuration changed.
- Both 0.5.1 plugins install successfully in isolated Codex/Claude homes. Claude
  still requests its two required userConfig settings in a fresh profile.
- Relative to 0.5.0, the Claude adapter changes only its release version. Its
  settings, MCP config, hooks, commands and shared core are unchanged.

The full user-driven setup was not applied to the user's normal Codex profile.
The real HTTP checks and native UI/Keychain checks were performed separately.
Cross-client memory write/recall and production server deployment were not part
of this release. No claim of a Codex-embedded form: setup uses macOS dialogs.

## Reproduce

```sh
python3 scripts/check_spongram_release.py
python3 scripts/smoke_spongram_keychain.py
python3 scripts/smoke_spongram_dialogs.py
python3 scripts/smoke_spongram_mcp.py
```

The native smoke scripts require appropriate OS permissions and may request
Keychain access or briefly display a test dialog. The MCP smoke binds loopback.
