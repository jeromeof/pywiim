"""Unit tests for GroupOperations.

Tests group operations including metadata propagation and master name lookup.
"""

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from pywiim.models import DeviceInfo, PlayerStatus


class TestGroupOperations:
    """Test GroupOperations class."""

    @pytest.fixture
    def mock_player(self, mock_client):
        """Create a mock Player instance."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._status_model = PlayerStatus()
        player._device_info = None
        player._group = None
        player._state_synchronizer = MagicMock()
        player._state_synchronizer.update_from_http = MagicMock()
        return player

    @pytest.fixture
    def group_ops(self, mock_player):
        """Create a GroupOperations instance."""
        from pywiim.player.groupops import GroupOperations

        return GroupOperations(mock_player)

    @pytest.mark.asyncio
    async def test_get_master_name_from_group(self, group_ops, mock_player):
        """Test getting master name from group."""
        from pywiim.group import Group

        master = MagicMock()
        master._device_info = DeviceInfo(uuid="master-uuid", name="Master Device")
        master.name = "Master Device"
        master.host = "192.168.1.200"
        master.refresh = AsyncMock()
        group = Group(master)
        mock_player._group = group

        result = await group_ops.get_master_name()

        assert result == "Master Device"

    @pytest.mark.asyncio
    async def test_get_master_name_from_group_refreshes(self, group_ops, mock_player):
        """Test getting master name refreshes master if needed."""
        from pywiim.group import Group

        master = MagicMock()
        master._device_info = None
        master.name = None
        master.host = "192.168.1.200"
        master.refresh = AsyncMock()
        group = Group(master)
        mock_player._group = group

        await group_ops.get_master_name()

        master.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_master_name_from_device_info(self, group_ops, mock_player):
        """Test getting master name from device info."""
        device_info = DeviceInfo(uuid="test-uuid", master_ip="192.168.1.200")
        mock_player._device_info = device_info
        with patch("pywiim.client.WiiMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_device_name = AsyncMock(return_value="Master Device")
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await group_ops.get_master_name()

            assert result == "Master Device"
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_master_name_from_device_info_fallback(self, group_ops, mock_player):
        """Test getting master name falls back to IP when name fetch fails."""
        device_info = DeviceInfo(uuid="test-uuid", master_ip="192.168.1.200")
        mock_player._device_info = device_info
        with patch("pywiim.client.WiiMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_device_name = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await group_ops.get_master_name()

            assert result == "192.168.1.200"
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_master_name_none(self, group_ops, mock_player):
        """Test getting master name when no group or device info."""
        result = await group_ops.get_master_name()

        assert result is None

    def test_propagate_metadata_to_slaves(self, group_ops, mock_player):
        """Test propagating metadata to slaves."""
        from pywiim.group import Group

        slave = MagicMock()
        slave._status_model = PlayerStatus()
        slave._state_synchronizer = MagicMock()
        slave._state_synchronizer.update_from_http = MagicMock()
        slave._on_state_changed = None
        slave.host = "192.168.1.101"
        slave._group = None
        group = Group(mock_player)
        group.add_slave(slave)
        mock_player._group = group
        type(mock_player).is_master = PropertyMock(return_value=True)
        mock_player._status_model = PlayerStatus(
            title="Master Track",
            artist="Master Artist",
            album="Master Album",
            entity_picture="http://example.com/art.jpg",
        )

        group_ops.propagate_metadata_to_slaves()

        # Should update slave metadata
        assert slave._status_model.title == "Master Track"
        assert slave._status_model.artist == "Master Artist"
        assert slave._status_model.album == "Master Album"
        # Verify update_from_http was called with source="propagated"
        # Note: update_from_http may be called multiple times (e.g., for source field)
        # Check that at least one call has source="propagated"
        calls = slave._state_synchronizer.update_from_http.call_args_list
        propagated_call = None
        for call in calls:
            if len(call[1]) > 0 and call[1].get("source") == "propagated":
                propagated_call = call
                break
        assert propagated_call is not None, "update_from_http should have been called with source='propagated'"
        # Verify the call contains metadata
        assert "title" in propagated_call[0][0]
        assert propagated_call[0][0]["title"] == "Master Track"

    def test_propagate_metadata_to_slaves_not_master(self, group_ops, mock_player):
        """Test propagating metadata when not master."""
        type(mock_player).is_master = PropertyMock(return_value=False)

        group_ops.propagate_metadata_to_slaves()

        # Should return early, no updates

    def test_propagate_metadata_to_slaves_no_group(self, group_ops, mock_player):
        """Test propagating metadata when no group."""
        type(mock_player).is_master = PropertyMock(return_value=True)
        mock_player._group = None

        group_ops.propagate_metadata_to_slaves()

        # Should return early, no updates

    def test_propagate_metadata_to_slaves_no_slaves(self, group_ops, mock_player):
        """Test propagating metadata when no slaves."""
        from pywiim.group import Group

        type(mock_player).is_master = PropertyMock(return_value=True)
        group = Group(mock_player)
        mock_player._group = group

        group_ops.propagate_metadata_to_slaves()

        # Should return early, no updates

    def test_propagate_metadata_to_slaves_triggers_callback(self, group_ops, mock_player):
        """Test propagating metadata triggers callback on slave."""
        from pywiim.group import Group

        slave = MagicMock()
        slave._status_model = PlayerStatus()
        slave._state_synchronizer = MagicMock()
        slave._state_synchronizer.update_from_http = MagicMock()
        slave._on_state_changed = MagicMock()
        slave.host = "192.168.1.101"
        slave._group = None
        group = Group(mock_player)
        group.add_slave(slave)
        mock_player._group = group
        type(mock_player).is_master = PropertyMock(return_value=True)
        mock_player._status_model = PlayerStatus(title="Master Track", artist="Master Artist")

        group_ops.propagate_metadata_to_slaves()

        slave._on_state_changed.assert_called_once()

    def test_propagate_metadata_to_slaves_callback_error(self, group_ops, mock_player):
        """Test propagating metadata when callback raises error."""
        from pywiim.group import Group

        slave = MagicMock()
        slave._status_model = PlayerStatus()
        slave._state_synchronizer = MagicMock()
        slave._state_synchronizer.update_from_http = MagicMock()
        slave._on_state_changed = MagicMock(side_effect=Exception("Callback error"))
        slave.host = "192.168.1.101"
        slave._group = None
        group = Group(mock_player)
        group.add_slave(slave)
        mock_player._group = group
        type(mock_player).is_master = PropertyMock(return_value=True)
        mock_player._status_model = PlayerStatus(title="Master Track", artist="Master Artist")

        # Should not raise
        group_ops.propagate_metadata_to_slaves()

    def test_find_slave_player_by_host(self, group_ops, mock_player):
        """Test finding slave player by host/IP."""
        slave = MagicMock()
        slave.host = "192.168.1.101"
        mock_player._player_finder = MagicMock(return_value=slave)

        result = group_ops._find_slave_player("192.168.1.101", None)

        assert result == slave
        mock_player._player_finder.assert_called_with("192.168.1.101")

    def test_find_slave_player_by_uuid_fallback(self, group_ops, mock_player):
        """Test finding slave player by UUID when IP doesn't match.

        This handles WiFi Direct multiroom where slaves use internal 10.10.10.x IPs
        but HA knows them by their LAN IPs. UUID provides the fallback match.
        """
        slave = MagicMock()
        slave.host = "192.168.1.101"
        slave.uuid = "FF31F008-25D7-2F58-1507-DE05FF31F008"

        # First call with IP returns None (internal IP not known)
        # Second call with UUID returns the player
        mock_player._player_finder = MagicMock(side_effect=[None, slave])

        result = group_ops._find_slave_player(
            "10.10.10.92",  # Internal WiFi Direct IP
            "FF31F008-25D7-2F58-1507-DE05FF31F008",  # UUID for fallback
        )

        assert result == slave
        assert mock_player._player_finder.call_count == 2
        mock_player._player_finder.assert_any_call("10.10.10.92")
        mock_player._player_finder.assert_any_call("FF31F008-25D7-2F58-1507-DE05FF31F008")

    def test_find_slave_player_no_finder(self, group_ops, mock_player):
        """Test finding slave player when no player_finder is set."""
        mock_player._player_finder = None

        result = group_ops._find_slave_player("192.168.1.101", "some-uuid")

        assert result is None

    def test_find_slave_player_not_found(self, group_ops, mock_player):
        """Test finding slave player when not found by host or UUID."""
        mock_player._player_finder = MagicMock(return_value=None)

        result = group_ops._find_slave_player("10.10.10.92", "unknown-uuid")

        assert result is None
        assert mock_player._player_finder.call_count == 2


class TestCrossCoordinatorRoleInference:
    """Tests for cross-coordinator role inference in WiFi Direct multiroom."""

    @pytest.fixture
    def mock_player(self, mock_client):
        """Create a mock Player instance with UUID."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._status_model = PlayerStatus()
        player._device_info = DeviceInfo(uuid="SLAVE-UUID-1234")
        player._group = None
        player._detected_role = "solo"
        player._state_synchronizer = MagicMock()
        player._state_synchronizer.update_from_http = MagicMock()
        return player

    @pytest.fixture
    def group_ops(self, mock_player):
        """Create a GroupOperations instance."""
        from pywiim.player.groupops import GroupOperations

        return GroupOperations(mock_player)

    @pytest.mark.asyncio
    async def test_check_if_slave_no_all_players_finder(self, group_ops, mock_player):
        """Test cross-coordinator check returns None when all_players_finder not set."""
        mock_player._all_players_finder = None

        result = await group_ops._check_if_slave_of_any_master()

        assert result is None

    @pytest.mark.asyncio
    async def test_check_if_slave_no_uuid(self, group_ops, mock_player):
        """Test cross-coordinator check returns None when player has no UUID."""
        mock_player._all_players_finder = MagicMock(return_value=[])
        mock_player._device_info = None  # No device info means no UUID

        result = await group_ops._check_if_slave_of_any_master()

        assert result is None

    @pytest.mark.asyncio
    async def test_check_if_slave_empty_players_list(self, group_ops, mock_player):
        """Test cross-coordinator check with empty players list."""
        mock_player._all_players_finder = MagicMock(return_value=[])

        result = await group_ops._check_if_slave_of_any_master()

        assert result is None

    @pytest.mark.asyncio
    async def test_check_if_slave_found_in_master_group(self, group_ops, mock_player):
        """Test finding self in a master's linked slave list."""
        # Create a master with a group that has our slave linked
        master = MagicMock()
        master._detected_role = "master"
        master.host = "192.168.1.100"
        master.client = MagicMock()

        # Create the slave (mock_player) entry in master's group
        slave_entry = MagicMock()
        slave_entry.uuid = "SLAVE-UUID-1234"  # Matches mock_player's UUID
        slave_entry.host = "10.10.10.92"

        master._group = MagicMock()
        master._group.slaves = [slave_entry]

        # Mock all_players_finder to return the master
        mock_player._all_players_finder = MagicMock(return_value=[mock_player, master])

        result = await group_ops._check_if_slave_of_any_master()

        assert result == "slave"

    @pytest.mark.asyncio
    async def test_check_if_slave_via_api_query(self, group_ops, mock_player):
        """Test finding self via API query when not linked in group."""
        # Create a master that doesn't have us linked in group.slaves
        master = MagicMock()
        master._detected_role = "master"
        master.host = "192.168.1.100"
        master._group = MagicMock()
        master._group.slaves = []  # No slaves linked yet

        # But the master's API returns our UUID in slave list
        master.client = MagicMock()
        master.client.get_slaves_info = AsyncMock(
            return_value=[{"uuid": "SLAVE-UUID-1234", "ip": "10.10.10.92", "name": "TestSlave"}]
        )

        mock_player._all_players_finder = MagicMock(return_value=[mock_player, master])

        result = await group_ops._check_if_slave_of_any_master()

        assert result == "slave"
        master.client.get_slaves_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_if_slave_uuid_normalization(self, group_ops, mock_player):
        """Test UUID normalization handles different formats."""
        # Test with uuid: prefix and different case
        mock_player._device_info = DeviceInfo(uuid="slave-uuid-1234")

        master = MagicMock()
        master._detected_role = "master"
        master.host = "192.168.1.100"
        master._group = MagicMock()
        master._group.slaves = []
        master.client = MagicMock()
        # API returns UUID with prefix and uppercase
        master.client.get_slaves_info = AsyncMock(return_value=[{"uuid": "uuid:SLAVE-UUID-1234", "ip": "10.10.10.92"}])

        mock_player._all_players_finder = MagicMock(return_value=[mock_player, master])

        result = await group_ops._check_if_slave_of_any_master()

        assert result == "slave"

    @pytest.mark.asyncio
    async def test_check_if_slave_skips_self(self, group_ops, mock_player):
        """Test cross-coordinator check skips self in player list."""
        # Only player in the list is self
        mock_player._all_players_finder = MagicMock(return_value=[mock_player])

        result = await group_ops._check_if_slave_of_any_master()

        assert result is None

    @pytest.mark.asyncio
    async def test_check_if_slave_skips_non_masters(self, group_ops, mock_player):
        """Test cross-coordinator check skips non-master players."""
        other_solo = MagicMock()
        other_solo._detected_role = "solo"
        other_solo.host = "192.168.1.101"
        other_solo._group = None
        other_solo.client = MagicMock()
        other_solo.client.get_slaves_info = AsyncMock(return_value=[])

        mock_player._all_players_finder = MagicMock(return_value=[mock_player, other_solo])

        result = await group_ops._check_if_slave_of_any_master()

        assert result is None

    @pytest.mark.asyncio
    async def test_check_if_slave_api_error_continues(self, group_ops, mock_player):
        """Test cross-coordinator check continues after API error."""
        # First master has API error
        master1 = MagicMock()
        master1._detected_role = "master"
        master1.host = "192.168.1.100"
        master1._group = MagicMock()
        master1._group.slaves = []
        master1.client = MagicMock()
        master1.client.get_slaves_info = AsyncMock(side_effect=Exception("Connection timeout"))

        # Second master has our slave
        master2 = MagicMock()
        master2._detected_role = "master"
        master2.host = "192.168.1.101"
        master2._group = MagicMock()
        master2._group.slaves = []
        master2.client = MagicMock()
        master2.client.get_slaves_info = AsyncMock(return_value=[{"uuid": "SLAVE-UUID-1234", "ip": "10.10.10.92"}])

        mock_player._all_players_finder = MagicMock(return_value=[mock_player, master1, master2])

        result = await group_ops._check_if_slave_of_any_master()

        assert result == "slave"

    @pytest.mark.asyncio
    async def test_check_if_slave_callback_error(self, group_ops, mock_player):
        """Test cross-coordinator check handles all_players_finder callback error."""
        mock_player._all_players_finder = MagicMock(side_effect=Exception("Registry error"))

        result = await group_ops._check_if_slave_of_any_master()

        assert result is None

    @pytest.mark.asyncio
    async def test_check_if_slave_creates_group_on_master(self, group_ops, mock_player):
        """Test cross-coordinator creates group on master if it doesn't exist."""
        # Master without a group object
        master = MagicMock()
        master._detected_role = "solo"  # Not detected as master yet
        master.host = "192.168.1.100"
        master._group = None  # No group yet
        master.client = MagicMock()
        master.client.get_slaves_info = AsyncMock(return_value=[{"uuid": "SLAVE-UUID-1234", "ip": "10.10.10.92"}])

        mock_player._all_players_finder = MagicMock(return_value=[mock_player, master])

        result = await group_ops._check_if_slave_of_any_master()

        assert result == "slave"
        assert master._detected_role == "master"  # Should be updated
        assert master._group is not None  # Group should be created
