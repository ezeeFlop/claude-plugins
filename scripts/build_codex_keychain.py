#!/usr/bin/env python3
"""Build once per native helper version; vendor identical bytes to all adapters.

Ordinary plugin releases use --check, NOT a rebuild. An identity-changing native
update requires a new helper path/service version and an explicit migration.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / 'shared/codex-keychain'
PLUGINS = ('spongram', 'rayonne', 'spt-models')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    binary = SHARED / 'keychain-helper'
    if args.build:
        if binary.exists():
            raise SystemExit('Refusing to replace a released helper identity; bump native protocol/path/service first')
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'keychain-helper'
            subprocess.run(['xcrun', 'clang', '-fobjc-arc', '-O2', '-arch', 'arm64', '-arch', 'x86_64',
                            '-mmacosx-version-min=11.0', '-framework', 'Foundation', '-framework', 'Security',
                            str(SHARED / 'keychain-helper.m'), '-o', str(output)], check=True)
            subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none',
                            '--identifier', 'ai.sponge-theory.codex-keychain.v1', str(output)], check=True)
            shutil.copy2(output, binary)
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    python = (SHARED / 'native_keychain.py').read_text().replace('BUILD_REQUIRED', digest).encode()
    for plugin in PLUGINS:
        scripts = ROOT / 'plugins' / (plugin + '-codex') / 'scripts'
        for name, data in [('native_keychain.py', python), ('keychain-helper', binary.read_bytes())]:
            target = scripts / name
            if args.check:
                if not target.exists() or target.read_bytes() != data:
                    raise SystemExit('Native Keychain drift: ' + str(target))
            else:
                target.write_bytes(data)
                target.chmod(0o755 if name == 'keychain-helper' else 0o644)
    print('Native Keychain parity OK' if args.check else 'Native Keychain vendored')


if __name__ == '__main__':
    main()
