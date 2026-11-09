import { createInterface } from 'node:readline/promises';
import { emitKeypressEvents } from 'node:readline';
import { mkdir, mkdtemp, writeFile, rename, rm } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { configPath, clientName, DEFAULT_URL, validateUrl } from './config.mjs';
import { installHelper, keychain, validateApiKey } from './keychain.mjs';
import { CodeurClient, readLimited } from './client.mjs';

async function hiddenPassword() {
  if (!process.stdin.isTTY) throw new Error('Run setup with --gui or in an interactive terminal.');
  process.stdout.write('Clé API Codeur (saisie masquée) : ');
  emitKeypressEvents(process.stdin);
  process.stdin.setRawMode(true);
  process.stdin.resume();
  return new Promise((resolve, reject) => {
    let password = '';
    const finish = () => {
      process.stdin.off('keypress', onKey);
      process.stdin.setRawMode(false);
      process.stdin.pause();
      process.stdout.write('\n');
    };
    const onKey = (text, key = {}) => {
      if (key.ctrl && key.name === 'c') { finish(); reject(new Error('Setup cancelled.')); }
      else if (key.name === 'return') { finish(); resolve(password); }
      else if (key.name === 'backspace') { password = password.slice(0, -1); }
      else if (text && !key.ctrl && !key.meta && !text.includes('\u001b')) password += text;
    };
    process.stdin.on('keypress', onKey);
  });
}

export async function setup() {
  if (process.platform !== 'darwin') throw new Error('Use the MCPB sensitive API key field, or CODEUR_API_KEY in the CLI launching environment.');
  const client = clientName();
  if (client === 'desktop') throw new Error('Use the Claude Desktop MCPB settings to enter the API key.');
  const gui = process.argv.includes('--gui') || !process.stdin.isTTY;
  const askGui = (prompt, value = '', hidden = false) => {
    const script = `on run argv\nset answer to display dialog (item 1 of argv) default answer (item 2 of argv) ${hidden ? 'with' : 'without'} hidden answer with title "Codeur — connexion MCP"\nreturn text returned of answer\nend run`;
    try { return execFileSync('/usr/bin/osascript', ['-e', script, prompt, value], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).replace(/[\r\n]+$/, ''); }
    catch { throw new Error('Setup cancelled. No credential was printed.'); }
  };
  let url, apiKey;
  if (gui) {
    url = validateUrl(askGui('URL de votre instance Codeur', DEFAULT_URL));
    apiKey = validateApiKey(askGui('Clé API créée dans Paramètres → Accès MCP (codeur_mcp_…)', '', true));
  } else {
    const prompt = createInterface({ input: process.stdin, output: process.stdout });
    try { url = validateUrl((await prompt.question(`URL de Codeur [${DEFAULT_URL}] : `)).trim() || DEFAULT_URL); }
    finally { prompt.close(); }
    apiKey = validateApiKey(await hiddenPassword());
  }
  const api = new CodeurClient({ baseUrl: url, apiKey, timeoutMs: 30000 });
  const response = await api.request('/api/mcp/identity', { method: 'GET' });
  const identity = JSON.parse((await readLimited(response)).toString('utf8'));
  if (identity.authenticated !== true) throw new Error('The API did not authenticate this key.');
  await installHelper();
  const previous = keychain('read', url, client, undefined, true);
  const destination = configPath();
  await mkdir(dirname(destination), { recursive: true, mode: 0o700 });
  const temporary = await mkdtemp(join(dirname(destination), '.setup-'));
  try {
    keychain('write', url, client, apiKey, true);
    await writeFile(join(temporary, 'profile.json'), JSON.stringify({ url, storage: 'native-v1', client, key_id: identity.key_id }, null, 2) + '\n', { mode: 0o600 });
    await rename(join(temporary, 'profile.json'), destination);
  } catch (error) {
    keychain(previous ? 'write' : 'delete', url, client, previous || undefined, true);
    throw error;
  } finally { await rm(temporary, { recursive: true, force: true }); }
  process.stdout.write('Connexion vérifiée. Clé enregistrée dans le trousseau dédié ; aucun secret dans le profil ou les journaux.\n');
}
