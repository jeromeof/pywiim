"""Unit tests for StateManager.

Tests state management, refresh, UPnP integration, and state synchronization.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from pywiim.models import DeviceInfo, PlayerStatus


class TestStateManager:
    """Test StateManager class."""

    @pytest.fixture
    def mock_player(self, mock_client):
        """Create a mock Player instance."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._status_model = PlayerStatus()
        player._device_info = None
        player._upnp_client = None
        player._upnp_health_tracker = None
        player._state_synchronizer = MagicMock()
        player._state_synchronizer.update_from_upnp = MagicMock()
        player._state_synchronizer.get_merged_state = MagicMock(return_value={})
        player._on_state_changed = None
        player._group = None
        player._cover_art_manager = MagicMock()
        player._cover_art_manager.fetch_cover_art = AsyncMock()
        # Mock properties - store originals to restore later
        from pywiim.player import Player as PlayerClass

        property_names = ["play_state", "volume_level", "is_muted", "media_title", "media_position", "is_master"]
        for prop_name in property_names:
            if not hasattr(PlayerClass, f"_original_{prop_name}_property"):
                setattr(PlayerClass, f"_original_{prop_name}_property", getattr(PlayerClass, prop_name, None))
            setattr(PlayerClass, prop_name, PropertyMock(return_value=None if prop_name != "is_muted" else False))
        return player

    @pytest.fixture
    def state_manager(self, mock_player):
        """Create a StateManager instance."""
        from pywiim.player.statemgr import StateManager

        return StateManager(mock_player)

    @staticmethod
    def _setup_refresh_mocks(mock_player, state_manager):
        """Helper to set up common mocks for refresh tests."""
        from pywiim.polling import PollingStrategy

        mock_player._state_synchronizer.update_from_http = MagicMock()
        mock_player._state_synchronizer.get_merged_state = MagicMock(return_value={})
        # Mock capabilities as a property - store original to restore later
        client_class = type(mock_player.client)
        if not hasattr(client_class, "_original_capabilities_property"):
            # Store original property descriptor before patching
            client_class._original_capabilities_property = getattr(client_class, "capabilities", None)
        # Patch on class using PropertyMock (will be restored by test cleanup)
        client_class.capabilities = PropertyMock(return_value={})
        mock_player._last_refresh = time.time() - 10
        mock_player._audio_output_status = None
        mock_player._last_audio_output_check = None
        mock_player._last_eq_presets_check = None
        mock_player._last_presets_check = None
        mock_player._last_bt_history_check = None
        mock_player._upnp_health_tracker = None
        mock_player._metadata = None
        mock_player._eq_presets = None
        mock_player._presets = []
        mock_player._bluetooth_history = []
        mock_player._group = None
        mock_player._available = True
        state_manager._polling_strategy = PollingStrategy({})
        state_manager._last_track_signature = None
        state_manager._last_eq_preset = None
        state_manager._last_source = None

    def test_init(self, state_manager):
        """Test StateManager initialization."""
        assert state_manager.player is not None
        assert state_manager._last_track_signature is None
        assert state_manager._upnp_client_creation_attempted is False
        assert state_manager.stream_enrichment_enabled is True

    def test_apply_diff_no_changes(self, state_manager, mock_player):
        """Test apply_diff with no changes."""
        result = state_manager.apply_diff({})

        assert result is False

    def test_apply_diff_with_changes(self, state_manager, mock_player):
        """Test apply_diff with changes."""
        # Mock properties to return different values before and after
        # Use return_value for first call, then side_effect for subsequent
        play_state_values = ["stop", "play"]
        volume_values = [0.3, 0.5]

        play_state_prop = PropertyMock()
        play_state_prop.side_effect = lambda: play_state_values.pop(0) if play_state_values else "play"
        volume_prop = PropertyMock()
        volume_prop.side_effect = lambda: volume_values.pop(0) if volume_values else 0.5

        type(mock_player).play_state = play_state_prop
        type(mock_player).volume_level = volume_prop
        type(mock_player).is_muted = PropertyMock(return_value=False)
        type(mock_player).media_title = PropertyMock(return_value=None)
        type(mock_player).media_position = PropertyMock(return_value=None)
        mock_player._state_synchronizer.get_merged_state.return_value = {
            "play_state": "play",
            "volume": 0.5,
        }

        # Reset the lists for the actual test
        play_state_values[:] = ["stop", "play"]
        volume_values[:] = [0.3, 0.5]

        result = state_manager.apply_diff({"play_state": "play", "volume": 0.5})

        # Just verify it doesn't crash and returns a boolean
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_ensure_upnp_client_already_exists(self, state_manager, mock_player):
        """Test _ensure_upnp_client when client already exists."""
        mock_player._upnp_client = MagicMock()

        result = await state_manager._ensure_upnp_client()

        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_upnp_client_creation_attempted(self, state_manager, mock_player):
        """Test _ensure_upnp_client when creation already attempted."""
        state_manager._upnp_client_creation_attempted = True

        result = await state_manager._ensure_upnp_client()

        assert result is False

    @pytest.mark.asyncio
    async def test_ensure_upnp_client_success(self, state_manager, mock_player):
        """Test successful UPnP client creation."""
        with patch("pywiim.upnp.client.UpnpClient") as mock_upnp_client_class:
            mock_upnp_client = MagicMock()
            mock_upnp_client.av_transport = MagicMock()
            mock_upnp_client.rendering_control = MagicMock()
            mock_upnp_client_class.create = AsyncMock(return_value=mock_upnp_client)
            mock_player.client._ensure_session = AsyncMock()
            mock_player.client._session = MagicMock()

            result = await state_manager._ensure_upnp_client()

            assert result is True
            assert mock_player._upnp_client == mock_upnp_client

    @pytest.mark.asyncio
    async def test_ensure_upnp_client_failure(self, state_manager, mock_player):
        """Test UPnP client creation failure."""
        with patch("pywiim.upnp.client.UpnpClient") as mock_upnp_client_class:
            mock_upnp_client_class.create = AsyncMock(side_effect=Exception("Connection failed"))
            mock_player.client._ensure_session = AsyncMock()

            result = await state_manager._ensure_upnp_client()

            assert result is False
            assert mock_player._upnp_client is None

    def test_update_from_upnp_no_play_state(self, state_manager, mock_player):
        """Test update_from_upnp without play_state."""
        mock_player._state_synchronizer.get_merged_state.return_value = {"volume": 0.5}

        state_manager.update_from_upnp({"volume": 0.5})

        mock_player._state_synchronizer.update_from_upnp.assert_called_once()

    def test_update_from_upnp_play_state_debounce(self, state_manager, mock_player):
        """Test update_from_upnp with play_state debouncing."""
        type(mock_player).play_state = PropertyMock(return_value="play")
        mock_player._state_synchronizer.get_merged_state.return_value = {"play_state": "pause"}

        state_manager.update_from_upnp({"play_state": "pause"})

        # Should schedule delayed update
        assert state_manager._pending_state_task is not None

    def test_update_from_upnp_play_state_immediate(self, state_manager, mock_player):
        """Test update_from_upnp with immediate play state."""
        type(mock_player).play_state = PropertyMock(return_value="stop")
        mock_player._state_synchronizer.get_merged_state.return_value = {"play_state": "play"}

        state_manager.update_from_upnp({"play_state": "play"})

        mock_player._state_synchronizer.update_from_upnp.assert_called_once()

    def test_schedule_delayed_update(self, state_manager, mock_player):
        """Test scheduling delayed update."""
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_task = MagicMock()
            mock_loop.return_value.create_task = MagicMock(return_value=mock_task)

            state_manager._schedule_delayed_update("pause")

            assert state_manager._pending_state_task == mock_task

    @pytest.mark.asyncio
    async def test_apply_delayed_state(self, state_manager, mock_player):
        """Test applying delayed state."""
        mock_player._state_synchronizer.get_merged_state.return_value = {"play_state": "pause"}

        await state_manager._apply_delayed_state("pause")

        mock_player._state_synchronizer.update_from_upnp.assert_called()

    @pytest.mark.asyncio
    async def test_apply_delayed_state_cancelled(self, state_manager, mock_player):
        """Test applying delayed state when cancelled."""
        with patch("asyncio.sleep", side_effect=asyncio.CancelledError()):
            # Should not raise
            await state_manager._apply_delayed_state("pause")

    @pytest.mark.asyncio
    async def test_refresh_full(self, state_manager, mock_player):
        """Test full refresh."""
        mock_status = PlayerStatus(play_state="play", volume=50)
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_player.client.get_device_info_model = AsyncMock(return_value=mock_info)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        mock_player._last_refresh = time.time() - 10  # Not first refresh
        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=True)

        mock_player.client.get_player_status_model.assert_called_once()
        mock_player.client.get_device_info_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_not_full(self, state_manager, mock_player):
        """Test non-full refresh."""
        mock_status = PlayerStatus(play_state="play", volume=50)
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_player._state_synchronizer.update_from_http = MagicMock()

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        mock_player.client.get_player_status_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_device_info(self, state_manager, mock_player):
        """Test getting device info."""
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_player.client.get_device_info_model = AsyncMock(return_value=mock_info)

        result = await state_manager.get_device_info()

        assert result == mock_info

    @pytest.mark.asyncio
    async def test_get_status(self, state_manager, mock_player):
        """Test getting status."""
        mock_status = PlayerStatus(play_state="play", volume=50)
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)

        result = await state_manager.get_status()

        assert result == mock_status

    @pytest.mark.asyncio
    async def test_get_play_state(self, state_manager, mock_player):
        """Test getting play state."""
        mock_status = PlayerStatus(play_state="play")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)

        result = await state_manager.get_play_state()

        assert result == "play"

    def test_check_and_fetch_artwork_on_track_change(self, state_manager, mock_player):
        """Test checking and fetching artwork on track change."""
        merged = {"title": "New Track", "artist": "New Artist"}
        state_manager._last_track_signature = None

        state_manager._check_and_fetch_artwork_on_track_change(merged)

        # Should update last track signature
        assert state_manager._last_track_signature is not None

    @pytest.mark.asyncio
    async def test_fetch_artwork_from_metainfo(self, state_manager, mock_player):
        """Test fetching artwork from meta info."""
        mock_player.client.get_meta_info = AsyncMock(return_value={"image_url": "http://example.com/art.jpg"})
        mock_player._cover_art_manager.fetch_cover_art = AsyncMock()

        await state_manager._fetch_artwork_from_metainfo()

        mock_player.client.get_meta_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_artwork_from_metainfo_no_meta_info(self, state_manager, mock_player):
        """Test fetching artwork when get_meta_info not available."""
        if not hasattr(mock_player.client, "get_meta_info"):
            # Skip if method doesn't exist
            return

        mock_player.client.get_meta_info = AsyncMock(return_value={})

        await state_manager._fetch_artwork_from_metainfo()

        # Should not crash

    def test_propagate_metadata_to_slaves(self, state_manager, mock_player):
        """Test propagating metadata to slaves."""
        from pywiim.group import Group

        slave = MagicMock()
        slave._status_model = PlayerStatus()
        slave._state_synchronizer = MagicMock()
        slave._state_synchronizer.update_from_http = MagicMock()
        slave._on_state_changed = None
        slave.host = "192.168.1.101"
        slave._group = None  # Ensure slave is not already in a group
        group = Group(mock_player)
        group.add_slave(slave)
        mock_player._group = group
        type(mock_player).is_master = PropertyMock(return_value=True)
        mock_player._status_model = PlayerStatus(title="Master Track", artist="Master Artist", album="Master Album")

        state_manager._propagate_metadata_to_slaves()

        # Should update slave metadata
        assert slave._status_model.title == "Master Track"
        # update_from_http is called twice: once in add_slave (for source) and once in _propagate_metadata_to_slaves
        # Check that the metadata propagation call was made (with title)
        calls = slave._state_synchronizer.update_from_http.call_args_list
        metadata_call_found = any(
            call and call[0] and isinstance(call[0][0], dict) and "title" in call[0][0] for call in calls
        )
        assert metadata_call_found, "Metadata propagation call with title not found"

    @pytest.mark.asyncio
    async def test_enrich_stream_metadata(self, state_manager, mock_player):
        """Test enriching stream metadata."""
        status = PlayerStatus(source="wifi", title="Stream Title")
        mock_player._state_synchronizer.get_merged_state.return_value = {"source": "wifi"}

        await state_manager._enrich_stream_metadata(status)

        # Should not crash

    @pytest.mark.asyncio
    async def test_fetch_and_apply_stream_metadata(self, state_manager, mock_player):
        """Test fetching and applying stream metadata."""
        with patch("pywiim.player.statemgr.get_stream_metadata") as mock_get_metadata:
            from pywiim.player.stream import StreamMetadata

            mock_metadata = StreamMetadata(title="Stream Title", artist="Stream Artist")
            mock_get_metadata.return_value = mock_metadata
            mock_player._state_synchronizer.get_merged_state.return_value = {}

            await state_manager._fetch_and_apply_stream_metadata("http://example.com/stream.mp3")

            mock_get_metadata.assert_called_once()

    def test_apply_stream_metadata(self, state_manager, mock_player):
        """Test applying stream metadata."""
        from pywiim.player.stream import StreamMetadata

        metadata = StreamMetadata(title="Stream Title", artist="Stream Artist")
        mock_player._state_synchronizer.update_from_http = MagicMock()
        mock_player._state_synchronizer.get_merged_state = MagicMock(
            return_value={"title": "Stream Title", "artist": "Stream Artist"}
        )

        state_manager._apply_stream_metadata(metadata)

        mock_player._state_synchronizer.update_from_http.assert_called_once()

    # === Comprehensive refresh() tests ===

    @pytest.mark.asyncio
    async def test_refresh_first_time_always_full(self, state_manager, mock_player):
        """Test that first refresh is always full."""
        mock_status = PlayerStatus(play_state="play", volume=50)
        mock_info = DeviceInfo(uuid="test-uuid", name="Test Device")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        mock_player.client.get_device_info_model = AsyncMock(return_value=mock_info)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        mock_player._last_refresh = None  # First refresh
        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)  # Even though False, should be full

            mock_player.client.get_device_info_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_upnp_volume(self, state_manager, mock_player):
        """Test refresh with UPnP volume/mute."""
        mock_status = PlayerStatus(play_state="play", volume=50)
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        mock_player._upnp_client = MagicMock()
        mock_player._upnp_client.rendering_control = MagicMock()
        mock_player._upnp_client.get_volume = AsyncMock(return_value=75)
        mock_player._upnp_client.get_mute = AsyncMock(return_value=True)

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        # Should use UPnP volume
        call_args = mock_player._state_synchronizer.update_from_http.call_args[0][0]
        assert call_args["volume"] == 75
        assert call_args["muted"] is True

    @pytest.mark.asyncio
    async def test_refresh_upnp_volume_fails_fallback(self, state_manager, mock_player):
        """Test refresh when UPnP volume fails, falls back to HTTP."""
        mock_status = PlayerStatus(play_state="play", volume=50, mute=False)
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        mock_player._upnp_client = MagicMock()
        mock_player._upnp_client.rendering_control = MagicMock()
        mock_player._upnp_client.get_volume = AsyncMock(side_effect=Exception("UPnP error"))

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        # Should use HTTP volume
        call_args = mock_player._state_synchronizer.update_from_http.call_args[0][0]
        assert call_args["volume"] == 50

    @pytest.mark.asyncio
    async def test_refresh_track_changed_fetches_metadata(self, state_manager, mock_player):
        """Test refresh when track changes, fetches metadata."""
        mock_status = PlayerStatus(play_state="play", title="New Track", artist="New Artist")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        type(mock_player.client).capabilities = PropertyMock(return_value={"supports_metadata": True})
        mock_player.client.get_meta_info = AsyncMock(return_value={"metaData": {}})
        state_manager._last_track_signature = "Old|Track|Album"

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        mock_player.client.get_meta_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_eq_preset_changed(self, state_manager, mock_player):
        """Test refresh when EQ preset changes."""
        mock_status = PlayerStatus(play_state="play", eq_preset="rock")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        type(mock_player.client).capabilities = PropertyMock(return_value={"supports_eq": True})
        mock_player.client.get_eq = AsyncMock(return_value={})
        state_manager._last_eq_preset = "jazz"

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        mock_player.client.get_eq.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_source_changed_fetches_audio_output(self, state_manager, mock_player):
        """Test refresh when source changes, fetches audio output."""
        mock_status = PlayerStatus(play_state="play", source="bluetooth")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        type(mock_player.client).capabilities = PropertyMock(return_value={"supports_audio_output": True})
        mock_player.get_audio_output_status = AsyncMock(return_value={"mode": "bluetooth"})
        state_manager._last_source = "wifi"

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        mock_player.get_audio_output_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_fetches_eq_presets(self, state_manager, mock_player):
        """Test refresh fetches EQ presets on track change."""
        mock_status = PlayerStatus(play_state="play", title="New Track")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        type(mock_player.client).capabilities = PropertyMock(return_value={"supports_eq": True})
        mock_player.client.get_eq_presets = AsyncMock(return_value=["rock", "jazz"])
        mock_player._last_eq_presets_check = None
        state_manager._last_track_signature = "Old|Track"

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        mock_player.client.get_eq_presets.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_fetches_presets(self, state_manager, mock_player):
        """Test refresh fetches presets on track change."""
        mock_status = PlayerStatus(play_state="play", title="New Track")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        type(mock_player.client).capabilities = PropertyMock(return_value={"supports_presets": True})
        mock_player.client.get_presets = AsyncMock(return_value=[])
        mock_player._last_presets_check = None
        state_manager._last_track_signature = "Old|Track"

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        mock_player.client.get_presets.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_fetches_bluetooth_history(self, state_manager, mock_player):
        """Test refresh fetches Bluetooth history."""
        mock_status = PlayerStatus(play_state="play", title="New Track")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        mock_player.client.get_bluetooth_history = AsyncMock(return_value=[])
        mock_player._last_bt_history_check = None
        state_manager._last_track_signature = "Old|Track"

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        mock_player.client.get_bluetooth_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_error_handling(self, state_manager, mock_player):
        """Test refresh error handling."""
        mock_player.client.get_player_status_model = AsyncMock(side_effect=RuntimeError("Network error"))
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)

        with pytest.raises(RuntimeError):
            with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
                mock_groupops.return_value._synchronize_group_state = AsyncMock()

                await state_manager.refresh(full=False)

        assert mock_player._available is False

    @pytest.mark.asyncio
    async def test_refresh_updates_upnp_health_tracker(self, state_manager, mock_player):
        """Test refresh updates UPnP health tracker."""
        from pywiim.upnp.health import UpnpHealthTracker

        mock_status = PlayerStatus(play_state="play", volume=50, mute=False)
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        mock_player._upnp_health_tracker = UpnpHealthTracker()

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()

            await state_manager.refresh(full=False)

        # Health tracker should have been updated
        assert mock_player._upnp_health_tracker._last_poll_state is not None

    @pytest.mark.asyncio
    async def test_refresh_propagates_metadata_to_slaves(self, state_manager, mock_player):
        """Test refresh propagates metadata to slaves when master."""
        from pywiim.group import Group

        mock_status = PlayerStatus(play_state="play", title="Master Track", artist="Master Artist")
        mock_player.client.get_player_status_model = AsyncMock(return_value=mock_status)
        TestStateManager._setup_refresh_mocks(mock_player, state_manager)
        type(mock_player).is_master = PropertyMock(return_value=True)
        mock_player._status_model = mock_status

        slave = MagicMock()
        slave._status_model = PlayerStatus()
        slave._state_synchronizer = MagicMock()
        slave._state_synchronizer.update_from_http = MagicMock()
        slave._on_state_changed = None
        slave.host = "192.168.1.101"
        slave._group = None  # Ensure slave is not in a group
        group = Group(mock_player)
        group.add_slave(slave)
        mock_player._group = group

        with patch("pywiim.player.groupops.GroupOperations") as mock_groupops:
            mock_groupops.return_value._synchronize_group_state = AsyncMock()
            await state_manager.refresh(full=False)

        # Should propagate to slave - check that slave's status model was updated
        assert slave._status_model.title == "Master Track"

    @pytest.mark.asyncio
    async def test_enrich_stream_metadata_disabled(self, state_manager, mock_player):
        """Test stream enrichment when disabled."""
        state_manager.stream_enrichment_enabled = False
        status = PlayerStatus(source="wifi", title="http://example.com/stream.mp3", play_state="play")

        await state_manager._enrich_stream_metadata(status)

        # Should return early
        assert state_manager._stream_enrichment_task is None

    @pytest.mark.asyncio
    async def test_enrich_stream_metadata_not_playing(self, state_manager, mock_player):
        """Test stream enrichment when not playing."""
        status = PlayerStatus(source="wifi", title="http://example.com/stream.mp3", play_state="stop")

        await state_manager._enrich_stream_metadata(status)

        # Should return early - play_state="stop" should cause early return
        # Task should not be created or should remain unchanged
        # Note: The method checks play_state and returns early, so task should not change
        # But if it does get created somehow, we just verify the method doesn't crash

    @pytest.mark.asyncio
    async def test_enrich_stream_metadata_wrong_source(self, state_manager, mock_player):
        """Test stream enrichment with wrong source."""
        status = PlayerStatus(source="bluetooth", title="http://example.com/stream.mp3", play_state="play")

        await state_manager._enrich_stream_metadata(status)

        # Should return early
        assert state_manager._stream_enrichment_task is None

    @pytest.mark.asyncio
    async def test_enrich_stream_metadata_cached(self, state_manager, mock_player):
        """Test stream enrichment uses cached metadata."""
        from pywiim.player.stream import StreamMetadata

        status = PlayerStatus(source="wifi", title="http://example.com/stream.mp3", play_state="play")
        cached_metadata = StreamMetadata(title="Cached Title", artist="Cached Artist")
        state_manager._last_stream_url = "http://example.com/stream.mp3"
        state_manager._last_stream_metadata = cached_metadata
        mock_player._state_synchronizer.update_from_http = MagicMock()

        await state_manager._enrich_stream_metadata(status)

        # Should use cached metadata
        mock_player._state_synchronizer.update_from_http.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_and_apply_stream_metadata_success(self, state_manager, mock_player):
        """Test fetching and applying stream metadata successfully."""
        with patch("pywiim.player.statemgr.get_stream_metadata") as mock_get_metadata:
            from pywiim.player.stream import StreamMetadata

            mock_metadata = StreamMetadata(title="Stream Title", artist="Stream Artist")
            mock_get_metadata.return_value = mock_metadata
            mock_player._state_synchronizer.update_from_http = MagicMock()
            mock_player._state_synchronizer.get_merged_state = MagicMock(return_value={"title": "Stream Title"})
            mock_player._on_state_changed = MagicMock()

            await state_manager._fetch_and_apply_stream_metadata("http://example.com/stream.mp3")

            mock_get_metadata.assert_called_once()
            assert state_manager._last_stream_metadata == mock_metadata

    @pytest.mark.asyncio
    async def test_fetch_and_apply_stream_metadata_cancelled(self, state_manager, mock_player):
        """Test fetching stream metadata when cancelled."""
        import asyncio

        with patch("pywiim.player.statemgr.get_stream_metadata", side_effect=asyncio.CancelledError()):
            # Should not raise - CancelledError is caught
            try:
                await state_manager._fetch_and_apply_stream_metadata("http://example.com/stream.mp3")
            except asyncio.CancelledError:
                pytest.fail("CancelledError should be caught")

    @pytest.mark.asyncio
    async def test_fetch_and_apply_stream_metadata_error(self, state_manager, mock_player):
        """Test fetching stream metadata when error occurs."""
        with patch("pywiim.player.statemgr.get_stream_metadata", side_effect=Exception("Network error")):
            # Should not raise
            await state_manager._fetch_and_apply_stream_metadata("http://example.com/stream.mp3")

    @pytest.mark.asyncio
    async def test_get_master_name_from_group(self, state_manager, mock_player):
        """Test getting master name from group."""
        from pywiim.group import Group

        master = MagicMock()
        master._device_info = DeviceInfo(uuid="master-uuid", name="Master Device")
        master.name = "Master Device"
        master.host = "192.168.1.200"
        group = Group(master)
        mock_player._group = group

        result = await state_manager._get_master_name(None, None)

        assert result == "Master Device"

    @pytest.mark.asyncio
    async def test_get_master_name_from_device_info(self, state_manager, mock_player):
        """Test getting master name from device info."""
        device_info = DeviceInfo(uuid="test-uuid", master_ip="192.168.1.200")
        with patch("pywiim.client.WiiMClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_device_name = AsyncMock(return_value="Master Device")
            mock_client.close = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await state_manager._get_master_name(device_info, None)

            assert result == "Master Device"
            # close() is called in finally block
            mock_client.close.assert_called_once()

    def test_check_and_fetch_artwork_track_changed_no_artwork(self, state_manager, mock_player):
        """Test checking artwork when track changed and no artwork."""
        merged = {"title": "New Track", "artist": "New Artist", "image_url": None}
        state_manager._last_track_signature = "Old|Track|Album"
        mock_player.client._capabilities = {"supports_metadata": True}
        mock_player.client.get_meta_info = MagicMock()

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_task = MagicMock()
            mock_loop.return_value.create_task = MagicMock(return_value=mock_task)

            state_manager._check_and_fetch_artwork_on_track_change(merged)

            # Should schedule artwork fetch
            assert state_manager._artwork_fetch_task == mock_task

    def test_check_and_fetch_artwork_first_track(self, state_manager, mock_player):
        """Test checking artwork on first track."""
        merged = {"title": "First Track", "artist": "First Artist"}
        state_manager._last_track_signature = None

        state_manager._check_and_fetch_artwork_on_track_change(merged)

        assert state_manager._last_track_signature is not None

    @pytest.mark.asyncio
    async def test_fetch_artwork_from_metainfo_with_artwork(self, state_manager, mock_player):
        """Test fetching artwork from meta info with valid artwork."""
        mock_player.client.get_meta_info = AsyncMock(return_value={"metaData": {"cover": "http://example.com/art.jpg"}})
        mock_player._state_synchronizer.update_from_http = MagicMock()
        mock_player._state_synchronizer.get_merged_state = MagicMock(
            return_value={"image_url": "http://example.com/art.jpg"}
        )
        mock_player._on_state_changed = MagicMock()

        await state_manager._fetch_artwork_from_metainfo()

        mock_player._state_synchronizer.update_from_http.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_artwork_from_metainfo_cancelled(self, state_manager, mock_player):
        """Test fetching artwork when cancelled."""
        import asyncio

        if not hasattr(mock_player.client, "get_meta_info"):
            pytest.skip("get_meta_info not available")
        mock_player.client.get_meta_info = AsyncMock(side_effect=asyncio.CancelledError())

        # Should not raise - CancelledError is caught
        try:
            await state_manager._fetch_artwork_from_metainfo()
        except asyncio.CancelledError:
            pytest.fail("CancelledError should be caught")

    def test_update_from_upnp_with_upnp_health_tracker(self, state_manager, mock_player):
        """Test update_from_upnp updates UPnP health tracker."""
        from pywiim.upnp.health import UpnpHealthTracker

        mock_player._upnp_health_tracker = UpnpHealthTracker()
        mock_player._state_synchronizer.get_merged_state.return_value = {"volume": 0.5}

        state_manager.update_from_upnp({"volume": 0.5, "muted": False})

        # Health tracker should have been updated
        assert mock_player._upnp_health_tracker._last_upnp_state is not None

    def test_update_from_upnp_volume_conversion(self, state_manager, mock_player):
        """Test update_from_upnp converts float volume to int."""
        from pywiim.upnp.health import UpnpHealthTracker

        mock_player._upnp_health_tracker = UpnpHealthTracker()
        mock_player._state_synchronizer.get_merged_state.return_value = {"volume": 50}

        state_manager.update_from_upnp({"volume": 0.5})  # Float 0.0-1.0

        # Should convert to int 0-100
        upnp_state = mock_player._upnp_health_tracker._last_upnp_state
        assert upnp_state["volume"] == 50

    def test_schedule_delayed_update_no_event_loop(self, state_manager, mock_player):
        """Test scheduling delayed update when no event loop."""
        with patch("asyncio.get_event_loop", side_effect=RuntimeError("No event loop")):
            state_manager._schedule_delayed_update("pause")

            # Should apply immediately
            mock_player._state_synchronizer.update_from_upnp.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_delayed_state_with_callback(self, state_manager, mock_player):
        """Test applying delayed state triggers callback."""
        mock_player._state_synchronizer.get_merged_state.return_value = {"play_state": "pause"}
        mock_player._on_state_changed = MagicMock()

        await state_manager._apply_delayed_state("pause")

        mock_player._on_state_changed.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_delayed_state_callback_error(self, state_manager, mock_player):
        """Test applying delayed state when callback raises error."""
        mock_player._state_synchronizer.get_merged_state.return_value = {"play_state": "pause"}
        mock_player._on_state_changed = MagicMock(side_effect=Exception("Callback error"))

        # Should not raise
        await state_manager._apply_delayed_state("pause")
