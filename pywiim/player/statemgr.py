"""State management - refresh, UPnP integration, state synchronization."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from ..state import PLAYING_STATES, normalize_play_state
from .stream import StreamMetadata, get_stream_metadata

if TYPE_CHECKING:
    from ..models import DeviceInfo, PlayerStatus
    from . import Player

_LOGGER = logging.getLogger(__name__)

# Standard sources that shouldn't be cleared when checking for multiroom/master names
STANDARD_SOURCES = {
    "spotify",
    "tidal",
    "amazon",
    "qobuz",
    "deezer",
    "wifi",
    "bluetooth",
    "linein",
    "coax",
    "optical",
    "usb",
    "airplay",
    "dlna",
    "unknown",
}


class StateManager:
    """Manages player state refresh and UPnP integration."""

    def __init__(self, player: Player) -> None:
        """Initialize state manager.

        Args:
            player: Parent Player instance.
        """
        self.player = player
        # Track last track signature to detect track changes for immediate artwork fetching
        self._last_track_signature: str | None = None
        # Track if we're already fetching artwork to avoid duplicate requests
        self._artwork_fetch_task: asyncio.Task | None = None

        # Stream enrichment state
        self.stream_enrichment_enabled: bool = True
        self._stream_enrichment_task: asyncio.Task | None = None
        self._last_stream_url: str | None = None
        self._last_stream_metadata: StreamMetadata | None = None  # StreamMetadata from .stream

        # Track pending pause/stop/buffering state to debounce track changes
        self._pending_state_task: asyncio.Task | None = None

    def apply_diff(self, changes: dict[str, Any]) -> bool:
        """Apply state changes from UPnP events.

        Args:
            changes: Dictionary with state fields from UPnP event.

        Returns:
            True if state changed, False otherwise.
        """
        if not changes:
            return False

        # Track if state actually changed
        old_state = {
            "play_state": self.player.play_state,
            "volume": self.player.volume_level,
            "muted": self.player.is_muted,
            "title": self.player.media_title,
            "position": self.player.media_position,
        }
        old_play_state = old_state["play_state"]

        # Update from UPnP
        self.update_from_upnp(changes)

        # Check if state changed
        new_state = {
            "play_state": self.player.play_state,
            "volume": self.player.volume_level,
            "muted": self.player.is_muted,
            "title": self.player.media_title,
            "position": self.player.media_position,
        }
        new_play_state = new_state["play_state"]

        # Handle position timer based on play state changes
        if old_play_state != new_play_state:
            # Check if transitioning from playing to paused/stopped
            was_playing = old_play_state and any(s in str(old_play_state).lower() for s in PLAYING_STATES)
            is_playing = new_play_state and any(s in str(new_play_state).lower() for s in PLAYING_STATES)

            _LOGGER.info(
                "🎵 Play state changed: %s -> %s (was_playing=%s, is_playing=%s)",
                old_play_state,
                new_play_state,
                was_playing,
                is_playing,
            )

        return old_state != new_state

    def update_from_upnp(self, data: dict[str, Any]) -> None:
        """Update state from UPnP event data.

        Args:
            data: Dictionary with state fields from UPnP event.
        """
        # Handle debounce for play state to smooth track changes
        # Devices often report STOPPED/PAUSED briefly between tracks
        if "play_state" in data:
            raw_state = data["play_state"]

            new_state = normalize_play_state(raw_state)
            current_state = self.player.play_state

            # Check if currently playing (or loading/transitioning)
            is_playing = current_state and any(s in str(current_state).lower() for s in PLAYING_STATES)

            # Check if new state is pause/stop or buffering
            # We debounce buffering too, to avoid UI flashes during track transitions
            is_interruption = new_state is not None and new_state in ("pause", "stop", "idle", "buffering")

            if is_playing and is_interruption and new_state is not None:
                # Transitioning Play -> Pause/Buffering: Debounce it
                # Don't apply play_state immediately, schedule it
                self._schedule_delayed_update(new_state)

                # Make a copy without play_state to apply other changes immediately
                data_copy = data.copy()
                del data_copy["play_state"]
                self.player._state_synchronizer.update_from_upnp(data_copy)
                return

            elif new_state in ("play", "playing"):
                # Transitioning to Play: Cancel any pending state update and apply immediately
                if self._pending_state_task and not self._pending_state_task.done():
                    self._pending_state_task.cancel()
                    self._pending_state_task = None
                    _LOGGER.debug("Track change detected (Play -> Play), cancelled pending state update")

        self.player._state_synchronizer.update_from_upnp(data)

        # Update UPnP health tracker with UPnP event data
        if self.player._upnp_health_tracker:
            # Convert volume to int (0-100) if it's a float (0.0-1.0)
            volume = data.get("volume")
            if isinstance(volume, float) and 0.0 <= volume <= 1.0:
                volume = int(volume * 100)
            elif volume is not None:
                volume = int(volume)

            upnp_state = {
                "play_state": data.get("play_state"),
                "volume": volume,
                "muted": data.get("muted"),
                "title": data.get("title"),
                "artist": data.get("artist"),
                "album": data.get("album"),
            }
            self.player._upnp_health_tracker.on_upnp_event(upnp_state)

        # Get merged state and update cached models
        # CRITICAL: Always get fresh merged state after UPnP update to ensure
        # properties are updated before callbacks fire
        merged = self.player._state_synchronizer.get_merged_state()

        # Update cached status_model with merged state
        # IMPORTANT: Update ALL fields from merged state, not just changed ones.
        # This ensures properties (media_title, media_artist, etc.) are current
        # when callbacks fire, even if the UPnP event didn't include metadata.
        if self.player._status_model:
            # Update fields from merged state (always update, even if None)
            for field_name in ["play_state", "position", "duration", "source"]:
                if field_name in merged:
                    setattr(self.player._status_model, field_name, merged.get(field_name))

            # Update volume and mute
            if "volume" in merged:
                vol = merged.get("volume")
                if vol is not None:
                    if isinstance(vol, float) and 0.0 <= vol <= 1.0:
                        self.player._status_model.volume = int(vol * 100)
                    else:
                        self.player._status_model.volume = int(vol)
                # Note: We don't set to None here to preserve existing value if merged state has None

            if "muted" in merged:
                muted_val = merged.get("muted")
                if muted_val is not None:
                    self.player._status_model.mute = muted_val

            # Update metadata - ALWAYS update from merged state to ensure
            # properties reflect latest data when callbacks fire
            for field_name in ["title", "artist", "album"]:
                if field_name in merged:
                    # Always update, even if None (merged state is source of truth)
                    setattr(self.player._status_model, field_name, merged.get(field_name))

            if "image_url" in merged:
                image_url = merged.get("image_url")
                self.player._status_model.entity_picture = image_url
                self.player._status_model.cover_url = image_url

        # Detect track changes and fetch artwork immediately if missing
        self._check_and_fetch_artwork_on_track_change(merged)

        # If this is a master, propagate metadata to all linked slaves
        if self.player.is_master and self.player._group and self.player._group.slaves:
            self._propagate_metadata_to_slaves()

    def _schedule_delayed_update(self, new_state: str) -> None:
        """Schedule a delayed update to play state (pause/stop/buffering).

        This debounces the 'stop' or 'buffering' events that occur during track changes.
        """
        if self._pending_state_task and not self._pending_state_task.done():
            self._pending_state_task.cancel()

        try:
            loop = asyncio.get_event_loop()
            self._pending_state_task = loop.create_task(self._apply_delayed_state(new_state))
        except RuntimeError:
            # No event loop (sync context) - apply immediately
            self.player._state_synchronizer.update_from_upnp({"play_state": new_state})

    async def _apply_delayed_state(self, new_state: str) -> None:
        """Apply play state after delay."""
        try:
            # Wait 500ms - typical track change stop is < 100ms, but buffering can take longer
            await asyncio.sleep(0.5)

            # If we get here, the timer expired without being cancelled by a "Play" event
            _LOGGER.debug("Debounce timer expired, applying delayed state: %s", new_state)

            self.player._state_synchronizer.update_from_upnp({"play_state": new_state})

            # Force update of cached model
            merged = self.player._state_synchronizer.get_merged_state()
            if self.player._status_model and "play_state" in merged:
                self.player._status_model.play_state = merged["play_state"]

            # Trigger callback
            if self.player._on_state_changed:
                try:
                    self.player._on_state_changed()
                except Exception as err:
                    _LOGGER.debug("Error in callback after delayed state update: %s", err)

        except asyncio.CancelledError:
            # Task cancelled - track change confirmed (Play -> Interruption -> Play)
            pass
        except Exception as e:
            _LOGGER.error("Error in delayed state task: %s", e)
        finally:
            self._pending_state_task = None

    def _check_and_fetch_artwork_on_track_change(self, merged: dict[str, Any]) -> None:
        """Check if track changed and fetch artwork immediately if missing.

        Args:
            merged: Merged state dictionary from StateSynchronizer.
        """
        # Build current track signature
        title = merged.get("title") or ""
        artist = merged.get("artist") or ""
        album = merged.get("album") or ""
        current_signature = f"{title}|{artist}|{album}"

        # Check if track changed
        track_changed = (
            current_signature and self._last_track_signature and current_signature != self._last_track_signature
        )

        if track_changed:
            self._last_track_signature = current_signature

            # Check if artwork is missing or is default logo
            image_url = merged.get("image_url")
            from ..api.constants import DEFAULT_WIIM_LOGO_URL

            has_valid_artwork = (
                image_url
                and str(image_url).strip()
                and str(image_url).strip().lower() not in ("unknow", "unknown", "un_known", "none", "")
                and str(image_url).strip() != DEFAULT_WIIM_LOGO_URL
            )

            # If artwork is missing and device supports getMetaInfo, fetch it immediately
            if not has_valid_artwork:
                capabilities = self.player.client._capabilities
                if capabilities.get("supports_metadata", True) and hasattr(self.player.client, "get_meta_info"):
                    # Cancel any existing artwork fetch task
                    if self._artwork_fetch_task and not self._artwork_fetch_task.done():
                        self._artwork_fetch_task.cancel()

                    # Start background task to fetch artwork
                    try:
                        loop = asyncio.get_event_loop()
                        self._artwork_fetch_task = loop.create_task(self._fetch_artwork_from_metainfo())
                        _LOGGER.debug("Track changed, fetching artwork from getMetaInfo immediately")
                    except RuntimeError:
                        # No event loop available (sync context) - will fetch on next poll
                        _LOGGER.debug("No event loop available, artwork will be fetched on next poll")
        elif not self._last_track_signature and current_signature:
            # First track detected
            self._last_track_signature = current_signature

    async def _fetch_artwork_from_metainfo(self) -> None:
        """Fetch artwork from getMetaInfo and update state.

        This runs as a background task when track changes and artwork is missing.
        """
        try:
            if not hasattr(self.player.client, "get_meta_info"):
                return

            meta_info = await self.player.client.get_meta_info()
            if not meta_info or "metaData" not in meta_info:
                return

            meta_data = meta_info["metaData"]

            # Extract artwork URL
            artwork_url = (
                meta_data.get("cover")
                or meta_data.get("cover_url")
                or meta_data.get("albumart")
                or meta_data.get("albumArtURI")
                or meta_data.get("albumArtUri")
                or meta_data.get("albumarturi")
                or meta_data.get("art_url")
                or meta_data.get("artwork_url")
                or meta_data.get("pic_url")
            )

            # Validate artwork URL
            if artwork_url and str(artwork_url).strip() not in (
                "unknow",
                "unknown",
                "un_known",
                "",
                "none",
            ):
                # Basic URL validation
                if "http" in str(artwork_url).lower() or str(artwork_url).startswith("/"):
                    # Get current metadata for cache-busting
                    merged = self.player._state_synchronizer.get_merged_state()
                    title = merged.get("title") or ""
                    artist = merged.get("artist") or ""
                    album = merged.get("album") or ""
                    cache_key = f"{title}-{artist}-{album}"

                    if cache_key:
                        from urllib.parse import quote

                        encoded = quote(cache_key)
                        sep = "&" if "?" in artwork_url else "?"
                        artwork_url = f"{artwork_url}{sep}cache={encoded}"

                    # Update state synchronizer with new artwork
                    self.player._state_synchronizer.update_from_http(
                        {"entity_picture": artwork_url}, timestamp=time.time()
                    )

                    # Update cached status model
                    merged = self.player._state_synchronizer.get_merged_state()
                    if self.player._status_model and "image_url" in merged:
                        image_url = merged.get("image_url")
                        self.player._status_model.entity_picture = image_url
                        self.player._status_model.cover_url = image_url

                    # Trigger callback to notify of artwork update
                    if self.player._on_state_changed:
                        try:
                            self.player._on_state_changed()
                        except Exception as err:
                            _LOGGER.debug("Error in callback after artwork update: %s", err)

                    _LOGGER.debug("Fetched artwork from getMetaInfo on track change: %s", artwork_url)
        except asyncio.CancelledError:
            # Task was cancelled (new track change detected)
            pass
        except Exception as e:
            _LOGGER.debug("Error fetching artwork from getMetaInfo on track change: %s", e)

    async def _get_master_name(self, device_info: DeviceInfo | None, status: PlayerStatus | None) -> str | None:
        """Get master device name."""
        # First try: Use Group object if available
        if (
            self.player._group is not None
            and self.player._group.master is not None
            and self.player._group.master != self.player
        ):
            if self.player._group.master._device_info is None or self.player._group.master.name is None:
                try:
                    await self.player._group.master.refresh()
                except Exception:
                    pass
            return self.player._group.master.name or self.player._group.master.host

        # Second try: Use master_ip from device_info/status
        if device_info:
            master_ip = device_info.master_ip or (status.master_ip if status else None)
            if master_ip:
                master_client = None
                try:
                    from ..client import WiiMClient

                    master_client = WiiMClient(master_ip)
                    master_name = await master_client.get_device_name()
                    return master_name
                except Exception as e:
                    _LOGGER.debug("Failed to get master name from IP %s: %s", master_ip, e)
                    return master_ip
                finally:
                    if master_client is not None:
                        try:
                            await master_client.close()
                        except Exception:
                            pass

        return None

    def _propagate_metadata_to_slaves(self) -> None:
        """Propagate metadata from master to all linked slaves.

        This ensures slaves always have the latest metadata from the master,
        even when the master's metadata changes via UPnP or refresh.
        """
        if not self.player.is_master or not self.player._group or not self.player._group.slaves:
            return

        if not self.player._status_model:
            return

        master_status = self.player._status_model

        for slave in self.player._group.slaves:
            if not slave._status_model:
                continue

            # Copy ALL playback metadata from master to slave
            slave._status_model.title = master_status.title
            slave._status_model.artist = master_status.artist
            slave._status_model.album = master_status.album
            slave._status_model.entity_picture = master_status.entity_picture
            slave._status_model.cover_url = master_status.cover_url
            slave._status_model.play_state = master_status.play_state
            slave._status_model.position = master_status.position
            slave._status_model.duration = master_status.duration

            # Update state synchronizer with master's metadata
            slave._state_synchronizer.update_from_http(
                {
                    "title": master_status.title,
                    "artist": master_status.artist,
                    "album": master_status.album,
                    "image_url": master_status.entity_picture or master_status.cover_url,
                    "play_state": master_status.play_state,
                    "position": master_status.position,
                    "duration": master_status.duration,
                }
            )

            # Trigger callback on slave so HA integration updates
            if slave._on_state_changed:
                try:
                    slave._on_state_changed()
                except Exception as err:
                    _LOGGER.debug("Error calling on_state_changed callback for slave %s: %s", slave.host, err)

            _LOGGER.debug(
                "Propagated metadata from master %s to slave %s: '%s' by %s",
                self.player.host,
                slave.host,
                master_status.title,
                master_status.artist,
            )

    async def refresh(self, full: bool = False) -> None:
        """Refresh cached state from device.

        Args:
            full: If True, perform a full refresh including expensive endpoints (device info, EQ, BT).
                 If False (default), only fetch fast-changing status data (volume, playback).
        """
        try:
            # Tier 1: Always fetch fast status
            status = await self.player.client.get_player_status_model()

            # Tier 3: Only fetch Device Info on full refresh or if missing
            device_info = self.player._device_info
            if full or device_info is None:
                device_info = await self.player.client.get_device_info_model()
                self.player._device_info = device_info

            # Update StateSynchronizer with HTTP data
            status_dict = status.model_dump(exclude_none=False) if status else {}
            if "entity_picture" in status_dict:
                status_dict["image_url"] = status_dict.pop("entity_picture")
            for field_name in ["title", "artist", "album", "image_url"]:
                if field_name not in status_dict:
                    status_dict[field_name] = None

            self.player._state_synchronizer.update_from_http(status_dict)

            # Update UPnP health tracker with HTTP poll data
            if self.player._upnp_health_tracker:
                # Convert volume to int (0-100) if it's a float (0.0-1.0)
                volume = status_dict.get("volume")
                if isinstance(volume, float) and 0.0 <= volume <= 1.0:
                    volume = int(volume * 100)
                elif volume is not None:
                    volume = int(volume)

                poll_state = {
                    "play_state": status_dict.get("play_state"),
                    "volume": volume,
                    "muted": status_dict.get("muted"),
                    "title": status_dict.get("title"),
                    "artist": status_dict.get("artist"),
                    "album": status_dict.get("album"),
                }
                self.player._upnp_health_tracker.on_poll_update(poll_state)

            # Update cached models
            self.player._status_model = status
            if self.player._status_model and self.player._status_model.source == "multiroom":
                # We don't fetch master name for slaves anymore - handled by Master
                pass

            # Enrich metadata if playing a stream
            await self._enrich_stream_metadata(status)

            self.player._last_refresh = time.time()
            self.player._available = True

            # === Tier 2: Trigger-Based Fetching ===

            # 1. Metadata (Bitrate/Sample Rate) - Only if track changed
            current_signature = f"{status.title}|{status.artist}|{status.album}"
            if current_signature != self._last_track_signature:
                # Track changed (or first run)
                if self.player.client.capabilities.get("supports_metadata", False):
                    try:
                        metadata = await self.player.client.get_meta_info()
                        self.player._metadata = metadata if metadata else None
                    except Exception as err:
                        _LOGGER.debug("Failed to fetch metadata for %s: %s", self.player.host, err)
                        self.player._metadata = None

            # 2. Audio Output Status - Only if source changed or full refresh
            # TODO: Store last source to detect change
            if full and self.player.client.capabilities.get("supports_audio_output", False):
                try:
                    audio_output_status = await self.player.client.get_audio_output_status()
                    self.player._audio_output_status = audio_output_status
                except Exception as err:
                    _LOGGER.debug("Failed to fetch audio output status for %s: %s", self.player.host, err)
                    self.player._audio_output_status = None

            # 3. EQ Presets - Only on full refresh
            if full and self.player.client.capabilities.get("supports_eq", False):
                try:
                    eq_presets = await self.player.client.get_eq_presets()
                    self.player._eq_presets = eq_presets if eq_presets else None
                except Exception as err:
                    _LOGGER.debug("Failed to fetch EQ presets for %s: %s", self.player.host, err)
                    self.player._eq_presets = None

            # 4. Bluetooth History - Only on full refresh or explicit trigger
            if full:
                try:
                    bluetooth_history = await self.player.client.get_bluetooth_history()
                    self.player._bluetooth_history = bluetooth_history if bluetooth_history else []
                except Exception as err:
                    _LOGGER.debug("Failed to fetch Bluetooth history for %s: %s", self.player.host, err)
                    self.player._bluetooth_history = []

            # Synchronize group state from device state
            from .groupops import GroupOperations

            await GroupOperations(self.player)._synchronize_group_state()

            # If this is a master, propagate metadata to all linked slaves
            if self.player.is_master and self.player._group and self.player._group.slaves:
                self._propagate_metadata_to_slaves()

            # Notify callback
            if self.player._on_state_changed:
                try:
                    self.player._on_state_changed()
                except Exception as err:
                    _LOGGER.debug("Error calling on_state_changed callback for %s: %s", self.player.host, err)

        except Exception as err:
            device_context = f"host={self.player.host}"
            if self.player._device_info:
                device_context += (
                    f", model={self.player._device_info.model}, firmware={self.player._device_info.firmware}"
                )
            _LOGGER.warning("Failed to refresh state for %s: %s", device_context, err)
            self.player._available = False
            raise

    async def get_device_info(self) -> DeviceInfo:
        """Get device information (always queries device)."""
        return await self.player.client.get_device_info_model()

    async def get_status(self) -> PlayerStatus:
        """Get current player status (always queries device)."""
        return await self.player.client.get_player_status_model()

    async def get_play_state(self) -> str:
        """Get current playback state by querying device."""
        status = await self.get_status()
        return status.play_state or "stop"

    async def _enrich_stream_metadata(self, status: PlayerStatus) -> None:
        """Enrich status with stream metadata if playing a raw stream.

        Handles cases where the device plays a direct URL (Icecast, M3U, PLS)
        but returns the URL as the title instead of parsed metadata.
        """
        if not self.stream_enrichment_enabled:
            return

        # Check if we are playing
        if not status.play_state or status.play_state in ("stop", "idle"):
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
            if self._stream_enrichment_task and not self._stream_enrichment_task.done():
                self._stream_enrichment_task.cancel()

            # Start new task
            loop = asyncio.get_running_loop()
            self._stream_enrichment_task = loop.create_task(self._fetch_and_apply_stream_metadata(url))

    async def _fetch_and_apply_stream_metadata(self, url: str) -> None:
        """Fetch metadata from stream and apply it to state."""
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
        """Apply enriched metadata to state."""
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
