#!/usr/bin/env python3
"""Test Spotify content-type detection for shuffle/repeat support."""

import asyncio
import sys

from pywiim import WiiMClient
from pywiim.player import Player


async def test_spotify_detection(ip: str) -> None:
    """Test that shuffle/repeat support varies by Spotify content type."""
    print(f"\n{'=' * 80}")
    print(f"🎵 Testing Spotify Content-Type Detection - {ip}")
    print(f"{'=' * 80}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        await player.refresh()
        
        print(f"Device: {player.name}")
        print(f"Source: {player.source}\n")
        
        if player.source != "spotify":
            print("⚠️  Not playing Spotify. Please start Spotify playback.")
            return
        
        # Get vendor URI
        vendor_uri = player._status_model.vendor if player._status_model else None
        
        print(f"📝 Content Info:")
        print(f"   Vendor URI: {vendor_uri}")
        
        # Detect content type
        if vendor_uri and isinstance(vendor_uri, str):
            if vendor_uri.startswith("spotify:album:"):
                content_type = "🎵 Album (Music)"
                expected_supported = True
            elif vendor_uri.startswith("spotify:playlist:"):
                content_type = "🎵 Playlist (Music/Radio)"
                expected_supported = True
            elif vendor_uri.startswith("spotify:show:"):
                content_type = "🎙️ Podcast/Audiobook (Episodic)"
                expected_supported = False
            elif vendor_uri.startswith("spotify:episode:"):
                content_type = "🎙️ Episode (Episodic)"
                expected_supported = False
            else:
                content_type = "❓ Unknown"
                expected_supported = None
            
            print(f"   Content Type: {content_type}")
            print(f"   Expected shuffle/repeat: {expected_supported}\n")
        else:
            print(f"   ⚠️  No vendor URI available\n")
            expected_supported = None
        
        # Check what pywiim reports
        shuffle_supported = player.shuffle_supported
        repeat_supported = player.repeat_supported
        
        print(f"🔍 PyWiim Detection:")
        print(f"   shuffle_supported: {shuffle_supported}")
        print(f"   repeat_supported: {repeat_supported}\n")
        
        # Verify
        if expected_supported is not None:
            if shuffle_supported == expected_supported and repeat_supported == expected_supported:
                print(f"✅ CORRECT! Content-type detection working properly!")
            else:
                print(f"❌ MISMATCH! Expected {expected_supported}, got shuffle={shuffle_supported}, repeat={repeat_supported}")
        
        print(f"\n{'=' * 80}\n")

    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test-spotify-content-types.py <device_ip>")
        print("\nTests content-type detection for Spotify:")
        print("  - Albums/Playlists → shuffle_supported should be True")
        print("  - Podcasts/Audiobooks → shuffle_supported should be False")
        sys.exit(1)
    
    asyncio.run(test_spotify_detection(sys.argv[1]))

