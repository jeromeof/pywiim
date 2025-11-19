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
        """Connect to a Bluetooth device by MAC address.

        Args:
            mac_address: MAC address of the Bluetooth device.
        """
        # Call API (raises on failure)
        await self.player.client.connect_bluetooth_device(mac_address)

        # Call callback to notify state change (bluetooth output changed)
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def disconnect_bluetooth_device(self) -> None:
        """Disconnect the currently connected Bluetooth device."""
        # Call API (raises on failure)
        await self.player.client.disconnect_bluetooth_device()

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
