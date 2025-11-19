"""Device information normalization helpers.

This module provides pure functions for normalizing and enriching device
information, with no network or framework dependencies.
"""

from __future__ import annotations

from typing import Any

from .models import DeviceInfo

__all__ = ["normalize_device_info", "normalize_vendor"]


def normalize_device_info(device_info: DeviceInfo) -> dict[str, Any]:
    """Normalize and enrich device information with derived fields.

    This function takes a DeviceInfo model and returns a dictionary with
    additional normalized and derived fields. The returned dictionary can
    be merged with the original model's dict representation.

    Args:
        device_info: DeviceInfo model instance

    Returns:
        Dictionary with normalized and derived fields including:
        - firmware: Firmware version
        - firmware_date: Release date
        - hardware: Hardware revision
        - project: Device model/project name
        - mcu_version: MCU firmware version
        - dsp_version: DSP firmware version
        - preset_slots: Number of preset slots (from preset_key)
        - wmrm_version: WiiM multiroom protocol version
        - update_available: Whether firmware update is available
        - latest_version: Latest available firmware version

    Example:
        ```python
        device_info = await client.get_device_info_model()
        normalized = normalize_device_info(device_info)

        # Merge with original dict
        full_info = {**device_info.model_dump(), **normalized}
        ```
    """
    payload: dict[str, Any] = {}

    # Core firmware / build information
    if device_info.firmware:
        payload["firmware"] = device_info.firmware

    if device_info.release_date:
        payload["firmware_date"] = device_info.release_date

    # Hardware & project identifiers
    if device_info.hardware:
        payload["hardware"] = device_info.hardware

    if device_info.model:
        payload["project"] = device_info.model

    # MCU / DSP versions
    if device_info.mcu_ver is not None:
        payload["mcu_version"] = str(device_info.mcu_ver)

    if device_info.dsp_ver is not None:
        payload["dsp_version"] = str(device_info.dsp_ver)

    # Preset slots – convert preset_key to integer count when valid
    if device_info.preset_key is not None:
        try:
            payload["preset_slots"] = int(device_info.preset_key)
        except (TypeError, ValueError):
            pass  # Leave unset if conversion fails

    # WiiM multi-room protocol version
    if device_info.wmrm_version:
        payload["wmrm_version"] = device_info.wmrm_version

    # Firmware update availability
    if device_info.version_update is not None:
        update_flag = str(device_info.version_update)
        payload["update_available"] = update_flag == "1"

        if device_info.latest_version:
            payload["latest_version"] = device_info.latest_version

    return payload


def normalize_vendor(vendor: str | None) -> str:
    """Normalize vendor name to standard format.

    Args:
        vendor: Raw vendor string (may be None, mixed case, or variant)

    Returns:
        Normalized vendor string: "wiim", "arylic", "audio_pro", or "linkplay_generic"
    """
    if not vendor:
        return "linkplay_generic"

    vendor_lower = vendor.lower().strip()

    # Normalize common variations
    vendor_map = {
        "wiim": "wiim",
        "wiimu": "wiim",
        "wii m": "wiim",
        "wii-m": "wiim",
        "arylic": "arylic",
        "up2stream": "arylic",
        "audio pro": "audio_pro",
        "audio_pro": "audio_pro",
        "addon": "audio_pro",
        "linkplay": "linkplay_generic",
        "linkplay_generic": "linkplay_generic",
        "generic": "linkplay_generic",
        "unknown": "linkplay_generic",
    }

    # Direct match
    if vendor_lower in vendor_map:
        return vendor_map[vendor_lower]

    # Partial match
    for key, normalized in vendor_map.items():
        if key in vendor_lower or vendor_lower in key:
            return normalized

    return "linkplay_generic"
