"""State management - refresh, UPnP integration, state synchronization."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

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
            was_playing = old_play_state and str(old_play_state).lower() in ("play", "playing", "load")
            is_playing = new_play_state and str(new_play_state).lower() in ("play", "playing", "load")

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

    async def refresh(self) -> None:
        """Refresh cached state from device."""
        try:
            status = await self.player.client.get_player_status_model()
            device_info = await self.player.client.get_device_info_model()

            # Update StateSynchronizer with HTTP data
            status_dict = status.model_dump(exclude_none=False) if status else {}
            if "entity_picture" in status_dict:
                status_dict["image_url"] = status_dict.pop("entity_picture")
            for field_name in ["title", "artist", "album", "image_url"]:
                if field_name not in status_dict:
                    status_dict[field_name] = None

            # Replace "multiroom" with master's name for slaves
            if status_dict.get("source") == "multiroom":
                master_name = await self._get_master_name(device_info, status)
                if master_name:
                    status_dict["source"] = master_name
                    _LOGGER.debug(
                        "Replacing 'multiroom' with master name '%s' for slave %s", master_name, self.player.host
                    )

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
                master_name = await self._get_master_name(device_info, status)
                if master_name:
                    self.player._status_model.source = master_name
                    _LOGGER.debug(
                        "Updated status_model source to master name '%s' for slave %s", master_name, self.player.host
                    )

            self.player._device_info = device_info
            self.player._last_refresh = time.time()
            self.player._available = True

            # Copy ALL metadata from master to slave when linked
            # Slave devices report incomplete data - we populate from master
            if self.player.is_slave:
                master = None
                # First try: Use linked Group object if available
                if self.player._group and self.player._group.master:
                    master = self.player._group.master
                # Second try: Use master_ip from device_info to find master Player via player_finder
                elif device_info.master_ip and self.player._player_finder:
                    try:
                        master = self.player._player_finder(device_info.master_ip)
                    except Exception as e:
                        _LOGGER.debug(
                            "Failed to find master Player via player_finder for %s: %s", device_info.master_ip, e
                        )

                if master and master._status_model and self.player._status_model:
                    # Copy ALL playback metadata from master to slave
                    self.player._status_model.title = master._status_model.title
                    self.player._status_model.artist = master._status_model.artist
                    self.player._status_model.album = master._status_model.album
                    self.player._status_model.entity_picture = master._status_model.entity_picture
                    self.player._status_model.cover_url = master._status_model.cover_url
                    self.player._status_model.play_state = master._status_model.play_state
                    self.player._status_model.position = master._status_model.position
                    self.player._status_model.duration = master._status_model.duration

                    # Update state synchronizer with master's metadata
                    self.player._state_synchronizer.update_from_http(
                        {
                            "title": master._status_model.title,
                            "artist": master._status_model.artist,
                            "album": master._status_model.album,
                            "image_url": master._status_model.entity_picture or master._status_model.cover_url,
                            "play_state": master._status_model.play_state,
                            "position": master._status_model.position,
                            "duration": master._status_model.duration,
                        }
                    )

                    _LOGGER.debug(
                        "Copied metadata from master %s to slave %s: '%s' by %s",
                        master.host,
                        self.player.host,
                        master._status_model.title,
                        master._status_model.artist,
                    )

            # Clear source if device is no longer a slave
            if self.player._status_model and self.player._status_model.source:
                current_source = self.player._status_model.source
                is_currently_solo = (
                    self.player._group is None
                    and (not device_info.master_ip and not device_info.master_uuid)
                    and (device_info.group == "0" or not device_info.group)
                    and (not status.master_ip and not status.master_uuid)
                )
                source_is_multiroom_or_master = current_source == "multiroom" or (
                    current_source not in STANDARD_SOURCES and current_source is not None
                )
                if is_currently_solo and source_is_multiroom_or_master:
                    # Clear ALL slave metadata when no longer a slave
                    self.player._status_model.source = None
                    self.player._status_model._multiroom_mode = None
                    self.player._status_model.title = None
                    self.player._status_model.artist = None
                    self.player._status_model.album = None
                    self.player._status_model.entity_picture = None
                    self.player._status_model.cover_url = None

                    self.player._state_synchronizer.update_from_http(
                        {
                            "source": None,
                            "title": None,
                            "artist": None,
                            "album": None,
                            "image_url": None,
                        }
                    )
                    _LOGGER.debug(
                        "Cleared source and metadata for device %s - no longer a slave (was: %s)",
                        self.player.host,
                        current_source,
                    )

            # Update cached status_model from merged state
            merged = self.player._state_synchronizer.get_merged_state()
            if self.player._status_model:
                for field_name in ["play_state", "position", "duration", "source"]:
                    if field_name in merged and merged[field_name] is not None:
                        value = merged[field_name]
                        if field_name == "source" and value == "multiroom":
                            master_name = await self._get_master_name(
                                self.player._device_info, self.player._status_model
                            )
                            if master_name:
                                value = master_name
                                self.player._state_synchronizer.update_from_http({"source": master_name})
                                _LOGGER.debug(
                                    "Replaced 'multiroom' with master name '%s' in merged state for slave %s",
                                    master_name,
                                    self.player.host,
                                )
                        setattr(self.player._status_model, field_name, value)

                # Check again if source should be cleared after merged state update
                if self.player._status_model.source:
                    current_source = self.player._status_model.source
                    is_currently_solo = (
                        self.player._group is None
                        and (not device_info.master_ip and not device_info.master_uuid)
                        and (device_info.group == "0" or not device_info.group)
                        and (not status.master_ip and not status.master_uuid)
                    )
                    source_is_multiroom_or_master = current_source == "multiroom" or (
                        current_source not in STANDARD_SOURCES and current_source is not None
                    )
                    if is_currently_solo and source_is_multiroom_or_master:
                        # Clear ALL slave metadata when no longer a slave
                        self.player._status_model.source = None
                        self.player._status_model._multiroom_mode = None
                        self.player._status_model.title = None
                        self.player._status_model.artist = None
                        self.player._status_model.album = None
                        self.player._status_model.entity_picture = None
                        self.player._status_model.cover_url = None

                        self.player._state_synchronizer.update_from_http(
                            {
                                "source": None,
                                "title": None,
                                "artist": None,
                                "album": None,
                                "image_url": None,
                            }
                        )
                        _LOGGER.debug(
                            "Cleared source and metadata for device %s after merged state update - "
                            "no longer a slave (was: %s)",
                            self.player.host,
                            current_source,
                        )

                # Update volume and mute
                if "volume" in merged and merged["volume"] is not None:
                    vol = merged["volume"]
                    if isinstance(vol, float) and 0.0 <= vol <= 1.0:
                        self.player._status_model.volume = int(vol * 100)
                    else:
                        self.player._status_model.volume = int(vol) if vol is not None else None

                if "muted" in merged and merged["muted"] is not None:
                    self.player._status_model.mute = merged["muted"]

                # Update metadata from merged state
                for field_name in ["title", "artist", "album"]:
                    value = merged.get(field_name)
                    current_value = getattr(self.player._status_model, field_name, None)
                    if value != current_value:
                        setattr(self.player._status_model, field_name, value)
                        if _LOGGER.isEnabledFor(logging.DEBUG):
                            _LOGGER.debug("Updated %s from merged state: %s -> %s", field_name, current_value, value)

                if "image_url" in merged:
                    self.player._status_model.entity_picture = merged.get("image_url")
                    self.player._status_model.cover_url = merged.get("image_url")

            # Fetch audio output status if device supports it
            if self.player.client.capabilities.get("supports_audio_output", False):
                try:
                    audio_output_status = await self.player.client.get_audio_output_status()
                    self.player._audio_output_status = audio_output_status
                except Exception as err:
                    _LOGGER.debug("Failed to fetch audio output status for %s: %s", self.player.host, err)
                    self.player._audio_output_status = None

            # Fetch EQ presets if device supports EQ
            if self.player.client.capabilities.get("supports_eq", False):
                try:
                    eq_presets = await self.player.client.get_eq_presets()
                    self.player._eq_presets = eq_presets if eq_presets else None
                except Exception as err:
                    _LOGGER.debug("Failed to fetch EQ presets for %s: %s", self.player.host, err)
                    self.player._eq_presets = None

            # Fetch metadata (audio quality info) if device supports it
            if self.player.client.capabilities.get("supports_metadata", False):
                try:
                    metadata = await self.player.client.get_meta_info()
                    self.player._metadata = metadata if metadata else None
                except Exception as err:
                    _LOGGER.debug("Failed to fetch metadata for %s: %s", self.player.host, err)
                    self.player._metadata = None

            # Fetch Bluetooth history (for output device list) - less frequently
            # BT pairing doesn't change often, so fetch every 60 seconds instead of every poll
            if not hasattr(self.player, "_last_bt_history_check"):
                self.player._last_bt_history_check = 0

            now_time = time.time()
            if now_time - self.player._last_bt_history_check > 60:  # 60 seconds
                try:
                    bluetooth_history = await self.player.client.get_bluetooth_history()
                    self.player._bluetooth_history = bluetooth_history if bluetooth_history else []
                    self.player._last_bt_history_check = now_time
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
