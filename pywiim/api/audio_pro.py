"""Audio Pro device response handling and normalization.

This module handles Audio Pro-specific response variations, including:
- String responses instead of JSON
- Field name variations
- Legacy firmware compatibility
- Response validation and normalization
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def validate_audio_pro_response(
    response: dict[str, Any] | str,
    endpoint: str,
    host: str,
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Handle Audio Pro specific response variations and legacy firmware issues.

    Args:
        response: Raw API response (dict or string)
        endpoint: API endpoint that was called
        host: Device hostname/IP for logging
        capabilities: Device capabilities dict

    Returns:
        Validated response with safe defaults if needed
    """
    # Handle empty responses from Audio Pro units
    if not response or response == {}:
        generation = capabilities.get("audio_pro_generation", "unknown") if capabilities else "unknown"
        _LOGGER.debug(
            "Empty response from Audio Pro/legacy device %s (generation: %s) for %s",
            host,
            generation,
            endpoint,
        )
        return _get_audio_pro_defaults(endpoint)

    # Handle Audio Pro MkII/W-Series string responses
    if isinstance(response, str):
        generation = capabilities.get("audio_pro_generation", "unknown") if capabilities else "unknown"
        _LOGGER.debug(
            "String response from Audio Pro device %s (generation: %s) for %s: %s",
            host,
            generation,
            endpoint,
            response,
        )
        return normalize_audio_pro_string_response(response, endpoint)

    # Handle malformed JSON responses from legacy devices
    if not isinstance(response, dict):
        _LOGGER.debug(
            "Non-dict response from Audio Pro/legacy device for %s: %s",
            endpoint,
            type(response),
        )
        return {"raw": str(response)}

    # Normalize Audio Pro specific field variations
    normalized = normalize_audio_pro_fields(response, endpoint)

    # Log field normalization if any mappings were applied
    if normalized != response:
        _LOGGER.debug("Normalized Audio Pro response fields for %s on %s", host, endpoint)

    return normalized


def normalize_audio_pro_string_response(response: str, endpoint: str) -> dict[str, Any]:
    """Normalize Audio Pro string responses to standard dict format.

    Args:
        response: String response from device
        endpoint: API endpoint that was called

    Returns:
        Normalized dict response
    """
    response = response.strip()

    # Common Audio Pro response patterns
    if response == "OK" or response == "ok":
        return {"raw": "OK"}
    elif response.lower() == "error" or response.lower() == "failed":
        return {"error": response}
    elif "error" in response.lower():
        return {"error": response}
    elif "not supported" in response.lower() or "unknown command" in response.lower():
        return {"error": "unsupported_command", "raw": response}
    else:
        # For status endpoints, try to parse as key:value pairs
        if "getPlayerStatus" in endpoint or "getStatus" in endpoint:
            return parse_audio_pro_status_string(response)
        else:
            return {"raw": response}


def parse_audio_pro_status_string(response: str) -> dict[str, Any]:
    """Parse Audio Pro status responses that come as strings instead of JSON.

    Audio Pro devices sometimes return status as "key:value" pairs.

    Args:
        response: String response to parse

    Returns:
        Parsed dict with normalized fields
    """
    result: dict[str, Any] = {}

    # Try to parse common patterns
    if ":" in response:
        parts = response.split(":")
        if len(parts) >= 2:
            key = parts[0].strip().lower()
            value = ":".join(parts[1:]).strip()

            # Map common Audio Pro status fields
            if key in ["state", "status", "player_state"]:
                result["state"] = value.lower()
            elif key in ["vol", "volume"]:
                try:
                    result["volume"] = int(value)
                    result["volume_level"] = int(value) / 100
                except ValueError:
                    result["volume"] = value
            elif key in ["mute", "muted"]:
                result["mute"] = value.lower() in ["1", "true", "on", "yes"]
            elif key == "title":
                result["title"] = value
            elif key == "artist":
                result["artist"] = value
            elif key == "album":
                result["album"] = value
            else:
                result[key] = value

    if not result:
        # Fallback: treat as generic status
        result = {"state": "unknown", "raw": response}

    return result


def normalize_audio_pro_fields(
    response: dict[str, Any],
    endpoint: str,
) -> dict[str, Any]:
    """Normalize Audio Pro specific field names and variations.

    Args:
        response: Raw response dict
        endpoint: API endpoint that was called

    Returns:
        Normalized response dict
    """
    normalized = response.copy()

    # Audio Pro specific field mappings
    field_mappings = {
        "player_state": "state",
        "play_status": "state",
        "vol": "volume",
        "volume_level": "volume_level",
        "mute": "mute",
        "muted": "mute",
        "title": "title",
        "artist": "artist",
        "album": "album",
        "device_name": "DeviceName",
        "friendly_name": "DeviceName",
    }

    # Apply field mappings
    for audio_pro_field, standard_field in field_mappings.items():
        if audio_pro_field in normalized and standard_field not in normalized:
            normalized[standard_field] = normalized.pop(audio_pro_field)

    # Normalize volume to 0-1 range if it's 0-100
    if "volume" in normalized and isinstance(normalized["volume"], (int, float)):
        if normalized["volume"] > 1:
            normalized["volume_level"] = normalized["volume"] / 100
        else:
            normalized["volume_level"] = normalized["volume"]

    # Normalize mute to boolean
    if "mute" in normalized:
        mute_value = normalized["mute"]
        if isinstance(mute_value, str):
            normalized["mute"] = mute_value.lower() in ["1", "true", "on", "yes"]
        elif isinstance(mute_value, (int, float)):
            normalized["mute"] = bool(mute_value)

    return normalized


def _get_audio_pro_defaults(endpoint: str) -> dict[str, Any]:
    """Get Audio Pro specific safe defaults based on endpoint.

    Args:
        endpoint: API endpoint that was called

    Returns:
        Dict with safe default values
    """
    if "getSlaveList" in endpoint:
        return {"slaves": 0, "slave_list": []}
    elif "getStatus" in endpoint or "getPlayerStatus" in endpoint:
        return {
            "group": "0",
            "state": "stop",
            "volume": 30,
            "volume_level": 0.3,
            "mute": False,
            "title": "Unknown",
            "artist": "Unknown Artist",
        }
    elif "getMetaInfo" in endpoint:
        return {"title": "", "artist": "", "album": ""}
    elif "getDeviceInfo" in endpoint or "getStatusEx" in endpoint:
        return {
            "DeviceName": "Audio Pro Speaker",
            "uuid": "",
            "firmware": "unknown",
            "group": "0",
            "state": "stop",
        }
    else:
        return {"raw": "OK"}
