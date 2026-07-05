# AudiGEO Claude Code plugin

GEO audits, AI-platform monitoring, hallucination detection, and content
generation, accessible directly inside Claude Code.

## Install

**Via the Sponge Theory marketplace (recommended):**

```
/plugin marketplace add ezeeFlop/audigeo
/plugin install audigeo@sponge-theory
```

**Manually**, from the downloaded `audigeo-claude-code-<version>.tar.gz`
(https://audigeo.ai → Settings → Intégrations Claude):

```bash
mkdir -p ~/.claude/plugins
tar -xzf audigeo-claude-code-*.tar.gz -C ~/.claude/plugins/
```

Either way, the bundled `.mcp.json` launches the MCP server via
`uvx audigeo-mcp` — **you need `uv` installed**
(https://docs.astral.sh/uv/getting-started/installation/). `uvx` fetches the
published `audigeo-mcp` package from PyPI and caches an isolated environment
on first launch — no manual `pip install`.

## Configure

Set your API key (generate at https://audigeo.ai → Settings → API Keys,
requires plan Pro or Agency) in your shell environment before starting Claude
Code:

```bash
export AUDIGEO_API_KEY=agk_...
```

Restart Claude Code. Try `/audigeo-status` to verify.

## What's included

- **MCP server**: 26 tools, 3 resources, 3 prompt templates (see
  https://audigeo.ai/docs/mcp for the complete list).
- **7 skills**: contextual guidance the agent loads on demand (audit,
  monitoring, hallucination triage, brand profile, content generation, bot
  analytics, product overview).
- **4 slash commands**: `/audigeo-status`, `/audigeo-audit`,
  `/audigeo-monitor`, `/audigeo-content`.
- **Subagent `audigeo-strategist`**: an in-house GEO expert agent with the
  full toolkit at its disposal.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `AUDIGEO_API_KEY` | — (required) | Your AudiGEO API key (`agk_...`). |
| `AUDIGEO_API_URL` | `https://audigeo.ai/api/v1` | Override for staging/self-hosted — export it in your shell if you need a non-default value. |
| `AUDIGEO_READ_ONLY` | `false` | When `true`, disables every write tool. |
| `AUDIGEO_DEFAULT_SITE_ID` | — | UUID used when an agent omits `site_id`. |

## License

Sponge Theory proprietary. Distribution restricted to AudiGEO subscribers.
