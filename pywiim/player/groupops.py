"""Group operations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal, cast

from ..role import RoleDetectionResult

if TYPE_CHECKING:
    from ..group import Group
    from . import Player

_LOGGER = logging.getLogger(__name__)


class GroupOperations:
    """Manages group operations."""

    def __init__(self, player: Player) -> None:
        """Initialize group operations.

        Args:
            player: Parent Player instance.
        """
        self.player = player

    def _notify_all_group_members(self, group: Group | None) -> None:
        """Notify all players in a group of state changes.

        This ensures all coordinators/integrations are notified when group
        membership changes, so UIs update immediately across all group members.

        Args:
            group: The group whose members should be notified, or None.
        """
        if not group:
            return

        for player in group.all_players:
            if player._on_state_changed:
                try:
                    player._on_state_changed()
                except Exception as err:
                    _LOGGER.debug("Error calling on_state_changed callback for %s: %s", player.host, err)

    async def _synchronize_group_state(self) -> None:
        """Synchronize group state from device API state."""
        if self.player._status_model is None or self.player._device_info is None:
            return

        try:
            group_info = await self.player.client.get_device_group_info()
            detected_role = group_info.role
            role_result = RoleDetectionResult(
                role=detected_role,
                master_host=group_info.master_host,
                master_uuid=group_info.master_uuid,
                slave_hosts=group_info.slave_hosts,
                slave_count=group_info.slave_count,
            )
        except Exception as err:
            # get_device_group_info() failed - can't determine role reliably
            # Keep current Group structure to avoid flipping (don't use stale multiroom data)
            _LOGGER.warning(
                "Failed to get device group info for %s: %s - keeping current role %s",
                self.player.host,
                err,
                self.player.role,
            )
            # Use current role from Group structure - don't fall back to detect_role() which uses stale multiroom data
            # Cast to Literal type to match DeviceGroupInfo.role type
            detected_role = cast(Literal["solo", "master", "slave"], self.player.role)
            role_result = RoleDetectionResult(
                role=detected_role,
                master_host=None,
                master_uuid=None,
                slave_hosts=[],
                slave_count=0,
            )

        from ..group import Group as GroupClass

        # Sync Group structure to match device API state
        # Case 1: Device is solo but we think it's in a group
        if detected_role == "solo" and self.player._group is not None:
            if self.player._group.master == self.player and len(self.player._group.slaves) == 0:
                _LOGGER.debug(
                    "Device %s is solo but has empty group object - keeping it (ready for slaves)", self.player.host
                )
            else:
                _LOGGER.debug("Device %s is solo but has group object - clearing group", self.player.host)
                old_group = self.player._group
                if self.player._group.master != self.player:
                    self.player._group.remove_slave(self.player)
                else:
                    for slave in list(self.player._group.slaves):
                        self.player._group.remove_slave(slave)
                    self.player._group.master._group = None
                self.player._group = None
                # Notify all members of the disbanded group
                self._notify_all_group_members(old_group)

        # Case 2: Device is master but we don't have a group object
        elif detected_role == "master" and self.player._group is None:
            _LOGGER.debug("Device %s is master but has no group object - creating group", self.player.host)
            group = GroupClass(self.player)
            self.player._group = group

            if role_result.slave_hosts:
                for slave_host in role_result.slave_hosts:
                    _LOGGER.debug("Master %s has slave %s but no Player object available", self.player.host, slave_host)

            # Notify the master that it's now in a group
            if self.player._on_state_changed:
                try:
                    self.player._on_state_changed()
                except Exception as err:
                    _LOGGER.debug("Error calling on_state_changed callback for %s: %s", self.player.host, err)

        # Case 3: Device is master and we have a group - sync slave list
        elif detected_role == "master" and self.player._group is not None:
            slaves_changed = False

            if self.player._group.master != self.player:
                _LOGGER.warning("Device %s is master but group object says we're a slave - fixing", self.player.host)
                old_group = self.player._group
                self.player._group = None
                old_group.remove_slave(self.player)
                group = GroupClass(self.player)
                self.player._group = group
                slaves_changed = True

            if role_result.slave_hosts:
                device_slave_hosts = set(role_result.slave_hosts)
                for slave in list(self.player._group.slaves):
                    if slave.host not in device_slave_hosts:
                        _LOGGER.debug("Removing slave %s from group (no longer in device state)", slave.host)
                        self.player._group.remove_slave(slave)
                        slaves_changed = True

            # Notify all group members if slaves changed
            if slaves_changed:
                self._notify_all_group_members(self.player._group)

        # Case 4: Device is slave but we don't have a group object
        elif detected_role == "slave" and self.player._group is None:
            _LOGGER.debug("Device %s is slave but has no group object - need master Player object", self.player.host)

        # Case 5: Device is slave and we have a group - verify master matches
        elif detected_role == "slave" and self.player._group is not None:
            if self.player._group.master == self.player:
                _LOGGER.warning("Device %s is slave but group object says we're master - fixing", self.player.host)
                old_group = self.player._group
                for slave in list(old_group.slaves):
                    old_group.remove_slave(slave)
                old_group.master._group = None
                self.player._group = None
                # Notify old group members
                self._notify_all_group_members(old_group)
            else:
                if role_result.master_host and self.player._group.master.host != role_result.master_host:
                    _LOGGER.warning(
                        "Device %s is slave but master host mismatch: group=%s, device=%s",
                        self.player.host,
                        self.player._group.master.host,
                        role_result.master_host,
                    )
                    old_group = self.player._group
                    self.player._group = None
                    old_group.remove_slave(self.player)
                    # Notify old group members
                    self._notify_all_group_members(old_group)

    async def create_group(self) -> Group:
        """Create a new group with this player as master."""
        if self.player.is_slave:
            _LOGGER.debug("Player %s is slave, leaving group before creating new group", self.player.host)
            await self.leave_group()

        if self.player.is_master:
            return self.player._group  # type: ignore[return-value]

        await self.player.client.create_group()

        if self.player._group is None:
            from ..group import Group as GroupClass

            group = GroupClass(self.player)
            self.player._group = group

        if self.player._on_state_changed:
            try:
                self.player._on_state_changed()
            except Exception as err:
                _LOGGER.debug("Error calling on_state_changed callback: %s", err)

        return self.player._group

    async def join_group(self, master: Any) -> None:
        """Join this player to another player."""
        old_group = self.player._group if self.player.is_slave else None

        if self.player.is_master:
            _LOGGER.debug("Player %s is master, disbanding group before join", self.player.host)
            await self.leave_group()

        if master.is_slave:
            _LOGGER.debug("Target %s is slave, having it leave group first", master.host)
            await master.leave_group()

        if master.is_solo:
            _LOGGER.debug("Target %s is solo, creating group", master.host)
            await GroupOperations(master).create_group()

        await self.player.client.join_slave(master.host)

        if old_group is not None:
            old_group.remove_slave(self.player)

        if master.group is not None:
            master.group.add_slave(self.player)

        # Notify all players in the new group (including the joiner and master)
        self._notify_all_group_members(master.group)

        # Also notify old group members if the joiner left a different group
        if old_group is not None and old_group != master.group:
            self._notify_all_group_members(old_group)

    async def leave_group(self) -> None:
        """Leave the current group."""
        if self.player.is_solo:
            raise RuntimeError("Player is not in a group")

        group = self.player._group
        if group is None:
            raise RuntimeError("Group reference is None")

        master = group.master if group else None

        # Notify all members BEFORE disbanding/leaving (while group structure is intact)
        self._notify_all_group_members(group)

        if self.player.is_master:
            await group.disband()
        else:
            await self.player.client._request("/httpapi.asp?command=multiroom:Ungroup")
            group.remove_slave(self.player)

            if len(group.slaves) == 0:
                _LOGGER.debug("Group is now empty, auto-disbanding (master: %s)", master.host if master else "unknown")
                await group.disband()
