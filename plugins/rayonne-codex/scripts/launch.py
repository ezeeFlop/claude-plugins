"""Resolve credentials privately, then start the unchanged PyPI MCP server."""
import os
import sys
from connection import SetupError, load_profile, normalize_instance, read_secret, validate_key


def login_file():
    """The key `rayonne-mcp login` saved for the user (``rayonne_mcp.credentials``),
    validated like any other; ``(None, None)`` without one."""
    try:
        from rayonne_mcp import credentials
    except ImportError:  # a server older than the login command
        return None, None
    saved = credentials.load() or {}
    key, url = saved.get("api_key"), saved.get("api_url")
    if not key or not url:
        return None, None
    return normalize_instance(str(url).removesuffix("/api/public/v1")), validate_key(str(key))


def configure_environment():
    url = os.environ.get("RAYONNE_API_URL")
    key = os.environ.get("RAYONNE_API_KEY")
    if url or key:
        if not url or not key:
            raise SetupError("Set both RAYONNE_API_URL and RAYONNE_API_KEY, or use rayonne-setup")
        url, key = normalize_instance(url), validate_key(key)
    else:
        try:
            profile = load_profile()
        except SetupError:
            # No keychain profile (Linux, or a key installed with
            # `rayonne-mcp login`): the user's own 0600 file, if any.
            url, key = login_file()
        else:
            url, key = profile["instance_url"], read_secret(profile["credential"])
            os.environ.setdefault("RAYONNE_READ_ONLY", str(profile["read_only"]).lower())
        if not key:
            raise SetupError("Rayonne API key missing. Run rayonne-setup")
    read_only = os.environ.get("RAYONNE_READ_ONLY", "false").strip().lower()
    if read_only not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
        raise SetupError("Invalid RAYONNE_READ_ONLY value")
    os.environ["RAYONNE_API_URL"] = url
    os.environ["RAYONNE_API_KEY"] = key
    os.environ["RAYONNE_READ_ONLY"] = read_only


if __name__ == "__main__":
    try:
        configure_environment()
    except (SetupError, OSError, ValueError, KeyError, TypeError):
        sys.exit("Rayonne credentials unavailable. Run the rayonne-setup skill.")
    from rayonne_mcp.server import main
    main()
