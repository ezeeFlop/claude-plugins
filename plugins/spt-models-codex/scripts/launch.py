"""Resolve SPT credentials privately, then run the bundled stdio server."""
import os
from pathlib import Path
import runpy
import sys
from connection import SetupError, load_profile, normalize_instance, read_secret, validate_key


def configure_environment():
    url = os.environ.get("SPT_BASE_URL")
    key = os.environ.get("SPT_API_KEY")
    if url or key:
        if not url or not key:
            raise SetupError("Set both SPT_BASE_URL and SPT_API_KEY, or use the setup skill")
        url, key = normalize_instance(url), validate_key(key)
    else:
        profile = load_profile()
        url = profile["instance_url"]
        key = read_secret(profile["credential"])
        if not key:
            raise SetupError("SPT API key missing. Run spt-models-setup")
    os.environ["SPT_BASE_URL"] = url
    os.environ["SPT_API_KEY"] = key
    os.environ.setdefault("SPT_REQUEST_TIMEOUT", "3900")


if __name__ == "__main__":
    try:
        configure_environment()
    except (SetupError, OSError, ValueError, KeyError, TypeError):
        sys.exit("SPT Models credentials unavailable. Run the spt-models-setup skill.")
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "server/main.py"), run_name="__main__")
