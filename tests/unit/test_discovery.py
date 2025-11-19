"""Unit tests for device discovery.

Tests SSDP discovery, device validation, and discovery orchestration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pywiim.discovery import DiscoveredDevice, discover_devices, discover_via_ssdp, validate_device
from pywiim.exceptions import WiiMError
from pywiim.models import DeviceInfo


class TestDiscoveredDevice:
    """Test DiscoveredDevice dataclass."""

    def test_discovered_device_creation(self):
        """Test creating DiscoveredDevice."""
        device = DiscoveredDevice(
            ip="192.168.1.100",
            name="Test Device",
            model="WiiM Pro",
            firmware="5.0.1",
            mac="AA:BB:CC:DD:EE:FF",
            uuid="test-uuid",
            port=80,
            protocol="http",
            vendor="wiim",
            discovery_method="ssdp",
            validated=True,
        )

        assert device.ip == "192.168.1.100"
        assert device.name == "Test Device"
        assert device.validated is True

    def test_discovered_device_to_dict(self):
        """Test converting DiscoveredDevice to dict."""
        device = DiscoveredDevice(ip="192.168.1.100", name="Test Device")
        device_dict = device.to_dict()

        assert device_dict["ip"] == "192.168.1.100"
        assert device_dict["name"] == "Test Device"
        assert "validated" in device_dict

    def test_discovered_device_str(self):
        """Test DiscoveredDevice string representation."""
        device = DiscoveredDevice(ip="192.168.1.100", name="Test Device", model="WiiM Pro")
        device_str = str(device)

        assert "Test Device" in device_str
        assert "WiiM Pro" in device_str
        assert "192.168.1.100" in device_str


class TestDiscoverViaSSDP:
    """Test SSDP discovery."""

    @pytest.mark.asyncio
    async def test_discover_via_ssdp_no_async_upnp_client(self):
        """Test SSDP discovery when async-upnp-client is not available."""
        # Mock the module-level async_search to be None
        with patch("pywiim.discovery.async_search", None):
            devices = await discover_via_ssdp(timeout=5)
            assert devices == []

    @pytest.mark.asyncio
    async def test_discover_via_ssdp_success(self):
        """Test successful SSDP discovery."""
        mock_response = {
            "location": "http://192.168.1.100:49152/description.xml",
            "usn": "uuid:test-uuid::upnp:rootdevice",
        }

        async def mock_async_search(async_callback, timeout, search_target):
            await async_callback(mock_response)

        with patch("pywiim.discovery.async_search", mock_async_search):
            devices = await discover_via_ssdp(timeout=5)

            assert len(devices) == 1
            assert devices[0].ip == "192.168.1.100"
            assert devices[0].uuid == "test-uuid"
            assert devices[0].port == 80  # API port, not UPnP port
            assert devices[0].discovery_method == "ssdp"

    @pytest.mark.asyncio
    async def test_discover_via_ssdp_no_location(self):
        """Test SSDP discovery with response missing location."""
        mock_response = {"usn": "uuid:test-uuid"}

        async def mock_async_search(async_callback, timeout, search_target):
            await async_callback(mock_response)

        with patch("pywiim.discovery.async_search", mock_async_search):
            devices = await discover_via_ssdp(timeout=5)

            assert len(devices) == 0

    @pytest.mark.asyncio
    async def test_discover_via_ssdp_duplicate_ip(self):
        """Test SSDP discovery filtering duplicate IPs."""
        mock_response = {
            "location": "http://192.168.1.100:49152/description.xml",
            "usn": "uuid:test-uuid::upnp:rootdevice",
        }

        async def mock_async_search(async_callback, timeout, search_target):
            await async_callback(mock_response)
            await async_callback(mock_response)  # Duplicate

        with patch("pywiim.discovery.async_search", mock_async_search):
            devices = await discover_via_ssdp(timeout=5)

            assert len(devices) == 1  # Should filter duplicates

    @pytest.mark.asyncio
    async def test_discover_via_ssdp_https(self):
        """Test SSDP discovery with HTTPS location."""
        mock_response = {
            "location": "https://192.168.1.100:49152/description.xml",
            "usn": "uuid:test-uuid",
        }

        async def mock_async_search(async_callback, timeout, search_target):
            await async_callback(mock_response)

        with patch("pywiim.discovery.async_search", mock_async_search):
            devices = await discover_via_ssdp(timeout=5)

            assert devices[0].protocol == "https"

    @pytest.mark.asyncio
    async def test_discover_via_ssdp_exception_handling(self):
        """Test SSDP discovery exception handling."""

        async def mock_async_search(async_callback, timeout, search_target):
            raise Exception("Network error")

        with patch("pywiim.discovery.async_search", mock_async_search):
            devices = await discover_via_ssdp(timeout=5)

            assert devices == []


class TestValidateDevice:
    """Test device validation."""

    @pytest.mark.asyncio
    async def test_validate_device_success(self):
        """Test successful device validation."""
        device = DiscoveredDevice(ip="192.168.1.100", port=80, protocol="http")
        mock_device_info = DeviceInfo(
            uuid="test-uuid",
            name="Test Device",
            model="WiiM Pro",
            firmware="5.0.1",
            mac="AA:BB:CC:DD:EE:FF",
        )

        mock_client = MagicMock()
        mock_client.host = "192.168.1.100"
        mock_client.port = 80
        mock_client.capabilities = {"vendor": "wiim"}
        mock_client._detect_capabilities = AsyncMock()
        mock_client.get_device_info_model = AsyncMock(return_value=mock_device_info)
        mock_client.get_player_status = AsyncMock()
        mock_client.close = AsyncMock()

        with patch("pywiim.discovery.WiiMClient", return_value=mock_client):
            validated = await validate_device(device)

            assert validated.validated is True
            assert validated.name == "Test Device"
            assert validated.model == "WiiM Pro"
            assert validated.vendor == "wiim"
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_device_already_validated(self):
        """Test validating already validated device."""
        device = DiscoveredDevice(ip="192.168.1.100", validated=True)

        validated = await validate_device(device)

        assert validated.validated is True

    @pytest.mark.asyncio
    async def test_validate_device_validation_failure(self):
        """Test device validation failure."""
        device = DiscoveredDevice(ip="192.168.1.100", port=80, protocol="http")

        mock_client = MagicMock()
        mock_client.host = "192.168.1.100"
        mock_client._detect_capabilities = AsyncMock(side_effect=WiiMError("Connection failed"))
        mock_client.close = AsyncMock()

        with patch("pywiim.discovery.WiiMClient", return_value=mock_client):
            validated = await validate_device(device)

            assert validated.validated is False
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_device_client_creation_failure(self):
        """Test device validation when client creation fails."""
        device = DiscoveredDevice(ip="192.168.1.100", port=80, protocol="http")

        with patch("pywiim.discovery.WiiMClient", side_effect=Exception("Failed")):
            validated = await validate_device(device)

            assert validated.validated is False


class TestDiscoverDevices:
    """Test discover_devices orchestration."""

    @pytest.mark.asyncio
    async def test_discover_devices_ssdp_only(self):
        """Test discovering devices via SSDP only."""
        mock_device = DiscoveredDevice(ip="192.168.1.100", name="Test Device", discovery_method="ssdp", validated=True)

        async def mock_validate(device):
            device.validated = True
            return device

        with patch("pywiim.discovery.discover_via_ssdp", return_value=[mock_device]):
            with patch("pywiim.discovery.validate_device", side_effect=mock_validate):
                devices = await discover_devices(methods=["ssdp"], validate=True)

                assert len(devices) == 1
                assert devices[0].ip == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_discover_devices_no_validation(self):
        """Test discovering devices without validation."""
        mock_device = DiscoveredDevice(ip="192.168.1.100", name="Test Device", validated=False)

        with patch("pywiim.discovery.discover_via_ssdp", return_value=[mock_device]):
            devices = await discover_devices(methods=["ssdp"], validate=False)

            assert len(devices) == 1
            assert devices[0].validated is False

    @pytest.mark.asyncio
    async def test_discover_devices_filter_invalid(self):
        """Test filtering out invalid devices."""
        valid_device = DiscoveredDevice(ip="192.168.1.100", name="Valid", validated=True)
        invalid_device = DiscoveredDevice(ip="192.168.1.101", name="Invalid", validated=False)

        async def mock_validate(device):
            return device  # Return as-is

        with patch("pywiim.discovery.discover_via_ssdp", return_value=[valid_device, invalid_device]):
            with patch("pywiim.discovery.validate_device", side_effect=mock_validate):
                devices = await discover_devices(methods=["ssdp"], validate=True)

                # Should only include validated devices
                assert len(devices) == 1
                assert devices[0].validated is True

    @pytest.mark.asyncio
    async def test_discover_devices_remove_duplicates(self):
        """Test removing duplicate devices by IP."""
        device1 = DiscoveredDevice(ip="192.168.1.100", name="Device 1")
        device2 = DiscoveredDevice(ip="192.168.1.100", name="Device 2")  # Same IP

        with patch("pywiim.discovery.discover_via_ssdp", return_value=[device1, device2]):
            with patch("pywiim.discovery.validate_device", side_effect=lambda d: d):
                devices = await discover_devices(methods=["ssdp"], validate=False)

                assert len(devices) == 1  # Should remove duplicate

    @pytest.mark.asyncio
    async def test_discover_devices_default_methods(self):
        """Test discovering devices with default methods."""
        mock_device = DiscoveredDevice(ip="192.168.1.100", name="Test Device", validated=True)

        async def mock_validate(device):
            device.validated = True
            return device

        with patch("pywiim.discovery.discover_via_ssdp", return_value=[mock_device]):
            with patch("pywiim.discovery.validate_device", side_effect=mock_validate):
                devices = await discover_devices()

                assert len(devices) == 1
