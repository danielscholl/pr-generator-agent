"""
AIPR - AI-powered Merge Request Description Generator
"""

import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version
from pathlib import Path


def get_version():
    """Return the version from pyproject.toml in dev, else the installed package metadata.

    The source checkout is authoritative when present (a stale dist in the dev
    virtualenv must not shadow it); installed packages have no pyproject.toml
    next to the source, so they fall through to importlib.metadata.
    """
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        pass
    try:
        return _package_version("pr-generator-agent")
    except PackageNotFoundError:
        return "unknown"


__version__ = get_version()
