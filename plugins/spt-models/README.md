# SPT Models — Claude Code plugin

Inference and model-catalogue access for the [SPT Models](https://models.sponge-theory.dev)
GPU stack, directly inside Claude Code: chat, completion, embeddings, image /
video / audio / music generation, speech and music transcription, vocal /
accompaniment separation, rerank and typed document classification — over an
OpenAI-compatible API, with per-model prompting guides the agent reads before
each call.

## Install

Add the public Sponge Theory marketplace once, then install the plugin from it.
In a Claude Code session:

```
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install spt-models@sponge-theory
```

`/plugin install` opens the plugin's details: choose a scope (**Install for you**
makes it available in every project on this machine), then fill in the form
described below. If Claude Code prints `Run /reload-plugins to activate`, run it.

From a shell instead (the plugin loads at the next start of Claude Code; the
configuration form appears then):

```bash
claude plugin marketplace add ezeeFlop/claude-plugins
claude plugin install spt-models@sponge-theory
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

*To change values later:* run `/plugin`, open **Installed** → `spt-models`, then
**Configure options**. You can also set the same `SPT_*` variables in the `env`
block of `~/.claude/settings.json` or in your shell before launching Claude Code;
the server reads them from the environment either way.

Verify with `/mcp` — the `spt-models` server should show **connected**.

## Update

Third-party marketplaces do not auto-update by default. Either turn auto-update
on once (`/plugin` → **Marketplaces** → `sponge-theory` → **Enable auto-update**),
or update by hand:

```bash
claude plugin marketplace update sponge-theory
claude plugin update spt-models@sponge-theory
```

then `/reload-plugins` in any open session.

The MCP server itself does not wait for that: at each start it asks your
gateway which server version it ships and, when that is newer than the
installed one, downloads it once (checksum-verified, cached in
`~/Library/Caches/spt-models-mcp` on macOS) and runs it. A gateway upgrade thus
reaches the plugin at the next session, without reinstalling or retyping the
key; if the gateway is unreachable, the installed version runs. Set
`SPT_AUTO_UPDATE=false` in the environment to always run the installed version.

## Uninstall

```bash
claude plugin uninstall spt-models@sponge-theory
```

Do not install this plugin next to the pre-configured `.plugin` bundle that the
SPT admin UI can generate for a key: both declare the same `spt-models` MCP server.

## Workflow

The bundled skill teaches the agent the right order:

1. **Discover** — `list_models(type=…)` to see what's in the catalogue.
2. **Read the prompting guide** — `get_model_info(slug)` for `recommended_params`
   (steps, guidance, width/height, system prompt, format).
3. **Infer** — call the matching tool (`chat`, `generate_image`, `tts`, …).
   The platform **auto-loads** the model on first use and auto-evicts the
   least-recently-used one under VRAM pressure. **Never call `load_model`
   first** — it is an ops-only tool.

## Transcription — verbatim or intended

`transcribe` takes two optional parameters beyond `language` (plugin 1.6.0+):

| Parameter | Values | Effect |
|---|---|---|
| `mode` | `verbatim` \| `intended` | `verbatim` keeps every filler, stutter, repetition and vocal sound; `intended` returns the clean readable sentence. Only `crisperwhisper-2.0-large` honours it today — the other STT backends ignore it silently. Omit it to keep the model's own default. |
| `timestamp_granularities` | `["word"]` and/or `["segment"]` | Mirrors the OpenAI field. `crisperwhisper-2.0-large` returns word timings by default and they cost real time (4.0 s vs 1.8 s on a 15 s clip) — pass `["segment"]` to opt out. Timings arrive nested as `segments[].words`, not as a top-level `words` array. |

Ask for `verbatim` when the disfluencies *are* the signal — medical or legal
transcripts, speech therapy, interview analysis, dubbing — and `intended` when
you want prose. Both come from the same request, so you can run the two and
diff them.

## What's included

- **MCP server**: 17 tools — `list_models`, `get_model_info`, `chat`,
  `complete`, `embed`, `generate_image`, `generate_video`, `generate_music`,
  `tts`, `transcribe`, `transcribe_music`, `separate_audio`, `rerank`,
  `classify`, plus
  admin-gated `load_model`, `unload_model`, `refresh_prompting_guide` — plus
  the `spt://models` and `spt://guide` resources and the `spt://model/{slug}`
  resource template.
- **`classify`** (plugin 1.13.0+, gateway with `POST /v1/classifications`):
  typed questions — `choice`, `score`, yes/no — asked of one document (`input`)
  or a batch (`items`). It returns per-label probabilities and a confidence
  that measures how concentrated the distribution is, not the chance of being
  right: nothing is calibrated on your data, so pick your own thresholds.
- **`separate_audio`** (plugin 1.14.0+, gateway with `POST /v1/audio/separations`):
  splits a song (up to 90 s) into vocals / accompaniment WAVs with the input's
  exact length, written to disk (paths returned) — time sung lyrics by running
  `transcribe` on the vocal stem.
- **`transcribe_music`** (plugin 1.12.0+): turns a song recording into a score,
  with optional MIDI. Pass `audio_path` (a file on your machine, preferred for
  real songs) or `audio_b64`.
- **`output_path`** (plugin 1.15.0+) on `generate_image`, `generate_video`,
  `generate_music` and `tts`: the tool writes the file itself and returns
  `files: [{path, bytes, mime_type, width/height | duration_s}]`. Use it by
  default — inline base64 is truncated by MCP clients beyond a few hundred KB.
- **Tool annotations** (plugin 1.14.1+): `list_models` and `get_model_info` are
  read-only, inference tools are non-destructive, `unload_model` and
  `refresh_prompting_guide` are destructive — clients can approve reads
  automatically.
- **Model aliases** (gateway ≥ 1.1.0 with migration 015): `list_models` also
  returns admin-defined aliases (`gpt-4`, `default-llm`, …) marked with
  `alias_of: <slug>`; every inference tool accepts either name and the
  response echoes the one you used.
- **Skill** `spt-models`: the discover → prompting-guide → infer workflow,
  loaded on demand so a plain "generate me an image" surfaces the catalogue and
  uses the right per-model prompting style.

## License

MIT.
