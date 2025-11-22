#!/usr/bin/env python3
"""Inspect HLS playlist to see what metadata is available."""

import asyncio
import logging
import sys

import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

_LOGGER = logging.getLogger(__name__)

USER_AGENT = "VLC/3.0.16 LibVLC/3.0.16"


async def inspect_playlist(url: str) -> None:
    """Inspect HLS playlist for metadata."""
    _LOGGER.info("Inspecting playlist: %s", url)
    _LOGGER.info("-" * 80)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to fetch playlist: HTTP %d", response.status)
                    return

                content = await response.text()
                lines = content.splitlines()

                _LOGGER.info("Playlist content (%d lines):", len(lines))
                _LOGGER.info("")

                # Look for metadata in EXTINF tags
                for i, line in enumerate(lines[:50]):  # First 50 lines
                    line = line.strip()
                    if not line:
                        continue

                    # Check for EXTINF tags (often contain track info)
                    if line.startswith("#EXTINF"):
                        _LOGGER.info("EXTINF tag found:")
                        _LOGGER.info("  Line %d: %s", i + 1, line)
                        # EXTINF format: #EXTINF:duration,Title - Artist
                        if "," in line:
                            parts = line.split(",", 1)
                            if len(parts) > 1:
                                track_info = parts[1]
                                _LOGGER.info("  Track info: %s", track_info)
                                if " - " in track_info:
                                    artist, title = track_info.split(" - ", 1)
                                    _LOGGER.info("    Artist: %s", artist)
                                    _LOGGER.info("    Title: %s", title)
                        _LOGGER.info("")

                    # Check for other metadata tags
                    elif line.startswith("#EXT"):
                        _LOGGER.info("EXT tag: %s", line)

                # Check if it's a master playlist
                if "#EXT-X-STREAM-INF" in content:
                    _LOGGER.info("")
                    _LOGGER.info("This is a master playlist. Checking variant...")
                    # Try to parse with m3u8
                    try:
                        import m3u8

                        playlist = m3u8.loads(content, uri=url)
                        if playlist.is_variant and playlist.playlists:
                            variant = playlist.playlists[0]
                            variant_url = variant.uri
                            if not variant_url.startswith(("http://", "https://")):
                                from urllib.parse import urljoin

                                variant_url = urljoin(url, variant_url)
                            _LOGGER.info("Variant URL: %s", variant_url)
                            _LOGGER.info("")
                            await inspect_playlist(variant_url)
                    except ImportError:
                        _LOGGER.warning("m3u8 library not available")
                    except Exception as e:
                        _LOGGER.error("Error parsing playlist: %s", e)

    except Exception as e:
        _LOGGER.error("Error: %s", e, exc_info=True)


async def main() -> None:
    """Main entry point."""
    url = "https://rcavliveaudio.akamaized.net/hls/live/2006635/P-2QMTL0_MTL/adaptive_192/master.m3u8"
    await inspect_playlist(url)


if __name__ == "__main__":
    asyncio.run(main())
