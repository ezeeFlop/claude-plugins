"""Code map client/hook fixes ported from the Spongram server repository's
2026-10-01 production audit (D7, D8 amended, M4):

- D7: ``push()`` retries on 409 (ingest already running for this repo) and
  503 (upstream unavailable), honoring ``Retry-After`` (default 15s, capped
  at 120s), up to 6 attempts and 10 minutes of REAL elapsed time. Before this
  fix a 409 collision (e.g. the post-commit hook firing while a manual
  rebuild is still running) silently dropped the push.
- D8 (amended): a LINKED git worktree never publishes the code map —
  ``update`` replaces the repo's whole subgraph, so publishing from a
  worktree would make the map follow whichever worktree committed last.
  ``post-commit.sh`` exits silently in a worktree; ``setup-codemap.sh``
  abstains with exactly one stderr line. Both use ``--git-dir`` vs
  ``--git-common-dir`` to tell a linked worktree from the main checkout, and
  derive the repo name from the MAIN checkout (parent of the common .git).
- M4: ``--path-format=absolute`` only exists since git 2.31; an older git
  either rejects it or echoes it back verbatim on stdout. Both hooks fall
  back to ``cd`` + ``pwd -P`` in that case.
"""

from __future__ import annotations

import email.message
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SHARED_LIB = ROOT / "shared/spongram/lib"
HOOKS = ROOT / "plugins/spongram/hooks"


def _load_push_module():
    """Load the shared-core ``spongram_codemap.push`` module directly from
    ``shared/spongram/lib`` (the release source of truth) rather than relying
    on whatever happens to be on ``sys.path`` — mirrors how ``test_spongram.py``
    loads ``project_context`` from the shared tree."""
    package_init = SHARED_LIB / "spongram_codemap/__init__.py"
    pkg_spec = importlib.util.spec_from_file_location(
        "spongram_codemap", package_init, submodule_search_locations=[str(package_init.parent)]
    )
    pkg = importlib.util.module_from_spec(pkg_spec)
    sys.modules["spongram_codemap"] = pkg
    pkg_spec.loader.exec_module(pkg)

    spec = importlib.util.spec_from_file_location(
        "spongram_codemap.push", SHARED_LIB / "spongram_codemap/push.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["spongram_codemap.push"] = mod
    spec.loader.exec_module(mod)
    return mod


push_mod = _load_push_module()
push = push_mod.push


class _Clock:
    """Fake monotonic clock: ``sleep`` AND a simulated request latency
    (``tick``) both advance the same clock read by ``monotonic``."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def monotonic(self) -> float:
        return self.now

    def tick(self, seconds: float) -> None:
        self.now += seconds


def _http_error(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    hdrs = email.message.Message()
    if retry_after is not None:
        hdrs["Retry-After"] = retry_after
    return urllib.error.HTTPError(url="http://x/v1/codemap/ingest", code=code, msg="err", hdrs=hdrs, fp=None)


class _FakeResponse:
    def __init__(self, body: dict) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _queue(clock: _Clock, *outcomes, latency: float = 0.0):
    calls: list[None] = []
    remaining = list(outcomes)

    def fake_urlopen(req, timeout=120):
        calls.append(None)
        if latency:
            clock.tick(latency)
        outcome = remaining.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return _FakeResponse(outcome)

    return calls, fake_urlopen


def _push(clock: _Clock, *args):
    return push(*args, sleep=clock.sleep, monotonic=clock.monotonic)


class PushRetry(unittest.TestCase):
    """D7 — ``spongram_codemap.push.push`` retries on 409/503."""

    def test_409_then_200_succeeds_after_retry_after_wait(self):
        clock = _Clock()
        calls, fake = _queue(clock, _http_error(409, "7"), {"ingested": {"nodes": 1}})
        with patch.object(push_mod.urllib.request, "urlopen", fake):
            out = _push(clock, "http://x", "key", "repo", [], [], [])
        self.assertEqual(out, {"ingested": {"nodes": 1}})
        self.assertEqual(len(calls), 2)
        self.assertEqual(clock.sleeps, [7.0])

    def test_503_then_200_also_retries(self):
        clock = _Clock()
        calls, fake = _queue(clock, _http_error(503, "3"), {"ok": True})
        with patch.object(push_mod.urllib.request, "urlopen", fake):
            out = _push(clock, "http://x", "key", "repo", [], [], [])
        self.assertEqual(out, {"ok": True})
        self.assertEqual(len(calls), 2)
        self.assertEqual(clock.sleeps, [3.0])

    def test_missing_retry_after_defaults_to_15s(self):
        clock = _Clock()
        _, fake = _queue(clock, _http_error(409, None), {"ok": True})
        with patch.object(push_mod.urllib.request, "urlopen", fake):
            _push(clock, "http://x", "key", "repo", [], [], [])
        self.assertEqual(clock.sleeps, [15.0])

    def test_retry_after_is_capped_at_120s(self):
        clock = _Clock()
        _, fake = _queue(clock, _http_error(409, "99999"), {"ok": True})
        with patch.object(push_mod.urllib.request, "urlopen", fake):
            _push(clock, "http://x", "key", "repo", [], [], [])
        self.assertEqual(clock.sleeps, [120.0])

    def test_seven_consecutive_409_raises_after_six_attempts(self):
        clock = _Clock()
        calls, fake = _queue(clock, *[_http_error(409, "1") for _ in range(7)])
        with patch.object(push_mod.urllib.request, "urlopen", fake):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                _push(clock, "http://x", "key", "repo", [], [], [])
        self.assertEqual(ctx.exception.code, 409)
        # At most 6 attempts consumed (never the 7th); 5 waits between them.
        self.assertEqual(len(calls), 6)
        self.assertEqual(len(clock.sleeps), 5)

    def test_non_retryable_status_raises_immediately(self):
        clock = _Clock()
        calls, fake = _queue(clock, _http_error(404, "1"))
        with patch.object(push_mod.urllib.request, "urlopen", fake):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                _push(clock, "http://x", "key", "repo", [], [], [])
        self.assertEqual(ctx.exception.code, 404)
        self.assertEqual(len(calls), 1)
        self.assertEqual(clock.sleeps, [])

    def test_total_wait_budget_of_ten_minutes_stops_retrying(self):
        # Each Retry-After=120 -> 5 waits of 120s = 600s = already the cap:
        # the 6th attempt must not wait again, it raises instead.
        clock = _Clock()
        calls, fake = _queue(clock, *[_http_error(409, "120") for _ in range(6)])
        with patch.object(push_mod.urllib.request, "urlopen", fake):
            with self.assertRaises(urllib.error.HTTPError):
                _push(clock, "http://x", "key", "repo", [], [], [])
        self.assertLessEqual(sum(clock.sleeps), 600.0)
        self.assertLessEqual(len(calls), 6)

    def test_real_elapsed_time_including_latency_counts_toward_budget(self):
        """The 10-minute cap must measure REAL elapsed time (monotonic
        clock), not just the sum of the waits — a slow request must count
        too. With Retry-After=90s and 50s of latency PER call (time spent
        IN the request itself, never recorded as a sleep), the budget (600s)
        is crossed on the 5th failure: (50+90)*4 + 50 = 610 > 600, i.e.
        BEFORE the 6-attempt cap — whereas summing only the waits
        (4*90=360, or even 5*90=450) would never have exceeded 600s within
        6 attempts."""
        clock = _Clock()
        calls, fake = _queue(clock, *[_http_error(409, "90") for _ in range(6)], latency=50.0)
        with patch.object(push_mod.urllib.request, "urlopen", fake):
            with self.assertRaises(urllib.error.HTTPError):
                _push(clock, "http://x", "key", "repo", [], [], [])
        self.assertEqual(len(calls), 5)
        self.assertEqual(len(clock.sleeps), 4)


def _git(*args, cwd=None, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def _init_repo_with_worktree(tmp_path: Path, *, main_name: str, worktree_name: str):
    main_repo = tmp_path / main_name
    main_repo.mkdir()
    _git("init", "-q", str(main_repo))
    _git("config", "user.email", "t@t", cwd=main_repo)
    _git("config", "user.name", "t", cwd=main_repo)
    (main_repo / "f.txt").write_text("x", encoding="utf-8")
    _git("add", "f.txt", cwd=main_repo)
    _git("commit", "-q", "-m", "init", cwd=main_repo)

    worktree = tmp_path / worktree_name
    _git("worktree", "add", "-q", str(worktree), "-b", "wtbranch", cwd=main_repo)
    return main_repo, worktree


def _fake_launcher(path: Path, log: Path) -> None:
    path.write_text(f'#!/bin/bash\nprintf "%s\\n" "$@" >> "{log}"\n', encoding="utf-8")
    path.chmod(0o755)


def _codemap_home(home: Path, log: Path) -> None:
    conn_dir = home / ".spongram" / "codemap"
    conn_dir.mkdir(parents=True)
    (conn_dir / "connection.env").write_text(
        "SPONGRAM_BASE_URL=http://x\nSPONGRAM_BRAIN_KEY=k\n", encoding="utf-8"
    )
    _fake_launcher(conn_dir / "codemap-run.sh", log)


class PostCommitWorktree(unittest.TestCase):
    """D8 amended — ``post-commit.sh`` reads the connection from
    ``~/.spongram/codemap/connection.env`` and hardcodes the launcher to
    ``~/.spongram/codemap/codemap-run.sh`` — override ``HOME`` to inject a
    fake, trace-only one."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="spongram-codemap-test-")
        self.addCleanup(self.temp.cleanup)
        self.tmp_path = Path(self.temp.name)

    def test_linked_worktree_makes_no_call_and_no_stderr(self):
        _main_repo, worktree = _init_repo_with_worktree(
            self.tmp_path, main_name="spongram-main", worktree_name="spg-m3"
        )
        log = self.tmp_path / "invocation.log"
        home = self.tmp_path / "home"
        _codemap_home(home, log)
        env = dict(os.environ, HOME=str(home))
        r = subprocess.run(
            ["bash", str(HOOKS / "post-commit.sh")], cwd=worktree, env=env, capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, "")
        time.sleep(1.0)  # give the (would-be) background subshell time to run
        self.assertFalse(log.exists(), "post-commit published from a linked worktree")

    def test_main_repo_calls_launcher_with_repo_name(self):
        main_repo, _worktree = _init_repo_with_worktree(
            self.tmp_path, main_name="spongram-main", worktree_name="spg-m3"
        )
        log = self.tmp_path / "invocation.log"
        home = self.tmp_path / "home"
        _codemap_home(home, log)
        env = dict(os.environ, HOME=str(home))
        r = subprocess.run(
            ["bash", str(HOOKS / "post-commit.sh")], cwd=main_repo, env=env, capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, "")
        deadline = time.time() + 5
        while time.time() < deadline and not log.exists():
            time.sleep(0.05)
        self.assertTrue(log.exists(), "post-commit never invoked the codemap launcher")
        args = log.read_text(encoding="utf-8").splitlines()
        self.assertIn("--repo", args)
        self.assertEqual(args[args.index("--repo") + 1], "spongram-main")


class SetupCodemapWorktree(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="spongram-codemap-test-")
        self.addCleanup(self.temp.cleanup)
        self.tmp_path = Path(self.temp.name)

    def test_linked_worktree_abstains_with_one_stderr_message_no_fs_noise(self):
        main_repo, worktree = _init_repo_with_worktree(
            self.tmp_path, main_name="spongram-main", worktree_name="spg-m3"
        )
        home = self.tmp_path / "home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home), SPONGRAM_CODEMAP_SKIP_BUILD="1")
        r = subprocess.run(
            ["bash", str(HOOKS / "setup-codemap.sh")],
            input=json.dumps({"source": "startup", "cwd": str(worktree)}),
            cwd=worktree,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("worktree", r.stderr.lower())
        self.assertLessEqual(r.stderr.count("\n"), 1, f"expected ONE line, got: {r.stderr!r}")
        self.assertFalse((main_repo / ".git" / "hooks" / "post-commit").exists())

    def test_main_repo_installs_hook_with_repo_name(self):
        main_repo, _worktree = _init_repo_with_worktree(
            self.tmp_path, main_name="spongram-main", worktree_name="spg-m3"
        )
        home = self.tmp_path / "home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home), SPONGRAM_CODEMAP_SKIP_BUILD="1")
        r = subprocess.run(
            ["bash", str(HOOKS / "setup-codemap.sh")],
            input=json.dumps({"source": "startup", "cwd": str(main_repo)}),
            cwd=main_repo,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        hook = main_repo / ".git" / "hooks" / "post-commit"
        self.assertTrue(hook.exists())
        self.assertIn("# spongram-codemap-hook", hook.read_text(encoding="utf-8"))


def _old_git_env(tmp_path: Path, mode: str, **extra: str) -> dict:
    """Environment whose PATH starts with a fake ``git`` simulating a git <
    2.31: ``reject`` refuses ``--path-format`` (exit 129), ``echo`` copies it
    back on stdout — what an unknown ``rev-parse`` option really did — then
    runs the real git without it."""
    real = shutil.which("git")
    assert real
    bindir = tmp_path / f"oldgit-{mode}"
    bindir.mkdir(exist_ok=True)
    if mode == "reject":
        body = (
            'for a in "$@"; do case "$a" in --path-format=*) '
            'echo "error: unknown option $a" >&2; exit 129;; esac; done\n'
            f'exec "{real}" "$@"\n'
        )
    else:
        body = (
            "args=()\n"
            'for a in "$@"; do case "$a" in --path-format=*) echo "$a";; '
            '*) args+=("$a");; esac; done\n'
            f'exec "{real}" "${{args[@]}}"\n'
        )
    git = bindir / "git"
    git.write_text("#!/bin/bash\n" + body, encoding="utf-8")
    git.chmod(0o755)
    return dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", **extra)


class OldGitFallback(unittest.TestCase):
    """M4 — ``--path-format`` doesn't exist before git 2.31."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="spongram-codemap-test-")
        self.addCleanup(self.temp.cleanup)
        self.tmp_path = Path(self.temp.name)

    def _check(self, mode):
        main_repo, _wt = _init_repo_with_worktree(self.tmp_path, main_name="m", worktree_name="w")
        r = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-dir"],
            cwd=main_repo,
            env=_old_git_env(self.tmp_path, mode),
            capture_output=True,
            text=True,
        )
        self.assertFalse(r.stdout.startswith("/"), "fake git should behave like git < 2.31")

    def test_fake_old_git_really_lacks_path_format_reject(self):
        self._check("reject")

    def test_fake_old_git_really_lacks_path_format_echo(self):
        self._check("echo")

    def _main_repo_publishes(self, mode):
        main_repo, _wt = _init_repo_with_worktree(
            self.tmp_path, main_name="spongram-main", worktree_name="spg-m3"
        )
        log = self.tmp_path / "invocation.log"
        home = self.tmp_path / "home"
        _codemap_home(home, log)
        env = _old_git_env(self.tmp_path, mode, HOME=str(home))
        r = subprocess.run(
            ["bash", str(HOOKS / "post-commit.sh")], cwd=main_repo, env=env, capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, "")
        deadline = time.time() + 5
        while time.time() < deadline and not log.exists():
            time.sleep(0.05)
        self.assertTrue(log.exists(), "no publish from the main repo with an old git")
        args = log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(args[args.index("--repo") + 1], "spongram-main")
        state = Path(args[args.index("--state") + 1])
        self.assertEqual(state.parent.resolve(), (main_repo / ".git").resolve())

    def test_old_git_post_commit_main_repo_publishes_under_main_name_reject(self):
        self._main_repo_publishes("reject")

    def test_old_git_post_commit_main_repo_publishes_under_main_name_echo(self):
        self._main_repo_publishes("echo")

    def _worktree_stays_silent(self, mode):
        _main, worktree = _init_repo_with_worktree(
            self.tmp_path, main_name="spongram-main", worktree_name="spg-m3"
        )
        log = self.tmp_path / "invocation.log"
        home = self.tmp_path / "home"
        _codemap_home(home, log)
        env = _old_git_env(self.tmp_path, mode, HOME=str(home))
        r = subprocess.run(
            ["bash", str(HOOKS / "post-commit.sh")], cwd=worktree, env=env, capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stderr, "")
        time.sleep(1.0)
        self.assertFalse(log.exists(), "a linked worktree must never publish, even with an old git")

    def test_old_git_post_commit_worktree_stays_silent_reject(self):
        self._worktree_stays_silent("reject")

    def test_old_git_post_commit_worktree_stays_silent_echo(self):
        self._worktree_stays_silent("echo")

    def _setup_installs_hook(self, mode):
        main_repo, _wt = _init_repo_with_worktree(
            self.tmp_path, main_name="spongram-main", worktree_name="spg-m3"
        )
        home = self.tmp_path / "home"
        home.mkdir()
        env = _old_git_env(self.tmp_path, mode, HOME=str(home), SPONGRAM_CODEMAP_SKIP_BUILD="1")
        r = subprocess.run(
            ["bash", str(HOOKS / "setup-codemap.sh")],
            input=json.dumps({"source": "startup", "cwd": str(main_repo)}),
            cwd=main_repo,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")
        hook = main_repo / ".git" / "hooks" / "post-commit"
        self.assertTrue(hook.exists(), "hook not installed with an old git")
        self.assertIn("# spongram-codemap-hook", hook.read_text(encoding="utf-8"))

    def test_old_git_setup_codemap_main_repo_installs_hook_reject(self):
        self._setup_installs_hook("reject")

    def test_old_git_setup_codemap_main_repo_installs_hook_echo(self):
        self._setup_installs_hook("echo")

    def _setup_worktree_abstains(self, mode):
        main_repo, worktree = _init_repo_with_worktree(
            self.tmp_path, main_name="spongram-main", worktree_name="spg-m3"
        )
        home = self.tmp_path / "home"
        home.mkdir()
        env = _old_git_env(self.tmp_path, mode, HOME=str(home), SPONGRAM_CODEMAP_SKIP_BUILD="1")
        r = subprocess.run(
            ["bash", str(HOOKS / "setup-codemap.sh")],
            input=json.dumps({"source": "startup", "cwd": str(worktree)}),
            cwd=worktree,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("worktree", r.stderr.lower())
        self.assertLessEqual(r.stderr.count("\n"), 1, r.stderr)
        self.assertFalse((main_repo / ".git" / "hooks" / "post-commit").exists())

    def test_old_git_setup_codemap_worktree_abstains_reject(self):
        self._setup_worktree_abstains("reject")

    def test_old_git_setup_codemap_worktree_abstains_echo(self):
        self._setup_worktree_abstains("echo")


class HooksShipTheWorktreeBailOut(unittest.TestCase):
    def test_hooks_ship_the_worktree_bail_out(self):
        for path in (HOOKS / "post-commit.sh", HOOKS / "setup-codemap.sh"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("--git-dir", text, f"{path} does not distinguish --git-dir (D8)")
            self.assertIn("--git-common-dir", text, f"{path} does not use --git-common-dir (D8)")
            self.assertIn("GIT_DIR_ABS", text)
            self.assertIn("GIT_COMMON_DIR", text)


if __name__ == "__main__":
    unittest.main()
