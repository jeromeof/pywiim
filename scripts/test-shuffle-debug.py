#!/usr/bin/env python3
"""Debug what loop_mode commands are being sent."""

import asyncio
import sys

from pywiim import WiiMClient
from pywiim.api.loop_mode import get_loop_mode_mapping
from pywiim.player import Player


async def debug_shuffle_commands(ip: str) -> None:
    """Show what loop_mode values would be sent."""
    print(f"\n{'=' * 80}")
    print(f"🔍 Debug Shuffle/Repeat Commands for {ip}")
    print(f"{'=' * 80}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        await player.refresh()
        
        print(f"Device: {player.name}")
        print(f"Model: {player.model}")
        print(f"Vendor: {player.client._capabilities.get('vendor')}\n")
        
        vendor = player.client._capabilities.get('vendor')
        mapping = get_loop_mode_mapping(vendor)
        
        print("WiiM Loop Mode Mapping:")
        print(f"  normal (no shuffle, no repeat): {mapping.normal}")
        print(f"  repeat_one: {mapping.repeat_one}")
        print(f"  repeat_all: {mapping.repeat_all}")
        print(f"  shuffle (no repeat): {mapping.shuffle}")
        print(f"  shuffle + repeat_one: {mapping.shuffle_repeat_one}")
        print(f"  shuffle + repeat_all: {mapping.shuffle_repeat_all}\n")
        
        print("Current State:")
        print(f"  Loop Mode: {player._status_model.loop_mode if player._status_model else 'N/A'}")
        print(f"  Shuffle: {player.shuffle_state}")
        print(f"  Repeat: {player.repeat_mode}\n")
        
        print("Commands that WOULD be sent:")
        print(f"  set_shuffle(True) with repeat=off  → loop_mode={mapping.to_loop_mode(True, False, False)}")
        print(f"  set_shuffle(False) with repeat=off → loop_mode={mapping.to_loop_mode(False, False, False)}")
        print(f"  set_repeat('all') with shuffle=off → loop_mode={mapping.to_loop_mode(False, False, True)}")
        print(f"  set_repeat('one') with shuffle=off → loop_mode={mapping.to_loop_mode(False, True, False)}")
        print(f"  set_repeat('off') with shuffle=off → loop_mode={mapping.to_loop_mode(False, False, False)}\n")
        
        # Now actually try setting shuffle ON and watch what happens
        print(f"{'─' * 80}")
        print("🧪 Attempting to set shuffle ON...")
        print(f"{'─' * 80}\n")
        
        # Show what we're about to send
        target_loop_mode = mapping.to_loop_mode(shuffle=True, repeat_one=False, repeat_all=False)
        print(f"Will send: setPlayerCmd:loopmode:{target_loop_mode}\n")
        
        # Send it
        await player.set_shuffle(True)
        print("✓ Command sent successfully (no error)\n")
        
        # Wait and check
        await asyncio.sleep(2.0)
        await player.refresh()
        
        print("After command:")
        print(f"  Loop Mode: {player._status_model.loop_mode if player._status_model else 'N/A'}")
        print(f"  Shuffle: {player.shuffle_state}")
        print(f"  Repeat: {player.repeat_mode}\n")
        
        if player._status_model and player._status_model.loop_mode == target_loop_mode:
            print("✅ Device accepted the command and changed loop_mode!")
        else:
            print("❌ Device did NOT change loop_mode (command was ignored or rejected)")
            print(f"   Expected: {target_loop_mode}")
            print(f"   Got: {player._status_model.loop_mode if player._status_model else 'N/A'}\n")
            print("This suggests the device/source doesn't accept loop_mode changes from the API.")

        print(f"\n{'=' * 80}\n")

    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test-shuffle-debug.py <device_ip>")
        sys.exit(1)
    
    asyncio.run(debug_shuffle_commands(sys.argv[1]))

