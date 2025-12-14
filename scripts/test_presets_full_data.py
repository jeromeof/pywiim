#!/usr/bin/env python3
"""Test presets_full_data capability on real devices.

Tests the new presets_full_data capability to verify:
- WiiM devices: presets_full_data = True (can read names/URLs)
- LinkPlay devices: presets_full_data = False (only count available)
"""

import asyncio
import sys
from typing import Any

from pywiim import Player, WiiMClient


async def test_device(host: str) -> dict[str, Any]:
    """Test preset capabilities on a device."""
    print(f"\n{'='*60}")
    print(f"Testing device: {host}")
    print(f"{'='*60}")

    results = {
        "host": host,
        "connected": False,
        "supports_presets": False,
        "presets_full_data": False,
        "max_slots": 0,
        "preset_count": 0,
        "presets": [],
        "error": None,
    }

    try:
        # Create client and player
        client = WiiMClient(host=host)
        player = Player(client)

        # Get device info
        device_info = await client.get_device_info_model()
        print(f"\nDevice Info:")
        print(f"  Name: {device_info.name}")
        print(f"  Model: {device_info.model}")
        print(f"  Firmware: {device_info.firmware}")
        print(f"  Preset Key: {device_info.preset_key}")

        # Check capabilities (will trigger detection if not already done)
        if not client._capabilities_detected:
            await client._detect_capabilities()

        results["connected"] = True
        results["supports_presets"] = player.supports_presets
        results["presets_full_data"] = player.presets_full_data

        print(f"\nCapabilities:")
        print(f"  supports_presets: {results['supports_presets']}")
        print(f"  presets_full_data: {results['presets_full_data']}")

        if not results["supports_presets"]:
            print("\n⚠️  Device does not support presets")
            await client.close()
            return results

        # Get max preset slots
        try:
            max_slots = await client.get_max_preset_slots()
            results["max_slots"] = max_slots
            print(f"\nMax Preset Slots: {max_slots}")
        except Exception as e:
            print(f"\n⚠️  Could not get max preset slots: {e}")

        # Try to get presets
        try:
            await player.refresh(full=True)
            presets = player.presets
            results["presets"] = presets or []
            results["preset_count"] = len(results["presets"])

            print(f"\nPresets:")
            if results["presets_full_data"]:
                print(f"  Capability: Full preset data (WiiM) - names and URLs available")
                if results["presets"]:
                    print(f"  Found {results['preset_count']} preset(s):")
                    for preset in results["presets"][:5]:  # Show first 5
                        name = preset.get("name", "Unnamed")
                        number = preset.get("number", "?")
                        url = preset.get("url", "")
                        print(f"    Preset {number}: {name}")
                        if url and url not in ["unknow", "unknown", "none", ""]:
                            print(f"      URL: {url[:60]}...")
                    if results["preset_count"] > 5:
                        print(f"    ... and {results['preset_count'] - 5} more")
                else:
                    print(f"  No presets configured")
            else:
                print(f"  Capability: Count only (LinkPlay) - preset names not available")
                print(f"  Max slots: {results['max_slots']}")
                print(f"  Preset list: {results['presets']} (empty - names not available)")
                print(f"  Can play presets 1-{results['max_slots']} by number")
        except Exception as e:
            print(f"\n⚠️  Error getting presets: {e}")
            results["error"] = str(e)

        # Test playing a preset if available
        if results["max_slots"] > 0:
            test_preset = 1
            print(f"\nTesting preset playback:")
            try:
                initial_state = player.play_state
                print(f"  Initial state: {initial_state}")

                await player.play_preset(test_preset)
                await asyncio.sleep(2.0)  # Give device time to start
                await player.refresh()

                new_state = player.play_state
                print(f"  After play_preset({test_preset}): {new_state}")
                print(f"  ✓ Preset playback command accepted")
            except Exception as e:
                print(f"  ✗ Error playing preset: {e}")

        await client.close()

    except Exception as e:
        print(f"\n❌ Error connecting to device: {e}")
        results["error"] = str(e)

    return results


async def main():
    """Test multiple devices."""
    devices = ["192.168.1.115", "192.168.6.50"]

    print("Testing presets_full_data capability on real devices")
    print("=" * 60)

    all_results = []
    for device in devices:
        results = await test_device(device)
        all_results.append(results)

    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for results in all_results:
        print(f"\n{results['host']}:")
        if not results["connected"]:
            print(f"  ❌ Could not connect")
            if results["error"]:
                print(f"  Error: {results['error']}")
            continue

        if not results["supports_presets"]:
            print(f"  ⊘ Presets not supported")
            continue

        print(f"  supports_presets: {results['supports_presets']}")
        print(f"  presets_full_data: {results['presets_full_data']}")
        print(f"  max_slots: {results['max_slots']}")
        print(f"  preset_count: {results['preset_count']}")

        if results["presets_full_data"]:
            print(f"  Type: WiiM (full preset data available)")
        else:
            print(f"  Type: LinkPlay (count only)")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
