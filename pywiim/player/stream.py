"""Stream metadata extraction utilities.

This module provides functionality to extract metadata (title, artist) directly
from audio streams (Icecast/SHOUTcast) and parse playlist formats (M3U, PLS).
It is used to enrich player state when the device does not report metadata
for certain stream types (e.g., direct URL playback).
"""

from __future__ import annotations

import asyncio
import logging
import re
import struct
from dataclasses import dataclass
from typing import Final

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Constants
ICE_METADATA_HEADER: Final = "Icy-MetaData"
ICE_NAME_HEADER: Final = "icy-name"
ICE_METAINT_HEADER: Final = "icy-metaint"
USER_AGENT: Final = "VLC/3.0.16 LibVLC/3.0.16"  # Mimic VLC to ensure we get proper streams
METADATA_TIMEOUT: Final = 5  # Seconds to wait for metadata


@dataclass
class StreamMetadata:
    """Metadata extracted from a stream."""

    title: str | None = None
    artist: str | None = None
    station_name: str | None = None
    image_url: str | None = None


async def get_stream_metadata(
    url: str,
    session: aiohttp.ClientSession | None = None,
    timeout: int = METADATA_TIMEOUT,
) -> StreamMetadata | None:
    """Get metadata from a stream URL.

    This function attempts to:
    1. Follow redirects
    2. Parse playlists (M3U, PLS) to find the actual stream URL
    3. Connect to the stream requesting Icecast metadata
    4. Extract the title/artist from the metadata stream

    Args:
        url: The URL to check.
        session: Optional aiohttp session (will create one if None).
        timeout: Timeout in seconds.

    Returns:
        StreamMetadata object if successful, None otherwise.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None

    # Manage session lifecycle locally if not provided
    local_session = False
    if session is None:
        session = aiohttp.ClientSession()
        local_session = True

    try:
        # 1. Resolve redirects and playlists
        final_url = await _resolve_stream_url(url, session)
        if not final_url:
            return None

        # 2. Fetch Icecast metadata
        return await _fetch_icecast_metadata(final_url, session, timeout)

    except Exception as err:
        _LOGGER.debug("Failed to get stream metadata for %s: %s", url, err)
        return None
    finally:
        if local_session and session:
            await session.close()


async def _resolve_stream_url(url: str, session: aiohttp.ClientSession) -> str:
    """Resolve redirects and parse playlists to find the actual stream URL."""
    current_url = url
    visited = {url}

    for _ in range(5):  # Max 5 hops/resolutions
        try:
            # Check for playlist extensions first
            lower_url = current_url.lower()
            if lower_url.endswith((".m3u", ".m3u8")):
                new_url = await _parse_m3u(current_url, session)
            elif lower_url.endswith(".pls"):
                new_url = await _parse_pls(current_url, session)
            else:
                # Check for HTTP redirects via HEAD request
                async with session.head(
                    current_url,
                    allow_redirects=False,
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status in (301, 302, 303, 307, 308) and "Location" in response.headers:
                        new_url = response.headers["Location"]
                    else:
                        # It's a direct link (hopefully)
                        return current_url

            if not new_url or new_url in visited:
                return current_url

            visited.add(new_url)
            current_url = new_url

        except (aiohttp.ClientError, TimeoutError):
            return current_url

    return current_url


async def _parse_m3u(url: str, session: aiohttp.ClientSession) -> str | None:
    """Parse M3U playlist."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status != 200:
                return None
            content = await response.text()

            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and line.startswith(("http://", "https://")):
                    return line
    except Exception:
        pass
    return None


async def _parse_pls(url: str, session: aiohttp.ClientSession) -> str | None:
    """Parse PLS playlist."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status != 200:
                return None
            content = await response.text()

            # Simple parsing for File1=http://...
            for line in content.splitlines():
                if line.lower().startswith("file") and "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        val = parts[1].strip()
                        if val.startswith(("http://", "https://")):
                            return val
    except Exception:
        pass
    return None


async def _fetch_icecast_metadata(url: str, session: aiohttp.ClientSession, timeout: int) -> StreamMetadata | None:
    """Connect to stream and extract Icecast metadata."""
    headers = {"Icy-MetaData": "1", "User-Agent": USER_AGENT}

    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            # Check for icy headers
            if not response.headers.get(ICE_METADATA_HEADER):
                # Not an icecast stream supporting metadata
                return None

            metadata = StreamMetadata()

            # Get station name
            icy_name = response.headers.get(ICE_NAME_HEADER)
            if icy_name and icy_name not in ("no name", "Unspecified name", "-"):
                metadata.station_name = _decode_text(icy_name)

            # Get metadata interval
            metaint_str = response.headers.get(ICE_METAINT_HEADER)
            if not metaint_str:
                return metadata  # Return just station name if no interval

            try:
                metaint = int(metaint_str)
            except ValueError:
                return metadata

            # Read up to the metadata block
            # In a real scenario, we might need to consume stream data.
            # We trust aiohttp to handle the buffering reasonably well for a short read.

            # Read audio data (discard)
            _ = await response.content.readexactly(metaint)

            # Read length byte
            len_byte = await response.content.readexactly(1)
            length = struct.unpack("B", len_byte)[0] * 16

            if length > 0:
                meta_block = await response.content.readexactly(length)
                _parse_stream_title(meta_block, metadata)

            return metadata

    except (aiohttp.ClientError, TimeoutError, asyncio.IncompleteReadError) as err:
        _LOGGER.debug("Error reading stream metadata: %s", err)
        return None
    except Exception as err:
        _LOGGER.debug("Unexpected error reading stream metadata: %s", err)
        return None


def _parse_stream_title(meta_block: bytes, metadata: StreamMetadata) -> None:
    """Parse StreamTitle from metadata block."""
    # Strip padding
    data = meta_block.rstrip(b"\0")

    # Look for StreamTitle='...';
    # Use robust regex to capture content inside single quotes
    match = re.search(rb"StreamTitle='([^']*)';", data)
    if match:
        raw_title = match.group(1)
        full_title = _decode_text(raw_title)

        if not full_title:
            return

        # Common format: "Artist - Title"
        if " - " in full_title:
            parts = full_title.split(" - ", 1)
            metadata.artist = parts[0].strip()
            metadata.title = parts[1].strip()
        else:
            metadata.title = full_title
            if metadata.station_name and not metadata.artist:
                metadata.artist = metadata.station_name


def _decode_text(data: str | bytes) -> str:
    """Decode text with fallback."""
    if isinstance(data, str):
        return data.strip()

    try:
        return data.decode("utf-8").strip()
    except UnicodeDecodeError:
        try:
            return data.decode("latin-1").strip()
        except Exception:
            return str(data, errors="ignore").strip()
