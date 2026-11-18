# SPT Models MCP 1.17.0

TRELLIS image-to-3D accepts a local PNG/JPG through `generate_image.image_path`.
The existing raw base64 `extra.image` interface remains supported. Gateway
error messages now reach the MCP client, including failures returned by an
asynchronous job. Unexpected internal exceptions remain masked by MCP SDK 2.

This is a compatible minor release of the connector. The gateway distributor
is version 1.10.5; no GPU worker or model-loader update is required.

## Claude Code — public marketplace

For an existing installation, in a terminal:

```bash
claude plugin marketplace update sponge-theory
claude plugin update spt-models@sponge-theory
```

Then run `/reload-plugins` in the open Claude Code session, or restart it.
For a first installation:

```
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install spt-models@sponge-theory
```

Existing URL/key settings are retained. Do not install the private per-key
`.plugin` alongside the public marketplace plugin: both expose the same server.

## Claude Desktop — MCPB

Download [spt-models-1.17.0.mcpb and SHA256SUMS](https://github.com/ezeeFlop/claude-plugins/releases/tag/spt-models-v1.17.0).
Drop the `.mcpb` into Claude Desktop and accept the extension update. For a
first installation, configure the gateway URL and API key in its masked form.
The public archive contains no API key or admin token.

Clients already using the launcher (1.16.0+) also fetch the latest server from
their configured gateway at startup. Quit and reopen Claude Desktop. If the
initial download/dependency setup exceeds the startup budget, the old server
runs while preparation finishes; reopen the app once more afterwards.
`SPT_AUTO_UPDATE=false` disables this mechanism. Older clients need the new
MCPB installed manually. A normal update does not require creating a new key.

## Codex

Refresh the `sponge-theory-codex` marketplace and update or reinstall
`spt-models-codex` from its plugin page, then open a new thread. The existing
macOS Keychain configuration is retained; the credential helper is unchanged.
The packaged server is byte-for-byte identical to Claude Code's server.

## Verify and use TRELLIS

Ask the client for the `generate_image` tool schema: it must include the
optional `image_path` field. First read `get_model_info` for `trellis-2-4b`,
then call `generate_image` with the following arguments, using actual paths
on the machine running the MCP server:

```json
{
  "model": "trellis-2-4b",
  "prompt": "",
  "image_path": "/absolute/path/object.png",
  "seed": 42,
  "extra": {"resolution": 512, "texture_size": 2048, "decimation_target": 300000},
  "output_path": "/absolute/path/object.glb"
}
```

The server reads and encodes the input. If using `extra.image` instead, pass
complete raw base64 bytes, never a filename, URL or data URI. Do not provide
both input forms. The output is a GLB mesh with PBR materials, reported under
`files`. Loading and inference can take many minutes; avoid duplicate jobs.

## Validation

The registered MCP tool is tested with both SDK 1.30.0 and 2.2.0: existing
base64 input, local image input, asynchronous GLB delivery, invalid files,
and gateway errors from submission and job results. Packaging checks cover
the catalogue, public plugin copies, manifests and served update archives.
No changes to credentials, model parameters or GPU worker images are included.
