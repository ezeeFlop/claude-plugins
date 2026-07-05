# SPT Models — agent workflow

Single source of truth for how an LLM agent should use the SPT Models MCP
server.  Loaded at server startup as the FastMCP `instructions=` (visible to
Claude Desktop), exposed as the MCP resource `spt://guide` (re-readable by
any agent), and wrapped as a Claude Code SKILL inside the plugin bundle.

This is a private GPU stack with a curated catalogue of LLM / VLM / image /
video / audio / embedding / rerank models.

## Golden rules (read these first)

1. **To run inference, just call the inference tool.** The platform auto-loads
   the model on the first request and auto-evicts the least-recently-used model
   when VRAM is tight. You do **not** pre-load. **Never call `load_model` before
   an inference tool.** A model showing `loaded: false` is fine — calling the
   inference tool (`chat`, `generate_image`, `tts`, …) loads it on demand. The
   first call to a cold model can take tens of seconds (big diffusion models
   longer); that's the load, not an error. `load_model` / `unload_model` are
   ops-only tools (deliberate pre-warm, pin, or free VRAM) — not the normal flow.

2. **Always call `get_model_info(slug)` first and apply `recommended_params`.**
   They are model-specific and getting them wrong ruins the output — e.g. 30
   steps + CFG 7.5 on a distilled *Turbo* model (which wants ~8 steps, guidance
   ~1.0), or the default 512×512 square for a wide hero banner.

3. **Resolution and model-specific knobs go through `extra`.** For image models,
   set the size with `extra={"width": W, "height": H}` using a resolution from
   the model's guide — this is the authoritative channel and always wins. The
   top-level `size="WxH"` arg is OpenAI-compatible and also maps to the
   resolution, but `extra` width/height is the reliable one. `extra` is also how
   you pass any model-specific flag (e.g. ErnieImage's `use_pe`) and non-standard
   params on `chat` / `complete` / `generate_music` (e.g. `top_k`).

4. **Never invent a slug** — only use slugs returned by `list_models`.

## 1. Discover

Call `list_models(type=<kind>)` to see what's available.  Map the user's
intent to a model type:

| User says                                   | type        |
|---------------------------------------------|-------------|
| génère une image / generate an image        | `image_gen` |
| génère une vidéo / generate a video         | `video_gen` |
| génère du son, de la musique, un sound effect | `sound_gen` |
| lis ce texte, voix off, TTS                 | `tts`       |
| transcris cet audio, speech-to-text         | `stt`       |
| chat, réponds, raisonne                     | `llm`       |
| analyse cette image, VLM                    | `vlm`       |
| embeddings, vectorise                       | `embedding` |
| reranke, classe des documents               | `rerank`    |

If the catalogue has exactly one matching model, pick it.  If several, show
the user a short list (`slug — short description`) and ask which one.

## 2. Read the prompting guide

Once the model is chosen, call `get_model_info(slug)` and read the
`prompting_guide` field.  Keys you may find:

- `system_prompt` / `format` — required structure for the prompt
- `example_prompts` — concrete good prompts to imitate
- `recommended_params` — temperature, steps, guidance/cfg, **width/height**,
  etc.  Pass these in the inference call unless the user explicitly overrides.
  For image models, feed width/height through `extra` (see golden rule 3).
- `do_dont` — hard constraints; respect them
- `limitations` — surface to the user when relevant

Reformulate the user's intent into a prompt that matches the guide.  For
image / video / sound models this often means adding style descriptors,
switching to English, or using a specific tag syntax.

## 3. Run inference

Call the matching tool with the params from the prompting guide.  **The model
loads automatically on this call** — you never load it yourself.

| type        | tool                                                     |
|-------------|----------------------------------------------------------|
| `llm`       | `chat(model, messages, ...)` or `complete(model, prompt, ...)` |
| `vlm`       | `chat(model, messages with image url or base64, ...)`    |
| `image_gen` | `generate_image(model, prompt, ...)`                     |
| `video_gen` | `generate_video(model, prompt, ...)` if available        |
| `sound_gen` | `generate_music(model, prompt, ...)`                     |
| `tts`       | `tts(model, text, voice?, ...)`                          |
| `stt`       | `transcribe(model, audio_base64, ...)`                   |
| `embedding` | `embed(model, input, ...)`                               |
| `rerank`    | `rerank(model, query, documents, ...)`                   |

### Worked example — image generation

```
get_model_info("ernie-image-turbo")
# guide → supported resolutions incl. 1376×768, recommended 8 steps,
#         guidance 1.0, optional use_pe (prompt enhancer)

generate_image(
    model="ernie-image-turbo",
    prompt="…detailed prompt written per the guide…",
    num_inference_steps=8,
    guidance_scale=1.0,
    extra={"width": 1376, "height": 768, "use_pe": True},
)
```

The first call triggers the load (tens of seconds for big diffusion models);
subsequent calls reuse the loaded model and are fast.  Without `extra` width/
height you get 512×512 — too small/square for most real uses.

**Always cite which model you used** at the end of your response
("Generated with `ernie-image-turbo`" / "Transcribed with `whisperx-large-v3`").

## Resources for grounding

- `spt://models` — full catalogue (resource, not tool)
- `spt://model/<slug>` — single-model details (resource)
- `spt://guide` — this document, re-readable any time

Resources are fine to read silently for context; prefer them over extra
`list_models` calls when you only need a quick re-check.

## What NOT to do

- **Don't call `load_model` before an inference tool** — inference auto-loads
  (and the platform auto-evicts an LRU model if VRAM is short). Use
  `load_model` / `unload_model` only for deliberate ops (pre-warm, pin, free).
- Don't call an inference tool without first reading the model's prompting guide.
- Don't rely on a bare `generate_image(size=…)` and assume the resolution
  stuck — set `extra={"width": …, "height": …}` from the model's supported
  resolutions.
- Don't invent a model slug.
- Don't drop or paraphrase the user's prompt — reformulate it per the guide,
  preserving the intent.
