"""Adapter tests; no real credentials or network calls."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/spt-models-codex/scripts'
# Run this file separately: the Spongram tests also import a module named connection.
sys.path.insert(0, str(SCRIPTS))
import connection
import configure
import claude_credentials
import launch


class AdapterTests(unittest.TestCase):
    def test_origin_validation(self):
        for url in ['http://host', 'https://host/v1', 'https://u:p@host', 'https://host?key=x', 'https://host/#x']:
            with self.subTest(url=url), self.assertRaises(connection.SetupError):
                connection.normalize_instance(url)
        self.assertEqual(connection.normalize_instance('https://models.example/'), 'https://models.example')

    def test_failed_probe_does_not_save(self):
        store = Mock()
        with self.assertRaises(connection.SetupError):
            configure.save('https://models.example', 'test-key', store,
                           verify=Mock(side_effect=connection.SetupError('Unavailable')))
        store.write.assert_not_called()

    def test_profile_has_reference_only(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(configure, 'directory', return_value=Path(tmp)):
            store = Mock()
            store.read.return_value = None
            configure.save('https://models.example', 'test-key', store, verify=Mock())
            data = (Path(tmp) / 'connection.json').read_text()
            self.assertNotIn('test-key', data)
            self.assertEqual(json.loads(data)['credential']['kind'], 'spt-models')
            self.assertEqual((Path(tmp) / 'connection.json').stat().st_mode & 0o777, 0o600)

    def test_save_rolls_back_key_on_disk_failure(self):
        store = Mock()
        store.read.return_value = 'old-key'
        with patch.object(configure, 'atomic_write', side_effect=OSError()), self.assertRaises(OSError):
            configure.save('https://models.example', 'new-key', store, verify=Mock())
        self.assertEqual(store.write.call_args.args[1], 'old-key')

    def test_claude_reference_does_not_write_store(self):
        store = Mock()
        with patch.object(configure, 'atomic_write'):
            configure.save('https://models.example', 'test-key', store,
                           source={'kind': 'claude'}, verify=Mock())
        store.write.assert_not_called()

    def test_only_selected_plugin_key_is_read(self):
        store = Mock()
        store.read.return_value = json.dumps({'pluginSecrets': {
            'spt-models@sponge-theory': {'spt_api_key': 'expected'},
            'spongram@sponge-theory': {'brain_key': 'unrelated'}}})
        with patch.object(connection, 'Keychain', return_value=store):
            key = connection.read_secret({'kind': 'claude', 'service': 'Claude Code-credentials',
                                          'account': 'test', 'plugin_id': 'spt-models@sponge-theory'})
        self.assertEqual(key, 'expected')

    def test_unrelated_plugin_reference_is_rejected(self):
        with patch.object(connection, 'Keychain') as store, self.assertRaises(connection.SetupError):
            connection.read_secret({'kind': 'claude', 'service': 'Claude Code-credentials',
                                    'account': 'test', 'plugin_id': 'other'})
        store.assert_not_called()

    def test_partial_environment_does_not_mix_credentials(self):
        with patch.dict(os.environ, {'SPT_BASE_URL': 'https://other.example'}, clear=True), self.assertRaises(connection.SetupError):
            launch.configure_environment()

    def test_environment_pair_bypasses_keychain(self):
        with patch.dict(os.environ, {'SPT_BASE_URL': 'https://models.example', 'SPT_API_KEY': 'test-key'}, clear=True), patch.object(launch, 'load_profile') as load:
            launch.configure_environment()
            self.assertEqual(os.environ['SPT_REQUEST_TIMEOUT'], '3900')
            load.assert_not_called()

    def test_claude_manifest_default_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'plugins').mkdir()
            installed = root / 'installed'
            (installed / '.claude-plugin').mkdir(parents=True)
            (installed / '.claude-plugin/plugin.json').write_text(json.dumps({'userConfig': {'spt_base_url': {'default': 'https://models.example'}}}))
            (root / 'plugins/installed_plugins.json').write_text(json.dumps({'plugins': {'spt-models@sponge-theory': [{'scope': 'user', 'installPath': str(installed)}]}}))
            with patch.dict(os.environ, {'CLAUDE_CONFIG_DIR': tmp}):
                profiles = claude_credentials.profiles()
            self.assertEqual(profiles[0]['instance_url'], 'https://models.example')


if __name__ == '__main__':
    unittest.main()
