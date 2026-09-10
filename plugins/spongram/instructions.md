## Claude Code adapter

Use `client=claude-code`. Read the project context injected by SessionStart.
If missing, run `python3 <plugin-root>/lib/project_context.py --client claude-code
--cwd <session-working-directory>` and use its tags.
Connection uses the existing Claude `userConfig` (`instance_url`, `brain_key`).
The SessionStart, Stop, PostToolUse, PreCompact and SessionEnd hooks remain
Claude-specific; do not run them in Codex.

SessionStart installs the existing git post-commit map refresh and seeds missing
maps. `SPONGRAM_CODEMAP_DISABLE=1` disables setup; see README for existing hooks.
The `/spongram:recall`, `/spongram:brain-stats`, `/spongram:brain-graph` and
`/spongram:persona` commands remain available. Persona tone must respect project
and client instructions. See README for automatic capture and its off switch.
