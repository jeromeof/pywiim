"""Equaliser (EQ) helpers for WiiM HTTP client.

This mixin handles preset selection, custom 10-band EQ upload, enable/disable,
and querying current EQ status and the list of presets.

It assumes the base client provides the `_request` coroutine. No state is stored –
all results come from the device each call.
"""

from __future__ import annotations

from typing import Any, cast

from .constants import (
    API_ENDPOINT_EQ_CUSTOM,
    API_ENDPOINT_EQ_GET,
    API_ENDPOINT_EQ_LIST,
    API_ENDPOINT_EQ_OFF,
    API_ENDPOINT_EQ_ON,
    API_ENDPOINT_EQ_PRESET,
    API_ENDPOINT_EQ_STATUS,
    EQ_PRESET_MAP,
)


class EQAPI:
    """Equaliser helpers (presets, on/off, custom bands).

    This mixin provides methods for managing the device's equalizer settings,
    including presets, custom 10-band EQ, and enable/disable functionality.
    """

    # ------------------------------------------------------------------
    # Preset handling
    # ------------------------------------------------------------------

    async def set_eq_preset(self, preset: str) -> None:
        """Apply a named EQ preset (e.g. "rock", "flat").

        Args:
            preset: Preset name (must be a key in EQ_PRESET_MAP).

        Raises:
            ValueError: If preset name is invalid.
            WiiMError: If the request fails.
        """
        if preset not in EQ_PRESET_MAP:
            raise ValueError(f"Invalid EQ preset: {preset}")
        api_value = EQ_PRESET_MAP[preset]  # convert key → label
        await self._request(f"{API_ENDPOINT_EQ_PRESET}{api_value}")  # type: ignore[attr-defined]

    async def get_eq_presets(self) -> list[str]:
        """Get list of available EQ presets from the device.

        Returns:
            List of preset names available on the device.

        Raises:
            WiiMError: If the request fails.
        """
        resp = await self._request(API_ENDPOINT_EQ_LIST)  # type: ignore[attr-defined]

        # Handle direct list response (most common)
        if isinstance(resp, list):
            # Ensure all items are strings
            return [str(item) for item in resp if item]

        # Handle dict response (some devices wrap the list)
        if isinstance(resp, dict):
            # Check common keys that might contain the list
            for key in ["EQList", "eq_list", "list", "presets", "preset_list"]:
                if key in resp and isinstance(resp[key], list):
                    # Ensure all items are strings
                    return [str(item) for item in resp[key] if item]
            # If no list found in dict, return empty
            return []

        # Fallback for unexpected types
        return []

    # ------------------------------------------------------------------
    # Custom 10-band upload
    # ------------------------------------------------------------------

    async def set_eq_custom(self, eq_values: list[int]) -> None:
        """Upload custom 10-band EQ in LinkPlay format (list of 10 ints).

        Args:
            eq_values: List of exactly 10 integer values for the EQ bands.

        Raises:
            ValueError: If eq_values doesn't have exactly 10 bands.
            WiiMError: If the request fails.
        """
        if len(eq_values) != 10:
            raise ValueError("EQ must have exactly 10 bands")
        eq_str = ",".join(str(v) for v in eq_values)
        await self._request(f"{API_ENDPOINT_EQ_CUSTOM}{eq_str}")  # type: ignore[attr-defined]

    async def get_eq(self) -> dict[str, Any]:
        """Get current EQ band values.

        Returns:
            Dictionary containing current EQ band values.

        Raises:
            WiiMError: If the request fails.
        """
        result = await self._request(API_ENDPOINT_EQ_GET)  # type: ignore[attr-defined]
        return cast(dict[str, Any], result)

    # ------------------------------------------------------------------
    # Enable / disable
    # ------------------------------------------------------------------

    async def set_eq_enabled(self, enabled: bool) -> None:
        """Enable or disable the EQ.

        Args:
            enabled: True to enable EQ, False to disable.

        Raises:
            WiiMError: If the request fails.
        """
        await self._request(API_ENDPOINT_EQ_ON if enabled else API_ENDPOINT_EQ_OFF)  # type: ignore[attr-defined]

    async def get_eq_status(self) -> bool:
        """Return True if device reports EQ enabled (best-effort).

        This method attempts to determine if EQ is enabled by checking
        the EQ status endpoint. If that fails, it tries to get EQ band
        values as a fallback.

        Returns:
            True if EQ appears to be enabled, False otherwise.
        """
        try:
            response = await self._request(API_ENDPOINT_EQ_STATUS)  # type: ignore[attr-defined]
            if "EQStat" in response:
                return str(response["EQStat"]).lower() == "on"
            if str(response.get("status", "")).lower() == "failed":
                # heuristic: if EQGetBand succeeds, EQ subsystem exists – treat as enabled
                try:
                    response = await self._request(API_ENDPOINT_EQ_GET)  # type: ignore[attr-defined]
                    # Verify we got a valid response (not "unknown command")
                    if isinstance(response, dict) and response.get("status") == "OK":
                        return True
                    return False
                except Exception:  # noqa: BLE001
                    return False
            return False
        except Exception:  # noqa: BLE001
            return False
