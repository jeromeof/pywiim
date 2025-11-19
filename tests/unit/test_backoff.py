"""Unit tests for backoff controller."""

from datetime import timedelta

from pywiim.backoff import BackoffController


class TestBackoffController:
    """Test BackoffController class."""

    def test_init(self):
        """Test BackoffController initialization."""
        backoff = BackoffController()

        assert backoff.consecutive_failures == 0

    def test_record_success(self):
        """Test recording success resets failures."""
        backoff = BackoffController()

        backoff.record_failure()
        backoff.record_failure()
        assert backoff.consecutive_failures == 2

        backoff.record_success()
        assert backoff.consecutive_failures == 0

    def test_record_failure(self):
        """Test recording failure increments counter."""
        backoff = BackoffController()

        backoff.record_failure()
        assert backoff.consecutive_failures == 1

        backoff.record_failure()
        assert backoff.consecutive_failures == 2

    def test_next_interval_no_failures(self):
        """Test next interval with no failures."""
        backoff = BackoffController()

        interval = backoff.next_interval(default_seconds=5)

        assert interval == timedelta(seconds=5)

    def test_next_interval_after_2_failures(self):
        """Test next interval after 2 failures."""
        backoff = BackoffController()

        backoff.record_failure()
        backoff.record_failure()

        interval = backoff.next_interval(default_seconds=5)

        assert interval == timedelta(seconds=10)

    def test_next_interval_after_3_failures(self):
        """Test next interval after 3 failures."""
        backoff = BackoffController()

        backoff.record_failure()
        backoff.record_failure()
        backoff.record_failure()

        interval = backoff.next_interval(default_seconds=5)

        assert interval == timedelta(seconds=30)

    def test_next_interval_after_5_failures(self):
        """Test next interval after 5 failures."""
        backoff = BackoffController()

        for _ in range(5):
            backoff.record_failure()

        interval = backoff.next_interval(default_seconds=5)

        assert interval == timedelta(seconds=60)

    def test_next_interval_after_many_failures(self):
        """Test next interval after many failures."""
        backoff = BackoffController()

        for _ in range(10):
            backoff.record_failure()

        interval = backoff.next_interval(default_seconds=5)

        assert interval == timedelta(seconds=60)  # Max is 60

    def test_reset(self):
        """Test reset method."""
        backoff = BackoffController()

        backoff.record_failure()
        backoff.reset()

        assert backoff.consecutive_failures == 0

    def test_repr(self):
        """Test string representation."""
        backoff = BackoffController()

        backoff.record_failure()
        backoff.record_failure()

        assert "BackoffController" in repr(backoff)
        assert "failures=2" in repr(backoff)
