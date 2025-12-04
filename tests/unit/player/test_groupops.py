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
        slave._state_synchronizer.update_from_http.assert_called()

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
