"""Helper functions for building and managing group state.

This module provides framework-agnostic helper functions for working with
multiroom groups, including building group state from multiple devices and
discovering group members.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import GroupDeviceState, GroupState

if TYPE_CHECKING:
    from .player import Player

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "build_group_state_from_players",
]


async def build_group_state_from_players(
    master_player: Player,
    slave_players: list[Player] | None = None,
) -> GroupState:
    """Build group state from Player instances.

    This helper function builds a GroupState from Player instances (from
    pywiim.player.Player). It extracts state from the cached Player state.

    Args:
        master_player: Player instance for the master device.
        slave_players: Optional list of Player instances for slave devices.

    Returns:
        GroupState with complete group information.

    Raises:
        RuntimeError: If master_player is not the group master.
        ValueError: If player state is not available.

    Example:
        ```python
        from pywiim import Player, build_group_state_from_players

        master = Player(WiiMClient("192.168.1.100"))
        slave1 = Player(WiiMClient("192.168.1.101"))

        await master.refresh()
        await slave1.refresh()

        group_state = await build_group_state_from_players(
            master,
            slave_players=[slave1]
        )
        ```
    """
    import time

    # Verify master
    if master_player.role != "master":
        raise RuntimeError(f"Player {master_player.host} is not the group master (role: {master_player.role})")

    # Get master state
    if master_player._status_model is None:
        raise ValueError("Master player state not available - call refresh() first")

    master_status = master_player._status_model
    now = time.time()

    # Build master device state
    master_state = GroupDeviceState(
        host=master_player.host,
        role="master",
        volume=master_status.volume,
        mute=master_status.mute,
        play_state=master_status.play_state,
        position=master_status.position,
        duration=master_status.duration,
        source=master_status.source,
        title=master_status.title,
        album=master_status.album,
        last_updated=now,
    )

    # Build slave states
    slave_states: list[GroupDeviceState] = []
    slave_hosts: list[str] = []

    if slave_players:
        for slave_player in slave_players:
            if slave_player._status_model is None:
                _LOGGER.warning(
                    "Slave player %s state not available - skipping",
                    slave_player.host,
                )
                continue

            slave_status = slave_player._status_model
            slave_hosts.append(slave_player.host)

            slave_states.append(
                GroupDeviceState(
                    host=slave_player.host,
                    role="slave",
                    volume=slave_status.volume,
                    mute=slave_status.mute,
                    play_state=slave_status.play_state,
                    position=slave_status.position,
                    duration=slave_status.duration,
                    source=slave_status.source,
                    title=slave_status.title,
                    album=slave_status.album,
                    last_updated=now,
                )
            )

    # Calculate group volume/mute (MAX volume, ALL muted)
    volumes = [s.volume for s in [master_state] + slave_states if s.volume is not None]
    mutes = [s.mute for s in [master_state] + slave_states if s.mute is not None]

    group_volume = max(volumes) if volumes else None
    group_muted = all(mutes) if mutes else None

    return GroupState(
        master_host=master_player.host,
        slave_hosts=slave_hosts,
        master_state=master_state,
        slave_states=slave_states,
        play_state=master_status.play_state,
        position=master_status.position,
        duration=master_status.duration,
        source=master_status.source,
        title=master_status.title,
        artist=master_status.artist,
        album=master_status.album,
        volume_level=group_volume,
        is_muted=group_muted,
        created_at=now,
        last_updated=now,
    )
