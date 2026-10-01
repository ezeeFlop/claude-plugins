"""Stable, locally signed native Keychain helper; never print its pipe output."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

# Filled by scripts/build_codex_keychain.py from the signed universal binary.
HELPER_SHA256 = "c1f611619d3b60c292abddb84302df699e736b2b5e205bac136ec2f253b967f1"


class NativeKeychainError(Exception):
    pass


def helper_path():
    return Path.home() / '.sponge-theory/codex-keychain/v1/spt-codex-keychain'


def verified(path):
    return (path.is_file() and not path.is_symlink()
            and path.stat().st_uid == os.getuid()
            and not path.stat().st_mode & 0o022
            and hashlib.sha256(path.read_bytes()).hexdigest() == HELPER_SHA256)


def install_helper():
    if sys.platform != 'darwin':
        raise NativeKeychainError('Secure Keychain setup requires macOS')
    path = helper_path()
    if verified(path):
        return
    if path.exists() or path.is_symlink():
        raise NativeKeychainError('Keychain helper differs from this release; preserve it and repair setup explicitly')
    source = Path(__file__).with_name('keychain-helper')
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != HELPER_SHA256:
        raise NativeKeychainError('Packaged Keychain helper is missing or corrupt; reinstall the plugin')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        os.fchmod(fd, 0o700)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(source.read_bytes())
        # Do not replace an identity created by a concurrent setup.
        try:
            os.link(temporary, path)
        except FileExistsError:
            if not verified(path):
                raise NativeKeychainError('Concurrent Keychain setup; retry') from None
    finally:
        os.unlink(temporary)


def perform(service, operation, account, value=None, *, interactive=False):
    path = helper_path()
    if not verified(path):
        raise NativeKeychainError('Keychain helper unavailable; run the plugin setup --migrate')
    command = [str(path)] + (['--interactive'] if interactive else [])
    request = {'service': service, 'operation': operation, 'account': account}
    if value is not None:
        request['value'] = value
    try:
        result = subprocess.run(command, input=json.dumps(request), capture_output=True,
                                text=True, timeout=120 if interactive else 10)
        if result.returncode:
            raise ValueError()
        reply = json.loads(result.stdout)
        status = reply['status']
        if status == -25300 and operation in ('read', 'delete'):
            return None
        if status:
            raise NativeKeychainError(f'Keychain unavailable (status {status}); unlock the login keychain and run setup --migrate')
        return reply.get('value')
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        raise NativeKeychainError('Native Keychain operation failed; run plugin setup --migrate') from None
