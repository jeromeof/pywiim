#!/usr/bin/env python3
"""Debug script to check loop_mode field in API response."""

import asyncio
import json
import sys

from pywiim import WiiMClient
from pywiim.player import Player


async def debug_loop_mode(ip: str):
    """Debug loop_mode field from API."""
    print(f"\n{'='*70}")
    print(f"🔍 Debugging loop_mode on {ip}")
    print(f"{'='*70}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Get raw API response
        print("📡 Fetching raw API response...")
        raw_response = await client._request("/httpapi.asp?command=getPlayerStatusEx")

        print("\n📋 Raw API Response (first 2000 chars):")
        print(json.dumps(raw_response, indent=2)[:2000])
        print("\n... (truncated)\n")

        # Check for loop_mode related fields
        print("🔍 Checking for loop_mode related fields:")
        loop_fields = {}
        for key in raw_response.keys():
            key_lower = key.lower()
            if "loop" in key_lower or "shuffle" in key_lower or "repeat" in key_lower:
                loop_fields[key] = raw_response[key]

        if loop_fields:
            print("Found loop-related fields:")
            for key, value in loop_fields.items():
                print(f"  {key}: {value} (type: {type(value).__name__})")
        else:
            print("  ⚠️  No loop-related fields found in raw response!")

        # Get parsed response
        print("\n📋 Parsed response (from get_player_status):")
        parsed = await client.get_player_status()
        print(f"  loop_mode: {parsed.get('loop_mode')} (type: {type(parsed.get('loop_mode')).__name__})")
        print(f"  play_mode: {parsed.get('play_mode')} (type: {type(parsed.get('play_mode')).__name__})")
        print(f"  shuffle: {parsed.get('shuffle')} (type: {type(parsed.get('shuffle')).__name__})")
        print(f"  repeat: {parsed.get('repeat')} (type: {type(parsed.get('repeat')).__name__})")

        # Get player status model
        print("\n📋 PlayerStatus model:")
        await player.refresh()
        status_model = player._status_model
        if status_model:
            print(f"  loop_mode: {status_model.loop_mode} (type: {type(status_model.loop_mode).__name__})")
            print(f"  play_mode: {status_model.play_mode}")
            print(f"  shuffle: {status_model.shuffle}")
            print(f"  repeat: {status_model.repeat}")

        # Get player properties
        print("\n📋 Player properties:")
        print(f"  shuffle_state: {player.shuffle_state} (type: {type(player.shuffle_state).__name__})")
        print(f"  repeat_mode: {player.repeat_mode} (type: {type(player.repeat_mode).__name__})")

        print("\n" + "=" * 70)
        print("💡 Now change shuffle/repeat from WiiM app and run again to see if loop_mode updates")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug-loop-mode.py <device_ip>")
        print("\nExample:")
        print("  python scripts/debug-loop-mode.py 192.168.1.116")
        sys.exit(1)

    asyncio.run(debug_loop_mode(sys.argv[1]))
