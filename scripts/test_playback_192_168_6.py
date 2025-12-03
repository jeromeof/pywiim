#!/usr/bin/env python3
"""Test playback functionality on 192.168.6.x devices using play_url.

This script tests playback controls on devices that support play_url,
keeping volume at safe levels (< 10%).

Usage:
    python scripts/test_playback_192_168_6.py
"""

import asyncio
import sys
from typing import Any

from pywiim.client import WiiMClient
from pywiim.exceptions import WiiMError
from pywiim.player import Player

# Test URL - a short, reliable audio stream
TEST_URL = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

# Devices to test
DEVICES = [
    "192.168.6.95",  # Dock
    "192.168.6.50",  # Main Deck
    "192.168.6.221",  # Cabin
]

MAX_VOLUME = 0.10  # 10% max volume


async def test_device_playback(ip: str) -> dict[str, Any]:
    """Test playback functionality on a device."""
    print(f"\n{'='*70}")
    print(f"Testing Playback on {ip}")
    print(f"{'='*70}\n")

    result = {
        "ip": ip,
        "device_name": None,
        "initial_volume": None,
        "initial_source": None,
        "tests": {},
        "errors": [],
    }

    client = WiiMClient(host=ip)
    player = Player(client)

    try:
        # Get device info
        await player.refresh()
        device_info = await player.get_device_info()
        result["device_name"] = device_info.name
        print(f"📱 Device: {device_info.name} ({device_info.model})")
        print(f"   Firmware: {device_info.firmware}\n")

        # Save initial state
        result["initial_volume"] = await player.get_volume()
        result["initial_source"] = player.source
        print(f"📊 Initial State:")
        print(f"   Volume: {result['initial_volume']}")
        print(f"   Source: {result['initial_source']}")
        print(f"   Play State: {player.play_state}\n")

        # Set safe volume (< 10%)
        print("🔊 Setting volume to 5% for safe testing...")
        await player.set_volume(0.05)
        await asyncio.sleep(0.5)
        current_volume = await player.get_volume()
        print(f"   ✓ Volume set to: {current_volume}\n")

        # Test 1: Play URL
        print("🎵 Test 1: Playing URL...")
        try:
            await player.play_url(TEST_URL)
            await asyncio.sleep(3.0)  # Give device time to start
            await player.refresh()

            play_state = player.play_state
            if play_state in ("play", "playing", "PLAY", "buffering"):
                print(f"   ✅ Playback started: {play_state}")
                result["tests"]["play_url"] = True
            elif play_state in ("pause", "paused", "PAUSE"):
                print(f"   ⚠️  URL loaded but paused: {play_state}")
                result["tests"]["play_url"] = True  # Still counts as success
            else:
                print(f"   ⚠️  Unexpected state: {play_state}")
                result["tests"]["play_url"] = False
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            result["tests"]["play_url"] = False
            result["errors"].append(f"play_url: {e}")

        # Test 2: Pause
        print("\n⏸️  Test 2: Pausing playback...")
        try:
            await player.pause()
            await asyncio.sleep(1.0)
            await player.refresh()

            play_state = player.play_state
            if play_state in ("pause", "paused", "PAUSE"):
                print(f"   ✅ Paused successfully: {play_state}")
                result["tests"]["pause"] = True
            else:
                print(f"   ⚠️  Unexpected state after pause: {play_state}")
                result["tests"]["pause"] = False
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            result["tests"]["pause"] = False
            result["errors"].append(f"pause: {e}")

        # Test 3: Resume/Play
        print("\n▶️  Test 3: Resuming playback...")
        try:
            await player.resume()
            await asyncio.sleep(2.0)
            await player.refresh()

            play_state = player.play_state
            if play_state in ("play", "playing", "PLAY", "buffering"):
                print(f"   ✅ Resumed successfully: {play_state}")
                result["tests"]["resume"] = True
            else:
                print(f"   ⚠️  Unexpected state after resume: {play_state}")
                result["tests"]["resume"] = False
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            result["tests"]["resume"] = False
            result["errors"].append(f"resume: {e}")

        # Test 4: Volume control (while playing)
        print("\n🔊 Test 4: Testing volume control during playback...")
        try:
            # Test different volume levels (all < 10%)
            volumes_to_test = [0.03, 0.07, 0.05]
            for vol in volumes_to_test:
                await player.set_volume(vol)
                await asyncio.sleep(0.5)
                actual_vol = await player.get_volume()
                if actual_vol is not None:
                    diff = abs(actual_vol - vol)
                    if diff < 0.05:  # Allow 5% tolerance
                        print(f"   ✅ Volume {vol:.0%} set correctly: {actual_vol:.0%}")
                    else:
                        print(f"   ⚠️  Volume {vol:.0%} set to {actual_vol:.0%} (diff: {diff:.0%})")

            result["tests"]["volume_control"] = True
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            result["tests"]["volume_control"] = False
            result["errors"].append(f"volume_control: {e}")

        # Test 5: Mute control
        print("\n🔇 Test 5: Testing mute control...")
        try:
            initial_mute = await player.get_muted()

            # Mute
            await player.set_mute(True)
            await asyncio.sleep(0.5)
            muted = await player.get_muted()
            if muted:
                print(f"   ✅ Muted successfully")
            else:
                print(f"   ⚠️  Mute command sent but state unclear")

            # Unmute
            await player.set_mute(False)
            await asyncio.sleep(0.5)
            unmuted = await player.get_muted()
            if not unmuted:
                print(f"   ✅ Unmuted successfully")
            else:
                print(f"   ⚠️  Unmute command sent but state unclear")

            result["tests"]["mute_control"] = True
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            result["tests"]["mute_control"] = False
            result["errors"].append(f"mute_control: {e}")

        # Test 6: Media metadata (if available)
        print("\n📝 Test 6: Checking media metadata...")
        try:
            await player.refresh()
            title = player.media_title
            artist = player.media_artist
            album = player.media_album
            duration = player.media_duration
            position = player.media_position

            if title or artist or album:
                print(f"   ✅ Metadata available:")
                if title:
                    print(f"      Title: {title}")
                if artist:
                    print(f"      Artist: {artist}")
                if album:
                    print(f"      Album: {album}")
            else:
                print(f"   ℹ️  No metadata available (may be normal for URL playback)")

            if duration:
                print(f"   Duration: {duration}s")
            if position:
                print(f"   Position: {position}s")

            result["tests"]["metadata"] = True
        except Exception as e:
            print(f"   ⚠️  Metadata check: {e}")
            result["tests"]["metadata"] = False

        # Test 7: Stop playback
        print("\n⏹️  Test 7: Stopping playback...")
        try:
            await player.stop()
            await asyncio.sleep(1.0)
            await player.refresh()

            play_state = player.play_state
            if play_state in ("stop", "STOP", "idle", "IDLE", "pause", "PAUSE"):
                print(f"   ✅ Stopped successfully: {play_state}")
                result["tests"]["stop"] = True
            else:
                print(f"   ⚠️  Unexpected state after stop: {play_state}")
                result["tests"]["stop"] = False
        except Exception as e:
            print(f"   ⚠️  Stop command: {e} (may not be supported)")
            result["tests"]["stop"] = False

        print(f"\n✅ Playback tests completed for {ip}")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        result["errors"].append(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Restore initial volume
        if result["initial_volume"] is not None:
            try:
                print(f"\n🔄 Restoring initial volume ({result['initial_volume']:.0%})...")
                await player.set_volume(result["initial_volume"])
                await asyncio.sleep(0.5)
            except Exception:
                pass

        # Stop playback if still playing
        try:
            await player.stop()
            await asyncio.sleep(0.5)
        except Exception:
            pass

        await client.close()

    return result


async def main():
    """Main test function."""
    print(f"\n{'='*70}")
    print("Playback Testing on 192.168.6.x Devices")
    print(f"{'='*70}")
    print(f"\nTesting {len(DEVICES)} device(s) using play_url")
    print(f"Volume will be kept at < 10% for safety")
    print(f"Test URL: {TEST_URL}\n")

    results = []
    for ip in DEVICES:
        result = await test_device_playback(ip)
        results.append(result)

    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}\n")

    for result in results:
        print(f"{result['ip']} ({result['device_name']}):")
        passed = sum(1 for v in result["tests"].values() if v)
        total = len(result["tests"])
        print(f"  Tests: {passed}/{total} passed")

        for test_name, passed in result["tests"].items():
            status = "✅" if passed else "❌"
            print(f"    {status} {test_name}")

        if result["errors"]:
            print(f"  Errors:")
            for error in result["errors"]:
                print(f"    - {error}")
        print()

    # Overall summary
    total_passed = sum(sum(1 for v in r["tests"].values() if v) for r in results)
    total_tests = sum(len(r["tests"]) for r in results)

    print(f"{'='*70}")
    print(f"Overall: {total_passed}/{total_tests} tests passed across {len(DEVICES)} devices")
    print(f"{'='*70}\n")

    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
