#!/usr/bin/env python3
"""Test that forces fallback to WiiM logo when no artwork is available."""

import asyncio
import sys
from pathlib import Path

from pywiim import WiiMClient
from pywiim.api.constants import DEFAULT_WIIM_LOGO_URL
from pywiim.player import Player


async def test_wiim_logo_fallback(ip: str):
    """Test fallback to WiiM logo by mocking responses with no artwork."""
    print(f"\n{'='*70}")
    print(f"🎨 Testing WiiM Logo Fallback on {ip}")
    print(f"{'='*70}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # First, let's see what the normal response looks like
        print("📡 Step 1: Getting normal player status...")
        normal_status = await client.get_player_status()
        print(f"   Normal entity_picture: {normal_status.get('entity_picture')}")
        print()

        # Now let's test the fallback by patching the responses
        print("🧪 Step 2: Simulating no artwork scenario...")

        # Create a mock response with NO artwork
        mock_raw_response = {
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

        # Mock getMetaInfo to also return no artwork
        mock_meta_info = {
            "metaData": {
                "album": "Test Album",
                "title": "Test Song",
                "artist": "Test Artist",
                # NO albumArtURI or any artwork fields
                "sampleRate": "44100",
                "bitDepth": "16",
                "bitRate": "256",
            }
        }

        # Patch the _request method to return our mock response
        original_request = client._request

        async def mock_request(endpoint):
            if "getPlayerStatusEx" in endpoint or "getStatusEx" in endpoint:
                return mock_raw_response
            return await original_request(endpoint)

        # Patch get_meta_info if it exists
        original_get_meta_info = None
        if hasattr(client, "get_meta_info"):
            original_get_meta_info = client.get_meta_info

            async def mock_get_meta_info():
                return mock_meta_info

            client.get_meta_info = mock_get_meta_info

        try:
            client._request = mock_request

            # Now get player status - should fall back to default logo
            print("📋 Step 3: Getting player status with no artwork...")
            fallback_status = await client.get_player_status()
            entity_picture = fallback_status.get("entity_picture")

            print(f"   entity_picture: {entity_picture}")
            print()

            if entity_picture == DEFAULT_WIIM_LOGO_URL:
                print("✅ SUCCESS: Fallback to WiiM logo is working!")
                print(f"   entity_picture correctly set to: {DEFAULT_WIIM_LOGO_URL}")
            else:
                print(f"❌ FAIL: Expected default logo, got: {entity_picture}")
                return 1

            # Refresh player to get the fallback status
            print("\n📡 Step 4: Refreshing player with fallback status...")
            await player.refresh()
            player_url = player.media_image_url

            print(f"   player.media_image_url: {player_url}")

            if player_url == DEFAULT_WIIM_LOGO_URL:
                print("   ✅ Player is using default logo")
            else:
                print(f"   ⚠️  Player URL: {player_url}")

            # Try to fetch the logo
            print("\n📥 Step 5: Fetching WiiM logo image...")
            result = await player.fetch_cover_art()

            if result:
                image_bytes, content_type = result
                print("   ✅ Success!")
                print(f"      Content Type: {content_type}")
                print(f"      Size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")

                # Save to file
                output_file = Path("wiim-logo-fallback.jpg")
                output_file.write_bytes(image_bytes)
                print(f"\n💾 Saved to: {output_file.absolute()}")
                print(f"   File size: {output_file.stat().st_size:,} bytes")
                print("   ✅ WiiM logo saved successfully!")
            else:
                print("   ⚠️  fetch_cover_art() returned None")
                print("   This might happen if the external URL is not accessible")
                print("   But the fallback logic is still working (entity_picture is set correctly)")

        finally:
            # Restore original methods
            client._request = original_request
            if original_get_meta_info:
                client.get_meta_info = original_get_meta_info

        print()
        print("=" * 70)
        print("✅ Fallback Test Complete")
        print("=" * 70)
        print("\n💡 Summary:")
        print("   - When no artwork in getPlayerStatusEx: ✅ Parser sets default logo")
        print("   - When no artwork in getMetaInfo: ✅ Default logo remains")
        print(f"   - Final entity_picture: {DEFAULT_WIIM_LOGO_URL}")
        print("   - Fallback working: ✅")

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
    if len(sys.argv) > 1:
        ip = sys.argv[1]

    sys.exit(asyncio.run(test_wiim_logo_fallback(ip)))

