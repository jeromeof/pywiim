"""Bluetooth operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import Player


class BluetoothControl:
    """Manages Bluetooth operations."""

    def __init__(self, player: Player) -> None:
        """Initialize Bluetooth control.

        Args:
            player: Parent Player instance.
        """
        self.player = player

    async def get_bluetooth_history(self) -> list[dict[str, Any]]:
        """Get Bluetooth connection history (previously paired devices)."""
        return await self.player.client.get_bluetooth_history()

    async def connect_bluetooth_device(self, mac_address: str) -> None:
        """Connect to a Bluetooth output device (Audio Sink) by MAC address.

        This connects to a Bluetooth device that will be used as an audio output,
        not an input source. The device must be an Audio Sink (output device) from
        the Bluetooth history.

        Args:
            mac_address: MAC address of the Bluetooth output device.

        Raises:
            ValueError: If the Bluetooth device is unavailable (powered off, out of range, etc.)
            WiiMRequestError: If the connection request fails for other reasons
        """
        from ..exceptions import WiiMRequestError

        try:
            # Call API (raises on failure)
            await self.player.client.connect_bluetooth_device(mac_address)
        except WiiMRequestError as err:
            # Refresh BT history to get latest device status
            # The device may have been removed or connection status changed
            try:
                bluetooth_history = await self.player.client.get_bluetooth_history()
                self.player._bluetooth_history = bluetooth_history if bluetooth_history else []
            except Exception:
                # If refresh fails, continue with error handling
                pass

            # Refresh audio output status to get current state after connection failure
            # This ensures we show the actual current output (likely hardware mode) rather than stale BT state
            # Use player-level method which automatically updates the cache
            try:
                await self.player.get_audio_output_status()
            except Exception:
                # If refresh fails, clear cache to avoid showing stale state
                self.player._audio_output_status = None

            # Notify integrations that state changed (audio output status was refreshed)
            # Even though BT connection failed, the output mode may have changed
            if self.player._on_state_changed:
                self.player._on_state_changed()

            # Provide clearer error message for connection failures
            # This often happens when the BT device is powered off, out of range, or unavailable
            error_msg = str(err)
            if "connectbta2dpsynk" in error_msg.lower():
                raise ValueError(
                    f"Bluetooth device {mac_address} is unavailable. "
                    "The device may be powered off, out of range, or not responding. "
                    "Please ensure the device is on and in range, then try again."
                ) from err
            # Re-raise other request errors as-is
            raise

        # Refresh to update audio output status cache and BT history
        # Use full=True to ensure audio output status and BT history are fetched
        await self.player.refresh(full=True)

        # Call callback to notify state change (bluetooth output changed)
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def disconnect_bluetooth_device(self) -> None:
        """Disconnect the currently connected Bluetooth output device.

        This disconnects the Bluetooth device that is currently being used as
        an audio output (Audio Sink), not an input source.
        """
        # Call API (raises on failure)
        await self.player.client.disconnect_bluetooth_device()

        # Refresh to update audio output status cache
        # Use full=True to ensure audio output status is fetched
        await self.player.refresh(full=True)

        # Call callback to notify state change (bluetooth output disconnected)
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def get_bluetooth_pair_status(self) -> dict[str, Any]:
        """Get Bluetooth pairing status."""
        return await self.player.client.get_bluetooth_pair_status()

    async def scan_for_bluetooth_devices(self, duration: int = 3) -> list[dict[str, Any]]:
        """Scan for nearby Bluetooth devices.

        Args:
            duration: Scan duration in seconds (default: 3).
        """
        return await self.player.client.scan_for_bluetooth_devices(duration)
