---
name: brain-graph
description: Open the Spongram 3D graph explorer (read-only, scoped to this user's brain).
---

Give the user the URL of their Spongram graph explorer.

1. Determine the instance URL. Run in Bash:

   ```bash
   printenv CLAUDE_PLUGIN_OPTION_INSTANCE_URL || echo "https://spongram.sponge-theory.dev"
   ```

   Use the printed value (it's the `instance_url` the user set when enabling the
   plugin; falls back to the hosted default).

2. Print this message verbatim, substituting `<INSTANCE_URL>` — then stop (do not
   fetch or open anything yourself):

   ```
   Open the Spongram graph explorer:

     <INSTANCE_URL>/v1/graph

   It's a Spongram-served read-only 3D view, strictly scoped to your own brain —
   no other tenant's data is reachable. When the page prompts for a key, paste
   your spt_brain_… key (the same brain key you configured for this plugin).
   ```

   Never print a `spt_brain_…` key in your reply.
