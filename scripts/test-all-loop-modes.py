#!/usr/bin/env python3
"""Test all possible loop_mode combinations to discover what the device supports."""

import asyncio
import sys

from pywiim import WiiMClient
from pywiim.player import Player


async def test_all_modes(ip: str) -> None:
    """Try all shuffle/repeat combinations and see what loop_mode values we get."""
    print(f"\n{'=' * 80}")
    print(f"🔍 Testing ALL Loop Mode Combinations on {ip}")
    print(f"{'=' * 80}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        await player.refresh()
        
        print(f"Device: {player.name}")
        print(f"Model: {player.model}")
        print(f"Vendor: {player.client._capabilities.get('vendor')}\n")
        
        print("Testing each combination with 2 second delays...\n")
        
        tests = [
            ("Shuffle OFF, Repeat OFF", False, "off"),
            ("Shuffle OFF, Repeat ONE", False, "one"),
            ("Shuffle OFF, Repeat ALL", False, "all"),
            ("Shuffle ON, Repeat OFF", True, "off"),
            ("Shuffle ON, Repeat ONE", True, "one"),
            ("Shuffle ON, Repeat ALL", True, "all"),
        ]
        
        results = []
        
        for desc, shuffle, repeat in tests:
            print(f"Setting: {desc}")
            
            # Set shuffle first
            await player.set_shuffle(shuffle)
            await asyncio.sleep(0.5)
            
            # Then repeat
            await player.set_repeat(repeat)
            await asyncio.sleep(2.0)
            
            # Read back
            await player.refresh()
            loop_mode = player._status_model.loop_mode if player._status_model else None
            read_shuffle = player.shuffle_state
            read_repeat = player.repeat_mode
            
            print(f"  → loop_mode={loop_mode}, shuffle={read_shuffle}, repeat={read_repeat}\n")
            
            results.append({
                "description": desc,
                "set_shuffle": shuffle,
                "set_repeat": repeat,
                "loop_mode": loop_mode,
                "read_shuffle": read_shuffle,
                "read_repeat": read_repeat,
            })
        
        # Summary table
        print(f"{'=' * 80}")
        print("RESULTS SUMMARY")
        print(f"{'=' * 80}\n")
        print(f"{'Setting':<30} {'loop_mode':<12} {'Read Back':<25}")
        print(f"{'-' * 30} {'-' * 12} {'-' * 25}")
        
        for r in results:
            setting = r['description']
            loop_mode = r['loop_mode']
            read_back = f"shuffle={r['read_shuffle']}, repeat={r['read_repeat']}"
            print(f"{setting:<30} {str(loop_mode):<12} {read_back:<25}")
        
        print(f"\n{'=' * 80}")
        print("RECOMMENDED MAPPING:")
        print(f"{'=' * 80}\n")
        
        # Build mapping from results
        mapping = {}
        for r in results:
            key = (r['set_shuffle'], r['set_repeat'])
            mapping[key] = r['loop_mode']
        
        print("WIIM_LOOP_MODE = LoopModeMapping(")
        print(f"    normal={mapping.get((False, 'off'), '?')},  # no shuffle, no repeat")
        print(f"    repeat_one={mapping.get((False, 'one'), '?')},  # no shuffle, repeat one")
        print(f"    repeat_all={mapping.get((False, 'all'), '?')},  # no shuffle, repeat all")
        print(f"    shuffle={mapping.get((True, 'off'), '?')},  # shuffle, no repeat")
        print(f"    shuffle_repeat_one={mapping.get((True, 'one'), '?')},  # shuffle + repeat one")
        print(f"    shuffle_repeat_all={mapping.get((True, 'all'), '?')},  # shuffle + repeat all")
        print(")")
        
        print(f"\n{'=' * 80}\n")

    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test-all-loop-modes.py <device_ip>")
        print("\nThis will test all shuffle/repeat combinations to discover")
        print("the actual loop_mode values your device uses.")
        sys.exit(1)
    
    asyncio.run(test_all_modes(sys.argv[1]))

