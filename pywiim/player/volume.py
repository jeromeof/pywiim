"""Volume and mute control."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Player


class VolumeControl:
    """Manages volume and mute operations."""

    def __init__(self, player: Player) -> None:
        """Initialize volume control.

        Args:
            player: Parent Player instance.
        """
        self.player = player

    async def set_volume(self, volume: float) -> None:
        """Set volume level (0.0-1.0).

        Sets volume on THIS device only. Does not propagate to other devices in a group.
        Use Group.set_volume_all() for group-wide volume changes.

        Args:
            volume: Volume level from 0.0 to 1.0.
        """
        # Set volume on this device only
        # Call API (raises on failure)
        await self.player.client.set_volume(volume)

        # Update cached state immediately (optimistic)
        volume_int = int(max(0.0, min(volume, 1.0)) * 100)
        if self.player._status_model:
            self.player._status_model.volume = volume_int

        # Update state synchronizer (expects 0-100 range)
        self.player._state_synchronizer.update_from_http({"volume": volume_int})

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

        # If in group, fire master's callback for virtual entity updates
        if self.player.group and self.player.group.master._on_state_changed:
            # Don't fire master's callback if this IS the master (already fired above)
            if self.player.group.master != self.player:
                self.player.group.master._on_state_changed()

    async def set_mute(self, mute: bool) -> None:
        """Set mute state.

        Sets mute on THIS device only. Does not propagate to other devices in a group.
        Use Group.mute_all() for group-wide mute changes.

        Args:
            mute: True to mute, False to unmute.
        """
        # Set mute on this device only
        # Call API (raises on failure)
        await self.player.client.set_mute(mute)

        # Update cached state immediately (optimistic)
        if self.player._status_model:
            self.player._status_model.mute = mute

        # Update state synchronizer
        self.player._state_synchronizer.update_from_http({"muted": mute})

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

        # If in group, fire master's callback for virtual entity updates
        if self.player.group and self.player.group.master._on_state_changed:
            # Don't fire master's callback if this IS the master (already fired above)
            if self.player.group.master != self.player:
                self.player.group.master._on_state_changed()

    async def get_volume(self) -> float | None:
        """Get current volume level by querying device."""
        from .statemgr import StateManager

        status = await StateManager(self.player).get_status()
        return status.volume / 100.0 if status.volume is not None else None

    async def get_muted(self) -> bool | None:
        """Get current mute state by querying device."""
        from .statemgr import StateManager

        status = await StateManager(self.player).get_status()
        return status.mute
