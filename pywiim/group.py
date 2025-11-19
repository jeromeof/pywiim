"""Group class - represents a multiroom group of players.

This module provides the Group class, which manages relationships between
players in a multiroom group and provides group-level operations.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from .exceptions import WiiMError
from .models import PlayerStatus

if TYPE_CHECKING:
    from .player import Player
else:
    Player = None  # Will be imported when needed to avoid circular import

_LOGGER = logging.getLogger(__name__)


class Group:
    """Represents a multiroom group of players.

    A Group is a first-class object that owns the relationships between players.
    It provides group-level operations for volume, mute, and playback control.

    Key behaviors:
    - Group volume = MAX volume of any device (so moving any slider updates group)
    - Group mute = ALL devices are muted
    - Slave commands propagate to master, master syncs to all slaves
    - Playback commands go to master, which syncs to slaves

    Example:
        ```python
        # Create group
        master = Player(WiiMClient("192.168.1.100"))
        group = await master.create_group()

        # Add slaves
        slave1 = Player(WiiMClient("192.168.1.101"))
        await group.add_slave(slave1)

        # Group operations
        await group.set_volume_all(0.5)
        await group.mute_all(False)
        await group.play()

        # Group state queries
        volume = await group.get_volume_level()
        is_muted = await group.is_muted()
        ```

    Args:
        master: The master player of the group.
    """

    def __init__(self, master: Player) -> None:
        """Initialize a Group instance.

        Args:
            master: The master player of the group.
        """
        self.master = master
        self.slaves: list[Player] = []
        master._group = self

    @property
    def all_players(self) -> list[Player]:
        """All players in the group (master + slaves).

        Returns:
            List of all players, with master first.
        """
        return [self.master] + self.slaves

    @property
    def size(self) -> int:
        """Number of players in the group.

        Returns:
            Total number of players (master + slaves).
        """
        return 1 + len(self.slaves)

    def add_slave(self, slave: Player) -> None:
        """Add a slave to the group.

        This is called automatically when a player joins via join_group().
        The slave must already have joined via the API.

        Args:
            slave: The slave player to add.

        Raises:
            ValueError: If the slave is already in a group.
        """
        if slave._group is not None:
            raise ValueError(f"Player {slave.host} is already in a group")

        self.slaves.append(slave)
        slave._group = self

        # Set source to master's name when slave joins group
        # Set in both status model and state synchronizer
        if slave._status_model:
            master_name = self.master.name or self.master.host
            slave._status_model.source = master_name
            slave._status_model._multiroom_mode = True
            # Also update state synchronizer
            slave._state_synchronizer.update_from_http({"source": master_name})
            _LOGGER.debug("Set source to master name '%s' for slave %s after joining group", master_name, slave.host)

        _LOGGER.debug("Added slave %s to group (master: %s)", slave.host, self.master.host)

    def remove_slave(self, slave: Player) -> None:
        """Remove a slave from the group.

        This is called automatically when a slave leaves via leave_group().

        Args:
            slave: The slave player to remove.
        """
        if slave in self.slaves:
            self.slaves.remove(slave)
            slave._group = None

            # Clear source when slave leaves group (could be "multiroom" or master name)
            # Clear from both status model and state synchronizer
            if slave._status_model:
                current_source = slave._status_model.source
                # Check if source is multiroom or matches master's name/host
                should_clear = False
                if current_source == "multiroom":
                    should_clear = True
                elif self.master:
                    master_name = self.master.name or self.master.host
                    if current_source == master_name:
                        should_clear = True

                if should_clear:
                    # Set to None (empty) when leaving group
                    slave._status_model.source = None
                    slave._status_model._multiroom_mode = None
                    # Also clear from state synchronizer to prevent refresh() from restoring it
                    slave._state_synchronizer.update_from_http({"source": None})
                    _LOGGER.debug(
                        "Cleared source for slave %s after leaving group (was: %s)", slave.host, current_source
                    )

                # Clear metadata and artwork when leaving group
                # This shows the WiiM default state instead of stale metadata from the group
                slave._status_model.title = None
                slave._status_model.artist = None
                slave._status_model.album = None
                slave._status_model.entity_picture = None
                slave._status_model.cover_url = None
                # Also clear from state synchronizer
                slave._state_synchronizer.update_from_http(
                    {
                        "title": None,
                        "artist": None,
                        "album": None,
                        "entity_picture": None,
                        "cover_url": None,
                    }
                )
                _LOGGER.debug("Cleared metadata and artwork for slave %s after leaving group", slave.host)

            _LOGGER.debug("Removed slave %s from group (master: %s)", slave.host, self.master.host)

    async def disband(self) -> None:
        """Disband the group.

        The HTTP API call will raise `WiiMError` if the disband fails. If it returns
        successfully, the disband succeeded and all players are now solo.

        All slaves leave the group, and the master becomes solo.
        This is called automatically when the master leaves the group.

        Raises:
            WiiMError: If the HTTP API call fails (disband rejected by device).
        """
        _LOGGER.debug("Disbanding group (master: %s)", self.master.host)

        # Store references before disbanding (needed for callbacks)
        master = self.master
        slaves = list(self.slaves)

        # Step 1: Call API (raises WiiMError if it fails)
        # Call API directly (bypass client state checks - we manage state in Player)
        try:
            await self.master.client._request("/httpapi.asp?command=multiroom:Ungroup")
        except WiiMError as err:
            _LOGGER.warning("Failed to delete group via API: %s", err)
            # Continue with cleanup anyway (device may have already disbanded)

        # Step 2: Clean up group object immediately (API success = disband succeeded)
        for slave in slaves:
            self.remove_slave(slave)

        self.master._group = None

        # Step 3: Call callbacks if provided
        if master._on_state_changed:
            try:
                master._on_state_changed()
            except Exception as err:
                _LOGGER.debug("Error calling master's on_state_changed callback: %s", err)

        for slave in slaves:
            if slave._on_state_changed:
                try:
                    slave._on_state_changed()
                except Exception as err:
                    _LOGGER.debug("Error calling slave's on_state_changed callback: %s", err)

        _LOGGER.info("Group disbanded (master: %s)", master.host)

    # ===== Group-Level Volume and Mute Control =====

    async def set_volume_all(self, volume: float) -> None:
        """Set virtual master volume with proportional changes to all devices.

        When virtual master volume changes, each device (master + all slaves) changes
        by the same absolute percentage points. This maintains relative volume differences
        between devices while changing the overall group volume.

        Example: If virtual master is 50% and changed to 60% (+10 percentage points), then:
        - Master at 50% → 60% (+10 percentage points)
        - Slave at 30% → 40% (+10 percentage points)
        - Slave at 40% → 50% (+10 percentage points)

        Virtual master volume is always the MAX of all device volumes (read-only property).

        Args:
            volume: Target virtual master volume level (0.0-1.0).

        Raises:
            WiiMError: If the request fails.
        """
        # Get current virtual master volume (MAX of all devices)
        current_virtual_vol = self.volume_level

        if current_virtual_vol is None or current_virtual_vol == 0.0:
            # No current volume or all devices at 0 - set all to target volume
            _LOGGER.debug("Setting volume on all devices to %.2f (no current virtual master)", volume)
            tasks = [self.master.set_volume(volume)]
            tasks.extend([slave.set_volume(volume) for slave in self.slaves])
            await asyncio.gather(*tasks, return_exceptions=True)
            return

        # Calculate absolute change in percentage points
        # If virtual master goes from 50% to 60%, that's +10 percentage points
        # Each device should change by the same absolute amount
        delta = volume - current_virtual_vol

        # Apply absolute change to each device
        _LOGGER.debug(
            "Setting virtual master volume: %.2f -> %.2f (delta: %+.2f) on master + %d slaves",
            current_virtual_vol,
            volume,
            delta,
            len(self.slaves),
        )

        # Update master first, then each slave sequentially to make logging clearer
        players = [("master", self.master, self.master.volume_level or 0.0)]
        players.extend((f"slave-{i+1}", slave, slave.volume_level or 0.0) for i, slave in enumerate(self.slaves))

        for role, player, current in players:
            target = max(0.0, min(1.0, current + delta))
            _LOGGER.info(
                "group:set_volume start host=%s role=%s current=%.2f target=%.2f delta=%+.2f",
                player.host,
                role,
                current,
                target,
                delta,
            )
            try:
                await player.set_volume(target)
                _LOGGER.info("group:set_volume done host=%s role=%s target=%.2f", player.host, role, target)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("group:set_volume error host=%s role=%s: %s", player.host, role, err)

    async def mute_all(self, mute: bool) -> None:
        """Mute/unmute ALL devices in group.

        Sets mute on master AND all slaves explicitly. Mute states do NOT propagate
        between devices - each device maintains independent mute state. Virtual master
        mute is True only when ALL devices are muted (read-only property).

        Args:
            mute: True to mute, False to unmute.

        Raises:
            WiiMError: If the request fails.
        """
        # Set mute on master and all slaves explicitly
        # Note: Mute states do NOT propagate between devices
        _LOGGER.debug("Setting mute on all devices: master + %d slaves to %s", len(self.slaves), mute)

        tasks = [self.master.set_mute(mute)]
        tasks.extend([slave.set_mute(mute) for slave in self.slaves])
        await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def volume_level(self) -> float | None:
        """Virtual master volume = MAXIMUM volume of any device (read-only).

        Virtual master volume is always the highest volume among all devices
        (master + all slaves). This is a computed property - volumes do NOT
        propagate between devices. Each device maintains independent volume.

        Uses cached state - call refresh() on players first for accuracy.

        Returns:
            Maximum volume level (0.0-1.0) or None if unknown.
        """
        volumes = []

        master_vol = self.master.volume_level
        if master_vol is not None:
            volumes.append(master_vol)

        for slave in self.slaves:
            slave_vol = slave.volume_level
            if slave_vol is not None:
                volumes.append(slave_vol)

        if not volumes:
            return None

        return max(volumes)

    @property
    def is_muted(self) -> bool | None:
        """Virtual master mute = ALL devices are muted (read-only).

        Virtual master mute is True only when EVERY device (master + all slaves)
        is muted. This is a computed property - mute states do NOT propagate
        between devices. Each device maintains independent mute state.

        Uses cached state - call refresh() on players first for accuracy.

        Returns:
            True if all devices are muted, False if any device is not muted,
            None if mute state is unknown for any device.
        """
        mute_states = []

        master_mute = self.master.is_muted
        if master_mute is not None:
            mute_states.append(master_mute)

        for slave in self.slaves:
            slave_mute = slave.is_muted
            if slave_mute is not None:
                mute_states.append(slave_mute)

        if not mute_states:
            return None

        # All must be muted
        return all(mute_states)

    async def get_volume_level(self) -> float | None:
        """Get group volume = MAXIMUM volume of any device (queries devices).

        This ensures moving any member's slider updates the group entity.
        Queries all devices in parallel for efficiency.

        Returns:
            Maximum volume level (0.0-1.0) or None if unknown.
        """
        # Query all devices in parallel
        volumes = await asyncio.gather(
            self.master.get_volume(),
            *[slave.get_volume() for slave in self.slaves],
            return_exceptions=True,
        )

        # Filter out exceptions and None values
        valid_volumes = [v for v in volumes if isinstance(v, (int, float)) and v is not None]

        if not valid_volumes:
            return None

        return max(valid_volumes)

    async def get_muted(self) -> bool | None:
        """Get group mute = ALL devices are muted (queries devices).

        Returns True only if every device (master + all slaves) is muted.
        Queries all devices in parallel for efficiency.

        Returns:
            True if all devices are muted, False if any device is not muted,
            None if mute state is unknown for any device.
        """
        # Query all devices in parallel
        mute_states = await asyncio.gather(
            self.master.get_muted(),
            *[slave.get_muted() for slave in self.slaves],
            return_exceptions=True,
        )

        # Filter out exceptions and None values
        valid_mutes = [m for m in mute_states if isinstance(m, bool)]

        if not valid_mutes:
            return None

        # All must be muted
        return all(valid_mutes)

    # ===== Group-Level Playback Control =====

    async def play(self) -> None:
        """Start playback - command goes to master, which syncs to slaves.

        Raises:
            WiiMError: If the request fails.
        """
        await self.master.play()

    async def pause(self) -> None:
        """Pause playback - command goes to master, which syncs to slaves.

        Raises:
            WiiMError: If the request fails.
        """
        await self.master.pause()

    async def stop(self) -> None:
        """Stop playback - command goes to master, which syncs to slaves.

        Raises:
            WiiMError: If the request fails.
        """
        await self.master.stop()

    async def next_track(self) -> None:
        """Skip to next track - command goes to master, which syncs to slaves.

        Raises:
            WiiMError: If the request fails.
        """
        await self.master.next_track()

    async def previous_track(self) -> None:
        """Skip to previous track - command goes to master, which syncs to slaves.

        Raises:
            WiiMError: If the request fails.
        """
        await self.master.previous_track()

    @property
    def play_state(self) -> str | None:
        """Group play state = master's play state (from cached state).

        Returns:
            Play state string (e.g., 'play', 'pause', 'stop', 'idle') or None.
        """
        return self.master.play_state

    async def get_play_state(self) -> str:
        """Get group play state = master's play state (queries device).

        Returns:
            Play state string (e.g., 'play', 'pause', 'stop').
        """
        return await self.master.get_play_state()

    async def get_status(self) -> PlayerStatus:
        """Get master's player status (represents group playback state).

        Returns:
            PlayerStatus model with current playback state.
        """
        return await self.master.get_status()

    def __repr__(self) -> str:
        """String representation."""
        return f"Group(master={self.master.host!r}, slaves={len(self.slaves)})"
