#!/usr/bin/env python3
"""Diagnostic script to test HLS segment metadata extraction."""

import asyncio
import sys
from io import BytesIO

import aiohttp

sys.path.insert(0, str(__file__).replace("/scripts/test_hls_segment.py", ""))

try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3NoHeaderError
except ImportError:
    print("mutagen not installed")
    sys.exit(1)

try:
    import m3u8
except ImportError:
    print("m3u8 not installed")
    sys.exit(1)


async def test_segment():
    """Test downloading and parsing a single HLS segment."""
    url = "https://rcavliveaudio.akamaized.net/hls/live/2006635/P-2QMTL0_MTL/adaptive_192/chunklist_ao.m3u8"

    async with aiohttp.ClientSession() as session:
        # Fetch playlist
        async with session.get(url) as response:
            playlist_content = await response.text()
            print("Playlist content (first 500 chars):")
            print(playlist_content[:500])
            print()

        # Parse playlist
        playlist = m3u8.loads(playlist_content, uri=url)
        print(f"Playlist type: {'variant' if playlist.is_variant else 'media'}")
        print(f"Number of segments: {len(playlist.segments)}")
        if playlist.segments:
            last_segment = playlist.segments[-1]
            segment_url = last_segment.uri
            if not segment_url.startswith(("http://", "https://")):
                from urllib.parse import urljoin

                segment_url = urljoin(url, segment_url)
            print(f"Last segment URL: {segment_url}")
            print()

            # Download segment
            print("Downloading segment...")
            async with session.get(segment_url) as response:
                segment_data = await response.read()
                print(f"Segment size: {len(segment_data)} bytes")
                print(f"First 100 bytes (hex): {segment_data[:100].hex()}")
                print()

            # Try to parse with mutagen
            print("Attempting to parse with mutagen...")
            audio_data = BytesIO(segment_data)

            # Check if segment starts with ID3 tag
            if segment_data.startswith(b"ID3"):
                print("File starts with ID3 tag")
                try:
                    from mutagen.id3 import ID3

                    # Reset BytesIO
                    audio_data.seek(0)
                    id3_tags = ID3(audio_data)
                    print(f"ID3 tags parsed: {id3_tags is not None}")
                    if id3_tags:
                        print("ID3 frames found:")
                        for frame_id, frame in id3_tags.items():
                            print(f"  {frame_id}: {frame}")
                            if hasattr(frame, "text"):
                                print(f"    Text: {frame.text}")
                except Exception as e:
                    print(f"Error parsing ID3: {type(e).__name__}: {e}")
                    import traceback

                    traceback.print_exc()

            # Try mutagen File() as fallback
            audio_data.seek(0)
            try:
                tags = MutagenFile(audio_data)
                print(f"Mutagen file type: {type(tags)}")
                print(f"Has tags: {tags is not None}")

                if tags and tags.tags:
                    print("Tags found:")
                    for key, value in tags.tags.items():
                        print(f"  {key}: {value}")
                else:
                    print("No tags found")
                    print(f"File object: {tags}")

            except ID3NoHeaderError as e:
                print(f"ID3NoHeaderError: {e}")
                print("File doesn't have ID3 header")
            except Exception as e:
                print(f"Error parsing: {type(e).__name__}: {e}")

            # Try to detect file type from magic bytes
            print()
            print("File type detection:")
            if segment_data.startswith(b"\xff\xf1") or segment_data.startswith(b"\xff\xf9"):
                print("  Detected: AAC/ADTS")
            elif segment_data.startswith(b"ID3"):
                print("  Detected: ID3 tag present")
            elif segment_data.startswith(b"\x47"):
                print("  Detected: MPEG-TS")
            else:
                print(f"  Unknown: starts with {segment_data[:4].hex()}")


if __name__ == "__main__":
    asyncio.run(test_segment())
