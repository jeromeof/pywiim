"""Stream metadata enrichment for raw URL playback."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from .stream import StreamMetadata, get_stream_metadata

if TYPE_CHECKING:
    from ..models import PlayerStatus
    from . import Player

_LOGGER = logging.getLogger(__name__)


class StreamEnricher:
    """Enriches player state when playing raw stream URLs.

    Handles cases where the device plays a direct URL (Icecast, M3U, PLS)
    but returns the URL as the title instead of parsed metadata.
    """

    def __init__(self, player: Player) -> None:
        """Initialize stream enricher.

        Args:
            player: Parent Player instance.
        """
        self.player = player
        self.enabled: bool = True
        self._last_stream_url: str | None = None
        self._last_stream_metadata: StreamMetadata | None = None
        self._enrichment_task: asyncio.Task | None = None

    async def enrich_if_needed(self, status: PlayerStatus | None) -> None:
        """Enrich status with stream metadata if playing a raw stream.

        Args:
            status: Current player status to check for stream URL.
        """
        if not self.enabled:
            return

        # Early return if status is None
        if status is None:
            return

        # Check if we are playing
        # Note: "stop" is normalized to "pause" by PlayerStatus, so check for both
        if not status.play_state or status.play_state in ("stop", "pause", "idle"):
            return

        # Check if source is suitable for enrichment (wifi/url playback)
        # 'wifi' (10, 20, 3) or 'unknown' are candidates.
        if status.source not in ("wifi", "unknown", None):
            return

        # Check if we have a URL in title
        url = status.title
        if not url or not str(url).startswith(("http://", "https://")):
            return

        # Avoid re-fetching same URL repeatedly if we have cached metadata
        if url == self._last_stream_url and self._last_stream_metadata:
            # Re-apply cached metadata
            self._apply_stream_metadata(self._last_stream_metadata)
            return

        # If URL changed, start new fetch
        if url != self._last_stream_url:
            self._last_stream_url = url
            self._last_stream_metadata = None  # Clear cache

            # Cancel existing task
            if self._enrichment_task and not self._enrichment_task.done():
                self._enrichment_task.cancel()

            # Start new task
            try:
                loop = asyncio.get_running_loop()
                self._enrichment_task = loop.create_task(self._fetch_and_apply_stream_metadata(url))
            except RuntimeError:
                # No event loop available (sync context) - will fetch on next poll
                _LOGGER.debug("No event loop available, stream metadata will be fetched on next poll")

    async def _fetch_and_apply_stream_metadata(self, url: str) -> None:
        """Fetch metadata from stream and apply it to state.

        Args:
            url: Stream URL to fetch metadata from.
        """
        try:
            # Use client session if available
            session = None
            if hasattr(self.player.client, "_session"):
                session = self.player.client._session

            metadata = await get_stream_metadata(url, session)

            if metadata:
                self._last_stream_metadata = metadata
                self._apply_stream_metadata(metadata)

                # Notify change
                if self.player._on_state_changed:
                    try:
                        self.player._on_state_changed()
                    except Exception as err:
                        _LOGGER.debug("Error in callback after stream enrichment: %s", err)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            _LOGGER.debug("Error enriching stream metadata for %s: %s", url, err)

    def _apply_stream_metadata(self, metadata: StreamMetadata) -> None:
        """Apply enriched metadata to state.

        Args:
            metadata: Stream metadata to apply.
        """
        update: dict[str, Any] = {}

        # Only update if fields are present
        if metadata.title:
            update["title"] = metadata.title
        if metadata.artist:
            update["artist"] = metadata.artist

        # Fallback: use station name as artist if artist is missing
        if metadata.station_name and not metadata.artist and not update.get("artist"):
            update["artist"] = metadata.station_name

        if update:
            _LOGGER.debug("Applying stream metadata enrichment: %s", update)

            # Update synchronizer (as if from HTTP)
            self.player._state_synchronizer.update_from_http(update, timestamp=time.time())

            # Update cached status model immediately for UI responsiveness
            if self.player._status_model:
                merged = self.player._state_synchronizer.get_merged_state()
                if "title" in merged:
                    self.player._status_model.title = merged["title"]
                if "artist" in merged:
                    self.player._status_model.artist = merged["artist"]
