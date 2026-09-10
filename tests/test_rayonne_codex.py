"""Boundary tests for the Codex adapter; no Keychain or external API access."""
import importlib.util
import json
from pathlib import Path
import sys
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'plugins/rayonne-codex/scripts'


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    modules = {}
    for name in ('connection', 'claude_credentials', 'configure', 'launch'):
        spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        modules[name] = module
    monkeypatch.setattr(modules['connection'], 'directory', lambda: tmp_path)
    monkeypatch.setattr(modules['configure'], 'directory', lambda: tmp_path)
    for name in ('RAYONNE_API_KEY', 'RAYONNE_API_URL', 'RAYONNE_READ_ONLY'):
        monkeypatch.setenv(name, '')
        monkeypatch.delenv(name)
    return modules


class Store:
    def __init__(self):
        self.value = None
    def read(self, name):
        return self.value
    def write(self, name, value):
        self.value = value
    def delete(self, name):
        self.value = None


def test_profile_contains_reference_not_secret(adapter, tmp_path):
    store = Store()
    adapter['configure'].save('https://rayonne.example', 'rk_test_only', store,
                              verify=lambda *args: None, read_only=True)
    path = tmp_path / 'connection.json'
    assert 'rk_test_only' not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600
    assert adapter['connection'].load_profile()['read_only'] is True
    assert store.value == 'rk_test_only'


def test_failed_probe_does_not_save(adapter, tmp_path):
    store = Store()
    def fail(*args):
        raise adapter['connection'].SetupError('Failed')
    with pytest.raises(adapter['connection'].SetupError):
        adapter['configure'].save('https://rayonne.example', 'rk_test_only', store, verify=fail)
    assert store.value is None
    assert not (tmp_path / 'connection.json').exists()


def test_failed_profile_write_restores_key(adapter, monkeypatch):
    store = Store()
    store.value = 'rk_previous'
    def fail(*args):
        raise OSError('disk failure')
    monkeypatch.setattr(adapter['configure'], 'atomic_write', fail)
    with pytest.raises(OSError):
        adapter['configure'].save('https://rayonne.example', 'rk_new', store, verify=lambda *a: None)
    assert store.value == 'rk_previous'


@pytest.mark.parametrize('url', ['http://example.com', 'https://user:pass@example.com',
    'https://example.com?key=secret', 'https://example.com/api', 'https://example.com/#secret'])
def test_reject_unsafe_origin(adapter, url):
    with pytest.raises(adapter['connection'].SetupError):
        adapter['connection'].normalize_instance(url)


def test_partial_environment_never_uses_stored_key(adapter, monkeypatch):
    monkeypatch.setenv('RAYONNE_API_URL', 'https://another.example')
    with pytest.raises(adapter['connection'].SetupError):
        adapter['launch'].configure_environment()


def test_launch_preserves_read_only(adapter, monkeypatch):
    import os
    launch = adapter['launch']
    monkeypatch.setattr(launch, 'load_profile', lambda: {'instance_url': 'https://rayonne.example', 'credential': {}, 'read_only': True})
    monkeypatch.setattr(launch, 'read_secret', lambda source: 'rk_test_only')
    launch.configure_environment()
    assert os.environ['RAYONNE_READ_ONLY'] == 'true'
    assert os.environ['RAYONNE_API_KEY'] == 'rk_test_only'


def test_claude_reference_never_written(adapter, tmp_path):
    class NoWrites(Store):
        def write(self, *args):
            raise AssertionError('must not write Claude credential')
    source = {'kind': 'claude', 'service': 'Claude Code-credentials', 'account': 'test', 'plugin_id': 'rayonne@sponge-theory'}
    adapter['configure'].save('https://rayonne.example', 'rk_test_only', NoWrites(), source, verify=lambda *a: None)
    assert json.loads((tmp_path / 'connection.json').read_text())['credential'] == source
