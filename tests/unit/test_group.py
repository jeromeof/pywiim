"""Unit tests for Group class.

Tests group creation, slave management, and group-level operations.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pywiim.exceptions import WiiMError
from pywiim.models import PlayerStatus


class TestGroupInitialization:
    """Test Group initialization."""

    @pytest.mark.asyncio
    async def test_group_init(self, mock_client):
        """Test Group initialization."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        assert group.master == master
        assert len(group.slaves) == 0
        assert group.size == 1
        assert master.group == group

    @pytest.mark.asyncio
    async def test_group_all_players(self, mock_client):
        """Test all_players property."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave1 = Player(mock_client)
        slave2 = Player(mock_client)
        group = Group(master)
        group.add_slave(slave1)
        group.add_slave(slave2)

        all_players = group.all_players
        assert len(all_players) == 3
        assert all_players[0] == master
        assert slave1 in all_players
        assert slave2 in all_players


class TestGroupSlaveManagement:
    """Test Group slave management."""

    @pytest.mark.asyncio
    async def test_add_slave(self, mock_client):
        """Test adding a slave."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)

        group.add_slave(slave)

        assert slave in group.slaves
        assert group.size == 2
        assert slave.group == group

    @pytest.mark.asyncio
    async def test_add_slave_already_in_different_group_moves_slave(self, mock_client):
        """Test adding slave that's in a DIFFERENT group moves it automatically."""
        from pywiim.group import Group
        from pywiim.player import Player

        master1 = Player(mock_client)
        master2 = Player(mock_client)
        slave = Player(mock_client)
        group1 = Group(master1)
        group2 = Group(master2)

        group1.add_slave(slave)
        assert slave in group1.slaves
        assert slave.group == group1

        # Adding to group2 should automatically remove from group1
        group2.add_slave(slave)

        assert slave not in group1.slaves
        assert slave in group2.slaves
        assert slave.group == group2
        assert group1.size == 1  # Just master1
        assert group2.size == 2  # master2 + slave

    @pytest.mark.asyncio
    async def test_add_slave_already_in_same_group_idempotent(self, mock_client):
        """Test adding slave that's already in THIS group is idempotent (no error)."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)

        group.add_slave(slave)
        assert slave in group.slaves
        assert group.size == 2

        # Adding again should NOT raise - should be idempotent
        group.add_slave(slave)

        # State should be unchanged
        assert slave in group.slaves
        assert group.size == 2
        assert slave.group == group

    @pytest.mark.asyncio
    async def test_remove_slave(self, mock_client):
        """Test removing a slave."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        group.remove_slave(slave)

        assert slave not in group.slaves
        assert group.size == 1
        assert slave.group is None

    @pytest.mark.asyncio
    async def test_remove_slave_not_in_group(self, mock_client):
        """Test removing slave that's not in group."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)

        # Should not raise, just do nothing
        group.remove_slave(slave)

        assert slave not in group.slaves


class TestGroupDisband:
    """Test Group disband method."""

    @pytest.mark.asyncio
    async def test_disband(self, mock_client):
        """Test disbanding a group."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave1 = Player(mock_client)
        slave2 = Player(mock_client)
        group = Group(master)
        group.add_slave(slave1)
        group.add_slave(slave2)

        mock_client._request = AsyncMock(return_value={"status": "ok"})

        await group.disband()

        assert master.group is None
        assert slave1.group is None
        assert slave2.group is None
        assert len(group.slaves) == 0
        mock_client._request.assert_called_once_with("/httpapi.asp?command=multiroom:Ungroup")

    @pytest.mark.asyncio
    async def test_disband_api_failure(self, mock_client):
        """Test disbanding when API fails."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        mock_client.delete_group = AsyncMock(side_effect=WiiMError("Failed"))

        # Should still clean up local state
        await group.disband()

        assert master.group is None
        assert slave.group is None


class TestGroupVolumeControl:
    """Test Group volume control methods."""

    @pytest.mark.asyncio
    async def test_set_volume_all_with_slaves(self, mock_client):
        """Test setting volume on all devices via slave propagation."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        slave.set_volume = AsyncMock()

        await group.set_volume_all(0.5)

        slave.set_volume.assert_called_once_with(0.5)

    @pytest.mark.asyncio
    async def test_set_volume_all_no_slaves(self, mock_client):
        """Test setting volume when no slaves."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        master.set_volume = AsyncMock()

        await group.set_volume_all(0.5)

        master.set_volume.assert_called_once_with(0.5)

    @pytest.mark.asyncio
    async def test_mute_all_with_slaves(self, mock_client):
        """Test muting all devices via slave propagation."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        slave.set_mute = AsyncMock()

        await group.mute_all(True)

        slave.set_mute.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_volume_level_max(self, mock_client):
        """Test getting group volume (max of all devices)."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        # Set volumes in status model
        master._status_model = PlayerStatus(volume=50, play_state="play")
        slave._status_model = PlayerStatus(volume=75, play_state="play")

        # Ensure state synchronizer has volume data (property reads from synchronizer first)
        master._state_synchronizer.update_from_http({"volume": 50})
        slave._state_synchronizer.update_from_http({"volume": 75})

        volume = group.volume_level

        assert volume == 0.75  # Max of 0.5 and 0.75

    @pytest.mark.asyncio
    async def test_volume_level_none(self, mock_client):
        """Test getting group volume when unknown."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        volume = group.volume_level

        assert volume is None

    @pytest.mark.asyncio
    async def test_is_muted_all(self, mock_client):
        """Test checking if all devices are muted."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        master._status_model = PlayerStatus(mute=True, play_state="play")
        slave._status_model = PlayerStatus(mute=True, play_state="play")

        # Ensure state synchronizer has mute data (property reads from synchronizer first)
        master._state_synchronizer.update_from_http({"muted": True})
        slave._state_synchronizer.update_from_http({"muted": True})

        assert group.is_muted is True

    @pytest.mark.asyncio
    async def test_is_muted_partial(self, mock_client):
        """Test checking mute when not all devices are muted."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        master._status_model = PlayerStatus(mute=True, play_state="play")
        slave._status_model = PlayerStatus(mute=False, play_state="play")

        assert group.is_muted is False

    @pytest.mark.asyncio
    async def test_get_volume_level(self, mock_client):
        """Test getting group volume by querying devices."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        master.get_volume = AsyncMock(return_value=0.5)
        slave.get_volume = AsyncMock(return_value=0.75)

        volume = await group.get_volume_level()

        assert volume == 0.75  # Max

    @pytest.mark.asyncio
    async def test_get_muted(self, mock_client):
        """Test getting group mute by querying devices."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        master.get_muted = AsyncMock(return_value=True)
        slave.get_muted = AsyncMock(return_value=True)

        muted = await group.get_muted()

        assert muted is True


class TestGroupPlaybackControl:
    """Test Group playback control methods."""

    @pytest.mark.asyncio
    async def test_play(self, mock_client):
        """Test group play command."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        master.play = AsyncMock()

        await group.play()

        master.play.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause(self, mock_client):
        """Test group pause command."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        master.pause = AsyncMock()

        await group.pause()

        master.pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, mock_client):
        """Test group stop command."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        master.stop = AsyncMock()

        await group.stop()

        master.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_next_track(self, mock_client):
        """Test group next track command."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        master.next_track = AsyncMock()

        await group.next_track()

        master.next_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_state(self, mock_client):
        """Test getting group play state."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        master._status_model = PlayerStatus(play_state="play")

        # Ensure state synchronizer has play_state data (property reads from synchronizer first)
        master._state_synchronizer.update_from_http({"play_state": "play"})

        assert group.play_state == "play"

    @pytest.mark.asyncio
    async def test_get_play_state(self, mock_client):
        """Test getting group play state by querying."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        master.get_play_state = AsyncMock(return_value="play")

        state = await group.get_play_state()

        assert state == "play"

    @pytest.mark.asyncio
    async def test_get_status(self, mock_client):
        """Test getting group status."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        group = Group(master)

        status = PlayerStatus(play_state="play", volume=50)
        master.get_status = AsyncMock(return_value=status)

        result = await group.get_status()

        assert result == status
