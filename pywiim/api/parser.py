"""WiiM API response parser.

This module provides functions to parse and normalize API responses from WiiM devices.
Handles field mapping, time unit conversion, text decoding, and device-specific quirks.
"""

from __future__ import annotations

import asyncio
import html
import logging
import time
from typing import Any
from urllib.parse import quote

from .constants import (
    EQ_NUMERIC_MAP,
    MODE_MAP,
    PLAY_MODE_NORMAL,
    PLAY_MODE_REPEAT_ALL,
    PLAY_MODE_REPEAT_ONE,
    PLAY_MODE_SHUFFLE,
    PLAY_MODE_SHUFFLE_REPEAT_ALL,
    STATUS_MAP,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_time_value(value: int, field_name: str, source: str | None = None) -> int:
    """Normalize time values that may be in milliseconds or microseconds.

    The LinkPlay API returns time in different units depending on the streaming source:
    - Most sources: milliseconds (1,000 ms = 1 second)
    - Streaming services (Spotify, etc.): microseconds (1,000,000 μs = 1 second)

    This function uses a sanity check approach: if a value would represent > 10 hours
    when interpreted as milliseconds, it's likely in microseconds instead.

    Args:
        value: Raw time value from API
        field_name: Name of field for logging ("position" or "duration")
        source: Optional source name for enhanced logging

    Returns:
        Time in seconds

    See: https://github.com/mjcumming/wiim/issues/75
    """
    # Sanity threshold: 10 hours in milliseconds
    # Most music tracks are < 10 minutes; if > 10 hours in "ms", likely microseconds
    MS_THRESHOLD = 36_000_000  # 10 hours * 3600 seconds * 1000 ms

    if value > MS_THRESHOLD:
        # Value appears to be in microseconds
        result = value // 1_000_000
        _LOGGER.debug(
            "🎵 %s value %d appears to be in microseconds (> 10 hours if ms), "
            "converting from μs to seconds: %d seconds (source: %s)",
            field_name.capitalize(),
            value,
            result,
            source or "unknown",
        )
        return result
    else:
        # Standard millisecond conversion
        result = value // 1_000
        _LOGGER.debug(
            "🎵 %s value %d appears to be in milliseconds, converting to seconds: %d seconds (source: %s)",
            field_name.capitalize(),
            value,
            result,
            source or "unknown",
        )
        return result


def parse_player_status(
    raw: dict[str, Any], last_track: str | None = None, vendor: str | None = None
) -> tuple[dict[str, Any], str | None]:
    """Normalise *getPlayerStatusEx* / *getStatusEx* responses.

    Parses raw API response and normalizes field names, values, and formats.
    Handles time unit conversion, text decoding, and device-specific quirks.

    Args:
        raw: Raw API response dictionary
        last_track: Previous track identifier for change detection
        vendor: Device vendor for vendor-specific loop mode parsing

    Returns:
        Tuple of (parsed_data, new_last_track)
    """
    data: dict[str, Any] = {}

    play_state_val = raw.get("state") or raw.get("player_state") or raw.get("status")
    if play_state_val is not None:
        data["play_status"] = play_state_val

    # Generic key mapping first.
    for k, v in raw.items():
        if k in ("status", "state", "player_state"):
            continue
        data[STATUS_MAP.get(k, k)] = v

    # Hex-encoded strings → UTF-8 (per LinkPlay API standard)
    # Get raw values from original dict (before STATUS_MAP mapping)
    # STATUS_MAP maps Title/Artist/Album to title_hex/artist_hex/album_hex,
    # but we need the original hex values to decode them
    raw_title = raw.get("Title") or raw.get("title") or data.get("title_hex")
    raw_artist = raw.get("Artist") or raw.get("artist") or data.get("artist_hex")
    raw_album = raw.get("Album") or raw.get("album") or data.get("album_hex")

    decoded_title = _decode_text(raw_title)
    decoded_artist = _decode_text(raw_artist)
    decoded_album = _decode_text(raw_album)

    # Set both lowercase (for StateSynchronizer) and capitalized (for model alias)
    # Override any hex values with decoded values
    data["title"] = decoded_title
    data["Title"] = decoded_title  # For Pydantic model alias
    data["artist"] = decoded_artist
    data["Artist"] = decoded_artist  # For Pydantic model alias
    data["album"] = decoded_album
    data["Album"] = decoded_album  # For Pydantic model alias

    # Metadata parsing debug logging removed to reduce noise on every poll.
    # Track changes are logged below when they actually change.

    # Track change detection for debug logging.
    new_last_track = last_track
    if data.get("title") and data["title"] != "Unknown":
        cur = f"{data.get('artist', 'Unknown')} - {data['title']}"
        if last_track != cur:
            _LOGGER.debug("🎵 Track changed: %s", cur)
            new_last_track = cur

    # Power state defaults to *True* when missing.
    data.setdefault("power", True)

    # Volume (int percentage) → float 0-1.
    if (vol := raw.get("vol")) is not None:
        try:
            vol_i = int(vol)
            data["volume_level"] = vol_i / 100
            data["volume"] = vol_i
        except ValueError:
            _LOGGER.debug("Invalid volume value: %s", vol)

    # Playback position & duration (auto-detect ms vs μs).
    # The API returns time in milliseconds for most sources but microseconds for streaming services.
    # Use intelligent normalization to handle both cases.
    # See: https://github.com/mjcumming/wiim/issues/75
    source_hint = raw.get("mode")  # Will be used for enhanced logging

    # AirPlay debug logging removed to reduce noise on every poll.
    # Raw API response still available for debugging if needed.

    # Check both original field names and mapped field names (since generic mapping happens first)
    if (pos := raw.get("curpos") or raw.get("offset_pts") or data.get("position_ms")) is not None:
        try:
            pos_int = int(pos)
            normalized_position = _normalize_time_value(pos_int, "position", source_hint)
            data["position"] = normalized_position
            _LOGGER.debug("🎵 API PARSER: Setting data['position'] = %s", normalized_position)

            # Enhanced logging for position parsing
            source_type = "AirPlay" if source_hint and "airplay" in source_hint.lower() else source_hint or "unknown"
            _LOGGER.debug(
                "🎵 Position from API: %d seconds (source: %s, raw_value: %d)",
                normalized_position,
                source_type,
                pos_int,
            )

            # Try to use event loop time if available (async context), otherwise use time.time()
            try:
                data["position_updated_at"] = asyncio.get_running_loop().time()
            except RuntimeError:
                data["position_updated_at"] = time.time()
        except (ValueError, TypeError):
            _LOGGER.debug("Invalid position value: %s", pos)

    if (duration_val := raw.get("totlen") or data.get("duration_ms")) is not None:
        try:
            duration_int = int(duration_val)
            if duration_int > 0:  # Only set duration if it's actually provided
                normalized_duration = _normalize_time_value(duration_int, "duration", source_hint)

                # For AirPlay and other streaming sources, totlen is the actual total duration
                # The previous logic incorrectly interpreted it as remaining time
                # AirPlay provides both position (elapsed) and totlen (total duration) correctly
                data["duration"] = normalized_duration

                # Enhanced logging to help identify AirPlay and other sources
                source_type = (
                    "AirPlay" if source_hint and "airplay" in source_hint.lower() else source_hint or "unknown"
                )
        except (ValueError, TypeError):
            _LOGGER.debug("Invalid duration value: %s", duration_val)

    # Validate position vs duration - detect impossible scenarios
    if data.get("position") is not None and data.get("duration") is not None:
        position = data["position"]
        duration = data["duration"]
        if position > duration and duration > 0:
            # Check if duration seems too short (likely firmware bug)
            # If position is reasonable (> 30 seconds) but duration is very short (< 2 minutes),
            # the duration is likely wrong, not the position
            if position > 30 and duration < 120:
                _LOGGER.warning(
                    "🚨 Impossible media position detected: %d seconds elapsed > %d seconds duration "
                    "(device: %s, source: %s). Duration appears too short - likely firmware bug "
                    "Hiding duration to prevent UI confusion",
                    position,
                    duration,
                    raw.get("device_name", "unknown"),
                    source_hint or "unknown",
                )
                data["duration"] = None  # Hide duration instead of resetting position
            else:
                _LOGGER.warning(
                    "🚨 Impossible media position detected: %d seconds elapsed > %d seconds duration "
                    "(device: %s, source: %s). This appears to be a device firmware bug "
                    "Setting position to 0 to prevent UI confusion",
                    position,
                    duration,
                    raw.get("device_name", "unknown"),
                    source_hint or "unknown",
                )
                data["position"] = 0

    # Mute → bool.
    if "mute" in data:
        try:
            data["mute"] = bool(int(data["mute"]))
        except (TypeError, ValueError):  # noqa: PERF203 – clarity > micro perf.
            data["mute"] = bool(data["mute"])

    # Play-mode mapping from loop_mode values.
    # Different vendors use different loop_mode value schemes (see loop_mode.py)
    if "loop_mode" in data:
        try:
            # Convert loop_mode to int (API returns it as string)
            loop_val = int(data["loop_mode"])
            # Update data dict with int value for PlayerStatus model
            data["loop_mode"] = loop_val
        except (TypeError, ValueError):
            loop_val = 0
            data["loop_mode"] = 0

        # Only process play_mode if not already set
        if "play_mode" not in data:
            # Use vendor-specific loop mode mapping
            from .loop_mode import get_loop_mode_mapping

            mapping = get_loop_mode_mapping(vendor)
            is_shuffle, is_repeat_one, is_repeat_all = mapping.from_loop_mode(loop_val)

            # Map to play modes
            if is_shuffle and is_repeat_all:
                data["play_mode"] = PLAY_MODE_SHUFFLE_REPEAT_ALL
            elif is_shuffle and is_repeat_one:
                data["play_mode"] = PLAY_MODE_SHUFFLE  # Some devices don't differentiate shuffle+repeat_one
            elif is_shuffle:
                data["play_mode"] = PLAY_MODE_SHUFFLE
            elif is_repeat_one:
                data["play_mode"] = PLAY_MODE_REPEAT_ONE
            elif is_repeat_all:
                data["play_mode"] = PLAY_MODE_REPEAT_ALL
            else:
                data["play_mode"] = PLAY_MODE_NORMAL

    # Artwork – attempt cache-busting when metadata changes.
    cover = (
        raw.get("cover")
        or raw.get("cover_url")
        or raw.get("albumart")
        or raw.get("albumArtURI")
        or raw.get("albumArtUri")
        or raw.get("albumarturi")
        or raw.get("art_url")
        or raw.get("artwork_url")
        or raw.get("pic_url")
    )

    # Validate artwork URL - filter out invalid values like "unknow", "unknown", etc.
    if cover and str(cover).strip() not in (
        "unknow",
        "unknown",
        "un_known",
        "",
        "none",
    ):
        try:
            # Basic URL validation - must contain http or start with /
            if "http" in str(cover).lower() or str(cover).startswith("/"):
                cache_key = f"{data.get('title', '')}-{data.get('artist', '')}-{data.get('album', '')}"
                if cache_key:
                    encoded = quote(cache_key)
                    sep = "&" if "?" in cover else "?"
                    cover = f"{cover}{sep}cache={encoded}"
                data["entity_picture"] = cover
            else:
                _LOGGER.debug("Invalid artwork URL format: %s", cover)
        except Exception as e:
            _LOGGER.debug("Error processing artwork URL %s: %s", cover, e)

    # No valid cover art available - use WiiM logo as fallback
    # Check if entity_picture is missing, None, empty, or invalid
    entity_picture = data.get("entity_picture")
    if not entity_picture or str(entity_picture).strip() in (
        "unknow",
        "unknown",
        "un_known",
        "",
        "none",
    ):
        from .constants import DEFAULT_WIIM_LOGO_URL

        data["entity_picture"] = DEFAULT_WIIM_LOGO_URL

    # Source mapping from *mode* field.
    # Always derive source from mode if source is missing, None, empty, or invalid.
    # This handles cases where the API returns mode but not source (e.g., DLNA mode="2").
    # See: https://github.com/mjcumming/wiim/issues/104
    if (mode_val := raw.get("mode")) is not None:
        current_source = data.get("source")
        # Only override if source is missing, None, empty, or invalid
        if not current_source or current_source in ("unknown", "wifi", ""):
            if str(mode_val) == "99":
                # Set multiroom source when mode=99, but check if we explicitly cleared it
                # If source was explicitly set to "unknown" (by remove_slave), don't override
                # Otherwise, trust mode=99 as indicating multiroom mode
                group_field = raw.get("group") or data.get("group")
                master_uuid = raw.get("master_uuid") or data.get("master_uuid")
                master_ip = raw.get("master_ip") or data.get("master_ip")

                # Check if device is explicitly NOT in a group (group="0" and no master info)
                # This indicates the device has left the group
                explicitly_not_in_group = group_field == "0" and not master_uuid and not master_ip

                # Only skip setting source if explicitly not in group AND source is None or "unknown"
                # (which indicates we just cleared it in remove_slave)
                if explicitly_not_in_group and (current_source is None or current_source == "unknown"):
                    # Device just left group - don't set source
                    _LOGGER.debug(
                        "Mode=99 detected but device explicitly not in group (group=%s) and source=%s, "
                        "not setting source",
                        group_field,
                        current_source or "None",
                    )
                else:
                    # Set source - use "multiroom" as fallback
                    # Note: If source is already set to master's name (by add_slave), this won't override
                    # because the condition checks for missing/unknown/multiroom sources.
                    # The actual master name will be set by add_slave() when device joins.
                    data["source"] = "multiroom"
                    data["_multiroom_mode"] = True
            else:
                mapped_source = MODE_MAP.get(str(mode_val), "unknown")
                # Only set if we have a valid mapping (not "unknown" or "idle")
                # "idle" is a play STATE, not a SOURCE - don't overwrite existing source
                # Defensive fix for Issues #122, #103: Prevent mode=0 from setting source="idle"
                # - Modern WiiM devices: Report correct mode values (e.g., mode=31 for Spotify)
                # - Legacy Audio Pro devices: May report mode=0 for DLNA/Spotify (Issue #103)
                # Without this check, source from vendor field could be overwritten with "idle"
                if mapped_source not in ("unknown", "idle"):
                    data["source"] = mapped_source
                    _LOGGER.debug(
                        "Mapped mode %s to source '%s' (previous source: %s)",
                        mode_val,
                        mapped_source,
                        current_source or "missing",
                    )
                else:
                    _LOGGER.debug(
                        "Mode %s maps to '%s' (not a valid source), keeping source '%s'",
                        mode_val,
                        mapped_source,
                        current_source or "missing",
                    )
        else:
            # Source already set to something other than unknown/wifi/empty
            # Log why mapping was skipped (following HA pattern: log both success and skip cases)
            _LOGGER.debug(
                "Skipping mode-to-source mapping: mode=%s, source already set to '%s'",
                mode_val,
                current_source,
            )

    # Vendor override (e.g. Amazon Music).
    vendor_val = raw.get("vendor") or raw.get("Vendor") or raw.get("app")
    if vendor_val:
        vendor_clean = str(vendor_val).strip()
        _VENDOR_MAP = {
            "amazon music": "amazon",
            "amazonmusic": "amazon",
            "prime": "amazon",
            "qobuz": "qobuz",
            "tidal": "tidal",
            "deezer": "deezer",
        }
        if data.get("source") in {None, "wifi", "unknown"}:
            data["source"] = _VENDOR_MAP.get(vendor_clean.lower(), vendor_clean.lower().replace(" ", "_"))
        data["vendor"] = vendor_clean

    # EQ numeric → textual preset.
    eq_raw = data.get("eq_preset")
    if isinstance(eq_raw, int | str) and str(eq_raw).isdigit():
        data["eq_preset"] = EQ_NUMERIC_MAP.get(str(eq_raw), eq_raw)

    # Enhanced Qobuz Connect state detection (addresses GitHub issue #35)
    # Qobuz Connect has complex state reporting issues that require sophisticated detection
    if data.get("source") == "qobuz" or (vendor_val and "qobuz" in str(vendor_val).lower()):
        _handle_qobuz_connect_state_quirks(data, raw)

    return data, new_last_track


def _hex_to_str(val: str | None) -> str | None:
    """Decode hex-encoded UTF-8 strings as used by LinkPlay."""
    if not val:
        return None
    try:
        return bytes.fromhex(val).decode("utf-8", errors="replace")
    except ValueError:
        return val


def _handle_qobuz_connect_state_quirks(data: dict[str, Any], raw: dict[str, Any]) -> None:
    """Handle Qobuz Connect state detection quirks.

    Addresses GitHub issue #35: Qobuz Connect shows playing briefly then switches to idle.
    This implements the enhanced state detection logic that was added in python-linkplay v0.2.9.

    Args:
        data: Parsed data dictionary (modified in place)
        raw: Raw API response for additional context
    """
    current_status = data.get("play_status", "").lower()

    # Only apply workaround when status appears to be incorrectly reported as stopped/idle
    if current_status not in {"stop", "stopped", "idle", ""}:
        return  # Status appears correct, don't interfere

    # Enhanced detection: Look for multiple indicators that suggest active playback
    # This mimics the improved logic from python-linkplay v0.2.9

    title = data.get("title")
    has_track_info = bool(title and isinstance(title, str) and title.strip() and title != "Unknown")
    has_position_info = bool(data.get("position") or raw.get("curpos") or raw.get("offset_pts"))
    has_duration_info = bool(data.get("duration") or raw.get("totlen"))
    has_artwork = bool(data.get("entity_picture") or raw.get("cover") or raw.get("albumArtURI"))

    # Additional context indicators
    artist = data.get("artist")
    has_artist = bool(artist and isinstance(artist, str) and artist.strip() and artist != "Unknown")
    album = data.get("album")
    has_album = bool(album and isinstance(album, str) and album.strip() and album != "Unknown")

    # Count the number of positive indicators
    playback_indicators = sum(
        [
            has_track_info,
            has_position_info,
            has_duration_info,
            has_artwork,
            has_artist,
            has_album,
        ]
    )

    # Qobuz Connect specific: If we have rich metadata but status is stopped,
    # it's likely incorrectly reported. But be conservative to avoid false positives.
    if playback_indicators >= 3:  # Need multiple indicators to be confident
        _LOGGER.debug(
            "🎵 Qobuz Connect state correction: status='%s' but %d indicators suggest active playback. "
            "Correcting to 'play' (track: %s)",
            current_status,
            playback_indicators,
            data.get("title", "Unknown"),
        )
        data["play_status"] = "play"
    else:
        # Not enough indicators - probably genuinely stopped/idle
        _LOGGER.debug(
            "🎵 Qobuz Connect: status='%s' with %d indicators - leaving unchanged",
            current_status,
            playback_indicators,
        )


def _decode_text(val: str | None) -> str | None:
    """Decode hex-encoded UTF-8 strings, then clean up HTML entities."""
    if not val:
        return None

    # First: Standard hex decoding as per API specification
    decoded = _hex_to_str(val)
    if decoded:
        # Second: Clean up HTML entities that may appear in hex-decoded text
        return html.unescape(decoded)

    return val


__all__ = ["parse_player_status"]
