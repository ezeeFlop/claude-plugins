# Codex Keychain fix — 2026-10-01

Versions: Spongram Codex 0.5.2, Rayonne Codex 0.7.1, SPT Models Codex 1.13.1.

## Scope

The three Codex adapters previously saved live references to Claude's shared
`Claude Code-credentials` item. Different Python executables could repeatedly
request access, even after an Always Allow action. Rayonne also supported this
reference even when a particular user had configured a dedicated key.

Setup now imports the selected plugin key into an independent encrypted item:
`ai.sponge-theory.<plugin>.codex.v2`. The account remains the normalized endpoint
hash. No Claude item, ACL, config, hook, manifest or plugin is modified.
NeoKanban, NeoRAG, AudiGEO, Oriflux and SPT-AI are Claude adapters in this
marketplace and do not contain this Codex Python reader. They are not republished.

## Runtime and migration

All three Codex adapters share identical bytes of a universal macOS native helper
(arm64 and x86_64), locally ad-hoc signed with identifier
`ai.sponge-theory.codex-keychain.v1`. This is not a Developer ID signature.
Setup installs it once at
`~/.sponge-theory/codex-keychain/v1/spt-codex-keychain`, outside plugin caches and
Python environments. Runtime verifies the expected digest and disables Keychain
interaction. Missing/locked/inaccessible credentials cause an actionable error;
they never trigger automatic migration, Claude fallback or a dialog retry loop.

The helper only accepts the three Codex-owned v2 services. It cannot query or
modify Claude's item. Keys travel through private stdin/stdout pipes, never argv,
plaintext credential files or diagnostics. This protects against accidental
exposure; it is not an authorization boundary against arbitrary code already
running as the same user that can invoke the helper.

After upgrading the marketplace and reinstalling the relevant Codex plugins, run
their `scripts/configure.py --migrate` from the installed copy. Use Python for
Spongram and `uv run --locked` for Rayonne/SPT Models. Setup verifies the remote
endpoint before committing the new profile; Spongram refreshes its durable
header helper and preserves MCP tool policies. Rayonne preserves read-only mode.
The OS can ask for access to a legacy item during this explicit import. Start a
new Codex thread afterward. Existing processes may retain their old configuration.

Old entries are retained; Claude keeps working. A later rotation in Claude no
longer updates Codex: rerun interactive setup to provide the new key. If access
to the old item is denied, setup exits without replacing the active profile.

## Maintenance

The native source and canonical Python bridge live in `shared/codex-keychain`.
`scripts/build_codex_keychain.py` vendors them into the three standalone plugins.
Use `--check` for releases. Do not rebuild/re-sign the native helper on ordinary
plugin updates: its bytes are its ad-hoc identity. A future native change requires
a versioned path/service and explicit migration. The build refuses to overwrite
an existing native binary. Keep the current macOS login-keychain API while
supporting existing items; it is deprecated by Apple and will need revisiting if
future macOS removes support.

Rayonne still uses `rayonne-mcp==0.7.0`; no PyPI/server deployment is needed.
SPT Models vendors the already released Claude bundle's 1.13.0 server verbatim.
The Codex manifest patch is independent of those server versions.

## Release verification

Run adapter tests, `scripts/build_spongram.py --check`, native parity checks,
the official Codex plugin validator, fresh isolated Codex installations, the
synthetic native Keychain smoke, and `scripts/smoke_spongram_mcp.py`.
The synthetic Keychain smoke creates/reads/rotates/deletes one temporary key,
including eight separate noninteractive native processes. It never uses real
credentials. Live checks use only MCP discovery, catalogue and overview reads;
they perform no generation, publishing or memory writes.

Before pushing, assert the diff under `.claude-plugin`, `shared/spongram`, and
every `plugins/<name>` without the `-codex` suffix is empty. Commit and push the
marketplace and synchronize the Rayonne source adapter/build packaging. Confirm
the published versions and helper hashes from a fresh fetch before updating the
user's installed plugins. Remove replaced preview/personal Codex copies only
after installing the public replacements; keep all profiles and Claude plugins.

### Verified for this publication

- 50 marketplace tests passed; 11 Rayonne source adapter tests passed.
- All three official Codex manifest validations passed.
- Fresh isolated Codex installation of all three release versions passed;
  universal native signatures verified after cache installation.
- Native synthetic Keychain create/read/rotate/delete and eight new-process
  noninteractive reads passed on macOS.
- Actual HTTP MCP discovery passed in both local Codex executables.
- The user's three profiles were migrated successfully. Live Spongram MCP
  initialize/tools/list, SPT Models discovery + 16 tools/catalogue, and Rayonne
  discovery + 82 tools/overview succeeded. No GPU inference or publishing ran.
- Claude marketplace, all eight Claude plugin trees and shared Spongram core
  have no changes in this release.
