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


class TestMultiroomDiagnostics:
    """Test multiroom-specific diagnostics."""

    @pytest.fixture
    def mock_player(self, mock_client):
        """Create a mock Player instance with device info."""
        from pywiim.models import DeviceInfo
        from pywiim.player import Player

        player = Player(mock_client)
        player._device_info = DeviceInfo(
            uuid="uuid:FF31F09EFFF1D2BB4FDE2B3F",
            name="Test Device",
            model="WiiM Pro",
            firmware="4.8.731953",
        )
        player._detected_role = "solo"
        return player

    @pytest.fixture
    def diagnostics(self, mock_player):
        """Create a DiagnosticsCollector instance."""
        from pywiim.player.diagnostics import DiagnosticsCollector

        return DiagnosticsCollector(mock_player)

    @pytest.mark.asyncio
    async def test_multiroom_diagnostics_basic(self, diagnostics, mock_player):
        """Test basic multiroom diagnostics collection."""
        from pywiim.api.group import DeviceGroupInfo

        # Mock API responses
        mock_player.client.get_device_group_info = AsyncMock(
            return_value=DeviceGroupInfo(
                role="solo",
                master_host=None,
                master_uuid=None,
                slave_hosts=[],
                slave_uuids=[],
                slave_count=0,
            )
        )
        mock_player.client.get_slaves_info = AsyncMock(return_value=[])

        result = await diagnostics.get_multiroom_diagnostics()

        assert "this_device" in result
        assert result["this_device"]["host"] == mock_player.host
        assert result["this_device"]["uuid"] == mock_player.uuid
        assert result["this_device"]["role"] == "solo"
        assert result["callbacks"]["player_finder_set"] is False
        assert result["callbacks"]["all_players_finder_set"] is False

    @pytest.mark.asyncio
    async def test_multiroom_diagnostics_wifi_direct_detection(self, diagnostics, mock_player):
        """Test WiFi Direct scenario detection (10.10.10.x IPs)."""
        from pywiim.api.group import DeviceGroupInfo

        # Mock as master with WiFi Direct slaves
        mock_player._detected_role = "master"
        mock_player.client.get_device_group_info = AsyncMock(
            return_value=DeviceGroupInfo(
                role="master",
                master_host=mock_player.host,
                master_uuid=None,
                slave_hosts=["10.10.10.92", "10.10.10.93"],
                slave_uuids=["uuid:ABC123", "uuid:DEF456"],
                slave_count=2,
            )
        )
        mock_player.client.get_slaves_info = AsyncMock(
            return_value=[
                {"ip": "10.10.10.92", "uuid": "uuid:ABC123", "name": "Slave1"},
                {"ip": "10.10.10.93", "uuid": "uuid:DEF456", "name": "Slave2"},
            ]
        )

        result = await diagnostics.get_multiroom_diagnostics()

        # Should detect WiFi Direct scenario in analysis
        assert "linking_analysis" in result
        issues = result["linking_analysis"]["issues"]
        assert any("WiFi Direct detected" in issue for issue in issues)
        assert any("10.10.10.x" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_multiroom_diagnostics_all_players_finder(self, diagnostics, mock_player):
        """Test diagnostics with all_players_finder callback."""
        from unittest.mock import MagicMock

        from pywiim.api.group import DeviceGroupInfo
        from pywiim.models import DeviceInfo

        # Create another player (potential slave)
        other_player = MagicMock()
        other_player.host = "192.168.1.101"
        other_player.uuid = "uuid:ABC123"
        other_player.name = "Other Device"
        other_player._detected_role = "solo"
        other_player._device_info = DeviceInfo(uuid="uuid:ABC123")

        # Set up all_players_finder
        mock_player._all_players_finder = MagicMock(return_value=[mock_player, other_player])

        # Mock API responses
        mock_player.client.get_device_group_info = AsyncMock(
            return_value=DeviceGroupInfo(
                role="solo",
                master_host=None,
                master_uuid=None,
                slave_hosts=[],
                slave_uuids=[],
                slave_count=0,
            )
        )
        mock_player.client.get_slaves_info = AsyncMock(return_value=[])

        result = await diagnostics.get_multiroom_diagnostics()

        assert result["callbacks"]["all_players_finder_set"] is True
        assert "all_known_players" in result
        assert isinstance(result["all_known_players"], list)
        assert len(result["all_known_players"]) == 2

    @pytest.mark.asyncio
    async def test_multiroom_diagnostics_linking_analysis(self, diagnostics, mock_player):
        """Test linking analysis with UUID matching."""
        from unittest.mock import MagicMock

        from pywiim.api.group import DeviceGroupInfo
        from pywiim.models import DeviceInfo

        # Create slave player with matching UUID
        slave_player = MagicMock()
        slave_player.host = "192.168.1.101"
        slave_player.uuid = "uuid:ABC123"
        slave_player.name = "Slave Device"
        slave_player._detected_role = "solo"
        slave_player._device_info = DeviceInfo(uuid="uuid:ABC123")

        # Set up as master with slave in API
        mock_player._detected_role = "master"
        mock_player._all_players_finder = MagicMock(return_value=[mock_player, slave_player])

        mock_player.client.get_device_group_info = AsyncMock(
            return_value=DeviceGroupInfo(
                role="master",
                master_host=mock_player.host,
                master_uuid=None,
                slave_hosts=["10.10.10.92"],
                slave_uuids=["uuid:ABC123"],
                slave_count=1,
            )
        )
        mock_player.client.get_slaves_info = AsyncMock(
            return_value=[{"ip": "10.10.10.92", "uuid": "uuid:ABC123", "name": "Slave1"}]
        )

        result = await diagnostics.get_multiroom_diagnostics()

        # Should find UUID match
        analysis = result["linking_analysis"]
        assert any("UUID matches found" in issue for issue in analysis["issues"])

    def test_normalize_uuid(self, diagnostics):
        """Test UUID normalization for comparison."""
        # Test various UUID formats
        assert diagnostics._normalize_uuid("uuid:ABC123") == "abc123"
        assert diagnostics._normalize_uuid("ABC123") == "abc123"
        assert diagnostics._normalize_uuid("abc-123-def") == "abc123def"
        assert diagnostics._normalize_uuid("uuid:ABC-123-DEF") == "abc123def"
        assert diagnostics._normalize_uuid("UUID:FF31F09E-FFF1-D2BB-4FDE-2B3F") == "ff31f09efff1d2bb4fde2b3f"
