#!/usr/bin/env python3
"""Test script to verify shuffle and repeat properties work correctly."""

import asyncio
import sys

from pywiim import WiiMClient
from pywiim.player import Player


async def test_shuffle_repeat(ip: str):
    """Test shuffle and repeat properties."""
    print(f"\n{'='*70}")
    print(f"🎵 Testing Shuffle & Repeat on {ip}")
    print(f"{'='*70}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Initial refresh
        print("📡 Refreshing player state...")
        await player.refresh()

        # Display current state
        print("\n📋 Current State:")
        print(f"  shuffle_state: {player.shuffle_state}")
        print(f"  repeat_mode: {player.repeat_mode}")

        # Display raw model fields
        if player._status_model:
            print("\n📋 Raw Status Model Fields:")
            print(f"  loop_mode: {player._status_model.loop_mode}")
            print(f"  play_mode: {player._status_model.play_mode}")
            print(f"  shuffle: {player._status_model.shuffle}")
            print(f"  repeat: {player._status_model.repeat}")

        # Test setting shuffle
        print("\n🔄 Testing set_shuffle(True)...")
        try:
            await player.set_shuffle(True)
            await asyncio.sleep(0.5)  # Wait for change to propagate
            await player.refresh()
            print(f"  ✓ shuffle_state after set: {player.shuffle_state}")
            print(f"  ✓ loop_mode after set: {player._status_model.loop_mode if player._status_model else 'N/A'}")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")

        # Test setting repeat
        print("\n🔄 Testing set_repeat('all')...")
        try:
            await player.set_repeat("all")
            await asyncio.sleep(0.5)  # Wait for change to propagate
            await player.refresh()
            print(f"  ✓ repeat_mode after set: {player.repeat_mode}")
            print(f"  ✓ loop_mode after set: {player._status_model.loop_mode if player._status_model else 'N/A'}")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")

        # Reset to normal
        print("\n🔄 Resetting to normal mode (shuffle off, repeat off)...")
        try:
            await player.set_shuffle(False)
            await asyncio.sleep(0.2)
            await player.set_repeat("off")
            await asyncio.sleep(0.5)
            await player.refresh()
            print(f"  ✓ shuffle_state: {player.shuffle_state}")
            print(f"  ✓ repeat_mode: {player.repeat_mode}")
            print(f"  ✓ loop_mode: {player._status_model.loop_mode if player._status_model else 'N/A'}")
        except Exception as e:
            print(f"  ⚠️  Error: {e}")

        print("\n" + "=" * 70)
        print("✅ Test complete!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test-shuffle-repeat.py <device_ip>")
        print("\nExample:")
        print("  python scripts/test-shuffle-repeat.py 192.168.1.116")
        sys.exit(1)

    asyncio.run(test_shuffle_repeat(sys.argv[1]))

