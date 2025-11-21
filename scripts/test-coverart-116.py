#!/usr/bin/env python3
"""Real-world test to verify cover art retrieval on player at .116."""

import asyncio
import sys
from pathlib import Path

from pywiim import WiiMClient
from pywiim.player import Player


async def test_coverart(ip: str):
    """Test cover art retrieval."""
    print(f"\n{'='*70}")
    print(f"🎨 Testing Cover Art Retrieval on {ip}")
    print(f"{'='*70}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Refresh player state
        print("📡 Refreshing player state...")
        await player.refresh()
        print("✅ Player state refreshed\n")

        # Display current track info
        print("📋 Current Track Info:")
        print(f"  Title: {player.media_title or 'N/A'}")
        print(f"  Artist: {player.media_artist or 'N/A'}")
        print(f"  Album: {player.media_album or 'N/A'}")
        print(f"  State: {player.play_state or 'N/A'}")
        print()

        # Get cover art URL
        print("🖼️  Cover Art URL:")
        cover_url = player.media_image_url
        if cover_url:
            print(f"  ✅ URL: {cover_url}")
        else:
            print("  ❌ No cover art URL available")
            return

        # Check if it's the default logo
        from pywiim.api.constants import DEFAULT_WIIM_LOGO_URL
        if cover_url == DEFAULT_WIIM_LOGO_URL:
            print("  ⚠️  Warning: Using default WiiM logo (no artwork available)")
        else:
            print("  ✅ Real artwork URL (not default logo)")

        print()

        # Fetch the actual cover art image
        print("📥 Fetching cover art image...")
        try:
            result = await player.fetch_cover_art()
            if result:
                image_bytes, content_type = result
                print("  ✅ Success!")
                print(f"     Content Type: {content_type}")
                print(f"     Size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")

                # Save to file for verification
                output_file = Path(f"coverart-{ip.replace('.', '-')}.jpg")
                output_file.write_bytes(image_bytes)
                print(f"     Saved to: {output_file}")
                print(f"     File exists: {output_file.exists()}")
                print(f"     File size matches: {output_file.stat().st_size == len(image_bytes)}")
            else:
                print("  ❌ fetch_cover_art() returned None")
        except Exception as e:
            print(f"  ❌ Error fetching cover art: {e}")
            import traceback
            traceback.print_exc()

        print()
        print("=" * 70)
        print("✅ Test Complete")
        print("=" * 70)

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

    asyncio.run(test_coverart(ip))

