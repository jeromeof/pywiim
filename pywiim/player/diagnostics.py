"""Diagnostics information."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import Player


class DiagnosticsCollector:
    """Collects diagnostic information."""

    def __init__(self, player: Player) -> None:
        """Initialize diagnostics collector.

        Args:
            player: Parent Player instance.
        """
        self.player = player

    async def get_diagnostics(self) -> dict[str, Any]:
        """Get comprehensive diagnostic information for this player."""
        # Import __version__ here to avoid circular import
        from .. import __version__

        diagnostics: dict[str, Any] = {
            "timestamp": time.time(),
            "host": self.player.host,
            "pywiim_version": __version__,
        }

        # Device information
        try:
            if self.player._device_info:
                diagnostics["device"] = {
                    "uuid": self.player._device_info.uuid,
                    "name": self.player._device_info.name,
                    "model": self.player._device_info.model,
                    "firmware": self.player._device_info.firmware,
                    "mac": self.player._device_info.mac,
                    "ip": self.player._device_info.ip,
                    "preset_key": self.player._device_info.preset_key,
                    "input_list": self.player._device_info.input_list,
                    "hardware": self.player._device_info.hardware,
                    "wmrm_version": self.player._device_info.wmrm_version,
                    "mcu_ver": self.player._device_info.mcu_ver,
                    "dsp_ver": self.player._device_info.dsp_ver,
                }
            else:
                from .statemgr import StateManager

                device_info = await StateManager(self.player).get_device_info()
                diagnostics["device"] = {
                    "uuid": device_info.uuid,
                    "name": device_info.name,
                    "model": device_info.model,
                    "firmware": device_info.firmware,
                    "mac": device_info.mac,
                    "ip": device_info.ip,
                    "preset_key": device_info.preset_key,
                    "input_list": device_info.input_list,
                    "hardware": device_info.hardware,
                    "wmrm_version": device_info.wmrm_version,
                    "mcu_ver": device_info.mcu_ver,
                    "dsp_ver": device_info.dsp_ver,
                }
        except Exception as err:
            diagnostics["device"] = {"error": str(err)}

        # Current status
        try:
            if self.player._status_model:
                diagnostics["status"] = {
                    "play_state": self.player._status_model.play_state,
                    "volume": self.player._status_model.volume,
                    "mute": self.player._status_model.mute,
                    "source": self.player._status_model.source,
                    "position": self.player._status_model.position,
                    "duration": self.player._status_model.duration,
                    "title": self.player._status_model.title,
                    "artist": self.player._status_model.artist,
                    "album": self.player._status_model.album,
                }
            else:
                from .statemgr import StateManager

                status = await StateManager(self.player).get_status()
                diagnostics["status"] = {
                    "play_state": status.play_state,
                    "volume": status.volume,
                    "mute": status.mute,
                    "source": status.source,
                    "position": status.position,
                    "duration": status.duration,
                    "title": status.title,
                    "artist": status.artist,
                    "album": status.album,
                }
        except Exception as err:
            diagnostics["status"] = {"error": str(err)}

        # Capabilities
        try:
            diagnostics["capabilities"] = self.player.client.capabilities.copy()
        except Exception as err:
            diagnostics["capabilities"] = {"error": str(err)}

        # Multiroom information
        try:
            multiroom = await self.player.client.get_multiroom_status()
            diagnostics["multiroom"] = multiroom
        except Exception:
            diagnostics["multiroom"] = None

        # Group info
        try:
            group_info = await self.player.client.get_device_group_info()
            diagnostics["group_info"] = {
                "role": group_info.role,
                "master_host": group_info.master_host,
                "master_uuid": group_info.master_uuid,
                "slave_hosts": group_info.slave_hosts,
                "slave_count": group_info.slave_count,
            }
        except Exception:
            diagnostics["group_info"] = None

        # UPnP statistics (if available)
        try:
            if hasattr(self.player, "_upnp_eventer") and self.player._upnp_eventer:
                diagnostics["upnp"] = self.player._upnp_eventer.statistics
            else:
                diagnostics["upnp"] = None
        except Exception:
            diagnostics["upnp"] = None

        # API statistics
        try:
            diagnostics["api_stats"] = self.player.client.api_stats
        except Exception:
            diagnostics["api_stats"] = None

        # Connection statistics
        try:
            diagnostics["connection_stats"] = self.player.client.connection_stats
        except Exception:
            diagnostics["connection_stats"] = None

        # Audio output status
        try:
            if self.player._audio_output_status:
                diagnostics["audio_output"] = self.player._audio_output_status
            else:
                if self.player.client.capabilities.get("supports_audio_output", False):
                    # Use player-level method which automatically updates the cache
                    audio_output = await self.player.get_audio_output_status()
                    diagnostics["audio_output"] = audio_output
                else:
                    diagnostics["audio_output"] = None
        except Exception:
            diagnostics["audio_output"] = None

        # EQ settings
        try:
            if self.player.client.capabilities.get("supports_eq", False):
                eq = await self.player.client.get_eq()
                diagnostics["eq"] = eq
            else:
                diagnostics["eq"] = None
        except Exception:
            diagnostics["eq"] = None

        # Role
        diagnostics["role"] = self.player.role
        diagnostics["available"] = self.player.available

        return diagnostics

    async def reboot(self) -> None:
        """Reboot the device.

        Note: This command may not return a response as the device will restart.
        The method handles this gracefully and considers the command successful
        even if the device stops responding.

        Raises:
            WiiMError: If the request fails before the device reboots.
        """
        await self.player.client.reboot()
        self.player._available = False

    async def sync_time(self, ts: int | None = None) -> None:
        """Synchronize device time with system time or provided timestamp.

        Args:
            ts: Unix timestamp (seconds since epoch). If None, uses current system time.

        Raises:
            WiiMError: If the request fails.
        """
        await self.player.client.sync_time(ts)
