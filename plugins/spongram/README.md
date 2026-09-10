# spongram — Claude Code plugin

> **Spongram by Sponge Theory** — mémoire partagée entre clients.

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
  git post-commit code-map refresh for the current repo;
- **Memory-capture nudge** — a throttled reminder fired at the end of a turn, and
  right after a `git commit`, when nothing durable has been written for a while.
  Advisory only: it never forces an extra turn, and it makes no network call.
  Disable with `SPONGRAM_NUDGE_DISABLED=1`; tune with `SPONGRAM_NUDGE_GAP` /
  `SPONGRAM_NUDGE_COOLDOWN` (Stop) and `SPONGRAM_NUDGE_COMMIT_GAP` /
  `SPONGRAM_NUDGE_COMMIT_COOLDOWN` (commit);
- **Out-of-band capture** — on context compaction and at session end, a bounded
  tail of the transcript is sent to your brain, which distils the durable facts
  and stores them. Those two moments cannot prompt the assistant at all, so the
  capture does not rely on it: compaction is exactly when context is discarded.
  Runs detached — it never delays a compaction or a session exit — and requires
  `SPONGRAM_DISTILL_ENABLED` on your instance. Disable client-side with
  `SPONGRAM_CAPTURE_DISABLED=1`. Episodes it writes are tagged `capture=auto`.

## Setup

When you enable the plugin, Claude Code prompts you (native configuration form)
for two values:

| Field | Notes |
|---|---|
| **Spongram instance URL** | e.g. `https://spongram.sponge-theory.dev` (or your self-host), without `/mcp`. Default provided. |
| **Brain key (`spt_brain_…`)** | Shown once in the Spongram admin at brain creation. Marked sensitive in Claude configuration. Code-map setup also writes it in plaintext to `~/.spongram/codemap/connection.env` (mode 600) for the Git hook. |

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
Code's native `userConfig` (marked `sensitive`; storage depends on the client).
The existing code-map bootstrap persists a plaintext copy in
`~/.spongram/codemap/connection.env` with permissions 600 so Git can authenticate
outside Claude Code. This is not keychain-only storage. Keep this file private;
rotation in Claude refreshes it on the next SessionStart. Disabling setup does
not remove an existing file or installed Git hook; use
`bash <plugin-root>/hooks/uninstall-codemap-hook.sh` in each repo to remove the hook,
and remove the connection file separately if it is no longer needed.

Retrieved memories are transmitted to Claude and its model provider. Automatic
PreCompact/SessionEnd capture sends up to 300 recent user/assistant text turns
(each truncated to 4,000 characters, within a 1.5 MB input tail by default) to
`/v1/memory/distill`. It is not guaranteed to redact secrets. Set
`SPONGRAM_CAPTURE_DISABLED=1` before launching Claude to disable it. Existing
capture behavior is preserved. Codex has no automatic transcript capture.

## Personas

Une **persona** est une identité que Claude adopte à la demande : un rôle, une
voix (ton, tutoiement, langue), des règles, des compétences au standard
[Agent Skills](https://agentskills.io) (`SKILL.md`) et une mémoire propre qui
la suit d'un projet à l'autre et de Claude Code à Claude Desktop.

- `/spongram:persona` — liste vos personas ; `/spongram:persona <slug>` en active une.
- Création et édition sur `https://<votre-instance>/v1/personas` (clé `spt_brain_…`).
- **Claude Code n'est jamais dégradé** : par défaut il n'hérite que du ton et de
  la langue, précédés de la règle que les conventions du projet et les
  instructions de développement priment sur la persona. Aucun output style,
  aucune modification de `CLAUDE.md`, des permissions ou de la liste d'outils.

## Support

- Documentation: <https://spongram.sponge-theory.dev>
- Contact: support@sponge-theory.io

## Shared core and Codex

This remains the Claude Code entry at `plugins/spongram`; its manifest, MCP
userConfig and hook events retain their existing interfaces. The Codex adapter
is `plugins/spongram-codex`. Both are built from `shared/spongram` with
`python3 scripts/build_spongram.py`. Use the same brain in both clients.
Set the same `SPONGRAM_PROJECT` override in both environments when needed; default
slugs preserve the historical session-directory basename. Client tags identify
provenance and never partition recall.
