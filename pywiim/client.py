"""Main WiiM client facade.

This module provides the main WiiMClient class that composes all API mixins
into a single, unified interface for communicating with WiiM and LinkPlay devices.
"""

from __future__ import annotations

import logging
import ssl
from typing import Any

from aiohttp import ClientSession

from .api.audio_settings import AudioSettingsAPI
from .api.base import BaseWiiMClient
from .api.bluetooth import BluetoothAPI
from .api.device import DeviceAPI
from .api.diagnostics import DiagnosticsAPI
from .api.eq import EQAPI
from .api.firmware import FirmwareAPI
from .api.group import GroupAPI
from .api.lms import LMSAPI
from .api.misc import MiscAPI
from .api.playback import PlaybackAPI
from .api.preset import PresetAPI
from .api.timer import TimerAPI
from .capabilities import WiiMCapabilities, detect_device_capabilities
from .exceptions import (
    WiiMConnectionError,
    WiiMError,
    WiiMInvalidDataError,
    WiiMRequestError,
    WiiMResponseError,
    WiiMTimeoutError,
)
from .models import DeviceInfo

_LOGGER = logging.getLogger(__name__)


class WiiMClient(
    BluetoothAPI,
    AudioSettingsAPI,
    LMSAPI,
    MiscAPI,
    DeviceAPI,
    PlaybackAPI,
    EQAPI,
    GroupAPI,
    PresetAPI,
    DiagnosticsAPI,
    FirmwareAPI,
    TimerAPI,
    BaseWiiMClient,
):
    """Unified WiiM HTTP API client – modular with official and unofficial endpoints.

    This client includes both official WiiM HTTP API endpoints and unofficial
    reverse-engineered endpoints. The unofficial endpoints may not be available
    on all firmware versions or device models.

    The client automatically detects device capabilities and adapts its behavior
    accordingly. It supports multiple LinkPlay-based device vendors including:
    - WiiM devices (Pro, Mini, Amp, Ultra)
    - Arylic devices (Up2Stream, S10+)
    - Audio Pro devices (Addon C5/C10, MkII, W-Generation)
    - Generic LinkPlay devices

    Example:
        ```python
        import asyncio
        from pywiim import WiiMClient

        async def main():
            # Create client
            client = WiiMClient("192.168.1.100")

            # Detect capabilities (optional, done automatically on first request)
            device_info = await client.get_device_info_model()
            capabilities = await client._detect_capabilities()

            # Use the client
            status = await client.get_player_status()
            await client.set_volume(0.5)
            await client.play()

            # Clean up
            await client.close()

        asyncio.run(main())
        ```

    Args:
        host: Device hostname or IP address. May include port (e.g., "192.168.1.100:8080").
        port: Optional port override (default: 80 for HTTP, 443 for HTTPS).
        timeout: Network timeout in seconds (default: 5.0).
        ssl_context: Custom SSL context for advanced use cases.
        session: Optional shared aiohttp ClientSession for connection pooling.
        capabilities: Optional pre-detected device capabilities dict.
            If not provided, capabilities will be detected automatically on first use.

    Attributes:
        capabilities: Device capabilities dictionary (read-only).
        host: Device hostname or IP address (read-only).
        base_url: Base URL used for the last successful request (read-only).
    """

    def __init__(
        self,
        host: str,
        port: int | None = None,
        protocol: str | None = None,
        timeout: float = 5.0,
        ssl_context: ssl.SSLContext | None = None,
        session: ClientSession | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the WiiM client.

        Args:
            host: Device hostname or IP address
            port: Optional port override. If None, will probe standard ports.
            protocol: Optional protocol override ("http" or "https"). If None, will probe both.
            timeout: Network timeout in seconds
            ssl_context: Custom SSL context for advanced use cases
            session: Optional shared aiohttp ClientSession
            capabilities: Optional pre-detected device capabilities
        """
        super().__init__(host, port, protocol, timeout, ssl_context, session, capabilities)

        # Capability detection system
        self._capability_detector = WiiMCapabilities()
        self._capabilities_detected = capabilities is not None
        self._detecting_capabilities = False  # Flag to prevent recursion

    async def _detect_capabilities(self) -> dict[str, Any]:
        """Detect device capabilities and update client configuration.

        This method is called automatically on first use if capabilities were not
        provided during initialization. It probes the device to determine:
        - Device type (WiiM, Arylic, Audio Pro, etc.)
        - Firmware version
        - Supported endpoints
        - Protocol preferences
        - Generation-specific quirks

        Returns:
            Dictionary of detected capabilities.

        Raises:
            WiiMError: If capability detection fails.
        """
        if self._capabilities_detected:
            return self._capabilities

        try:
            # Get device info first (use base class method to avoid recursion)
            device_info = await BaseWiiMClient.get_device_info_model(self)

            # Detect capabilities using the capability detector
            capabilities = await self._capability_detector.detect_capabilities(self, device_info)

            # Ensure vendor is normalized (safety check)
            from .normalize import normalize_vendor

            if "vendor" in capabilities:
                capabilities["vendor"] = normalize_vendor(capabilities["vendor"])
            elif "vendor" not in capabilities or not capabilities.get("vendor"):
                # Fallback: detect vendor if missing
                from .capabilities import detect_vendor

                vendor = detect_vendor(device_info)
                capabilities["vendor"] = normalize_vendor(vendor)

            # Update client capabilities
            self._capabilities.update(capabilities)

            # Update timeout based on capabilities
            if "response_timeout" in capabilities:
                self.timeout = capabilities["response_timeout"]

            self._capabilities_detected = True
            # Capabilities are already logged in capabilities.py with more detail
            # Only log at debug level here to avoid duplicate messages
            _LOGGER.debug(
                "Capabilities applied to client for %s: vendor=%s, generation=%s",
                self.host,
                capabilities.get("vendor", "unknown"),
                capabilities.get("audio_pro_generation", "unknown"),
            )

            return self._capabilities

        except Exception as err:
            _LOGGER.warning(
                "Failed to detect capabilities for %s: %s. Using defaults.",
                self.host,
                err,
            )
            # Fall back to static detection
            try:
                device_info = await BaseWiiMClient.get_device_info_model(self)
                capabilities = detect_device_capabilities(device_info)
                # Ensure vendor is set in static detection
                from .capabilities import detect_vendor
                from .normalize import normalize_vendor

                if "vendor" not in capabilities or not capabilities.get("vendor"):
                    vendor = detect_vendor(device_info)
                    capabilities["vendor"] = normalize_vendor(vendor)
                else:
                    capabilities["vendor"] = normalize_vendor(capabilities["vendor"])
                self._capabilities.update(capabilities)
                self._capabilities_detected = True
                return self._capabilities
            except Exception:
                # If even static detection fails, use empty capabilities
                self._capabilities_detected = True
                return self._capabilities

    async def get_device_info_model(self) -> DeviceInfo:
        """Get device information as a Pydantic model.

        This method automatically triggers capability detection on first use
        if capabilities were not provided during initialization.

        Returns:
            DeviceInfo model with device information.

        Raises:
            WiiMError: If the request fails.
        """
        # Auto-detect capabilities on first use if not already detected
        if not self._capabilities_detected and not self._detecting_capabilities:
            # Use flag to prevent recursion instead of setting _capabilities_detected
            self._detecting_capabilities = True
            try:
                await self._detect_capabilities()
            except Exception:
                # If detection fails, reset flag and re-raise
                self._detecting_capabilities = False
                raise
            finally:
                self._detecting_capabilities = False

        # Call parent method (BaseWiiMClient)
        return await BaseWiiMClient.get_device_info_model(self)

    async def get_player_status(self) -> dict[str, Any]:
        """Get player status with automatic capability detection.

        This method automatically triggers capability detection on first use
        if capabilities were not provided during initialization.

        Returns:
            Dictionary with player status information.

        Raises:
            WiiMError: If the request fails.
        """
        # Auto-detect capabilities on first use if not already detected
        if not self._capabilities_detected and not self._detecting_capabilities:
            # Use flag to prevent recursion instead of setting _capabilities_detected
            self._detecting_capabilities = True
            try:
                await self._detect_capabilities()
            except Exception:
                # If detection fails, reset flag and re-raise
                self._detecting_capabilities = False
                raise
            finally:
                self._detecting_capabilities = False

        # Call parent method (BaseWiiMClient)
        return await BaseWiiMClient.get_player_status(self)

    async def close(self) -> None:
        """Close the client and clean up resources.

        This method should be called when the client is no longer needed.
        It closes the HTTP session and cleans up any resources.
        """
        await BaseWiiMClient.close(self)


# Export exceptions for convenience
__all__ = [
    "WiiMClient",
    "WiiMError",
    "WiiMRequestError",
    "WiiMResponseError",
    "WiiMTimeoutError",
    "WiiMConnectionError",
    "WiiMInvalidDataError",
]
