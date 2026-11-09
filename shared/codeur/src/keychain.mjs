import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync, lstatSync } from 'node:fs';
import { mkdir, mkdtemp, copyFile, chmod, link, rm } from 'node:fs/promises';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import identity from './keychain-identity.json' with { type: 'json' };

export const helperPath = () => join(homedir(), '.sponge-theory', 'codeur-keychain', identity.version, 'spt-codeur-keychain');
export const credentialAccount = url => createHash('sha256').update(url).digest('hex');
export const credentialService = client => {
  if (!['codex', 'claude-code'].includes(client)) throw new Error('Use the sensitive API key field in Claude Desktop.');
  return `ai.sponge-theory.codeur.${client}.v1`;
};
export function validateApiKey(value) {
  if (!/^codeur_mcp_[A-Za-z0-9_-]{43}$/.test(value)) throw new Error('Enter the Codeur API key (codeur_mcp_…), without the Bearer prefix.');
  return value;
}

export function verifiedHelper(path = helperPath()) {
  try {
    const stat = lstatSync(path);
    return stat.isFile() && !stat.isSymbolicLink() && stat.uid === process.getuid() && !(stat.mode & 0o022)
      && createHash('sha256').update(readFileSync(path)).digest('hex') === identity.sha256;
  } catch { return false; }
}

export async function installHelper(source) {
  if (process.platform !== 'darwin') throw new Error('Native Keychain setup requires macOS.');
  const target = helperPath();
  if (verifiedHelper(target)) return;
  try { lstatSync(target); throw new Error('Existing Codeur helper differs; repair its installation explicitly.'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  source ||= typeof __dirname !== 'undefined' ? join(__dirname, 'native/keychain-helper') : fileURLToPath(new URL('../native/keychain-helper', import.meta.url));
  if (createHash('sha256').update(readFileSync(source)).digest('hex') !== identity.sha256) throw new Error('Packaged Keychain helper is corrupt. Reinstall the plugin.');
  await mkdir(dirname(target), { recursive: true, mode: 0o700 });
  const temp = await mkdtemp(join(dirname(target), '.install-'));
  try {
    const staged = join(temp, 'helper');
    await copyFile(source, staged);
    await chmod(staged, 0o700);
    try { await link(staged, target); }
    catch (error) { if (error.code !== 'EEXIST' || !verifiedHelper(target)) throw new Error('Concurrent Keychain installation failed. Run setup again.'); }
  } finally { await rm(temp, { recursive: true, force: true }); }
}

export function keychain(operation, url, client, value, interactive = false) {
  if (!verifiedHelper()) throw new Error('Codeur Keychain helper unavailable. Run the plugin setup.');
  const request = { service: credentialService(client), account: credentialAccount(url), operation };
  if (value !== undefined) request.value = validateApiKey(value);
  let reply;
  try {
    reply = JSON.parse(execFileSync(helperPath(), interactive ? ['--interactive'] : [], {
      input: JSON.stringify(request), encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'], timeout: interactive ? 120000 : 10000,
    }));
  } catch { throw new Error('Native Keychain operation failed. Run the plugin setup; no credential was printed.'); }
  if (reply.status === -25300 && ['read', 'delete'].includes(operation)) return null;
  if (reply.status !== 0) throw new Error(`Codeur Keychain unavailable (status ${reply.status}). Unlock it and run setup; runtime never opens a dialog.`);
  return reply.value;
}
