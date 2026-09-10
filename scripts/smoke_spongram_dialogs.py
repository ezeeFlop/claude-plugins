#!/usr/bin/env python3
"""Manual macOS smoke: compile actual dialogs, then show an auto-closing test."""
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plugins/spongram-codex/scripts'))
from configure import ask, reuse_saved


def main():
    scripts = []
    with patch.object(subprocess, 'run', return_value=Mock(returncode=0, stdout='test')) as run:
        ask('test', secret=True)
        scripts.append(run.call_args.args[0][2])
        ask('test')
        scripts.append(run.call_args.args[0][2])
        reuse_saved()
        scripts.append(run.call_args.args[0][2])
    with tempfile.TemporaryDirectory() as tmp:
        for index, script in enumerate(scripts):
            result = subprocess.run(['/usr/bin/osacompile', '-o', str(Path(tmp)/f'{index}.scpt'), '-'],
                                    input=script, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr.strip())
    # Test only: close automatically without requesting any real credential.
    script = scripts[0].replace('default button "Continuer"',
                                'giving up after 2 default button "Continuer"')
    result = subprocess.run(['/usr/bin/osascript', '-e', script,
                             'Test Spongram : saisie masquée. Fermeture automatique dans 2 secondes.',
                             'synthetic-test-only'], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0 and result.stdout.strip() == 'synthetic-test-only'
    print('Native macOS dialogs compile; auto-closing masked-input test: OK.')


if __name__ == '__main__':
    main()
