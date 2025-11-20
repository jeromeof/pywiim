#!/usr/bin/env python3
"""Test cover art fallback to WiiM logo when artwork is not available."""

import asyncio
import sys
from pathlib import Path

from pywiim import WiiMClient
from pywiim.player import Player
from pywiim.api.constants import DEFAULT_WIIM_LOGO_URL


async def test_coverart_fallback(ip: str):
    """Test cover art fallback behavior."""
    print(f"\n{'='*70}")
    print(f"🎨 Testing Cover Art Fallback on {ip}")
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
            print(f"  URL: {cover_url}")
            
            # Check if it's the default logo
            if cover_url == DEFAULT_WIIM_LOGO_URL:
                print("  ✅ Using default WiiM logo (fallback working)")
                is_fallback = True
            else:
                print("  ℹ️  Real artwork URL found")
                print("  💡 To test fallback, try stopping playback or playing a source without artwork")
                is_fallback = False
        else:
            print("  ❌ No cover art URL available")
            is_fallback = True

        print()

        # Test fetch_cover_art() - should work even with default logo
        print("📥 Testing fetch_cover_art()...")
        try:
            result = await player.fetch_cover_art()
            if result:
                image_bytes, content_type = result
                print(f"  ✅ Success!")
                print(f"     Content Type: {content_type}")
                print(f"     Size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")
                
                # Save to file for verification
                if is_fallback:
                    output_file = Path(f"coverart-fallback-{ip.replace('.', '-')}.jpg")
                else:
                    output_file = Path(f"coverart-{ip.replace('.', '-')}.jpg")
                output_file.write_bytes(image_bytes)
                print(f"     Saved to: {output_file}")
                print(f"     File exists: {output_file.exists()}")
                print(f"     File size matches: {output_file.stat().st_size == len(image_bytes)}")
                
                # Verify it's actually an image
                if content_type.startswith("image/"):
                    print(f"     ✅ Valid image file ({content_type})")
                else:
                    print(f"     ⚠️  Unexpected content type: {content_type}")
            else:
                print("  ❌ fetch_cover_art() returned None")
        except Exception as e:
            print(f"  ❌ Error fetching cover art: {e}")
            import traceback
            traceback.print_exc()

        print()

        # Test fetching the default logo directly
        print("📥 Testing direct fetch of default WiiM logo...")
        try:
            result = await player.fetch_cover_art(DEFAULT_WIIM_LOGO_URL)
            if result:
                image_bytes, content_type = result
                print(f"  ✅ Success!")
                print(f"     Content Type: {content_type}")
                print(f"     Size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")
                
                # Save to file
                output_file = Path(f"wiim-logo-direct.jpg")
                output_file.write_bytes(image_bytes)
                print(f"     Saved to: {output_file}")
                print(f"     ✅ Default logo can be fetched successfully")
            else:
                print("  ❌ Failed to fetch default logo")
        except Exception as e:
            print(f"  ❌ Error fetching default logo: {e}")
            import traceback
            traceback.print_exc()

        print()
        print("=" * 70)
        print("✅ Fallback Test Complete")
        print("=" * 70)
        print("\n💡 Summary:")
        print(f"   - Current cover art URL: {cover_url or 'None'}")
        print(f"   - Is fallback (default logo): {is_fallback if cover_url else 'N/A'}")
        print(f"   - Default logo URL: {DEFAULT_WIIM_LOGO_URL}")
        print(f"   - fetch_cover_art() works: {result is not None if 'result' in locals() else 'Not tested'}")

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
    
    asyncio.run(test_coverart_fallback(ip))

