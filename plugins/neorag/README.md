# neorag — Claude Code plugin

**SPT NeoRAG by Sponge Theory** — enterprise Retrieval-Augmented Generation
(knowledge bases, document ingestion, semantic + hybrid + knowledge-graph
retrieval, structured extraction) directly inside Claude Code.

The plugin is 100% static and carries **no secret**: it talks directly to your
NeoRAG instance over authenticated streamable HTTP (`type: http`). Your instance
URL and API key are entered once, natively, when you enable the plugin.

## What it does

- Exposes your NeoRAG instance as MCP tools: manage knowledge bases, ingest
  documents (upload / web scrape), run RAG queries and raw retrieval, and explore
  the knowledge graph.
- **`neorag` skill** — teaches Claude how and when to use those tools (retrieve
  vs. generate, cite sources, confirm before destructive ops).
- **Slash commands** — `/neorag:kb-list`, `/neorag:query <question>`.

## Install (marketplace)

```bash
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install neorag@sponge-theory
```

When you enable the plugin, Claude Code prompts you (native configuration form)
for two values:

| Field | Notes |
|---|---|
| **NeoRAG instance URL** | e.g. `https://rag.sponge-theory.dev` (or your self-host), without `/mcp`. Default provided. |
| **NeoRAG API key** | Created in the **API Keys** section of your NeoRAG instance; shown once at creation. Stored masked in your system keychain — never in the plugin or a settings file in plaintext. |

The MCP server then connects automatically with `Authorization: Bearer <your key>`.

> If you already had this marketplace registered, refresh it first so the new
> plugin is visible: `/plugin marketplace update sponge-theory`.

### Manual fallback (any Claude Code version)

If your Claude Code build doesn't render the configuration form, add the server
by hand:

```bash
claude mcp add --transport http neorag https://rag.sponge-theory.dev/mcp \
  --header "Authorization: Bearer <your NeoRAG API key>"
```

You can also download a ready-made `.mcp.json` from the **Settings → MCP
Configuration** card in the NeoRAG web UI, or from the API key creation dialog.

## Claude Desktop

Claude Desktop users install the `neorag.mcpb` bundle from the NeoRAG web UI
(Settings → MCP Configuration → *Download neorag.mcpb*), not from this plugin.

## Security

No secret ships in this plugin. Your API key is entered via Claude Code's native
`userConfig` (marked `sensitive`, stored in the system keychain) and is sent only
to your own NeoRAG instance over HTTPS.

## Support

- Documentation: <https://rag.sponge-theory.dev>
- Contact: support@sponge-theory.io
