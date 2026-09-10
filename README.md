# Sponge Theory — Claude Code plugins

Marketplace of [Claude Code](https://docs.claude.com/en/docs/claude-code)
plugins published by [Sponge Theory](https://sponge-theory.ai).

## Install

```
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install <plugin>@sponge-theory
```

Claude plugins declare their connection settings (API keys, instance URL).
Secret storage depends on the client and plugin: see each plugin README.
Spongram’s Claude code-map hook keeps a private plaintext connection file;
the Codex adapter provides guided macOS setup with Keychain storage.

## Available plugins

| Plugin | Description |
|---|---|
| **spongram** | Persistent cross-session brain for Claude Code — temporal knowledge graph memory, code map, 3D cortex — backed by your [Spongram](https://spongram.sponge-theory.dev) instance (hosted or self-host). On enable, enter your instance URL and your `spt_brain_…` key (shown once in the Spongram admin). |
| **audigeo** | GEO audits, AI-platform monitoring, hallucination detection, and content generation for [AudiGEO.ai](https://audigeo.ai). Requires plan Pro or Agency. On enable, enter your `agk_…` API key (Settings → API Keys). Needs [`uv`](https://docs.astral.sh/uv/) installed — the plugin runs its MCP server via `uvx audigeo-mcp`. |
| **spt-models** | Inference + model catalogue for the [SPT Models](https://models.sponge-theory.dev) GPU stack — chat, image / video / audio / music generation, transcription (verbatim or intended, with word-level timings), embeddings, rerank — over an OpenAI-compatible API. On enable, enter your gateway URL and SPT API key (admin UI → Keys). Needs [`uv`](https://docs.astral.sh/uv/) installed — the MCP server is vendored in the plugin and launched via `uv run`. |
| **neorag** | [SPT NeoRAG](https://rag.sponge-theory.dev) enterprise RAG in Claude Code — knowledge bases, document ingestion, semantic + knowledge-graph retrieval (140+ tools), plus `/neorag:kb-list` and `/neorag:query` commands. Works with cloud or self-hosted instances. On enable, enter your instance URL and a NeoRAG API key (created in the API Keys page, shown once). |
| **neokanban** | [NeoKanban](https://kanban.sponge-theory.dev) task, project and board management — plus audio transcription with speaker diarization — directly from Claude Code. On enable, enter your instance URL and an `nk_mcp_…` token (NeoKanban web UI → Settings → Integrations → MCP, shown once at creation). |
| **spt-ai** | Manage the content of your [Sponge-Theory.ai](https://sponge-theory.ai) site from Claude Code — create/edit/translate/share blog posts, products, external-SaaS entries, tiers and digital products, upload media and update site config. Static remote-HTTP plugin (no PyPI). On enable, enter your API base URL (`https://apisaas.sponge-theory.ai`) and a service API key (`spt_…`, created in your site admin → Settings → API keys, shown once). |
| **oriflux** | [Oriflux](https://oriflux.sponge-theory.dev) cookieless web + product + API analytics in Claude Code — read-only traffic, sessions, geography and API health through Oriflux's typed metric registry, plus `/oriflux:projects` and `/oriflux:overview` commands. Static remote-HTTP plugin (no PyPI); works with cloud or self-hosted instances. On enable, enter your API base URL (`https://api.oriflux.sponge-theory.dev`) and a read-scoped `ofx_read_…` key (Oriflux dashboard, shown once). |

## Layout

```
.claude-plugin/marketplace.json   # marketplace manifest
plugins/<name>/                    # each plugin (self-contained)
```

## Spongram : Claude Code et Codex

Le plugin Claude Code conserve son chemin `plugins/spongram`. L'intégration
Codex est dans [`plugins/spongram-codex`](plugins/spongram-codex/README.md), avec
sa marketplace `.agents/plugins/marketplace.json`. Elles utilisent le cœur
`shared/spongram` : règles mémoire, contexte projet et extracteur de code-map.

Après une modification du cœur : `python3 scripts/build_spongram.py`, puis
`python3 scripts/build_spongram.py --check` et
`python3 -m unittest discover -s tests -p 'test_spongram*.py'`.
Les copies générées dans chaque plugin rendent les archives autonomes ; aucune
référence à un fichier situé hors du plugin n'est nécessaire à l'exécution.
L'extracteur partagé est une copie versionnée de `spongram_codemap` du dépôt
serveur ; mettre à jour cette copie puis régénérer les deux plugins ensemble.

Publication de Spongram : voir [SPONGRAM_RELEASE.md](SPONGRAM_RELEASE.md).
Le contrôle `python3 scripts/check_spongram_release.py` valide les deux adaptateurs
et vérifie les fichiers indexés avant publication ; il ne pousse rien lui-même.
