"""Media playback control."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from ..exceptions import WiiMError

if TYPE_CHECKING:
    from . import Player

_LOGGER = logging.getLogger(__name__)


class MediaControl:
    """Manages media playback operations."""

    def __init__(self, player: Player) -> None:
        """Initialize media control.

        Args:
            player: Parent Player instance.
        """
        self.player = player

    async def play(self) -> None:
        """Start playback (raw API call).

        Note: On streaming sources when paused, this may restart the track from the
        beginning. Consider using resume() or media_play_pause() instead to continue
        from the current position.

        Raises:
            WiiMError: If the request fails.
        """
        # Route slave commands through group to master
        if self.player.is_slave and self.player.group:
            await self.player.group.play()
            return

        if self.player.is_slave:
            _LOGGER.debug("Slave %s has no group object, cannot route playback command", self.player.host)
            raise WiiMError("Slave player not linked to group")

        # Call API (raises on failure)
        await self.player.client.play()

        # Update cached state immediately (optimistic)
        if self.player._status_model:
            self.player._status_model.play_state = "play"

        # Update state synchronizer (for immediate property reads)
        self.player._state_synchronizer.update_from_http({"play_state": "play"})

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def pause(self) -> None:
        """Pause playback (raw API call).

        Raises:
            WiiMError: If the request fails.
        """
        # Route slave commands through group to master
        if self.player.is_slave and self.player.group:
            await self.player.group.pause()
            return

        if self.player.is_slave:
            _LOGGER.debug("Slave %s has no group object, cannot route playback command", self.player.host)
            raise WiiMError("Slave player not linked to group")

        # Call API (raises on failure)
        await self.player.client.pause()

        # Update cached state immediately (optimistic)
        if self.player._status_model:
            self.player._status_model.play_state = "pause"

        # Update state synchronizer (for immediate property reads)
        self.player._state_synchronizer.update_from_http({"play_state": "pause"})

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def resume(self) -> None:
        """Resume playback from paused state (raw API call).

        This command continues playback from the current position without restarting
        the track. Use this instead of play() when resuming paused content on streaming
        sources to avoid restarting from the beginning.

        Raises:
            WiiMError: If the request fails.
        """
        # Route slave commands through group to master
        if self.player.is_slave and self.player.group:
            await self.player.group.master.resume()
            return

        if self.player.is_slave:
            _LOGGER.debug("Slave %s has no group object, cannot route playback command", self.player.host)
            raise WiiMError("Slave player not linked to group")

        # Call API (raises on failure)
        await self.player.client.resume()

        # Update cached state immediately (optimistic)
        if self.player._status_model:
            self.player._status_model.play_state = "play"

        # Update state synchronizer (for immediate property reads)
        self.player._state_synchronizer.update_from_http({"play_state": "play"})

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def stop(self) -> None:
        """Stop playback (raw API call).

        Note: WiFi/Webradio sources may not stay stopped and may return to playing state.
        For web radio streams, consider using pause() instead if stop() doesn't work reliably.

        Raises:
            WiiMError: If the request fails.
        """
        # Route slave commands through group to master
        if self.player.is_slave and self.player.group:
            await self.player.group.stop()
            return

        if self.player.is_slave:
            _LOGGER.debug("Slave %s has no group object, cannot route playback command", self.player.host)
            raise WiiMError("Slave player not linked to group")

        # Call API (raises on failure)
        await self.player.client.stop()

        # Update cached state immediately (optimistic)
        if self.player._status_model:
            self.player._status_model.play_state = "stop"

        # Update state synchronizer (for immediate property reads)
        self.player._state_synchronizer.update_from_http({"play_state": "stop"})

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def media_play_pause(self) -> None:
        """Toggle play/pause state intelligently (Home Assistant compatible).

        This method follows Home Assistant media_player conventions and handles the
        play/pause/resume semantics correctly across different sources:

        - When paused: Uses resume() to continue from current position (avoiding
          the issue where play() restarts streaming tracks from the beginning)
        - When playing: Uses pause() to pause playback
        - When stopped/idle: Uses play() to start playback

        This is the recommended method for implementing Home Assistant's media_play_pause
        service, as it avoids the track restart issue on streaming sources (Issue #102).

        Raises:
            WiiMError: If the request fails.

        Example:
            ```python
            # In Home Assistant media player entity
            async def async_media_play_pause(self) -> None:
                await self.coordinator.player.media_play_pause()
            ```
        """
        current_state = self.player.play_state

        if current_state in ("pause", "paused"):
            # Resume from current position (don't restart)
            await self.resume()
        elif current_state in ("play", "playing"):
            # Pause playback
            await self.pause()
        else:
            # Start playback (stopped/idle/unknown)
            await self.play()

    async def next_track(self) -> None:
        """Skip to next track."""
        # Route slave commands through group to master
        if self.player.is_slave and self.player.group:
            await self.player.group.next_track()
            return

        if self.player.is_slave:
            _LOGGER.debug("Slave %s has no group object, cannot route playback command", self.player.host)
            raise WiiMError("Slave player not linked to group")

        # Call API (raises on failure)
        await self.player.client.next_track()

        # Call callback to notify state change (track will change)
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def previous_track(self) -> None:
        """Skip to previous track."""
        # Route slave commands through group to master
        if self.player.is_slave and self.player.group:
            await self.player.group.previous_track()
            return

        if self.player.is_slave:
            _LOGGER.debug("Slave %s has no group object, cannot route playback command", self.player.host)
            raise WiiMError("Slave player not linked to group")

        # Call API (raises on failure)
        await self.player.client.previous_track()

        # Call callback to notify state change (track will change)
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def seek(self, position: int) -> None:
        """Seek to position in current track.

        Args:
            position: Position in seconds to seek to.
        """
        # Call API (raises on failure)
        await self.player.client.seek(position)

        # Update cached state immediately (optimistic)
        if self.player._status_model:
            self.player._status_model.position = position

        # Update state synchronizer (for immediate property reads)
        self.player._state_synchronizer.update_from_http({"position": position})

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def play_url(self, url: str, enqueue: Literal["add", "next", "replace", "play"] = "replace") -> None:
        """Play a URL directly with optional enqueue support.

        Args:
            url: URL to play.
            enqueue: How to enqueue the media.
        """
        # Call API (raises on failure)
        if enqueue in ("add", "next"):
            if not self.player._upnp_client:
                raise WiiMError(f"Queue management (enqueue='{enqueue}') requires UPnP client.")
            await self._enqueue_via_upnp(url, enqueue)  # type: ignore[arg-type]
        else:
            await self.player.client.play_url(url)

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def play_playlist(self, playlist_url: str) -> None:
        """Play a playlist (M3U) URL.

        Args:
            playlist_url: URL to M3U playlist file.
        """
        # Call API (raises on failure)
        await self.player.client.play_playlist(playlist_url)

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def play_notification(self, url: str) -> None:
        """Play a notification sound from URL.

        Args:
            url: URL to notification audio file.
        """
        # Call API (raises on failure)
        await self.player.client.play_notification(url)

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def add_to_queue(self, url: str, metadata: str = "") -> None:
        """Add URL to end of queue (requires UPnP client).

        Args:
            url: URL to add to queue.
            metadata: Optional DIDL-Lite metadata.
        """
        if not self.player._upnp_client:
            raise WiiMError("Queue management requires UPnP client.")

        await self.player._upnp_client.async_call_action(
            "AVTransport",
            "AddURIToQueue",
            {
                "InstanceID": 0,
                "EnqueuedURI": url,
                "EnqueuedURIMetaData": metadata,
                "DesiredFirstTrackNumberEnqueued": 0,
                "EnqueueAsNext": False,
            },
        )

    async def insert_next(self, url: str, metadata: str = "") -> None:
        """Insert URL after current track (requires UPnP client).

        Args:
            url: URL to insert.
            metadata: Optional DIDL-Lite metadata.
        """
        if not self.player._upnp_client:
            raise WiiMError("Queue management requires UPnP client.")

        await self.player._upnp_client.async_call_action(
            "AVTransport",
            "InsertURIToQueue",
            {
                "InstanceID": 0,
                "EnqueuedURI": url,
                "EnqueuedURIMetaData": metadata,
                "DesiredTrackNumber": 0,
            },
        )

    async def _enqueue_via_upnp(self, url: str, enqueue: Literal["add", "next"]) -> None:
        """Internal helper for UPnP queue operations."""
        if enqueue == "add":
            await self.add_to_queue(url)
        elif enqueue == "next":
            await self.insert_next(url)

    async def play_preset(self, preset: int) -> None:
        """Play a preset by number.

        Args:
            preset: Preset number (1-based).
        """
        # Call API (raises on failure)
        await self.player.client.play_preset(preset)

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def clear_playlist(self) -> None:
        """Clear the current playlist."""
        # Call API (raises on failure)
        await self.player.client.clear_playlist()

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()
