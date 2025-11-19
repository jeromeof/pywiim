"""Integration tests for WiiMClient with real devices.

These tests require a real WiiM device to be available on the network.
Set the WIIM_TEST_DEVICE environment variable to enable these tests.

NOTE: These are minimal smoke tests for basic API functionality.
For comprehensive testing, use the `wiim-verify` CLI tool instead.

Example:
    WIIM_TEST_DEVICE=192.168.1.100 pytest tests/integration/test_real_device.py -v

For HTTPS devices:
    WIIM_TEST_DEVICE=192.168.1.100 WIIM_TEST_HTTPS=true pytest tests/integration/test_real_device.py -v
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestRealDevice:
    """Integration tests with real WiiM devices."""

    async def test_device_connection(self, real_device_client, integration_test_marker):
        """Test basic device connection."""
        # Test that we can connect to the device
        device_info = await real_device_client.get_device_info_model()

        assert device_info is not None
        assert device_info.uuid is not None
        assert device_info.model is not None
        assert device_info.firmware is not None

    async def test_get_device_info(self, real_device_client, integration_test_marker):
        """Test getting device information."""
        device_info = await real_device_client.get_device_info_model()

        assert device_info.uuid is not None
        assert device_info.name is not None
        assert device_info.model is not None
        assert device_info.firmware is not None
        assert device_info.mac is not None

        print("\nDevice Info:")
        print(f"  Name: {device_info.name}")
        print(f"  Model: {device_info.model}")
        print(f"  Firmware: {device_info.firmware}")
        print(f"  MAC: {device_info.mac}")
        print(f"  UUID: {device_info.uuid}")

    async def test_get_player_status(self, real_device_client, integration_test_marker):
        """Test getting player status."""
        status = await real_device_client.get_player_status()

        assert status is not None
        assert "play_state" in status or "state" in status

        print("\nPlayer Status:")
        print(f"  State: {status.get('play_state') or status.get('state')}")
        print(f"  Volume: {status.get('volume')}")
        print(f"  Source: {status.get('source')}")

    async def test_capability_detection(self, real_device_client, integration_test_marker):
        """Test automatic capability detection."""
        # Reset capabilities to trigger detection
        real_device_client._capabilities_detected = False
        real_device_client._capabilities = {}

        # Trigger capability detection
        await real_device_client._detect_capabilities()

        assert real_device_client._capabilities_detected is True
        assert "vendor" in real_device_client._capabilities
        assert (
            "is_wiim_device" in real_device_client._capabilities
            or "is_legacy_device" in real_device_client._capabilities
        )

        print("\nCapabilities:")
        print(f"  Vendor: {real_device_client._capabilities.get('vendor')}")
        print(f"  Is WiiM: {real_device_client._capabilities.get('is_wiim_device')}")
        print(f"  Is Legacy: {real_device_client._capabilities.get('is_legacy_device')}")
