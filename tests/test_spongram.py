import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / "plugins/spongram"
CODEX = ROOT / "plugins/spongram-codex"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


context = module("project_context", ROOT / "shared/spongram/lib/project_context.py")
config = module("configure", CODEX / "scripts/configure.py")
check = module("check_connection", CODEX / "scripts/check_connection.py")


class SharedCore(unittest.TestCase):
    def test_generated_plugins_are_current(self):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_spongram.py"), "--check"], check=True
        )

    def test_project_identity_and_provenance_across_clients(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.dict(os.environ, {"SPONGRAM_PROJECT": ""}),
        ):
            repo = Path(temp) / "My_Project.v2"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "remote",
                    "add",
                    "origin",
                    "git@github.com:team/My_Project.v2.git",
                ],
                check=True,
            )
            a = context.context(repo, "codex")
            b = context.context(repo, "claude-code")
            self.assertEqual(a["project_slug"], "my-project-v2")
            self.assertEqual(a["repo"], "team/My_Project.v2")
            self.assertEqual(
                a["source_description"].replace("client=codex", "client=claude-code"),
                b["source_description"],
            )
            with patch.dict(os.environ, {"SPONGRAM_PROJECT": "legacy-name"}):
                self.assertEqual(context.context(repo, "codex")["project_slug"], "legacy-name")
            with patch.dict(os.environ, {"SPONGRAM_PROJECT": "x client=evil"}):
                with self.assertRaises(ValueError):
                    context.context(repo, "codex")

    def test_claude_sessionstart_runs_without_credentials(self):
        with tempfile.TemporaryDirectory() as temp:
            env = dict(
                os.environ,
                HOME=temp,
                CLAUDE_PLUGIN_OPTION_INSTANCE_URL="",
                CLAUDE_PLUGIN_OPTION_BRAIN_KEY="",
                SPONGRAM_PROJECT="shared-demo",
            )
            result = subprocess.run(
                ["bash", str(CLAUDE / "hooks/recall-on-start.sh")],
                input=json.dumps({"source": "startup", "cwd": temp}),
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            output = json.loads(result.stdout)["hookSpecificOutput"]
            self.assertEqual(output["hookEventName"], "SessionStart")
            self.assertIn("project=shared-demo", output["additionalContext"])
            self.assertIn("client=claude-code", output["additionalContext"])
            self.assertNotIn("THIS SYSTEM IS DISABLED", output["additionalContext"])

    def test_claude_capture_uses_shared_project_and_keeps_off_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            transcript = Path(temp) / "transcript.jsonl"
            transcript.write_text(
                "\n".join(
                    json.dumps({"type": "user", "message": {"content": "A durable decision"}})
                    for _ in range(6)
                )
            )
            # Execute only the capture's embedded Python payload builder: no network/background process.
            script = (CLAUDE / "hooks/memory-capture.sh").read_text()
            code = script.split("<<'PY' 2>/dev/null\n", 1)[1].split("\nPY\n", 1)[0]
            inp = json.dumps(
                {"hook_event_name": "PreCompact", "transcript_path": str(transcript), "cwd": temp}
            )
            env = dict(os.environ, SPONGRAM_PROJECT="same-project")
            result = subprocess.run(
                [sys.executable, "-", inp, str(CLAUDE / "lib")],
                input=code,
                capture_output=True,
                text=True,
                env=env,
                check=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["project"], "same-project")
            self.assertEqual(payload["source"], "precompact")
            self.assertEqual(len(payload["turns"]), 6)
            result = subprocess.run(
                ["bash", str(CLAUDE / "hooks/memory-capture.sh")],
                input="{}",
                capture_output=True,
                text=True,
                env=dict(env, SPONGRAM_CAPTURE_DISABLED="1"),
                check=True,
            )
            self.assertEqual(result.stdout, "")

    def test_claude_interfaces_and_codex_hook_isolation(self):
        manifest = json.loads((CLAUDE / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(set(manifest["userConfig"]), {"instance_url", "brain_key"})
        self.assertEqual(
            json.loads((CLAUDE / ".mcp.json").read_text())["mcpServers"]["spongram"]["type"], "http"
        )
        for command in ("recall", "brain-stats", "brain-graph", "persona"):
            self.assertTrue((CLAUDE / "commands" / (command + ".md")).exists())
        hooks = json.loads((CLAUDE / "hooks/hooks.json").read_text())["hooks"]
        self.assertTrue(
            {"SessionStart", "Stop", "PostToolUse", "PreCompact", "SessionEnd"} <= set(hooks)
        )
        self.assertFalse((CODEX / "hooks").exists())
        self.assertFalse((CODEX / ".claude-plugin").exists())
        market = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
        self.assertEqual([p["name"] for p in market["plugins"]], ["spongram-codex"])

    def test_secret_free_config_and_custom_instance(self):
        server = config.server_config("https://example.test/spongram/")
        self.assertEqual(server["url"], "https://example.test/spongram/mcp")
        self.assertEqual(server["bearer_token_env_var"], "SPONGRAM_BRAIN_KEY")
        self.assertEqual(server["http_headers"]["X-Spongram-Client"], "codex")
        for invalid in [
            "http://remote.test",
            "https://user:pass@example.test",
            "https://example.test?key=secret",
        ]:
            with self.assertRaises(ValueError):
                config.server_config(invalid)
        bundled = json.loads((CODEX / ".mcp.json").read_text())
        self.assertEqual(
            bundled["mcpServers"]["spongram"],
            config.server_config("https://spongram.sponge-theory.dev"),
        )
        self.assertNotIn("CLAUDE_PLUGIN_OPTION", (CODEX / "scripts/codemap.py").read_text())

    def test_codemap_secret_stays_in_process_and_map_identity_matches_claude(self):
        from types import SimpleNamespace

        runner = module("codemap_runner", CODEX / "scripts/codemap.py")
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "shared-repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            calls = []

            def fake_run(args):
                calls.append(args)
                return 0

            with (
                patch.dict(os.environ, {"SPONGRAM_BRAIN_KEY": "test-only-secret"}),
                patch.dict(sys.modules, {"spongram_codemap.cli": SimpleNamespace(main=fake_run)}),
                patch.object(sys, "argv", ["codemap.py", "build", str(repo)]),
                patch.object(subprocess, "check_output", wraps=subprocess.check_output) as git,
            ):
                self.assertEqual(runner.main(), 0)
                for call in git.call_args_list:
                    self.assertNotIn("test-only-secret", str(call))
            args = calls[0]
            self.assertEqual(args[args.index("--repo") + 1], "shared-repo")
            self.assertEqual(args[args.index("--key") + 1], "test-only-secret")
            self.assertTrue(args[args.index("--state") + 1].endswith("spongram-codemap-codex.json"))
            self.assertFalse((Path(temp) / ".spongram").exists())

    def test_shell_syntax(self):
        for script in (CLAUDE / "hooks").glob("*.sh"):
            subprocess.run(["bash", "-n", str(script)], check=True)


class MCPHandshake(unittest.TestCase):
    def test_json_and_sse_session_headers_and_pagination(self):
        calls = []

        class Response(io.BytesIO):
            def __init__(self, obj=None, sse=False):
                data = json.dumps(obj) if obj else ""
                super().__init__(
                    ("event: message\r\ndata: " + data + "\r\n\r\n" if sse else data).encode()
                )
                self.headers = {
                    "Content-Type": "text/event-stream" if sse else "application/json",
                    "Mcp-Session-Id": "session-test",
                }

        def fake_open(req, timeout):
            calls.append(req)
            rpc = json.loads(req.data)
            headers = {k.lower(): v for k, v in req.header_items()}
            self.assertEqual(headers["authorization"], "Bearer test-key")
            self.assertEqual(headers["x-spongram-client"], "codex")
            if rpc["method"] == "initialize":
                return Response(
                    {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-03-26"}}
                )
            self.assertEqual(headers["mcp-session-id"], "session-test")
            self.assertEqual(headers["mcp-protocol-version"], "2025-03-26")
            if rpc["method"] == "notifications/initialized":
                return Response()
            self.assertEqual(rpc["method"], "tools/list")
            if rpc["id"] == 2:
                return Response(
                    {"id": 2, "result": {"tools": [{"name": "add_memory"}], "nextCursor": "page2"}},
                    True,
                )
            self.assertEqual(rpc["params"]["cursor"], "page2")
            return Response(
                {
                    "id": 3,
                    "result": {
                        "tools": [{"name": "search_nodes"}, {"name": "search_memory_facts"}]
                    },
                }
            )

        names = check.probe("https://example.test/mcp", "test-key", fake_open)
        self.assertEqual(len(names), 3)
        self.assertEqual(len(calls), 4)

    def test_rpc_error_is_not_success(self):
        response = io.BytesIO(b'{"id":1,"error":{"message":"secret response"}}')
        response.headers = {"Content-Type": "application/json"}
        with self.assertRaisesRegex(ValueError, "MCP request failed: initialize"):
            check.probe("https://example.test/mcp", "test-key", lambda *a, **kw: response)


if __name__ == "__main__":
    unittest.main()
