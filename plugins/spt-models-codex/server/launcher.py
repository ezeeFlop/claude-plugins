"""Start the newest SPT Models MCP server the gateway ships.

An installed client never updates itself: Claude Desktop wants the .mcpb
dragged in again, API key retyped; Claude Code and Codex a marketplace update.
So every client starts here rather than in server/main.py:

1. ask the gateway which bundle it ships (`GET /v1/mcp/bundle/info`, with the
   API key the client already holds);
2. when that is newer than the installed version and not prepared yet, a
   detached process downloads it (`GET /v1/mcp/bundle`), checks its SHA-256,
   unpacks it into a per-user cache and has uv install its dependencies;
3. run the newest prepared version (`uv run --directory <cache>/<version>
   server/main.py`), else the installed one, in this process.

A gateway deploy thus reaches every client at its next start.  The check gets
`SPT_UPDATE_BUDGET_S` seconds (default 7, under the 10 s some clients allow an
MCP server to start); a preparation still running then carries on in the
background and its version is used from the next start.

Never worse than without it: a gateway unreachable or without the route, a bad
checksum, dependencies that fail to install — the installed version runs.  A
version that failed is not retried for an hour.  The gateway's version is
followed, but never below the installed one.

stdout is the MCP channel: nothing here writes to it.  Logs go to stderr (the
client's MCP log); the background preparation logs to `<cache>/launcher.log`.

Settings: SPT_AUTO_UPDATE=false turns it off; SPT_MCP_CACHE_DIR moves the cache
(default: the platform's user cache directory, `spt-models-mcp`).
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent          # <installed>/server
INSTALLED = HERE.parent

READY = ".ready"                 # in a version dir: dependencies installed
LAST_USED = ".last-used"         # in a version dir: touched at every start
FAILED = ".failed.json"          # in the cache: {version: unix time of the failure}
LOG = "launcher.log"

INFO_TIMEOUT_S = 3.0
DOWNLOAD_TIMEOUT_S = 30.0
SYNC_TIMEOUT_S = 600             # background: it delays no start
RETRY_AFTER_S = 3600
LOCK_STALE_S = 900
KEEP_VERSIONS = 2
PRUNE_UNUSED_FOR_S = 7 * 24 * 3600
MAX_BUNDLE_BYTES = 20 * 1024 * 1024
MAX_UNPACKED_BYTES = 50 * 1024 * 1024
MAX_LOG_BYTES = 1024 * 1024

_VERSION_RE = re.compile(r"^\d+(?:\.\d+){1,3}$")

logger = logging.getLogger("spt-mcp-launcher")


# ---------------------------------------------------------------- settings

def _setting(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default


def _flag(name: str, default: bool) -> bool:
    raw = _setting(name).lower()
    return default if not raw else raw not in ("0", "false", "no", "off")


def _seconds(name: str, default: float) -> float:
    try:
        return max(0.0, float(_setting(name, str(default))))
    except ValueError:
        return default


def cache_root() -> Path:
    custom = _setting("SPT_MCP_CACHE_DIR")
    if custom:
        return Path(custom).expanduser()
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "spt-models-mcp"


# ---------------------------------------------------------------- versions

def version_key(version) -> tuple[int, ...] | None:
    if isinstance(version, str) and _VERSION_RE.match(version):
        return tuple(int(part) for part in version.split("."))
    return None


def installed_version(root: Path = INSTALLED) -> str:
    """From manifest.json (the .mcpb) or pyproject.toml (the plugins)."""
    try:
        version = json.loads((root / "manifest.json").read_text(encoding="utf-8")).get("version")
        if version_key(version):
            return version
    except (OSError, ValueError, AttributeError):
        pass
    try:
        found = re.search(r'^version\s*=\s*"([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"), re.M)
        if found and version_key(found.group(1)):
            return found.group(1)
    except OSError:
        pass
    return "0.0"


def is_ready(version_dir: Path) -> bool:
    return (version_dir / READY).is_file() and (version_dir / "server" / "main.py").is_file()


def newest_ready(cache: Path, above: str) -> Path | None:
    floor = version_key(above) or ()
    best, best_key = None, None
    for entry in cache.iterdir() if cache.is_dir() else ():
        key = version_key(entry.name)
        if key and key > floor and is_ready(entry) and (best_key is None or key > best_key):
            best, best_key = entry, key
    return best


# ---------------------------------------------------------------- gateway

def _client(timeout: float):
    import httpx   # a dependency of the bundle, present in its environment

    return httpx.Client(
        base_url=_setting("SPT_BASE_URL").rstrip("/"),
        headers={"Authorization": f"Bearer {_setting('SPT_API_KEY')}"},
        timeout=timeout,
        verify=_flag("SPT_VERIFY_TLS", True),
    )


def offered_version() -> str | None:
    """The version the gateway ships; None when it cannot say."""
    try:
        with _client(INFO_TIMEOUT_S) as client:
            resp = client.get("/v1/mcp/bundle/info")
        if resp.status_code != 200:
            logger.info("gateway answered HTTP %s to the update check", resp.status_code)
            return None
        version = resp.json().get("version")
    except Exception as exc:   # unreachable, TLS, not JSON: never block the start
        logger.info("update check failed (%s)", type(exc).__name__)
        return None
    return version if version_key(version) else None


def download(version: str) -> bytes:
    with _client(DOWNLOAD_TIMEOUT_S) as client:
        resp = client.get("/v1/mcp/bundle")
    resp.raise_for_status()
    data = resp.content
    shipped = resp.headers.get("x-spt-bundle-version")
    if shipped != version:
        raise ValueError(f"the gateway now ships {shipped!r}, not {version}")
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError(f"bundle of {len(data)} bytes, above {MAX_BUNDLE_BYTES}")
    expected = resp.headers.get("x-spt-bundle-sha256", "").lower()
    if not expected or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("bundle checksum mismatch")
    return data


# ---------------------------------------------------------------- preparation

def unpack(data: bytes, cache: Path, version: str) -> Path:
    """Unpack into `cache/version`, atomically: a version dir is complete or absent."""
    target = cache / version
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=cache))
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            total = 0
            for info in zf.infolist():
                parts = PurePosixPath(info.filename).parts
                if (info.filename.startswith("/") or "\\" in info.filename or ".." in parts
                        or (parts and ":" in parts[0])):
                    raise ValueError(f"unsafe path in bundle: {info.filename!r}")
                total += info.file_size
            if total > MAX_UNPACKED_BYTES:
                raise ValueError(f"bundle of {total} bytes once unpacked")
            zf.extractall(staging)
        if installed_version(staging) != version:
            raise ValueError(f"bundle declares {installed_version(staging)}, not {version}")
        if not (staging / "server" / "main.py").is_file():
            raise ValueError("bundle without server/main.py")
        if target.exists() and not (target / "server" / "main.py").is_file():
            shutil.rmtree(target)
        try:
            os.rename(staging, target)
        except OSError:
            if not (target / "server" / "main.py").is_file():
                raise
            # another process unpacked the same version first
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return target


def uv_executable() -> str | None:
    # `uv run` exports UV (its own path): Claude Desktop's uv may not be on PATH.
    return os.environ.get("UV") or shutil.which("uv")


def child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)   # the installed version's: not the cached one's
    return env


def install_dependencies(version_dir: Path) -> None:
    uv = uv_executable()
    if not uv:
        raise RuntimeError("uv not found")
    done = subprocess.run(
        [uv, "sync", "--directory", str(version_dir)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=child_env(), timeout=SYNC_TIMEOUT_S,
    )
    if done.returncode:
        raise RuntimeError("uv sync failed: " + done.stdout.decode(errors="replace")[-2000:])


def _failures(cache: Path) -> dict:
    try:
        failures = json.loads((cache / FAILED).read_text(encoding="utf-8"))
        return failures if isinstance(failures, dict) else {}
    except (OSError, ValueError):
        return {}


def recently_failed(cache: Path, version: str) -> bool:
    when = _failures(cache).get(version)
    return isinstance(when, (int, float)) and time.time() - when < RETRY_AFTER_S


def _mark_failed(cache: Path, version: str) -> None:
    failures = _failures(cache)
    failures[version] = time.time()
    tmp = cache / f"{FAILED}.{os.getpid()}"
    tmp.write_text(json.dumps(failures), encoding="utf-8")
    os.replace(tmp, cache / FAILED)


def _take_lock(cache: Path, version: str) -> Path | None:
    lock = cache / f".prepare-{version}.lock"
    for _ in range(2):
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return lock
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime < LOCK_STALE_S:
                    return None
                lock.unlink()   # left by a preparation that died
            except FileNotFoundError:
                pass
    return None


def prune(cache: Path) -> None:
    """Beyond the KEEP_VERSIONS newest, drop versions unused for a week (a
    client still running one keeps reading its files)."""
    versions = sorted((d for d in cache.iterdir() if d.is_dir() and version_key(d.name)),
                      key=lambda d: version_key(d.name), reverse=True)
    now = time.time()
    for old in versions[KEEP_VERSIONS:]:
        marker = old / LAST_USED
        used = marker.stat().st_mtime if marker.exists() else old.stat().st_mtime
        if now - used > PRUNE_UNUSED_FOR_S:
            shutil.rmtree(old, ignore_errors=True)
    for staging in cache.glob(".staging-*"):
        if now - staging.stat().st_mtime > LOCK_STALE_S:
            shutil.rmtree(staging, ignore_errors=True)


def prepare(version: str) -> bool:
    """Download, unpack and install `version`.  True when it is ready."""
    cache = cache_root()
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / version
    if is_ready(target):
        return True
    lock = _take_lock(cache, version)
    if lock is None:
        logger.info("%s is being prepared by another process", version)
        return False
    try:
        if not (target / "server" / "main.py").is_file():
            unpack(download(version), cache, version)
        install_dependencies(target)
        (target / READY).write_text(str(int(time.time())), encoding="utf-8")
        logger.info("prepared %s in %s", version, target)
    except Exception:
        logger.exception("preparing %s failed; next attempt in an hour", version)
        _mark_failed(cache, version)
        return False
    finally:
        lock.unlink(missing_ok=True)
    try:
        prune(cache)
    except OSError:
        logger.warning("could not prune %s", cache, exc_info=True)
    return True


def spawn_prepare(version: str) -> None:
    """Prepare in a detached process: it outlives this one if it takes longer
    than the start budget."""
    cache = cache_root()
    log = cache / LOG
    try:
        if log.stat().st_size > MAX_LOG_BYTES:
            log.unlink()
    except OSError:
        pass
    options: dict = {"stdin": subprocess.DEVNULL, "close_fds": True, "cwd": str(cache)}
    if os.name == "nt":
        options["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    with open(log, "ab") as out:
        proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--prepare", version],
                                stdout=out, stderr=out, **options)
    if os.name != "nt":
        proc.wait(timeout=10)   # the intermediate forks the worker and exits at once


# ---------------------------------------------------------------- choice and start

def choose(installed: str) -> Path | None:
    """The cached version to run, or None for the installed one."""
    started = time.monotonic()
    budget = _seconds("SPT_UPDATE_BUDGET_S", 7.0)
    cache = cache_root()
    cache.mkdir(parents=True, exist_ok=True)
    offered = offered_version()
    if offered is None:
        return newest_ready(cache, installed)
    if version_key(offered) <= version_key(installed):
        return None
    target = cache / offered
    if is_ready(target):
        return target
    if recently_failed(cache, offered):
        logger.info("%s failed to prepare less than an hour ago; not retried yet", offered)
        return newest_ready(cache, installed)
    spawn_prepare(offered)
    while time.monotonic() - started < budget:
        if is_ready(target):
            return target
        if recently_failed(cache, offered):
            break
        time.sleep(0.2)
    else:
        logger.info("%s is still being prepared; it will run from the next start", offered)
    return newest_ready(cache, installed)


def run_cached(version_dir: Path) -> None:
    uv = uv_executable()
    if not uv:
        raise RuntimeError("uv not found")
    (version_dir / LAST_USED).touch()
    # --frozen: the lock `uv sync` wrote is used as is, no resolution at start.
    argv = [uv, "run", "--frozen", "--directory", str(version_dir), "server/main.py"]
    sys.stderr.flush()
    if os.name == "nt":   # no exec that keeps the process: relay stdio, then exit with it
        sys.exit(subprocess.call(argv, env=child_env()))
    os.execve(uv, argv, child_env())


def run_installed() -> None:
    runpy.run_path(str(HERE / "main.py"), run_name="__main__")


def _log_to_stderr() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s spt-mcp-launcher %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "--prepare":
        if hasattr(os, "fork") and os.fork():
            os._exit(0)   # double fork: the worker is nobody's zombie
        _log_to_stderr()
        prepare(argv[1])
        return

    _log_to_stderr()
    installed = installed_version()
    target = None
    if not _flag("SPT_AUTO_UPDATE", True):
        logger.info("auto-update off (SPT_AUTO_UPDATE)")
    elif _setting("SPT_BASE_URL") and _setting("SPT_API_KEY"):
        try:
            target = choose(installed)
        except Exception:
            logger.exception("update check failed")
    if target is not None:
        logger.info("running %s from %s (installed: %s)", target.name, target, installed)
        try:
            run_cached(target)
            return
        except Exception:
            logger.exception("could not start %s", target.name)
    logger.info("running the installed %s", installed)
    run_installed()


if __name__ == "__main__":
    main()
