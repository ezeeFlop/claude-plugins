## Codex adapter

Use `client=codex`. At the start of a Spongram task, run
`python3 <plugin-root>/lib/project_context.py --client codex --cwd <session-working-directory>`.
Use the same session working directory and any `SPONGRAM_PROJECT` override as
Claude Code. Read the shared memory rules below before tool calls.

Connect via the bundled HTTP MCP server, with `SPONGRAM_BRAIN_KEY` in the Codex
process environment. See README to select an instance. Do not read Claude's
settings, keychain or `~/.spongram/codemap/connection.env` to obtain credentials.
Respect AGENTS.md, Codex instructions, sandbox and tool approvals.

This adapter has no automatic hooks or transcript capture. For a task worth
remembering, write a concise durable summary through `add_memory` when authorized.
Recall and statistics use MCP tools; the Claude slash commands are not installed.

For an authorized map upload, run `python3 <plugin-root>/scripts/codemap.py build
<repository-root>` (or `update`). It uses the shared extractor and reads the key
from the environment without persisting it. Install graphifyy==0.8.35 in a dedicated
Python >=3.10 environment first; it is not installed automatically. Querying an
existing map over MCP needs no local extractor. No git hook is installed by Codex.
