"""Unit tests for WiiMClient using mocks."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pywiim.client import WiiMClient


class TestWiiMClient:
    """Test suite for WiiMClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_aiohttp_session, mock_capabilities):
        """Test client initialization."""
        client = WiiMClient(
            host="192.168.1.100",
            port=80,
            session=mock_aiohttp_session,
            capabilities=mock_capabilities,
        )

        assert client.host == "192.168.1.100"
        assert client.port == 80
        assert client.capabilities == mock_capabilities
        assert client._capabilities_detected is True

    @pytest.mark.asyncio
    async def test_client_auto_detect_capabilities(self, mock_client):
        """Test automatic capability detection."""
        from pywiim.api.base import BaseWiiMClient
        from pywiim.models import DeviceInfo

        # Reset capabilities detection flag
        mock_client._capabilities_detected = False
        mock_client._capabilities = {}

        # Mock device info
        mock_device_info = DeviceInfo(
            uuid="test-uuid",
            model="WiiM Pro",
            firmware="5.0.1",
        )

        # Mock BaseWiiMClient.get_device_info_model to return device info
        with patch.object(BaseWiiMClient, "get_device_info_model", new_callable=AsyncMock) as mock_base:
            mock_base.return_value = mock_device_info

            # Mock capability detector
            mock_client._capability_detector.detect_capabilities = AsyncMock(
                return_value={
                    "vendor": "wiim",
                    "is_wiim_device": True,
                    "response_timeout": 2.0,
                }
            )

            # Call method that triggers auto-detection
            await mock_client.get_device_info_model()

            # Verify capabilities were detected
            assert mock_client._capabilities_detected is True

    @pytest.mark.asyncio
    async def test_client_close(self, mock_client):
        """Test client cleanup."""
        # Ensure session exists and is not closed (it should from the fixture)
        if mock_client._session is not None:
            # Ensure session is marked as not closed
            mock_client._session.closed = False
            # Store reference to session before close (close sets _session to None)
            session = mock_client._session
            await mock_client.close()
            # Verify session was closed (close() checks if not closed before calling)
            session.close.assert_called_once()
            # Verify session was set to None
            assert mock_client._session is None
        else:
            # If no session, just verify close doesn't raise
            await mock_client.close()

    @pytest.mark.asyncio
    async def test_client_host_with_port(self):
        """Test client initialization with port in host string."""
        client = WiiMClient(host="192.168.1.100:8080")

        assert client.host == "192.168.1.100"
        assert client.port == 8080

    # Note: IPv6 host parsing is tested in tests/unit/api/test_base.py
    # These tests were removed due to test isolation issues when run with full suite
    # The functionality is verified in test_base.py::TestBaseWiiMClientInitialization

    @pytest.mark.asyncio
    async def test_get_device_info_with_auto_detection(self, mock_client):
        """Test get_device_info_model with automatic capability detection."""
        from pywiim.api.base import BaseWiiMClient
        from pywiim.models import DeviceInfo

        # Reset capabilities
        mock_client._capabilities_detected = False
        mock_client._capabilities = {}

        # Mock device info
        mock_device_info = DeviceInfo(
            uuid="test-uuid",
            model="WiiM Pro",
            firmware="5.0.1",
        )

        # Mock BaseWiiMClient.get_device_info_model
        with patch.object(BaseWiiMClient, "get_device_info_model", new_callable=AsyncMock) as mock_base:
            mock_base.return_value = mock_device_info

            # Mock capability detection
            mock_client._detect_capabilities = AsyncMock(return_value={"vendor": "wiim", "is_wiim_device": True})

            result = await mock_client.get_device_info_model()

            assert result == mock_device_info
            assert mock_client._detect_capabilities.called

    @pytest.mark.asyncio
    async def test_get_player_status_with_auto_detection(self, mock_client):
        """Test get_player_status with automatic capability detection."""
        from pywiim.api.base import BaseWiiMClient

        # Reset capabilities
        mock_client._capabilities_detected = False
        mock_client._capabilities = {}

        # Mock player status
        mock_status = {"play_state": "play", "volume": 50}

        # Mock BaseWiiMClient.get_player_status
        with patch.object(BaseWiiMClient, "get_player_status", new_callable=AsyncMock) as mock_base:
            mock_base.return_value = mock_status

            # Mock capability detection
            mock_client._detect_capabilities = AsyncMock(return_value={"vendor": "wiim", "is_wiim_device": True})

            result = await mock_client.get_player_status()

            assert result == mock_status
            assert mock_client._detect_capabilities.called
