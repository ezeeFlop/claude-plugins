---
name: spt-ai
description: Pilot EVERYTHING on your Sponge-Theory.ai CORPORATE SITE (sponge-theory.ai) from Claude Code — list AND read AND create/update/delete/translate/share blog posts, products, external-SaaS entries, tiers and digital products; upload media by URL; and manage CMS pages (home, FAQ, terms, privacy) and site config. ACTIVATE THIS SKILL whenever the user mentions "my corporate site", "mon site corporate", "my site", "le site", "the blog", "sponge-theory.ai", or asks to list, read, browse, publish, create, edit, translate, share, or delete any site content, products, tiers, media, or pages. All operations go through the spt-ai MCP tools (mcp__spt-ai__*); never edit the site's files or database directly.
---

# spt-ai — Sponge-Theory.ai corporate site content admin

You can administer the **entire content of the user's Sponge-Theory.ai corporate
site** (sponge-theory.ai) through the `spt-ai` MCP server, declared in this
plugin's `.mcp.json` and authenticated with the site's `base_url` + a service
**API key** (`X-API-Key`) the user set when enabling the plugin. No credential is
baked into this plugin; the key maps to an admin identity on the site.

**When the user refers to "the corporate site", "mon site", "the blog", or
sponge-theory.ai, use these tools** — both to READ (list/browse/inspect) and to
WRITE (create/edit/translate/share/delete). Always LIST or GET first to find the
exact item, then act on it.

## Tools (mcp__spt-ai__*)

### Read / browse (use these first to discover content)
- **Blog** — `blog_list` (paginated; supports `published` = true/false/omit-for-all, `tag`, `search`, `order_by`, `order_direction`), `blog_get` (by slug)
- **Products** — `product_list`, `product_get` (by id)
- **External SaaS** — `external_saas_list` (supports `published_only`), `external_saas_get_by_id`
- **Tiers** — `tier_list`
- **Digital products** — `digital_product_list`, `digital_product_get`, `digital_content_list`
- **Media** — `media_list`
- **CMS pages** — `content_get_home`, `content_get_faq`, `content_get_terms`, `content_get_privacy`
- **Site config** — `site_config_get`

### Write
- **Blog** — `blog_create`, `blog_update`, `blog_delete`, `blog_translate`, `blog_share`
- **Products** — `product_create`, `product_update`, `product_delete`, `product_translate`, `product_share`
- **External SaaS** — `external_saas_create`, `external_saas_update`, `external_saas_delete`, `external_saas_share`
- **Tiers** — `tier_create`, `tier_update`, `tier_delete`
- **Digital products** — `digital_product_create`, `digital_product_update`, `digital_product_delete`, `digital_product_translate`, `digital_product_share`, `digital_content_upload`, `digital_content_delete`
- **Media** — `media_upload_from_url` (give a public image URL; use the returned url as `image_url`), `media_delete`
- **CMS pages** — `content_update_home`, `content_update_faq`, `content_update_terms`, `content_update_privacy`, `content_translate` (translate a page between locales)
- **Site config** — `site_config_update`

## Content model

- Locales: **en, fr, de, es, zh** (default `en`).
- Localized fields (`title`, `content`, `description`) are objects keyed by locale,
  e.g. `{"en": "...", "fr": "..."}`. Create in one locale, fill the rest with the
  `*_translate` tools.
- Blog posts have a `published` flag: drafts are `published=false`. `blog_list`
  returns published-only by default context — pass `published=false` to see drafts,
  or omit the filter to get both.

## Typical workflows

- **"List my latest blog posts"** → `blog_list` (order_by=created_at, desc). To
  include drafts, add `published=false` (or query both).
- **"Edit the post about X"** → `blog_list`/`blog_get` to find the slug/id → read it
  → `blog_update` with the changed fields → optionally `blog_translate` then `blog_share`.
- **"Publish a new post"** → `blog_create` (default-locale title/content/description)
  → `media_upload_from_url` for the hero image, set `image_url` → `blog_translate` for
  the other locales → `blog_share`.
- **"Update the homepage / FAQ / terms"** → `content_get_home` (or faq/terms/privacy)
  to read the current content → `content_update_home` with the new content →
  `content_translate` to propagate to other locales.
- **Products / external-SaaS / tiers / digital products** — `*_list`/`*_get` to find,
  then the matching `*_create`/`*_update`/`*_delete`/`*_translate`/`*_share`.

## Rules

- Always discover with a `*_list`/`*_get` before editing, so you act on the right item.
- Ground every field in what the user asked for — do not invent prices, dates, copy,
  or attendees. Ask if a required field is missing.
- Never attempt to reach payments, users, billing, or auth — those are not exposed
  by this server.
- If a tool returns 401, the API key is missing/invalid/revoked — tell the user to
  create a fresh key in their site admin (Settings → API keys) and re-enter it in the
  plugin config. If a write tool returns 404, LIST first to get the correct id/slug.
