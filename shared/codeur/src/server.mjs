import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import Ajv from 'ajv/dist/2020.js';
import { loadConfig } from './config.mjs';
import { CodeurClient } from './client.mjs';
import { CodeurService, INSTRUCTIONS, TOOLS } from './service.mjs';
import { setup } from './setup.mjs';

async function main() {
  if (process.argv.includes('--client')) process.env.CODEUR_CLIENT = process.argv[process.argv.indexOf('--client') + 1];
  if (process.argv.includes('--setup')) return setup();
  const client = new CodeurClient(loadConfig());
  const service = new CodeurService(client);
  const ajv = new Ajv({ strict: false });
  const validators = new Map(TOOLS.map(tool => [tool.name, ajv.compile(tool.inputSchema)]));
  const server = new Server({ name: 'codeur-automation', version: '0.1.0' }, { capabilities: { tools: {} }, instructions: INSTRUCTIONS });
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));
  server.setRequestHandler(CallToolRequestSchema, async request => {
    try {
      const { name, arguments: args = {} } = request.params;
      const validate = validators.get(name);
      if (!validate || !validate(args)) throw new Error('Invalid tool arguments. Read the tool input schema.');
      const result = await service.call(name, args);
      return { content: [{ type: 'text', text: JSON.stringify(result) }], ...(result?.status === 'failed' || result?.status === 'uncertain' ? { isError: true } : {}) };
    } catch (error) {
      return { content: [{ type: 'text', text: JSON.stringify({ error: client.redact(error.message) }) }], isError: true };
    }
  });
  await server.connect(new StdioServerTransport());
}

main().catch(error => { process.stderr.write(`Codeur MCP: ${error.message}\n`); process.exitCode = 1; });
