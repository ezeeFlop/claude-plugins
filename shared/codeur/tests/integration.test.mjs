import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'node:net';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { operation } from '../src/catalogue.mjs';
import { existsSync } from 'node:fs';

const mcpRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = process.env.CODEUR_SOURCE_ROOT || resolve(mcpRoot, '..');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

test('packaged MCP drives the real FastAPI app on an isolated database', { timeout: 45000, skip: !existsSync(join(root, 'src/api.py')) && 'Set CODEUR_SOURCE_ROOT to the backend checkout for integration testing.' }, async t => {
  const dir = await mkdtemp(join(tmpdir(), 'codeur-mcp-integration-'));
  const socket = createServer();
  await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
  const port = socket.address().port;
  await new Promise(resolve => socket.close(resolve));
  const url = `http://127.0.0.1:${port}`;
  let logs = '';
  const backend = spawn(process.env.CODEUR_TEST_PYTHON || 'python3', ['-m', 'uvicorn', 'src.api:app', '--host', '127.0.0.1', '--port', String(port), '--log-level', 'warning'], {
    cwd: dir,
    env: { ...process.env, PYTHONPATH: root, CODEUR_DB_PATH: join(dir, 'test.db'), APP_PASSWORD: 'mcp-integration-password', LANGFUSE_ENABLED: 'false', POLL_INTERVAL_MINUTES: '0', MAILING_TICK_MINUTES: '0', ANTHROPIC_API_KEY: '', RESEND_API_KEY: '', SLACK_WEBHOOK_URL: '' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  backend.stdout.on('data', chunk => { logs = (logs + chunk).slice(-4000); });
  backend.stderr.on('data', chunk => { logs = (logs + chunk).slice(-4000); });
  let mcp;
  t.after(async () => {
    await mcp?.close();
    backend.kill('SIGTERM');
    for (let i = 0; i < 50 && backend.exitCode === null; i++) await delay(50);
    if (backend.exitCode === null) backend.kill('SIGKILL');
    await rm(dir, { recursive: true, force: true });
  });
  let ready = false;
  for (let i = 0; i < 100; i++) {
    try { if ((await fetch(`${url}/api/health`)).ok) { ready = true; break; } } catch { /* booting */ }
    if (backend.exitCode !== null) break;
    await delay(100);
  }
  assert.ok(ready, `Test backend failed to start: ${logs}`);
  const login = await fetch(`${url}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: 'mcp-integration-password' }) });
  const cookie = login.headers.get('set-cookie').split(';')[0];
  const keyResponse = await fetch(`${url}/api/mcp-keys`, { method: 'POST', headers: { Cookie: cookie, 'Content-Type': 'application/json' }, body: JSON.stringify({ name: 'Isolated MCP integration', scope: 'read_write' }) });
  assert.equal(keyResponse.status, 201);
  const key = await keyResponse.json();
  mcp = new Client({ name: 'codeur-integration', version: '1.0.0' });
  const transport = new StdioClientTransport({ command: process.execPath, args: [join(mcpRoot, 'dist/server.cjs')], cwd: dir, env: { CODEUR_URL: url, CODEUR_API_KEY: key.api_key, CODEUR_OUTPUT_DIR: join(dir, 'exports'), CODEUR_CONFIG_PATH: join(dir, 'missing-config.json') }, stderr: 'pipe' });
  await mcp.connect(transport);
  assert.equal((await mcp.listTools()).tools.length, 7);
  const tool = async (name, args = {}) => {
    const response = await mcp.callTool({ name, arguments: args });
    const data = JSON.parse(response.content[0].text);
    assert.ok(!response.isError, JSON.stringify(data));
    return data;
  };
  const settled = async job => {
    while (job.status === 'running') job = await tool('codeur_job_status', { job_id: job.job_id, wait_ms: 100 });
    assert.equal(job.status, 'completed', JSON.stringify(job));
    return job.result;
  };
  const call = async (id, parameters = {}) => settled(await tool(`codeur_${operation(id).access}`, { operation: id, parameters }));
  const diagnostic = await settled(await tool('codeur_diagnostics'));
  assert.equal(diagnostic.access.ok, true);
  assert.deepEqual(diagnostic.contract.missing_operations, []);
  assert.deepEqual(diagnostic.contract.uncovered_routes, []);

  const customer = await call('customers.create_customer', { body: { name: 'Client MCP test', email: 'client@example.test' } });
  assert.ok(customer.id);
  assert.equal((await call('customers.get_customer', { path: { customer_id: customer.id } })).name, 'Client MCP test');
  const stages = await call('affaires.get_stages');
  const affaire = await call('affaires.create_affaire', { body: { customer_id: customer.id, title: 'Affaire MCP', stage_key: stages[0].key } });
  assert.ok(affaire.id);
  const devis = await call('devis.create_devis', { body: { customer_id: customer.id, title: 'Devis MCP test' } });
  await call('affaires.link_devis', { path: { affaire_id: affaire.id, devis_id: devis.id } });
  await call('devis.update_devis', { path: { devis_id: devis.id }, body: { title: 'Devis modifié par MCP' } });
  assert.equal((await call('devis.get_devis', { path: { devis_id: devis.id } })).title, 'Devis modifié par MCP');
  assert.ok((await call('devis.list_devis_versions', { path: { devis_id: devis.id } })).length > 0);

  const uploaded = await call('devis.upload_devis_attachment', { path: { devis_id: devis.id }, body: { file: { base64: Buffer.from('MCP attachment').toString('base64'), filename: 'brief.txt' } } });
  const downloaded = await call('devis.download_devis_attachment', { path: { devis_id: devis.id, att_id: uploaded.attachment.id } });
  assert.equal(await readFile(downloaded.file, 'utf8'), 'MCP attachment');

  const invoice = await call('invoices.create_invoice', { body: { customer_id: customer.id, devis_id: devis.id, invoice_type: 'standard', line_items: [{ description: 'Test', quantity: 1, unit_price_ht: 100 }] } });
  assert.equal(invoice.status, 'draft');
  assert.equal((await call('invoices.get_invoice', { path: { invoice_id: invoice.id } })).customer_id, customer.id);

  const campaign = await call('campaigns.create_campaign', { body: { name: 'Brouillon MCP', subject: 'Test', body_markdown: 'Bonjour' } });
  const preview = await call('campaigns.preview_campaign', { path: { campaign_id: campaign.id }, body: {} });
  assert.ok(JSON.stringify(preview).includes('Bonjour'));
  const imported = await call('prospects.import_file', { body: { file: { base64: Buffer.from('email,first_name\nprospect@example.test,Ada\n').toString('base64'), filename: 'prospects.csv' }, mapping: JSON.stringify({ email: 'email', first_name: 'first_name' }) } });
  assert.equal(imported.created, 1);
  const prospects = await call('prospects.list_prospects');
  assert.ok(JSON.stringify(prospects).includes('prospect@example.test'));

  const rejected = await mcp.callTool({ name: 'codeur_read', arguments: { operation: 'campaigns.send_campaign', parameters: { path: { campaign_id: campaign.id } } } });
  assert.equal(rejected.isError, true);
  assert.equal((await call('campaigns.get_campaign', { path: { campaign_id: campaign.id } })).status, 'draft');
  assert.equal((await fetch(`${url}/api/mcp-keys/${key.item.id}`, { method: 'DELETE', headers: { Cookie: cookie } })).status, 200);
  const revoked = await mcp.callTool({ name: 'codeur_read', arguments: { operation: 'diagnostic.mcp_identity', parameters: {} } });
  assert.equal(revoked.isError, true);
  assert.ok(!JSON.stringify(revoked).includes(key.api_key));
});
