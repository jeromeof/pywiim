"""UPnP event health tracking.

This module provides health tracking for UPnP events by detecting when
HTTP polling discovers changes that UPnP events should have caught.

The key insight: We can't detect UPnP health when nothing is changing (no events = healthy),
but we CAN detect it when things ARE changing by comparing what HTTP polling sees vs what
UPnP events report.
"""

from __future__ import annotations

import logging
import time
from typing import Any

_LOGGER = logging.getLogger(__name__)


# Fields that UPnP should reliably notify about
# These are fields where a change should ALWAYS trigger a UPnP event
UPNP_MONITORED_FIELDS = {
    "play_state",  # play/pause/stop always fires UPnP event
    "volume",  # Volume changes always fire UPnP event
    "muted",  # Mute changes always fire UPnP event
    "title",  # Track changes include metadata updates
    "artist",  # Track changes include metadata updates
    "album",  # Track changes include metadata updates
}

# Note: We deliberately DON'T monitor position/duration because:
# - UPnP only sends position/duration on track start, not continuously
# - Position during playback is estimated locally, not via UPnP events


class UpnpHealthTracker:
    """Track UPnP event health by detecting missed changes.

    This class monitors state changes detected by HTTP polling and checks
    whether UPnP events also reported those changes. If polling consistently
    detects changes that UPnP missed, we mark UPnP as unhealthy.

    This approach avoids false negatives from time-based detection:
    - Time-based: "No events in X seconds" = unhealthy → WRONG when device is idle
    - Change-based: "Polling saw change, UPnP didn't" = unhealthy → CORRECT

    Example:
        >>> tracker = UpnpHealthTracker()
        >>>
        >>> # After HTTP poll
        >>> tracker.on_poll_update({"play_state": "play", "volume": 50})
        >>>
        >>> # After UPnP event
        >>> tracker.on_upnp_event({"play_state": "play", "volume": 50})
        >>>
        >>> # Check health
        >>> if tracker.is_healthy:
        >>>     print("UPnP working!")
    """

    def __init__(self, grace_period: float = 2.0, min_samples: int = 3):
        """Initialize health tracker.

        Args:
            grace_period: Time window (seconds) to wait for UPnP event after poll detects change.
                         Handles race conditions where poll arrives before UPnP event.
            min_samples: Minimum number of detected changes before making health decisions.
                        Avoids false positives from insufficient data.
        """
        self._grace_period = grace_period
        self._min_samples = min_samples

        # State tracking
        self._last_poll_state: dict[str, Any] = {}
        self._last_upnp_state: dict[str, Any] = {}
        self._last_upnp_event_time: float | None = None

        # Statistics
        self._detected_changes = 0  # Total changes detected by polling
        self._missed_changes = 0  # Changes polling saw but UPnP didn't
        self._upnp_working = True  # Current health status (assume healthy initially)

        # For logging state transitions
        self._last_logged_status = True

    @property
    def is_healthy(self) -> bool:
        """Check if UPnP events are working properly.

        Returns:
            True if UPnP is healthy, False if degraded/failed
        """
        return self._upnp_working

    @property
    def miss_rate(self) -> float:
        """Get current miss rate (0.0 = perfect, 1.0 = all missed).

        Returns:
            Fraction of changes missed by UPnP (0.0 to 1.0)
        """
        if self._detected_changes == 0:
            return 0.0
        return self._missed_changes / self._detected_changes

    @property
    def statistics(self) -> dict[str, Any]:
        """Get health statistics for diagnostics.

        Returns:
            Dictionary with detected_changes, missed_changes, miss_rate, is_healthy
        """
        return {
            "detected_changes": self._detected_changes,
            "missed_changes": self._missed_changes,
            "miss_rate": self.miss_rate,
            "is_healthy": self.is_healthy,
            "has_enough_samples": self._detected_changes >= self._min_samples,
        }

    def on_poll_update(self, state: dict[str, Any]) -> None:
        """Called after HTTP polling updates state.

        Detects changes by comparing with previous poll state, then checks
        if UPnP events should have (and did) report those changes.

        Args:
            state: Current state from HTTP polling (dict with play_state, volume, etc)
        """
        if not self._last_poll_state:
            # First poll, just record state
            self._last_poll_state = self._extract_monitored_fields(state)
            return

        # Detect changes in monitored fields
        changes = self._detect_changes(self._last_poll_state, state)

        if changes:
            self._detected_changes += len(changes)

            # Check if UPnP should have caught these changes
            for field, new_value in changes.items():
                if not self._upnp_saw_change(field, new_value):
                    self._missed_changes += 1
                    _LOGGER.debug(
                        "UPnP missed change: %s changed to %s (detected by polling)",
                        field,
                        new_value,
                    )

        # Update stored state
        self._last_poll_state = self._extract_monitored_fields(state)

        # Re-evaluate health status
        self._update_health_status()

    def on_upnp_event(self, event_data: dict[str, Any]) -> None:
        """Called when UPnP event arrives.

        Records the event data and timestamp so we can check if UPnP
        is catching the changes that polling detects.

        Args:
            event_data: State data from UPnP event (dict with play_state, volume, etc)
        """
        self._last_upnp_state.update(self._extract_monitored_fields(event_data))
        self._last_upnp_event_time = time.time()

        # If we were unhealthy and now receiving events, re-evaluate
        if not self._upnp_working:
            _LOGGER.debug("UPnP event received while in degraded state, re-evaluating health")
            self._update_health_status()

    def reset_statistics(self) -> None:
        """Reset statistics (useful when UPnP recovers or resubscribes).

        Call this when UPnP resubscribes or you want to give it a fresh start.
        This prevents old statistics from keeping UPnP in "degraded" state forever.
        """
        old_missed = self._missed_changes
        old_detected = self._detected_changes

        self._detected_changes = 0
        self._missed_changes = 0
        self._upnp_working = True  # Optimistic: assume working until proven otherwise

        if old_detected > 0:
            _LOGGER.info(
                "Reset UPnP health statistics (was: %d/%d changes caught, %.1f%% miss rate)",
                old_detected - old_missed,
                old_detected,
                (old_missed / old_detected * 100) if old_detected > 0 else 0,
            )

    def _extract_monitored_fields(self, state: dict[str, Any]) -> dict[str, Any]:
        """Extract only the fields we monitor for UPnP health.

        Args:
            state: Full state dictionary

        Returns:
            Dictionary with only monitored fields
        """
        return {field: state.get(field) for field in UPNP_MONITORED_FIELDS if field in state}

    def _detect_changes(
        self,
        old_state: dict[str, Any],
        new_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Detect which monitored fields changed between states.

        Args:
            old_state: Previous state
            new_state: Current state

        Returns:
            Dictionary of {field: new_value} for fields that changed
        """
        changes = {}

        new_monitored = self._extract_monitored_fields(new_state)

        for field in UPNP_MONITORED_FIELDS:
            old_value = old_state.get(field)
            new_value = new_monitored.get(field)

            # Check if value changed
            if old_value != new_value and new_value is not None:
                changes[field] = new_value

        return changes

    def _upnp_saw_change(self, field: str, new_value: Any) -> bool:
        """Check if UPnP event captured this change within grace period.

        Args:
            field: Field name (e.g., "play_state")
            new_value: New value detected by polling

        Returns:
            True if UPnP event reported this change within grace period
        """
        # If we haven't received any UPnP events yet, can't have seen the change
        if self._last_upnp_event_time is None:
            return False

        # Check if UPnP event is recent (within grace period)
        time_since_upnp = time.time() - self._last_upnp_event_time
        if time_since_upnp > self._grace_period:
            # UPnP event too old, couldn't have caught this change
            return False

        # Check if UPnP reported the same value
        upnp_value = self._last_upnp_state.get(field)
        return bool(upnp_value == new_value)

    def _update_health_status(self) -> None:
        """Update UPnP health status based on miss rate.

        Uses hysteresis to avoid flapping:
        - Mark unhealthy if miss rate > 50% (more than half of changes missed)
        - Mark healthy if miss rate < 20% (catching most changes)
        """
        # Need enough samples before making decisions
        if self._detected_changes < self._min_samples:
            return

        miss_rate = self.miss_rate
        old_status = self._upnp_working

        # Hysteresis thresholds to avoid flapping
        UNHEALTHY_THRESHOLD = 0.5  # >50% miss rate = unhealthy
        HEALTHY_THRESHOLD = 0.2  # <20% miss rate = healthy

        if miss_rate > UNHEALTHY_THRESHOLD:
            if self._upnp_working:
                _LOGGER.warning(
                    "🔴 UPnP events appear DEGRADED: %.1f%% miss rate (%d/%d changes missed)",
                    miss_rate * 100,
                    self._missed_changes,
                    self._detected_changes,
                )
                _LOGGER.warning("   → Switching to fast polling (1 second) to compensate")
                self._upnp_working = False
        elif miss_rate < HEALTHY_THRESHOLD:
            if not self._upnp_working:
                _LOGGER.info(
                    "🟢 UPnP events RECOVERED: %.1f%% miss rate (%d/%d changes caught)",
                    miss_rate * 100,
                    self._detected_changes - self._missed_changes,
                    self._detected_changes,
                )
                _LOGGER.info("   → Reducing polling frequency")
                self._upnp_working = True
                # Reset stats to give fresh start
                self._detected_changes = 0
                self._missed_changes = 0

        # Log status if it changed
        if old_status != self._upnp_working:
            self._last_logged_status = self._upnp_working
