# neokanban — Claude Code plugin

> **NeoKanban by Sponge Theory** — your task board, in Claude Code.

Manage tasks, projects and boards, and run audio transcription with speaker
diarization, directly from Claude Code. The plugin is 100% static and carries
**no secret**: it talks to your NeoKanban instance over authenticated
streamable HTTP (`type: http`). Your instance URL and MCP token are entered
once, natively, when you enable the plugin.

## What it does

Exposes the 17 NeoKanban MCP tools:

- **Tasks** — `create_task`, `get_task`, `list_tasks`, `update_task`, `delete_task`
- **Projects** — `create_project`, `get_project`, `list_projects`, `update_project`, `delete_project`
- **Boards** — `create_board`, `get_board`, `list_boards`, `update_board`, `delete_board`
- **Transcription** — `transcribe_audio` (async job, WhisperX + diarization on the
  spt-models cluster) and `get_transcription_status` (poll for the transcript)

## Install

```bash
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install neokanban@sponge-theory
```

When you enable the plugin, Claude Code prompts you (native configuration form)
for two values:

| Field | Notes |
|---|---|
| **NeoKanban API URL** | e.g. `https://kanban.sponge-theory.dev` (or your self-host), without a path. Default provided. |
| **MCP token (`nk_mcp_…`)** | Generate in the NeoKanban web UI under **Settings → Integrations → MCP**. Shown once at creation. Stored masked in your system keychain — never in the plugin or a settings file in plaintext. |

That's it — the MCP server connects automatically with `Authorization: Bearer
<your token>`. Rotate the token any time from the web UI and update it in the
plugin configuration.

If you installed from the CLI rather than the interactive `/plugin` menu and the
configuration form did not appear, run `/plugin configure neokanban@sponge-theory`.

### Generating the token

1. Sign in to your NeoKanban instance (e.g. `https://kanban.sponge-theory.dev`).
2. Go to **Settings → Integrations → MCP**.
3. Create a new MCP token and copy it (it starts with `nk_mcp_` and is shown only once).
4. Paste it into the plugin's **MCP token** field.

### Manual fallback (any Claude Code version)

If your Claude Code build does not render the configuration form, add the server
by hand:

```bash
claude mcp add --transport http neokanban https://kanban.sponge-theory.dev/api/v1/mcp/messages \
  --header "Authorization: Bearer nk_mcp_…"
```

### Stale marketplace cache

If you already had the `sponge-theory` marketplace registered before this plugin
was published and installation reports *"Plugin neokanban not found in
marketplace"*, refresh the local clone first:

```bash
/plugin marketplace update sponge-theory
```

## Desktop

This public plugin targets **cloud / self-hosted** NeoKanban instances. Claude
Desktop users install the `.mcpb` bundle from NeoKanban instead (Settings →
Integrations → MCP → download the Claude Desktop extension).

## Security

No secret ships in this plugin. Your `nk_mcp_…` token is entered via Claude
Code's native `userConfig` (marked `sensitive`, stored in the system keychain)
and is sent only to your own NeoKanban instance over HTTPS.

## Support

- Documentation: <https://kanban.sponge-theory.dev>
- Sponge Theory: <https://sponge-theory.io>
