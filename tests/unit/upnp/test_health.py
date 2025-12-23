"""Unit tests for UPnP health tracking.

Tests UpnpHealthTracker class for monitoring UPnP event health.
"""

from __future__ import annotations

from pywiim.upnp.health import UpnpHealthTracker


class TestUpnpHealthTrackerInitialization:
    """Test UpnpHealthTracker initialization."""

    def test_init_defaults(self):
        """Test initialization with default parameters."""
        tracker = UpnpHealthTracker()

        assert tracker._grace_period == 2.0
        assert tracker._min_samples == 10
        assert tracker._detected_changes == 0
        assert tracker._missed_changes == 0
        assert tracker._upnp_working is True
        assert tracker.is_healthy is True

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        tracker = UpnpHealthTracker(grace_period=5.0, min_samples=5)

        assert tracker._grace_period == 5.0
        assert tracker._min_samples == 5

    def test_init_state_tracking(self):
        """Test initial state tracking."""
        tracker = UpnpHealthTracker()

        assert tracker._last_poll_state == {}
        assert tracker._last_upnp_state == {}
        assert tracker._last_upnp_event_time is None


class TestUpnpHealthTrackerProperties:
    """Test UpnpHealthTracker properties."""

    def test_is_healthy_default(self):
        """Test is_healthy property defaults to True."""
        tracker = UpnpHealthTracker()
        assert tracker.is_healthy is True

    def test_miss_rate_no_changes(self):
        """Test miss_rate with no changes detected."""
        tracker = UpnpHealthTracker()
        assert tracker.miss_rate == 0.0

    def test_miss_rate_calculation(self):
        """Test miss_rate calculation."""
        tracker = UpnpHealthTracker()
        tracker._detected_changes = 10
        tracker._missed_changes = 3

        assert tracker.miss_rate == 0.3

    def test_statistics(self):
        """Test statistics property."""
        tracker = UpnpHealthTracker()
        tracker._detected_changes = 15
        tracker._missed_changes = 3

        stats = tracker.statistics

        assert stats["detected_changes"] == 15
        assert stats["missed_changes"] == 3
        assert stats["miss_rate"] == 0.2
        assert stats["is_healthy"] is True
        assert stats["has_enough_samples"] is True

    def test_statistics_insufficient_samples(self):
        """Test statistics with insufficient samples."""
        tracker = UpnpHealthTracker()
        tracker._detected_changes = 5  # Less than min_samples (10)

        stats = tracker.statistics

        assert stats["has_enough_samples"] is False


class TestUpnpHealthTrackerOnPollUpdate:
    """Test on_poll_update method."""

    def test_first_poll(self):
        """Test first poll just records state."""
        tracker = UpnpHealthTracker()

        tracker.on_poll_update({"play_state": "play", "volume": 50})

        assert tracker._last_poll_state == {"play_state": "play", "volume": 50}
        assert tracker._detected_changes == 0

    def test_detect_change(self):
        """Test detecting changes in poll updates."""
        tracker = UpnpHealthTracker()
        tracker._last_poll_state = {"play_state": "stop", "volume": 30}

        tracker.on_poll_update({"play_state": "play", "volume": 50})

        assert tracker._detected_changes == 2  # play_state and volume changed
        assert tracker._last_poll_state == {"play_state": "play", "volume": 50}

    def test_detect_change_upnp_missed(self):
        """Test detecting change that UPnP missed."""
        tracker = UpnpHealthTracker()
        tracker._last_poll_state = {"play_state": "stop"}
        tracker._last_upnp_event_time = 0  # Old event

        tracker.on_poll_update({"play_state": "play"})

        assert tracker._detected_changes == 1
        assert tracker._missed_changes == 1  # UPnP didn't catch it

    def test_detect_change_upnp_caught(self):
        """Test detecting change that UPnP caught."""
        import time

        tracker = UpnpHealthTracker()
        tracker._last_poll_state = {"play_state": "stop"}
        tracker._last_upnp_state = {"play_state": "play"}
        tracker._last_upnp_event_time = time.time()  # Recent event

        tracker.on_poll_update({"play_state": "play"})

        assert tracker._detected_changes == 1
        assert tracker._missed_changes == 0  # UPnP caught it

    def test_ignores_non_monitored_fields(self):
        """Test that non-monitored fields are ignored."""
        tracker = UpnpHealthTracker()
        tracker._last_poll_state = {"play_state": "play", "custom_field": "old"}

        tracker.on_poll_update({"play_state": "play", "custom_field": "new"})

        # custom_field is not monitored, so no change detected
        assert tracker._detected_changes == 0

    def test_grace_period(self):
        """Test grace period for UPnP events."""
        import time

        tracker = UpnpHealthTracker(grace_period=2.0)
        tracker._last_poll_state = {"play_state": "stop"}
        tracker._last_upnp_state = {"play_state": "play"}
        # Event 1 second ago (within grace period)
        tracker._last_upnp_event_time = time.time() - 1.0

        tracker.on_poll_update({"play_state": "play"})

        assert tracker._missed_changes == 0  # Within grace period

    def test_grace_period_expired(self):
        """Test grace period expiration."""
        import time

        tracker = UpnpHealthTracker(grace_period=2.0)
        tracker._last_poll_state = {"play_state": "stop"}
        tracker._last_upnp_state = {"play_state": "play"}
        # Event 3 seconds ago (outside grace period)
        tracker._last_upnp_event_time = time.time() - 3.0

        tracker.on_poll_update({"play_state": "play"})

        assert tracker._missed_changes == 1  # Grace period expired


class TestUpnpHealthTrackerOnUpnpEvent:
    """Test on_upnp_event method."""

    def test_record_event(self):
        """Test recording UPnP event."""
        import time

        tracker = UpnpHealthTracker()

        tracker.on_upnp_event({"play_state": "play", "volume": 50})

        assert tracker._last_upnp_state == {"play_state": "play", "volume": 50}
        assert tracker._last_upnp_event_time is not None
        assert abs(tracker._last_upnp_event_time - time.time()) < 1.0

    def test_update_existing_state(self):
        """Test updating existing UPnP state."""
        tracker = UpnpHealthTracker()
        tracker._last_upnp_state = {"play_state": "stop"}

        tracker.on_upnp_event({"play_state": "play", "volume": 50})

        assert tracker._last_upnp_state == {"play_state": "play", "volume": 50}

    def test_re_evaluate_when_unhealthy(self):
        """Test re-evaluation when unhealthy."""
        tracker = UpnpHealthTracker()
        tracker._upnp_working = False

        tracker.on_upnp_event({"play_state": "play"})

        # Should trigger re-evaluation (implementation detail)
        assert tracker._last_upnp_state == {"play_state": "play"}


class TestUpnpHealthTrackerResetStatistics:
    """Test reset_statistics method."""

    def test_reset_statistics(self):
        """Test resetting statistics."""
        tracker = UpnpHealthTracker()
        tracker._detected_changes = 10
        tracker._missed_changes = 5
        tracker._upnp_working = False

        tracker.reset_statistics()

        assert tracker._detected_changes == 0
        assert tracker._missed_changes == 0
        assert tracker._upnp_working is True

    def test_reset_statistics_no_previous_data(self):
        """Test reset with no previous data."""
        tracker = UpnpHealthTracker()

        tracker.reset_statistics()

        assert tracker._detected_changes == 0
        assert tracker._missed_changes == 0


class TestUpnpHealthTrackerHealthStatus:
    """Test health status updates."""

    def test_health_status_insufficient_samples(self):
        """Test health status not updated with insufficient samples."""
        tracker = UpnpHealthTracker(min_samples=10)
        tracker._last_poll_state = {"play_state": "stop"}

        # Only 5 changes detected (less than min_samples)
        for i in range(5):
            tracker.on_poll_update({"play_state": f"state{i}"})

        # Should still be healthy (not enough samples to make decision)
        assert tracker.is_healthy is True

    def test_health_status_unhealthy_threshold(self):
        """Test health status becomes unhealthy at threshold."""
        tracker = UpnpHealthTracker(min_samples=10)
        tracker._last_poll_state = {"play_state": "stop"}

        # Create enough missed changes to exceed 50% threshold
        for i in range(11):
            tracker.on_poll_update({"play_state": f"state{i}"})
            # UPnP doesn't catch any (no events)

        assert tracker.is_healthy is False

    def test_health_status_healthy_threshold(self):
        """Test health status becomes healthy at threshold."""
        tracker = UpnpHealthTracker(min_samples=10)
        tracker._last_poll_state = {"play_state": "stop"}
        tracker._upnp_working = False  # Start unhealthy

        import time

        # Create changes that UPnP catches (within grace period)
        for i in range(11):
            tracker._last_upnp_state = {"play_state": f"state{i}"}
            tracker._last_upnp_event_time = time.time()
            tracker.on_poll_update({"play_state": f"state{i}"})

        # Should become healthy (miss rate < 20%)
        assert tracker.is_healthy is True

    def test_health_status_hysteresis(self):
        """Test health status uses hysteresis to avoid flapping."""
        tracker = UpnpHealthTracker(min_samples=10)
        tracker._last_poll_state = {"play_state": "stop"}

        # Create exactly 50% miss rate (should not change from healthy)
        for i in range(10):
            if i % 2 == 0:
                # Every other change is caught by UPnP
                import time

                tracker._last_upnp_state = {"play_state": f"state{i}"}
                tracker._last_upnp_event_time = time.time()

            tracker.on_poll_update({"play_state": f"state{i}"})

        # Threshold is >50%, so exactly 50% should stay healthy
        # Current stats: 5 missed / 10 total = 50%
        assert tracker.miss_rate == 0.5
        assert tracker.is_healthy is True

        # Now exceed 50%
        # Next miss: 6 missed / 11 total = 54.5%
        tracker.on_poll_update({"play_state": "final_miss"})
        assert tracker.is_healthy is False


class TestUpnpHealthTrackerHelperMethods:
    """Test helper methods."""

    def test_extract_monitored_fields(self):
        """Test _extract_monitored_fields."""
        tracker = UpnpHealthTracker()

        state = {
            "play_state": "play",
            "volume": 50,
            "muted": True,
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "custom_field": "value",
        }

        result = tracker._extract_monitored_fields(state)

        assert "play_state" in result
        assert "volume" in result
        assert "muted" in result
        assert "title" in result
        assert "artist" in result
        assert "album" in result
        assert "custom_field" not in result

    def test_detect_changes(self):
        """Test _detect_changes."""
        tracker = UpnpHealthTracker()

        old_state = {"play_state": "stop", "volume": 30}
        new_state = {"play_state": "play", "volume": 50, "title": "New"}

        changes = tracker._detect_changes(old_state, new_state)

        # title is new (None -> "New"), so it IS detected as a change
        # The method checks if old_value != new_value and new_value is not None
        assert "play_state" in changes
        assert "volume" in changes
        assert "title" in changes  # New field is detected as change
        assert changes["play_state"] == "play"
        assert changes["volume"] == 50
        assert changes["title"] == "New"

    def test_detect_changes_no_changes(self):
        """Test _detect_changes with no changes."""
        tracker = UpnpHealthTracker()

        old_state = {"play_state": "play", "volume": 50}
        new_state = {"play_state": "play", "volume": 50}

        changes = tracker._detect_changes(old_state, new_state)

        assert changes == {}

    def test_detect_changes_ignores_unknown_metadata(self):
        """Test that changes to 'Unknown' metadata are ignored."""
        tracker = UpnpHealthTracker()

        old_state = {"title": "Song", "artist": "Artist"}
        new_state = {"title": "Unknown", "artist": "unknown", "album": "none"}

        changes = tracker._detect_changes(old_state, new_state)

        # All metadata changes to "Unknown" should be ignored
        assert changes == {}

    def test_upnp_saw_change_no_events(self):
        """Test _upnp_saw_change with no UPnP events."""
        tracker = UpnpHealthTracker()

        result = tracker._upnp_saw_change("play_state", "play")

        assert result is False

    def test_upnp_saw_change_within_grace_period(self):
        """Test _upnp_saw_change within grace period."""
        import time

        tracker = UpnpHealthTracker()
        tracker._last_upnp_state = {"play_state": "play"}
        tracker._last_upnp_event_time = time.time() - 1.0  # 1 second ago

        result = tracker._upnp_saw_change("play_state", "play")

        assert result is True

    def test_upnp_saw_change_different_value(self):
        """Test _upnp_saw_change with different value."""
        import time

        tracker = UpnpHealthTracker()
        tracker._last_upnp_state = {"play_state": "pause"}
        tracker._last_upnp_event_time = time.time() - 1.0

        result = tracker._upnp_saw_change("play_state", "play")

        assert result is False
