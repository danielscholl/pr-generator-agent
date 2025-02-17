"""
AIPR - AI-powered Merge Request Description Generator
"""

import tomllib
from pathlib import Path


def get_version():
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        return "unknown"


__version__ = get_version()
