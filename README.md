# Sponge Theory — Claude Code plugins

Marketplace of [Claude Code](https://docs.claude.com/en/docs/claude-code)
plugins published by [Sponge Theory](https://sponge-theory.ai).

## Install

```
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install <plugin>@sponge-theory
```

Each plugin prompts for its configuration (API keys, instance URL) when
enabled — secrets are stored in your system keychain, never in files.

## Available plugins

| Plugin | Description |
|---|---|
| **spongram** | Persistent cross-session brain for Claude Code — temporal knowledge graph memory, code map, 3D cortex — backed by your [Spongram](https://spongram.sponge-theory.dev) instance (hosted or self-host). On enable, enter your instance URL and your `spt_brain_…` key (shown once in the Spongram admin). |
| **audigeo** | GEO audits, AI-platform monitoring, hallucination detection, and content generation for [AudiGEO.ai](https://audigeo.ai). Requires plan Pro or Agency. On enable, enter your `agk_…` API key (Settings → API Keys). Needs [`uv`](https://docs.astral.sh/uv/) installed — the plugin runs its MCP server via `uvx audigeo-mcp`. |
| **spt-models** | Inference + model catalogue for the [SPT Models](https://models.sponge-theory.dev) GPU stack — chat, image / video / audio / music generation, transcription, embeddings, rerank — over an OpenAI-compatible API. On enable, enter your gateway URL and SPT API key (admin UI → Keys). Needs [`uv`](https://docs.astral.sh/uv/) installed — the MCP server is vendored in the plugin and launched via `uv run`. |
| **neorag** | [SPT NeoRAG](https://rag.sponge-theory.dev) enterprise RAG in Claude Code — knowledge bases, document ingestion, semantic + knowledge-graph retrieval (140+ tools), plus `/neorag:kb-list` and `/neorag:query` commands. Works with cloud or self-hosted instances. On enable, enter your instance URL and a NeoRAG API key (created in the API Keys page, shown once). |
| **neokanban** | [NeoKanban](https://kanban.sponge-theory.dev) task, project and board management — plus audio transcription with speaker diarization — directly from Claude Code. On enable, enter your instance URL and an `nk_mcp_…` token (NeoKanban web UI → Settings → Integrations → MCP, shown once at creation). |

## Layout

```
.claude-plugin/marketplace.json   # marketplace manifest
plugins/<name>/                    # each plugin (self-contained)
```
