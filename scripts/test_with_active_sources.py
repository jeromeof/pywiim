#!/usr/bin/env python3
"""Comprehensive test script that tests features requiring active sources.

This script tests features that require an active source with media:
- Shuffle and repeat controls
- Next/previous track
- Source switching
- Playback controls with active media

Usage:
    # Test all devices
    python scripts/test_with_active_sources.py 192.168.1.115 192.168.1.116 192.168.1.68

    # Test specific device with specific source
    python scripts/test_with_active_sources.py --source spotify 192.168.1.115

    # Test with volume limit
    python scripts/test_with_active_sources.py --max-volume 0.10 192.168.1.115
"""

import argparse
import asyncio
import sys
from typing import Any

from pywiim.client import WiiMClient
from pywiim.exceptions import WiiMError
from pywiim.player import Player

MAX_VOLUME = 0.10  # Default 10% max volume


async def wait_for_playback(player: Player, timeout: int = 10) -> bool:
    """Wait for device to start playing, with timeout."""
    for _ in range(timeout):
        await asyncio.sleep(1.0)
        await player.refresh()
        if player.play_state in ("play", "playing", "PLAY", "buffering"):
            return True
    return False


async def test_shuffle_repeat(player: Player, max_volume: float) -> dict[str, Any]:
    """Test shuffle and repeat controls."""
    print("\n🔄 Testing Shuffle and Repeat Controls...")
    result = {"shuffle": False, "repeat": False, "errors": []}

    try:
        # Check if shuffle is supported
        if not player.shuffle_supported:
            print("   ⚠️  Shuffle not supported for current source")
            result["shuffle"] = None  # Not an error, just not supported
        else:
            # Save initial state
            initial_shuffle = player.shuffle_state
            initial_repeat = player.repeat_mode

            # Test shuffle ON
            print("   Testing shuffle ON...")
            await player.set_shuffle(True)
            await asyncio.sleep(1.0)
            await player.refresh()

            if player.shuffle_state is True:
                print("   ✅ Shuffle enabled")
                result["shuffle"] = True
            else:
                print(f"   ⚠️  Shuffle state: {player.shuffle_state}")
                result["shuffle"] = False

            # Verify repeat preserved
            if player.repeat_mode == initial_repeat:
                print(f"   ✅ Repeat preserved: {player.repeat_mode}")
            else:
                print(f"   ⚠️  Repeat changed: {initial_repeat} → {player.repeat_mode}")

            # Test shuffle OFF
            print("   Testing shuffle OFF...")
            await player.set_shuffle(False)
            await asyncio.sleep(1.0)
            await player.refresh()

            if player.shuffle_state is False:
                print("   ✅ Shuffle disabled")
            else:
                print(f"   ⚠️  Shuffle still on: {player.shuffle_state}")

            # Restore initial shuffle
            if initial_shuffle is not None:
                await player.set_shuffle(initial_shuffle)
                await asyncio.sleep(0.5)

        # Test repeat controls
        if not player.repeat_supported:
            print("   ⚠️  Repeat not supported for current source")
            result["repeat"] = None
        else:
            # Save initial state
            initial_repeat = player.repeat_mode
            initial_shuffle = player.shuffle_state

            # Test repeat ALL
            print("   Testing repeat ALL...")
            await player.set_repeat("all")
            await asyncio.sleep(1.0)
            await player.refresh()

            if player.repeat_mode == "all":
                print("   ✅ Repeat set to 'all'")
                result["repeat"] = True
            else:
                print(f"   ⚠️  Repeat mode: {player.repeat_mode}")

            # Verify shuffle preserved
            if player.shuffle_state == initial_shuffle:
                print(f"   ✅ Shuffle preserved: {player.shuffle_state}")
            else:
                print(f"   ⚠️  Shuffle changed: {initial_shuffle} → {player.shuffle_state}")

            # Test repeat ONE
            print("   Testing repeat ONE...")
            await player.set_repeat("one")
            await asyncio.sleep(1.0)
            await player.refresh()

            if player.repeat_mode == "one":
                print("   ✅ Repeat set to 'one'")
            else:
                print(f"   ⚠️  Repeat mode: {player.repeat_mode}")

            # Test repeat OFF
            print("   Testing repeat OFF...")
            await player.set_repeat("off")
            await asyncio.sleep(1.0)
            await player.refresh()

            if player.repeat_mode == "off":
                print("   ✅ Repeat set to 'off'")
            else:
                print(f"   ⚠️  Repeat mode: {player.repeat_mode}")

            # Restore initial repeat
            if initial_repeat is not None:
                await player.set_repeat(initial_repeat)
                await asyncio.sleep(0.5)

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_next_previous(player: Player, max_volume: float) -> dict[str, Any]:
    """Test next/previous track controls."""
    print("\n⏭️  Testing Next/Previous Track Controls...")
    result = {"next": False, "previous": False, "errors": []}

    try:
        # Ensure we're playing
        if player.play_state not in ("play", "playing", "PLAY"):
            print("   Starting playback...")
            await player.play()
            if not await wait_for_playback(player):
                print("   ⚠️  Cannot start playback - skipping next/previous tests")
                return result

        # Get initial track info
        await player.refresh()
        initial_title = player.media_title
        initial_position = player.media_position
        print(f"   Current track: {initial_title}")
        print(f"   Position: {initial_position}s")

        # Test next track
        print("   Testing next track...")
        try:
            await player.next_track()
            await asyncio.sleep(2.0)
            await player.refresh()

            new_title = player.media_title
            if new_title and new_title != initial_title:
                print(f"   ✅ Next track: {new_title}")
                result["next"] = True
            elif player.play_state in ("play", "playing", "PLAY", "buffering"):
                print(f"   ✅ Next command accepted (track: {new_title or 'unknown'})")
                result["next"] = True
            else:
                print(f"   ⚠️  State after next: {player.play_state}")
                result["next"] = False
        except Exception as e:
            print(f"   ❌ Next track failed: {e}")
            result["errors"].append(f"next_track: {e}")

        # Test previous track
        print("   Testing previous track...")
        try:
            await player.previous_track()
            await asyncio.sleep(2.0)
            await player.refresh()

            prev_title = player.media_title
            if prev_title:
                print(f"   ✅ Previous track: {prev_title}")
                result["previous"] = True
            elif player.play_state in ("play", "playing", "PLAY", "buffering", "pause", "PAUSE"):
                print(f"   ✅ Previous command accepted")
                result["previous"] = True
            else:
                print(f"   ⚠️  State after previous: {player.play_state}")
                result["previous"] = False
        except Exception as e:
            print(f"   ❌ Previous track failed: {e}")
            result["errors"].append(f"previous_track: {e}")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_source_switching(player: Player, max_volume: float, target_source: str | None = None) -> dict[str, Any]:
    """Test source switching."""
    print("\n📻 Testing Source Switching...")
    result = {"switched": False, "errors": []}

    try:
        # Get available sources
        available_sources = player.available_sources
        if not available_sources:
            print("   ⚠️  No sources available")
            return result

        print(f"   Available sources: {', '.join(available_sources)}")

        # Get current source
        current_source = player.source
        print(f"   Current source: {current_source}")

        # Determine target source
        if target_source:
            if target_source not in available_sources:
                print(f"   ⚠️  Target source '{target_source}' not available")
                return result
            target = target_source
        else:
            # Find an alternate source
            target = None
            for source in available_sources:
                if source != current_source:
                    target = source
                    break

        if not target:
            print("   ⚠️  No alternate source available for testing")
            return result

        print(f"   Switching to: {target}")

        # Switch source
        await player.set_source(target)
        await asyncio.sleep(3.0)  # Give device time to switch
        await player.refresh()

        new_source = player.source
        if new_source == target or (new_source and target.lower() in new_source.lower()):
            print(f"   ✅ Source switched to: {new_source}")
            result["switched"] = True
        else:
            print(f"   ⚠️  Source: {new_source} (expected: {target})")
            result["switched"] = False

        # Optionally switch back
        if current_source and current_source in available_sources:
            print(f"   Restoring source: {current_source}")
            await player.set_source(current_source)
            await asyncio.sleep(2.0)

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_device_with_active_source(
    ip: str, max_volume: float, target_source: str | None = None
) -> dict[str, Any]:
    """Test device with active source."""
    print(f"\n{'='*70}")
    print(f"Testing Device: {ip}")
    if target_source:
        print(f"Target Source: {target_source}")
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

        # Set safe volume
        if result["initial_volume"] is not None:
            safe_volume = min(
                max_volume, result["initial_volume"] if result["initial_volume"] < max_volume else max_volume
            )
            print(f"🔊 Setting volume to {safe_volume:.0%} for safe testing...")
            await player.set_volume(safe_volume)
            await asyncio.sleep(0.5)

        # Switch to target source if specified
        if target_source:
            print(f"\n📻 Switching to source: {target_source}")
            try:
                await player.set_source(target_source)
                await asyncio.sleep(3.0)
                await player.refresh()
                print(f"   Current source: {player.source}")

                # Try to start playback if not already playing
                if player.play_state not in ("play", "playing", "PLAY"):
                    print("   Starting playback...")
                    await player.play()
                    await asyncio.sleep(2.0)
                    await player.refresh()
            except Exception as e:
                print(f"   ⚠️  Source switch/playback: {e}")
                result["errors"].append(f"source_switch: {e}")

        # Check if we have active playback
        await player.refresh()
        if player.play_state in ("idle", "IDLE", "stop", "STOP", None):
            print("\n⚠️  No active playback detected.")
            print("   Please start a source (Spotify, Amazon, Bluetooth, etc.) before running tests.")
            print("   Some tests will be skipped.\n")
        else:
            print(f"\n✅ Active playback detected: {player.play_state}")
            if player.media_title:
                print(f"   Track: {player.media_title}")
            print()

        # Run tests
        result["tests"]["shuffle_repeat"] = await test_shuffle_repeat(player, max_volume)
        result["tests"]["next_previous"] = await test_next_previous(player, max_volume)
        result["tests"]["source_switching"] = await test_source_switching(player, max_volume, target_source)

        print(f"\n✅ Tests completed for {ip}")

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

        await client.close()

    return result


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test pywiim features that require active sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "device_ips",
        nargs="+",
        help="Device IP addresses to test",
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Target source to switch to (e.g., spotify, amazon, bluetooth)",
    )
    parser.add_argument(
        "--max-volume",
        type=float,
        default=MAX_VOLUME,
        help=f"Maximum volume for testing (default: {MAX_VOLUME:.0%})",
    )

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print("Testing Features Requiring Active Sources")
    print(f"{'='*70}")
    print(f"\nTesting {len(args.device_ips)} device(s)")
    print(f"Max volume: {args.max_volume:.0%}")
    if args.source:
        print(f"Target source: {args.source}")
    print("\n💡 Make sure to start a source (Spotify, Amazon, Bluetooth, etc.)")
    print("   on each device before running these tests.\n")

    results = []
    for ip in args.device_ips:
        result = await test_device_with_active_source(ip, args.max_volume, args.source)
        results.append(result)

    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}\n")

    for result in results:
        print(f"{result['ip']} ({result['device_name']}):")

        # Shuffle/Repeat
        sr = result["tests"].get("shuffle_repeat", {})
        if sr.get("shuffle") is not None:
            print(f"  Shuffle: {'✅' if sr['shuffle'] else '❌'}")
        if sr.get("repeat") is not None:
            print(f"  Repeat: {'✅' if sr['repeat'] else '❌'}")

        # Next/Previous
        np = result["tests"].get("next_previous", {})
        print(f"  Next Track: {'✅' if np.get('next') else '❌'}")
        print(f"  Previous Track: {'✅' if np.get('previous') else '❌'}")

        # Source Switching
        ss = result["tests"].get("source_switching", {})
        print(f"  Source Switching: {'✅' if ss.get('switched') else '❌'}")

        if result["errors"]:
            print(f"  Errors: {len(result['errors'])}")
            for error in result["errors"]:
                print(f"    - {error}")
        print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
