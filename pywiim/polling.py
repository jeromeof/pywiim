"""Framework-agnostic polling strategy helpers for WiiM devices.

This module provides polling strategy recommendations and helpers for applications
managing their own polling loops. The strategy is based on the proven approach
used in the Home Assistant integration, but abstracted to be framework-agnostic.

Applications are responsible for managing their own polling loops. This module
provides recommendations for optimal intervals and conditional fetching logic.
"""

from __future__ import annotations

import time
from typing import Any

__all__ = [
    "PollingStrategy",
    "TrackChangeDetector",
    "fetch_parallel",
]


class PollingStrategy:
    """Polling strategy recommendations and helpers.

    This class provides framework-agnostic polling strategy recommendations
    based on device capabilities and state. Applications use these recommendations
    to manage their own polling loops.

    The strategy is based on the proven approach from the Home Assistant integration:
    - Adaptive intervals based on device state (playing vs idle)
    - Conditional fetching based on data type
    - Capability-aware endpoint selection

    Example:
        ```python
        from pywiim import WiiMClient, PollingStrategy

        client = WiiMClient("192.168.1.100")
        capabilities = await client._detect_capabilities()
        strategy = PollingStrategy(capabilities)

        # Get recommended interval
        role = "solo"
        is_playing = False
        interval = strategy.get_optimal_interval(role, is_playing)
        print(f"Poll every {interval} seconds")

        # Check if device info should be fetched
        last_device_info = 0
        if strategy.should_fetch_device_info(last_device_info):
            device_info = await client.get_device_info_model()
            last_device_info = time.time()
        ```
    """

    # Polling interval constants (in seconds)
    # Note: With hybrid position estimation, we poll less frequently during playback
    # Position is estimated locally and corrected every 5-10 seconds via polling
    FAST_POLL_INTERVAL = 5.0  # During active playback (was 1.0, now 5.0 with hybrid estimation)
    NORMAL_POLL_INTERVAL = 5.0  # When idle
    DEVICE_INFO_INTERVAL = 60.0  # Device health check
    MULTIROOM_INTERVAL = 15.0  # Role detection + group changes
    EQ_INFO_INTERVAL = 60.0  # Settings rarely change
    AUDIO_OUTPUT_INTERVAL = 15.0  # Mode changes rarely

    # Legacy device intervals (longer for older devices)
    LEGACY_FAST_POLL_INTERVAL = 3.0  # Legacy devices during playback
    LEGACY_NORMAL_POLL_INTERVAL = 15.0  # Legacy devices when idle
    LEGACY_SLAVE_INTERVAL = 10.0  # Legacy slaves

    def __init__(self, capabilities: dict[str, Any]) -> None:
        """Initialize polling strategy with device capabilities.

        Args:
            capabilities: Device capabilities dictionary from capability detection.
        """
        self.capabilities = capabilities

    def get_optimal_interval(
        self,
        role: str,
        is_playing: bool,
    ) -> float:
        """Get optimal polling interval based on device capabilities and state.

        The interval adapts based on:
        - Device type (WiiM vs Legacy)
        - Device role (master/slave/solo)
        - Playback state (playing vs idle)

        Args:
            role: Device role ("master", "slave", or "solo")
            is_playing: Whether device is currently playing

        Returns:
            Recommended polling interval in seconds
        """
        if self.capabilities.get("is_legacy_device", False):
            # Legacy devices need longer intervals
            if role == "slave":
                return self.LEGACY_SLAVE_INTERVAL
            elif is_playing:
                return self.LEGACY_FAST_POLL_INTERVAL
            else:
                return self.LEGACY_NORMAL_POLL_INTERVAL
        else:
            # Modern WiiM devices
            # With hybrid position estimation, we can poll less frequently
            # Position is estimated locally and corrected via periodic polls
            if role == "slave":
                return self.NORMAL_POLL_INTERVAL  # 5 seconds for slaves
            elif is_playing:
                return self.FAST_POLL_INTERVAL  # 5 seconds when playing (hybrid estimation handles smooth updates)
            else:
                return self.NORMAL_POLL_INTERVAL  # 5 seconds when idle

    def should_fetch_device_info(
        self,
        last_fetch_time: float,
        now: float | None = None,
    ) -> bool:
        """Check if device info should be fetched (60s interval).

        Device info is fetched periodically for health checks. It doesn't change
        frequently, so a 60-second interval is sufficient.

        Args:
            last_fetch_time: Timestamp of last device info fetch (0 if never fetched)
            now: Current time (defaults to time.time())

        Returns:
            True if device info should be fetched
        """
        if now is None:
            now = time.time()

        # Always fetch on first check
        if last_fetch_time == 0:
            return True

        return (now - last_fetch_time) >= self.DEVICE_INFO_INTERVAL

    def should_fetch_multiroom(
        self,
        last_fetch_time: float,
        is_activity_triggered: bool = False,
        now: float | None = None,
    ) -> bool:
        """Check if multiroom info should be fetched (15s + activity).

        Multiroom info is fetched:
        - Every 15 seconds (for role detection and group changes)
        - On activity triggers (track changes, source changes)

        Args:
            last_fetch_time: Timestamp of last multiroom fetch (0 if never fetched)
            is_activity_triggered: Whether activity triggered this check
            now: Current time (defaults to time.time())

        Returns:
            True if multiroom info should be fetched
        """
        if now is None:
            now = time.time()

        # Always fetch on first check or activity trigger
        if last_fetch_time == 0 or is_activity_triggered:
            return True

        return (now - last_fetch_time) >= self.MULTIROOM_INTERVAL

    def should_fetch_metadata(
        self,
        track_changed: bool,
        metadata_supported: bool | None,
    ) -> bool:
        """Check if metadata should be fetched (on track change only).

        Metadata is only fetched when:
        - Track has changed (title, artist, source, artwork)
        - Device supports metadata endpoint

        Args:
            track_changed: Whether track has changed since last check
            metadata_supported: Whether device supports metadata endpoint

        Returns:
            True if metadata should be fetched
        """
        if metadata_supported is False:
            return False  # Endpoint not supported

        return track_changed

    def should_fetch_eq_info(
        self,
        last_fetch_time: float,
        eq_supported: bool | None,
        now: float | None = None,
    ) -> bool:
        """Check if EQ info should be fetched (60s interval, if supported).

        EQ settings change rarely, so a 60-second interval is sufficient.

        Args:
            last_fetch_time: Timestamp of last EQ info fetch (0 if never fetched)
            eq_supported: Whether device supports EQ endpoint
            now: Current time (defaults to time.time())

        Returns:
            True if EQ info should be fetched
        """
        if eq_supported is False:
            return False  # Endpoint not supported

        if now is None:
            now = time.time()

        # Always fetch on first check
        if last_fetch_time == 0:
            return True

        return (now - last_fetch_time) >= self.EQ_INFO_INTERVAL

    def should_fetch_audio_output(
        self,
        last_fetch_time: float,
        audio_output_supported: bool | None,
        now: float | None = None,
    ) -> bool:
        """Check if audio output status should be fetched (15s interval, if supported).

        Audio output modes change rarely, so a 15-second interval is sufficient.

        Args:
            last_fetch_time: Timestamp of last audio output fetch (0 if never fetched)
            audio_output_supported: Whether device supports audio output endpoint
            now: Current time (defaults to time.time())

        Returns:
            True if audio output status should be fetched
        """
        if audio_output_supported is False:
            return False  # Endpoint not supported

        if now is None:
            now = time.time()

        # Always fetch on first check
        if last_fetch_time == 0:
            return True

        return (now - last_fetch_time) >= self.AUDIO_OUTPUT_INTERVAL


class TrackChangeDetector:
    """Detect track changes for metadata fetching.

    This helper tracks track metadata (title, artist, source, artwork) to
    detect when a track has changed. This is used to determine when metadata
    should be fetched (only on track changes, not every poll cycle).

    Example:
        ```python
        detector = TrackChangeDetector()

        # Check if track changed
        if detector.track_changed(title, artist, source, artwork):
            # Fetch metadata
            metadata = await client.get_meta_info()
        ```
    """

    def __init__(self) -> None:
        """Initialize track change detector."""
        self._last_track_info: tuple[str, str, str, str] | None = None

    def track_changed(
        self,
        title: str | None,
        artist: str | None,
        source: str | None,
        artwork: str | None,
    ) -> bool:
        """Check if track has changed.

        Args:
            title: Current track title
            artist: Current track artist
            source: Current source
            artwork: Current artwork URL

        Returns:
            True if track changed, False otherwise
        """
        current = (
            title or "",
            artist or "",
            source or "",
            artwork or "",
        )

        if self._last_track_info is None:
            self._last_track_info = current
            return True  # First time, consider it changed

        changed = current != self._last_track_info
        if changed:
            self._last_track_info = current

        return changed

    def reset(self) -> None:
        """Reset track change detector (clear last track info)."""
        self._last_track_info = None


async def fetch_parallel(
    *tasks: Any,
    return_exceptions: bool = True,
) -> list[Any]:
    """Execute multiple fetch tasks in parallel.

    This helper executes multiple async tasks in parallel using asyncio.gather.
    It's useful for conditional fetching where multiple endpoints may be fetched
    in the same poll cycle.

    Args:
        *tasks: Async tasks to execute
        return_exceptions: If True, return exceptions in results instead of raising

    Returns:
        List of results (or exceptions if return_exceptions=True)

    Example:
        ```python
        tasks = []
        tasks.append(client.get_player_status())

        if strategy.should_fetch_device_info(last_device_info):
            tasks.append(client.get_device_info_model())

        results = await fetch_parallel(*tasks)
        ```
    """
    import asyncio

    return await asyncio.gather(*tasks, return_exceptions=return_exceptions)
