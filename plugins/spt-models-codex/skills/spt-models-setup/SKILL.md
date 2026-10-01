---
name: spt-models-setup
description: Configure or verify the SPT Models Codex plugin, including gateway URL and secure API key setup on macOS.
---

# Configure SPT Models

Run `uv run --locked --directory <plugin-root> scripts/configure.py --gui`.
The local dialog accepts the URL and masked API key, or offers reuse of the
matching Claude Code SPT Models credential. Never request a key in chat,
read credential values yourself, or print the launcher's environment.
The helper verifies `/v1/models` before saving an active profile. Only the
selected SPT Models credential may be read from Claude's store; other secrets
must never be output or used. No admin credential is imported automatically.

Run `uv run --locked --directory <plugin-root> scripts/check_connection.py` for a
secret-free MCP handshake and catalogue test. Start a new Codex thread after
installation/configuration to expose the tools. On other platforms, supply
`SPT_BASE_URL` and `SPT_API_KEY` in the host environment before launching Codex;
`SPT_ADMIN_TOKEN` is optional for operations explicitly requested by the user.

For an existing installation or recurring Keychain prompts, run
`uv run --locked --directory <plugin-root> scripts/configure.py --migrate`.
The selected saved key is copied once into a Codex-owned native Keychain entry;
Claude's item is never changed. Runtime never reads Claude storage or opens
Keychain dialogs. Setup installs the bundled, locally signed native helper at a
stable path. Never invoke that helper directly as an agent tool. Rotation in
Claude no longer updates the independent Codex copy; rerun interactive setup.
