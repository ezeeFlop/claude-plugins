# Spongram for Codex

This adapter connects Codex to the same HTTP MCP brain as Claude Code. Use the
same instance and brain key in both clients. Provenance tags are `client=codex`
and `client=claude-code`; project/global recall includes both.

## Setup

Requires a Codex version supporting `.codex-plugin/plugin.json` and HTTP MCP
configuration (`bearer_token_env_var`). The CLI syntax was checked with 0.154.0.
No plugin or user configuration is installed by the build script.

1. Select the instance in this checkout, before installing. The default is
   `https://spongram.sponge-theory.dev`:

   ```bash
   python3 plugins/spongram-codex/scripts/configure.py --instance-url https://your-instance.example
   ```

2. Provide `SPONGRAM_BRAIN_KEY` through the environment of the Codex process
   (for example, injected by your secret manager). The value is the existing
   brain key, without the `Bearer ` prefix. Never put it in this repository,
   `.mcp.json`, `config.toml`, a command argument or shell history. A GUI-launched
   Codex process does not automatically inherit a terminal's environment; supply
   it through the launcher/secret-manager integration used by that installation.
   This adapter does not manage a keychain or copy Claude credentials.

3. To install the local repo marketplace, from this repository's root:

   ```bash
   codex plugin marketplace add .
   codex plugin add spongram-codex@sponge-theory-codex
   ```

   Then start a new Codex session and invoke the Spongram skill. Only the Codex
   adapter is in this marketplace. Claude continues to use `.claude-plugin/marketplace.json`.
   A cached install uses a copy: changing this checkout requires updating the
   installed plugin before the new endpoint or skills take effect.

4. Optional read-only connectivity check, using the same process environment:

   ```bash
   python3 plugins/spongram-codex/scripts/check_connection.py
   ```

   This performs `initialize`, `notifications/initialized`, and `tools/list`;
   it does not read or write memories. It does not replace a test inside Codex.
   In Codex, inspect `/mcp`, invoke `get_status`, then verify a project-scoped
   recall. For an explicitly authorized disposable test, write a fact with
   `project=<test-project> client=codex`, recall it in Claude, then do the reverse.

### Standalone MCP fallback

For an installation that does not support plugins, print a secret-free TOML
stanza to merge into your Codex configuration:

```bash
python3 plugins/spongram-codex/scripts/configure.py --instance-url https://your-instance.example --print-toml
```

Install `skills/spongram` through your normal Codex skill workflow, retaining its
relative `lib` and `scripts` dependencies, or refer explicitly to this checkout's
SKILL.md. MCP configuration alone exposes tools but does not install instructions.
Use either bundled MCP or standalone MCP to avoid duplicate connections.

## Memory and code map

`shared/spongram/memory.md` defines the common policy. Project identity uses the
legacy session-directory basename. Set the same `SPONGRAM_PROJECT` slug in both
clients for ambiguous repository names. Use the same working directory across
clients; subdirectories historically have distinct slugs.

Query code maps through MCP without local dependencies. Explicit uploads require
Python >=3.10 and `graphifyy==0.8.35` in a dedicated environment:

```bash
python3 plugins/spongram-codex/scripts/codemap.py build /path/to/repo
python3 plugins/spongram-codex/scripts/codemap.py update /path/to/repo
```

These commands upload structural code metadata to the instance selected above.
They read the brain key from the environment, invoke the shared extractor in
process and write only a manifest to `.git/spongram-codemap-codex.json` (worktrees
use their own Git directory). Map identity remains the repository basename,
matching Claude. No hook, venv or dependency is installed automatically.

## Privacy and feature boundaries

Memory reads send stored content to Codex and its model provider. Writes send
selected content to your Spongram instance. This adapter never captures full
transcripts, installs Git hooks or modifies AGENTS.md. Use concise, authorized
memory summaries. Claude's existing automatic capture and plaintext code-map
connection file are documented in its README; this adapter never reads that file.

Claude-specific slash commands, SessionStart context injection, Stop nudges,
PreCompact/SessionEnd capture and automatic post-commit bootstrap are not
installed in Codex. The common MCP tools remain available for explicit use.

## Verification and sources

Build/check: `python3 scripts/build_spongram.py --check`.
Tests: `python3 -m unittest discover -s tests -p 'test_spongram*.py'`.
Tests cover artifacts, project identity, Claude hook output and mocked MCP JSON/SSE
handshakes. A live authenticated Codex/Spongram connection is still to be tested.

- [Official OpenAI MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Official OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins)
