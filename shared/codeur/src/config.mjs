import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, resolve } from 'node:path';
import { keychain, validateApiKey } from './keychain.mjs';

export const DEFAULT_URL = 'https://codeur.sponge-theory.dev';
export const clientName = () => {
  const value = process.env.CODEUR_CLIENT || 'codex';
  if (!['codex', 'claude-code', 'desktop'].includes(value)) throw new Error('Invalid Codeur client.');
  return value;
};
export const configPath = () => process.env.CODEUR_CONFIG_PATH || join(homedir(), '.config', 'codeur-mcp', clientName(), 'connection.json');

export function validateUrl(value) {
  const url = new URL(value);
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(local && url.protocol === 'http:')) throw new Error('CODEUR_URL must use HTTPS (HTTP is supported on localhost).');
  if (url.username || url.password || url.search || url.hash) throw new Error('CODEUR_URL must not contain credentials, a query or a fragment.');
  return url.href.replace(/\/$/, '');
}

export function loadConfig(env = process.env) {
  let stored = {};
  try { stored = JSON.parse(readFileSync(configPath(), 'utf8')); }
  catch (error) { if (error.code !== 'ENOENT') throw new Error('Cannot read the Codeur MCP configuration.'); }
  const baseUrl = validateUrl(env.CODEUR_URL || stored.url || DEFAULT_URL);
  let apiKey = env.CODEUR_API_KEY || '';
  if (!apiKey && stored.storage === 'native-v1' && process.platform === 'darwin') {
    apiKey = keychain('read', baseUrl, clientName()) || '';
  }
  if (apiKey) validateApiKey(apiKey);
  const timeoutMs = Number(env.CODEUR_TIMEOUT_SECONDS || 1200) * 1000;
  if (!Number.isFinite(timeoutMs) || timeoutMs < 1000 || timeoutMs > 3600000) throw new Error('CODEUR_TIMEOUT_SECONDS must be between 1 and 3600.');
  return {
    baseUrl, apiKey, timeoutMs,
    outputDir: resolve(env.CODEUR_OUTPUT_DIR || stored.output_dir || join(homedir(), 'Downloads', 'Codeur')),
    readOnly: /^(true|1)$/i.test(env.CODEUR_READ_ONLY || ''),
  };
}
