"""Basic unit tests for UPnP eventer.

These are basic tests that mock the async_upnp_client dependencies.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pywiim.upnp.eventer import UpnpEventer


class TestUpnpEventer:
    """Test UpnpEventer class."""

    def test_init(self):
        """Test UpnpEventer initialization."""
        mock_upnp_client = MagicMock()
        mock_state_manager = MagicMock()

        eventer = UpnpEventer(mock_upnp_client, mock_state_manager, "test-uuid")

        assert eventer.upnp_client == mock_upnp_client
        assert eventer.state_manager == mock_state_manager
        assert eventer.device_uuid == "test-uuid"
        assert eventer._event_count == 0
        assert eventer._last_notify_ts is None

    def test_init_with_callback(self):
        """Test UpnpEventer initialization with callback."""
        mock_upnp_client = MagicMock()
        mock_state_manager = MagicMock()

        def callback():
            pass

        eventer = UpnpEventer(mock_upnp_client, mock_state_manager, "test-uuid", state_updated_callback=callback)

        assert eventer.state_updated_callback == callback

    @pytest.mark.asyncio
    async def test_start(self):
        """Test starting event subscriptions."""
        mock_upnp_client = MagicMock()
        mock_state_manager = MagicMock()
        mock_notify_server = MagicMock()
        mock_notify_server.callback_url = "http://192.168.1.100:8000/notify"
        mock_notify_server.host = "192.168.1.100"
        mock_dmr_device = MagicMock()
        mock_dmr_device.async_subscribe_services = AsyncMock()

        mock_upnp_client.start_notify_server = AsyncMock(return_value=mock_notify_server)
        mock_upnp_client._dmr_device = mock_dmr_device
        mock_upnp_client.notify_server = mock_notify_server

        eventer = UpnpEventer(mock_upnp_client, mock_state_manager, "test-uuid")

        await eventer.start()

        mock_upnp_client.start_notify_server.assert_called_once()
        mock_dmr_device.async_subscribe_services.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_unsubscribe(self):
        """Test unsubscribing from services."""
        mock_upnp_client = MagicMock()
        mock_state_manager = MagicMock()
        mock_dmr_device = MagicMock()
        mock_dmr_device.async_unsubscribe_services = AsyncMock()

        mock_upnp_client._dmr_device = mock_dmr_device
        mock_upnp_client.unwind_notify_server = AsyncMock()

        eventer = UpnpEventer(mock_upnp_client, mock_state_manager, "test-uuid")

        await eventer.async_unsubscribe()

        mock_dmr_device.async_unsubscribe_services.assert_called_once()
        mock_upnp_client.unwind_notify_server.assert_called_once()

    def test_get_subscription_stats(self):
        """Test getting subscription statistics."""
        import time

        mock_upnp_client = MagicMock()
        mock_state_manager = MagicMock()

        eventer = UpnpEventer(mock_upnp_client, mock_state_manager, "test-uuid")
        eventer._event_count = 5
        eventer._last_notify_ts = time.time() - 10.0

        stats = eventer.get_subscription_stats()

        assert stats["total_events"] == 5
        assert stats["last_notify_ts"] is not None
        assert stats["time_since_last"] is not None

    def test_statistics_property(self):
        """Test statistics property."""
        import time

        mock_upnp_client = MagicMock()
        mock_upnp_client.host = "192.168.1.100"
        mock_state_manager = MagicMock()

        eventer = UpnpEventer(mock_upnp_client, mock_state_manager, "test-uuid")
        eventer._event_count = 3
        eventer._last_notify_ts = time.time() - 5.0

        stats = eventer.statistics

        assert stats["event_count"] == 3
        assert stats["device_uuid"] == "test-uuid"
        assert stats["device_host"] == "192.168.1.100"
        assert stats["time_since_last_event"] is not None
