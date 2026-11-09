import { open, mkdir, writeFile } from 'node:fs/promises';
import { basename, extname, isAbsolute, join } from 'node:path';
import { randomUUID, createHash } from 'node:crypto';
import { validateUrl } from './config.mjs';

const MAX_BYTES = 32 * 1024 * 1024;
const MIME = { '.pdf': 'application/pdf', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.csv': 'text/csv', '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' };

export class ApiError extends Error {
  constructor(message, status, uncertain = false) {
    super(message); this.status = status; this.uncertain = uncertain;
  }
}

export async function readLimited(response, maximum = MAX_BYTES) {
  if (Number(response.headers.get('content-length')) > maximum) {
    await response.body?.cancel();
    throw new Error(`Response exceeds ${maximum} bytes.`);
  }
  const chunks = []; let size = 0;
  if (response.body) {
    for await (const chunk of response.body) {
      size += chunk.length;
      if (size > maximum) throw new Error(`Response exceeds ${maximum} bytes.`);
      chunks.push(chunk);
    }
  }
  return Buffer.concat(chunks);
}

async function uploadFile(value) {
  let bytes, filename, mime;
  if (value.path) {
    if (!isAbsolute(value.path)) throw new Error('Upload paths must be absolute paths on this computer.');
    const file = await open(value.path, 'r');
    try {
      const info = await file.stat();
      if (!info.isFile() || info.size > MAX_BYTES) throw new Error('Upload must be a regular file, at most 32 MiB.');
      // A bounded read also protects against a file growing after stat().
      bytes = Buffer.alloc(info.size + 1);
      let total = 0;
      while (total < bytes.length) {
        const { bytesRead } = await file.read(bytes, total, bytes.length - total, total);
        if (!bytesRead) break;
        total += bytesRead;
      }
      if (total !== info.size) throw new Error('Upload changed while it was being read.');
      bytes = bytes.subarray(0, total);
    } finally { await file.close(); }
    filename = basename(value.path);
    mime = MIME[extname(filename).toLowerCase()];
  } else {
    if (value.base64.length > Math.ceil(MAX_BYTES / 3) * 4) throw new Error('Upload is larger than 32 MiB.');
    bytes = Buffer.from(value.base64, 'base64');
    if (bytes.length > MAX_BYTES || bytes.toString('base64') !== value.base64) throw new Error('Invalid base64 upload or file larger than 32 MiB.');
    filename = basename(value.filename.replaceAll('\\', '/'));
    mime = value.content_type || MIME[extname(filename).toLowerCase()];
  }
  return { blob: new Blob([bytes], { type: mime || 'application/octet-stream' }), filename };
}

export class CodeurClient {
  constructor(config, fetchImpl = fetch) {
    this.config = { ...config, baseUrl: validateUrl(config.baseUrl) };
    this.fetch = fetchImpl;
  }

  redact(value) {
    if (typeof value === 'string') {
      for (const secret of [this.config.apiKey]) {
        if (secret) value = value.replaceAll(secret, '[redacted]');
      }
      return value;
    }
    if (Array.isArray(value)) return value.map(item => this.redact(item));
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, /password|secret|api[_-]?key|authorization|auth_session|access_token/i.test(key) ? '[redacted]' : this.redact(item)]));
    return value;
  }

  async raw(path, init = {}) {
    if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Invalid API path.');
    let response;
    try {
      response = await this.fetch(this.config.baseUrl + path, { ...init, redirect: 'manual', signal: AbortSignal.timeout(this.config.timeoutMs) });
    } catch {
      throw new ApiError('Connection failed or timed out. The operation may still be running on the application; inspect its state before retrying.', undefined, init.method && init.method !== 'GET');
    }
    if (response.status >= 300 && response.status < 400) {
      await response.body?.cancel();
      throw new ApiError('API redirected the request. Check CODEUR_URL and authentication; redirects are not followed.', response.status);
    }
    return response;
  }

  async request(path, init = {}) {
    if (!this.config.apiKey && path !== '/api/health') throw new ApiError('Configure a Codeur API key from Settings → Accès MCP, using the extension’s sensitive field or macOS setup.', 401);
    const response = await this.raw(path, { ...init, headers: { ...init.headers, ...(this.config.apiKey ? { Authorization: `Bearer ${this.config.apiKey}` } : {}) } });
    if (response.status === 401) {
      await response.body?.cancel();
      throw new ApiError('Codeur API key invalid, expired or revoked. Create a new key in the application settings and update the client configuration.', 401);
    }
    if (!response.ok) {
      const bytes = await readLimited(response);
      let detail;
      try { detail = JSON.parse(bytes.toString('utf8')).detail; } catch { /* Do not echo HTML or proxy output. */ }
      if (Array.isArray(detail)) detail = detail.map(({ loc, msg }) => ({ loc, msg }));
      throw new ApiError(`API HTTP ${response.status}${detail ? `: ${JSON.stringify(this.redact(detail)).slice(0, 3000)}` : ''}`, response.status, response.status >= 500 && init.method !== 'GET');
    }
    return response;
  }

  async execute(op, parameters) {
    let path = op.path.replace(/\{([^}]+)\}/g, (_, key) => {
      const value = String(parameters.path?.[key]);
      if (!/^[A-Za-z0-9_.-]+$/.test(value) || ['.', '..'].includes(value)) throw new Error(`Invalid path parameter: ${key}`);
      return encodeURIComponent(value);
    });
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(parameters.query || {})) {
      if (value === null || value === undefined) continue;
      for (const item of Array.isArray(value) ? value : [value]) query.append(key, String(item));
    }
    if (query.size) path += `?${query}`;
    const init = { method: op.method, headers: { Accept: '*/*' } };
    if (parameters.body !== undefined) {
      if (op.content_type === 'multipart/form-data') {
        const form = new FormData();
        for (const [key, value] of Object.entries(parameters.body)) {
          if (value === null || value === undefined) continue;
          if (typeof value === 'object' && !Array.isArray(value) && ('path' in value || 'base64' in value)) {
            const file = await uploadFile(value);
            form.append(key, file.blob, file.filename);
          } else form.append(key, typeof value === 'object' ? JSON.stringify(value) : String(value));
        }
        init.body = form;
      } else {
        init.headers['Content-Type'] = 'application/json';
        init.body = JSON.stringify(parameters.body);
      }
    }
    try {
      const response = await this.request(path, init);
      const bytes = await readLimited(response);
      const contentType = response.headers.get('content-type') || '';
      if (!bytes.length) return { status: response.status };
      if (contentType.includes('application/json')) {
        try { return this.redact(JSON.parse(bytes.toString('utf8'))); }
        catch { throw new Error('Cannot decode the API JSON response. Check the record before retrying a write.'); }
      }
      // Exports are written locally, never injected as enormous base64 tool output.
      let filename = response.headers.get('content-disposition')?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
      if (filename) { try { filename = decodeURIComponent(filename); } catch { filename = undefined; } }
      filename ||= response.headers.get('content-disposition')?.match(/filename="?([^";]+)/i)?.[1];
      const mediaType = contentType.split(';')[0].trim();
      const extension = Object.entries(MIME).find(([, mime]) => mime === mediaType)?.[0]
        || ({ 'image/svg+xml': '.svg', 'image/webp': '.webp', 'text/html': '.html', 'text/plain': '.txt' })[mediaType] || '.bin';
      filename ||= op.id + extension;
      filename = basename(filename.replaceAll('\\', '/')).replace(/[^\p{L}\p{N}._-]/gu, '_').slice(-150) || 'export';
      await mkdir(this.config.outputDir, { recursive: true, mode: 0o700 });
      const filePath = join(this.config.outputDir, `${randomUUID()}-${filename}`);
      await writeFile(filePath, bytes, { flag: 'wx', mode: 0o600 });
      return { file: filePath, filename, content_type: contentType, size: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
    } catch (error) {
      if (op.access === 'write' && (!error.status || error.status >= 500)) error.uncertain = true;
      throw error;
    }
  }
}
