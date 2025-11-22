#!/usr/bin/env python3
"""Test script to discover WiiM Ultra headphone output mode.

This script helps identify the hardware mode number that WiiM Ultra
reports when the physical 3.5mm headphone jack is in use.

Usage:
    1. Activate venv: source .venv/bin/activate
    2. Plug headphones into WiiM Ultra front panel
    3. Select headphone output on the device
    4. Run: python3 scripts/test-headphone-mode.py YOUR_DEVICE_IP
"""

import asyncio
import sys

from pywiim import WiiMClient


async def test_headphone_mode(host: str):
    """Query audio output status to identify headphone mode."""
    print(f"Testing WiiM Ultra at {host}")
    print("=" * 60)

    async with WiiMClient(host) as client:
        # Get device info
        device_info = await client.get_device_info()
        print(f"Device Model: {device_info.get('model', 'Unknown')}")
        print(f"Firmware: {device_info.get('firmware', 'Unknown')}")
        print()

        # Get audio output status
        print("Audio Output Status:")
        print("-" * 60)
        status = await client.get_audio_output_status()

        if status:
            print(f"Full Response: {status}")
            print()

            hardware_mode = status.get("hardware")
            source = status.get("source")
            audiocast = status.get("audiocast")

            print(f"hardware field: {hardware_mode} (type: {type(hardware_mode).__name__})")
            print(f"source field:   {source} (type: {type(source).__name__})")
            print(f"audiocast field: {audiocast}")
            print()

            # Try to convert to friendly name with current mappings
            try:
                mode_int = int(hardware_mode) if isinstance(hardware_mode, str) else hardware_mode
                friendly_name = client.audio_output_mode_to_name(mode_int)
                print(f"Current Mapping: Mode {mode_int} -> '{friendly_name}'")
            except (ValueError, TypeError) as e:
                print(f"Could not convert to friendly name: {e}")

            print()
            print("=" * 60)
            print("INSTRUCTIONS:")
            print("=" * 60)
            print("1. If headphones are currently plugged in and selected:")
            print(f"   -> The 'hardware' value ({hardware_mode}) is the headphone mode")
            print()
            print("2. If NOT using headphones, please:")
            print("   a. Plug headphones into the front panel 3.5mm jack")
            print("   b. Select headphone output on the device")
            print("   c. Run this script again")
            print()
            print("3. Report the 'hardware' value in the GitHub issue:")
            print("   https://github.com/mjcumming/wiim/issues/86")
        else:
            print("⚠️  Device does not support audio output mode API")
            print("   (This feature is WiiM only, not available on Arylic devices)")


async def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python3 test-headphone-mode.py <device_ip>")
        print()
        print("Example:")
        print("  python3 scripts/test-headphone-mode.py 192.168.1.100")
        sys.exit(1)

    host = sys.argv[1]

    try:
        await test_headphone_mode(host)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
