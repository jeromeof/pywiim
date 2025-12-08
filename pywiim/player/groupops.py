"""Group operations.

# pragma: allow-long-file groupops-cohesive
# This file exceeds the 600 LOC hard limit (680 lines) but is kept as a single
# cohesive unit because:
# 1. Single responsibility: Group operations (create, join, leave, synchronize)
# 2. Well-organized: Clear sections for group management and metadata propagation
# 3. Tight coupling: All methods work together for group operations
# 4. Maintainable: Clear structure, follows group operations design pattern
# 5. Natural unit: Represents one concept (group operations)
# Splitting would add complexity without clear benefit.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

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
        """Synchronize group state from device API state.

        Uses a "Master-Centric" approach for robust role detection:
        1. Slaves often don't know who their master is.
        2. Only Masters reliably know their slave list.
        3. We use fast status-based detection to avoid expensive getDeviceInfo calls.
        4. The 'group' field is authoritative for slave detection:
           - group == "1" means device is a slave
           - group == "0" means device is solo or master (check slave list to determine)
        5. We only call get_device_group_info() (which uses getDeviceInfo) when:
           - Potential slave detected (group="1")
           - We have a group object (might be master, need to verify)
           - Device info is cached (full refresh happened, safe to check)
        6. When a slave is detected, the coordinator should trigger master detection
           on all players to find which one became the master.

        Note: We previously used mode=="99" to detect slaves, but this can get stuck
        after leaving a group (firmware bug). The 'group' field is always reliable.
        """
        if self.player._status_model is None:
            return

        status = self.player._status_model
        old_role = self.player._detected_role

        # Fast path: Use group field to detect potential slaves
        # group == "1" is the authoritative indicator that device is a slave
        # Note: mode=="99" can get stuck after leaving group (firmware bug), so we don't use it
        is_potential_slave = status.group == "1"

        # We only call get_device_group_info() (which uses getDeviceInfo) when:
        # 1. Potential slave detected (group="1")
        # 2. We have a group object (might be master, need to verify)
        # 3. We have device_info cached (full refresh happened, safe to check)
        should_check_role = False

        if is_potential_slave:
            # Potential slave detected via fast path - we need to check role
            should_check_role = True
            _LOGGER.debug(
                "Potential slave detected for %s (group=1) - checking role via get_device_group_info()",
                self.player.host,
            )
        elif self.player._group is not None:
            # We think we're in a group - need to verify (might be master)
            should_check_role = True
            _LOGGER.debug("Group object exists for %s - checking role via get_device_group_info()", self.player.host)
        elif self.player._device_info is not None:
            # Device info is cached (full refresh happened) - safe to check role
            # This handles the case where a master might also have group="0"
            should_check_role = True
            _LOGGER.debug("Device info cached for %s - checking role via get_device_group_info()", self.player.host)

        if should_check_role:
            # Call get_device_group_info() to determine role accurately
            try:
                group_info = await self.player.client.get_device_group_info()
                detected_role = group_info.role
                slave_hosts = group_info.slave_hosts

                # Trust get_device_group_info() result - it checks group field and master info
                # No override needed - the group field is always correct
            except Exception as err:
                _LOGGER.warning(
                    "Failed to get device group info for %s: %s - keeping current role",
                    self.player.host,
                    err,
                )
                return
        else:
            # Fast path: No slave indicator (group != "1") and we're solo with no group
            # Skip expensive call - device is definitely solo
            detected_role = "solo"
            slave_hosts = []

        # Detect role change (especially solo->slave, which triggers master detection)
        became_slave = old_role == "solo" and detected_role == "slave"

        # Update _detected_role - this is the single source of truth for player.role
        self.player._detected_role = detected_role

        # Clear source if not a slave but source is still "multiroom" (for UI clarity)
        if detected_role != "slave" and self.player._status_model:
            current_source = self.player._status_model.source
            if current_source == "multiroom":
                _LOGGER.debug(
                    "Clearing multiroom source for %s (role=%s, was=%s)",
                    self.player.host,
                    detected_role,
                    old_role,
                )
                self.player._status_model.source = None
                self.player._status_model._multiroom_mode = None
                # Also clear from state synchronizer to prevent refresh() from restoring it
                self.player._state_synchronizer.update_from_http({"source": None})

        # If we became a slave, log it (coordinator should trigger master detection on all players)
        if became_slave:
            _LOGGER.info(
                "Device %s became SLAVE (was solo) - coordinator should trigger master detection on all players",
                self.player.host,
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

            # Automatically link slave Player objects if player_finder is available
            if slave_hosts and self.player._player_finder:
                for slave_host in slave_hosts:
                    try:
                        slave_player = self.player._player_finder(slave_host)
                        if slave_player:
                            # If slave is already in another group, remove it first
                            if slave_player._group and slave_player._group != group:
                                slave_player._group.remove_slave(slave_player)

                            if slave_player not in group.slaves:
                                _LOGGER.debug("Auto-linking slave %s to master %s", slave_host, self.player.host)
                                group.add_slave(slave_player)
                    except Exception as err:
                        _LOGGER.debug("Failed to find/link slave Player %s: %s", slave_host, err)

            # Force an immediate role update notification
            # This ensures the master's role change (solo -> master) is broadcast
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

            if slave_hosts:
                device_slave_hosts = set(slave_hosts)
                linked_slave_hosts = {slave.host for slave in self.player._group.slaves}

                # Remove slaves that are no longer in device state
                for slave in list(self.player._group.slaves):
                    if slave.host not in device_slave_hosts:
                        _LOGGER.debug("Removing slave %s from group (no longer in device state)", slave.host)
                        self.player._group.remove_slave(slave)
                        slaves_changed = True

                # Automatically link new slave Player objects if player_finder is available
                if self.player._player_finder:
                    for slave_host in device_slave_hosts:
                        if slave_host not in linked_slave_hosts:
                            try:
                                slave_player = self.player._player_finder(slave_host)
                                if slave_player:
                                    # If slave is already in another group, remove it first
                                    if slave_player._group and slave_player._group != self.player._group:
                                        slave_player._group.remove_slave(slave_player)

                                    _LOGGER.debug(
                                        "Auto-linking new slave %s to master %s", slave_host, self.player.host
                                    )
                                    self.player._group.add_slave(slave_player)
                                    slaves_changed = True
                            except Exception as err:
                                _LOGGER.debug("Failed to find/link slave Player %s: %s", slave_host, err)

            # Notify all group members if slaves changed
            if slaves_changed:
                self._notify_all_group_members(self.player._group)

        # Case 4: Device is slave
        elif detected_role == "slave":
            # We do NOTHING here.
            # Slaves are passive. They are claimed by the Master.
            # If we are a slave, we wait for the Master's poll cycle to find us and add us.
            # Just ensure we aren't holding onto a stale Master identity if we know we are solo.

            # However, if we have a player_finder and we know the master IP from status (rare but possible),
            # we can try to link up proactively.
            pass

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
        """Join this player to another player's group.

        This method handles all preconditions automatically:
        - If this player is master: disbands its group first
        - If this player is slave: leaves current group first
        - If target is slave: has target leave its group first
        - If target is solo: creates a group on target first
        - Uses WiFi Direct mode for legacy firmware (< 4.2.8020)

        This method is idempotent: calling it multiple times with the same target
        is safe and will return success if already in the target group.

        The integration/caller doesn't need to check roles or handle preconditions -
        just call this method and it will orchestrate everything needed.

        Args:
            master: The player to join (will become or is already the master).
        """
        # Idempotent check: if already in the target master's group, return success (no-op)
        if self.player._group is not None and self.player._group.master is not None:
            if self.player._group.master.host == master.host:
                _LOGGER.debug(
                    "Player %s is already in target master %s's group - no action needed",
                    self.player.host,
                    master.host,
                )
                return

        old_group = self.player._group if self.player.is_slave else None

        if self.player.is_master:
            _LOGGER.debug("Player %s is master, disbanding group before join", self.player.host)
            await self.leave_group()

        # If this player is a slave in a DIFFERENT group, leave it first
        if self.player.is_slave and old_group is not None:
            _LOGGER.debug("Player %s is slave in different group, leaving first", self.player.host)
            await self.leave_group()
            old_group = None  # Already left, no need to remove later

        if master.is_slave:
            _LOGGER.debug("Target %s is slave, having it leave group first", master.host)
            await master.leave_group()
            # Device needs time to settle after leaving a group before it can accept new connections
            # Without this wait, the subsequent join may fail silently (API returns OK but device doesn't change state)
            await asyncio.sleep(2.0)
            await master.refresh(full=True)
            _LOGGER.debug("After leave_group + wait: %s role is now %s", master.host, master.role)

        if master.is_solo:
            _LOGGER.debug("Target %s is solo, creating group", master.host)
            await GroupOperations(master).create_group()

        # Ensure device_info is available (refresh if needed)
        if self.player._device_info is None:
            _LOGGER.debug("Device info not cached for %s, refreshing", self.player.host)
            await self.player.refresh(full=True)
        if master._device_info is None:
            _LOGGER.debug("Device info not cached for master %s, refreshing", master.host)
            await master.refresh(full=True)

        slave_info = self.player._device_info
        master_info = master._device_info

        # Check if WiFi Direct mode is needed (firmware < 4.2.8020)
        use_wifi_direct = (master_info and master_info.needs_wifi_direct_multiroom) or (
            slave_info and slave_info.needs_wifi_direct_multiroom
        )

        if use_wifi_direct:
            _LOGGER.info(
                "WiFi Direct mode required (legacy firmware). " "Slave: %s (firmware=%s), Master: %s (firmware=%s)",
                self.player.host,
                slave_info.firmware if slave_info else "unknown",
                master.host,
                master_info.firmware if master_info else "unknown",
            )

        # Get WiFi Direct info if needed
        master_ssid: str | None = None
        master_wifi_channel: int | None = None

        if use_wifi_direct and master_info:
            # Try DeviceInfo first, then fetch from API
            if master_info.ssid and master_info.wifi_channel:
                master_ssid = master_info.ssid
                master_wifi_channel = master_info.wifi_channel
                _LOGGER.debug(
                    "Using WiFi Direct info from DeviceInfo: ssid=%s, channel=%s", master_ssid, master_wifi_channel
                )
            else:
                _LOGGER.debug("Fetching WiFi Direct info from master %s", master.host)
                try:
                    master_ssid, master_wifi_channel = await master.client.get_wifi_direct_info()
                    if master_ssid and master_wifi_channel:
                        _LOGGER.debug("Fetched WiFi Direct info: ssid=%s, channel=%s", master_ssid, master_wifi_channel)
                    else:
                        _LOGGER.warning("Failed to get WiFi Direct info from master %s - join may fail", master.host)
                except Exception as e:
                    _LOGGER.warning("Failed to fetch WiFi Direct info from master %s: %s", master.host, e)

        _LOGGER.debug(
            "Joining: slave=%s -> master=%s (wifi_direct=%s)",
            self.player.host,
            master.host,
            use_wifi_direct,
        )

        await self.player.client.join_slave(
            master.host,
            master_device_info=master_info,
            master_ssid=master_ssid,
            master_wifi_channel=master_wifi_channel,
        )

        # CRITICAL: join_slave() always returns "OK" even when it fails
        # Refresh slave to verify the join actually worked by checking if device became a slave
        await self.player.refresh(full=False)

        # Verify the join actually worked by checking device state
        # If still solo, the join failed (but API returned success)
        if self.player.is_solo:
            # Re-fetch device info after refresh
            slave_info_after = self.player._device_info
            master_info_after = master._device_info

            # Log detailed error - include WiFi Direct info if that mode was used
            used_wifi_direct = (slave_info_after and slave_info_after.needs_wifi_direct_multiroom) or (
                master_info_after and master_info_after.needs_wifi_direct_multiroom
            )
            if used_wifi_direct:
                _LOGGER.error(
                    "WiFi Direct join failed - %s is still solo. "
                    "Slave: model=%s, firmware=%s. Master: model=%s, firmware=%s, ssid=%s, channel=%s. "
                    "Possible causes: SSID/channel mismatch, network issue, or incompatible devices.",
                    self.player.host,
                    slave_info_after.model if slave_info_after else "unknown",
                    slave_info_after.firmware if slave_info_after else "unknown",
                    master_info_after.model if master_info_after else "unknown",
                    master_info_after.firmware if master_info_after else "unknown",
                    master_info_after.ssid if master_info_after else "unknown",
                    master_info_after.wifi_channel if master_info_after else "unknown",
                )
            else:
                _LOGGER.warning(
                    "join_slave() returned success but %s is still solo - join may have failed.",
                    self.player.host,
                )
            return

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
        """Leave the current group.

        This method works for all player roles:
        - Solo: No-op (idempotent, returns immediately)
        - Master: Disbands the entire group (all players become solo)
        - Slave: Leaves the group (master and other slaves remain grouped)

        The integration/caller doesn't need to check player role - just call this method
        and it will do the right thing.
        """
        # Idempotent: if already solo, nothing to do
        if self.player.is_solo:
            _LOGGER.debug("Player %s is already solo, nothing to do", self.player.host)
            return

        group = self.player._group
        if group is None:
            # Shouldn't happen (is_solo should have caught this), but handle gracefully
            _LOGGER.warning("Player %s reports non-solo but has no group reference", self.player.host)
            return

        master = group.master if group else None

        # Notify all members BEFORE disbanding/leaving (while group structure is intact)
        self._notify_all_group_members(group)

        if self.player.is_master:
            # Master leaving = disband the entire group
            _LOGGER.debug("Player %s is master, disbanding group", self.player.host)
            await group.disband()
        else:
            # Slave leaving = just leave the group
            _LOGGER.debug("Player %s is slave, leaving group", self.player.host)
            await self.player.client._request("/httpapi.asp?command=multiroom:Ungroup")
            group.remove_slave(self.player)

            if len(group.slaves) == 0:
                _LOGGER.debug("Group is now empty, auto-disbanding (master: %s)", master.host if master else "unknown")
                await group.disband()

    async def get_master_name(self) -> str | None:
        """Get master device name.

        Returns:
            Master device name if available, None otherwise.
        """

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
        device_info = self.player._device_info
        status = self.player._status_model
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

    def propagate_metadata_to_slaves(self) -> None:
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
            # Use source="propagated" to distinguish from slave's own device state
            # This helps conflict resolution prefer master's authoritative metadata
            slave._state_synchronizer.update_from_http(
                {
                    "title": master_status.title,
                    "artist": master_status.artist,
                    "album": master_status.album,
                    "image_url": master_status.entity_picture or master_status.cover_url,
                    "play_state": master_status.play_state,
                    "position": master_status.position,
                    "duration": master_status.duration,
                },
                source="propagated",
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
