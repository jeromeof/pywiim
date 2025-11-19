"""Endpoint abstraction and registry for handling vendor/generation variations.

This module provides an endpoint registry that maps logical endpoint names to
vendor-specific and generation-specific endpoint paths with fallback chains.
"""

from __future__ import annotations

from typing import Any

from .constants import (
    API_ENDPOINT_ARYLIC_LED,
    API_ENDPOINT_ARYLIC_LED_BRIGHTNESS,
    API_ENDPOINT_AUDIO_OUTPUT_SET,
    API_ENDPOINT_AUDIO_OUTPUT_STATUS,
    API_ENDPOINT_DEVICE_INFO,
    API_ENDPOINT_EQ_GET,
    API_ENDPOINT_EQ_PRESET,
    API_ENDPOINT_GROUP_EXIT,
    API_ENDPOINT_GROUP_SLAVES,
    API_ENDPOINT_LED,
    API_ENDPOINT_LED_BRIGHTNESS,
    API_ENDPOINT_METADATA,
    API_ENDPOINT_MUTE,
    API_ENDPOINT_NEXT,
    API_ENDPOINT_PAUSE,
    API_ENDPOINT_PLAY,
    API_ENDPOINT_PLAYER_STATUS,
    API_ENDPOINT_PRESET_INFO,
    API_ENDPOINT_PREV,
    API_ENDPOINT_SEEK,
    API_ENDPOINT_STATUS,
    API_ENDPOINT_STOP,
    API_ENDPOINT_VOLUME,
    VENDOR_ARYLIC,
    VENDOR_AUDIO_PRO,
    VENDOR_LINKPLAY_GENERIC,
    VENDOR_WIIM,
)

# Logical endpoint names
ENDPOINT_PLAYER_STATUS = "player_status"
ENDPOINT_DEVICE_STATUS = "device_status"
ENDPOINT_METADATA = "metadata"
ENDPOINT_PLAY = "play"
ENDPOINT_PAUSE = "pause"
ENDPOINT_STOP = "stop"
ENDPOINT_NEXT = "next"
ENDPOINT_PREV = "prev"
ENDPOINT_VOLUME = "volume"
ENDPOINT_MUTE = "mute"
ENDPOINT_SEEK = "seek"
ENDPOINT_LED = "led"
ENDPOINT_LED_BRIGHTNESS = "led_brightness"
ENDPOINT_EQ_GET = "eq_get"
ENDPOINT_EQ_STATUS = "eq_status"
ENDPOINT_EQ_LIST = "eq_list"
ENDPOINT_EQ_PRESET = "eq_preset"
ENDPOINT_PRESET_INFO = "preset_info"
ENDPOINT_PRESET = "preset"
ENDPOINT_GROUP_SLAVES = "group_slaves"
ENDPOINT_GROUP_EXIT = "group_exit"
ENDPOINT_AUDIO_OUTPUT_STATUS = "audio_output_status"
ENDPOINT_AUDIO_OUTPUT_SET = "audio_output_set"

# Endpoint registry: logical_name -> variant -> endpoint_chain
# Each variant has an ordered list of endpoints to try
ENDPOINT_REGISTRY: dict[str, dict[str, list[str]]] = {
    ENDPOINT_PLAYER_STATUS: {
        "default": [
            API_ENDPOINT_PLAYER_STATUS,  # getPlayerStatusEx (WiiM, most devices)
            API_ENDPOINT_STATUS,  # getStatusEx (fallback)
            "/httpapi.asp?command=getPlayerStatus",  # Legacy fallback
            "/httpapi.asp?command=getStatus",  # Legacy fallback
        ],
        "audio_pro_mkii": [
            API_ENDPOINT_STATUS,  # getStatusEx (MkII doesn't support getPlayerStatusEx)
            "/httpapi.asp?command=getStatus",  # Legacy fallback
            "/api/status",  # REST variant (some MkII devices)
            "/cgi-bin/status.cgi",  # CGI variant (some MkII devices)
            "/status",  # Simple REST variant
            "/api/v1/status",  # Versioned REST variant
            "/device/status",  # Device-specific REST variant
        ],
        "audio_pro_w_generation": [
            API_ENDPOINT_PLAYER_STATUS,  # Preferred (W-Generation supports it)
            API_ENDPOINT_STATUS,  # Fallback
            "/httpapi.asp?command=getPlayerStatus",  # Legacy fallback
        ],
        "audio_pro_original": [
            API_ENDPOINT_STATUS,  # Primary (original generation)
            "/httpapi.asp?command=getStatus",  # Legacy fallback
        ],
        "arylic": [
            API_ENDPOINT_PLAYER_STATUS,  # Primary
            API_ENDPOINT_STATUS,  # Fallback
        ],
    },
    ENDPOINT_DEVICE_STATUS: {
        "default": [
            API_ENDPOINT_STATUS,  # getStatusEx
            API_ENDPOINT_DEVICE_INFO,  # getDeviceInfo (fallback)
        ],
        "audio_pro_mkii": [
            API_ENDPOINT_STATUS,  # getStatusEx (primary for MkII)
            API_ENDPOINT_DEVICE_INFO,  # getDeviceInfo (fallback)
        ],
        "audio_pro_w_generation": [
            API_ENDPOINT_STATUS,  # getStatusEx
            API_ENDPOINT_DEVICE_INFO,  # getDeviceInfo (fallback)
        ],
        "audio_pro_original": [
            API_ENDPOINT_STATUS,  # getStatusEx
            API_ENDPOINT_DEVICE_INFO,  # getDeviceInfo (fallback)
        ],
    },
    ENDPOINT_METADATA: {
        "default": [
            API_ENDPOINT_METADATA,  # getMetaInfo
        ],
        "audio_pro_mkii": [],  # Not supported - empty list means unsupported
        "audio_pro_w_generation": [
            API_ENDPOINT_METADATA,  # May be supported (probe to confirm)
        ],
        "audio_pro_original": [],  # Not supported
        "arylic": [
            API_ENDPOINT_METADATA,  # Generally supported
        ],
    },
    ENDPOINT_LED: {
        "default": [
            API_ENDPOINT_LED,  # setLED: (standard)
        ],
        "arylic": [
            API_ENDPOINT_ARYLIC_LED,  # MCU+PAS+RAKOIT:LED: (Arylic-specific)
            API_ENDPOINT_LED,  # Fallback to standard
        ],
        "audio_pro_mkii": [
            API_ENDPOINT_LED,  # Standard (may vary)
        ],
        "audio_pro_w_generation": [
            API_ENDPOINT_LED,  # Standard
        ],
        "audio_pro_original": [
            API_ENDPOINT_LED,  # Standard
        ],
    },
    ENDPOINT_LED_BRIGHTNESS: {
        "default": [
            API_ENDPOINT_LED_BRIGHTNESS,  # setLEDBrightness: (standard)
        ],
        "arylic": [
            API_ENDPOINT_ARYLIC_LED_BRIGHTNESS,  # MCU+PAS+RAKOIT:LEDBRIGHTNESS: (Arylic-specific)
            API_ENDPOINT_LED_BRIGHTNESS,  # Fallback to standard
        ],
    },
    ENDPOINT_EQ_GET: {
        "default": [
            API_ENDPOINT_EQ_GET,  # EQGetBand
        ],
        "audio_pro_mkii": [],  # Not supported
        "audio_pro_w_generation": [
            API_ENDPOINT_EQ_GET,  # May be supported (probe to confirm)
        ],
        "audio_pro_original": [],  # Not supported
    },
    ENDPOINT_EQ_PRESET: {
        "default": [
            API_ENDPOINT_EQ_PRESET,  # EQLoad:
        ],
        "audio_pro_mkii": [],  # Not supported
        "audio_pro_w_generation": [
            API_ENDPOINT_EQ_PRESET,  # May be supported (probe to confirm)
        ],
        "audio_pro_original": [],  # Not supported
    },
    ENDPOINT_PRESET_INFO: {
        "default": [
            API_ENDPOINT_PRESET_INFO,  # getPresetInfo
        ],
        "audio_pro_mkii": [],  # Not supported (returns 404)
        "audio_pro_w_generation": [
            API_ENDPOINT_PRESET_INFO,  # May be supported (probe to confirm)
        ],
        "audio_pro_original": [],  # May not be supported
    },
    # Playback control endpoints are generally universal
    ENDPOINT_PLAY: {
        "default": [API_ENDPOINT_PLAY],
    },
    ENDPOINT_PAUSE: {
        "default": [API_ENDPOINT_PAUSE],
    },
    ENDPOINT_STOP: {
        "default": [API_ENDPOINT_STOP],
    },
    ENDPOINT_NEXT: {
        "default": [API_ENDPOINT_NEXT],
    },
    ENDPOINT_PREV: {
        "default": [API_ENDPOINT_PREV],
    },
    ENDPOINT_VOLUME: {
        "default": [API_ENDPOINT_VOLUME],
        # Note: Audio Pro MkII may not support HTTP volume (use UPnP)
    },
    ENDPOINT_MUTE: {
        "default": [API_ENDPOINT_MUTE],
    },
    ENDPOINT_SEEK: {
        "default": [API_ENDPOINT_SEEK],
    },
    # Multiroom endpoints
    ENDPOINT_GROUP_SLAVES: {
        "default": [API_ENDPOINT_GROUP_SLAVES],
    },
    ENDPOINT_GROUP_EXIT: {
        "default": [API_ENDPOINT_GROUP_EXIT],
    },
    # Audio output endpoints
    ENDPOINT_AUDIO_OUTPUT_STATUS: {
        "default": [API_ENDPOINT_AUDIO_OUTPUT_STATUS],
        "audio_pro_mkii": [],  # Limited support (probe to confirm)
    },
    ENDPOINT_AUDIO_OUTPUT_SET: {
        "default": [API_ENDPOINT_AUDIO_OUTPUT_SET],
        "audio_pro_mkii": [],  # Limited support (probe to confirm)
    },
}


class EndpointResolver:
    """Resolve logical endpoint names to actual endpoint paths with fallback chains.

    Handles vendor-specific and generation-specific endpoint variations.
    """

    def __init__(self, capabilities: dict[str, Any]):
        """Initialize resolver with device capabilities.

        Args:
            capabilities: Device capabilities including vendor, generation, firmware
        """
        self.capabilities = capabilities
        self.vendor = capabilities.get("vendor", VENDOR_LINKPLAY_GENERIC)
        self.generation = capabilities.get("audio_pro_generation")
        self.firmware = capabilities.get("firmware_version")

    def get_endpoint_chain(self, logical_name: str) -> list[str]:
        """Get ordered list of endpoint paths to try for a logical operation.

        Args:
            logical_name: Logical endpoint name (e.g., "player_status")

        Returns:
            List of endpoint paths to try in order (empty if unsupported)
        """
        if logical_name not in ENDPOINT_REGISTRY:
            return []  # Unknown endpoint

        endpoint_variants = ENDPOINT_REGISTRY[logical_name]

        # Determine variant key based on vendor and generation
        variant_key = self._get_variant_key()

        # Try variant-specific chain first
        if variant_key in endpoint_variants:
            chain = endpoint_variants[variant_key]
            if chain:  # Not empty (not unsupported)
                return chain

        # Fallback to default chain
        if "default" in endpoint_variants:
            return endpoint_variants["default"]

        # No endpoint found - return empty (unsupported)
        return []

    def _get_variant_key(self) -> str:
        """Get variant key based on vendor and generation.

        Returns:
            Variant key string for endpoint registry lookup
        """
        if self.vendor == VENDOR_AUDIO_PRO:
            if self.generation == "mkii":
                return "audio_pro_mkii"
            elif self.generation == "w_generation":
                return "audio_pro_w_generation"
            elif self.generation == "original":
                return "audio_pro_original"
            return "audio_pro_default"
        elif self.vendor == VENDOR_ARYLIC:
            return "arylic"
        elif self.vendor == VENDOR_WIIM:
            return "default"  # WiiM uses default endpoints
        else:
            return "default"

    def is_endpoint_supported(self, logical_name: str) -> bool:
        """Check if endpoint is supported for this device.

        Args:
            logical_name: Logical endpoint name

        Returns:
            True if endpoint has at least one variant available
        """
        chain = self.get_endpoint_chain(logical_name)
        return len(chain) > 0


__all__ = [
    "ENDPOINT_PLAYER_STATUS",
    "ENDPOINT_DEVICE_STATUS",
    "ENDPOINT_METADATA",
    "ENDPOINT_PLAY",
    "ENDPOINT_PAUSE",
    "ENDPOINT_STOP",
    "ENDPOINT_NEXT",
    "ENDPOINT_PREV",
    "ENDPOINT_VOLUME",
    "ENDPOINT_MUTE",
    "ENDPOINT_SEEK",
    "ENDPOINT_LED",
    "ENDPOINT_LED_BRIGHTNESS",
    "ENDPOINT_EQ_GET",
    "ENDPOINT_EQ_STATUS",
    "ENDPOINT_EQ_LIST",
    "ENDPOINT_EQ_PRESET",
    "ENDPOINT_PRESET_INFO",
    "ENDPOINT_PRESET",
    "ENDPOINT_GROUP_SLAVES",
    "ENDPOINT_GROUP_EXIT",
    "ENDPOINT_AUDIO_OUTPUT_STATUS",
    "ENDPOINT_AUDIO_OUTPUT_SET",
    "ENDPOINT_REGISTRY",
    "EndpointResolver",
]
