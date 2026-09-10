"""Use Codex's config API to preserve unrelated settings and concurrent edits."""
import json
import os
from pathlib import Path
import queue
import shlex
import shutil
import subprocess
import sys
import threading
import time
from connection import SetupError, directory


def executable():
    found = shutil.which("codex")
    if found:
        return found
    for app in ("ChatGPT", "Codex"):
        path = Path("/Applications") / (app + ".app/Contents/Resources/codex")
        if path.is_file():
            return str(path)
    raise SetupError("Codex executable not found; install or update Codex first")


def server_config(instance, credential_account):
    return {
        "url": instance + "/mcp",
        "http_headers_helper": shlex.join([
            str(Path(sys.executable).absolute()),
            str(directory() / "runtime" / "auth_headers.py"),
            json.dumps(credential_account if isinstance(credential_account, dict) else
                       {"kind": "spongram", "account": credential_account}, separators=(",", ":"))]),
        "http_headers": {"X-Spongram-Client": "codex"},
    }


def owned(server):
    try:
        args = shlex.split(server.get("http_headers_helper", ""))
        return len(args) == 3 and args[1] == str(directory() / "runtime" / "auth_headers.py")
    except ValueError:
        return False


class CodexConfig:
    def __enter__(self):
        self.process = subprocess.Popen(
            [executable(), "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, cwd=str(Path.home()))
        self.messages = queue.Queue()
        self.ident = 0

        def read():
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    pass
            self.messages.put(None)

        threading.Thread(target=read, daemon=True).start()
        try:
            self.request("initialize", {"clientInfo": {
                "name": "spongram-setup", "version": "0.5.1"}})
            self.process.stdin.write('{"method":"initialized"}\n')
            self.process.stdin.flush()
            result = self.request("config/read", {"includeLayers": True})
            target = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
            self.path, self.version, self.config = str(target.resolve()), None, {}
            for layer in result.get("layers") or []:
                name = layer["name"]
                if name["type"] == "user" and name.get("file") == self.path and not name.get("profile"):
                    self.version = layer["version"]
                    self.config = layer["config"]
            effective = result["config"].get("mcp_servers", {}).get("spongram")
            existing = self.config.get("mcp_servers", {}).get("spongram")
            if (existing and not owned(existing)) or (effective and not existing):
                raise SetupError("An existing spongram MCP configuration is not owned by this setup; it was preserved")
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def request(self, method, params):
        self.ident += 1
        self.process.stdin.write(json.dumps({"id": self.ident, "method": method, "params": params}) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + 25
        while True:
            try:
                message = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                raise SetupError("Codex configuration service timed out") from None
            if message is None:
                raise SetupError("Codex configuration service stopped")
            if message.get("id") == self.ident:
                if "error" in message:
                    raise SetupError("Codex rejected the configuration; update Codex or check managed settings")
                return message["result"]
            if time.monotonic() >= deadline:
                raise SetupError("Codex configuration service timed out")

    def write(self, server):
        previous = self.config.get("mcp_servers", {}).get("spongram", {})
        if server is not None:
            policies = {k: v for k, v in previous.items() if k in (
                "enabled", "enabled_tools", "disabled_tools", "tools", "default_tools_approval_mode")}
            server = {**policies, **server}
        self.request("config/value/write", {
            "filePath": self.path, "expectedVersion": self.version,
            "keyPath": "mcp_servers.spongram", "mergeStrategy": "replace", "value": server})

    def __exit__(self, *args):
        self.process.stdin.close()
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdout.close()
