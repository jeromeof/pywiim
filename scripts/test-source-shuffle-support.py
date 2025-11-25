#!/usr/bin/env python3
"""Test shuffle/repeat support detection for any source."""

import asyncio
import sys

from pywiim import WiiMClient
from pywiim.player import Player


async def test_source_support(ip: str) -> None:
    """Test shuffle/repeat support for currently playing source."""
    print(f"\n{'=' * 80}")
    print(f"🎵 Testing Shuffle/Repeat Support - {ip}")
    print(f"{'=' * 80}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        await player.refresh()
        
        print(f"Device: {player.name}")
        print(f"Source: {player.source}")
        print(f"Play State: {player.play_state}\n")
        
        # Get raw data
        vendor = player._status_model.vendor if player._status_model else None
        mode = player._status_model.mode if player._status_model else None
        loop_mode = player._status_model.loop_mode if player._status_model else None
        
        print(f"📝 Raw Device Data:")
        print(f"   mode: {mode}")
        print(f"   vendor: {vendor if vendor else '(empty)'}")
        print(f"   loop: {loop_mode}\n")
        
        # Check support
        shuffle_supported = player.shuffle_supported
        repeat_supported = player.repeat_supported
        
        print(f"🔍 Library Detection:")
        print(f"   shuffle_supported: {shuffle_supported}")
        print(f"   repeat_supported: {repeat_supported}\n")
        
        if shuffle_supported:
            shuffle_state = player.shuffle_state
            repeat_mode = player.repeat_mode
            print(f"📊 Current State:")
            print(f"   shuffle: {shuffle_state}")
            print(f"   repeat: {repeat_mode}\n")
            
            print("✅ Shuffle/repeat controls available")
        else:
            print("❌ Shuffle/repeat controlled by source (not device)")
            print("   Controls should be hidden in UI\n")
        
        print(f"{'=' * 80}\n")

    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test-source-shuffle-support.py <device_ip>")
        sys.exit(1)
    
    asyncio.run(test_source_support(sys.argv[1]))

