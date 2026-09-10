# Verification — 2026-09-10

- Codex plugin schema validator: passed.
- Adapter unit tests: 10 passed (URL validation, credential isolation, rollback,
  profile permissions, environment pairing, Claude metadata discovery).
- Live MCP: initialization succeeded, all 14 tools discovered, `list_models`
  returned HTTP 200 against the configured SPT Models gateway.
- Installed through `codex plugin add` in the separate
  `sponge-theory-codex-preview` local marketplace.
- `codex mcp get spt-models --json` confirmed enabled state, a resolved installed
  cache working directory, startup timeout 120s and tool timeout 4000s.
- The live MCP check was also run from the installed cache copy.

The legacy Codex MCP format does not expand `${PLUGIN_ROOT}` inside arguments.
Use `cwd: "."`, which Codex resolves relative to the installed plugin, and
`uv run --locked scripts/launch.py`. Keep this when updating packaging.

Not validated: GPU inference, very large media response delivery, non-macOS
hosts, and tool pickup in a new interactive Codex thread. Configuration and
catalogue checks do not load a GPU model. A new thread is required after install.
