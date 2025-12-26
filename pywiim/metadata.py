"""Metadata placeholder detection and validation utilities.

This module centralizes the library's definition of "invalid" metadata values.
These placeholders commonly appear during WiiM/LinkPlay track/source transitions
or on sources that don't expose metadata reliably.

Keeping this logic in one place prevents drift across modules (state merge,
player properties, UPnP health tracking, etc.).
"""

from __future__ import annotations

from typing import Any

# String placeholders seen across devices/firmware builds.
# Keep this list intentionally small and focused to avoid false negatives.
_PLACEHOLDER_STRINGS = {
    "unknown",
    "unknow",
    "un_known",
    "none",
    "null",
    "(null)",
    "n/a",
    "na",
    "-",
    "--",
}


def is_placeholder_string(val: str) -> bool:
    """Return True if val is a known placeholder string (case-insensitive)."""
    return val.strip().lower() in _PLACEHOLDER_STRINGS


def is_valid_metadata_value(val: Any) -> bool:
    """Return True if val is a non-empty, non-placeholder metadata value.

    This is intended for title/artist/album-like fields.
    """
    if val is None:
        return False
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return False
        return not is_placeholder_string(s)
    return True


def is_valid_image_url(val: Any) -> bool:
    """Return True if val looks like a usable image URL for artwork.

    - Must be http/https
    - Must not be a known placeholder/sentinel (including 'un_known' paths)
    """
    if not isinstance(val, str):
        return False
    s = val.strip()
    if not s:
        return False

    s_lower = s.lower()
    if is_placeholder_string(s_lower):
        return False
    if "un_known" in s_lower:
        return False
    return s_lower.startswith(("http://", "https://"))


__all__ = [
    "is_placeholder_string",
    "is_valid_metadata_value",
    "is_valid_image_url",
]
