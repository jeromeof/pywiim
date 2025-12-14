#!/usr/bin/env python3
"""Real-world test script for firmware update functionality.

This script tests firmware update properties and (optionally) installation
on a real WiiM device.

Usage:
    # Test properties only (safe)
    python scripts/test_firmware_update.py 192.168.1.100

    # Test installation (WARNING: will actually install update!)
    python scripts/test_firmware_update.py 192.168.1.100 --install

Requirements:
    - Real WiiM device on the network
    - Firmware update available (for installation test)
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from pywiim import Player, WiiMClient


async def test_firmware_properties(host: str) -> None:
    """Test firmware update properties."""
    print(f"\n{'='*60}")
    print(f"Testing firmware update properties on {host}")
    print(f"{'='*60}\n")

    client = WiiMClient(host)
    player = Player(client)

    try:
        await player.refresh()

        # Device info
        print("Device Information:")
        print(f"  Name: {player.name}")
        print(f"  Model: {player.model}")
        print(f"  Current Firmware: {player.firmware}")
        print(f"  Supports Firmware Install: {player.supports_firmware_install}")
        print()

        # Firmware update info
        print("Firmware Update Status:")
        print(f"  Update Available: {player.firmware_update_available}")
        print(f"  Latest Version: {player.latest_firmware_version}")

        device_info = player.device_info
        if device_info:
            print(f"  Version Update Flag: {device_info.version_update}")
            print(f"  Latest Version (raw): {device_info.latest_version}")
        print()

        if player.firmware_update_available:
            print("✅ Firmware update is available!")
            if player.latest_firmware_version:
                print(f"   Update from {player.firmware} to {player.latest_firmware_version}")
        else:
            print("ℹ️  No firmware update available")
        print()

        if player.supports_firmware_install:
            print("✅ Device supports firmware installation via API (WiiM device)")
        else:
            print("ℹ️  Device does not support firmware installation via API")
            print("   (Use reboot() method after update is downloaded)")

    finally:
        await client.close()


async def test_update_check(host: str) -> None:
    """Test checking for updates on WiiM device."""
    print(f"\n{'='*60}")
    print(f"Testing update check on {host}")
    print(f"{'='*60}\n")

    client = WiiMClient(host)
    player = Player(client)

    try:
        await player.refresh()

        if not player.supports_firmware_install:
            print("❌ Device does not support firmware installation via API")
            return

        print("Checking for firmware updates...")
        update_check = await player.check_for_updates_wiim()
        print(f"Update check result: {update_check}")

    finally:
        await client.close()


async def test_update_installation(host: str) -> None:
    """Test firmware update installation (WARNING: will actually install!)."""
    print(f"\n{'='*60}")
    print(f"FIRMWARE UPDATE INSTALLATION TEST")
    print(f"{'='*60}")
    print("⚠️  WARNING: This will actually install a firmware update!")
    print("⚠️  DO NOT POWER OFF THE DEVICE DURING THIS PROCESS!")
    print(f"{'='*60}\n")

    client = WiiMClient(host)
    player = Player(client)

    try:
        await player.refresh()

        if not player.supports_firmware_install:
            print("❌ Device does not support firmware installation via API")
            return

        if not player.firmware_update_available:
            print("❌ No firmware update available")
            return

        print(f"Current firmware: {player.firmware}")
        print(f"Latest firmware: {player.latest_firmware_version}")
        print()

        # Confirm installation (skip if stdin is not a TTY)
        import sys

        if sys.stdin.isatty():
            response = input("Do you want to proceed with installation? (yes/no): ")
            if response.lower() != "yes":
                print("Installation cancelled.")
                return
        else:
            print("Non-interactive mode: Proceeding with installation...")

        print("\nStarting firmware update installation...")
        await player.install_firmware_update()

        # Monitor download progress
        print("\nMonitoring download progress...")
        for i in range(30):  # Check for up to 30 seconds
            await asyncio.sleep(2)
            try:
                download_status = await player.get_update_download_status()
                # Handle both dict and int responses
                if isinstance(download_status, dict):
                    status = download_status.get("status", "unknown")
                else:
                    status = download_status

                # Normalize status to string for comparison
                status_str = str(status)
                print(f"  Download status: {status_str}")

                # Status 30 means download and verification completed
                if status_str == "30":
                    print("  ✅ Download completed!")
                    break
            except Exception as e:
                print(f"  Error checking download status: {e}")

        # Monitor installation progress
        print("\nMonitoring installation progress...")
        for i in range(120):  # Check for up to 2 minutes
            await asyncio.sleep(5)
            try:
                install_status = await player.get_update_install_status()
                progress = install_status.get("progress", "0")
                status = install_status.get("status", "unknown")
                print(f"  Installation: {progress}% (status: {status})")

                if progress == "100":
                    print("  ✅ Installation completed! Device will reboot.")
                    break
            except Exception as e:
                # Device may become unresponsive during installation
                print(f"  Device may be installing (error expected): {e}")
                break

        print("\n✅ Firmware update installation process completed.")
        print("   Device should reboot automatically.")

    finally:
        await client.close()


async def main() -> None:
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test firmware update functionality")
    parser.add_argument("host", help="Device IP address or hostname")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Test installation (WARNING: will actually install update!)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only test update check (WiiM devices only)",
    )

    args = parser.parse_args()

    try:
        # Always test properties first
        await test_firmware_properties(args.host)

        if args.check_only:
            await test_update_check(args.host)
        elif args.install:
            await test_update_installation(args.host)

        print("\n✅ All tests completed successfully!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
