"""Unit tests for state synchronization.

Tests StateSynchronizer and GroupStateSynchronizer for merging HTTP and UPnP data.
"""

from __future__ import annotations

import time

import pytest

from pywiim.state import (
    StateSynchronizer,
    SynchronizedState,
    TimestampedField,
    normalize_play_state,
)


class TestNormalizePlayState:
    """Test play state normalization."""

    def test_normalize_play_state_standard(self):
        """Test normalizing standard play states."""
        assert normalize_play_state("play") == "play"
        assert normalize_play_state("pause") == "pause"
        assert normalize_play_state("stop") == "pause"  # Modern UX: stop maps to pause

    def test_normalize_play_state_variations(self):
        """Test normalizing play state variations."""
        assert normalize_play_state("playing") == "play"
        assert normalize_play_state("paused") == "pause"
        assert normalize_play_state("stopped") == "pause"  # Modern UX: stopped maps to pause
        assert normalize_play_state("idle") == "idle"

    def test_normalize_play_state_upnp(self):
        """Test normalizing UPnP play states."""
        assert normalize_play_state("PAUSED_PLAYBACK") == "pause"
        assert normalize_play_state("NO_MEDIA_PRESENT") == "idle"

    def test_normalize_play_state_none(self):
        """Test normalizing None play state."""
        assert normalize_play_state(None) is None

    def test_normalize_play_state_unknown(self):
        """Test normalizing unknown play state."""
        result = normalize_play_state("unknown_state")
        assert result is not None  # Returns normalized lowercase


class TestTimestampedField:
    """Test TimestampedField dataclass."""

    def test_timestamped_field_creation(self):
        """Test creating TimestampedField."""
        field = TimestampedField(value="test", source="http", timestamp=1000.0)

        assert field.value == "test"
        assert field.source == "http"
        assert field.timestamp == 1000.0
        assert field.confidence == 1.0

    def test_is_fresh(self):
        """Test checking if field is fresh."""
        now = time.time()
        field = TimestampedField(value="test", source="http", timestamp=now - 1.0)

        assert field.is_fresh("play_state", now) is True  # 1s < 5s window

    def test_is_stale(self):
        """Test checking if field is stale."""
        now = time.time()
        field = TimestampedField(value="test", source="http", timestamp=now - 10.0)

        assert field.is_fresh("play_state", now) is False  # 10s > 5s window

    def test_age(self):
        """Test getting field age."""
        now = time.time()
        field = TimestampedField(value="test", source="http", timestamp=now - 5.0)

        assert abs(field.age(now) - 5.0) < 0.1


class TestStateSynchronizer:
    """Test StateSynchronizer class."""

    def test_init(self):
        """Test StateSynchronizer initialization."""
        sync = StateSynchronizer()

        assert sync._http_state == {}
        assert sync._upnp_state == {}
        assert sync._merged_state is not None

    def test_update_from_http(self):
        """Test updating from HTTP data."""
        sync = StateSynchronizer()

        http_data = {
            "play_state": "play",
            "volume": 50,
            "muted": False,
            "title": "Test Song",
            "position": 120,
        }

        sync.update_from_http(http_data)

        assert "play_state" in sync._http_state
        assert sync._http_state["play_state"].value == "play"
        assert sync._merged_state.http_last_update is not None

    def test_update_from_upnp(self):
        """Test updating from UPnP data."""
        sync = StateSynchronizer()

        upnp_data = {
            "play_state": "playing",
            "volume": 0.75,
            "muted": False,
        }

        sync.update_from_upnp(upnp_data)

        assert "play_state" in sync._upnp_state
        assert sync._upnp_state["play_state"].value == "play"  # Normalized
        assert sync._merged_state.upnp_last_update is not None

    def test_merge_state_http_only(self):
        """Test merging state when only HTTP data available."""
        sync = StateSynchronizer()

        sync.update_from_http({"play_state": "play", "volume": 50})
        merged = sync.get_merged_state()

        assert merged["play_state"] == "play"
        assert merged["volume"] == 50

    def test_merge_state_upnp_only(self):
        """Test merging state when only UPnP data available."""
        sync = StateSynchronizer()

        sync.update_from_upnp({"play_state": "playing", "volume": 0.75})
        merged = sync.get_merged_state()

        assert merged["play_state"] == "play"  # Normalized
        assert merged["volume"] == 0.75

    def test_merge_state_conflict_fresh_upnp(self):
        """Test merging when both sources present, UPnP is fresh."""
        sync = StateSynchronizer()

        now = time.time()
        # HTTP data is stale
        sync.update_from_http({"play_state": "pause"}, timestamp=now - 10.0)
        # UPnP data is fresh
        sync.update_from_upnp({"play_state": "play"}, timestamp=now)

        merged = sync.get_merged_state()

        # Should prefer fresh UPnP
        assert merged["play_state"] == "play"

    def test_merge_state_conflict_priority(self):
        """Test merging using source priority."""
        sync = StateSynchronizer()

        now = time.time()
        # Both fresh, use priority
        sync.update_from_http({"play_state": "pause"}, timestamp=now)
        sync.update_from_upnp({"play_state": "play"}, timestamp=now)

        merged = sync.get_merged_state()

        # play_state priority is ["upnp", "http"], so should use UPnP
        assert merged["play_state"] == "play"

    def test_merge_state_metadata_priority(self):
        """Test merging metadata - UPnP preferred when both fresh (fires on track changes)."""
        sync = StateSynchronizer()

        now = time.time()
        # Set play state first so metadata is preserved
        sync.update_from_http({"play_state": "play", "title": "HTTP Title"}, timestamp=now)
        sync.update_from_upnp({"play_state": "play", "title": "UPnP Title"}, timestamp=now)

        merged = sync.get_merged_state()

        # Metadata: prefer UPnP when both fresh (UPnP fires immediately on track changes)
        # HTTP may have stale metadata (e.g., Spotify only sends metadata via UPnP)
        assert merged["title"] == "UPnP Title"

    def test_get_merged_state(self):
        """Test getting merged state as dictionary."""
        sync = StateSynchronizer()

        sync.update_from_http({"play_state": "play", "volume": 50})
        merged = sync.get_merged_state()

        assert isinstance(merged, dict)
        assert "play_state" in merged
        assert "_source_health" in merged
        assert merged["_source_health"]["http_available"] is True

    def test_get_state_object(self):
        """Test getting merged state object."""
        sync = StateSynchronizer()

        sync.update_from_http({"play_state": "play"})
        state_obj = sync.get_state_object()

        assert isinstance(state_obj, SynchronizedState)
        assert state_obj.play_state is not None
        assert state_obj.play_state.value == "play"


class TestGroupStateSynchronizer:
    """Test GroupStateSynchronizer class."""

    def test_init(self):
        """Test GroupStateSynchronizer initialization."""
        from pywiim.state import GroupStateSynchronizer

        sync = GroupStateSynchronizer()

        assert sync._master_state is None
        assert sync._slave_states == {}
        assert sync._last_update == 0.0

    def test_update_master_state(self):
        """Test updating master state."""
        from pywiim.state import GroupStateSynchronizer, SynchronizedState

        sync = GroupStateSynchronizer()
        master_state = SynchronizedState()
        master_state.play_state = TimestampedField(value="play", source="http", timestamp=time.time())

        sync.update_master_state(master_state)

        assert sync._master_state == master_state
        assert sync._last_update > 0

    def test_update_slave_state(self):
        """Test updating slave state."""
        from pywiim.state import GroupStateSynchronizer, SynchronizedState

        sync = GroupStateSynchronizer()
        slave_state = SynchronizedState()
        slave_state.volume = TimestampedField(value=0.5, source="http", timestamp=time.time())

        sync.update_slave_state("192.168.1.101", slave_state)

        assert "192.168.1.101" in sync._slave_states
        assert sync._slave_states["192.168.1.101"] == slave_state

    def test_remove_slave(self):
        """Test removing slave state."""
        from pywiim.state import GroupStateSynchronizer, SynchronizedState

        sync = GroupStateSynchronizer()
        slave_state = SynchronizedState()
        sync.update_slave_state("192.168.1.101", slave_state)

        sync.remove_slave("192.168.1.101")

        assert "192.168.1.101" not in sync._slave_states

    def test_clear(self):
        """Test clearing all state."""
        from pywiim.state import GroupStateSynchronizer, SynchronizedState

        sync = GroupStateSynchronizer()
        master_state = SynchronizedState()
        sync.update_master_state(master_state)
        sync.update_slave_state("192.168.1.101", SynchronizedState())

        sync.clear()

        assert sync._master_state is None
        assert len(sync._slave_states) == 0
        assert sync._last_update == 0.0

    def test_build_group_state(self):
        """Test building group state from synchronized states."""
        from pywiim.state import GroupStateSynchronizer, SynchronizedState, TimestampedField

        sync = GroupStateSynchronizer()

        # Create master state
        master_state = SynchronizedState()
        master_state.play_state = TimestampedField(value="play", source="http", timestamp=time.time())
        master_state.volume = TimestampedField(value=0.5, source="http", timestamp=time.time())
        master_state.muted = TimestampedField(value=False, source="http", timestamp=time.time())
        master_state.title = TimestampedField(value="Test Song", source="http", timestamp=time.time())
        sync.update_master_state(master_state)

        # Create slave state
        slave_state = SynchronizedState()
        slave_state.volume = TimestampedField(value=0.75, source="http", timestamp=time.time())
        slave_state.muted = TimestampedField(value=True, source="http", timestamp=time.time())
        sync.update_slave_state("192.168.1.101", slave_state)

        group_state = sync.build_group_state("192.168.1.100", ["192.168.1.101"])

        assert group_state.master_host == "192.168.1.100"
        assert group_state.slave_hosts == ["192.168.1.101"]
        assert group_state.play_state == "play"
        assert group_state.volume_level == 0.75  # Max of 0.5 and 0.75
        assert group_state.is_muted is False  # Not all muted (master=False, slave=True)

    def test_build_group_state_no_master(self):
        """Test building group state when master state not available."""
        from pywiim.state import GroupStateSynchronizer

        sync = GroupStateSynchronizer()

        with pytest.raises(ValueError, match="Master state not available"):
            sync.build_group_state("192.168.1.100", [])
