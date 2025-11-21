#!/usr/bin/env python3
"""Test script for verifying play/pause, shuffle, and repeat controls on real WiiM devices.

This script tests the Player object's playback control methods against real hardware.

Usage:
    python scripts/test-playback-controls.py <device_ip>

Example:
    python scripts/test-playback-controls.py 192.168.1.100

Requirements:
    - Device must be on the network and accessible
    - Device should have some media ready to play (queue not empty)
    - Script will not change volume or disrupt playback permanently
"""

import asyncio
import sys
from typing import Any

from pywiim import WiiMClient
from pywiim.exceptions import WiiMError
from pywiim.player import Player


async def wait_for_state_update(player: Player, delay: float = 1.0) -> None:
    """Wait and refresh player state."""
    await asyncio.sleep(delay)
    await player.refresh()


async def test_playback_controls(ip: str) -> dict[str, Any]:
    """Test play/pause/shuffle/repeat controls on a real device."""
    print(f"\n{'='*70}")
    print(f"🎵 Testing Playback Controls on {ip}")
    print(f"{'='*70}\n")

    results = {
        "ip": ip,
        "connected": False,
        "device_info": None,
        "tests": {
            "play": None,
            "pause": None,
            "shuffle": None,
            "repeat": None,
        },
        "errors": [],
    }

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Initialize connection
        print("📋 Connecting to device...")
        await player.refresh()

        device_info = player.device_info
        if not device_info:
            raise WiiMError("Failed to get device info")

        results["device_info"] = {
            "name": player.name,
            "model": player.model,
            "firmware": player.firmware,
        }
        results["connected"] = True

        print(f"   ✓ Connected: {player.name}")
        print(f"   ✓ Model: {player.model}")
        print(f"   ✓ Firmware: {player.firmware}\n")

        # Store initial state
        initial_state = player.play_state
        initial_shuffle = player.shuffle_state
        initial_repeat = player.repeat_mode

        print("📊 Initial State:")
        print(f"   Play State: {initial_state}")
        print(f"   Shuffle: {initial_shuffle}")
        print(f"   Repeat: {initial_repeat}\n")

        # ================================================================
        # Test 1: Play Command
        # ================================================================
        print("🎯 Test 1: Play Command")
        try:
            await player.play()
            await wait_for_state_update(player, 1.5)

            new_state = player.play_state
            print("   ✓ Play command sent")
            print(f"   State after play: {new_state}")

            results["tests"]["play"] = {
                "success": True,
                "before": initial_state,
                "after": new_state,
            }
        except Exception as e:
            print(f"   ✗ Play test failed: {e}")
            results["tests"]["play"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Play test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 2: Pause Command
        # ================================================================
        print("\n🎯 Test 2: Pause Command")
        try:
            await player.pause()
            await wait_for_state_update(player, 1.5)

            new_state = player.play_state
            print("   ✓ Pause command sent")
            print(f"   State after pause: {new_state}")

            results["tests"]["pause"] = {
                "success": True,
                "after": new_state,
            }
        except Exception as e:
            print(f"   ✗ Pause test failed: {e}")
            results["tests"]["pause"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Pause test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 3: Shuffle Control
        # ================================================================
        print("\n🎯 Test 3: Shuffle Control")
        try:
            # Enable shuffle
            print("   Testing shuffle ON...")
            await player.set_shuffle(True)
            await wait_for_state_update(player, 1.5)

            shuffle_on = player.shuffle_state
            repeat_after_shuffle = player.repeat_mode
            print("   ✓ Set shuffle ON")
            print(f"   Shuffle state: {shuffle_on}")
            print(f"   Repeat preserved: {repeat_after_shuffle}")

            # Disable shuffle
            print("   Testing shuffle OFF...")
            await player.set_shuffle(False)
            await wait_for_state_update(player, 1.5)

            shuffle_off = player.shuffle_state
            repeat_after_unshuffle = player.repeat_mode
            print("   ✓ Set shuffle OFF")
            print(f"   Shuffle state: {shuffle_off}")
            print(f"   Repeat preserved: {repeat_after_unshuffle}")

            results["tests"]["shuffle"] = {
                "success": True,
                "initial": initial_shuffle,
                "after_on": shuffle_on,
                "after_off": shuffle_off,
                "repeat_preserved": repeat_after_shuffle == repeat_after_unshuffle,
            }
        except Exception as e:
            print(f"   ✗ Shuffle test failed: {e}")
            results["tests"]["shuffle"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Shuffle test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 4: Repeat Control
        # ================================================================
        print("\n🎯 Test 4: Repeat Control")
        try:
            # Test repeat "all"
            print("   Testing repeat ALL...")
            await player.set_repeat("all")
            await wait_for_state_update(player, 1.5)

            repeat_all = player.repeat_mode
            shuffle_after_repeat_all = player.shuffle_state
            print("   ✓ Set repeat ALL")
            print(f"   Repeat mode: {repeat_all}")
            print(f"   Shuffle preserved: {shuffle_after_repeat_all}")

            # Test repeat "one"
            print("   Testing repeat ONE...")
            await player.set_repeat("one")
            await wait_for_state_update(player, 1.5)

            repeat_one = player.repeat_mode
            shuffle_after_repeat_one = player.shuffle_state
            print("   ✓ Set repeat ONE")
            print(f"   Repeat mode: {repeat_one}")
            print(f"   Shuffle preserved: {shuffle_after_repeat_one}")

            # Test repeat "off"
            print("   Testing repeat OFF...")
            await player.set_repeat("off")
            await wait_for_state_update(player, 1.5)

            repeat_off = player.repeat_mode
            shuffle_after_repeat_off = player.shuffle_state
            print("   ✓ Set repeat OFF")
            print(f"   Repeat mode: {repeat_off}")
            print(f"   Shuffle preserved: {shuffle_after_repeat_off}")

            results["tests"]["repeat"] = {
                "success": True,
                "initial": initial_repeat,
                "after_all": repeat_all,
                "after_one": repeat_one,
                "after_off": repeat_off,
                "shuffle_preserved": (shuffle_after_repeat_all == shuffle_after_repeat_one == shuffle_after_repeat_off),
            }
        except Exception as e:
            print(f"   ✗ Repeat test failed: {e}")
            results["tests"]["repeat"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Repeat test: {e}")

        # ================================================================
        # Restore Initial State
        # ================================================================
        print("\n🔄 Restoring initial state...")
        try:
            if initial_shuffle is not None:
                await player.set_shuffle(initial_shuffle)
            if initial_repeat is not None:
                await player.set_repeat(initial_repeat)
            if initial_state and initial_state in ["play", "playing"]:
                await player.play()
            elif initial_state and initial_state in ["pause", "paused"]:
                await player.pause()

            print("   ✓ State restored")
        except Exception as e:
            print(f"   ⚠ Could not fully restore state: {e}")

        print(f"\n{'='*70}")
        print("✅ All tests completed!")
        print(f"{'='*70}")

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        results["errors"].append("Test interrupted")
    except Exception as e:
        results["errors"].append(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()

    return results


async def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test-playback-controls.py <device_ip>")
        print("\nExample:")
        print("  python scripts/test-playback-controls.py 192.168.1.100")
        print("\nNote: Device should have media in queue for best results")
        sys.exit(1)

    device_ip = sys.argv[1]

    # Run tests
    result = await test_playback_controls(device_ip)

    # Print summary
    print(f"\n{'='*70}")
    print("📊 TEST SUMMARY")
    print(f"{'='*70}\n")

    if result["connected"]:
        info = result["device_info"]
        print(f"Device: {info['name']} ({info['model']}) - fw: {info['firmware']}")
        print("\nTest Results:")

        for test_name, test_result in result["tests"].items():
            if test_result is None:
                status = "⊘ Not run"
            elif test_result.get("success"):
                status = "✅ Passed"
            else:
                status = f"❌ Failed - {test_result.get('error', 'Unknown error')}"

            print(f"  {test_name.ljust(15)}: {status}")

        if result["errors"]:
            print("\n⚠️  Errors encountered:")
            for error in result["errors"]:
                print(f"  • {error}")
    else:
        print(f"❌ Could not connect to {device_ip}")
        if result["errors"]:
            for error in result["errors"]:
                print(f"  Error: {error}")

    print(f"\n{'='*70}\n")

    # Exit with appropriate code
    if result["connected"] and not result["errors"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
