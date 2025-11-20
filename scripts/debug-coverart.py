#!/usr/bin/env python3
"""Debug script to check cover art field in API response."""

import asyncio
import json
import sys

from pywiim import WiiMClient
from pywiim.player import Player


async def debug_coverart(ip: str):
    """Debug cover art fields from API."""
    print(f"\n{'='*70}")
    print(f"🔍 Debugging cover art on {ip}")
    print(f"{'='*70}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Get raw API response
        print("📡 Fetching raw API response...")
        try:
            raw_response = await client._request("/httpapi.asp?command=getPlayerStatusEx")
        except Exception as e:
            print(f"⚠️  getPlayerStatusEx failed: {e}")
            print("Trying getStatusEx fallback...")
            raw_response = await client._request("/httpapi.asp?command=getStatusEx")

        print("\n📋 Raw API Response (cover art related fields):")
        cover_fields = {}
        for key, value in raw_response.items():
            key_lower = key.lower()
            if any(
                term in key_lower
                for term in [
                    "cover",
                    "art",
                    "album",
                    "pic",
                    "image",
                    "artwork",
                    "picture",
                ]
            ):
                cover_fields[key] = value

        if cover_fields:
            print("Found cover art related fields:")
            for key, value in cover_fields.items():
                print(f"  {key}: {repr(value)} (type: {type(value).__name__})")
        else:
            print("  ⚠️  No cover art related fields found in raw response!")

        # Show full raw response (truncated)
        print("\n📋 Full Raw API Response (first 3000 chars):")
        print(json.dumps(raw_response, indent=2)[:3000])
        if len(json.dumps(raw_response, indent=2)) > 3000:
            print("\n... (truncated)\n")

        # Get parsed response
        print("\n📋 Parsed response (from get_player_status):")
        parsed = await client.get_player_status()
        print(f"  entity_picture: {parsed.get('entity_picture')}")
        print(f"  cover_url: {parsed.get('cover_url')}")
        print(f"  title: {parsed.get('title')}")
        print(f"  artist: {parsed.get('artist')}")
        print(f"  album: {parsed.get('album')}")

        # Check if getMetaInfo is available and has artwork
        print("\n📋 Checking getMetaInfo for artwork...")
        if hasattr(client, "get_meta_info"):
            try:
                meta_info = await client.get_meta_info()
                if meta_info:
                    print("  getMetaInfo response:")
                    print(json.dumps(meta_info, indent=2)[:2000])
                    if "metaData" in meta_info:
                        meta_data = meta_info["metaData"]
                        artwork_fields = {}
                        for key, value in meta_data.items():
                            key_lower = key.lower()
                            if any(
                                term in key_lower
                                for term in [
                                    "cover",
                                    "art",
                                    "album",
                                    "pic",
                                    "image",
                                    "artwork",
                                    "picture",
                                ]
                            ):
                                artwork_fields[key] = value
                        if artwork_fields:
                            print("\n  Cover art fields in metaData:")
                            for key, value in artwork_fields.items():
                                print(f"    {key}: {repr(value)}")
                        else:
                            print("  ⚠️  No cover art fields in metaData")
                else:
                    print("  ⚠️  getMetaInfo returned None or empty")
            except Exception as e:
                print(f"  ⚠️  getMetaInfo failed: {e}")
        else:
            print("  ⚠️  get_meta_info method not available on client")

        # Get player status model
        print("\n📋 PlayerStatus model:")
        await player.refresh()
        status_model = player._status_model
        if status_model:
            print(f"  entity_picture: {status_model.entity_picture}")
            print(f"  cover_url: {status_model.cover_url}")
            print(f"  title: {status_model.title}")
            print(f"  artist: {status_model.artist}")
            print(f"  album: {status_model.album}")

        # Get player properties
        print("\n📋 Player properties:")
        from pywiim.player.properties import PlayerProperties

        props = PlayerProperties(player)
        print(f"  media_image_url: {props.media_image_url}")
        print(f"  media_title: {player.media_title}")
        print(f"  media_artist: {player.media_artist}")
        print(f"  media_album: {player.media_album}")

        # Try fetching cover art
        print("\n📋 Testing fetch_cover_art():")
        try:
            result = await player.fetch_cover_art()
            if result:
                image_bytes, content_type = result
                print(f"  ✅ Success! Content type: {content_type}, Size: {len(image_bytes)} bytes")
            else:
                print("  ⚠️  fetch_cover_art() returned None")
        except Exception as e:
            print(f"  ❌ fetch_cover_art() failed: {e}")
            import traceback

            traceback.print_exc()

        print("\n" + "=" * 70)
        print("💡 Summary:")
        print("=" * 70)
        print(f"Raw response has cover art: {'Yes' if cover_fields else 'No'}")
        print(f"Parsed entity_picture: {parsed.get('entity_picture') or 'None'}")
        print(f"Player media_image_url: {props.media_image_url or 'None'}")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug-coverart.py <device_ip>")
        print("\nExample:")
        print("  python scripts/debug-coverart.py 192.168.1.116")
        sys.exit(1)

    asyncio.run(debug_coverart(sys.argv[1]))

