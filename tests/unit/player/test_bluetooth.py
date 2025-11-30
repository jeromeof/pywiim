"""Unit tests for BluetoothControl.

Tests Bluetooth operations including history, connection, and scanning.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pywiim.exceptions import WiiMRequestError


class TestBluetoothControl:
    """Test BluetoothControl class."""

    @pytest.fixture
    def mock_player(self, mock_client):
        """Create a mock Player instance."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._bluetooth_history = []
        player._audio_output_status = None
        player._on_state_changed = None
        return player

    @pytest.fixture
    def bluetooth_control(self, mock_player):
        """Create a BluetoothControl instance."""
        from pywiim.player.bluetooth import BluetoothControl

        return BluetoothControl(mock_player)

    @pytest.mark.asyncio
    async def test_get_bluetooth_history(self, bluetooth_control, mock_player):
        """Test getting Bluetooth history."""
        expected_history = [
            {"name": "Device 1", "mac": "AA:BB:CC:DD:EE:01", "connected": False},
            {"name": "Device 2", "mac": "AA:BB:CC:DD:EE:02", "connected": True},
        ]
        mock_player.client.get_bluetooth_history = AsyncMock(return_value=expected_history)

        result = await bluetooth_control.get_bluetooth_history()

        assert result == expected_history
        mock_player.client.get_bluetooth_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_bluetooth_device_success(self, bluetooth_control, mock_player):
        """Test successful Bluetooth device connection."""
        mock_player.client.connect_bluetooth_device = AsyncMock()
        mock_player.refresh = AsyncMock()
        mock_player._on_state_changed = MagicMock()

        await bluetooth_control.connect_bluetooth_device("AA:BB:CC:DD:EE:01")

        mock_player.client.connect_bluetooth_device.assert_called_once_with("AA:BB:CC:DD:EE:01")
        mock_player.refresh.assert_called_once_with(full=True)
        mock_player._on_state_changed.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_bluetooth_device_unavailable(self, bluetooth_control, mock_player):
        """Test connection failure when device is unavailable."""
        error = WiiMRequestError("connectbta2dpsynk failed")
        mock_player.client.connect_bluetooth_device = AsyncMock(side_effect=error)
        mock_player.client.get_bluetooth_history = AsyncMock(return_value=[])
        mock_player.get_audio_output_status = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="unavailable"):
            await bluetooth_control.connect_bluetooth_device("AA:BB:CC:DD:EE:01")

    @pytest.mark.asyncio
    async def test_connect_bluetooth_device_error_refresh(self, bluetooth_control, mock_player):
        """Test connection error with refresh."""
        error = WiiMRequestError("Connection failed")
        mock_player.client.connect_bluetooth_device = AsyncMock(side_effect=error)
        mock_player.client.get_bluetooth_history = AsyncMock(
            return_value=[{"name": "Device", "mac": "AA:BB:CC:DD:EE:01"}]
        )
        mock_player.get_audio_output_status = AsyncMock(return_value={"mode": "hardware"})
        mock_player._on_state_changed = MagicMock()

        with pytest.raises(WiiMRequestError):
            await bluetooth_control.connect_bluetooth_device("AA:BB:CC:DD:EE:01")

        # Should have refreshed history and audio output
        assert mock_player._bluetooth_history is not None
        mock_player._on_state_changed.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_bluetooth_device_refresh_fails(self, bluetooth_control, mock_player):
        """Test connection error when refresh fails."""
        error = WiiMRequestError("Connection failed")
        mock_player.client.connect_bluetooth_device = AsyncMock(side_effect=error)
        mock_player.client.get_bluetooth_history = AsyncMock(side_effect=Exception("Refresh error"))
        mock_player.get_audio_output_status = AsyncMock(side_effect=Exception("Refresh error"))

        # Should still raise the original error
        with pytest.raises(WiiMRequestError):
            await bluetooth_control.connect_bluetooth_device("AA:BB:CC:DD:EE:01")

    @pytest.mark.asyncio
    async def test_disconnect_bluetooth_device(self, bluetooth_control, mock_player):
        """Test disconnecting Bluetooth device."""
        mock_player.client.disconnect_bluetooth_device = AsyncMock()
        mock_player.refresh = AsyncMock()
        mock_player._on_state_changed = MagicMock()

        await bluetooth_control.disconnect_bluetooth_device()

        mock_player.client.disconnect_bluetooth_device.assert_called_once()
        mock_player.refresh.assert_called_once_with(full=True)
        mock_player._on_state_changed.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_bluetooth_pair_status(self, bluetooth_control, mock_player):
        """Test getting Bluetooth pair status."""
        expected_status = {"pairing": False, "device": None}
        mock_player.client.get_bluetooth_pair_status = AsyncMock(return_value=expected_status)

        result = await bluetooth_control.get_bluetooth_pair_status()

        assert result == expected_status
        mock_player.client.get_bluetooth_pair_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_for_bluetooth_devices(self, bluetooth_control, mock_player):
        """Test scanning for Bluetooth devices."""
        expected_devices = [
            {"name": "New Device", "mac": "AA:BB:CC:DD:EE:03", "rssi": -70},
        ]
        mock_player.client.scan_for_bluetooth_devices = AsyncMock(return_value=expected_devices)

        result = await bluetooth_control.scan_for_bluetooth_devices(duration=5)

        assert result == expected_devices
        mock_player.client.scan_for_bluetooth_devices.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_scan_for_bluetooth_devices_default_duration(self, bluetooth_control, mock_player):
        """Test scanning with default duration."""
        mock_player.client.scan_for_bluetooth_devices = AsyncMock(return_value=[])

        await bluetooth_control.scan_for_bluetooth_devices()

        mock_player.client.scan_for_bluetooth_devices.assert_called_once_with(3)
