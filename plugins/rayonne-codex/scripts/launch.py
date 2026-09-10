"""Resolve credentials privately, then start the unchanged PyPI MCP server."""
import os
import sys
from connection import SetupError, load_profile, normalize_instance, read_secret, validate_key


def configure_environment():
    url = os.environ.get("RAYONNE_API_URL")
    key = os.environ.get("RAYONNE_API_KEY")
    if url or key:
        if not url or not key:
            raise SetupError("Set both RAYONNE_API_URL and RAYONNE_API_KEY, or use rayonne-setup")
        url, key = normalize_instance(url), validate_key(key)
    else:
        profile = load_profile()
        url, key = profile["instance_url"], read_secret(profile["credential"])
        if not key:
            raise SetupError("Rayonne API key missing. Run rayonne-setup")
        os.environ.setdefault("RAYONNE_READ_ONLY", str(profile["read_only"]).lower())
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
