## Codex adapter

Use `client=codex`. At the start of a Spongram task, run
`python3 <plugin-root>/lib/project_context.py --client codex --cwd <session-working-directory>`.
Use the same session working directory and any `SPONGRAM_PROJECT` override as
Claude Code. Read the shared memory rules below before tool calls.

For first-time setup or credential changes, use the `spongram-setup` skill.
The setup registers a user-level HTTP MCP server named `spongram`, using a
private Keychain header helper. Start a new session after setup. Never run
`auth_headers.py` as an agent tool: its stdout contains the Bearer credential.
Use `scripts/check_connection.py` for diagnostics; it only reports success/failure.
Do not ask for a key in chat or inspect credential values. The setup/helper alone
may read the selected Spongram credential from Claude's Keychain store.
Respect AGENTS.md, Codex instructions, sandbox and tool approvals.

This adapter has no automatic hooks or transcript capture. For a task worth
remembering, write a concise durable summary through `add_memory` when authorized.
Recall and statistics use MCP tools; the Claude slash commands are not installed.

For an authorized map upload, run `python3 <plugin-root>/scripts/codemap.py build
<repository-root>` (or `update`). It uses the shared extractor and reads the key
from the macOS Keychain without exposing it to the agent. Install graphifyy==0.8.35 in a dedicated
Python >=3.10 environment first; it is not installed automatically. Querying an
existing map over MCP needs no local extractor. No git hook is installed by Codex.
