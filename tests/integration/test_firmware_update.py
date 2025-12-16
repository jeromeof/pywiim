"""Integration test for firmware update functionality.

This test requires a real WiiM device with a firmware update available.
Set the WIIM_TEST_HOST environment variable to the device IP address.

Example:
    WIIM_TEST_HOST=192.168.1.100 pytest tests/integration/test_firmware_update.py -xvs
"""

from __future__ import annotations

import asyncio
import os

import pytest

from pywiim import Player, WiiMClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_firmware_update_properties():
    """Test firmware update properties from device_info."""
    host = os.getenv("WIIM_TEST_HOST")
    if not host:
        pytest.skip("WIIM_TEST_HOST environment variable not set")

    client = WiiMClient(host)
    player = Player(client)

    await player.refresh()

    # Test properties exist
    assert hasattr(player, "firmware_update_available")
    assert hasattr(player, "latest_firmware_version")
    assert hasattr(player, "supports_firmware_install")

    # Test device_info fields
    device_info = player.device_info
    assert device_info is not None
    assert hasattr(device_info, "version_update")
    assert hasattr(device_info, "latest_version")
    assert hasattr(device_info, "firmware")

    # Test current firmware is available
    assert player.firmware is not None
    print(f"Current firmware: {player.firmware}")

    # Test update availability (may be True or False)
    update_available = player.firmware_update_available
    print(f"Update available: {update_available}")

    if update_available:
        latest = player.latest_firmware_version
        assert latest is not None
        print(f"Latest version: {latest}")
        assert latest != player.firmware

    # Test capability check
    supports_install = player.supports_firmware_install
    print(f"Supports firmware install: {supports_install}")

    if supports_install:
        # WiiM device - should support installation
        assert player.model is not None
        model_lower = player.model.lower()
        assert "wiim" in model_lower, f"Expected WiiM device, got {player.model}"

    # Test get_firmware_info() for detailed firmware information
    firmware_info = await client.get_firmware_info()
    assert isinstance(firmware_info, dict)
    assert "current_version" in firmware_info
    assert "update_available" in firmware_info
    assert firmware_info["current_version"] == player.firmware
    assert firmware_info["update_available"] == update_available

    if update_available:
        assert firmware_info.get("latest_version") is not None
        assert firmware_info["latest_version"] == player.latest_firmware_version

    print(f"Detailed firmware info: {firmware_info}")

    await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_firmware_update_check_wiim():
    """Test checking for firmware updates on WiiM device."""
    host = os.getenv("WIIM_TEST_HOST")
    if not host:
        pytest.skip("WIIM_TEST_HOST environment variable not set")

    client = WiiMClient(host)
    player = Player(client)

    await player.refresh()

    # Only test on WiiM devices
    if not player.supports_firmware_install:
        pytest.skip("Device does not support firmware installation via API")

    # Check for updates
    update_check = await player.check_for_updates_wiim()
    assert isinstance(update_check, dict)
    print(f"Update check result: {update_check}")

    await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Requires manual execution - will install firmware update")
async def test_firmware_update_install_wiim():
    """Test installing firmware update on WiiM device.

    WARNING: This test will actually install a firmware update!
    Only run this when you want to test the full installation process.

    To run:
        WIIM_TEST_HOST=192.168.1.100 pytest \
            tests/integration/test_firmware_update.py::test_firmware_update_install_wiim -xvs
    """
    host = os.getenv("WIIM_TEST_HOST")
    if not host:
        pytest.skip("WIIM_TEST_HOST environment variable not set")

    client = WiiMClient(host)
    player = Player(client)

    await player.refresh()

    # Only test on WiiM devices
    if not player.supports_firmware_install:
        pytest.skip("Device does not support firmware installation via API")

    # Check if update is available
    if not player.firmware_update_available:
        pytest.skip("No firmware update available")

    print(f"Current firmware: {player.firmware}")
    print(f"Latest firmware: {player.latest_firmware_version}")
    print("Starting firmware update installation...")
    print("WARNING: DO NOT POWER OFF THE DEVICE DURING THIS PROCESS!")

    # Start installation
    await player.install_firmware_update()

    # Monitor download progress
    print("Monitoring download progress...")
    for _ in range(30):  # Check for up to 30 seconds
        await asyncio.sleep(2)
        download_status = await player.get_update_download_status()
        print(f"Download status: {download_status}")

        # Status 30 means download and verification completed
        if download_status.get("status") == "30":
            print("Download completed!")
            break

    # Monitor installation progress
    print("Monitoring installation progress...")
    for _ in range(120):  # Check for up to 2 minutes
        try:
            await asyncio.sleep(5)
            install_status = await player.get_update_install_status()
            progress = install_status.get("progress", "0")
            print(f"Installation progress: {progress}%")

            if progress == "100":
                print("Installation completed! Device will reboot.")
                break
        except Exception as e:
            # Device may become unresponsive during installation
            print(f"Device may be installing (error expected): {e}")
            break

    print("Firmware update installation process completed.")
    print("Device should reboot automatically.")

    await client.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_firmware_update_status_monitoring():
    """Test monitoring firmware update status without installing."""
    host = os.getenv("WIIM_TEST_HOST")
    if not host:
        pytest.skip("WIIM_TEST_HOST environment variable not set")

    client = WiiMClient(host)
    player = Player(client)

    await player.refresh()

    # Only test on WiiM devices
    if not player.supports_firmware_install:
        pytest.skip("Device does not support firmware installation via API")

    # Test getting download status (may fail if no update in progress)
    try:
        download_status = await player.get_update_download_status()
        assert isinstance(download_status, dict)
        print(f"Download status: {download_status}")
    except Exception as e:
        # Expected if no update is in progress
        print(f"Download status check (expected to fail if no update in progress): {e}")

    # Test getting installation status (may fail if no update in progress)
    try:
        install_status = await player.get_update_install_status()
        assert isinstance(install_status, dict)
        print(f"Installation status: {install_status}")
    except Exception as e:
        # Expected if no update is in progress
        print(f"Installation status check (expected to fail if no update in progress): {e}")

    await client.close()
