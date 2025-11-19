"""Unit tests for BaseWiiMClient HTTP transport layer.

Tests protocol detection, SSL/TLS, retry logic, response parsing, and error handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from pywiim.api.base import BaseWiiMClient
from pywiim.exceptions import (
    WiiMRequestError,
    WiiMResponseError,
)


class TestBaseWiiMClientInitialization:
    """Test BaseWiiMClient initialization."""

    @pytest.mark.asyncio
    async def test_init_basic(self):
        """Test basic client initialization."""
        client = BaseWiiMClient(host="192.168.1.100")
        assert client.host == "192.168.1.100"
        assert client.port == 443  # Default HTTPS port
        assert client._host_url == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_init_with_port(self):
        """Test initialization with explicit port."""
        client = BaseWiiMClient(host="192.168.1.100", port=80)
        assert client.host == "192.168.1.100"
        assert client.port == 80

    @pytest.mark.asyncio
    async def test_init_host_with_port(self):
        """Test initialization with port in host string."""
        client = BaseWiiMClient(host="192.168.1.100:8080")
        assert client.host == "192.168.1.100"
        assert client.port == 8080
        assert client._discovered_port is True

    @pytest.mark.asyncio
    async def test_init_ipv6(self):
        """Test initialization with IPv6 address."""
        client = BaseWiiMClient(host="2001:db8::1", port=80)
        assert client.host == "2001:db8::1"
        assert client.port == 80
        assert client._host_url == "[2001:db8::1]"

    @pytest.mark.asyncio
    async def test_init_ipv6_with_port(self):
        """Test initialization with IPv6 address and port in brackets."""
        client = BaseWiiMClient(host="[2001:db8::1]:8080")
        assert client.host == "2001:db8::1"
        assert client.port == 8080
        assert client._discovered_port is True

    @pytest.mark.asyncio
    async def test_init_with_capabilities(self):
        """Test initialization with device capabilities."""
        capabilities = {
            "response_timeout": 3.0,
            "retry_count": 2,
            "protocol_priority": ["http", "https"],
        }
        client = BaseWiiMClient(host="192.168.1.100", capabilities=capabilities)
        assert client.timeout == 3.0
        assert client._capabilities == capabilities

    @pytest.mark.asyncio
    async def test_init_with_session(self):
        """Test initialization with existing session."""
        session = MagicMock(spec=aiohttp.ClientSession)
        session.closed = False
        client = BaseWiiMClient(host="192.168.1.100", session=session)
        assert client._session == session


class TestBaseWiiMClientProperties:
    """Test BaseWiiMClient properties."""

    @pytest.mark.asyncio
    async def test_host_property(self):
        """Test host property."""
        client = BaseWiiMClient(host="192.168.1.100")
        assert client.host == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_capabilities_property(self):
        """Test capabilities property."""
        capabilities = {"vendor": "wiim"}
        client = BaseWiiMClient(host="192.168.1.100", capabilities=capabilities)
        assert client.capabilities == capabilities

    @pytest.mark.asyncio
    async def test_base_url_property(self):
        """Test base_url property."""
        client = BaseWiiMClient(host="192.168.1.100")
        # Initially endpoint is None (lazy discovery)
        assert client.base_url is None
        # After setting endpoint, base_url returns it
        client._endpoint = "https://192.168.1.100:443"
        assert client.base_url == "https://192.168.1.100:443"


class TestBaseWiiMClientMetrics:
    """Test BaseWiiMClient metrics collection."""

    @pytest.mark.asyncio
    async def test_metrics_enabled_by_default(self):
        """Test metrics are enabled by default."""
        client = BaseWiiMClient(host="192.168.1.100")
        assert client._metrics_enabled is True

    @pytest.mark.asyncio
    async def test_enable_metrics(self):
        """Test enabling/disabling metrics."""
        client = BaseWiiMClient(host="192.168.1.100")
        client.enable_metrics(False)
        assert client._metrics_enabled is False

        client.enable_metrics(True)
        assert client._metrics_enabled is True

    @pytest.mark.asyncio
    async def test_api_stats_initial(self):
        """Test initial API stats."""
        client = BaseWiiMClient(host="192.168.1.100")
        stats = client.api_stats
        assert stats["metrics_enabled"] is True
        assert stats["total_requests"] == 0
        assert stats["successful_requests"] == 0
        assert stats["failed_requests"] == 0

    @pytest.mark.asyncio
    async def test_api_stats_disabled(self):
        """Test API stats when metrics disabled."""
        client = BaseWiiMClient(host="192.168.1.100")
        client.enable_metrics(False)
        stats = client.api_stats
        assert stats["metrics_enabled"] is False


class TestBaseWiiMClientRequest:
    """Test BaseWiiMClient request methods."""

    @pytest.mark.asyncio
    async def test_request_success(self, mock_aiohttp_session):
        """Test successful request."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"status": "ok"}')
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp_session.request = AsyncMock(return_value=mock_response)
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        client._endpoint = "https://192.168.1.100:443"

        # Mock SSL context
        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None

            result = await client._request("/api/status")

            assert result == {"status": "ok"}
            mock_aiohttp_session.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_retry_on_failure(self, mock_aiohttp_session):
        """Test request retries on failure."""
        # Mock response that fails first time, succeeds second
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"status": "ok"}')
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # First call fails with ClientError (retryable), second succeeds
        mock_aiohttp_session.request = AsyncMock(
            side_effect=[
                aiohttp.ClientConnectorError(MagicMock(), OSError("Connection failed")),
                mock_response,
            ]
        )
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(
            host="192.168.1.100",
            session=mock_aiohttp_session,
            capabilities={"retry_count": 2},
        )
        client._endpoint = "https://192.168.1.100:443"

        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip actual sleep
                result = await client._request("/api/status")

                assert result == {"status": "ok"}
                # Should have retried, so called at least twice
                assert mock_aiohttp_session.request.call_count >= 2

    @pytest.mark.asyncio
    async def test_request_max_retries_exceeded(self, mock_aiohttp_session):
        """Test request raises error after max retries."""
        # Mock response that always fails with retryable error
        mock_aiohttp_session.request = AsyncMock(
            side_effect=aiohttp.ClientConnectorError(MagicMock(), OSError("Connection failed"))
        )
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(
            host="192.168.1.100",
            session=mock_aiohttp_session,
            capabilities={"retry_count": 2},
        )
        client._endpoint = "https://192.168.1.100:443"

        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None
            with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip actual sleep
                with pytest.raises(WiiMRequestError) as exc_info:
                    await client._request("/api/status")

                # Error message may vary, but should indicate failure
                assert "failed" in str(exc_info.value).lower() or "attempts" in str(exc_info.value).lower()
                # Should have retried
                assert mock_aiohttp_session.request.call_count >= 2

    @pytest.mark.asyncio
    async def test_request_empty_response(self, mock_aiohttp_session):
        """Test request with empty response (non-reboot command)."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="")
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp_session.request = AsyncMock(return_value=mock_response)
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        client._endpoint = "https://192.168.1.100:443"

        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None

            result = await client._request("/api/status")

            assert result == {"raw": ""}

    @pytest.mark.asyncio
    async def test_request_ok_response(self, mock_aiohttp_session):
        """Test request with 'OK' text response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp_session.request = AsyncMock(return_value=mock_response)
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        client._endpoint = "https://192.168.1.100:443"

        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None

            result = await client._request("/api/command")

            assert result == {"raw": "OK"}

    @pytest.mark.asyncio
    async def test_request_switchmode_empty_response(self, mock_aiohttp_session):
        """Test switchmode command with empty response (returns OK)."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="")
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp_session.request = AsyncMock(return_value=mock_response)
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        client._endpoint = "https://192.168.1.100:443"

        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None

            # Test switchmode:bluetooth with empty response
            result = await client._request("/httpapi.asp?command=switchmode:bluetooth")

            # Empty response from switchmode should return success
            assert result == {"raw": "OK"}

    @pytest.mark.asyncio
    async def test_request_switchmode_non_json_response(self, mock_aiohttp_session):
        """Test switchmode command with non-JSON response (returns OK)."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="Command executed")
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp_session.request = AsyncMock(return_value=mock_response)
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        client._endpoint = "https://192.168.1.100:443"

        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None

            # Test switchmode:wifi with non-JSON response
            result = await client._request("/httpapi.asp?command=switchmode:wifi")

            # Non-JSON response from switchmode should return success
            assert result == {"raw": "OK"}

    @pytest.mark.asyncio
    async def test_request_setalarmclock_non_json_response(self, mock_aiohttp_session):
        """Test setAlarmClock command with non-JSON response (returns OK)."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp_session.request = AsyncMock(return_value=mock_response)
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        client._endpoint = "https://192.168.1.100:443"

        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None

            # Test setAlarmClock with non-JSON response (plain "OK")
            result = await client._request("/httpapi.asp?command=setAlarmClock:0:2:1:070000")

            # Non-JSON response from setAlarmClock should return success
            assert result == {"raw": "OK"}

    @pytest.mark.asyncio
    async def test_request_setalarmclock_empty_response(self, mock_aiohttp_session):
        """Test setAlarmClock command with empty response (returns OK)."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="")
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp_session.request = AsyncMock(return_value=mock_response)
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        client._endpoint = "https://192.168.1.100:443"

        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None

            # Test setAlarmClock with empty response
            result = await client._request("/httpapi.asp?command=setAlarmClock:1:1:1:080000:20250120")

            # Empty response from setAlarmClock should return success
            assert result == {"raw": "OK"}

    @pytest.mark.asyncio
    async def test_request_invalid_json(self, mock_aiohttp_session):
        """Test request with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="not json")
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp_session.request = AsyncMock(return_value=mock_response)
        mock_aiohttp_session.closed = False

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        client._endpoint = "https://192.168.1.100:443"

        with patch.object(client, "_get_ssl_context", new_callable=AsyncMock) as mock_ssl:
            mock_ssl.return_value = None

            # Invalid JSON raises WiiMResponseError (not retryable, so not wrapped)
            with pytest.raises(WiiMResponseError) as exc_info:
                await client._request("/api/status")

            # Error message should mention JSON or invalid response
            error_str = str(exc_info.value).lower()
            assert "json" in error_str or "invalid" in error_str or "response" in error_str


class TestBaseWiiMClientClose:
    """Test BaseWiiMClient cleanup."""

    @pytest.mark.asyncio
    async def test_close_with_session(self, mock_aiohttp_session):
        """Test closing client with session."""
        mock_aiohttp_session.closed = False
        mock_aiohttp_session.close = AsyncMock()

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        await client.close()

        mock_aiohttp_session.close.assert_called_once()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_close_without_session(self):
        """Test closing client without session."""
        client = BaseWiiMClient(host="192.168.1.100")
        # Should not raise error
        await client.close()

    @pytest.mark.asyncio
    async def test_close_already_closed_session(self, mock_aiohttp_session):
        """Test closing client with already closed session."""
        mock_aiohttp_session.closed = True

        client = BaseWiiMClient(host="192.168.1.100", session=mock_aiohttp_session)
        await client.close()

        # Should not call close on already closed session
        assert not hasattr(mock_aiohttp_session.close, "call_count") or mock_aiohttp_session.close.call_count == 0


class TestBaseWiiMClientPublicAPI:
    """Test BaseWiiMClient public API methods."""

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, mock_client):
        """Test validate_connection with successful connection."""
        mock_client.get_player_status = AsyncMock(return_value={"status": "ok"})

        result = await mock_client.validate_connection()

        assert result is True
        mock_client.get_player_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, mock_client):
        """Test validate_connection with failed connection."""
        from pywiim.exceptions import WiiMError

        mock_client.get_player_status = AsyncMock(side_effect=WiiMError("Connection failed"))

        result = await mock_client.validate_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_device_name_from_status(self, mock_client):
        """Test get_device_name from player status."""
        mock_client.get_player_status = AsyncMock(return_value={"DeviceName": "Test Device"})

        name = await mock_client.get_device_name()

        assert name == "Test Device"

    @pytest.mark.asyncio
    async def test_get_device_name_from_info(self, mock_client):
        """Test get_device_name from device info."""
        mock_client.get_player_status = AsyncMock(return_value={})
        mock_client.get_device_info = AsyncMock(return_value={"DeviceName": "Test Device"})

        name = await mock_client.get_device_name()

        assert name == "Test Device"

    @pytest.mark.asyncio
    async def test_get_device_name_fallback_to_ip(self, mock_client):
        """Test get_device_name falls back to IP."""
        from pywiim.exceptions import WiiMError

        mock_client.get_player_status = AsyncMock(side_effect=WiiMError("Error"))
        mock_client.get_device_info = AsyncMock(side_effect=WiiMError("Error"))
        # Ensure _host is set (it's set during initialization)
        mock_client._host = "192.168.1.100"

        name = await mock_client.get_device_name()

        assert name == "192.168.1.100"  # Default host
