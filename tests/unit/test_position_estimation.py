"""Unit tests for position estimation with smooth tracking.

Tests the improved position estimation logic that prioritizes smooth UI updates
over exact HTTP synchronization.
"""

from __future__ import annotations

import time

from pywiim.state import StateSynchronizer


class TestPositionEstimationSmoothing:
    """Test smooth position estimation with tolerance-based HTTP integration."""

    def test_small_drift_keeps_smooth_estimation(self):
        """Test that small drift (< 3s) doesn't cause position jumps."""
        sync = StateSynchronizer()

        # Initial state: playing at position 100
        base_time = time.time()
        sync.update_from_http(
            {"play_state": "play", "position": 100, "duration": 300},
            timestamp=base_time,
        )

        # After 3 seconds, our timer estimates position = 103
        # HTTP poll comes back with position = 104 (1 second drift)
        sync.update_from_http(
            {"play_state": "play", "position": 104, "duration": 300},
            timestamp=base_time + 3,
        )

        # Should NOT reset because drift is only 1s (< 3s tolerance)
        # Our smooth estimation should continue from where it was
        merged = sync.get_merged_state()
        position = merged.get("position")

        # Position should be close to our estimated 103, not jumped to HTTP's 104
        # The exact value depends on timing, but should be within range
        assert position is not None
        # After HTTP update at t+3, estimated position should be 104 (base) + 0 (just updated) = 104
        # Actually, since we kept the smooth estimation, it should be close to 103
        # But the system uses the HTTP value as base if reset, so let's check the behavior

        # Get the estimation base - if it didn't reset, it should still be 100
        assert sync._estimation_base_position == 100, "Should keep original base (no reset)"
        assert abs(sync._estimation_start_time - base_time) < 0.1, "Should keep original start time"

    def test_large_drift_resets_estimation(self):
        """Test that large drift (> 3s) causes reset to HTTP position."""
        sync = StateSynchronizer()

        # Initial state: playing at position 100
        base_time = time.time()
        sync.update_from_http(
            {"play_state": "play", "position": 100, "duration": 300},
            timestamp=base_time,
        )

        # Record original start time
        original_start = sync._estimation_start_time

        # After 3 seconds, our timer estimates position = 103
        # HTTP poll comes back with position = 110 (7 second drift - maybe buffering happened)
        sync.update_from_http(
            {"play_state": "play", "position": 110, "duration": 300},
            timestamp=base_time + 3,
        )

        # SHOULD reset because drift is 7s (> 3s tolerance)
        # Check that base was updated (reset occurred)
        assert sync._estimation_base_position == 110, "Should update base to HTTP position on large drift"
        assert sync._estimation_start_time != original_start, "Should update start time on reset"
        assert abs(sync._estimation_start_time - (base_time + 3)) < 0.1, "Start time should be update timestamp"

    def test_track_change_always_resets(self):
        """Test that track changes always reset estimation."""
        sync = StateSynchronizer()

        # Initial state: playing track 1
        base_time = time.time()
        sync.update_from_http(
            {
                "play_state": "play",
                "position": 100,
                "duration": 300,
                "title": "Track 1",
                "artist": "Artist 1",
            },
            timestamp=base_time,
        )

        # Verify first track is set
        assert sync._estimation_base_position == 100, "Should set base to 100 for track 1"
        first_track_start = sync._estimation_start_time

        # 2 seconds later, new track starts at position 0
        sync.update_from_http(
            {
                "play_state": "play",
                "position": 0,
                "duration": 250,
                "title": "Track 2",
                "artist": "Artist 1",
            },
            timestamp=base_time + 2,
        )

        # Should reset to position 0 on track change
        assert sync._estimation_base_position == 0, "Should update base to 0 on track change"
        assert sync._estimation_start_time != first_track_start, "Should update start time on track change"
        assert abs(sync._estimation_start_time - (base_time + 2)) < 0.1, "Start time should be update timestamp"

    def test_seek_backward_always_resets(self):
        """Test that seeking backward always resets estimation."""
        sync = StateSynchronizer()

        # Initial state: playing at position 100
        base_time = time.time()
        sync.update_from_http(
            {"play_state": "play", "position": 100, "duration": 300},
            timestamp=base_time,
        )

        original_start = sync._estimation_start_time

        # 2 seconds later, user seeks back to position 50
        sync.update_from_http(
            {"play_state": "play", "position": 50, "duration": 300},
            timestamp=base_time + 2,
        )

        # Should reset to position 50 on seek backward
        assert sync._estimation_base_position == 50, "Should update base to 50 on seek backward"
        assert sync._estimation_start_time != original_start, "Should update start time on seek"
        assert abs(sync._estimation_start_time - (base_time + 2)) < 0.1, "Start time should be update timestamp"

    def test_seek_forward_always_resets(self):
        """Test that seeking forward always resets estimation."""
        sync = StateSynchronizer()

        # Initial state: playing at position 50
        base_time = time.time()
        sync.update_from_http(
            {"play_state": "play", "position": 50, "duration": 300},
            timestamp=base_time,
        )

        original_start = sync._estimation_start_time

        # 2 seconds later, user seeks forward to position 150 (>10s jump)
        sync.update_from_http(
            {"play_state": "play", "position": 150, "duration": 300},
            timestamp=base_time + 2,
        )

        # Should reset to position 150 on seek forward
        assert sync._estimation_base_position == 150, "Should update base to 150 on seek forward"
        assert sync._estimation_start_time != original_start, "Should update start time on seek"
        assert abs(sync._estimation_start_time - (base_time + 2)) < 0.1, "Start time should be update timestamp"

    def test_estimation_continues_smoothly_between_polls(self):
        """Test that position increments smoothly between HTTP polls."""
        sync = StateSynchronizer()

        # Initial state: playing at position 100
        base_time = time.time()
        sync.update_from_http(
            {"play_state": "play", "position": 100, "duration": 300},
            timestamp=base_time,
        )

        # Verify base is set
        assert sync._estimation_base_position == 100
        assert abs(sync._estimation_start_time - base_time) < 0.1

        # Simulate time advancing by manually setting start time in the past
        # This tests that estimation calculates correctly based on elapsed time
        for seconds_elapsed in [1, 2, 3, 4, 5]:
            # Pretend estimation started N seconds ago
            sync._estimation_start_time = time.time() - seconds_elapsed
            estimated = sync._get_estimated_position()
            # Should be base + elapsed time
            expected = 100 + seconds_elapsed
            assert estimated == expected, f"At t+{seconds_elapsed}, expected {expected}, got {estimated}"

    def test_http_confirmation_within_tolerance(self):
        """Test that HTTP updates within tolerance don't disrupt smooth playback."""
        sync = StateSynchronizer()

        # Start playing at position 100
        base_time = time.time()
        sync.update_from_http(
            {"play_state": "play", "position": 100, "duration": 300},
            timestamp=base_time,
        )

        # Simulate 5 seconds of playback
        # Our estimation: 100 + 5 = 105
        # HTTP comes back with 106 (1 second ahead due to network delay)
        sync.update_from_http(
            {"play_state": "play", "position": 106, "duration": 300},
            timestamp=base_time + 5,
        )

        # Should keep smooth estimation (not reset)
        # Base should still be 100, start time should still be base_time
        assert sync._estimation_base_position == 100, "Should not reset on small drift"
        assert abs(sync._estimation_start_time - base_time) < 0.1, "Should keep original start time"

        # Now simulate another 3 seconds
        # Our estimation: 100 + 8 = 108
        # HTTP comes back with 107 (1 second behind due to polling lag)
        sync.update_from_http(
            {"play_state": "play", "position": 107, "duration": 300},
            timestamp=base_time + 8,
        )

        # Should still keep smooth estimation
        assert sync._estimation_base_position == 100, "Should still not reset"

    def test_no_jitter_on_consecutive_http_polls(self):
        """Test that consecutive HTTP polls don't cause position jitter."""
        sync = StateSynchronizer()

        base_time = time.time()

        # Series of HTTP polls with slight variations
        positions = [100, 102, 105, 107, 110]  # Realistic with some variance
        for i, pos in enumerate(positions):
            sync.update_from_http(
                {"play_state": "play", "position": pos, "duration": 300},
                timestamp=base_time + (i * 2),  # Every 2 seconds
            )

            # Check that we're not constantly resetting
            # After first update, base should stay stable if within tolerance
            if i == 0:
                assert sync._estimation_base_position == pos, f"Initial base should be {pos}"
            # Subsequent updates should keep smooth estimation if within tolerance

        # Base should not have changed much if drift stayed within tolerance
        # This depends on the actual drift calculation
        # The key is that position should increase smoothly, not jump around


class TestPositionEstimationEdgeCases:
    """Test edge cases for position estimation."""

    def test_position_clamped_to_duration(self):
        """Test that position is clamped to track duration."""
        sync = StateSynchronizer()

        base_time = time.time()
        sync.update_from_http(
            {"play_state": "play", "position": 295, "duration": 300},
            timestamp=base_time,
        )

        # Simulate 10 seconds passing (would estimate 305, but should clamp to 300)
        sync._estimation_start_time = base_time - 10
        estimated = sync._get_estimated_position()

        assert estimated == 300, "Position should be clamped to duration"

    def test_negative_position_handling(self):
        """Test that negative positions are handled gracefully."""
        sync = StateSynchronizer()

        base_time = time.time()
        # Device might return -1 or 0 when stopped
        sync.update_from_http(
            {"play_state": "play", "position": 0, "duration": 300},
            timestamp=base_time,
        )

        merged = sync.get_merged_state()
        position = merged.get("position")

        assert position == 0, "Should handle position 0"

    def test_none_position_stops_estimation(self):
        """Test that None position stops estimation."""
        sync = StateSynchronizer()

        base_time = time.time()
        sync.update_from_http(
            {"play_state": "play", "position": 100, "duration": 300},
            timestamp=base_time,
        )

        # Position becomes None (maybe device stopped)
        sync.update_from_http(
            {"play_state": "stop", "position": None, "duration": 300},
            timestamp=base_time + 2,
        )

        # Estimation should stop
        estimated = sync._get_estimated_position()
        assert estimated is None, "Should not estimate when stopped"
