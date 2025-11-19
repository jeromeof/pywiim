"""Basic unit tests for UPnP client.

These are basic tests that mock the async_upnp_client dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from async_upnp_client.exceptions import UpnpError


class TestUpnpClient:
    """Test UpnpClient class."""

    def test_init(self):
        """Test UpnpClient initialization."""
        from pywiim.upnp.client import UpnpClient

        client = UpnpClient("192.168.1.100", "http://192.168.1.100/description.xml", None)

        assert client.host == "192.168.1.100"
        assert client.description_url == "http://192.168.1.100/description.xml"
        assert client._device is None
        assert client._dmr_device is None

    @pytest.mark.asyncio
    async def test_create_http(self):
        """Test creating UPnP client with HTTP description URL."""
        from pywiim.upnp.client import UpnpClient

        with (
            patch("pywiim.upnp.client.UpnpFactory") as mock_factory,
            patch("pywiim.upnp.client.ClientSession") as _mock_session,
            patch("pywiim.upnp.client.TCPConnector") as _mock_connector,
        ):
            mock_device = MagicMock()
            mock_av_transport = MagicMock()
            mock_rendering_control = MagicMock()

            mock_device.service = MagicMock(
                side_effect=lambda x: (
                    mock_av_transport
                    if "AVTransport" in x
                    else mock_rendering_control if "RenderingControl" in x else None
                )
            )

            mock_factory_instance = MagicMock()
            mock_factory_instance.async_create_device = AsyncMock(return_value=mock_device)
            mock_factory.return_value = mock_factory_instance

            client = await UpnpClient.create("192.168.1.100", "http://192.168.1.100/description.xml")

            assert client.host == "192.168.1.100"
            assert client._device == mock_device

    @pytest.mark.asyncio
    async def test_create_https(self):
        """Test creating UPnP client with HTTPS description URL."""
        from pywiim.upnp.client import UpnpClient

        with (
            patch("pywiim.upnp.client.UpnpFactory") as mock_factory,
            patch("pywiim.upnp.client.ClientSession") as _mock_session,
            patch("pywiim.upnp.client.TCPConnector") as _mock_connector,
        ):
            mock_device = MagicMock()
            mock_av_transport = MagicMock()
            mock_rendering_control = MagicMock()

            mock_device.service = MagicMock(
                side_effect=lambda x: (
                    mock_av_transport
                    if "AVTransport" in x
                    else mock_rendering_control if "RenderingControl" in x else None
                )
            )

            mock_factory_instance = MagicMock()
            mock_factory_instance.async_create_device = AsyncMock(return_value=mock_device)
            mock_factory.return_value = mock_factory_instance

            client = await UpnpClient.create("192.168.1.100", "https://192.168.1.100/description.xml")

            assert client.host == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_av_transport_property(self):
        """Test getting AVTransport service."""
        from pywiim.upnp.client import UpnpClient

        client = UpnpClient("192.168.1.100", "http://192.168.1.100/description.xml", None)
        mock_service = MagicMock()
        client._av_transport_service = mock_service

        assert client.av_transport == mock_service

    @pytest.mark.asyncio
    async def test_rendering_control_property(self):
        """Test getting RenderingControl service."""
        from pywiim.upnp.client import UpnpClient

        client = UpnpClient("192.168.1.100", "http://192.168.1.100/description.xml", None)
        mock_service = MagicMock()
        client._rendering_control_service = mock_service

        assert client.rendering_control == mock_service

    @pytest.mark.asyncio
    async def test_notify_server_property_not_started(self):
        """Test getting notify server when not started."""
        from pywiim.upnp.client import UpnpClient

        client = UpnpClient("192.168.1.100", "http://192.168.1.100/description.xml", None)

        with pytest.raises(RuntimeError, match="notify server not started"):
            _ = client.notify_server

    @pytest.mark.asyncio
    async def test_async_subscribe_service_not_available(self):
        """Test subscribing to service that's not available."""
        from pywiim.upnp.client import UpnpClient

        client = UpnpClient("192.168.1.100", "http://192.168.1.100/description.xml", None)
        client._av_transport_service = None

        with pytest.raises(UpnpError, match="Service.*not available"):
            await client.async_subscribe("unknown_service", timeout=1800)

    @pytest.mark.asyncio
    async def test_async_subscribe_notify_server_not_started(self):
        """Test subscribing when notify server not started."""
        from pywiim.upnp.client import UpnpClient

        client = UpnpClient("192.168.1.100", "http://192.168.1.100/description.xml", None)
        client._av_transport_service = MagicMock()
        client._notify_server = None

        with pytest.raises(UpnpError, match="Notify server not started"):
            await client.async_subscribe("avtransport", timeout=1800)

    @pytest.mark.asyncio
    async def test_unwind_notify_server(self):
        """Test unwinding notify server."""
        from pywiim.upnp.client import UpnpClient

        client = UpnpClient("192.168.1.100", "http://192.168.1.100/description.xml", None)
        mock_server = MagicMock()
        mock_server.async_stop_server = AsyncMock()
        client._notify_server = mock_server

        await client.unwind_notify_server()

        assert client._notify_server is None
        mock_server.async_stop_server.assert_called_once()
