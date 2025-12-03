#!/usr/bin/env python3
"""Test the new state properties against real devices.

Usage:
    python scripts/test_state_properties.py <device_ip>

Example:
    python scripts/test_state_properties.py 192.168.1.100
"""

import asyncio
import sys

from pywiim import Player, WiiMClient


async def test_state_properties(ip: str) -> None:
    """Test the new state properties against a real device."""
    print(f"\n{'='*60}")
    print(f"Testing STATE PROPERTIES for: {ip}")
    print(f"{'='*60}")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Refresh to get current state
        print("\n📋 Refreshing player state...")
        await player.refresh()

        device_info = player._device_info
        if device_info:
            print(f"   Device: {device_info.name} ({device_info.model})")
            print(f"   Firmware: {device_info.firmware}")

        # Test raw play_state
        print(f"\n🔍 Raw play_state: {player.play_state!r}")

        # Test new state properties
        print("\n✨ NEW STATE PROPERTIES:")
        print(f"   player.is_playing   = {player.is_playing}")
        print(f"   player.is_paused    = {player.is_paused}")
        print(f"   player.is_idle      = {player.is_idle}")
        print(f"   player.is_buffering = {player.is_buffering}")
        print(f"   player.state        = {player.state!r}")

        # Test shuffle/repeat (already existed but verify they return clean types)
        print("\n🔄 SHUFFLE/REPEAT PROPERTIES:")
        print(f"   player.shuffle_supported = {player.shuffle_supported}")
        print(f"   player.repeat_supported  = {player.repeat_supported}")
        print(f"   player.shuffle           = {player.shuffle!r} (type: {type(player.shuffle).__name__})")
        print(f"   player.repeat            = {player.repeat!r} (type: {type(player.repeat).__name__})")

        # Test capability properties
        print("\n🎯 CAPABILITY PROPERTIES:")
        print(f"   player.supports_eq           = {player.supports_eq}")
        print(f"   player.supports_presets      = {player.supports_presets}")
        print(f"   player.supports_audio_output = {player.supports_audio_output}")
        print(f"   player.supports_upnp         = {player.supports_upnp}")

        # Test transport capabilities
        print("\n🎵 TRANSPORT CAPABILITIES:")
        print(f"   player.supports_next_track     = {player.supports_next_track}")
        print(f"   player.supports_previous_track = {player.supports_previous_track}")
        print(f"   player.supports_seek           = {player.supports_seek}")

        # Verify state consistency
        print("\n✅ STATE CONSISTENCY CHECK:")
        state = player.state
        if state == "playing":
            assert player.is_playing, "state='playing' but is_playing=False!"
            print("   ✓ state='playing' matches is_playing=True")
        elif state == "paused":
            assert player.is_paused, "state='paused' but is_paused=False!"
            print("   ✓ state='paused' matches is_paused=True")
        elif state == "idle":
            assert player.is_idle, "state='idle' but is_idle=False!"
            print("   ✓ state='idle' matches is_idle=True")
        elif state == "buffering":
            assert player.is_buffering, "state='buffering' but is_buffering=False!"
            print("   ✓ state='buffering' matches is_buffering=True")

        # Verify shuffle returns bool|None (not string)
        shuffle = player.shuffle
        if shuffle is not None:
            assert isinstance(shuffle, bool), f"shuffle should be bool, got {type(shuffle)}"
            print(f"   ✓ shuffle is bool: {shuffle}")
        else:
            print("   ✓ shuffle is None (not supported for this source)")

        # Verify repeat returns normalized string|None
        repeat = player.repeat
        if repeat is not None:
            assert repeat in ("one", "all", "off"), f"repeat should be 'one'/'all'/'off', got {repeat!r}"
            print(f"   ✓ repeat is normalized: {repeat!r}")
        else:
            print("   ✓ repeat is None (not supported for this source)")

        print(f"\n{'='*60}")
        print("🎉 ALL STATE PROPERTY TESTS PASSED!")
        print(f"{'='*60}\n")

    except Exception as err:
        print(f"\n❌ Error: {err}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    device_ip = sys.argv[1]
    await test_state_properties(device_ip)


if __name__ == "__main__":
    asyncio.run(main())
