"""Regression: a fresh MCP process must never open Claude's Keychain item."""
import importlib.util
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=['spongram', 'rayonne', 'spt-models'])
def adapter(request, monkeypatch, tmp_path):
    scripts = ROOT / 'plugins' / (request.param + '-codex') / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    modules = {}
    names = ['connection', 'claude_credentials']
    if request.param == 'spongram':
        names += ['check_connection', 'codex_config']
    for name in names + ['configure']:
        spec = importlib.util.spec_from_file_location(name, scripts / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        modules[name] = module
    for name in ('connection', 'configure'):
        monkeypatch.setattr(modules[name], 'directory', lambda: tmp_path)
    return request.param, modules


def test_runtime_rejects_legacy_without_touching_keychain(adapter, monkeypatch):
    plugin, modules = adapter
    connection = modules['connection']
    store = Mock()
    monkeypatch.setattr(connection, 'Keychain', store)
    source = {'kind': 'claude', 'service': 'Claude Code-credentials',
              'account': 'test-user', 'plugin_id': plugin + '@sponge-theory'}
    for _ in range(3):  # independent launches/auth refreshes must stay quiet
        with pytest.raises(connection.SetupError, match='[Mm]igrat'):
            connection.read_secret(source)
    store.assert_not_called()


def test_setup_imports_only_selected_key_into_owned_storage(adapter):
    plugin, modules = adapter
    store = Mock()
    store.read.return_value = None
    source = {'kind': 'claude', 'service': 'Claude Code-credentials',
              'account': 'test-user', 'plugin_id': plugin + '@sponge-theory'}
    args = ['https://example.test', 'rk_synthetic_test_only', store]
    if plugin == 'spongram':
        args.append(Mock())
    modules['configure'].save(*args, source=source, verify=Mock())
    profile = modules['connection'].load_profile()
    assert profile['credential']['kind'] == plugin
    assert profile['credential']['storage'] == 'native-v1'
    store.write.assert_called_once_with(modules['connection'].account('https://example.test'), 'rk_synthetic_test_only')


def test_old_codex_entry_also_requires_explicit_migration(adapter, monkeypatch):
    plugin, modules = adapter
    connection = modules['connection']
    store = Mock()
    monkeypatch.setattr(connection, 'LegacyKeychain', store)
    with pytest.raises(connection.SetupError, match='migration'):
        connection.read_secret({'kind': plugin, 'account': 'old-account'})
    store.assert_not_called()


def test_runtime_reads_only_native_owned_entry(adapter, monkeypatch):
    plugin, modules = adapter
    connection = modules['connection']
    native = Mock(return_value='rk_synthetic_test_only')
    monkeypatch.setattr(connection.native_keychain, 'perform', native)
    source = connection.owned_source('endpoint-hash')
    assert connection.read_secret(source) == 'rk_synthetic_test_only'
    native.assert_called_once_with('ai.sponge-theory.' + plugin + '.codex.v2',
                                   'read', 'endpoint-hash', None, interactive=False)


def test_migration_refresh_keeps_same_reference(adapter):
    plugin, modules = adapter
    store = Mock()
    store.read.return_value = 'rk_synthetic_test_only'
    args = ['https://example.test', 'rk_synthetic_test_only', store]
    if plugin == 'spongram':
        args.append(Mock())
    save = modules['configure'].save
    save(*args, verify=Mock())
    before = modules['connection'].load_profile()
    save(*args, source=before['credential'], verify=Mock())
    assert modules['connection'].load_profile() == before


def test_all_plugins_package_identical_native_identity():
    import hashlib
    canonical = ROOT / 'shared/codex-keychain/keychain-helper'
    digest = hashlib.sha256(canonical.read_bytes()).hexdigest()
    for plugin in ('spongram', 'rayonne', 'spt-models'):
        scripts = ROOT / 'plugins' / (plugin + '-codex') / 'scripts'
        assert (scripts / 'keychain-helper').read_bytes() == canonical.read_bytes()
        assert digest in (scripts / 'native_keychain.py').read_text()


def test_spt_bundled_server_matches_released_server():
    for source in (ROOT / 'plugins/spt-models/server').iterdir():
        if source.is_file():
            assert source.read_bytes() == (ROOT / 'plugins/spt-models-codex/server' / source.name).read_bytes()
