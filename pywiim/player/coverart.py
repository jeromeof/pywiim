"""Cover art fetching and caching."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from . import Player

_LOGGER = logging.getLogger(__name__)


class CoverArtManager:
    """Manages cover art fetching and caching."""

    def __init__(self, player: Player) -> None:
        """Initialize cover art manager.

        Args:
            player: Parent Player instance.
        """
        self.player = player

    def _get_url_hash(self, url: str) -> str:
        """Generate a hash for a URL to use as cache key."""
        return hashlib.md5(url.encode()).hexdigest()

    def _cleanup_cover_art_cache(self) -> None:
        """Remove expired entries from cover art cache."""
        now = time.time()
        expired_keys = [
            key
            for key, (_, _, timestamp) in self.player._cover_art_cache.items()
            if now - timestamp > self.player._cover_art_cache_ttl
        ]
        for key in expired_keys:
            del self.player._cover_art_cache[key]

        # If still over max size, remove oldest entries
        if len(self.player._cover_art_cache) > self.player._cover_art_cache_max_size:
            sorted_entries = sorted(
                self.player._cover_art_cache.items(),
                key=lambda x: x[1][2],
            )
            for key, _ in sorted_entries[: len(self.player._cover_art_cache) - self.player._cover_art_cache_max_size]:
                del self.player._cover_art_cache[key]

    async def fetch_cover_art(self, url: str | None = None) -> tuple[bytes, str] | None:
        """Fetch cover art image from URL or return embedded fallback logo.

        Args:
            url: Cover art URL to fetch. If None, uses current track's cover art URL.
                If no valid URL is found, returns the embedded PyWiim logo (no HTTP call).

        Returns:
            Tuple of (image_bytes, content_type) if successful, None otherwise.
        """
        import base64

        from .properties import PlayerProperties

        if url is None:
            url = PlayerProperties(self.player).media_image_url

        # If no URL provided OR sentinel value, return embedded PyWiim logo directly (no HTTP call needed)
        from ..api.constants import DEFAULT_WIIM_LOGO_URL, EMBEDDED_LOGO_BASE64

        if not url or url == DEFAULT_WIIM_LOGO_URL:
            try:
                # Decode the embedded base64 PNG logo (join tuple of strings first)
                base64_string = "".join(EMBEDDED_LOGO_BASE64)
                logo_bytes = base64.b64decode(base64_string)
                _LOGGER.debug("Returning embedded PyWiim fallback logo (%d bytes)", len(logo_bytes))
                return (logo_bytes, "image/png")
            except Exception as e:
                _LOGGER.error("Failed to decode embedded logo: %s", e)
                return None

        # Clean up expired cache entries
        self._cleanup_cover_art_cache()

        # Check cache first
        url_hash = self._get_url_hash(url)
        if url_hash in self.player._cover_art_cache:
            cached_bytes, content_type, timestamp = self.player._cover_art_cache[url_hash]
            if time.time() - timestamp < self.player._cover_art_cache_ttl:
                _LOGGER.debug("Returning cover art from cache for URL: %s", url)
                return (cached_bytes, content_type)

        # Fetch from URL
        try:
            session = self.player.client._session
            should_close_session = False

            if session is None:
                session = aiohttp.ClientSession()
                should_close_session = True

            try:
                # Get SSL context from client if URL is HTTPS
                timeout = aiohttp.ClientTimeout(total=10)
                if url.startswith("https://"):
                    # Use the client's SSL context for HTTPS URLs
                    # This ensures we can fetch artwork from device URLs with self-signed certs
                    ssl_ctx = await self.player.client._get_ssl_context()
                    async with session.get(url, timeout=timeout, ssl=ssl_ctx) as response:
                        if response.status == 200:
                            image_bytes = await response.read()
                            content_type = response.headers.get("Content-Type", "image/jpeg")
                            if "image" not in content_type.lower():
                                content_type = "image/jpeg"

                            # Cache the result
                            self.player._cover_art_cache[url_hash] = (
                                image_bytes,
                                content_type,
                                time.time(),
                            )
                            _LOGGER.debug("Fetched and cached cover art from URL: %s", url)

                            # Clean up cache if needed
                            self._cleanup_cover_art_cache()

                            return (image_bytes, content_type)
                        else:
                            _LOGGER.debug(
                                "Failed to fetch cover art: HTTP %d from %s",
                                response.status,
                                url,
                            )
                            return None
                else:
                    # For HTTP URLs, use default SSL handling
                    async with session.get(url, timeout=timeout) as response:
                        if response.status == 200:
                            image_bytes = await response.read()
                            content_type = response.headers.get("Content-Type", "image/jpeg")
                            if "image" not in content_type.lower():
                                content_type = "image/jpeg"

                            # Cache the result
                            self.player._cover_art_cache[url_hash] = (
                                image_bytes,
                                content_type,
                                time.time(),
                            )
                            _LOGGER.debug("Fetched and cached cover art from URL: %s", url)

                            # Clean up cache if needed
                            self._cleanup_cover_art_cache()

                            return (image_bytes, content_type)
                        else:
                            _LOGGER.debug(
                                "Failed to fetch cover art: HTTP %d from %s",
                                response.status,
                                url,
                            )
                            return None
            finally:
                if should_close_session:
                    await session.close()
        except Exception as e:
            _LOGGER.debug("Error fetching cover art from %s: %s", url, e)
            return None

    async def get_cover_art_bytes(self, url: str | None = None) -> bytes | None:
        """Get cover art image bytes (convenience method).

        Args:
            url: Cover art URL to fetch. If None, uses current track's cover art URL.

        Returns:
            Image bytes if successful, None otherwise.
        """
        result = await self.fetch_cover_art(url)
        if result:
            return result[0]
        return None
