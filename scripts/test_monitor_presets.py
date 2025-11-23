#!/usr/bin/env python3
"""Quick test to show monitor CLI preset display."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pywiim import Player, WiiMClient


async def test_monitor_preset_display(host: str) -> None:
    """Test that monitor CLI would show presets."""
    print("Connecting to device...")
    client = WiiMClient(host)
    player = Player(client)

    print("\nRefreshing player state...")
    await player.refresh()

    print("\n=== Monitor CLI Preset Display (simulated) ===")
    presets = player.presets
    if presets:
        print("📻 Preset Stations:")
        # Show up to 10 presets, with names if available
        for preset in presets[:10]:
            preset_num = preset.get("number", "?")
            preset_name = preset.get("name", "Unnamed")
            # Show preset number and name
            print(f"   Preset {preset_num}: {preset_name}")
        if len(presets) > 10:
            print(f"   ... and {len(presets) - 10} more presets")
        print()
    elif client.capabilities.get("supports_presets", False):
        # Device supports presets but none are configured
        print("📻 Preset Stations: None configured")
        print()
    else:
        print("📻 Preset Stations: Not supported on this device")
        print()

    print("✓ Preset display test complete!")


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test monitor preset display")
    parser.add_argument("host", nargs="?", default="192.168.1.116", help="Device IP address")
    args = parser.parse_args()

    try:
        await test_monitor_preset_display(args.host)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
