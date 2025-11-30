"""Unit tests for DiagnosticsCollector.

Tests device maintenance operations including reboot and time sync.
"""

from unittest.mock import AsyncMock

import pytest

from pywiim.models import PlayerStatus


class TestDiagnosticsCollector:
    """Test DiagnosticsCollector class."""

    @pytest.fixture
    def mock_player(self, mock_client):
        """Create a mock Player instance."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._status_model = PlayerStatus()
        player._available = True
        return player

    @pytest.fixture
    def diagnostics(self, mock_player):
        """Create a DiagnosticsCollector instance."""
        from pywiim.player.diagnostics import DiagnosticsCollector

        return DiagnosticsCollector(mock_player)

    @pytest.mark.asyncio
    async def test_reboot(self, diagnostics, mock_player):
        """Test rebooting device."""
        mock_player.client.reboot = AsyncMock()

        await diagnostics.reboot()

        mock_player.client.reboot.assert_called_once()
        assert mock_player._available is False

    @pytest.mark.asyncio
    async def test_sync_time(self, diagnostics, mock_player):
        """Test syncing device time with timestamp."""
        mock_player.client.sync_time = AsyncMock()

        await diagnostics.sync_time(1234567890)

        mock_player.client.sync_time.assert_called_once_with(1234567890)

    @pytest.mark.asyncio
    async def test_sync_time_no_timestamp(self, diagnostics, mock_player):
        """Test syncing device time without timestamp (uses current time)."""
        mock_player.client.sync_time = AsyncMock()

        await diagnostics.sync_time()

        # Should be called with None (client will use current time)
        mock_player.client.sync_time.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_reboot_propagates_errors(self, diagnostics, mock_player):
        """Test that reboot errors are properly propagated."""
        from pywiim.exceptions import WiiMRequestError

        api_error = WiiMRequestError("Reboot failed")
        mock_player.client.reboot = AsyncMock(side_effect=api_error)

        with pytest.raises(WiiMRequestError) as exc_info:
            await diagnostics.reboot()

        assert exc_info.value == api_error
        # _available should still be set to False even if error occurs
        # (reboot command was sent, device may be rebooting)

    @pytest.mark.asyncio
    async def test_sync_time_propagates_errors(self, diagnostics, mock_player):
        """Test that sync_time errors are properly propagated."""
        from pywiim.exceptions import WiiMRequestError

        api_error = WiiMRequestError("Time sync failed")
        mock_player.client.sync_time = AsyncMock(side_effect=api_error)

        with pytest.raises(WiiMRequestError) as exc_info:
            await diagnostics.sync_time(1234567890)

        assert exc_info.value == api_error
