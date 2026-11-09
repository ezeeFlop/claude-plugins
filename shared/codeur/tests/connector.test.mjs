import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { CodeurClient } from '../src/client.mjs';
import { CodeurService } from '../src/service.mjs';
import { operations, operation, searchOperations, validateParameters } from '../src/catalogue.mjs';
import { Jobs } from '../src/jobs.mjs';
import { validateUrl } from '../src/config.mjs';

const config = { baseUrl: 'https://codeur.example.test', apiKey: 'codeur_mcp_' + 'a'.repeat(43), timeoutMs: 2000, outputDir: '/unused', readOnly: false };
const json = (body, status = 200, headers = {}) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', ...headers } });

test('every catalogue schema compiles and discovery is paginated', () => {
  for (const op of operations) {
    try { validateParameters(op, {}); }
    catch (error) { assert.match(error.message, /^Invalid parameters:/, op.id); }
  }
  const all = searchOperations({ limit: 50 });
  assert.equal(all.total, operations.length);
  assert.equal(all.next_offset, 50);
  assert.ok(searchOperations({ query: 'factures' }).operations.some(op => op.domain === 'invoices'));
  assert.ok(searchOperations({ query: 'pièces jointes' }).operations.some(op => op.domain === 'devis'));
});

test('validation prevents unknown operations, missing paths and misplaced parameters', () => {
  assert.throws(() => operation('GET https://other.test'), /Unknown operation/);
  assert.throws(() => validateParameters(operation('customers.get_customer'), {}), /Invalid parameters/);
  assert.throws(() => validateParameters(operation('customers.list_customers'), { query: { invalid: 1 } }), /Invalid parameters/);
  assert.throws(() => validateParameters(operation('invoices.create_invoice'), { body: { customer_id: 'c' } }), /Invalid parameters/);
});

test('write routing and read-only mode are enforced before any HTTP call', async () => {
  let calls = 0;
  const service = new CodeurService(new CodeurClient({ ...config, readOnly: true }, async () => { calls++; return json({}); }));
  await assert.rejects(service.call('codeur_read', { operation: 'customers.create_customer', parameters: { body: { name: 'x' } } }), /codeur_write/);
  await assert.rejects(service.call('codeur_write', { operation: 'customers.create_customer', parameters: { body: { name: 'x' } } }), /read-only/);
  assert.equal(operation('devis.get_devis').access, 'write');
  assert.equal(operation('campaigns.campaign_stats').access, 'write');
  assert.equal(operation('devis.get_devis_pdf').access, 'download');
  assert.equal(calls, 0);
});

test('API key travels only in Authorization and is redacted from results', async () => {
  const calls = [];
  const client = new CodeurClient(config, async (url, init) => {
    calls.push({ url, init });
    return json({ note: config.apiKey, anthropic_api_key: 'private-provider-key' });
  });
  const result = await client.execute(operation('customers.list_customers'), {});
  assert.equal(calls.length, 1);
  assert.equal(calls[0].init.headers.Authorization, `Bearer ${config.apiKey}`);
  assert.ok(!calls[0].url.includes(config.apiKey));
  assert.ok(!JSON.stringify(result).includes(config.apiKey));
  assert.ok(!JSON.stringify(result).includes('private-provider-key'));
  assert.equal(calls[0].init.redirect, 'manual');
});

test('a rejected key is not retried and never falls back to a password or cookie', async () => {
  let calls = 0;
  const client = new CodeurClient(config, async () => { calls++; return json({}, 401); });
  await assert.rejects(client.execute(operation('customers.list_customers'), {}), /expired or revoked/);
  assert.equal(calls, 1);
});

test('a mutation timeout/500 is uncertain and is not automatically replayed', async () => {
  for (const response of [() => { throw new Error('network'); }, () => json({ detail: 'unavailable' }, 500)]) {
    let calls = 0;
    const service = new CodeurService(new CodeurClient(config, async () => { calls++; return response(); }));
    const result = await service.call('codeur_write', { operation: 'customers.create_customer', parameters: { body: { name: 'Test' } } });
    assert.equal(result.status, 'uncertain');
    assert.equal(calls, 1);
    assert.equal((await service.call('codeur_job_status', { job_id: result.job_id, wait_ms: 0 })).status, 'uncertain');
    assert.equal(calls, 1);
  }
});

test('HTTP redirects and path traversal cannot forward credentials', async () => {
  let calls = 0;
  const client = new CodeurClient(config, async () => { calls++; return new Response('', { status: 302, headers: { location: 'https://attacker.test' } }); });
  await assert.rejects(client.execute(operation('customers.get_customer'), { path: { customer_id: '../settings' } }), /Invalid path/);
  assert.equal(calls, 0);
  await assert.rejects(client.execute(operation('customers.list_customers'), {}), /redirect/);
  assert.equal(calls, 1);
  assert.throws(() => validateUrl('http://remote.example.test'), /HTTPS/);
  assert.throws(() => validateUrl('https://user:password@remote.example.test'), /credentials/);
});

test('a successful write with an unreadable response remains uncertain', async () => {
  let calls = 0;
  const service = new CodeurService(new CodeurClient(config, async () => {
    calls++;
    return new Response('broken JSON', { headers: { 'content-type': 'application/json' } });
  }));
  const result = await service.call('codeur_write', { operation: 'customers.create_customer', parameters: { body: { name: 'Test' } } });
  assert.equal(result.status, 'uncertain');
  assert.equal(calls, 1);
});

test('API validation errors do not echo submitted secret values', async () => {
  const client = new CodeurClient(config, async () => json({ detail: [{ loc: ['body', 'key'], msg: 'Invalid value', input: 'never-echo-this-value' }] }, 422));
  await assert.rejects(client.execute(operation('settings.update_settings'), { body: {} }), error => !error.message.includes('never-echo-this-value') && error.message.includes('Invalid value'));
});

test('multipart supports local paths and base64 while exports stay inside output directory', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'codeur-files-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const source = join(dir, 'brief.pdf');
  await writeFile(source, '%PDF sample');
  let sent;
  const client = new CodeurClient({ ...config, outputDir: join(dir, 'exports') }, async (_, init) => {
    if (init.method === 'POST') {
      sent = init.body;
      return json({ ok: true });
    }
    return new Response('%PDF downloaded', { headers: { 'content-type': 'application/pdf', 'content-disposition': 'attachment; filename="../../outside.pdf"' } });
  });
  for (const file of [{ path: source }, { base64: Buffer.from('%PDF sample').toString('base64'), filename: 'brief.pdf' }]) {
    const params = { path: { devis_id: 'd1' }, body: { file, attachment_type: 'autre' } };
    validateParameters(operation('devis.upload_devis_attachment'), params);
    await client.execute(operation('devis.upload_devis_attachment'), params);
    assert.equal(await sent.get('file').text(), '%PDF sample');
    assert.equal(sent.get('attachment_type'), 'autre');
  }
  const result = await client.execute(operation('devis.get_devis_pdf'), { path: { devis_id: 'd1' } });
  assert.ok(result.file.startsWith(join(dir, 'exports') + '/'));
  assert.equal(result.filename, 'outside.pdf');
  assert.equal(await readFile(result.file, 'utf8'), '%PDF downloaded');
});

test('jobs report progress and completion without running work twice', async () => {
  const jobs = new Jobs();
  let release, count = 0;
  const result = await jobs.run('slow-operation', () => { count++; return new Promise(resolve => { release = resolve; }); });
  assert.equal(result.status, 'running');
  release({ ok: true });
  const completed = await jobs.status(result.job_id, 1);
  assert.equal(completed.status, 'completed');
  assert.deepEqual(completed.result, { ok: true });
  assert.equal(count, 1);
  await assert.rejects(jobs.status('missing', 0), /check the record/);
});
