"""Initialize the Codeur helper once. Ordinary releases only verify its identity."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
binary = ROOT / "native/keychain-helper"
identity_file = ROOT / "src/keychain-identity.json"
args = argparse.ArgumentParser()
args.add_argument("--init", action="store_true")
options = args.parse_args()
if options.init:
    if binary.exists() or identity_file.exists():
        raise SystemExit("Preserve the released helper identity; a native change requires a new versioned path and explicit migration.")
    with tempfile.TemporaryDirectory(prefix="codeur-native-") as tmp:
        output = Path(tmp) / "keychain-helper"
        subprocess.run(["xcrun", "clang", "-arch", "arm64", "-arch", "x86_64", "-mmacosx-version-min=11.0", "-Os", "-fobjc-arc", "-Wno-deprecated-declarations", "-framework", "Foundation", "-framework", "Security", str(ROOT / "native/keychain-helper.m"), "-o", str(output)], check=True)
        subprocess.run(["codesign", "--force", "--sign", "-", "--identifier", "ai.sponge-theory.codeur-keychain.v1", str(output)], check=True)
        binary.write_bytes(output.read_bytes())
        binary.chmod(0o755)
        identity_file.write_text(json.dumps({"sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "version": "v1"}, indent=2) + "\n")
identity = json.loads(identity_file.read_text())
if hashlib.sha256(binary.read_bytes()).hexdigest() != identity["sha256"]:
    raise SystemExit("Native helper identity mismatch")
subprocess.run(["codesign", "--verify", "--strict", str(binary)], check=True)
print("Codeur native helper identity verified")
