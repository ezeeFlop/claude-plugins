# spongram — Claude Code plugin

> *"Le cerveau persistant qui ne quitte jamais vos GPUs."* — **Spongram by Sponge Theory**

Persistent, cross-session memory + knowledge graph + code-map for Claude Code,
backed by your **Spongram** brain. The plugin is 100% static and carries **no
secret**: it talks directly to your Spongram instance over authenticated
streamable HTTP (`type: http`). Your instance URL and brain key are entered once,
natively, when you enable the plugin.

## What it does

- **Continuous cross-session memory** — what you tell Claude is stored in a
  temporal knowledge graph (Graphiti);
- **Namespaced slash commands** — `/spongram:recall`, `/spongram:brain-stats`,
  `/spongram:brain-graph`;
- **`spongram` skill** — teaches Claude *when* to read/write memory (preferences,
  decisions, facts) and to tag every memory by project;
- **SessionStart hooks** — inject project continuity from message 1, and wire a
  git post-commit code-map refresh for the current repo.

## Setup

When you enable the plugin, Claude Code prompts you (native configuration form)
for two values:

| Field | Notes |
|---|---|
| **Spongram instance URL** | e.g. `https://spongram.sponge-theory.dev` (or your self-host), without `/mcp`. Default provided. |
| **Brain key (`spt_brain_…`)** | Shown once in the Spongram admin at brain creation. Stored masked in your system keychain — never in the plugin or a settings file in plaintext. |

That's it — the MCP server connects automatically with `Authorization: Bearer
<your key>`. Rotate the key any time from the Spongram admin and update it in the
plugin configuration.

### Manual fallback (any Claude Code version)

If your Claude Code build doesn't render the configuration form, add the server
by hand:

```bash
claude mcp add --transport http spongram https://spongram.sponge-theory.dev/mcp \
  --header "Authorization: Bearer spt_brain_…"
```

## Desktop

This public plugin targets **cloud / self-hosted** Spongram instances. Claude
Desktop users get their integration from the Spongram Desktop app itself (its
in-app Connect card), not from this plugin.

## Security

No secret ships in this plugin. Your `spt_brain_…` key is entered via Claude
Code's native `userConfig` (marked `sensitive`, stored in the system keychain)
and is sent only to your own Spongram instance over HTTPS.

## Support

- Documentation: <https://spongram.sponge-theory.dev>
- Contact: support@sponge-theory.io
