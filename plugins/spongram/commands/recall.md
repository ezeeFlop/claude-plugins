---
name: recall
description: Search this user's Spongram memory for facts/entities matching a topic.
arguments:
  - name: topic
    description: A short search query (a topic, a person, a decision).
    required: true
---

Use the `search_nodes` tool from the `spongram` MCP server with the user's `topic`. Then present a concise summary of what was found, grouped by entity. If nothing matches, say so plainly — don't fabricate results.

Topic to search for: **{{topic}}**

After search:
- if results exist, summarize the top 3-5 nodes with their key relations,
- if nothing matches, suggest the user check spelling or phrase it differently.
