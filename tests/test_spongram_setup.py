import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'plugins/spongram-codex/scripts'
sys.path.insert(0, str(SCRIPTS))
import connection
import configure
import codex_config
import claude_credentials


class Setup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='spongram-setup-test-')
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'HOME': self.temp.name, 'CODEX_HOME': self.temp.name + '/.codex',
                                         'CLAUDE_CONFIG_DIR': '', 'CLAUDE_SECURESTORAGE_CONFIG_DIR': ''})
        self.env.start()
        self.addCleanup(self.env.stop)
        Path(os.environ['CODEX_HOME']).mkdir()
        self.store = Mock()
        self.store.read.return_value = None
        self.config = Mock()
        self.instance = 'https://example.test'
        self.key = 'synthetic-test-only'

    def test_save_contains_no_key_and_runtime_survives_cache_changes(self):
        configure.save(self.instance, self.key, self.store, self.config, verify=Mock())
        profile = connection.load_profile()
        self.assertEqual(profile['instance_url'], self.instance)
        for path in connection.directory().rglob('*'):
            if path.is_file():
                self.assertNotIn(self.key.encode(), path.read_bytes())
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(self.key, str(self.config.write.call_args))
        self.assertNotIn(str(SCRIPTS), str(self.config.write.call_args))
        self.store.write.assert_called_once_with(connection.account(self.instance), self.key)

    def test_failed_connection_saves_nothing(self):
        with self.assertRaises(ValueError):
            configure.save(self.instance, self.key, self.store, self.config,
                           verify=Mock(side_effect=ValueError('failed')))
        self.store.write.assert_not_called()
        self.config.write.assert_not_called()
        self.assertFalse(connection.directory().exists())

    def test_failed_registration_restores_previous_profile_and_key(self):
        configure.save(self.instance, self.key, self.store, self.config, verify=Mock())
        before = (connection.directory() / 'connection.json').read_bytes()
        self.store.read.return_value = self.key
        self.config.write.side_effect = connection.SetupError('configuration changed concurrently')
        with self.assertRaises(connection.SetupError):
            configure.save(self.instance, 'replacement-test-only', self.store, self.config, verify=Mock())
        self.store.write.assert_called_with(connection.account(self.instance), self.key)
        self.assertEqual((connection.directory() / 'connection.json').read_bytes(), before)

    def test_claude_reference_does_not_copy_or_modify_any_key(self):
        source = {'kind': 'claude', 'service': 'Claude Code-credentials',
                  'account': 'test-user', 'plugin_id': 'spongram@sponge-theory'}
        configure.save(self.instance, self.key, self.store, self.config, verify=Mock(), source=source)
        self.store.read.assert_not_called()
        self.store.write.assert_not_called()
        self.store.delete.assert_not_called()
        self.assertEqual(connection.load_profile()['credential'], source)
        with patch.object(connection, 'Keychain') as keychain:
            keychain.return_value.read.return_value = json.dumps({
                'claudeAiOauth': {'accessToken': 'unrelated-secret'},
                'pluginSecrets': {'spongram@sponge-theory': {'brain_key': self.key},
                                  'other@plugin': {'brain_key': 'unrelated-plugin'}}})
            self.assertEqual(connection.credentials(), (self.instance + '/mcp', self.key))
            keychain.return_value.read.return_value = json.dumps({
                'pluginSecrets': {'spongram@sponge-theory': {'brain_key': 'rotated-test-only'}}})
            self.assertEqual(connection.credentials()[1], 'rotated-test-only')
            keychain.return_value.write.assert_not_called()

    def test_claude_discovery_only_reuses_same_instance(self):
        root = Path(self.temp.name) / '.claude'
        (root / 'plugins').mkdir(parents=True)
        (root / 'settings.json').write_text(json.dumps({'pluginConfigs': {
            'spongram@sponge-theory': {'options': {'instance_url': self.instance}},
            'unrelated': {'options': {'instance_url': 'https://other.test'}}}}))
        with patch.object(claude_credentials, 'read_secret', return_value=self.key) as read:
            self.assertIsNone(claude_credentials.find('https://different.test'))
            read.assert_not_called()
            source, key = claude_credentials.find(self.instance)
            self.assertEqual(key, self.key)
            self.assertEqual(source['plugin_id'], 'spongram@sponge-theory')
            self.assertEqual(source['service'], 'Claude Code-credentials')

    def test_cancel_and_terminal_without_user_tty(self):
        with patch.object(subprocess, 'run', return_value=Mock(returncode=1)):
            with self.assertRaises(connection.SetupError):
                configure.ask('test')
        with patch.object(sys.stdin, 'isatty', return_value=False):
            with self.assertRaises(connection.SetupError):
                configure.ask('secret', secret=True, terminal=True)
        self.assertFalse(connection.directory().exists())

    def test_hidden_answer_never_enters_command_arguments(self):
        with patch.object(subprocess, 'run', return_value=Mock(returncode=0, stdout=self.key+'\n')) as run:
            self.assertEqual(configure.ask('Brain key', secret=True), self.key)
            self.assertNotIn(self.key, str(run.call_args))
            self.assertIn('with hidden answer', str(run.call_args))

    def test_external_keychain_cannot_be_modified(self):
        if sys.platform != 'darwin':
            self.skipTest('macOS only')
        store = connection.Keychain('Claude Code-credentials')
        with self.assertRaises(connection.SetupError):
            store.write('test-user', self.key)
        with self.assertRaises(connection.SetupError):
            store.delete('test-user')

    def test_real_codex_config_api_preserves_other_settings_and_tool_policies(self):
        path = Path(os.environ['CODEX_HOME']) / 'config.toml'
        path.write_text('# Preserve this comment\nmodel = "gpt-5.4"\n[mcp_servers.other]\nurl = "https://other.test/mcp"\n')
        server = codex_config.server_config(self.instance, connection.account(self.instance))
        with codex_config.CodexConfig() as config:
            config.write(dict(server, disabled_tools=['clear_graph']))
        with codex_config.CodexConfig() as config:
            config.write(server)
        text = path.read_text()
        self.assertIn('Preserve this comment', text)
        self.assertIn('https://other.test/mcp', text)
        self.assertIn('clear_graph', text)
        self.assertNotIn('bearer_token_env_var', text)
        with codex_config.CodexConfig() as config:
            config.write(None)
        self.assertNotIn('[mcp_servers.spongram]', path.read_text())
        self.assertIn('[mcp_servers.other]', path.read_text())

    def test_real_codex_config_rejects_unrelated_existing_server(self):
        path = Path(os.environ['CODEX_HOME']) / 'config.toml'
        original = '[mcp_servers.spongram]\nurl = "https://other.test/mcp"\n'
        path.write_text(original)
        with self.assertRaises(connection.SetupError):
            with codex_config.CodexConfig():
                pass
        self.assertEqual(path.read_text(), original)

    def test_real_codex_concurrent_change_is_preserved(self):
        path = Path(os.environ['CODEX_HOME']) / 'config.toml'
        path.write_text('model = "gpt-5.4"\n')
        with codex_config.CodexConfig() as config:
            path.write_text('model = "gpt-5.5"\n# concurrent edit\n')
            with self.assertRaises(connection.SetupError):
                config.write(codex_config.server_config(self.instance, connection.account(self.instance)))
        self.assertIn('concurrent edit', path.read_text())
        self.assertNotIn('http_headers_helper', path.read_text())
