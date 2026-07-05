---
name: brain-stats
description: Show this Spongram brain's status and latest activity.
---

Report a compact status of this user's Spongram brain, using the `spongram` MCP
server (already authenticated via the plugin's configured brain key).

1. Call the `get_status` tool to confirm the server is reachable and connected.
2. Call `get_episodes` with `max_episodes=5` to fetch the latest activity.

Display a compact summary:

```
Spongram — connected (<get_status message>)
latest episodes:
  - <created_at> — <short content>   (up to 5, most recent first)
```

If `get_status` errors with an auth failure, tell the user to check the brain key
they configured for this plugin (Spongram admin → regenerate if needed), and stop.
