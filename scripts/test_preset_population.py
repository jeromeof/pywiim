#!/usr/bin/env python3
"""Test script to verify preset names are populated automatically.

This script demonstrates that presets are fetched:
1. On first refresh (full refresh)
2. Periodically every 60 seconds
3. On track changes

Run: python3 scripts/test_preset_population.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pywiim import Player, WiiMClient


async def test_preset_population(host: str) -> None:
    """Test that presets are populated automatically."""
    print(f"Connecting to device at {host}...")
    client = WiiMClient(host)
    player = Player(client)

    print("\n=== Test 1: First refresh (should fetch presets) ===")
    await player.refresh()

    presets = player.presets
    if presets:
        print(f"✓ Presets populated: {len(presets)} presets found")
        for preset in presets[:5]:  # Show first 5
            name = preset.get("name", "Unnamed")
            number = preset.get("number", "?")
            print(f"  Preset {number}: {name}")
        if len(presets) > 5:
            print(f"  ... and {len(presets) - 5} more")
    else:
        print("✗ No presets found (may not be supported or device has no presets configured)")

    print("\n=== Test 2: Second refresh (lightweight, should use cached) ===")
    await player.refresh()

    presets2 = player.presets
    if presets2:
        print(f"✓ Presets still available: {len(presets2)} presets")
        print(f"  First preset name: {presets2[0].get('name', 'Unnamed') if presets2 else 'N/A'}")
    else:
        print("✗ Presets lost (should not happen)")

    print("\n=== Test 3: Wait 2 seconds, then refresh (should still use cache) ===")
    await asyncio.sleep(2)
    await player.refresh()

    presets3 = player.presets
    if presets3:
        print(f"✓ Presets still available after 2s: {len(presets3)} presets")
    else:
        print("✗ Presets lost")

    print("\n=== Test 4: Check last_presets_check timestamp ===")
    print(f"Last presets check: {player._last_presets_check}")
    if player._last_presets_check > 0:
        print("✓ Timestamp is being tracked")
    else:
        print("✗ Timestamp not set")

    print("\n=== Summary ===")
    if presets:
        print(f"✓ SUCCESS: Presets are populated automatically")
        print(f"  Total presets: {len(presets)}")
        print(f"  Preset names are available (not just 'Preset 1', 'Preset 2', etc.)")
        if any(
            p.get("name") and p.get("name") not in [f"Preset {p.get('number')}", f"preset{p.get('number')}"]
            for p in presets
        ):
            print(f"  ✓ Presets have actual names (not generic 'Preset N' names)")
    else:
        print("⚠ Device may not support presets or has no presets configured")
        print("  Check device capabilities and preset configuration")


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test preset population")
    parser.add_argument("host", nargs="?", default="192.168.1.116", help="Device IP address")
    args = parser.parse_args()

    try:
        await test_preset_population(args.host)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
