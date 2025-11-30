"""Unit tests for CoverArtManager.

Tests cover art fetching, caching, and URL hashing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from pywiim.api.constants import DEFAULT_WIIM_LOGO_URL


class TestCoverArtManager:
    """Test CoverArtManager class."""

    @pytest.fixture
    def mock_player(self, mock_client):
        """Create a mock Player instance."""
        from pywiim.player import Player

        player = Player(mock_client)
        # Initialize cover art cache attributes
        player._cover_art_cache = {}
        player._cover_art_cache_ttl = 3600
        player._cover_art_cache_max_size = 10
        return player

    @pytest.fixture
    def cover_art_manager(self, mock_player):
        """Create a CoverArtManager instance."""
        from pywiim.player.coverart import CoverArtManager

        return CoverArtManager(mock_player)

    def test_get_url_hash(self, cover_art_manager):
        """Test URL hash generation."""
        hash1 = cover_art_manager._get_url_hash("https://example.com/image.jpg")
        hash2 = cover_art_manager._get_url_hash("https://example.com/image.jpg")
        hash3 = cover_art_manager._get_url_hash("https://example.com/other.jpg")

        # Same URL should produce same hash
        assert hash1 == hash2
        # Different URLs should produce different hashes
        assert hash1 != hash3
        # Hash should be a hex string
        assert len(hash1) == 32  # MD5 hex digest length

    def test_cleanup_cover_art_cache_expired(self, cover_art_manager, mock_player):
        """Test cache cleanup removes expired entries."""
        import time

        # Add expired entry
        url_hash = cover_art_manager._get_url_hash("https://example.com/old.jpg")
        mock_player._cover_art_cache[url_hash] = (b"image_data", "image/jpeg", time.time() - 4000)

        # Add non-expired entry
        url_hash2 = cover_art_manager._get_url_hash("https://example.com/new.jpg")
        mock_player._cover_art_cache[url_hash2] = (b"image_data", "image/jpeg", time.time())

        cover_art_manager._cleanup_cover_art_cache()

        # Expired entry should be removed
        assert url_hash not in mock_player._cover_art_cache
        # Non-expired entry should remain
        assert url_hash2 in mock_player._cover_art_cache

    def test_cleanup_cover_art_cache_size_limit(self, cover_art_manager, mock_player):
        """Test cache cleanup enforces size limit."""
        import time

        # Fill cache beyond max size
        for i in range(15):
            url_hash = cover_art_manager._get_url_hash(f"https://example.com/image{i}.jpg")
            mock_player._cover_art_cache[url_hash] = (b"image_data", "image/jpeg", time.time() + i)

        cover_art_manager._cleanup_cover_art_cache()

        # Cache should be at max size
        assert len(mock_player._cover_art_cache) <= mock_player._cover_art_cache_max_size

    @pytest.mark.asyncio
    async def test_fetch_cover_art_embedded_logo(self, cover_art_manager):
        """Test fetch_cover_art returns embedded logo for sentinel URL."""
        result = await cover_art_manager.fetch_cover_art(DEFAULT_WIIM_LOGO_URL)

        assert result is not None
        image_bytes, content_type = result
        assert isinstance(image_bytes, bytes)
        assert content_type == "image/png"
        assert len(image_bytes) > 0

    @pytest.mark.asyncio
    async def test_fetch_cover_art_none_url(self, cover_art_manager, mock_player):
        """Test fetch_cover_art with None URL uses media_image_url."""
        from pywiim.player.properties import PlayerProperties

        # Mock PlayerProperties to return sentinel URL
        with patch.object(PlayerProperties, "media_image_url", new=DEFAULT_WIIM_LOGO_URL):
            result = await cover_art_manager.fetch_cover_art(None)

            assert result is not None
            image_bytes, content_type = result
            assert content_type == "image/png"

    @pytest.mark.asyncio
    async def test_fetch_cover_art_empty_url(self, cover_art_manager):
        """Test fetch_cover_art with empty URL returns embedded logo."""
        result = await cover_art_manager.fetch_cover_art("")

        assert result is not None
        image_bytes, content_type = result
        assert content_type == "image/png"

    @pytest.mark.asyncio
    async def test_fetch_cover_art_cache_hit(self, cover_art_manager, mock_player):
        """Test fetch_cover_art returns cached entry."""
        import time

        url = "https://example.com/image.jpg"
        url_hash = cover_art_manager._get_url_hash(url)
        cached_data = (b"cached_image", "image/jpeg", time.time())
        mock_player._cover_art_cache[url_hash] = cached_data

        # Mock session to ensure we don't make HTTP call
        mock_player.client._session = None

        result = await cover_art_manager.fetch_cover_art(url)

        assert result == (b"cached_image", "image/jpeg")

    @pytest.mark.asyncio
    async def test_fetch_cover_art_https_success(self, cover_art_manager, mock_player):
        """Test fetch_cover_art fetches HTTPS URL successfully."""
        url = "https://example.com/image.jpg"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.read = AsyncMock(return_value=b"image_data")

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_player.client._session = MagicMock()
        mock_player.client._session.get = MagicMock(return_value=mock_session)
        mock_player.client._get_ssl_context = AsyncMock(return_value=None)

        result = await cover_art_manager.fetch_cover_art(url)

        assert result is not None
        image_bytes, content_type = result
        assert image_bytes == b"image_data"
        assert content_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_fetch_cover_art_http_success(self, cover_art_manager, mock_player):
        """Test fetch_cover_art fetches HTTP URL successfully."""
        url = "http://example.com/image.jpg"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.read = AsyncMock(return_value=b"image_data")

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_player.client._session = MagicMock()
        mock_player.client._session.get = MagicMock(return_value=mock_session)

        result = await cover_art_manager.fetch_cover_art(url)

        assert result is not None
        image_bytes, content_type = result
        assert image_bytes == b"image_data"
        assert content_type == "image/png"

    @pytest.mark.asyncio
    async def test_fetch_cover_art_http_error(self, cover_art_manager, mock_player):
        """Test fetch_cover_art handles HTTP error."""
        url = "https://example.com/image.jpg"
        mock_response = MagicMock()
        mock_response.status = 404

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_player.client._session = MagicMock()
        mock_player.client._session.get = MagicMock(return_value=mock_session)
        mock_player.client._get_ssl_context = AsyncMock(return_value=None)

        result = await cover_art_manager.fetch_cover_art(url)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_cover_art_network_error(self, cover_art_manager, mock_player):
        """Test fetch_cover_art handles network errors."""
        url = "https://example.com/image.jpg"

        mock_player.client._session = MagicMock()
        mock_player.client._session.get = MagicMock(side_effect=aiohttp.ClientError("Network error"))
        mock_player.client._get_ssl_context = AsyncMock(return_value=None)

        result = await cover_art_manager.fetch_cover_art(url)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_cover_art_creates_session(self, cover_art_manager, mock_player):
        """Test fetch_cover_art creates session if none exists."""
        url = "https://example.com/image.jpg"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.read = AsyncMock(return_value=b"image_data")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        mock_player.client._session = None
        mock_player.client._get_ssl_context = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await cover_art_manager.fetch_cover_art(url)

            assert result is not None
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_cover_art_content_type_fallback(self, cover_art_manager, mock_player):
        """Test fetch_cover_art uses image/jpeg fallback for non-image content type."""
        url = "https://example.com/image.jpg"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/octet-stream"}
        mock_response.read = AsyncMock(return_value=b"image_data")

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_player.client._session = MagicMock()
        mock_player.client._session.get = MagicMock(return_value=mock_session)
        mock_player.client._get_ssl_context = AsyncMock(return_value=None)

        result = await cover_art_manager.fetch_cover_art(url)

        assert result is not None
        _, content_type = result
        assert content_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_get_cover_art_bytes(self, cover_art_manager):
        """Test get_cover_art_bytes convenience method."""
        with patch.object(cover_art_manager, "fetch_cover_art", return_value=(b"image_data", "image/jpeg")):
            result = await cover_art_manager.get_cover_art_bytes("https://example.com/image.jpg")

            assert result == b"image_data"

    @pytest.mark.asyncio
    async def test_get_cover_art_bytes_none(self, cover_art_manager):
        """Test get_cover_art_bytes returns None when fetch fails."""
        with patch.object(cover_art_manager, "fetch_cover_art", return_value=None):
            result = await cover_art_manager.get_cover_art_bytes("https://example.com/image.jpg")

            assert result is None
