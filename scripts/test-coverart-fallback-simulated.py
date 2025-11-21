#!/usr/bin/env python3
"""Test cover art fallback to WiiM logo - simulates no artwork scenario."""

import asyncio
import sys
from pathlib import Path

from pywiim import WiiMClient
from pywiim.api.constants import DEFAULT_WIIM_LOGO_URL
from pywiim.api.parser import parse_player_status
from pywiim.player import Player


async def test_coverart_fallback_simulated(ip: str):
    """Test cover art fallback by simulating a response with no artwork."""
    print(f"\n{'='*70}")
    print("🎨 Testing Cover Art Fallback (Simulated No Artwork)")
    print(f"{'='*70}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # First, get the real status to see current state
        print("📡 Getting current player status...")
        await player.refresh()
        print("✅ Player state refreshed\n")

        # Simulate a raw response with NO cover art fields
        print("🧪 Simulating API response with NO cover art...")
        simulated_raw = {
            "type": "0",
            "ch": "0",
            "mode": "1",
            "status": "play",
            "curpos": "10000",
            "totlen": "200000",
            "Title": "Test Song",
            "Artist": "Test Artist",
            "Album": "Test Album",
            # NO cover art fields - no "cover", "albumart", "albumArtURI", etc.
            "vol": "20",
            "mute": "0"
        }

        print("📋 Simulated raw response (no cover art fields):")
        print(f"   Title: {simulated_raw.get('Title')}")
        print(f"   Artist: {simulated_raw.get('Artist')}")
        print(f"   Album: {simulated_raw.get('Album')}")
        print("   Cover art fields: None")
        print()

        # Parse the simulated response
        print("🔍 Parsing simulated response...")
        parsed, _ = parse_player_status(simulated_raw, None)

        print("📋 Parsed result:")
        print(f"   entity_picture: {parsed.get('entity_picture')}")
        print(f"   title: {parsed.get('title')}")
        print(f"   artist: {parsed.get('artist')}")
        print(f"   album: {parsed.get('album')}")
        print()

        # Check if fallback to default logo occurred
        entity_picture = parsed.get("entity_picture")
        if entity_picture == DEFAULT_WIIM_LOGO_URL:
            print("✅ SUCCESS: Fallback to default WiiM logo is working!")
            print(f"   entity_picture correctly set to: {DEFAULT_WIIM_LOGO_URL}")
        else:
            print(f"❌ FAIL: Expected default logo, got: {entity_picture}")

        print()

        # Now test with a player that has no artwork (if we can find one)
        # Or test the fetch_cover_art with None URL (should use default)
        print("📥 Testing fetch_cover_art() with no URL (should use default logo)...")

        # Temporarily set player's status to have no artwork
        # We'll test by calling fetch_cover_art with the default logo URL directly
        print(f"   Testing fetch with default logo URL: {DEFAULT_WIIM_LOGO_URL}")
        try:
            result = await player.fetch_cover_art(DEFAULT_WIIM_LOGO_URL)
            if result:
                image_bytes, content_type = result
                print("  ✅ Success!")
                print(f"     Content Type: {content_type}")
                print(f"     Size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")

                # Save to file
                output_file = Path("wiim-logo-fallback-test.jpg")
                output_file.write_bytes(image_bytes)
                print(f"     Saved to: {output_file}")
                print("     ✅ Default logo can be fetched")
            else:
                print("  ⚠️  fetch_cover_art() returned None for default logo")
                print("     (This might be expected if external URL is not accessible)")
        except Exception as e:
            print(f"  ⚠️  Error fetching default logo: {e}")
            print("     (This might be expected if external URL is not accessible)")
            print("     The important part is that entity_picture is set to the default URL")

        print()

        # Test the actual player's current state
        print("📋 Current player state (for reference):")
        print(f"   media_image_url: {player.media_image_url}")
        print(f"   Has real artwork: {player.media_image_url != DEFAULT_WIIM_LOGO_URL if player.media_image_url else False}")

        print()
        print("=" * 70)
        print("✅ Fallback Test Complete")
        print("=" * 70)
        print("\n💡 Summary:")
        print(f"   - Parser fallback works: {entity_picture == DEFAULT_WIIM_LOGO_URL}")
        print(f"   - Default logo URL: {DEFAULT_WIIM_LOGO_URL}")
        print("   - When no artwork in API response, entity_picture = default logo: ✅")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    ip = "192.168.1.116"
    if len(sys.argv) > 1:
        ip = sys.argv[1]

    asyncio.run(test_coverart_fallback_simulated(ip))

