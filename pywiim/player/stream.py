"""Stream metadata extraction utilities.

This module provides functionality to extract metadata (title, artist) directly
from audio streams (Icecast/SHOUTcast, HLS) and parse playlist formats (M3U, PLS, M3U8).
It is used to enrich player state when the device does not report metadata
for certain stream types (e.g., direct URL playback).
"""

from __future__ import annotations

import asyncio
import logging
import re
import struct
from dataclasses import dataclass
from io import BytesIO
from typing import Final

import aiohttp

try:
    import m3u8  # type: ignore[import-untyped]
except ImportError:
    m3u8 = None

try:
    from mutagen import File as MutagenFile
except ImportError:
    MutagenFile = None

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
    2. Detect stream type (HLS, Icecast, or direct)
    3. Parse playlists (M3U, PLS, M3U8) to find the actual stream URL
    4. Extract metadata using appropriate method (HLS ID3 tags or Icecast headers)

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
        # Check if this is an HLS stream (.m3u8)
        lower_url = url.lower()
        is_hls = lower_url.endswith(".m3u8") or "/hls/" in lower_url or "/master.m3u8" in lower_url

        if is_hls and m3u8 is not None:
            # Try HLS metadata extraction first
            metadata = await _fetch_hls_metadata(url, session, timeout)
            if metadata:
                return metadata
            # Fall through to Icecast if HLS fails

        # 1. Resolve redirects and playlists
        final_url = await _resolve_stream_url(url, session)
        if not final_url:
            return None

        # 2. Fetch Icecast metadata (fallback or primary for non-HLS)
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
    """Parse M3U playlist (non-HLS).

    For HLS playlists (.m3u8), use _fetch_hls_metadata() instead.
    """
    try:
        # Skip HLS playlists - they need special handling
        if url.lower().endswith(".m3u8"):
            return None

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


async def _fetch_hls_metadata(url: str, session: aiohttp.ClientSession, timeout: int) -> StreamMetadata | None:
    """Extract metadata from HLS stream by parsing playlist and downloading latest segment.

    Args:
        url: The HLS playlist URL (.m3u8).
        session: aiohttp session for HTTP requests.
        timeout: Timeout in seconds.

    Returns:
        StreamMetadata object if successful, None otherwise.
    """
    if m3u8 is None:
        _LOGGER.debug("m3u8 library not available, cannot extract HLS metadata")
        return None

    if MutagenFile is None:
        _LOGGER.debug("mutagen library not available, cannot extract ID3 tags from HLS segments")
        return None

    try:
        # Fetch the playlist content asynchronously
        async with session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as response:
            if response.status != 200:
                _LOGGER.debug("Failed to fetch HLS playlist: HTTP %d", response.status)
                return None
            playlist_content = await response.text()

        # Parse the HLS playlist from content
        playlist = m3u8.loads(playlist_content, uri=url)

        # Handle master playlists (playlists that contain variant playlists)
        if playlist.is_variant:
            _LOGGER.debug("Master playlist detected, selecting first variant")
            if not playlist.playlists:
                _LOGGER.debug("Master playlist has no variants: %s", url)
                return None
            # Select the first variant (or could select by bandwidth)
            variant = playlist.playlists[0]
            variant_url = variant.uri
            if not variant_url.startswith(("http://", "https://")):
                from urllib.parse import urljoin

                variant_url = urljoin(url, variant_url)
            _LOGGER.debug("Fetching variant playlist: %s", variant_url)

            # Recursively fetch the variant playlist
            return await _fetch_hls_metadata(variant_url, session, timeout)

        # Handle media playlists (playlists with segments)
        if not playlist.segments:
            _LOGGER.debug("HLS playlist has no segments: %s", url)
            # Try to extract station name from URL as fallback
            metadata = _extract_station_name_from_url(url)
            return metadata if metadata.station_name else None

        # Try multiple segments (last few) to find metadata
        # Some streams only embed metadata in certain segments
        segments_to_check = playlist.segments[-3:] if len(playlist.segments) >= 3 else playlist.segments
        for segment in reversed(segments_to_check):  # Check most recent first
            # m3u8 handles relative URLs when base_uri is provided
            segment_url = segment.uri
            if not segment_url.startswith(("http://", "https://")):
                # Resolve relative URL against playlist base URL
                from urllib.parse import urljoin

                segment_url = urljoin(url, segment_url)

            _LOGGER.debug("Fetching HLS segment for metadata: %s", segment_url)

            try:
                # Download the segment
                async with session.get(
                    segment_url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status != 200:
                        _LOGGER.debug("Failed to download HLS segment: HTTP %d", response.status)
                        continue  # Try next segment

                    segment_data = await response.read()

                # Parse ID3 tags from the segment using mutagen
                # HLS segments often have ID3 tags embedded in AAC streams
                audio_data = BytesIO(segment_data)
                metadata = StreamMetadata()

                # Check if segment starts with ID3 tag
                if segment_data.startswith(b"ID3"):
                    # Try to parse ID3 tags directly
                    try:
                        from mutagen.id3 import ID3

                        # ID3 tags might be at the start of the file
                        id3_tags = ID3(audio_data)
                        if id3_tags:
                            # Extract standard ID3 tags
                            title_tag = id3_tags.get("TIT2")  # Title
                            artist_tag = id3_tags.get("TPE1")  # Artist

                            if title_tag:
                                metadata.title = _decode_text(str(title_tag))
                            if artist_tag:
                                metadata.artist = _decode_text(str(artist_tag))

                            if metadata.title or metadata.artist:
                                _LOGGER.debug(
                                    "Extracted HLS metadata from ID3: title=%s, artist=%s",
                                    metadata.title,
                                    metadata.artist,
                                )
                                return metadata
                    except Exception as id3_err:
                        _LOGGER.debug("Failed to parse ID3 tags directly: %s", id3_err)

                # Fallback: Try mutagen File() for other formats
                tags = MutagenFile(audio_data)
                if tags and tags.tags:
                    # Extract standard ID3 tags
                    title_tag = tags.tags.get("TIT2") if tags.tags else None
                    artist_tag = tags.tags.get("TPE1") if tags.tags else None

                    # Also try common alternative tag names
                    if not title_tag:
                        title_tag = tags.tags.get("TITLE") if tags.tags else None
                    if not artist_tag:
                        artist_tag = tags.tags.get("ARTIST") if tags.tags else None

                    # Extract text values from tags
                    if title_tag:
                        title_value = str(title_tag[0]) if title_tag else None
                        if title_value:
                            metadata.title = _decode_text(title_value)

                    if artist_tag:
                        artist_value = str(artist_tag[0]) if artist_tag else None
                        if artist_value:
                            metadata.artist = _decode_text(artist_value)

                # If we found metadata in this segment, return it
                if metadata.title or metadata.artist:
                    _LOGGER.debug("Extracted HLS metadata: title=%s, artist=%s", metadata.title, metadata.artist)
                    return metadata

                _LOGGER.debug("HLS segment has no extractable metadata")
                # Continue to next segment

            except Exception as e:
                _LOGGER.debug("Failed to parse metadata from segment %s: %s", segment_url, e)
                # Continue to next segment
                continue

        # If no metadata found in segments, try to extract station name from URL
        _LOGGER.debug("No metadata found in segments, trying URL-based extraction")
        metadata = _extract_station_name_from_url(url)
        return metadata if metadata.station_name else None

    except Exception as err:
        _LOGGER.debug("Error extracting HLS metadata from %s: %s", url, err)
        # Try URL-based extraction as last resort
        metadata = _extract_station_name_from_url(url)
        return metadata if metadata.station_name else None


def _extract_station_name_from_url(url: str) -> StreamMetadata:
    """Extract station name from URL patterns as fallback.

    Args:
        url: Stream URL

    Returns:
        StreamMetadata with station_name if found
    """
    metadata = StreamMetadata()

    # Radio-Canada patterns
    if "rcavliveaudio" in url or "radio-canada" in url.lower():
        if "P-2QMTL0_MTL" in url:
            metadata.station_name = "Radio-Canada ICI Première Montréal"
        elif "ICI_PREMIERE" in url.upper():
            metadata.station_name = "Radio-Canada ICI Première"
        elif "ICI_MUSIQUE" in url.upper():
            metadata.station_name = "Radio-Canada ICI Musique"
        else:
            metadata.station_name = "Radio-Canada"

    # BBC patterns
    elif "bbc" in url.lower():
        if "radio_one" in url.lower():
            metadata.station_name = "BBC Radio 1"
        elif "radio_two" in url.lower():
            metadata.station_name = "BBC Radio 2"
        else:
            metadata.station_name = "BBC Radio"

    # CBC patterns
    elif "cbc" in url.lower():
        if "CBCR1" in url.upper():
            metadata.station_name = "CBC Radio One"
        else:
            metadata.station_name = "CBC Radio"

    return metadata


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
