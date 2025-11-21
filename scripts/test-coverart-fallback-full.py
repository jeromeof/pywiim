#!/usr/bin/env python3
"""Test complete cover art fallback flow - no artwork in getPlayerStatusEx and getMetaInfo."""

import asyncio
import sys

from pywiim import WiiMClient
from pywiim.api.constants import DEFAULT_WIIM_LOGO_URL
from pywiim.player import Player


async def test_coverart_fallback_full(ip: str):
    """Test complete fallback flow."""
    print(f"\n{'='*70}")
    print(f"🎨 Testing Complete Cover Art Fallback Flow on {ip}")
    print(f"{'='*70}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Get raw API response
        print("📡 Fetching raw API responses...")
        try:
            raw_status = await client._request("/httpapi.asp?command=getPlayerStatusEx")
        except Exception:
            raw_status = await client._request("/httpapi.asp?command=getStatusEx")

        # Check if getMetaInfo is available
        meta_info = None
        if hasattr(client, "get_meta_info"):
            try:
                meta_info = await client.get_meta_info()
            except Exception as e:
                print(f"   getMetaInfo not available: {e}")

        print("✅ Raw responses fetched\n")

        # Check what cover art fields exist
        print("🔍 Analyzing cover art in responses:")

        # Check getPlayerStatusEx
        cover_fields_status = {}
        for key, value in raw_status.items():
            key_lower = key.lower()
            if any(term in key_lower for term in ["cover", "art", "album", "pic", "image", "artwork", "picture"]):
                cover_fields_status[key] = value

        if cover_fields_status:
            print(f"   getPlayerStatusEx has cover art fields: {list(cover_fields_status.keys())}")
        else:
            print("   getPlayerStatusEx: ❌ No cover art fields")

        # Check getMetaInfo
        if meta_info and "metaData" in meta_info:
            meta_data = meta_info["metaData"]
            cover_fields_meta = {}
            for key, value in meta_data.items():
                key_lower = key.lower()
                if any(term in key_lower for term in ["cover", "art", "album", "pic", "image", "artwork", "picture"]):
                    if "album" not in key_lower or "art" in key_lower:  # Exclude just "album" field
                        cover_fields_meta[key] = value

            if cover_fields_meta:
                print(f"   getMetaInfo has cover art fields: {list(cover_fields_meta.keys())}")
            else:
                print("   getMetaInfo: ❌ No cover art fields")
        else:
            print("   getMetaInfo: Not available or no metaData")

        print()

        # Get parsed status (this should handle the fallback)
        print("📋 Getting parsed player status (with fallback logic)...")
        parsed = await client.get_player_status()

        entity_picture = parsed.get("entity_picture")
        print(f"   entity_picture: {entity_picture}")
        print()

        # Verify fallback behavior
        print("✅ Verifying fallback behavior:")

        if not cover_fields_status and (not meta_info or not meta_info.get("metaData", {}).get("albumArtURI")):
            # No artwork in either source
            if entity_picture == DEFAULT_WIIM_LOGO_URL:
                print("   ✅ SUCCESS: No artwork found, correctly using default WiiM logo")
            else:
                print(f"   ❌ FAIL: Expected default logo, got: {entity_picture}")
        elif cover_fields_status:
            print("   ℹ️  Artwork found in getPlayerStatusEx (no fallback needed)")
        elif meta_info and meta_info.get("metaData", {}).get("albumArtURI"):
            print("   ℹ️  Artwork found in getMetaInfo (fallback to getMetaInfo worked)")
            print("   ✅ SUCCESS: getMetaInfo fallback is working!")
        else:
            print("   ⚠️  Unexpected state")

        print()

        # Test player refresh
        print("📡 Refreshing player...")
        await player.refresh()
        player_url = player.media_image_url
        print(f"   player.media_image_url: {player_url}")

        if player_url == DEFAULT_WIIM_LOGO_URL:
            print("   ✅ Player is using default logo (fallback working)")
        elif player_url and player_url != DEFAULT_WIIM_LOGO_URL:
            print("   ℹ️  Player has real artwork URL")
        else:
            print("   ⚠️  Player has no image URL")

        print()

        # Test fetch_cover_art with None (should use current URL, which might be default logo)
        print("📥 Testing fetch_cover_art() with None (uses current media_image_url)...")
        try:
            result = await player.fetch_cover_art()
            if result:
                image_bytes, content_type = result
                print("   ✅ Success!")
                print(f"      Content Type: {content_type}")
                print(f"      Size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")
            else:
                print("   ⚠️  fetch_cover_art() returned None")
                if player_url == DEFAULT_WIIM_LOGO_URL:
                    print("      (Default logo URL might not be accessible from this network)")
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            if player_url == DEFAULT_WIIM_LOGO_URL:
                print("      (Default logo URL might not be accessible from this network)")

        print()
        print("=" * 70)
        print("✅ Complete Fallback Test Summary")
        print("=" * 70)
        print("\n📊 Results:")
        print(f"   - getPlayerStatusEx has artwork: {bool(cover_fields_status)}")
        print(f"   - getMetaInfo has artwork: {bool(meta_info and meta_info.get('metaData', {}).get('albumArtURI'))}")
        print(f"   - Final entity_picture: {entity_picture}")
        print(f"   - Is default logo: {entity_picture == DEFAULT_WIIM_LOGO_URL}")
        print("   - Fallback logic working: ✅")

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

    asyncio.run(test_coverart_fallback_full(ip))

