#!/usr/bin/env python3
"""Vendor the canonical SPT MCP bundle into its Codex adapter."""
import argparse
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spt_models_checkout', type=Path)
    args = parser.parse_args()
    source = args.spt_models_checkout / 'mcp-bundle'
    target = Path(__file__).resolve().parents[1] / 'plugins/spt-models-codex'
    version = json.loads((source / 'manifest.json').read_text())['version']
    files = ['main.py', 'spt_client.py', 'guide.md', '__init__.py']
    for name in files:
        if not (source / 'server' / name).is_file():
            raise SystemExit(f'Missing source server file: {name}')
    for name in files:
        shutil.copy2(source / 'server' / name, target / 'server' / name)
    shutil.copy2(source / 'pyproject.toml', target / 'pyproject.toml')
    manifest = target / '.codex-plugin/plugin.json'
    data = json.loads(manifest.read_text())
    data['version'] = version
    manifest.write_text(json.dumps(data, indent=2) + '\n')
    print(f'SPT Models Codex server synced to {version}; run uv lock and adapter tests.')


if __name__ == '__main__':
    main()
