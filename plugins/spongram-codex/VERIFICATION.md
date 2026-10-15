# Claude 0.6.0 / Codex 0.6.0 — 2026-10-16

Shared-core release for Spongram server 1.17.0+. The project slug used by the
memory tags is now resolved from `SPONGRAM_PROJECT`, then the nearest
`.spongram.json` (`{"project": "<slug>"}`, normalized), then the name of the
main git repository (sub-folders and linked worktrees resolve to the main
checkout), then the folder name. The shared rules document the server-side
project aliases (`list_project_aliases`, `set_project_alias`,
`remove_project_alias`; read time only, never rewriting episodes). Both adapters
change together: `lib/project_context.py`, `memory.md`, SKILL, README and
instructions text, manifests 0.6.0. Keychain, dialog, header-helper and hook
runtime files are unchanged since 0.5.2.

- `python3 scripts/check_spongram_release.py`: 50 unit tests pass, generated
  shared-core parity and matching adapter versions (Claude 0.6.0, Codex 0.6.0)
  OK, staged release files scanned for likely credentials: none. The slug tests
  cover a repository sub-folder, a linked worktree, the nearest `.spongram.json`
  (normalized), an invalid nearest file stopping the search, and the
  `SPONGRAM_PROJECT` override.
- The shared module is byte-identical (sha256) to the copies tested in the
  Spongram repository against real git fixtures (worktree, submodule, nested
  JSON, oversize file, BOM).
- Slug rule verified live, without any brain key, through the Claude adapter's
  SessionStart hook from real folders: a `.spongram.json` placed in a
  repository wins; a sub-folder of a repository without one resolves to the
  main repository name, not the launch folder.
- Isolated install proof: with a fresh `CLAUDE_CONFIG_DIR`, `claude plugin
  install spongram@sponge-theory` installs 0.6.0 and reports its two required
  connection settings as not yet set; with a fresh `HOME` and `CODEX_HOME`,
  Codex CLI 0.162.1 installs `spongram-codex@sponge-theory-codex` 0.6.0
  (`authPolicy: ON_INSTALL`). No real key configured.
- `claude plugin validate` passes for the adapter and for the marketplace.
- `python3 scripts/smoke_spongram_mcp.py` (loopback, synthetic auth): actual
  Codex HTTP MCP, header helper and tools discovery OK.
- Server side, outside both client runtimes: the alias tools the shared rules
  refer to were exercised against production Spongram 1.17.0 on a throwaway
  instance deleted afterwards (MCP initialize contract, tools/list, alias
  declaration, scoped searches, continuity, export). No user brain was written
  or read by the packaging checks.

Not re-run for this release: the native Keychain and dialog smokes (their files
are unchanged since 0.5.2) and cross-client recall inside both clients.

## Previous verification

# Codex 0.5.2 — 2026-10-01

Native Keychain migration, synthetic repeated-process reads, isolated plugin
installation, both actual Codex MCP runtimes and live MCP initialize/tools/list
passed. No memories were read/written by the connection checks. Claude remains
0.5.1 with identical files. See `CODEX_KEYCHAIN_RELEASE.md` in the marketplace
repository for full scope and maintenance of the stable native identity.

## Previous verification

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
