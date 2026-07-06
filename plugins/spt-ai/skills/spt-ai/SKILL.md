---
name: spt-ai
description: Manage the CONTENT of a Sponge-Theory.ai site (sponge-theory.ai) remotely from Claude Code — create/update/delete/translate/share blog posts, products, external-SaaS entries, tiers and digital products, upload media by URL, and read/update site config. Use whenever the user asks to publish, edit, translate, or share site content, or manage products/media/site settings on their Sponge-Theory.ai site. All operations go through the spt-ai MCP tools; never edit the site's files or database directly.
---

# spt-ai — Sponge-Theory.ai content admin

You can administer the CONTENT of a **Sponge-Theory.ai** site through the `spt-ai`
MCP server, declared in this plugin's `.mcp.json` and authenticated with the
site's `base_url` + a service **API key** (`X-API-Key`) the user set when enabling
the plugin (Claude Code's native plugin configuration). No credential is baked
into this plugin, and the key maps to an admin identity on the site.

## What you can do (the MCP tools)

- **Blog** — `blog_create`, `blog_update`, `blog_delete`, `blog_translate`, `blog_share`
- **Products** — `product_create`, `product_update`, `product_delete`, `product_translate`, `product_share`
- **External SaaS** — `external_saas_create`, `external_saas_update`, `external_saas_delete`, `external_saas_get_by_id`, `external_saas_share`
- **Tiers** — `tier_create`, `tier_update`, `tier_delete`
- **Digital products** — `digital_product_create`, `digital_product_update`, `digital_product_delete`, `digital_product_translate`, `digital_product_share`, `digital_content_list`, `digital_content_delete`
- **Media** — `media_upload_from_url` (give a public image URL; use the returned url as `image_url`), `media_list`, `media_delete`
- **Site config** — `site_config_get`, `site_config_update`

## Content model

- Locales: **en, fr, de, es, zh** (default `en`).
- Localized fields (`title`, `content`, `description`) are objects keyed by locale,
  e.g. `{"en": "...", "fr": "..."}`. You may create in one locale and fill others
  with the `*_translate` tools.

## Typical workflows

- **Publish a blog post**: `blog_create` with `title`/`content`/`description` for the
  default locale → optionally `media_upload_from_url` for the hero image and set
  `image_url` → `blog_translate` to fill the other locales → `blog_share` to post to
  the connected social platforms.
- **Add a product / external SaaS / tier**: use the matching `*_create`, then
  `*_translate` and `*_share` where available.
- **Update site settings**: `site_config_get` to read the current config, adjust, then
  `site_config_update`.

## Rules

- Ground every field in what the user asked for — do not invent prices, dates, or
  copy. Ask if a required field is missing.
- Never attempt to reach payments, users, billing, or auth — those are not exposed
  by this server.
- If a tool returns 401, the API key is missing/invalid/revoked — tell the user to
  create a fresh key in their site admin (Settings → API keys) and re-enter it in the
  plugin config.
