# SPT Models — Claude Code plugin

Inference and model-catalogue access for the [SPT Models](https://models.sponge-theory.dev)
GPU stack, directly inside Claude Code: chat, completion, embeddings, image /
video / audio / music generation, transcription, and rerank — over an
OpenAI-compatible API, with per-model prompting guides the agent reads before
each call.

## Install

**Via the Sponge Theory marketplace (recommended):**

```
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install spt-models@sponge-theory
```

The MCP server is a small Python (stdio) proxy vendored inside the plugin. Its
dependencies are resolved on first launch by [`uv`](https://docs.astral.sh/uv/) —
**you need `uv` on your PATH** (no PyPI package, no manual `pip install`):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`.mcp.json` launches it with `uv run --directory ${CLAUDE_PLUGIN_ROOT} server/main.py`.

## Configure your key

When you enable the plugin, **Claude Code prompts you with a form**: your SPT
Gateway URL (defaults to `https://models.sponge-theory.dev`) and your SPT API
key (masked, stored in your system keychain — never written to a file). Create a
key in the SPT admin UI → **Keys** page. Optionally provide an admin token to
unlock the ops-only `load_model` / `unload_model` / `refresh_prompting_guide`
tools.

The form feeds these environment variables into the MCP server:

| Env var | Default | Purpose |
|---|---|---|
| `SPT_BASE_URL` | `https://models.sponge-theory.dev` | Your gateway base URL (no trailing path). |
| `SPT_API_KEY` | — (required) | Bearer token for `/v1/*` inference endpoints. |
| `SPT_ADMIN_TOKEN` | — (optional) | Enables `load_model` / `unload_model` / `refresh_prompting_guide`. |
| `SPT_REQUEST_TIMEOUT` | `300` | HTTP timeout (seconds); raise for large diffusion models. |
| `SPT_VERIFY_TLS` | `true` | Set `false` only for self-signed certs. |

*If the form doesn't appear (older Claude Code) or to change values later:* run
`/plugin configure spt-models@sponge-theory`, or set the same `SPT_*` variables
in the `env` block of `~/.claude/settings.json` or in your shell before
launching Claude Code. The server reads them from the environment either way.

Verify with `/mcp` — the `spt-models` server should show **connected**.

## Workflow

The bundled skill teaches the agent the right order:

1. **Discover** — `list_models(type=…)` to see what's in the catalogue.
2. **Read the prompting guide** — `get_model_info(slug)` for `recommended_params`
   (steps, guidance, width/height, system prompt, format).
3. **Infer** — call the matching tool (`chat`, `generate_image`, `tts`, …).
   The platform **auto-loads** the model on first use and auto-evicts the
   least-recently-used one under VRAM pressure. **Never call `load_model`
   first** — it is an ops-only tool.

## What's included

- **MCP server**: 14 tools — `list_models`, `get_model_info`, `chat`,
  `complete`, `embed`, `generate_image`, `generate_video`, `generate_music`,
  `tts`, `transcribe`, `rerank`, plus admin-gated `load_model`, `unload_model`,
  `refresh_prompting_guide` — and 3 resources (`spt://models`,
  `spt://model/{slug}`, `spt://guide`).
- **Skill** `spt-models`: the discover → prompting-guide → infer workflow,
  loaded on demand so a plain "generate me an image" surfaces the catalogue and
  uses the right per-model prompting style.

## License

MIT.
