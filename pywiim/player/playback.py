"""Playback control - shuffle, repeat, loop modes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..exceptions import WiiMError

if TYPE_CHECKING:
    from . import Player


class PlaybackControl:
    """Manages playback mode operations."""

    def __init__(self, player: Player) -> None:
        """Initialize playback control.

        Args:
            player: Parent Player instance.
        """
        self.player = player

    async def set_shuffle(self, enabled: bool) -> None:
        """Set shuffle mode on or off, preserving current repeat state.

        Args:
            enabled: True to enable shuffle, False to disable.

        Raises:
            WiiMError: If shuffle cannot be controlled on current source.
        """
        from .properties import PlayerProperties

        props = PlayerProperties(self.player)

        # Check if shuffle is supported for current source
        if not props.shuffle_supported:
            source = props.source or "unknown"
            raise WiiMError(
                f"Shuffle cannot be controlled when playing from '{source}'. "
                f"Shuffle is controlled by the source device/app, not the WiiM device. "
                f"Supported sources: USB, Line In, Optical, Coaxial, Playlist, Preset."
            )

        repeat_mode = props.repeat_mode
        is_repeat_one = repeat_mode == "one"
        is_repeat_all = repeat_mode == "all"

        if enabled:
            if is_repeat_one:
                loop_mode = 5  # shuffle + repeat_one
            elif is_repeat_all:
                loop_mode = 6  # shuffle + repeat_all
            else:
                loop_mode = 4  # shuffle only
        else:
            if is_repeat_one:
                loop_mode = 1  # repeat_one only
            elif is_repeat_all:
                loop_mode = 2  # repeat_all only
            else:
                loop_mode = 0  # normal

        # Call API (raises on failure)
        await self.player.client.set_loop_mode(loop_mode)

        # Update cached state immediately (optimistic)
        if self.player._status_model:
            self.player._status_model.loop_mode = loop_mode

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def set_repeat(self, mode: str) -> None:
        """Set repeat mode, preserving current shuffle state.

        Args:
            mode: Repeat mode - "off", "one", or "all".

        Raises:
            ValueError: If mode is not valid.
            WiiMError: If repeat cannot be controlled on current source.
        """
        mode_lower = mode.lower().strip()
        if mode_lower not in ("off", "one", "all"):
            raise ValueError(f"Invalid repeat mode: {mode}. Valid values: 'off', 'one', 'all'")

        from .properties import PlayerProperties

        props = PlayerProperties(self.player)

        # Check if repeat is supported for current source
        if not props.repeat_supported:
            source = props.source or "unknown"
            raise WiiMError(
                f"Repeat cannot be controlled when playing from '{source}'. "
                f"Repeat is controlled by the source device/app, not the WiiM device. "
                f"Supported sources: USB, Line In, Optical, Coaxial, Playlist, Preset."
            )

        shuffle_enabled = props.shuffle_state or False

        if shuffle_enabled:
            if mode_lower == "one":
                loop_mode = 5  # shuffle + repeat_one
            elif mode_lower == "all":
                loop_mode = 6  # shuffle + repeat_all
            else:  # off
                loop_mode = 4  # shuffle only
        else:
            if mode_lower == "one":
                loop_mode = 1  # repeat_one only
            elif mode_lower == "all":
                loop_mode = 2  # repeat_all only
            else:  # off
                loop_mode = 0  # normal

        # Call API (raises on failure)
        await self.player.client.set_loop_mode(loop_mode)

        # Update cached state immediately (optimistic)
        if self.player._status_model:
            self.player._status_model.loop_mode = loop_mode

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()
