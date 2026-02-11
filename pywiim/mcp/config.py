"""MCP server configuration: file + env vars."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _default_config_path() -> Path:
    """Default config file path (XDG ~/.config/wiim/config.json)."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", os.path.expanduser("~")))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")))
    return base / "wiim" / "config.json"


def load_config() -> dict:
    """Load config from file and env vars. Env vars override file values.

    Config file: WIIM_CONFIG_FILE or ~/.config/wiim/config.json
    Keys: default_device, named_devices, discovery_disabled, timeout, discovery_timeout

    Env overrides: WIIM_DEFAULT_DEVICE, WIIM_NAMED_DEVICES (JSON),
    WIIM_DISCOVERY_DISABLED, WIIM_TIMEOUT, WIIM_DISCOVERY_TIMEOUT
    """
    cfg: dict = {}

    # Load from file if present
    path = os.environ.get("WIIM_CONFIG_FILE") or str(_default_config_path())
    config_path = Path(path)
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                file_cfg = json.load(f)
            cfg["default_device"] = file_cfg.get("default_device")
            cfg["named_devices"] = file_cfg.get("named_devices") or {}
            cfg["discovery_disabled"] = file_cfg.get("discovery_disabled", False)
            cfg["timeout"] = float(file_cfg.get("timeout", 5.0))
            cfg["discovery_timeout"] = int(file_cfg.get("discovery_timeout", 5))
        except (json.JSONDecodeError, OSError):
            pass

    # Env overrides
    if env := os.environ.get("WIIM_DEFAULT_DEVICE"):
        cfg["default_device"] = env
    if env := os.environ.get("WIIM_NAMED_DEVICES"):
        try:
            cfg["named_devices"] = json.loads(env)
        except json.JSONDecodeError:
            pass
    if env := os.environ.get("WIIM_DISCOVERY_DISABLED"):
        cfg["discovery_disabled"] = env.lower() in ("1", "true", "yes")
    if env := os.environ.get("WIIM_TIMEOUT"):
        try:
            cfg["timeout"] = float(env)
        except ValueError:
            pass
    if env := os.environ.get("WIIM_DISCOVERY_TIMEOUT"):
        try:
            cfg["discovery_timeout"] = int(env)
        except ValueError:
            pass

    return cfg
