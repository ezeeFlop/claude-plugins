# Publish Spongram for Claude Code and Codex

This replaces the old Spongram recipe that copied only `mcp/claude_code_plugin`
from the server repository. The release source is now this repository:
`shared/spongram`, both adapter directories, and both marketplaces. Do not copy
an older Claude-only tree over these files or regenerate the Codex marketplace
from the Claude manifest.

Spongram is a static remote-HTTP MCP plugin. Publishing it means committing and
pushing this repository; no PyPI package or product/server deployment is involved.
The server's Codex persona adaptation is a separate server release.

## Prepare and validate

1. Fetch `origin`. Review changes to the other marketplace plugins and preserve
   them. Rebase the release commit onto the latest `origin/main` before pushing.
2. Update shared rules/helpers in `shared/spongram`; client instructions and
   scripts live in `plugins/spongram` and `plugins/spongram-codex` respectively.
3. Set the same release version in both `plugin.json` manifests and the Spongram
   entry of `.claude-plugin/marketplace.json`. Do not use a local Codex cachebuster
   for a public release. The Codex marketplace uses the adapter manifest version.
4. Run `python3 scripts/build_spongram.py`, review the changes, then stage only
   the release files:

   ```bash
   git add .claude-plugin/marketplace.json .agents/plugins/marketplace.json .gitignore README.md SPONGRAM_RELEASE.md plugins/spongram plugins/spongram-codex shared/spongram scripts/build_spongram.py scripts/check_spongram_release.py tests/test_spongram.py
   python3 scripts/check_spongram_release.py
   git diff --cached --check
   git diff --cached --stat
   ```

   The preflight checks generated parity, matching versions, unit tests, shell
   syntax and likely credentials in the actual staged files (without displaying
   matches). Review the full staged diff as well. Never stage credentials or local
   client caches. Run the official Codex plugin validator when available.

## Installation proof before publishing

Use a fresh temporary HOME, CODEX_HOME and CLAUDE_CONFIG_DIR. Keep these variables
scoped to each test command; do not alter the user's regular configuration.
Create the directories before invoking the CLIs.

- Codex: `codex plugin marketplace add <checkout>` then
  `codex plugin add spongram-codex@sponge-theory-codex --json`.
- Claude: `claude plugin marketplace add <checkout>` then
  `claude plugin install spongram@sponge-theory`.

Both should install version 0.5.0 for this release. Claude should report missing
required connection settings in the empty profile. Do not configure a real key
for this packaging test. No session hooks need to run.

An install proof is not a live MCP connection proof. When an authorized test
brain key is available through the process environment, run
`plugins/spongram-codex/scripts/check_connection.py` and verify recall inside both
clients. Record separately whether the live check ran; never report an untested
connection as working. Do not create or delete memories without authorization.

## Publish and verify

After the user authorizes publication, commit the reviewed staged files, fetch
again, rebase onto `origin/main`, rerun preflight on any changed release files and
push normally. Never force-push or overwrite another plugin's release.

```bash
git commit -m "feat(spongram): release shared Claude Code and Codex adapters 0.5.0"
git fetch origin
git rebase origin/main
git push origin HEAD:main
```

Verify that remote `main` contains the pushed SHA. Fetch the public raw manifests
and check both adapter versions, both marketplace entries, and the shared-core
files. If the remote has advanced concurrently, confirm the release commit remains
an ancestor instead of assuming its SHA must still be the tip.

Report the commit link, visible version, installation commands, and any untested
live connectivity. A separate GitHub Release or tag is not required by these
marketplaces.

## User installation and updates

Codex, first installation:

```bash
codex plugin marketplace add ezeeFlop/claude-plugins
codex plugin add spongram-codex@sponge-theory-codex
```

Codex, existing installation:

```bash
codex plugin marketplace upgrade sponge-theory-codex
codex plugin add spongram-codex@sponge-theory-codex
```

Provide `SPONGRAM_BRAIN_KEY` to the Codex process, using the same brain as Claude.
For a custom instance and GUI secret setup, follow the Codex adapter README.
Start a new session after installing/updating.

Claude, refresh the marketplace with
`claude plugin marketplace update sponge-theory`, then update Spongram from
`/plugin`. First-time users install `spongram@sponge-theory` and configure their
existing instance URL and brain key.
