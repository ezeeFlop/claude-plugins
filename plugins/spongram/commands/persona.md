---
name: persona
description: List this brain's personas, or activate one by slug (replaces the active persona).
arguments:
  - name: slug
    description: Persona slug to activate. Omit to list personas.
    required: false
---

If `{{slug}}` is empty: call the `list_personas` tool from the `spongram` MCP server and present the personas (slug, name, one-line role, voice) and which one is active. Do not activate anything.

If `{{slug}}` is given: call the `activate_persona` tool with `slug: "{{slug}}"`, then adopt the returned block immediately for the rest of this session. Remember: in Claude Code the project's conventions and the coding instructions take precedence over the persona. If the tool reports an unknown slug, show the available slugs from its error message.
