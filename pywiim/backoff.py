"""Backoff logic for handling consecutive failures.

This module provides exponential backoff functionality for retry logic,
tracking consecutive failures and recommending appropriate retry intervals.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

__all__ = ["BackoffController"]

# Mapping: consecutive_failures → new polling interval (seconds)
_BACKOFF_STEPS: Final[dict[int, int]] = {
    2: 10,  # after 2 failures → 10-second polling
    3: 30,  # after 3 → 30-second polling
    5: 60,  # after 5 → 60-second polling
}


class BackoffController:
    """Tracks consecutive failures and recommends next interval.

    This controller implements exponential backoff for handling transient
    failures. It tracks consecutive failures and recommends progressively
    longer intervals between retries.

    Example:
        ```python
        backoff = BackoffController()

        try:
            # Attempt operation
            await some_operation()
            backoff.record_success()  # Reset on success
        except Exception:
            backoff.record_failure()  # Increment failure count
            interval = backoff.next_interval(default_seconds=5)
            await asyncio.sleep(interval.total_seconds())
        ```

    Attributes:
        consecutive_failures: Number of consecutive failures (read-only).
    """

    def __init__(self) -> None:
        """Initialize the backoff controller."""
        self._failures = 0

    def record_success(self) -> None:
        """Reset failure counter after a successful operation."""
        self._failures = 0

    def record_failure(self) -> None:
        """Increment failure counter after a failed operation."""
        self._failures += 1

    @property
    def consecutive_failures(self) -> int:
        """Return the number of consecutive failures."""
        return self._failures

    def next_interval(self, default_seconds: int) -> timedelta:
        """Return recommended polling interval after last event.

        The interval increases based on the number of consecutive failures:
        - 0-1 failures: default interval
        - 2 failures: 10 seconds
        - 3 failures: 30 seconds
        - 5+ failures: 60 seconds

        Args:
            default_seconds: Default interval in seconds (used when no failures)

        Returns:
            Recommended interval as timedelta
        """
        # Find the highest threshold that has been reached
        active_seconds = default_seconds
        for threshold, seconds in sorted(_BACKOFF_STEPS.items()):
            if self._failures >= threshold:
                active_seconds = seconds
        return timedelta(seconds=active_seconds)

    def reset(self) -> None:
        """Reset the failure counter to zero.

        Alias for `record_success()` for clarity in some contexts.
        """
        self.record_success()

    def __repr__(self) -> str:
        """String representation."""
        return f"BackoffController(failures={self._failures})"
