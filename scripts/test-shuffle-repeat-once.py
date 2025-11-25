#!/usr/bin/env python3
"""Quick non-interactive shuffle/repeat test for the currently playing source.

Usage:
    python scripts/test-shuffle-repeat-once.py <device_ip> "<content_description>"

Example:
    python scripts/test-shuffle-repeat-once.py 192.168.1.115 "Spotify Album - Rumors"
"""

import asyncio
import sys

from pywiim import WiiMClient
from pywiim.player import Player


async def test_shuffle_repeat(ip: str, description: str) -> None:
    """Test shuffle/repeat on currently playing source."""
    print(f"\n{'=' * 80}")
    print(f"🎵 Testing Shuffle/Repeat on {ip}")
    print(f"{'=' * 80}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Connect
        print("📡 Connecting...")
        await player.refresh()
        
        print(f"   ✓ Device: {player.name}")
        print(f"   ✓ Model: {player.model}")
        print(f"   ✓ Firmware: {player.firmware}")
        print(f"   ✓ Vendor: {player.client._capabilities.get('vendor', 'unknown')}")

        source = player.source
        if not source:
            print("\n❌ No active source detected!")
            return

        print(f"\n{'─' * 80}")
        print(f"📊 Testing Source: {source}")
        print(f"📝 Content: {description}")
        print(f"{'─' * 80}\n")

        # Record initial state
        initial_shuffle = player.shuffle_state
        initial_repeat = player.repeat_mode
        initial_loop_mode = player._status_model.loop_mode if player._status_model else None
        initial_play_state = player.play_state

        print("📋 Initial State:")
        print(f"   Source: {source}")
        print(f"   Play State: {initial_play_state}")
        print(f"   Shuffle: {initial_shuffle}")
        print(f"   Repeat: {initial_repeat}")
        print(f"   Loop Mode: {initial_loop_mode}")

        # Check library prediction
        shuffle_supported = player.shuffle_supported
        repeat_supported = player.repeat_supported

        print(f"\n🔮 Library Prediction:")
        print(f"   Shuffle Supported: {shuffle_supported}")
        print(f"   Repeat Supported: {repeat_supported}")

        # Test Shuffle
        print(f"\n{'─' * 80}")
        print("🎲 Testing Shuffle Controls")
        print(f"{'─' * 80}")
        
        shuffle_works = None
        try:
            # Enable shuffle
            print("\n1️⃣  Setting shuffle ON...")
            await player.set_shuffle(True)
            await asyncio.sleep(1.5)
            await player.refresh()
            
            shuffle_on = player.shuffle_state
            loop_after_on = player._status_model.loop_mode if player._status_model else None
            repeat_after_shuffle = player.repeat_mode
            
            print(f"   ✓ Shuffle state: {shuffle_on}")
            print(f"   ✓ Loop mode: {loop_after_on}")
            print(f"   ✓ Repeat preserved: {repeat_after_shuffle == initial_repeat}")

            # Disable shuffle
            print("\n2️⃣  Setting shuffle OFF...")
            await player.set_shuffle(False)
            await asyncio.sleep(1.5)
            await player.refresh()
            
            shuffle_off = player.shuffle_state
            loop_after_off = player._status_model.loop_mode if player._status_model else None
            
            print(f"   ✓ Shuffle state: {shuffle_off}")
            print(f"   ✓ Loop mode: {loop_after_off}")
            
            # Assessment
            if shuffle_on == True and shuffle_off == False:
                shuffle_works = True
                print(f"\n   ✅ Shuffle controls WORK!")
            else:
                shuffle_works = False
                print(f"\n   ⚠️  Shuffle controls may not work (on={shuffle_on}, off={shuffle_off})")
                
        except Exception as e:
            shuffle_works = False
            print(f"\n   ❌ Shuffle test failed: {e}")

        # Test Repeat
        print(f"\n{'─' * 80}")
        print("🔁 Testing Repeat Controls")
        print(f"{'─' * 80}")
        
        repeat_works = None
        try:
            # Repeat ALL
            print("\n1️⃣  Setting repeat ALL...")
            await player.set_repeat("all")
            await asyncio.sleep(1.5)
            await player.refresh()
            
            repeat_all = player.repeat_mode
            loop_all = player._status_model.loop_mode if player._status_model else None
            shuffle_after = player.shuffle_state
            
            print(f"   ✓ Repeat mode: {repeat_all}")
            print(f"   ✓ Loop mode: {loop_all}")
            print(f"   ✓ Shuffle: {shuffle_after}")

            # Repeat ONE
            print("\n2️⃣  Setting repeat ONE...")
            await player.set_repeat("one")
            await asyncio.sleep(1.5)
            await player.refresh()
            
            repeat_one = player.repeat_mode
            loop_one = player._status_model.loop_mode if player._status_model else None
            
            print(f"   ✓ Repeat mode: {repeat_one}")
            print(f"   ✓ Loop mode: {loop_one}")

            # Repeat OFF
            print("\n3️⃣  Setting repeat OFF...")
            await player.set_repeat("off")
            await asyncio.sleep(1.5)
            await player.refresh()
            
            repeat_off = player.repeat_mode
            loop_off = player._status_model.loop_mode if player._status_model else None
            
            print(f"   ✓ Repeat mode: {repeat_off}")
            print(f"   ✓ Loop mode: {loop_off}")
            
            # Assessment
            if repeat_all == "all" and repeat_one == "one" and repeat_off == "off":
                repeat_works = True
                print(f"\n   ✅ Repeat controls WORK!")
            else:
                repeat_works = False
                print(f"\n   ⚠️  Repeat controls may not work (all={repeat_all}, one={repeat_one}, off={repeat_off})")
                
        except Exception as e:
            repeat_works = False
            print(f"\n   ❌ Repeat test failed: {e}")

        # Final Assessment
        print(f"\n{'=' * 80}")
        print("📊 FINAL ASSESSMENT")
        print(f"{'=' * 80}\n")
        
        print(f"Source: {source} - {description}\n")
        
        if shuffle_works is not None:
            shuffle_icon = "✅" if shuffle_works else "❌"
            print(f"{shuffle_icon} Shuffle: {'WORKS' if shuffle_works else 'DOES NOT WORK'}")
            if shuffle_supported != shuffle_works:
                print(f"   ⚠️  Library predicted {shuffle_supported}, but actually {'works' if shuffle_works else 'does not work'}!")
        else:
            print(f"⚠️  Shuffle: TEST FAILED")
            
        if repeat_works is not None:
            repeat_icon = "✅" if repeat_works else "❌"
            print(f"{repeat_icon} Repeat: {'WORKS' if repeat_works else 'DOES NOT WORK'}")
            if repeat_supported != repeat_works:
                print(f"   ⚠️  Library predicted {repeat_supported}, but actually {'works' if repeat_works else 'does not work'}!")
        else:
            print(f"⚠️  Repeat: TEST FAILED")

        # Restore initial state
        print(f"\n🔄 Restoring initial state...")
        try:
            if initial_shuffle is not None:
                await player.set_shuffle(initial_shuffle)
                await asyncio.sleep(0.3)
            if initial_repeat is not None:
                await player.set_repeat(initial_repeat)
                await asyncio.sleep(0.3)
            print("   ✓ State restored")
        except Exception as e:
            print(f"   ⚠️  Could not fully restore: {e}")

        print(f"\n{'=' * 80}\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


async def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/test-shuffle-repeat-once.py <device_ip> \"<content_description>\"")
        print("\nExample:")
        print('  python scripts/test-shuffle-repeat-once.py 192.168.1.115 "Spotify Album - Rumors"')
        sys.exit(1)

    device_ip = sys.argv[1]
    description = sys.argv[2]

    await test_shuffle_repeat(device_ip, description)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)

