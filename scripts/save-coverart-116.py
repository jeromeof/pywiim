#!/usr/bin/env python3
"""Save cover art from player at .116 as JPG file."""

import asyncio
import sys
from pathlib import Path

from pywiim import WiiMClient
from pywiim.player import Player


async def save_coverart(ip: str, output_file: str = "coverart-116.jpg"):
    """Fetch and save cover art."""
    print(f"\n📥 Fetching cover art from {ip}...\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Refresh player state
        await player.refresh()

        # Get track info
        print(f"🎵 Track: {player.media_title or 'N/A'}")
        print(f"🎤 Artist: {player.media_artist or 'N/A'}")
        print(f"💿 Album: {player.media_album or 'N/A'}")
        print(f"🖼️  Cover URL: {player.media_image_url or 'N/A'}")
        print()

        # Fetch cover art
        print("📥 Fetching cover art image...")
        result = await player.fetch_cover_art()

        if result:
            image_bytes, content_type = result
            print("✅ Success!")
            print(f"   Content Type: {content_type}")
            print(f"   Size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")

            # Save to file
            output_path = Path(output_file)
            output_path.write_bytes(image_bytes)
            print(f"\n💾 Saved to: {output_path.absolute()}")
            print(f"   File size: {output_path.stat().st_size:,} bytes")
            print("   ✅ Cover art saved successfully!")
        else:
            print("❌ Failed to fetch cover art")
            return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await client.close()

    return 0


if __name__ == "__main__":
    ip = "192.168.1.116"
    output_file = "coverart-116.jpg"

    if len(sys.argv) > 1:
        ip = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    sys.exit(asyncio.run(save_coverart(ip, output_file)))

