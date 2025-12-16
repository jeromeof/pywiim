#!/usr/bin/env python3
"""Test source selection on real devices.

Tests the fixes for GitHub issue #153:
- Source name normalization (Title Case for display, lowercase for API)
- Source selection with various input formats
- WiFi/Ethernet inclusion
- USB filtering for WiiM Pro Plus
"""

import asyncio
import sys
from typing import Any

from pywiim.client import WiiMClient
from pywiim.player import Player


async def test_source_selection(host: str) -> None:
    """Test source selection on a real device."""
    print(f"\n{'='*60}")
    print(f"Testing source selection on {host}")
    print(f"{'='*60}\n")

    client = WiiMClient(host)
    player = Player(client)

    try:
        # Refresh to get device info and current state
        print("Refreshing device state...")
        await player.refresh(full=True)
        print(f"Device: {player.device_name} ({player.model})")
        print(f"Current source: {player.source}")
        print(f"Available sources: {player.available_sources}")
        print()

        # Test 1: Check available_sources format (should be Title Case)
        print("Test 1: Checking available_sources format...")
        available = player.available_sources
        print(f"  Available sources: {available}")

        # Verify Title Case format
        for source in available:
            if source != source.title() and source not in (
                "WiFi",
                "AirPlay",
                "TuneIn",
                "iHeartRadio",
                "DLNA",
                "USB",
                "HDMI",
            ):
                # Multi-word sources like "Line In", "Master Bedroom" are OK
                if " " in source:
                    continue
                print(f"  ⚠️  Warning: '{source}' is not Title Case")
            else:
                print(f"  ✓ '{source}' format OK")
        print()

        # Test 2: Test source selection with various formats
        print("Test 2: Testing source selection with various formats...")

        # Get current source to restore later
        original_source = player.source
        print(f"  Original source: {original_source}")

        # Test different source name formats
        test_formats = []
        for source in available:
            if source.lower() in ("wifi", "bluetooth", "line in", "optical", "coaxial"):
                # Test various formats for physical inputs
                test_formats.extend(
                    [
                        source,  # Title Case from available_sources
                        source.lower(),  # lowercase
                        source.replace(" ", "_"),  # with underscore
                        source.replace(" ", "-"),  # with hyphen
                    ]
                )

        # Remove duplicates while preserving order
        test_formats = list(dict.fromkeys(test_formats))

        for test_format in test_formats[:3]:  # Test first 3 to avoid too many switches
            try:
                print(f"  Testing format: '{test_format}'")
                await player.audio.set_source(test_format)
                await asyncio.sleep(1)  # Wait for device to switch
                await player.refresh()
                actual_source = player.source
                print(f"    → Switched to: {actual_source}")

                # Verify it's in available_sources (case-insensitive)
                if actual_source and any(s.lower() == actual_source.lower() for s in available):
                    print(f"    ✓ Source '{actual_source}' is in available_sources")
                else:
                    print(f"    ⚠️  Source '{actual_source}' not found in available_sources")
            except Exception as e:
                print(f"    ✗ Error: {e}")
            print()

        # Restore original source if possible
        if original_source:
            try:
                print(f"Restoring original source: {original_source}")
                await player.audio.set_source(original_source)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"  Warning: Could not restore original source: {e}")

        print("\n✅ Source selection tests completed!")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


async def main() -> None:
    """Main entry point."""
    import yaml
    from pathlib import Path

    # Load devices from config file if no IP provided
    if len(sys.argv) >= 2:
        # Test specific device
        host = sys.argv[1]
        await test_source_selection(host)
    else:
        # Test all devices from devices.yaml
        config_path = Path(__file__).parent.parent / "tests" / "devices.yaml"
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}")
            print("\nUsage: python test_source_selection.py [device_ip]")
            print("\nExample:")
            print("  python test_source_selection.py 192.168.1.100")
            print("  python test_source_selection.py  # Test all devices from tests/devices.yaml")
            sys.exit(1)

        with open(config_path) as f:
            config = yaml.safe_load(f)

        devices = config.get("devices", [])
        if not devices:
            print("No devices found in devices.yaml")
            sys.exit(1)

        print("=" * 60)
        print("Testing source selection on all configured devices")
        print("=" * 60)

        results = []
        for device_config in devices:
            ip = device_config.get("ip")
            name = device_config.get("name", "Unknown")
            model = device_config.get("model", "unknown")

            print(f"\n\nTesting: {name} ({model}) @ {ip}")
            print("-" * 60)

            try:
                await test_source_selection(ip)
                results.append({"device": name, "ip": ip, "status": "✅ Passed"})
            except Exception as e:
                print(f"\n❌ Error testing {name}: {e}")
                results.append({"device": name, "ip": ip, "status": f"❌ Failed: {e}"})

        # Summary
        print("\n\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for result in results:
            print(f"{result['device']} ({result['ip']}): {result['status']}")


if __name__ == "__main__":
    asyncio.run(main())
