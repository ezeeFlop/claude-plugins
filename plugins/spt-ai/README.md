# spt-ai — Claude Code plugin

> Manage the **content** of your **Sponge-Theory.ai** site from Claude Code.

Create, edit, translate and share blog posts, products, external-SaaS entries,
tiers and digital products, upload media, and read/update site config — directly
from Claude Code, backed by your site's MCP endpoint. The plugin is 100% static
and carries **no secret**: it talks to your site over authenticated streamable
HTTP (`type: http`). Your API base URL and service API key are entered once,
natively, when you enable the plugin.

## What it does

- **`spt-ai` skill** — teaches Claude the content model (locales, localized fields)
  and the create → translate → share workflow.
- **MCP tools** for blog / products / external-SaaS / tiers / digital products /
  media / site config (curated allow-list; payments, users and billing are never
  exposed).

## Setup

1. **Create a service API key** on your site: sign in as an admin, go to
   **Settings → API keys**, create a key, and copy the `spt_…` value shown once.
2. **Install the plugin** in Claude Code:
   ```
   /plugin marketplace add ezeeFlop/claude-plugins
   /plugin install spt-ai@sponge-theory
   ```
3. When you enable it, Claude Code prompts you (native configuration form):

   | Field | Notes |
   |---|---|
   | **Sponge-Theory.ai API base URL** | e.g. `https://apisaas.sponge-theory.ai`, without `/mcp`. Default provided. |
   | **Service API key (`spt_…`)** | The key from step 1. Stored masked in your system keychain — never in the plugin or a settings file in plaintext. |

## Claude Desktop

The same MCP endpoint works in Claude Desktop as a **remote connector**: add a
custom connector pointing at `https://<your-base-url>/mcp` with an
`X-API-Key: <your key>` header.

## Security

- The key maps to an **admin** identity on your site and can create/edit/delete
  content — treat it like a password. Revoke it any time in **Settings → API keys**.
- The plugin sends the key as the `X-API-Key` header over HTTPS; nothing is stored
  in the repo.

---

© Sponge Theory — proprietary. https://sponge-theory.ai
