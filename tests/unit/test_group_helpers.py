"""Unit tests for group helper functions."""

from unittest.mock import MagicMock

import pytest

from pywiim.models import GroupState, PlayerStatus


class TestBuildGroupStateFromPlayers:
    """Test build_group_state_from_players function."""

    @pytest.mark.asyncio
    async def test_build_group_state_master_only(self, mock_client):
        """Test building group state with master only."""
        from pywiim.group_helpers import build_group_state_from_players
        from pywiim.player import Player

        master = Player(mock_client)
        master._group = MagicMock()  # Mock group to make it a master
        master._group.master = master
        master._detected_role = "master"  # Set role from device API state

        status = PlayerStatus(
            play_state="play",
            volume=50,
            mute=False,
            source="wifi",
            position=120,
            duration=240,
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
        )
        master._status_model = status

        # Add a slave to make it a proper master (master with no slaves is solo)
        slave = Player(mock_client)
        master._group.slaves = [slave]

        group_state = await build_group_state_from_players(master)

        assert isinstance(group_state, GroupState)
        assert group_state.master_host == master.host
        assert group_state.play_state == "play"
        assert group_state.volume_level == 50
        assert group_state.is_muted is False

    @pytest.mark.asyncio
    async def test_build_group_state_with_slaves(self, mock_client):
        """Test building group state with slaves."""
        from pywiim.group_helpers import build_group_state_from_players
        from pywiim.player import Player

        master = Player(mock_client)
        master._group = MagicMock()
        master._group.master = master
        master._detected_role = "master"  # Set role from device API state

        slave1 = Player(mock_client)
        slave1._detected_role = "slave"  # Set role from device API state
        slave2 = Player(mock_client)
        slave2._detected_role = "slave"  # Set role from device API state
        master._group.slaves = [slave1, slave2]  # Add slaves to group

        master_status = PlayerStatus(play_state="play", volume=50, mute=False)
        slave1_status = PlayerStatus(play_state="play", volume=75, mute=True)
        slave2_status = PlayerStatus(play_state="play", volume=60, mute=False)

        master._status_model = master_status
        slave1._status_model = slave1_status
        slave2._status_model = slave2_status

        group_state = await build_group_state_from_players(master, slave_players=[slave1, slave2])

        assert group_state.master_host == master.host
        assert len(group_state.slave_hosts) == 2
        assert slave1.host in group_state.slave_hosts
        assert slave2.host in group_state.slave_hosts
        assert group_state.volume_level == 75  # Max of 50, 75, 60
        assert group_state.is_muted is False  # Not all muted (master=False, slave1=True, slave2=False)

    @pytest.mark.asyncio
    async def test_build_group_state_all_muted(self, mock_client):
        """Test building group state when all devices are muted."""
        from pywiim.group_helpers import build_group_state_from_players
        from pywiim.player import Player

        master = Player(mock_client)
        master._group = MagicMock()
        master._group.master = master
        master._detected_role = "master"  # Set role from device API state

        slave = Player(mock_client)
        slave._detected_role = "slave"  # Set role from device API state
        master._group.slaves = [slave]  # Add slave to group

        master_status = PlayerStatus(play_state="play", volume=50, mute=True)
        slave_status = PlayerStatus(play_state="play", volume=75, mute=True)

        master._status_model = master_status
        slave._status_model = slave_status

        group_state = await build_group_state_from_players(master, slave_players=[slave])

        assert group_state.is_muted is True  # All muted

    @pytest.mark.asyncio
    async def test_build_group_state_not_master(self, mock_client):
        """Test building group state when player is not master."""
        from pywiim.group_helpers import build_group_state_from_players
        from pywiim.player import Player

        player = Player(mock_client)
        player._group = None  # Solo player

        with pytest.raises(RuntimeError, match="is not the group master"):
            await build_group_state_from_players(player)

    @pytest.mark.asyncio
    async def test_build_group_state_no_status(self, mock_client):
        """Test building group state when status not available."""
        from pywiim.group_helpers import build_group_state_from_players
        from pywiim.player import Player

        master = Player(mock_client)
        master._group = MagicMock()
        master._group.master = master
        master._detected_role = "master"  # Set role from device API state
        slave = Player(mock_client)
        master._group.slaves = [slave]  # Add slave to group
        master._status_model = None  # No status

        with pytest.raises(ValueError, match="state not available"):
            await build_group_state_from_players(master)

    @pytest.mark.asyncio
    async def test_build_group_state_slave_no_status(self, mock_client):
        """Test building group state when slave status not available."""
        from pywiim.group_helpers import build_group_state_from_players
        from pywiim.player import Player

        master = Player(mock_client)
        master._group = MagicMock()
        master._group.master = master
        master._detected_role = "master"  # Set role from device API state

        slave = Player(mock_client)
        slave._detected_role = "slave"  # Set role from device API state
        slave._status_model = None  # No status
        master._group.slaves = [slave]  # Add slave to group

        master_status = PlayerStatus(play_state="play", volume=50, mute=False)
        master._status_model = master_status

        # Should skip slave without status
        group_state = await build_group_state_from_players(master, slave_players=[slave])

        assert len(group_state.slave_hosts) == 0  # Slave skipped
        assert group_state.volume_level == 50  # Only master volume
