import Ajv from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import data from './catalogue.json' with { type: 'json' };

const ajv = new Ajv({ strict: false, allErrors: true });
addFormats(ajv);
const fileSchema = {
  oneOf: [
    { type: 'object', properties: { path: { type: 'string', description: 'Absolute path on this computer.' } }, required: ['path'], additionalProperties: false },
    { type: 'object', properties: { base64: { type: 'string' }, filename: { type: 'string' }, content_type: { type: 'string' } }, required: ['base64', 'filename'], additionalProperties: false },
  ],
};

function adaptFiles(value) {
  if (Array.isArray(value)) return value.map(adaptFiles);
  if (!value || typeof value !== 'object') return value;
  if (value.format === 'binary') return fileSchema;
  return Object.fromEntries(Object.entries(value).map(([key, child]) => [key, adaptFiles(child)]));
}

export const operations = data.operations.map(op => ({ ...op, input_schema: adaptFiles(op.input_schema) }));
const byId = new Map(operations.map(op => [op.id, op]));
const validators = new Map();

export function operation(id) {
  const op = byId.get(id);
  if (!op) throw new Error(`Unknown operation: ${id}. Use codeur_search_operations.`);
  return op;
}

export function validateParameters(op, parameters) {
  if (!validators.has(op.id)) validators.set(op.id, ajv.compile(op.input_schema));
  const validate = validators.get(op.id);
  if (!validate(parameters)) {
    // Never echo values: requests can include customer data and provider credentials.
    throw new Error(`Invalid parameters: ${validate.errors.slice(0, 8).map(e => `${e.instancePath || '/'} ${e.message}`).join('; ')}. Use codeur_describe_operation.`);
  }
}

const fold = text => String(text).normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
export function searchOperations({ query = '', domain, limit = 20, offset = 0 } = {}) {
  const words = fold(query).split(/\s+/).filter(Boolean);
  const matches = operations.filter(op => !domain || op.domain === domain).map(op => {
    const haystack = fold(`${op.id} ${op.summary} ${op.description} ${op.keywords}`);
    return { op, score: words.reduce((n, word) => n + (haystack.includes(word) ? 1 : 0), 0) };
  }).filter(item => !words.length || item.score > 0).sort((a, b) => b.score - a.score || a.op.id.localeCompare(b.op.id));
  return {
    total: matches.length, offset,
    domains: [...new Set(operations.map(op => op.domain))],
    operations: matches.slice(offset, offset + limit).map(({ op }) => ({
      id: op.id, domain: op.domain, summary: op.summary,
      tool: `codeur_${op.access}`,
      uploads: op.content_type === 'multipart/form-data',
      ...(op.business_effects_on_read ? { note: 'This API read can expire quotes or refresh tracking; use codeur_write.' } : {}),
    })),
    next_offset: offset + limit < matches.length ? offset + limit : null,
  };
}

export function describeOperation(id) {
  const op = operation(id);
  return { ...op, tool: `codeur_${op.access}`,
    result: 'JSON result, downloaded file metadata, or a job_id to follow with codeur_job_status.',
    ...(op.content_type === 'multipart/form-data' ? { file_inputs: 'Use body.<file field> = {path: absolute local path} or {base64, filename, content_type}. Other form fields stay in body.' } : {}),
  };
}
