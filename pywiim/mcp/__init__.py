"""MCP server for WiiM/LinkPlay device control.

Exposes pywiim as an MCP server with tools for discovery, playback,
volume, sources, and grouping. Install with: pip install pywiim[mcp]

Run with: python -m pywiim.mcp
Or: wiim-mcp (after pip install)
"""

from __future__ import annotations

from .server import run

__all__ = ["run"]
