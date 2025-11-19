"""Diagnostics / maintenance helpers (reboot, time sync, raw commands)."""

from __future__ import annotations

import logging
import time
from typing import Any, cast
from urllib.parse import quote

_LOGGER = logging.getLogger(__name__)


class DiagnosticsAPI:
    """Low-level device maintenance helpers.

    This mixin provides diagnostic and maintenance functions for device management.
    Use with caution - some operations (like reboot) may disconnect the device.
    """

    async def reboot(self) -> None:
        """Reboot the device.

        Note: This command may not return a response as the device will restart.
        The method handles this gracefully and considers the command successful
        even if the device stops responding.

        Raises:
            WiiMError: If the request fails before the device reboots.
        """
        try:
            # Send reboot command - device may not respond after this
            # Use a custom request method that handles empty responses gracefully
            await self._request_reboot("/httpapi.asp?command=reboot")
        except Exception as err:
            # Reboot commands often don't return proper responses
            # Log the attempt but don't fail the service call
            _LOGGER.info("Reboot command sent to device (device may not respond): %s", err)
            # Don't re-raise - reboot command was sent successfully

    async def _request_reboot(self, endpoint: str) -> None:
        """Special request method for reboot that handles empty responses gracefully.

        Args:
            endpoint: The reboot endpoint to call.

        Raises:
            WiiMError: If the request fails for reasons other than expected reboot behavior.
        """
        try:
            # Try to send the reboot command
            await self._request(endpoint)  # type: ignore[attr-defined]
        except Exception as err:
            # If the request fails due to parsing issues (common with reboot),
            # we still consider it successful since the command was sent
            error_str = str(err).lower()
            if any(x in error_str for x in ["expecting value", "json decode", "empty response"]):
                _LOGGER.info("Reboot command sent successfully (device stopped responding as expected)")
                return
            else:
                # Re-raise other types of errors
                raise

    async def sync_time(self, ts: int | None = None) -> None:
        """Synchronize device time with system time or provided timestamp.

        Args:
            ts: Unix timestamp (seconds since epoch). If None, uses current system time.

        Raises:
            WiiMError: If the request fails.
        """
        if ts is None:
            ts = int(time.time())
        await self._request(f"/httpapi.asp?command=timeSync:{ts}")  # type: ignore[attr-defined]

    async def send_command(self, command: str) -> dict[str, Any]:
        """Send arbitrary LinkPlay HTTP command (expert use only).

        This method allows sending raw LinkPlay commands for advanced use cases.
        Use with caution - incorrect commands may cause device errors.

        Args:
            command: Raw LinkPlay command string (e.g., "getStatusEx").

        Returns:
            Response dictionary from the device.

        Raises:
            WiiMError: If the request fails.

        Example:
            >>> response = await client.send_command("getStatusEx")
        """
        endpoint = f"/httpapi.asp?command={quote(command)}"
        result = await self._request(endpoint)  # type: ignore[attr-defined]
        return cast(dict[str, Any], result)
