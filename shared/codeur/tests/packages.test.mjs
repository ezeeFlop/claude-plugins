import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const dist = resolve(dirname(fileURLToPath(import.meta.url)), '../dist');
for (const surface of ['codex', 'claude', 'desktop']) {
  test(`${surface} package launches its declared MCP command and discovers operations`, async t => {
    const temp = await mkdtemp(join(tmpdir(), 'codeur-package-'));
    t.after(() => rm(temp, { recursive: true, force: true }));
    const root = surface === 'desktop' ? join(dist, 'desktop') : join(dist, 'plugins', surface === 'codex' ? 'codeur-codex' : 'codeur');
    let config;
    if (surface === 'desktop') {
      const manifest = JSON.parse(await readFile(join(root, 'manifest.json'), 'utf8'));
      assert.equal(manifest.user_config.api_key.sensitive, true);
      assert.equal(manifest.user_config.api_key.required, true);
      config = manifest.server.mcp_config;
    } else {
      const file = surface === 'codex' ? '.codex-plugin/plugin.json' : '.claude-plugin/plugin.json';
      const manifest = JSON.parse(await readFile(join(root, file), 'utf8'));
      config = JSON.parse(await readFile(join(root, manifest.mcpServers), 'utf8')).mcpServers['codeur-automation'];
      assert.match(await readFile(join(root, manifest.skills, 'codeur/SKILL.md'), 'utf8'), /codeur_search_operations/);
    }
    assert.equal(config.command, 'node');
    assert.deepEqual(await readFile(join(root, 'server.cjs')), await readFile(join(dist, 'server.cjs')));
    const args = config.args.map(arg => arg.replaceAll('${__dirname}', root).replaceAll('${CLAUDE_PLUGIN_ROOT}', root));
    const client = new Client({ name: 'package-test', version: '1' });
    const transport = new StdioClientTransport({ command: process.execPath, args, cwd: surface === 'codex' ? root : temp, env: { CODEUR_URL: 'https://example.test', CODEUR_API_KEY: 'codeur_mcp_' + 'z'.repeat(43), CODEUR_CLIENT: config.env.CODEUR_CLIENT, CODEUR_CONFIG_PATH: join(temp, 'config.json') }, stderr: 'pipe' });
    t.after(() => client.close());
    await client.connect(transport);
    assert.equal((await client.listTools()).tools.length, 7);
    const response = await client.callTool({ name: 'codeur_search_operations', arguments: { query: 'devis' } });
    assert.ok(!response.isError);
    assert.ok(JSON.parse(response.content[0].text).operations.some(op => op.id === 'devis.get_devis'));
  });
}
