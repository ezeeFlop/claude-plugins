#!/usr/bin/env python3
"""Preflight for the two Spongram adapters; does not commit, push or deploy."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads((ROOT / path).read_text())


def main():
    claude = read_json('plugins/spongram/.claude-plugin/plugin.json')
    codex = read_json('plugins/spongram-codex/.codex-plugin/plugin.json')
    market = read_json('.claude-plugin/marketplace.json')
    entry = next(p for p in market['plugins'] if p['name'] == 'spongram')
    version = claude['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Use a release version, without a local cachebuster')
    if codex['version'] != version or entry['version'] != version:
        raise ValueError('The two adapters and Claude marketplace must have matching versions')
    cm = read_json('.agents/plugins/marketplace.json')
    ce = next(p for p in cm['plugins'] if p['name'] == 'spongram-codex')
    if ce['source'] != {'source': 'local', 'path': './plugins/spongram-codex'}:
        raise ValueError('Unexpected Codex marketplace source')
    if (ROOT / 'plugins/spongram-codex/hooks').exists():
        raise ValueError('Codex must not package Claude hooks')
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_spongram.py'), '--check'], check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'),
                    '-p', 'test_spongram*.py'], check=True)
    for path in (ROOT / 'plugins/spongram/hooks').glob('*.sh'):
        subprocess.run(['bash', '-n', str(path)], check=True)

    # Scan the actual staged additions/updates without printing matched values.
    # This is a heuristic preflight; a human diff review is still required.
    names = subprocess.check_output(['git', 'diff', '--cached', '--name-only',
                                     '--diff-filter=ACMR', '-z'], cwd=ROOT).split(b'\0')
    patterns = [rb'spt_brain_[A-Za-z0-9_-]{20,}', rb'pypi-[A-Za-z0-9_-]{20,}',
                rb'gh[pousr]_[A-Za-z0-9]{20,}', rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                rb'Bearer [A-Za-z0-9_-]{30,}']
    count = 0
    for raw_name in names:
        if not raw_name:
            continue
        name = raw_name.decode()
        if '.env' in Path(name).suffixes or Path(name).name.startswith('.env'):
            raise ValueError('Environment file staged: ' + name)
        data = subprocess.check_output(['git', 'show', ':' + name], cwd=ROOT)
        if any(re.search(pattern, data) for pattern in patterns):
            raise ValueError('Possible credential staged in ' + name + ' (value redacted)')
        count += 1
    print(f'Spongram {version}: preflight OK; {count} staged files scanned.')
    if not count:
        print('Stage the release files and rerun to scan the publication contents.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, StopIteration) as error:
        sys.exit(str(error))
