import { build } from 'esbuild';
import { cp, mkdir, mkdtemp, rm, readFile, writeFile, readdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { TOOLS } from '../src/service.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');
const pkg = JSON.parse(await readFile(join(root, 'package.json'), 'utf8'));
const nativeIdentity = JSON.parse(await readFile(join(root, 'src/keychain-identity.json'), 'utf8'));
if (createHash('sha256').update(await readFile(join(root, 'native/keychain-helper'))).digest('hex') !== nativeIdentity.sha256) throw new Error('Native helper identity changed. Do not rebuild it during ordinary releases.');
const author = { name: 'Sponge Theory' };
const json = async (path, value) => {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(value, null, 2) + '\n');
};
await mkdir(dist, { recursive: true });
await cp(join(root, 'native'), join(dist, 'native'), { recursive: true });
await build({ entryPoints: [join(root, 'src/server.mjs')], bundle: true, platform: 'node', target: 'node20', format: 'cjs', outfile: join(dist, 'server.cjs'), legalComments: 'eof', logLevel: 'warning' });

// Include license texts for every installed production dependency. npm's lock
// records which packages are development-only; they are not shipped as code.
const lock = JSON.parse(await readFile(join(root, 'package-lock.json'), 'utf8'));
let notices = 'Third-party licenses for the bundled Codeur MCP server.\n';
for (const [path, meta] of Object.entries(lock.packages || {})) {
  if (!path || meta.dev) continue;
  const dir = join(root, path);
  for (const name of await readdir(dir)) {
    if (/^(licen[cs]e|copying)(\.|$)/i.test(name)) {
      notices += `\n\n--- ${path} (${meta.version}) ---\n${await readFile(join(dir, name), 'utf8')}\n`;
    }
  }
}
await writeFile(join(dist, 'THIRD_PARTY_NOTICES.txt'), notices);

for (const name of ['codeur', 'codeur-codex']) {
  const target = join(dist, 'plugins', name);
  await mkdir(target, { recursive: true });
  await cp(join(dist, 'server.cjs'), join(target, 'server.cjs'));
  await cp(join(root, 'native/keychain-helper'), join(target, 'native/keychain-helper'), { recursive: false });
  await cp(join(dist, 'THIRD_PARTY_NOTICES.txt'), join(target, 'THIRD_PARTY_NOTICES.txt'));
  await cp(join(root, 'skills'), join(target, 'skills'), { recursive: true });
  await cp(join(root, 'README.md'), join(target, 'README.md'));
  const manifest = { name, version: pkg.version, description: pkg.description, author, skills: './skills/', mcpServers: './.mcp.json' };
  if (name === 'codeur-codex') {
    manifest.interface = { displayName: 'Codeur Automation', shortDescription: 'CRM, devis, factures et campagnes', developerName: 'Sponge Theory', category: 'Productivity', capabilities: ['Read', 'Write'], defaultPrompt: ['Vérifie la connexion à Codeur.', 'Montre mon pipeline commercial.'] };
    await json(join(target, '.codex-plugin/plugin.json'), manifest);
    await json(join(target, '.mcp.json'), { mcpServers: { 'codeur-automation': { command: 'node', args: ['server.cjs'], cwd: '.', env: { CODEUR_CLIENT: 'codex' }, env_vars: ['CODEUR_URL', 'CODEUR_API_KEY', 'CODEUR_OUTPUT_DIR', 'CODEUR_READ_ONLY', 'CODEUR_CONFIG_PATH', 'CODEUR_TIMEOUT_SECONDS'], startup_timeout_sec: 20, tool_timeout_sec: 30 } } });
  } else {
    manifest.userConfig = {
      api_key: { type: 'string', title: 'Clé API Codeur', description: 'Clé codeur_mcp_… créée dans Codeur → Paramètres → Accès MCP. Laisser vide pour utiliser la configuration du trousseau dédiée à Claude Code.', sensitive: true, required: false },
      url: { type: 'string', title: 'URL de Codeur', description: 'URL HTTPS. Laisser vide pour utiliser la configuration locale ou https://codeur.sponge-theory.dev.', default: '' },
    };
    await json(join(target, '.claude-plugin/plugin.json'), manifest);
    await json(join(target, '.mcp.json'), { mcpServers: { 'codeur-automation': { command: 'node', args: ['${CLAUDE_PLUGIN_ROOT}/server.cjs'], env: { CODEUR_CLIENT: 'claude-code', CODEUR_URL: '${user_config.url}', CODEUR_API_KEY: '${user_config.api_key}' } } } });
  }
}
await json(join(dist, '.claude-plugin/marketplace.json'), { name: 'codeur-local', owner: author, plugins: [{ name: 'codeur', source: './plugins/codeur', version: pkg.version, description: pkg.description }] });
await json(join(dist, '.agents/plugins/marketplace.json'), { name: 'codeur-local', interface: { displayName: 'Codeur Automation (local)' }, plugins: [{ name: 'codeur-codex', source: { source: 'local', path: './plugins/codeur-codex' }, policy: { installation: 'AVAILABLE', authentication: 'ON_INSTALL' }, category: 'Productivity' }] });

const desktop = join(dist, 'desktop');
await mkdir(desktop, { recursive: true });
await cp(join(dist, 'server.cjs'), join(desktop, 'server.cjs'));
await cp(join(root, 'native/keychain-helper'), join(desktop, 'native/keychain-helper'));
await cp(join(dist, 'THIRD_PARTY_NOTICES.txt'), join(desktop, 'THIRD_PARTY_NOTICES.txt'));
await cp(join(root, 'README.md'), join(desktop, 'README.md'));
const manifest = JSON.parse(await readFile(join(root, 'packaging/manifest.json'), 'utf8'));
manifest.version = pkg.version;
manifest.tools = TOOLS.map(({ name, description }) => ({ name, description }));
await json(join(desktop, 'manifest.json'), manifest);
const cli = join(root, 'node_modules/@anthropic-ai/mcpb/dist/cli/cli.js');
execFileSync(process.execPath, [cli, 'validate', join(desktop, 'manifest.json')], { stdio: 'inherit' });
if (process.argv.includes('--pack')) {
  const artifact = join(dist, `codeur-automation-${pkg.version}.mcpb`);
  // Pack only these known files, never leftover files in a user's build folder.
  const staging = await mkdtemp(join(dist, '.mcpb-'));
  try {
    for (const name of ['manifest.json', 'server.cjs', 'README.md', 'THIRD_PARTY_NOTICES.txt', 'native/keychain-helper']) await cp(join(desktop, name), join(staging, name));
    execFileSync(process.execPath, [cli, 'pack', staging, artifact], { stdio: 'inherit' });
  } finally { await rm(staging, { recursive: true, force: true }); }
  const checksum = createHash('sha256').update(await readFile(artifact)).digest('hex');
  await writeFile(`${artifact}.sha256`, `${checksum}  ${artifact.split('/').at(-1)}\n`);
}
process.stdout.write(`Built Codex, Claude Code and Claude Desktop packages in ${dist}\n`);
