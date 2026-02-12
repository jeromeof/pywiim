"""Version consistency tests."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pywiim


def test_module_version_matches_pyproject() -> None:
    """Ensure runtime __version__ stays synced with release version."""
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    assert pywiim.__version__ == pyproject["project"]["version"]
