// Synthetic credentials only. Never print a helper reply or a credential.
import { randomBytes, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { installHelper, keychain, helperPath, credentialService, credentialAccount } from '../src/keychain.mjs';

await installHelper();
const url = `https://keychain-check-${randomUUID()}.invalid`;
for (const client of ['codex', 'claude-code']) {
  const token = `codeur_mcp_${randomBytes(32).toString('base64url')}`;
  try {
    keychain('write', url, client, token, true);
    // A fresh process must read without an interactive Keychain dialog.
    const raw = execFileSync(helperPath(), [], { input: JSON.stringify({ operation: 'read', service: credentialService(client), account: credentialAccount(url) }), encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'], timeout: 10000 });
    const reply = JSON.parse(raw);
    if (reply.status !== 0 || reply.value !== token) throw new Error('Noninteractive Keychain check failed.');
    const replacement = `codeur_mcp_${randomBytes(32).toString('base64url')}`;
    keychain('write', url, client, replacement, true);
    if (keychain('read', url, client) !== replacement) throw new Error('Keychain rotation check failed.');
  } finally { keychain('delete', url, client, undefined, true); }
  if (keychain('read', url, client) !== null) throw new Error('Keychain cleanup check failed.');
  process.stdout.write(`${client}: synthetic write, fresh noninteractive read, rotation and deletion passed.\n`);
}
