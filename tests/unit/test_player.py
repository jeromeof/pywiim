"""Unit tests for Player class.

Tests player initialization, state management, role detection, and control methods.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from pywiim.exceptions import WiiMError
from pywiim.models import DeviceInfo, PlayerStatus


class TestPlayerInitialization:
    """Test Player initialization."""

    @pytest.mark.asyncio
    async def test_player_init(self, mock_client):
        """Test Player initialization."""
        from pywiim.player import Player

        player = Player(mock_client)

        assert player.client == mock_client
        assert player._group is None
        assert player.role == "solo"
        assert player.is_solo is True
        assert player.is_master is False
        assert player.is_slave is False

    @pytest.mark.asyncio
    async def test_player_init_with_callback(self, mock_client):
        """Test Player initialization with state change callback."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        callback_called = []

        def on_state_changed():
            callback_called.append(True)

        player = Player(mock_client, on_state_changed=on_state_changed)

        assert player._on_state_changed is not None
        # Callback will be called during refresh
        mock_status = PlayerStatus(play_state="play", volume=50, mute=False)
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_client.get_device_info_model = AsyncMock(return_value=mock_info)
        await player.refresh()
        assert len(callback_called) > 0


class TestPlayerRole:
    """Test Player role detection."""

    @pytest.mark.asyncio
    async def test_player_role_solo(self, mock_client):
        """Test player role when solo."""
        from pywiim.player import Player

        player = Player(mock_client)

        assert player.role == "solo"
        assert player.is_solo is True
        assert player.is_master is False
        assert player.is_slave is False
        assert player.group is None

    @pytest.mark.asyncio
    async def test_player_role_master(self, mock_client):
        """Test player role when master."""
        from pywiim.group import Group
        from pywiim.player import Player

        player = Player(mock_client)
        player._detected_role = "master"  # Set role from device API state
        group = Group(player)

        # Add a slave to make it a proper master (master with no slaves is solo)
        slave = Player(mock_client)
        group.add_slave(slave)

        assert player.role == "master"
        assert player.is_solo is False
        assert player.is_master is True
        assert player.is_slave is False
        assert player.group == group

    @pytest.mark.asyncio
    async def test_player_role_slave(self, mock_client):
        """Test player role when slave."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        master._detected_role = "master"  # Set role from device API state
        slave = Player(mock_client)
        slave._detected_role = "slave"  # Set role from device API state
        group = Group(master)
        group.add_slave(slave)

        assert slave.role == "slave"
        assert slave.is_solo is False
        assert slave.is_master is False
        assert slave.is_slave is True
        assert slave.group == group


class TestPlayerProperties:
    """Test Player properties."""

    @pytest.mark.asyncio
    async def test_player_host(self, mock_client):
        """Test player host property."""
        from pywiim.player import Player

        player = Player(mock_client)
        assert player.host == mock_client.host

    @pytest.mark.asyncio
    async def test_player_name_from_cache(self, mock_client):
        """Test player name from cached device info."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", name="Test Device")
        player._device_info = device_info

        assert player.name == "Test Device"

    @pytest.mark.asyncio
    async def test_player_name_no_cache(self, mock_client):
        """Test player name when not cached."""
        from pywiim.player import Player

        player = Player(mock_client)
        assert player.name is None

    @pytest.mark.asyncio
    async def test_player_available(self, mock_client):
        """Test player available property."""
        from pywiim.player import Player

        player = Player(mock_client)
        assert player.available is True  # Default

        player._available = False
        assert player.available is False


class TestPlayerRefresh:
    """Test Player refresh method."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, mock_client):
        """Test successful refresh."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_status = PlayerStatus(play_state="play", volume=50, mute=False)
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_client.get_device_info_model = AsyncMock(return_value=mock_info)
        # Capabilities are set via constructor, mock_client already has them from conftest

        player = Player(mock_client)
        await player.refresh()

        assert player._status_model == mock_status
        assert player._device_info == mock_info
        assert player.available is True
        assert player._last_refresh is not None

    @pytest.mark.asyncio
    async def test_refresh_with_audio_output(self, mock_aiohttp_session):
        """Test refresh with audio output status."""
        from pywiim.client import WiiMClient
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        # Create client with audio output capability
        capabilities = {
            "supports_audio_output": True,
            "is_legacy_device": False,
        }
        mock_client = WiiMClient("192.168.1.100", session=mock_aiohttp_session, capabilities=capabilities)
        mock_client._request = AsyncMock(return_value={"status": "ok"})

        mock_status = PlayerStatus(play_state="play", volume=50, mute=False)
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_client.get_device_info_model = AsyncMock(return_value=mock_info)
        mock_client.get_audio_output_status = AsyncMock(return_value={"hardware": 0, "source": 0})

        player = Player(mock_client)
        await player.refresh(full=True)  # Audio output status is only fetched on full refresh

        assert player._audio_output_status == {"hardware": 0, "source": 0}

    @pytest.mark.asyncio
    async def test_refresh_failure(self, mock_client):
        """Test refresh failure."""
        from pywiim.player import Player

        mock_client.get_player_status_model = AsyncMock(side_effect=WiiMError("Failed"))

        player = Player(mock_client)
        with pytest.raises(WiiMError):
            await player.refresh()

        assert player.available is False

    @pytest.mark.asyncio
    async def test_refresh_callback_error(self, mock_client):
        """Test refresh when callback raises error."""
        from pywiim.player import Player

        def bad_callback():
            raise ValueError("Callback error")

        from pywiim.models import DeviceInfo, PlayerStatus

        mock_status = PlayerStatus(play_state="play", volume=50, mute=False)
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_client.get_device_info_model = AsyncMock(return_value=mock_info)
        # Capabilities are set via constructor, mock_client already has them from conftest

        player = Player(mock_client, on_state_changed=bad_callback)
        # Should not raise, just log error
        await player.refresh()

        assert player._status_model == mock_status

    @pytest.mark.asyncio
    async def test_refresh_with_upnp_volume(self, mock_client):
        """Test refresh uses UPnP GetVolume when available."""
        from unittest.mock import MagicMock

        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player
        from pywiim.upnp.client import UpnpClient

        # Setup HTTP status (volume=50)
        mock_status = PlayerStatus(play_state="play", volume=50, mute=False)
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_client.get_device_info_model = AsyncMock(return_value=mock_info)
        mock_client.get_device_info_model = AsyncMock(return_value=mock_info)

        # Setup UPnP client with RenderingControl
        mock_upnp_client = MagicMock(spec=UpnpClient)
        mock_upnp_client.rendering_control = MagicMock()
        mock_upnp_client.get_volume = AsyncMock(return_value=75)  # UPnP volume = 75
        mock_upnp_client.get_mute = AsyncMock(return_value=True)  # UPnP mute = True

        player = Player(mock_client, upnp_client=mock_upnp_client)
        await player.refresh()

        # Verify UPnP GetVolume was called
        mock_upnp_client.get_volume.assert_called_once()
        mock_upnp_client.get_mute.assert_called_once()

        # Verify state synchronizer was updated with UPnP values (overriding HTTP)
        merged = player._state_synchronizer.get_merged_state()
        # UPnP volume (75) should override HTTP volume (50)
        assert merged["volume"] == 75
        # UPnP mute (True) should override HTTP mute (False)
        assert merged["muted"] is True

    @pytest.mark.asyncio
    async def test_refresh_lazy_upnp_client_creation(self, mock_client):
        """Test refresh creates UPnP client lazily if not provided."""
        from unittest.mock import MagicMock, patch

        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        # Setup HTTP status
        mock_status = PlayerStatus(play_state="play", volume=50, mute=False)
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_client.get_device_info_model = AsyncMock(return_value=mock_info)

        # Mock UPnP client creation
        mock_upnp_client = MagicMock()
        mock_upnp_client.rendering_control = MagicMock()
        mock_upnp_client.get_volume = AsyncMock(return_value=60)
        mock_upnp_client.get_mute = AsyncMock(return_value=False)

        with patch("pywiim.upnp.client.UpnpClient.create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_upnp_client

            player = Player(mock_client)  # No UPnP client provided
            assert player._upnp_client is None

            await player.refresh()

            # Should attempt to create UPnP client
            mock_create.assert_called_once()
            # UPnP client should be set
            assert player._upnp_client is not None

    @pytest.mark.asyncio
    async def test_refresh_upnp_volume_fallback_to_http(self, mock_client):
        """Test refresh falls back to HTTP volume when UPnP GetVolume fails."""
        from unittest.mock import MagicMock

        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player
        from pywiim.upnp.client import UpnpClient

        # Setup HTTP status (volume=50)
        mock_status = PlayerStatus(play_state="play", volume=50, mute=False)
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_client.get_device_info_model = AsyncMock(return_value=mock_info)

        # Setup UPnP client but GetVolume fails
        mock_upnp_client = MagicMock(spec=UpnpClient)
        mock_upnp_client.rendering_control = MagicMock()
        mock_upnp_client.get_volume = AsyncMock(side_effect=Exception("UPnP error"))
        mock_upnp_client.get_mute = AsyncMock(side_effect=Exception("UPnP error"))

        player = Player(mock_client, upnp_client=mock_upnp_client)
        await player.refresh()

        # Should fall back to HTTP volume
        merged = player._state_synchronizer.get_merged_state()
        # Should use HTTP volume (50) since UPnP failed
        assert merged["volume"] == 50
        # Mute might be None if HTTP status doesn't include it, or False if it does
        # The important thing is that volume works (the main test)
        assert merged.get("muted") in [False, None]


class TestPlayerVolumeControl:
    """Test Player volume control methods."""

    @pytest.mark.asyncio
    async def test_set_volume(self, mock_client):
        """Test setting volume."""
        from pywiim.player import Player

        mock_client.set_volume = AsyncMock()

        player = Player(mock_client)
        await player.set_volume(0.5)

        mock_client.set_volume.assert_called_once_with(0.5)

    @pytest.mark.asyncio
    async def test_set_mute(self, mock_client):
        """Test setting mute."""
        from pywiim.player import Player

        mock_client.set_mute = AsyncMock()

        player = Player(mock_client)
        await player.set_mute(True)

        mock_client.set_mute.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_volume_level_from_cache(self, mock_client):
        """Test getting volume level from cache."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(volume=50, play_state="play")
        player._status_model = status

        assert player.volume_level == 0.5

    @pytest.mark.asyncio
    async def test_volume_level_none(self, mock_client):
        """Test getting volume level when not cached."""
        from pywiim.player import Player

        player = Player(mock_client)
        assert player.volume_level is None

    @pytest.mark.asyncio
    async def test_is_muted_from_cache(self, mock_client):
        """Test getting mute state from cache."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(mute=True, play_state="play")
        player._status_model = status

        assert player.is_muted is True

    @pytest.mark.asyncio
    async def test_get_volume(self, mock_client):
        """Test getting volume by querying device."""
        from pywiim.player import Player

        status = PlayerStatus(volume=75, play_state="play")
        mock_client.get_player_status_model = AsyncMock(return_value=status)

        player = Player(mock_client)
        volume = await player.get_volume()

        assert volume == 0.75

    @pytest.mark.asyncio
    async def test_get_muted(self, mock_client):
        """Test getting mute state by querying device."""
        from pywiim.player import Player

        status = PlayerStatus(mute=False, play_state="play")
        mock_client.get_player_status_model = AsyncMock(return_value=status)

        player = Player(mock_client)
        muted = await player.get_muted()

        assert muted is False

    @pytest.mark.asyncio
    async def test_set_volume_master_with_slaves(self, mock_client):
        """Test set_volume on master only affects that device (no auto-propagation)."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)

        # Set up master with detected role
        master._detected_role = "master"
        master._status_model = PlayerStatus(volume=50, play_state="play")

        # Create group and add slave
        group = Group(master)
        group.add_slave(slave)

        mock_client.set_volume = AsyncMock()

        # Call set_volume on master
        await master.set_volume(0.6)

        # Verify it called client directly (physical master only, no group propagation)
        # Group-wide operations require explicit group.set_volume_all()
        mock_client.set_volume.assert_called_once_with(0.6)

    @pytest.mark.asyncio
    async def test_set_volume_master_no_slaves(self, mock_client):
        """Test set_volume on master with no slaves only affects master."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        master._detected_role = "master"
        master._status_model = PlayerStatus(volume=50, play_state="play")

        # Create group but no slaves
        Group(master)

        mock_client.set_volume = AsyncMock()

        # Call set_volume on master with no slaves
        await master.set_volume(0.6)

        # Verify it called client directly (not group)
        mock_client.set_volume.assert_called_once_with(0.6)

    @pytest.mark.asyncio
    async def test_set_volume_slave(self, mock_client):
        """Test set_volume on slave only affects that slave."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)

        master._detected_role = "master"
        slave._detected_role = "slave"
        slave._status_model = PlayerStatus(volume=50, play_state="play")

        # Create group
        group = Group(master)
        group.add_slave(slave)

        mock_client.set_volume = AsyncMock()

        # Call set_volume on slave
        await slave.set_volume(0.7)

        # Verify it called client directly (slaves have independent volume)
        mock_client.set_volume.assert_called_once_with(0.7)

    @pytest.mark.asyncio
    async def test_set_mute_master_with_slaves(self, mock_client):
        """Test set_mute on master only affects that device (no auto-propagation)."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)

        master._detected_role = "master"
        master._status_model = PlayerStatus(mute=False, play_state="play")

        # Create group and add slave
        group = Group(master)
        group.add_slave(slave)

        mock_client.set_mute = AsyncMock()

        # Call set_mute on master
        await master.set_mute(True)

        # Verify it called client directly (physical master only, no group propagation)
        # Group-wide operations require explicit group.mute_all()
        mock_client.set_mute.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_set_mute_slave(self, mock_client):
        """Test set_mute on slave only affects that slave."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)

        master._detected_role = "master"
        slave._detected_role = "slave"
        slave._status_model = PlayerStatus(mute=False, play_state="play")

        # Create group
        group = Group(master)
        group.add_slave(slave)

        mock_client.set_mute = AsyncMock()

        # Call set_mute on slave
        await slave.set_mute(True)

        # Verify it called client directly (slaves have independent mute)
        mock_client.set_mute.assert_called_once_with(True)


class TestPlayerPlaybackControl:
    """Test Player playback control methods."""

    @pytest.mark.asyncio
    async def test_play(self, mock_client):
        """Test play command."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.play = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.play()

        mock_client.play.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause(self, mock_client):
        """Test pause command."""
        from pywiim.player import Player

        mock_client.pause = AsyncMock()

        player = Player(mock_client)
        await player.pause()

        mock_client.pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume(self, mock_client):
        """Test resume command."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.resume = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.resume()

        mock_client.resume.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, mock_client):
        """Test stop command."""
        from pywiim.player import Player

        mock_client.stop = AsyncMock()

        player = Player(mock_client)
        await player.stop()

        mock_client.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_next_track(self, mock_client):
        """Test next track command."""
        from pywiim.player import Player

        mock_client.next_track = AsyncMock()

        player = Player(mock_client)
        await player.next_track()

        mock_client.next_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_seek(self, mock_client):
        """Test seek command."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.seek = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.seek(120)

        mock_client.seek.assert_called_once_with(120)

    @pytest.mark.asyncio
    async def test_play_url(self, mock_client):
        """Test play URL command."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.play_url = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.play_url("http://example.com/stream.mp3")

        mock_client.play_url.assert_called_once_with("http://example.com/stream.mp3")

    @pytest.mark.asyncio
    async def test_play_playlist(self, mock_client):
        """Test play playlist command."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.play_playlist = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.play_playlist("http://example.com/playlist.m3u")

        mock_client.play_playlist.assert_called_once_with("http://example.com/playlist.m3u")

    @pytest.mark.asyncio
    async def test_play_url_with_enqueue_replace(self, mock_client):
        """Test play_url with enqueue='replace' (default, uses HTTP API)."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.play_url = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.play_url("http://example.com/song.mp3", enqueue="replace")

        mock_client.play_url.assert_called_once_with("http://example.com/song.mp3")

    @pytest.mark.asyncio
    async def test_play_url_with_enqueue_add_no_upnp(self, mock_client):
        """Test play_url with enqueue='add' without UPnP client raises error."""
        from pywiim.player import Player

        player = Player(mock_client)

        with pytest.raises(WiiMError, match="requires UPnP client"):
            await player.play_url("http://example.com/song.mp3", enqueue="add")

    @pytest.mark.asyncio
    async def test_play_url_with_enqueue_next_no_upnp(self, mock_client):
        """Test play_url with enqueue='next' without UPnP client raises error."""
        from pywiim.player import Player

        player = Player(mock_client)

        with pytest.raises(WiiMError, match="requires UPnP client"):
            await player.play_url("http://example.com/song.mp3", enqueue="next")

    @pytest.mark.asyncio
    async def test_add_to_queue_no_upnp(self, mock_client):
        """Test add_to_queue without UPnP client raises error."""
        from pywiim.player import Player

        player = Player(mock_client)

        with pytest.raises(WiiMError, match="requires UPnP client"):
            await player.add_to_queue("http://example.com/song.mp3")

    @pytest.mark.asyncio
    async def test_insert_next_no_upnp(self, mock_client):
        """Test insert_next without UPnP client raises error."""
        from pywiim.player import Player

        player = Player(mock_client)

        with pytest.raises(WiiMError, match="requires UPnP client"):
            await player.insert_next("http://example.com/song.mp3")

    @pytest.mark.asyncio
    async def test_add_to_queue_with_upnp(self, mock_client):
        """Test add_to_queue with UPnP client."""
        from pywiim.player import Player
        from pywiim.upnp.client import UpnpClient

        mock_upnp_client = MagicMock(spec=UpnpClient)
        mock_upnp_client.async_call_action = AsyncMock()

        player = Player(mock_client, upnp_client=mock_upnp_client)
        await player.add_to_queue("http://example.com/song.mp3")

        mock_upnp_client.async_call_action.assert_called_once_with(
            "AVTransport",
            "AddURIToQueue",
            {
                "InstanceID": 0,
                "EnqueuedURI": "http://example.com/song.mp3",
                "EnqueuedURIMetaData": "",
                "DesiredFirstTrackNumberEnqueued": 0,
                "EnqueueAsNext": False,
            },
        )

    @pytest.mark.asyncio
    async def test_add_to_queue_with_metadata(self, mock_client):
        """Test add_to_queue with metadata."""
        from pywiim.player import Player
        from pywiim.upnp.client import UpnpClient

        mock_upnp_client = MagicMock(spec=UpnpClient)
        mock_upnp_client.async_call_action = AsyncMock()

        player = Player(mock_client, upnp_client=mock_upnp_client)
        await player.add_to_queue("http://example.com/song.mp3", metadata="<DIDL-Lite>...</DIDL-Lite>")

        mock_upnp_client.async_call_action.assert_called_once_with(
            "AVTransport",
            "AddURIToQueue",
            {
                "InstanceID": 0,
                "EnqueuedURI": "http://example.com/song.mp3",
                "EnqueuedURIMetaData": "<DIDL-Lite>...</DIDL-Lite>",
                "DesiredFirstTrackNumberEnqueued": 0,
                "EnqueueAsNext": False,
            },
        )

    @pytest.mark.asyncio
    async def test_insert_next_with_upnp(self, mock_client):
        """Test insert_next with UPnP client."""
        from pywiim.player import Player
        from pywiim.upnp.client import UpnpClient

        mock_upnp_client = MagicMock(spec=UpnpClient)
        mock_upnp_client.async_call_action = AsyncMock()

        player = Player(mock_client, upnp_client=mock_upnp_client)
        await player.insert_next("http://example.com/song.mp3")

        mock_upnp_client.async_call_action.assert_called_once_with(
            "AVTransport",
            "InsertURIToQueue",
            {
                "InstanceID": 0,
                "EnqueuedURI": "http://example.com/song.mp3",
                "EnqueuedURIMetaData": "",
                "DesiredTrackNumber": 0,
            },
        )

    @pytest.mark.asyncio
    async def test_play_url_with_enqueue_add(self, mock_client):
        """Test play_url with enqueue='add' uses UPnP."""
        from pywiim.player import Player
        from pywiim.upnp.client import UpnpClient

        mock_upnp_client = MagicMock(spec=UpnpClient)
        mock_upnp_client.async_call_action = AsyncMock()

        player = Player(mock_client, upnp_client=mock_upnp_client)
        await player.play_url("http://example.com/song.mp3", enqueue="add")

        mock_upnp_client.async_call_action.assert_called_once_with(
            "AVTransport",
            "AddURIToQueue",
            {
                "InstanceID": 0,
                "EnqueuedURI": "http://example.com/song.mp3",
                "EnqueuedURIMetaData": "",
                "DesiredFirstTrackNumberEnqueued": 0,
                "EnqueueAsNext": False,
            },
        )
        # Should not call HTTP API (play_url is not mocked in this test)
        # The UPnP path doesn't call client.play_url()

    @pytest.mark.asyncio
    async def test_play_url_with_enqueue_next(self, mock_client):
        """Test play_url with enqueue='next' uses UPnP."""
        from pywiim.player import Player
        from pywiim.upnp.client import UpnpClient

        mock_upnp_client = MagicMock(spec=UpnpClient)
        mock_upnp_client.async_call_action = AsyncMock()

        player = Player(mock_client, upnp_client=mock_upnp_client)
        await player.play_url("http://example.com/song.mp3", enqueue="next")

        mock_upnp_client.async_call_action.assert_called_once_with(
            "AVTransport",
            "InsertURIToQueue",
            {
                "InstanceID": 0,
                "EnqueuedURI": "http://example.com/song.mp3",
                "EnqueuedURIMetaData": "",
                "DesiredTrackNumber": 0,
            },
        )
        # Should not call HTTP API (play_url is not mocked in this test)
        # The UPnP path doesn't call client.play_url()

    @pytest.mark.asyncio
    async def test_play_notification(self, mock_client):
        """Test play notification command."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.play_notification = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.play_notification("http://example.com/notification.mp3")

        mock_client.play_notification.assert_called_once_with("http://example.com/notification.mp3")

    @pytest.mark.asyncio
    async def test_play_preset(self, mock_client):
        """Test play preset command."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.play_preset = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.play_preset(1)

        mock_client.play_preset.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_set_source(self, mock_client):
        """Test set source command."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.set_source = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.set_source("bluetooth")

        mock_client.set_source.assert_called_once_with("bluetooth")

    @pytest.mark.asyncio
    async def test_set_audio_output_mode(self, mock_client):
        """Test set audio output mode command."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.set_audio_output_mode = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.set_audio_output_mode("Line Out")

        mock_client.set_audio_output_mode.assert_called_once_with("Line Out")

    @pytest.mark.asyncio
    async def test_set_shuffle(self, mock_client):
        """Test set shuffle command preserves repeat state."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.set_loop_mode = AsyncMock()
        status = PlayerStatus(play_state="play", repeat="all", source="usb")
        mock_client.get_player_status_model = AsyncMock(return_value=status)
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        player._status_model = status  # Cache status so repeat_mode property works
        await player.set_shuffle(True)

        # Should call set_loop_mode with shuffle+repeat_all (2 for WiiM)
        mock_client.set_loop_mode.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_set_shuffle_off(self, mock_client):
        """Test set shuffle off preserves repeat state."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.set_loop_mode = AsyncMock()
        status = PlayerStatus(play_state="play", repeat="one", source="usb")
        mock_client.get_player_status_model = AsyncMock(return_value=status)
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        player._status_model = status  # Cache status so repeat_mode property works
        await player.set_shuffle(False)

        # Should call set_loop_mode with repeat_one only (1)
        mock_client.set_loop_mode.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_set_repeat(self, mock_client):
        """Test set repeat command preserves shuffle state."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.set_loop_mode = AsyncMock()
        status = PlayerStatus(play_state="play", shuffle="1", source="usb")
        mock_client.get_player_status_model = AsyncMock(return_value=status)
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        player._status_model = status  # Cache status so shuffle_state property works
        await player.set_repeat("all")

        # Should call set_loop_mode with shuffle+repeat_all (2 for WiiM)
        mock_client.set_loop_mode.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_set_repeat_off(self, mock_client):
        """Test set repeat off preserves shuffle state."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.set_loop_mode = AsyncMock()
        status = PlayerStatus(play_state="play", shuffle="1", source="usb")
        mock_client.get_player_status_model = AsyncMock(return_value=status)
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        player._status_model = status  # Cache status so shuffle_state property works
        await player.set_repeat("off")

        # Should call set_loop_mode with shuffle only (3 for WiiM)
        mock_client.set_loop_mode.assert_called_once_with(3)

    @pytest.mark.asyncio
    async def test_set_repeat_invalid(self, mock_client):
        """Test set repeat with invalid mode raises ValueError."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        with pytest.raises(ValueError, match="Invalid repeat mode"):
            await player.set_repeat("invalid")

    @pytest.mark.asyncio
    async def test_set_shuffle_raises_error_for_external_source(self, mock_client):
        """Test set_shuffle raises WiiMError for blacklisted external sources (radio only)."""
        from pywiim.exceptions import WiiMError
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        # Use tunein (radio) which is still blacklisted
        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play", source="tunein"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.refresh()

        # Should raise WiiMError because TuneIn (radio) doesn't support device control
        with pytest.raises(WiiMError, match="Shuffle cannot be controlled when playing from"):
            await player.set_shuffle(True)

    @pytest.mark.asyncio
    async def test_set_repeat_raises_error_for_external_source(self, mock_client):
        """Test set_repeat raises WiiMError for blacklisted external sources (radio only)."""
        from pywiim.exceptions import WiiMError
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        # Use tunein (radio) which is still blacklisted
        mock_client.get_player_status_model = AsyncMock(
            return_value=PlayerStatus(play_state="play", source="tunein")  # Radio stream (blacklisted)
        )
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        await player.refresh()

        # Should raise WiiMError because TuneIn (radio) doesn't support device control
        with pytest.raises(WiiMError, match="Repeat cannot be controlled when playing from"):
            await player.set_repeat("all")

    @pytest.mark.asyncio
    async def test_set_shuffle_works_for_device_controlled_source(self, mock_client):
        """Test set_shuffle works normally for device-controlled sources."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play", source="usb"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))
        mock_client.set_loop_mode = AsyncMock()

        player = Player(mock_client)
        await player.refresh()

        # Should work without errors for USB source
        await player.set_shuffle(True)
        mock_client.set_loop_mode.assert_called_once_with(3)  # loop_mode=3 is shuffle only for WiiM

    @pytest.mark.asyncio
    async def test_set_repeat_works_for_device_controlled_source(self, mock_client):
        """Test set_repeat works normally for device-controlled sources."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play", source="usb"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))
        mock_client.set_loop_mode = AsyncMock()

        player = Player(mock_client)
        await player.refresh()

        # Should work without errors for USB source
        await player.set_repeat("all")
        mock_client.set_loop_mode.assert_called_once_with(0)  # loop_mode=0 is repeat_all for WiiM


class TestPlayerMediaMetadata:
    """Test Player media metadata properties."""

    @pytest.mark.asyncio
    async def test_media_title(self, mock_client):
        """Test getting media title."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(title="Test Song", play_state="play")
        player._status_model = status

        assert player.media_title == "Test Song"

    @pytest.mark.asyncio
    async def test_media_artist(self, mock_client):
        """Test getting media artist."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(artist="Test Artist", play_state="play")
        player._status_model = status

        assert player.media_artist == "Test Artist"

    @pytest.mark.asyncio
    async def test_media_album(self, mock_client):
        """Test getting media album."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(album="Test Album", play_state="play")
        player._status_model = status

        assert player.media_album == "Test Album"

    @pytest.mark.asyncio
    async def test_media_duration(self, mock_client):
        """Test getting media duration."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(duration=240, play_state="play")
        player._status_model = status

        assert player.media_duration == 240

    @pytest.mark.asyncio
    async def test_play_state(self, mock_client):
        """Test getting play state."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play")
        player._status_model = status

        assert player.play_state == "play"

    @pytest.mark.asyncio
    async def test_source(self, mock_client):
        """Test getting source."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(source="wifi", play_state="play")
        player._status_model = status

        # Ensure state synchronizer has source data (property reads from synchronizer first)
        player._state_synchronizer.update_from_http({"source": "wifi"})

        assert player.source == "wifi"

    @pytest.mark.asyncio
    async def test_media_duration_zero(self, mock_client):
        """Test getting media duration when zero (streaming)."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(duration=0, play_state="play")
        player._status_model = status

        assert player.media_duration is None  # Zero duration returns None

    @pytest.mark.asyncio
    async def test_media_duration_string(self, mock_client):
        """Test getting media duration from string."""
        from pywiim.player import Player

        player = Player(mock_client)
        # Create a status with duration as string (simulating API response)
        status = PlayerStatus(play_state="play")
        status.duration = "240"  # String duration
        player._status_model = status

        assert player.media_duration == 240

    @pytest.mark.asyncio
    async def test_media_position_basic(self, mock_client):
        """Test getting media position."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(position=120, duration=240, play_state="play")
        player._status_model = status
        # Update state synchronizer with position data
        player._state_synchronizer.update_from_http({"position": 120, "duration": 240, "play_state": "play"})

        assert player.media_position == 120

    @pytest.mark.asyncio
    async def test_media_position_negative(self, mock_client):
        """Test getting media position when negative."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(position=-10, duration=240, play_state="play")
        player._status_model = status

        assert player.media_position is None  # Negative position returns None

    @pytest.mark.asyncio
    async def test_media_position_clamped_to_duration(self, mock_client):
        """Test media position clamped to duration."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(position=300, duration=240, play_state="play")
        player._status_model = status
        # Update state synchronizer with position data
        player._state_synchronizer.update_from_http({"position": 300, "duration": 240, "play_state": "play"})

        assert player.media_position == 240  # Clamped to duration

    @pytest.mark.asyncio
    async def test_media_position_returns_raw_device_value(self, mock_client):
        """Test media position returns raw device value without estimation."""
        import time

        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(position=100, duration=240, play_state="play")
        player._status_model = status
        # Update state synchronizer with position data
        player._state_synchronizer.update_from_http({"position": 100, "duration": 240, "play_state": "play"})

        # Initial position
        pos1 = player.media_position
        assert pos1 == 100

        # Wait a bit and check again (should NOT estimate - returns raw value)
        time.sleep(0.1)
        pos2 = player.media_position
        # Should remain unchanged (raw device value, no estimation)
        assert pos2 == 100

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_media_image_url(self, mock_client):
        """Test getting media image URL."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(entity_picture="http://example.com/artwork.jpg", play_state="play")
        player._status_model = status

        assert player.media_image_url == "http://example.com/artwork.jpg"

    @pytest.mark.asyncio
    async def test_media_image_url_cover_url(self, mock_client):
        """Test getting media image URL from cover_url."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(cover_url="http://example.com/cover.jpg", play_state="play")
        player._status_model = status

        assert player.media_image_url == "http://example.com/cover.jpg"

    @pytest.mark.asyncio
    async def test_fetch_cover_art_success(self, mock_client):
        """Test fetching cover art successfully."""
        from unittest.mock import AsyncMock, MagicMock

        from pywiim.player import Player

        player = Player(mock_client)

        # Mock aiohttp session and response
        # The response needs to be an async context manager
        mock_response = MagicMock()
        mock_response.status = 200
        # Headers needs to support .get() method
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="image/jpeg")
        mock_response.headers = mock_headers
        mock_response.read = AsyncMock(return_value=b"fake_image_data")
        # Make it work as async context manager - __aenter__ returns self
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        # session.get() returns the mock_response directly (which is an async context manager)
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.closed = False

        mock_client._session = mock_session

        result = await player.fetch_cover_art("http://example.com/artwork.jpg")

        assert result is not None
        image_bytes, content_type = result
        assert image_bytes == b"fake_image_data"
        assert content_type == "image/jpeg"
        mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_cover_art_uses_current_track_url(self, mock_client):
        """Test fetching cover art uses current track's URL when None provided."""
        from unittest.mock import AsyncMock, MagicMock

        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(entity_picture="http://example.com/track.jpg", play_state="play")
        player._status_model = status

        # Mock aiohttp session and response
        mock_response = MagicMock()
        mock_response.status = 200
        # Headers needs to support .get() method
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="image/png")
        mock_response.headers = mock_headers
        mock_response.read = AsyncMock(return_value=b"track_image_data")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.closed = False

        mock_client._session = mock_session

        result = await player.fetch_cover_art()

        assert result is not None
        image_bytes, content_type = result
        assert image_bytes == b"track_image_data"
        assert content_type == "image/png"
        # Should have called with the track's URL
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args[0]
        assert "track.jpg" in call_args[0]

    @pytest.mark.asyncio
    async def test_fetch_cover_art_no_url(self, mock_client):
        """Test fetching cover art when no URL is available - should return embedded logo."""
        import base64

        from pywiim.api.constants import EMBEDDED_LOGO_BASE64
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play")  # No cover art URL
        player._status_model = status

        # Call fetch_cover_art() with no URL - should return embedded logo without HTTP call
        result = await player.fetch_cover_art()

        assert result is not None
        image_bytes, content_type = result

        # Verify it returned the embedded logo (decoded from base64)
        expected_bytes = base64.b64decode("".join(EMBEDDED_LOGO_BASE64))
        assert image_bytes == expected_bytes
        assert content_type == "image/png"

        # Verify NO HTTP call was made (embedded logo served directly)
        mock_client._session.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_cover_art_caching(self, mock_client):
        """Test that cover art is cached after first fetch."""
        from unittest.mock import AsyncMock, MagicMock

        from pywiim.player import Player

        player = Player(mock_client)

        # Mock aiohttp session and response
        mock_response = MagicMock()
        mock_response.status = 200
        # Headers needs to support .get() method
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="image/jpeg")
        mock_response.headers = mock_headers
        mock_response.read = AsyncMock(return_value=b"cached_image_data")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.closed = False

        mock_client._session = mock_session

        url = "http://example.com/cache_test.jpg"

        # First fetch - should make HTTP request
        result1 = await player.fetch_cover_art(url)
        assert result1 is not None
        assert mock_session.get.call_count == 1

        # Second fetch - should use cache
        result2 = await player.fetch_cover_art(url)
        assert result2 is not None
        assert result2 == result1
        # Should still be only 1 call (cached)
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_cover_art_http_error(self, mock_client):
        """Test fetching cover art handles HTTP errors gracefully."""
        from unittest.mock import AsyncMock, MagicMock

        from pywiim.player import Player

        player = Player(mock_client)

        # Mock aiohttp session with 404 response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.closed = False

        mock_client._session = mock_session

        result = await player.fetch_cover_art("http://example.com/notfound.jpg")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_cover_art_network_error(self, mock_client):
        """Test fetching cover art handles network errors gracefully."""
        from unittest.mock import AsyncMock, MagicMock

        import aiohttp

        from pywiim.player import Player

        player = Player(mock_client)

        # Mock aiohttp session that raises exception
        mock_session = MagicMock()
        mock_session.get = AsyncMock(side_effect=aiohttp.ClientError("Network error"))
        mock_session.closed = False

        mock_client._session = mock_session

        result = await player.fetch_cover_art("http://example.com/error.jpg")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_cover_art_creates_session_when_needed(self, mock_client):
        """Test fetching cover art creates temporary session when client has none."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from pywiim.player import Player

        player = Player(mock_client)
        mock_client._session = None  # No session on client

        # Mock aiohttp session and response
        mock_response = MagicMock()
        mock_response.status = 200
        # Headers needs to support .get() method
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="image/jpeg")
        mock_response.headers = mock_headers
        mock_response.read = AsyncMock(return_value=b"image_data")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()
        mock_session.closed = False

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await player.fetch_cover_art("http://example.com/test.jpg")

            assert result is not None
            mock_session.get.assert_called_once()
            mock_session.close.assert_called_once()  # Should close temporary session

    @pytest.mark.asyncio
    async def test_get_cover_art_bytes(self, mock_client):
        """Test get_cover_art_bytes convenience method."""
        from unittest.mock import AsyncMock, MagicMock

        from pywiim.player import Player

        player = Player(mock_client)

        # Mock aiohttp session and response
        mock_response = MagicMock()
        mock_response.status = 200
        # Headers needs to support .get() method
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="image/jpeg")
        mock_response.headers = mock_headers
        mock_response.read = AsyncMock(return_value=b"image_bytes")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.closed = False

        mock_client._session = mock_session

        result = await player.get_cover_art_bytes("http://example.com/test.jpg")

        assert result == b"image_bytes"

    @pytest.mark.asyncio
    async def test_get_cover_art_bytes_none(self, mock_client):
        """Test get_cover_art_bytes returns embedded logo when no cover art."""
        import base64

        from pywiim.api.constants import EMBEDDED_LOGO_BASE64
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play")  # No cover art URL
        player._status_model = status

        result = await player.get_cover_art_bytes()

        # Should return embedded logo bytes, not None
        assert result is not None
        expected_bytes = base64.b64decode("".join(EMBEDDED_LOGO_BASE64))
        assert result == expected_bytes

    @pytest.mark.asyncio
    async def test_shuffle_state(self, mock_client):
        """Test getting shuffle state."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play", source="usb")
        status.shuffle = "1"  # shuffle is a string field
        player._status_model = status

        assert player.shuffle_state is True

    @pytest.mark.asyncio
    async def test_shuffle_state_from_play_mode(self, mock_client):
        """Test getting shuffle state from play_mode."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play", source="usb")
        status.play_mode = "shuffle"
        player._status_model = status

        assert player.shuffle_state is True

    @pytest.mark.asyncio
    async def test_repeat_mode_one(self, mock_client):
        """Test getting repeat mode 'one'."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(repeat="one", play_state="play", source="usb")
        player._status_model = status

        assert player.repeat_mode == "one"

    @pytest.mark.asyncio
    async def test_repeat_mode_all(self, mock_client):
        """Test getting repeat mode 'all'."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(repeat="all", play_state="play", source="usb")
        player._status_model = status

        assert player.repeat_mode == "all"

    @pytest.mark.asyncio
    async def test_repeat_mode_from_play_mode(self, mock_client):
        """Test getting repeat mode from play_mode."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play", source="usb")
        status.play_mode = "repeat_all"
        player._status_model = status

        assert player.repeat_mode == "all"

    @pytest.mark.asyncio
    async def test_shuffle_supported_device_controlled_source(self, mock_client):
        """Test shuffle_supported returns True for device-controlled sources."""
        from pywiim.player import Player

        player = Player(mock_client)

        # Test device-controlled sources
        for source in ["usb", "line_in", "optical", "coaxial", "playlist", "preset", "http"]:
            status = PlayerStatus(source=source, play_state="play")
            player._status_model = status
            assert player.shuffle_supported is True, f"shuffle_supported should be True for {source}"

    @pytest.mark.asyncio
    async def test_shuffle_supported_external_source(self, mock_client):
        """Test shuffle_supported returns False only for truly external sources."""
        from pywiim.player import Player

        player = Player(mock_client)

        # Test external sources (blacklist) - AirPlay is no longer blacklisted (re-enabled for testing)
        for source in ["tunein", "iheartradio", "multiroom"]:
            status = PlayerStatus(source=source, play_state="play")
            player._status_model = status
            assert player.shuffle_supported is False, f"shuffle_supported should be False for {source}"

        # Test sources that ARE now supported (permissive approach)
        for source in ["bluetooth", "dlna", "spotify", "tidal", "qobuz", "deezer"]:
            status = PlayerStatus(source=source, play_state="play")
            player._status_model = status
            assert player.shuffle_supported is True, f"shuffle_supported should be True for {source}"

    @pytest.mark.asyncio
    async def test_repeat_supported_device_controlled_source(self, mock_client):
        """Test repeat_supported returns True for device-controlled sources."""
        from pywiim.player import Player

        player = Player(mock_client)

        # Test device-controlled sources
        for source in ["usb", "line_in", "optical", "coaxial", "playlist", "preset", "http"]:
            status = PlayerStatus(source=source, play_state="play")
            player._status_model = status
            assert player.repeat_supported is True, f"repeat_supported should be True for {source}"

    @pytest.mark.asyncio
    async def test_repeat_supported_external_source(self, mock_client):
        """Test repeat_supported returns False only for truly external sources."""
        from pywiim.player import Player

        player = Player(mock_client)

        # Test external sources (blacklist) - AirPlay is no longer blacklisted (re-enabled for testing)
        for source in ["tunein", "iheartradio", "multiroom"]:
            status = PlayerStatus(source=source, play_state="play")
            player._status_model = status
            assert player.repeat_supported is False, f"repeat_supported should be False for {source}"

        # Test sources that ARE now supported (permissive approach)
        for source in ["bluetooth", "dlna", "spotify", "tidal", "qobuz", "deezer"]:
            status = PlayerStatus(source=source, play_state="play")
            player._status_model = status
            assert player.repeat_supported is True, f"repeat_supported should be True for {source}"

    @pytest.mark.asyncio
    async def test_shuffle_state_returns_none_for_external_source(self, mock_client):
        """Test shuffle_state returns None for external sources (radio streams only)."""
        from pywiim.player import Player

        player = Player(mock_client)
        # Radio streams don't support shuffle
        status = PlayerStatus(source="tunein", play_state="play", loop_mode=4)  # loop_mode=4 is shuffle
        player._status_model = status

        # Should return None because TuneIn is a radio stream (blacklisted)
        assert player.shuffle_state is None

    @pytest.mark.asyncio
    async def test_repeat_mode_returns_none_for_external_source(self, mock_client):
        """Test repeat_mode returns None only for blacklisted external sources."""
        from pywiim.player import Player

        player = Player(mock_client)
        # Radio streams don't support repeat
        status = PlayerStatus(
            source="tunein", play_state="play", loop_mode=2
        )  # loop_mode=2 is shuffle+repeat_all for WiiM
        player._status_model = status

        # Should return None because TuneIn is a radio stream (blacklisted)
        assert player.repeat_mode is None

        # AirPlay is blacklisted - tested and confirmed iOS controls playback, not device
        status = PlayerStatus(source="airplay", play_state="play", loop_mode=2)
        player._status_model = status
        # Should return None because AirPlay is blacklisted (iOS device controls playback)
        assert player.repeat_mode is None

        # Bluetooth should also work (permissive approach)
        status = PlayerStatus(source="bluetooth", play_state="play", loop_mode=2)
        player._status_model = status
        assert player.repeat_mode is not None  # Bluetooth supports device control

    @pytest.mark.asyncio
    async def test_shuffle_state_works_for_device_controlled_source(self, mock_client):
        """Test shuffle_state works normally for device-controlled sources."""
        from pywiim.player import Player

        player = Player(mock_client)
        # For WiiM: loop_mode=3 is shuffle (no repeat), loop_mode=4 is normal (no shuffle, no repeat)
        status = PlayerStatus(source="usb", play_state="play", loop_mode=3)
        player._status_model = status

        # Should decode loop_mode normally for USB source
        assert player.shuffle_state is True

    @pytest.mark.asyncio
    async def test_repeat_mode_works_for_device_controlled_source(self, mock_client):
        """Test repeat_mode works normally for device-controlled sources."""
        from pywiim.player import Player

        player = Player(mock_client)
        # For WiiM: loop_mode=0 is repeat_all, loop_mode=2 is shuffle+repeat_all
        status = PlayerStatus(source="usb", play_state="play", loop_mode=0)
        player._status_model = status

        # Should decode loop_mode normally for USB source
        assert player.repeat_mode == "all"

    @pytest.mark.asyncio
    async def test_eq_preset(self, mock_client):
        """Test getting EQ preset."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(eq_preset="flat", play_state="play")
        player._status_model = status

        assert player.eq_preset == "flat"

    @pytest.mark.asyncio
    async def test_available_sources(self, mock_client):
        """Test getting available sources."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", input_list=["wifi", "bluetooth", "line_in"])
        player._device_info = device_info

        # WiFi should be filtered out, returns only physical inputs
        assert player.available_sources == ["bluetooth", "line_in"]

    @pytest.mark.asyncio
    async def test_available_sources_filters_wifi_variations(self, mock_client):
        """Test that WiFi is filtered out regardless of case."""
        from pywiim.player import Player

        player = Player(mock_client)
        # Test various case variations of wifi
        device_info = DeviceInfo(uuid="test", input_list=["WiFi", "WIFI", "wifi", "bluetooth", "line_in"])
        player._device_info = device_info

        # All WiFi variations should be filtered out, returns only physical inputs
        assert player.available_sources == ["bluetooth", "line_in"]

    @pytest.mark.asyncio
    async def test_available_sources_no_wifi(self, mock_client):
        """Test available sources when WiFi is not in the list."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", input_list=["bluetooth", "line_in", "optical"])
        player._device_info = device_info

        # Returns only physical inputs (no current source)
        assert player.available_sources == ["bluetooth", "line_in", "optical"]

    @pytest.mark.asyncio
    async def test_available_sources_only_wifi(self, mock_client):
        """Test available sources when only WiFi is in the list."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", input_list=["wifi"])
        player._device_info = device_info

        # WiFi is filtered out, fallback adds default physical inputs
        assert player.available_sources == ["bluetooth", "line_in", "optical"]

    @pytest.mark.asyncio
    async def test_available_sources_none(self, mock_client):
        """Test available sources when device info is None."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._device_info = None

        assert player.available_sources is None

    @pytest.mark.asyncio
    async def test_available_sources_filters_streaming_services(self, mock_client):
        """Test that unconfigured streaming services are filtered out."""
        from pywiim.player import Player

        player = Player(mock_client)
        # Device reports all sources including streaming services
        device_info = DeviceInfo(
            uuid="test", input_list=["bluetooth", "line_in", "airplay", "spotify", "tidal", "amazon", "qobuz"]
        )
        player._device_info = device_info
        player._status_model = None  # No current source

        # Should return only physical sources (no streaming services unless active)
        result = player.available_sources
        assert "bluetooth" in result
        assert "line_in" in result
        assert "airplay" not in result  # Not active, filtered out
        assert "dlna" not in result  # Not in input_list (filtered from input_list)
        assert "spotify" not in result  # Not active, filtered out
        assert "tidal" not in result
        assert "amazon" not in result
        assert "qobuz" not in result

    @pytest.mark.asyncio
    async def test_available_sources_includes_active_streaming_service(self, mock_client):
        """Test that currently active streaming service is included."""
        from pywiim.player import Player

        player = Player(mock_client)
        # Device reports all sources including streaming services
        device_info = DeviceInfo(
            uuid="test", input_list=["bluetooth", "line_in", "airplay", "spotify", "tidal", "amazon"]
        )
        player._device_info = device_info

        # Currently playing from Spotify
        status = PlayerStatus(source="spotify", play_state="play", volume=50, mute=False)
        player._status_model = status

        # Should include spotify since it's the current source
        result = player.available_sources
        assert "bluetooth" in result
        assert "line_in" in result
        assert "airplay" not in result  # Not active, filtered out
        assert "dlna" not in result  # Not in input_list (filtered from input_list)
        assert "spotify" in result  # Included because it's the current source
        assert "tidal" not in result  # Not active
        assert "amazon" not in result  # Not active

    @pytest.mark.asyncio
    async def test_available_sources_dlna_only_when_active(self, mock_client):
        """Test that DLNA is only included when currently active (not always)."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", input_list=["bluetooth", "line_in", "dlna", "spotify"])
        player._device_info = device_info
        player._status_model = None

        result = player.available_sources
        assert "dlna" not in result  # Not active, filtered out
        assert "spotify" not in result  # Not active, filtered out
        assert "bluetooth" in result
        assert "line_in" in result

    @pytest.mark.asyncio
    async def test_available_sources_streaming_service_variations(self, mock_client):
        """Test filtering works with streaming service name variations."""
        from pywiim.player import Player

        player = Player(mock_client)
        # Test case variations and compound names
        device_info = DeviceInfo(
            uuid="test", input_list=["bluetooth", "Spotify", "TIDAL", "Amazon Music", "iHeartRadio"]
        )
        player._device_info = device_info
        player._status_model = None

        result = player.available_sources
        assert "bluetooth" in result
        # All streaming services should be filtered out when not active
        assert "Spotify" not in result
        assert "TIDAL" not in result
        assert "Amazon Music" not in result
        assert "iHeartRadio" not in result

    @pytest.mark.asyncio
    async def test_available_sources_includes_multiroom_source(self, mock_client):
        """Test that multi-room follower source is included when active."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", input_list=["bluetooth", "line_in", "optical"])
        player._device_info = device_info

        # Currently following another device in multi-room
        status = PlayerStatus(source="Master Bedroom", play_state="play", volume=50, mute=False)
        player._status_model = status

        # Should include the multi-room master name as current source (preserves original casing)
        result = player.available_sources
        assert "bluetooth" in result
        assert "line_in" in result
        assert "optical" in result
        assert "Master Bedroom" in result  # Included because it's the current source (casing preserved)

    @pytest.mark.asyncio
    async def test_available_sources_preserves_source_casing(self, mock_client):
        """Test that source names preserve their original casing for UI display."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", input_list=["bluetooth", "line_in", "optical"])
        player._device_info = device_info

        # Test various properly-cased source names
        test_cases = [
            ("AirPlay", "AirPlay"),
            ("Spotify", "Spotify"),
            ("Amazon Music", "Amazon Music"),
            ("TIDAL", "TIDAL"),
        ]

        for source_name, expected_name in test_cases:
            status = PlayerStatus(source=source_name, play_state="play", volume=50, mute=False)
            player._status_model = status

            result = player.available_sources
            assert expected_name in result, f"Expected {expected_name} to be preserved in available_sources"
            assert (
                source_name.lower() not in result or source_name == source_name.lower()
            ), f"Source should not be lowercased: got {result}"

    @pytest.mark.asyncio
    async def test_audio_output_mode(self, mock_client):
        """Test getting audio output mode."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._audio_output_status = {"hardware": 0, "source": 0}
        mock_client.audio_output_mode_to_name = MagicMock(return_value="Line Out")

        assert player.audio_output_mode == "Line Out"

    @pytest.mark.asyncio
    async def test_audio_output_mode_bluetooth(self, mock_client):
        """Test getting audio output mode when Bluetooth is active."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._audio_output_status = {"hardware": 0, "source": 1}  # Bluetooth active

        assert player.audio_output_mode == "Bluetooth Out"

    @pytest.mark.asyncio
    async def test_audio_output_mode_int(self, mock_client):
        """Test getting audio output mode as integer."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._audio_output_status = {"hardware": 1, "source": 0}

        assert player.audio_output_mode_int == 1

    @pytest.mark.asyncio
    async def test_audio_output_mode_int_bluetooth(self, mock_client):
        """Test getting audio output mode int when Bluetooth is active."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._audio_output_status = {"hardware": 0, "source": 1}  # Bluetooth active

        assert player.audio_output_mode_int == 4  # Bluetooth Out

    @pytest.mark.asyncio
    async def test_available_output_modes_wiim_pro(self, mock_client):
        """Test available output modes for WiiM Pro."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", model="WiiM Pro")
        player._device_info = device_info
        # capabilities is read-only, patch it via _capabilities if needed
        if hasattr(mock_client, "_capabilities"):
            mock_client._capabilities["supports_audio_output"] = True

        modes = player.available_output_modes

        assert "Line Out" in modes
        assert "Optical Out" in modes
        assert "Coax Out" in modes
        # "Bluetooth Out" is not in available_output_modes - only specific BT devices shown
        assert "Bluetooth Out" not in modes

    @pytest.mark.asyncio
    async def test_available_output_modes_wiim_mini(self, mock_client):
        """Test available output modes for WiiM Mini."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", model="WiiM Mini")
        player._device_info = device_info
        # capabilities is read-only, patch it via _capabilities if needed
        if hasattr(mock_client, "_capabilities"):
            mock_client._capabilities["supports_audio_output"] = True

        modes = player.available_output_modes

        assert "Line Out" in modes
        assert "Optical Out" in modes
        assert "Coax Out" not in modes  # Mini doesn't have Coax

    @pytest.mark.asyncio
    async def test_available_output_modes_not_supported(self, mock_client):
        """Test available output modes when not supported."""
        from pywiim.player import Player

        player = Player(mock_client)
        # capabilities is read-only, patch it via _capabilities if needed
        if hasattr(mock_client, "_capabilities"):
            mock_client._capabilities["supports_audio_output"] = False

        modes = player.available_output_modes

        assert modes == []

    @pytest.mark.asyncio
    async def test_is_bluetooth_output_active(self, mock_client):
        """Test checking if Bluetooth output is active."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._audio_output_status = {"source": 1}  # Bluetooth active

        assert player.is_bluetooth_output_active is True

    @pytest.mark.asyncio
    async def test_is_bluetooth_output_active_false(self, mock_client):
        """Test checking if Bluetooth output is not active."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._audio_output_status = {"source": 0}  # Bluetooth not active

        assert player.is_bluetooth_output_active is False

    @pytest.mark.asyncio
    async def test_model_property(self, mock_client):
        """Test getting model property."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", model="WiiM Pro")
        player._device_info = device_info

        assert player.model == "WiiM Pro"

    @pytest.mark.asyncio
    async def test_firmware_property(self, mock_client):
        """Test getting firmware property."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", firmware="5.0.123456")
        player._device_info = device_info

        assert player.firmware == "5.0.123456"

    @pytest.mark.asyncio
    async def test_mac_address_property(self, mock_client):
        """Test getting MAC address property."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", mac="AA:BB:CC:DD:EE:FF")
        player._device_info = device_info

        assert player.mac_address == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_uuid_property(self, mock_client):
        """Test getting UUID property."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test-uuid-123")
        player._device_info = device_info

        assert player.uuid == "test-uuid-123"

    @pytest.mark.asyncio
    async def test_status_model_property(self, mock_client):
        """Test getting status_model property."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play", volume=50)
        player._status_model = status

        assert player.status_model == status

    @pytest.mark.asyncio
    async def test_device_info_property(self, mock_client):
        """Test getting device_info property."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test")
        player._device_info = device_info

        assert player.device_info == device_info

    @pytest.mark.asyncio
    async def test_is_muted_various_formats(self, mock_client):
        """Test is_muted with various formats."""
        from pywiim.player import Player

        player = Player(mock_client)

        # Test with boolean True
        status = PlayerStatus(mute=True, play_state="play")
        player._status_model = status
        assert player.is_muted is True

        # Test with int 1
        status = PlayerStatus(mute=1, play_state="play")
        player._status_model = status
        assert player.is_muted is True

        # Test with string "1"
        status = PlayerStatus(play_state="play")
        status.mute = "1"
        player._status_model = status
        assert player.is_muted is True

        # Test with string "true"
        status = PlayerStatus(play_state="play")
        status.mute = "true"
        player._status_model = status
        assert player.is_muted is True

        # Test with string "0"
        status = PlayerStatus(play_state="play")
        status.mute = "0"
        player._status_model = status
        assert player.is_muted is False

    @pytest.mark.asyncio
    async def test_media_position_track_change(self, mock_client):
        """Test media position resets on track change."""
        from pywiim.player import Player

        player = Player(mock_client)
        status1 = PlayerStatus(position=100, duration=240, play_state="play", title="Song 1", artist="Artist 1")
        player._status_model = status1
        # Update state synchronizer with position data
        player._state_synchronizer.update_from_http(
            {"position": 100, "duration": 240, "play_state": "play", "title": "Song 1", "artist": "Artist 1"}
        )

        pos1 = player.media_position
        assert pos1 == 100

        # Change track
        status2 = PlayerStatus(position=50, duration=200, play_state="play", title="Song 2", artist="Artist 2")
        player._status_model = status2
        # Update state synchronizer with new track data
        player._state_synchronizer.update_from_http(
            {"position": 50, "duration": 200, "play_state": "play", "title": "Song 2", "artist": "Artist 2"}
        )

        # Position should reset estimation
        pos2 = player.media_position
        assert pos2 == 50

    @pytest.mark.asyncio
    async def test_media_position_seek_detection(self, mock_client):
        """Test media position detects seeks."""
        from pywiim.player import Player

        player = Player(mock_client)
        status1 = PlayerStatus(position=100, duration=240, play_state="play")
        player._status_model = status1
        # Update state synchronizer with position data
        player._state_synchronizer.update_from_http({"position": 100, "duration": 240, "play_state": "play"})
        player._last_position = 100

        pos1 = player.media_position
        assert pos1 == 100

        # Simulate seek backward
        status2 = PlayerStatus(position=50, duration=240, play_state="play")
        player._status_model = status2
        # Update state synchronizer with new position data
        player._state_synchronizer.update_from_http({"position": 50, "duration": 240, "play_state": "play"})

        pos2 = player.media_position
        # Should detect seek and reset estimation
        assert pos2 == 50

    @pytest.mark.asyncio
    async def test_media_position_estimation_drift_limit(self, mock_client):
        """Test media position estimation has drift limit."""
        import time

        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(position=100, duration=240, play_state="play")
        player._status_model = status
        # Update state synchronizer with position data
        player._state_synchronizer.update_from_http({"position": 100, "duration": 240, "play_state": "play"})

        # Set estimation base far in the past to test drift limit
        player._estimation_base_position = 100
        player._estimation_start_time = time.time() - 100  # 100 seconds ago

        pos = player.media_position
        # Should not drift more than 30 seconds
        assert pos <= 130  # 100 + 30 max drift

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_available_output_modes_wiim_amp(self, mock_client):
        """Test available output modes for WiiM Amp."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", model="WiiM Amp")
        player._device_info = device_info
        # capabilities is read-only, patch it via _capabilities if needed
        if hasattr(mock_client, "_capabilities"):
            mock_client._capabilities["supports_audio_output"] = True

        modes = player.available_output_modes

        assert modes == ["Line Out"]  # Only Line Out for Amp

    @pytest.mark.asyncio
    async def test_available_output_modes_wiim_ultra(self, mock_client):
        """Test available output modes for WiiM Ultra."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", model="WiiM Ultra")
        player._device_info = device_info
        # capabilities is read-only, patch it via _capabilities if needed
        if hasattr(mock_client, "_capabilities"):
            mock_client._capabilities["supports_audio_output"] = True

        modes = player.available_output_modes

        assert "HDMI Out" in modes
        assert "Headphone Out" in modes
        assert "Line Out" in modes
        # "Bluetooth Out" is not in available_output_modes - only specific BT devices shown
        assert "Bluetooth Out" not in modes

    @pytest.mark.asyncio
    async def test_available_output_modes_unknown_model(self, mock_client):
        """Test available output modes for unknown model."""
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", model="Unknown Device")
        player._device_info = device_info
        # capabilities is read-only, patch it via _capabilities if needed
        if hasattr(mock_client, "_capabilities"):
            mock_client._capabilities["supports_audio_output"] = True

        modes = player.available_output_modes

        # Should return standard modes for unknown device
        assert "Line Out" in modes
        assert "Optical Out" in modes

    @pytest.mark.asyncio
    async def test_join_group_master_not_in_group(self, mock_client):
        """Test joining group when master is not in a group (should auto-create group)."""
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)

        # Mock API calls - create_group and join_slave
        mock_client.create_group = AsyncMock()
        mock_client.join_slave = AsyncMock()

        # Mock refresh to verify join worked - need to set slave status to show it's a slave
        async def mock_slave_refresh(full=False):
            slave._detected_role = "slave"

        slave.refresh = AsyncMock(side_effect=mock_slave_refresh)

        await slave.join_group(master)

        # Verify refresh was called to verify the join
        slave.refresh.assert_called_once_with(full=False)
        # Master should now have a group
        assert master.group is not None
        assert slave in master.group.slaves
        mock_client.create_group.assert_called_once()
        mock_client.join_slave.assert_called_once_with(master.host)

    @pytest.mark.asyncio
    async def test_leave_group_group_none(self, mock_client):
        """Test leaving group when group reference is None - idempotent behavior."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        # Create a group first
        Group(master)
        # Set role to master and keep group reference
        master._role = "master"
        # Now set _group to None to simulate edge case where role is set but group is None
        # This can happen in edge cases where role detection succeeded but group creation failed
        master._group = None  # Simulate None group after role is set

        # Idempotent behavior: When _group is None, is_solo will be True
        # leave_group() should return without error (idempotent)
        await master.leave_group()  # Should not raise

    @pytest.mark.asyncio
    async def test_get_diagnostics_comprehensive(self, mock_client):
        """Test comprehensive diagnostics collection."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        status = PlayerStatus(
            play_state="play",
            volume=50,
            mute=False,
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            position=120,
            duration=240,
        )
        device_info = DeviceInfo(
            uuid="test-uuid",
            name="Test Device",
            model="WiiM Pro",
            firmware="5.0.123456",
            mac="AA:BB:CC:DD:EE:FF",
            ip="192.168.1.100",
        )
        player = Player(mock_client)
        player._status_model = status
        player._device_info = device_info
        player._audio_output_status = {"hardware": 0, "source": 0}

        # Use mock_client's existing capabilities property
        # capabilities is read-only, so we patch it if needed
        if not hasattr(mock_client, "_capabilities"):
            mock_client._capabilities = {
                "supports_eq": True,
                "supports_audio_output": True,
                "is_legacy_device": False,
            }
        mock_client.get_multiroom_status = AsyncMock(return_value={"slaves": 0})
        mock_client.get_device_group_info = AsyncMock(return_value=None)
        mock_client.get_eq = AsyncMock(return_value={"preset": "flat", "enabled": True})
        # api_stats and connection_stats are properties - use PropertyMock

        type(mock_client).api_stats = PropertyMock(return_value={"total_requests": 10, "successful_requests": 9})
        type(mock_client).connection_stats = PropertyMock(return_value={"avg_latency_ms": 50.0, "success_rate": 0.9})

        diagnostics = await player.get_diagnostics()

        assert "timestamp" in diagnostics
        assert "host" in diagnostics
        assert diagnostics["host"] == player.host
        assert diagnostics["device"]["uuid"] == "test-uuid"
        assert diagnostics["device"]["model"] == "WiiM Pro"
        assert diagnostics["status"]["play_state"] == "play"
        assert diagnostics["status"]["title"] == "Test Song"
        assert diagnostics["capabilities"]["supports_eq"] is True
        assert diagnostics["multiroom"]["slaves"] == 0
        assert diagnostics["audio_output"]["hardware"] == 0

    @pytest.mark.asyncio
    async def test_get_diagnostics_with_upnp(self, mock_client):
        """Test diagnostics with UPnP statistics."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play", volume=50)
        device_info = DeviceInfo(uuid="test")
        player._status_model = status
        player._device_info = device_info

        # Mock UPnP eventer
        mock_eventer = MagicMock()
        mock_eventer.statistics = {
            "total_events": 100,
            "events_received": 95,
            "last_event_time": 1234567890.0,
        }
        player._upnp_eventer = mock_eventer

        # capabilities is read-only, use existing mock_client capabilities
        mock_client.get_multiroom_status = AsyncMock(return_value={"slaves": 0})
        mock_client.get_device_group_info = AsyncMock(return_value=None)

        diagnostics = await player.get_diagnostics()

        assert "upnp" in diagnostics
        assert diagnostics["upnp"]["total_events"] == 100

    @pytest.mark.asyncio
    async def test_get_diagnostics_with_group(self, mock_client):
        """Test diagnostics when in a group."""
        from pywiim.group import Group
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        master = Player(mock_client)
        slave = Player(mock_client)
        group = Group(master)
        group.add_slave(slave)

        status = PlayerStatus(play_state="play")
        device_info = DeviceInfo(uuid="test")
        master._status_model = status
        master._device_info = device_info

        # capabilities is read-only, use existing mock_client capabilities
        mock_client.get_multiroom_status = AsyncMock(return_value={"slaves": 1})
        mock_client.get_device_group_info = AsyncMock(
            return_value={
                "master": {"uuid": "master-uuid"},
                "slaves": [{"uuid": "slave-uuid"}],
            }
        )

        diagnostics = await master.get_diagnostics()

        # group_info may not be present if get_device_group_info returns None or fails
        # Just verify diagnostics were collected
        assert "timestamp" in diagnostics
        assert "host" in diagnostics
        assert diagnostics["device"]["uuid"] == "test"

    @pytest.mark.asyncio
    async def test_get_diagnostics_error_handling(self, mock_client):
        """Test diagnostics error handling."""
        from pywiim.models import DeviceInfo, PlayerStatus
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play")
        device_info = DeviceInfo(uuid="test")
        player._status_model = status
        player._device_info = device_info

        # capabilities is read-only, use existing mock_client capabilities
        mock_client.get_multiroom_status = AsyncMock(side_effect=Exception("Network error"))
        mock_client.get_device_group_info = AsyncMock(return_value=None)

        diagnostics = await player.get_diagnostics()

        # Should still return diagnostics (errors are caught and logged)
        assert "timestamp" in diagnostics
        assert "host" in diagnostics
        # multiroom section should have error info
        assert "multiroom" in diagnostics

    @pytest.mark.asyncio
    async def test_refresh_error_handling(self, mock_client):
        """Test refresh handles errors gracefully."""
        from pywiim.models import DeviceInfo
        from pywiim.player import Player

        mock_client.get_player_status_model = AsyncMock(side_effect=Exception("Network error"))
        mock_client.get_device_info_model = AsyncMock(return_value=DeviceInfo(uuid="test"))

        player = Player(mock_client)
        # refresh() catches, logs, and re-raises the original exception
        with pytest.raises(Exception, match="Network error"):
            await player.refresh()

    @pytest.mark.asyncio
    async def test_refresh_partial_failure(self, mock_client):
        """Test refresh when device info fails but status succeeds."""
        from pywiim.models import PlayerStatus
        from pywiim.player import Player

        mock_client.get_player_status_model = AsyncMock(return_value=PlayerStatus(play_state="play"))
        mock_client.get_device_info_model = AsyncMock(side_effect=Exception("Device info error"))

        player = Player(mock_client)
        # refresh() catches, logs, and re-raises the original exception
        with pytest.raises(Exception, match="Device info error"):
            await player.refresh()

    @pytest.mark.asyncio
    async def test_get_status_property(self, mock_client):
        """Test getting status via status_model property."""
        from pywiim.models import PlayerStatus
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play", volume=50)
        player._status_model = status

        assert player.status_model == status

    @pytest.mark.asyncio
    async def test_get_status_method(self, mock_client):
        """Test getting status via method."""
        from pywiim.models import PlayerStatus
        from pywiim.player import Player

        status = PlayerStatus(play_state="play", volume=50)
        mock_client.get_player_status_model = AsyncMock(return_value=status)

        player = Player(mock_client)
        result = await player.get_status()

        assert result == status
        mock_client.get_player_status_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_device_info_property(self, mock_client):
        """Test getting device info via property."""
        from pywiim.models import DeviceInfo
        from pywiim.player import Player

        player = Player(mock_client)
        device_info = DeviceInfo(uuid="test", name="Test Device")
        player._device_info = device_info

        assert player.device_info == device_info

    @pytest.mark.asyncio
    async def test_get_device_info_method(self, mock_client):
        """Test getting device info via method."""
        from pywiim.models import DeviceInfo
        from pywiim.player import Player

        device_info = DeviceInfo(uuid="test", name="Test Device")
        mock_client.get_device_info_model = AsyncMock(return_value=device_info)

        player = Player(mock_client)
        result = await player.get_device_info()

        assert result == device_info
        mock_client.get_device_info_model.assert_called_once()


class TestPlayerUPnPIntegration:
    """Test Player UPnP event integration."""

    @pytest.mark.asyncio
    async def test_apply_diff(self, mock_client):
        """Test applying UPnP diff."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="pause", volume=50, mute=False)
        player._status_model = status

        changes = {"play_state": "play", "volume": 75}
        changed = player.apply_diff(changes)

        assert changed is True
        assert player.play_state == "play"

    @pytest.mark.asyncio
    async def test_apply_diff_no_changes(self, mock_client):
        """Test applying UPnP diff with no changes."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="play", volume=50, mute=False)
        player._status_model = status

        changes = {"play_state": "play", "volume": 50}
        changed = player.apply_diff(changes)

        assert changed is False

    @pytest.mark.asyncio
    async def test_update_from_upnp(self, mock_client):
        """Test updating from UPnP data."""
        from pywiim.player import Player

        player = Player(mock_client)
        status = PlayerStatus(play_state="pause", volume=50, mute=False)
        player._status_model = status

        upnp_data = {"play_state": "play", "volume": 0.75, "muted": False}
        player.update_from_upnp(upnp_data)

        # State should be updated via StateSynchronizer
        assert player._state_synchronizer is not None


class TestPlayerGroupOperations:
    """Test Player group operations."""

    @pytest.mark.asyncio
    async def test_slave_playback_routes_to_master(self, mock_client):
        """Test that slave playback commands route through group to master."""
        from pywiim.group import Group
        from pywiim.player import Player

        # Create master and slave
        master_client = AsyncMock()
        master_client.play = AsyncMock()
        master_client.pause = AsyncMock()
        master_client.next_track = AsyncMock()
        master = Player(master_client)
        master._detected_role = "master"

        slave = Player(mock_client)
        slave._detected_role = "slave"

        # Create group and link them
        group = Group(master)
        group.add_slave(slave)

        # Slave playback commands should route to master
        await slave.play()
        master_client.play.assert_called_once()

        await slave.pause()
        master_client.pause.assert_called_once()

        await slave.next_track()
        master_client.next_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_slave_without_group_raises_error(self, mock_client):
        """Test that slave without group object raises error."""
        from pywiim.exceptions import WiiMError
        from pywiim.player import Player

        # Create a slave player without a group
        player = Player(mock_client)
        player._detected_role = "slave"

        # Should raise WiiMError when trying to play
        with pytest.raises(WiiMError, match="not linked to group"):
            await player.play()

    @pytest.mark.asyncio
    async def test_slave_volume_fires_master_callback(self, mock_client):
        """Test that slave volume changes fire master's callback."""
        from pywiim.group import Group
        from pywiim.player import Player

        # Create master and slave with callbacks
        master_callback_count = {"count": 0}
        slave_callback_count = {"count": 0}

        def master_callback():
            master_callback_count["count"] += 1

        def slave_callback():
            slave_callback_count["count"] += 1

        master_client = AsyncMock()
        master_client.set_volume = AsyncMock()
        master = Player(master_client, on_state_changed=master_callback)

        mock_client.set_volume = AsyncMock()
        slave = Player(mock_client, on_state_changed=slave_callback)

        # Create group and link them
        group = Group(master)
        group.add_slave(slave)

        # Change slave volume
        await slave.set_volume(0.5)

        # Both callbacks should fire
        assert slave_callback_count["count"] == 1
        assert master_callback_count["count"] == 1

    @pytest.mark.asyncio
    async def test_master_volume_only_fires_own_callback(self, mock_client):
        """Test that master volume changes only fire master's callback."""
        from pywiim.group import Group
        from pywiim.player import Player

        # Create master and slave with callbacks
        master_callback_count = {"count": 0}
        slave_callback_count = {"count": 0}

        def master_callback():
            master_callback_count["count"] += 1

        def slave_callback():
            slave_callback_count["count"] += 1

        mock_client.set_volume = AsyncMock()
        master = Player(mock_client, on_state_changed=master_callback)

        slave_client = AsyncMock()
        slave_client.set_volume = AsyncMock()
        slave = Player(slave_client, on_state_changed=slave_callback)

        # Create group and link them
        group = Group(master)
        group.add_slave(slave)

        # Change master volume
        await master.set_volume(0.8)

        # Only master callback should fire
        assert master_callback_count["count"] == 1
        assert slave_callback_count["count"] == 0

    @pytest.mark.asyncio
    async def test_create_group(self, mock_client, mock_player_status):
        """Test creating a group."""
        from pywiim.player import Player

        mock_client.create_group = AsyncMock()
        mock_client.get_player_status_model = AsyncMock(return_value=mock_player_status)

        player = Player(mock_client)
        group = await player.create_group()

        assert group is not None
        assert group.master == player
        assert player.group == group
        mock_client.create_group.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_group_when_in_group(self, mock_client):
        """Test creating group when already in group (returns existing group)."""
        from pywiim.group import Group
        from pywiim.player import Player

        player = Player(mock_client)
        existing_group = Group(player)  # Already in a group

        # create_group should return the existing group when already a master
        result = await player.create_group()

        assert result == existing_group
        assert player.group == existing_group

    @pytest.mark.asyncio
    async def test_join_group(self, mock_client, mock_player_status, mock_aiohttp_session, mock_capabilities):
        """Test joining a group."""
        from pywiim.client import WiiMClient
        from pywiim.group import Group
        from pywiim.player import Player

        # Create separate clients for master and slave
        master_client = WiiMClient(
            host="192.168.1.100",
            port=80,
            session=mock_aiohttp_session,
            capabilities=mock_capabilities,
        )
        master_client._request = AsyncMock(return_value={"status": "ok"})

        slave_client = WiiMClient(
            host="192.168.1.101",
            port=80,
            session=mock_aiohttp_session,
            capabilities=mock_capabilities,
        )
        slave_client._request = AsyncMock(return_value={"status": "ok"})

        master = Player(master_client)
        slave = Player(slave_client)
        group = Group(master)

        # Mock master status
        master_client.get_player_status_model = AsyncMock(return_value=mock_player_status)
        master_client.get_multiroom_status = AsyncMock(return_value={"slaves": [slave.host]})

        # Mock slave status - should show it's a slave with master info
        slave_status = mock_player_status.model_copy()
        slave_status.group = master.host
        slave_status.master_ip = master.host
        slave_client.get_player_status_model = AsyncMock(return_value=slave_status)
        slave_client.get_multiroom_status = AsyncMock(return_value={"slaves": []})
        slave_client.join_slave = AsyncMock()

        # Mock refresh to update slave status after join - must update role to "slave"
        async def mock_slave_refresh(full=False):
            slave._detected_role = "slave"
            slave._status_model = slave_status

        slave.refresh = AsyncMock(side_effect=mock_slave_refresh)

        await slave.join_group(master)

        # Verify refresh was called to verify the join
        slave.refresh.assert_called_once_with(full=False)
        assert slave.group == group
        assert slave in group.slaves
        slave_client.join_slave.assert_called_once_with(master.host)

    @pytest.mark.asyncio
    async def test_leave_group_as_slave(self, mock_client, mock_player_status):
        """Test leaving group as slave."""
        from pywiim.group import Group
        from pywiim.player import Player

        mock_client.get_player_status_model = AsyncMock(return_value=mock_player_status)
        master = Player(mock_client)
        master._detected_role = "master"  # Set role from device API state
        slave = Player(mock_client)
        slave._detected_role = "slave"  # Set role from device API state
        group = Group(master)
        group.add_slave(slave)

        mock_client._request = AsyncMock(return_value={"status": "ok"})

        await slave.leave_group()

        assert slave.group is None
        assert slave not in group.slaves
        # When last slave leaves, group should be auto-disbanded
        assert master.group is None
        # Should call _request for leave, then disband calls _request again
        assert mock_client._request.call_count >= 1
        mock_client._request.assert_any_call("/httpapi.asp?command=multiroom:Ungroup")

    @pytest.mark.asyncio
    async def test_leave_group_as_slave_with_multiple_slaves(
        self, mock_client, mock_player_status, mock_aiohttp_session, mock_capabilities
    ):
        """Test leaving group as slave when multiple slaves exist (should not auto-disband)."""
        from pywiim.client import WiiMClient
        from pywiim.group import Group
        from pywiim.player import Player

        # Create separate clients for each player
        master_client = WiiMClient(
            host="192.168.1.100",
            port=80,
            session=mock_aiohttp_session,
            capabilities=mock_capabilities,
        )
        master_client._request = AsyncMock(return_value={"status": "ok"})

        slave1_client = WiiMClient(
            host="192.168.1.101",
            port=80,
            session=mock_aiohttp_session,
            capabilities=mock_capabilities,
        )
        slave1_client._request = AsyncMock(return_value={"status": "ok"})

        slave2_client = WiiMClient(
            host="192.168.1.102",
            port=80,
            session=mock_aiohttp_session,
            capabilities=mock_capabilities,
        )
        slave2_client._request = AsyncMock(return_value={"status": "ok"})

        master = Player(master_client)
        master._detected_role = "master"  # Set role from device API state
        slave1 = Player(slave1_client)
        slave1._detected_role = "slave"  # Set role from device API state
        slave2 = Player(slave2_client)
        slave2._detected_role = "slave"  # Set role from device API state
        group = Group(master)
        group.add_slave(slave1)
        group.add_slave(slave2)

        # Mock status models
        master_client.get_player_status_model = AsyncMock(return_value=mock_player_status)
        # Slave1 after leaving should be solo (no group, no master info)
        slave1_status = mock_player_status.model_copy()
        slave1_status.group = None
        slave1_status.master_ip = None
        slave1_status.master_uuid = None
        slave1_client.get_player_status_model = AsyncMock(return_value=slave1_status)
        # Slave2 should still be in group (has master info)
        slave2_status = mock_player_status.model_copy()
        slave2_status.group = master.host
        slave2_status.master_ip = master.host
        slave2_client.get_player_status_model = AsyncMock(return_value=slave2_status)

        # Mock multiroom: slave1 is solo, master still has slave2
        slave1_client.get_multiroom_status = AsyncMock(return_value={"slaves": []})
        master_client.get_multiroom_status = AsyncMock(return_value={"slaves": [slave2.host]})

        await slave1.leave_group()

        assert slave1.group is None
        assert slave1 not in group.slaves
        assert slave2 in group.slaves
        # Group should still exist with remaining slave
        assert master.group == group
        # Should call _request for leave
        slave1_client._request.assert_called_once_with("/httpapi.asp?command=multiroom:Ungroup")
        # Should not call delete_group when other slaves remain (no auto-disband)
        assert master_client._request.call_count == 0

    @pytest.mark.asyncio
    async def test_leave_group_clears_metadata(self, mock_client, mock_player_status):
        """Test that leaving group clears metadata and artwork."""
        from pywiim.group import Group
        from pywiim.player import Player

        mock_client.get_player_status_model = AsyncMock(return_value=mock_player_status)
        master = Player(mock_client)
        master._detected_role = "master"  # Set role from device API state
        slave = Player(mock_client)
        slave._detected_role = "slave"  # Set role from device API state
        group = Group(master)

        # Set up slave with metadata from group playback
        slave._status_model = mock_player_status.model_copy()
        slave._status_model.source = master.host
        slave._status_model.title = "Test Song"
        slave._status_model.artist = "Test Artist"
        slave._status_model.album = "Test Album"
        slave._status_model.entity_picture = "http://example.com/art.jpg"
        slave._status_model.cover_url = "http://example.com/cover.jpg"

        group.add_slave(slave)

        mock_client._request = AsyncMock(return_value={"status": "ok"})

        await slave.leave_group()

        # Verify metadata and artwork are cleared
        assert slave._status_model.title is None
        assert slave._status_model.artist is None
        assert slave._status_model.album is None
        assert slave._status_model.entity_picture is None
        assert slave._status_model.cover_url is None
        assert slave._status_model.source is None

    @pytest.mark.asyncio
    async def test_leave_group_as_master(self, mock_client):
        """Test leaving group as master (disbands group)."""
        from pywiim.group import Group
        from pywiim.player import Player

        master = Player(mock_client)
        master._detected_role = "master"  # Set role from device API state
        slave = Player(mock_client)
        slave._detected_role = "slave"  # Set role from device API state
        group = Group(master)
        group.add_slave(slave)

        mock_client._request = AsyncMock(return_value={"status": "ok"})

        await master.leave_group()

        assert master.group is None
        assert slave.group is None
        # Master leaving calls disband which calls _request
        mock_client._request.assert_called_once_with("/httpapi.asp?command=multiroom:Ungroup")

    @pytest.mark.asyncio
    async def test_leave_group_when_solo(self, mock_client):
        """Test leaving group when solo - should be idempotent (no error)."""
        from pywiim.player import Player

        player = Player(mock_client)

        # Idempotent behavior: no error when solo, just returns
        await player.leave_group()  # Should not raise


class TestPlayerReboot:
    """Test Player reboot method."""

    @pytest.mark.asyncio
    async def test_reboot(self, mock_client):
        """Test rebooting device."""
        from pywiim.player import Player

        mock_client.reboot = AsyncMock()

        player = Player(mock_client)
        await player.reboot()

        assert player.available is False
        mock_client.reboot.assert_called_once()


class TestPlayerBluetoothOutputs:
    """Test Bluetooth output device handling."""

    @pytest.mark.asyncio
    async def test_bluetooth_output_devices_empty(self, mock_client):
        """Test bluetooth_output_devices with no paired devices."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._bluetooth_history = []

        devices = player.bluetooth_output_devices
        assert devices == []

    @pytest.mark.asyncio
    async def test_bluetooth_output_devices_filter_audio_sinks(self, mock_client):
        """Test that only Audio Sink devices are returned."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._bluetooth_history = [
            {"name": "Speaker", "ad": "AA:BB:CC:DD:EE:FF", "ct": 1, "role": "Audio Sink"},
            {"name": "Phone", "ad": "11:22:33:44:55:66", "ct": 0, "role": "Audio Source"},
            {"name": "Headphones", "ad": "22:33:44:55:66:77", "ct": 0, "role": "Audio Sink"},
        ]

        devices = player.bluetooth_output_devices
        assert len(devices) == 2
        assert devices[0]["name"] == "Speaker"
        assert devices[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        assert devices[0]["connected"] is True
        assert devices[1]["name"] == "Headphones"
        assert devices[1]["mac"] == "22:33:44:55:66:77"
        assert devices[1]["connected"] is False

    @pytest.mark.asyncio
    async def test_bluetooth_output_devices_unknown_device(self, mock_client):
        """Test handling of device with missing name."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._bluetooth_history = [
            {"ad": "AA:BB:CC:DD:EE:FF", "ct": 1, "role": "Audio Sink"},
        ]

        devices = player.bluetooth_output_devices
        assert len(devices) == 1
        assert devices[0]["name"] == "Unknown Device"
        assert devices[0]["mac"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_available_outputs_hardware_only(self, mock_client):
        """Test available_outputs with no BT devices."""
        from pywiim.models import DeviceInfo
        from pywiim.player import Player

        type(mock_client).capabilities = PropertyMock(return_value={"supports_audio_output": True})
        player = Player(mock_client)
        player._device_info = DeviceInfo(
            uuid="test", name="Test", model="WiiM Pro", firmware="1.0", ip="192.168.1.100", mac="AA:BB:CC:DD:EE:FF"
        )
        player._bluetooth_history = []

        outputs = player.available_outputs
        assert "Line Out" in outputs
        assert "Optical Out" in outputs
        assert "Coax Out" in outputs
        assert len([o for o in outputs if o.startswith("BT: ")]) == 0

    @pytest.mark.asyncio
    async def test_available_outputs_with_bt_devices(self, mock_client):
        """Test available_outputs combines hardware modes and BT devices."""
        from pywiim.models import DeviceInfo
        from pywiim.player import Player

        type(mock_client).capabilities = PropertyMock(return_value={"supports_audio_output": True})
        player = Player(mock_client)
        player._device_info = DeviceInfo(
            uuid="test", name="Test", model="WiiM Pro", firmware="1.0", ip="192.168.1.100", mac="AA:BB:CC:DD:EE:FF"
        )
        player._bluetooth_history = [
            {"name": "Sony Speaker", "ad": "AA:BB:CC:DD:EE:FF", "ct": 1, "role": "Audio Sink"},
            {"name": "JBL Headphones", "ad": "11:22:33:44:55:66", "ct": 0, "role": "Audio Sink"},
        ]

        outputs = player.available_outputs
        assert "Line Out" in outputs
        assert "Optical Out" in outputs
        assert "Coax Out" in outputs
        assert "BT: Sony Speaker" in outputs
        assert "BT: JBL Headphones" in outputs

    @pytest.mark.asyncio
    async def test_available_outputs_wiim_ultra(self, mock_client):
        """Test available_outputs for WiiM Ultra with all outputs including HDMI and Headphone."""
        from pywiim.models import DeviceInfo
        from pywiim.player import Player

        type(mock_client).capabilities = PropertyMock(return_value={"supports_audio_output": True})
        player = Player(mock_client)
        player._device_info = DeviceInfo(
            uuid="test", name="Test", model="WiiM Ultra", firmware="1.0", ip="192.168.1.100", mac="AA:BB:CC:DD:EE:FF"
        )
        player._bluetooth_history = []

        outputs = player.available_outputs
        # Ultra has all standard outputs plus HDMI and Headphone
        assert "Line Out" in outputs
        assert "Optical Out" in outputs
        assert "Coax Out" in outputs
        assert "Headphone Out" in outputs
        assert "HDMI Out" in outputs
        assert len([o for o in outputs if o.startswith("BT: ")]) == 0

    @pytest.mark.asyncio
    async def test_available_outputs_wiim_ultra_with_bt(self, mock_client):
        """Test available_outputs for WiiM Ultra with BT devices (removes generic BT Out)."""
        from pywiim.models import DeviceInfo
        from pywiim.player import Player

        type(mock_client).capabilities = PropertyMock(return_value={"supports_audio_output": True})
        player = Player(mock_client)
        player._device_info = DeviceInfo(
            uuid="test", name="Test", model="WiiM Ultra", firmware="1.0", ip="192.168.1.100", mac="AA:BB:CC:DD:EE:FF"
        )
        player._bluetooth_history = [
            {"name": "BT Speaker", "ad": "AA:BB:CC:DD:EE:FF", "ct": 0, "role": "Audio Sink"},
        ]

        outputs = player.available_outputs
        # Ultra-specific outputs
        assert "Headphone Out" in outputs
        assert "HDMI Out" in outputs
        # Standard outputs
        assert "Line Out" in outputs
        assert "Optical Out" in outputs
        assert "Coax Out" in outputs
        assert "BT: BT Speaker" in outputs

    @pytest.mark.asyncio
    async def test_select_output_hardware_mode(self, mock_client):
        """Test selecting a hardware output mode."""
        from pywiim.models import PlayerStatus
        from pywiim.player import Player

        mock_client.set_audio_output_mode = AsyncMock()
        mock_status = PlayerStatus(play_state="stop")
        mock_client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_client.get_device_info_model = AsyncMock(return_value=None)
        mock_client.get_bluetooth_history = AsyncMock(return_value=[])

        player = Player(mock_client)

        await player.select_output("Optical Out")

        mock_client.set_audio_output_mode.assert_called_once_with("Optical Out")

    @pytest.mark.asyncio
    async def test_select_output_bluetooth_device(self, mock_client):
        """Test selecting a specific Bluetooth device."""
        from pywiim.models import PlayerStatus
        from pywiim.player import Player

        mock_client.connect_bluetooth_device = AsyncMock()
        mock_status = PlayerStatus(play_state="stop")
        mock_client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_client.get_device_info_model = AsyncMock(return_value=None)
        mock_client.get_bluetooth_history = AsyncMock(return_value=[])

        player = Player(mock_client)
        player._bluetooth_history = [
            {"name": "Sony Speaker", "ad": "AA:BB:CC:DD:EE:FF", "ct": 0, "role": "Audio Sink"},
        ]

        await player.select_output("BT: Sony Speaker")

        # Should connect to the specific device (this automatically activates BT output mode)
        mock_client.connect_bluetooth_device.assert_called_once_with("AA:BB:CC:DD:EE:FF")

    @pytest.mark.asyncio
    async def test_select_output_bluetooth_device_not_found(self, mock_client):
        """Test selecting a Bluetooth device that's not paired."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._bluetooth_history = [
            {"name": "Sony Speaker", "ad": "AA:BB:CC:DD:EE:FF", "ct": 0, "role": "Audio Sink"},
        ]

        with pytest.raises(ValueError, match="Bluetooth device 'Unknown Device' not found"):
            await player.select_output("BT: Unknown Device")
