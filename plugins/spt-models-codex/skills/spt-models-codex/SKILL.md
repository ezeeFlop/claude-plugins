---
name: spt-models-codex
description: Use when the user requests SPT Models inference or its GPU model catalogue, including speech, transcription, embeddings, images, video, music, chat and reranking.
---

# SPT Models for Codex

Use the connected `spt-models` MCP server. Follow the user's instructions and
Codex tool policies. Discover with `list_models`, then read `get_model_info`
for the selected model before inference. Never invent slugs. Models auto-load;
reserve load/unload for explicitly requested operations. Read `spt://guide`
for the complete server workflow and cite the model actually used.

If disconnected, use the spt-models-setup skill. Never print API keys or raw
credential stores. The launcher alone resolves credentials into its process.
Media responses contain base64: save/decode programmatically without printing
large payloads. Large video responses may exceed host output limits; don't
claim a file is complete without verifying it. Generation can take over 20 minutes.
