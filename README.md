# Sponge Theory — Claude Code plugins

Marketplace of [Claude Code](https://docs.claude.com/en/docs/claude-code)
plugins published by [Sponge Theory](https://audigeo.ai).

## Install

```
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install audigeo@sponge-theory
```

## Available plugins

| Plugin | Description |
|---|---|
| **audigeo** | GEO audits, AI-platform monitoring, hallucination detection, and content generation for [AudiGEO.ai](https://audigeo.ai). Requires plan Pro or Agency. Set `AUDIGEO_API_KEY` (an `agk_…` key from Settings → API Keys) in your environment. Needs [`uv`](https://docs.astral.sh/uv/) installed — the plugin runs its MCP server via `uvx audigeo-mcp`. |

## Layout

```
.claude-plugin/marketplace.json   # marketplace manifest
plugins/<name>/                    # each plugin (self-contained)
```
