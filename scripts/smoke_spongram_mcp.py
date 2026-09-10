#!/usr/bin/env python3
"""Isolated Codex HTTP/header-helper smoke. Uses synthetic auth on loopback only."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/spongram-codex/scripts'))
import codex_config
from connection import atomic_write, directory


def run(binary):
    methods = []
    invalid = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(405)
            self.end_headers()

        def do_POST(self):
            rpc = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if (self.headers.get('Authorization') != 'Bearer synthetic-mcp-smoke'
                    or self.headers.get('X-Spongram-Client') != 'codex'):
                invalid.append(True)
                self.send_response(401)
                self.end_headers()
                return
            method = rpc['method']
            methods.append(method)
            if 'id' not in rpc:
                self.send_response(202)
                self.end_headers()
                return
            if method == 'initialize':
                result = {'protocolVersion': rpc['params']['protocolVersion'],
                          'capabilities': {'tools': {}},
                          'serverInfo': {'name': 'spongram-test', 'version': '1'}}
            elif method == 'tools/list':
                result = {'tools': [{'name': 'get_status', 'description': 'Synthetic test status',
                                     'inputSchema': {'type': 'object', 'properties': {}}}]}
            else:
                result = {}
            body = json.dumps({'jsonrpc': '2.0', 'id': rpc['id'], 'result': result}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with tempfile.TemporaryDirectory(prefix='spongram-mcp-runtime-') as home:
        with patch.dict(os.environ, {'HOME': home, 'CODEX_HOME': home + '/.codex'}), \
                patch.object(codex_config, 'executable', return_value=binary):
            Path(home + '/.codex').mkdir()
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                atomic_write(directory()/'runtime/auth_headers.py',
                             b'import json\nprint(json.dumps({"Authorization":"Bearer synthetic-mcp-smoke"}))\n')
                config = codex_config.server_config('https://example.test', 'test-account')
                # Plain HTTP is restricted to this synthetic loopback fixture.
                config['url'] = f'http://127.0.0.1:{server.server_port}/mcp'
                with codex_config.CodexConfig() as client:
                    client.write(config)
                with codex_config.CodexConfig() as client:
                    result = client.request('mcpServerStatus/list', {})
                    assert any(row['name'] == 'spongram' and row.get('tools') for row in result['data'])
                assert not invalid
                assert 'initialize' in methods and 'tools/list' in methods
            finally:
                server.shutdown()
                server.server_close()
    print(Path(binary).name + ': actual Codex HTTP MCP + header helper + tools discovery OK')


if __name__ == '__main__':
    run(codex_config.executable())
    app = '/Applications/ChatGPT.app/Contents/Resources/codex'
    if Path(app).exists():
        run(app)
