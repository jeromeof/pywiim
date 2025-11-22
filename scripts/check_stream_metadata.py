#!/usr/bin/env python3
"""Quick script to check metadata in a stream URL."""

import asyncio
import logging
import sys

import aiohttp

# Add parent directory to path to import pywiim
sys.path.insert(0, str(__file__).replace("/scripts/check_stream_metadata.py", ""))

from pywiim.player.stream import get_stream_metadata

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

_LOGGER = logging.getLogger(__name__)


async def check_stream(url: str) -> None:
    """Check metadata in a stream URL."""
    _LOGGER.info("Checking metadata for: %s", url)
    _LOGGER.info("-" * 80)

    try:
        async with aiohttp.ClientSession() as session:
            metadata = await get_stream_metadata(url, session, timeout=15)

            if metadata:
                _LOGGER.info("✓ Metadata found:")
                if metadata.title:
                    _LOGGER.info("  Title: %s", metadata.title)
                else:
                    _LOGGER.info("  Title: (none)")
                if metadata.artist:
                    _LOGGER.info("  Artist: %s", metadata.artist)
                else:
                    _LOGGER.info("  Artist: (none)")
                if metadata.station_name:
                    _LOGGER.info("  Station: %s", metadata.station_name)
                else:
                    _LOGGER.info("  Station: (none)")
                if metadata.image_url:
                    _LOGGER.info("  Image: %s", metadata.image_url)
                else:
                    _LOGGER.info("  Image: (none)")

                if not metadata.title and not metadata.artist and not metadata.station_name:
                    _LOGGER.warning("  ⚠ No title, artist, or station name found")
                    _LOGGER.warning("  This stream may not embed metadata in segments")
            else:
                _LOGGER.warning("✗ No metadata extracted")
                _LOGGER.warning("  This could mean:")
                _LOGGER.warning("  - Stream doesn't embed ID3 tags in segments")
                _LOGGER.warning("  - Playlist parsing failed")
                _LOGGER.warning("  - Segment download failed")

    except Exception as e:
        _LOGGER.error("✗ Error: %s", e, exc_info=True)


async def main() -> None:
    """Main entry point."""
    url = "https://rcavliveaudio.akamaized.net/hls/live/2006635/P-2QMTL0_MTL/adaptive_192/master.m3u8"
    await check_stream(url)


if __name__ == "__main__":
    asyncio.run(main())
