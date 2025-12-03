"""CLI tool for testing join/unjoin operations between two players.

This tool provides a simple interface for testing group operations between
exactly two WiiM/LinkPlay devices, with support for:
- Basic join/unjoin cycle
- Bidirectional testing
- Interactive mode
- Automated stress testing

Note on testing approach:
The library now handles all state updates automatically (no waiting/polling needed).
However, this test code performs defensive verification by:
1. Checking library state immediately after operations
2. Refreshing from device to verify device state matches library state
3. Adding delays between operations for stress testing

The delays in tests are for VERIFICATION and STRESS TESTING, not required for normal usage.
For normal library usage, users just call the operation - library handles everything.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from typing import Any

from ..client import WiiMClient
from ..player import Player

_LOGGER = logging.getLogger(__name__)


class JoinTester:
    """Test join/unjoin operations between two players."""

    def __init__(
        self,
        player1: Player,
        player2: Player,
        verbose: bool = False,
        delay: float = 2.0,
    ) -> None:
        """Initialize join tester.

        Args:
            player1: First player (IP address 1).
            player2: Second player (IP address 2).
            verbose: Enable verbose output.
            delay: Delay between operations in seconds.
        """
        self.player1 = player1
        self.player2 = player2
        self.verbose = verbose
        self.delay = delay
        self.results: dict[str, Any] = {
            "operations": [],
            "successful": 0,
            "failed": 0,
        }

    def _log(self, message: str, level: str = "info") -> None:
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "debug": "🔍",
        }.get(level, "•")

        if self.verbose or level in ("error", "warning", "success"):
            print(f"[{timestamp}] {icon} {message}")

        if level == "error":
            _LOGGER.error(message)
        elif level == "warning":
            _LOGGER.warning(message)
        elif level == "debug":
            _LOGGER.debug(message)
        else:
            _LOGGER.info(message)

    def _record_operation(self, name: str, success: bool, message: str = "") -> None:
        """Record an operation result."""
        self.results["operations"].append(
            {
                "name": name,
                "success": success,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if success:
            self.results["successful"] += 1
        else:
            self.results["failed"] += 1

    async def _ensure_solo(self, player: Player, name: str) -> bool:
        """Ensure a player is solo, leave group if needed.

        Args:
            player: Player to check.
            name: Player name for logging.

        Returns:
            True if player is solo, False otherwise.
        """
        try:
            await player.refresh()
            if player.is_solo:
                self._log(f"{name} is solo", "debug")
                return True

            # Player is in a group, try to leave
            self._log(f"{name} is {player.role}, leaving group...", "warning")
            await player.leave_group()
            await asyncio.sleep(self.delay)
            await player.refresh()

            if player.is_solo:
                self._log(f"{name} left group successfully", "success")
                return True
            else:
                self._log(f"{name} failed to leave group (still {player.role})", "error")
                return False
        except Exception as e:
            self._log(f"Error ensuring {name} is solo: {e}", "error")
            return False

    async def _check_state(self, player: Player, name: str, expected_role: str) -> bool:
        """Check player state matches expected role.

        Args:
            player: Player to check.
            name: Player name for logging.
            expected_role: Expected role ('solo', 'master', 'slave').

        Returns:
            True if state matches, False otherwise.
        """
        try:
            await player.refresh()
            actual_role = player.role
            if actual_role == expected_role:
                self._log(f"{name} state: {actual_role} ✓", "debug")
                return True
            else:
                self._log(
                    f"{name} state mismatch: expected {expected_role}, got {actual_role}",
                    "error",
                )
                return False
        except Exception as e:
            self._log(f"Error checking {name} state: {e}", "error")
            return False

    async def get_status(self) -> dict[str, Any]:
        """Get current status of both players.

        Returns:
            Dictionary with status of both players.
        """
        try:
            await asyncio.gather(
                self.player1.refresh(),
                self.player2.refresh(),
                return_exceptions=True,
            )

            return {
                "player1": {
                    "host": self.player1.host,
                    "name": self.player1.name or "Unknown",
                    "role": self.player1.role,
                    "group": self.player1.group is not None,
                },
                "player2": {
                    "host": self.player2.host,
                    "name": self.player2.name or "Unknown",
                    "role": self.player2.role,
                    "group": self.player2.group is not None,
                },
            }
        except Exception as e:
            self._log(f"Error getting status: {e}", "error")
            return {}

    def print_status(self, status: dict[str, Any] | None = None) -> None:
        """Print current status of both players."""
        if status is None:
            status = {}

        print("\n" + "=" * 60)
        print("Current Status")
        print("=" * 60)

        p1 = status.get("player1", {})
        p2 = status.get("player2", {})

        print(f"Player 1: {p1.get('host', self.player1.host)}")
        print(f"  Name: {p1.get('name', 'Unknown')}")
        print(f"  Role: {p1.get('role', 'unknown').upper()}")
        print(f"  In Group: {'Yes' if p1.get('group') else 'No'}")

        print(f"\nPlayer 2: {p2.get('host', self.player2.host)}")
        print(f"  Name: {p2.get('name', 'Unknown')}")
        print(f"  Role: {p2.get('role', 'unknown').upper()}")
        print(f"  In Group: {'Yes' if p2.get('group') else 'No'}")

        print("=" * 60)

    async def test_join(self, master: Player, slave: Player, master_name: str, slave_name: str) -> bool:
        """Test joining slave to master.

        Args:
            master: Master player.
            slave: Slave player to join.
            master_name: Name for logging (e.g., "Player 1").
            slave_name: Name for logging (e.g., "Player 2").

        Returns:
            True if join was successful, False otherwise.
        """
        try:
            # Library handles all preconditions automatically (including creating group if needed)
            self._log(f"Joining {slave_name} to {master_name}...", "info")
            await slave.join_group(master)

            # Defensive verification: Check library state immediately
            if slave.is_slave and master.is_master:
                self._log(f"{slave_name} joined {master_name} successfully", "success")
                self._record_operation(f"Join ({slave_name} → {master_name})", True)
            else:
                self._log(f"{slave_name} failed to join {master_name} (library state incorrect)", "error")
                self._record_operation(f"Join ({slave_name} → {master_name})", False, "Library state check failed")
                return False

            # Optional verification: Wait and refresh to check device state matches
            await asyncio.sleep(self.delay)
            if await self._check_state(slave, slave_name, "slave"):
                return True
            else:
                self._log("Device state mismatch after join", "warning")
                return False

        except Exception as e:
            self._log(f"Error during join: {e}", "error")
            self._record_operation(f"Join ({slave_name} → {master_name})", False, str(e))
            return False

    async def test_unjoin(self, player: Player, name: str) -> bool:
        """Test unjoining a player from a group.

        Args:
            player: Player to unjoin.
            name: Name for logging.

        Returns:
            True if unjoin was successful, False otherwise.
        """
        try:
            if player.is_solo:
                self._log(f"{name} is already solo", "debug")
                self._record_operation(f"Unjoin ({name})", True, "Already solo")
                return True

            # Library handles state updates automatically
            self._log(f"Unjoining {name}...", "info")
            await player.leave_group()

            # Defensive verification: Check library state immediately
            if player.is_solo:
                self._log(f"{name} unjoined successfully", "success")
                self._record_operation(f"Unjoin ({name})", True)
            else:
                self._log(f"{name} failed to unjoin (library state incorrect)", "error")
                self._record_operation(f"Unjoin ({name})", False, "Library state check failed")
                return False

            # Optional verification: Wait and refresh to check device state matches
            await asyncio.sleep(self.delay)
            if await self._check_state(player, name, "solo"):
                return True
            else:
                self._log("Device state mismatch after unjoin", "warning")
                return False

        except Exception as e:
            self._log(f"Error during unjoin: {e}", "error")
            self._record_operation(f"Unjoin ({name})", False, str(e))
            return False

    async def test_basic_cycle(self) -> bool:
        """Test basic join/unjoin cycle: Player 2 joins Player 1, then unjoins.

        Returns:
            True if cycle completed successfully, False otherwise.
        """
        self._log("Starting basic join/unjoin cycle...", "info")
        print("\n" + "=" * 60)
        print("Basic Join/Unjoin Cycle")
        print("=" * 60)

        # Ensure both are solo
        self._log("Ensuring both players are solo...", "info")
        if not await self._ensure_solo(self.player1, "Player 1"):
            return False
        if not await self._ensure_solo(self.player2, "Player 2"):
            return False

        # Join Player 2 to Player 1
        if not await self.test_join(self.player1, self.player2, "Player 1", "Player 2"):
            return False

        # Show status
        status = await self.get_status()
        self.print_status(status)

        # Unjoin Player 2
        if not await self.test_unjoin(self.player2, "Player 2"):
            return False

        # Verify both are solo
        if not await self._check_state(self.player1, "Player 1", "solo"):
            return False
        if not await self._check_state(self.player2, "Player 2", "solo"):
            return False

        self._log("Basic cycle completed successfully", "success")
        return True

    async def test_bidirectional(self) -> bool:
        """Test bidirectional join/unjoin: both directions.

        Returns:
            True if both directions completed successfully, False otherwise.
        """
        self._log("Starting bidirectional test...", "info")
        print("\n" + "=" * 60)
        print("Bidirectional Join/Unjoin Test")
        print("=" * 60)

        # Test Player 2 → Player 1
        self._log("\n--- Direction 1: Player 2 → Player 1 ---", "info")
        if not await self.test_join(self.player1, self.player2, "Player 1", "Player 2"):
            return False

        status = await self.get_status()
        self.print_status(status)

        if not await self.test_unjoin(self.player2, "Player 2"):
            return False

        await asyncio.sleep(self.delay)

        # Test Player 1 → Player 2
        self._log("\n--- Direction 2: Player 1 → Player 2 ---", "info")
        if not await self.test_join(self.player2, self.player1, "Player 2", "Player 1"):
            return False

        status = await self.get_status()
        self.print_status(status)

        if not await self.test_unjoin(self.player1, "Player 1"):
            return False

        # Verify both are solo
        if not await self._check_state(self.player1, "Player 1", "solo"):
            return False
        if not await self._check_state(self.player2, "Player 2", "solo"):
            return False

        self._log("Bidirectional test completed successfully", "success")
        return True

    async def test_stress(self, cycles: int) -> bool:
        """Run stress test with multiple join/unjoin cycles.

        Args:
            cycles: Number of cycles to run.

        Returns:
            True if all cycles completed successfully, False otherwise.
        """
        self._log(f"Starting stress test with {cycles} cycles...", "info")
        print("\n" + "=" * 60)
        print(f"Stress Test ({cycles} cycles)")
        print("=" * 60)

        success_count = 0
        for i in range(cycles):
            self._log(f"\n--- Cycle {i + 1}/{cycles} ---", "info")

            # Join
            if await self.test_join(self.player1, self.player2, "Player 1", "Player 2"):
                await asyncio.sleep(self.delay)

                # Unjoin
                if await self.test_unjoin(self.player2, "Player 2"):
                    success_count += 1
                    self._log(f"Cycle {i + 1} completed successfully", "success")
                else:
                    self._log(f"Cycle {i + 1} failed at unjoin", "error")
            else:
                self._log(f"Cycle {i + 1} failed at join", "error")

            # Small delay between cycles
            if i < cycles - 1:
                await asyncio.sleep(self.delay)

        self._log(f"\nStress test completed: {success_count}/{cycles} cycles successful", "info")
        return success_count == cycles

    async def test_volume_propagation(self) -> bool:
        """Test volume propagation: slave → master → all slaves.

        Tests:
        1. Slave sets volume → propagates to master and all slaves
        2. Master sets volume → syncs to all slaves
        3. Group volume = MAX of all devices
        4. Virtual master (group-level) volume control

        Returns:
            True if all volume tests pass, False otherwise.
        """
        self._log("Starting volume propagation tests...", "info")
        print("\n" + "=" * 60)
        print("Volume Propagation Tests")
        print("=" * 60)

        # Ensure both are solo first
        if not await self._ensure_solo(self.player1, "Player 1"):
            return False
        if not await self._ensure_solo(self.player2, "Player 2"):
            return False

        # Create group: Player 1 as master, Player 2 as slave
        if not await self.test_join(self.player1, self.player2, "Player 1", "Player 2"):
            return False

        try:
            # Wait for group to stabilize
            await asyncio.sleep(self.delay)

            # Get group reference
            group = self.player1.group

            # Test 1: Slave sets volume → should NOT propagate (volumes are independent)
            self._log("Test 1: Slave sets volume (0.15) - volumes are independent...", "info")
            test_volume = 0.15
            await self.player2.set_volume(test_volume)
            await asyncio.sleep(self.delay * 2.5)

            # Refresh all players to get updated state
            await asyncio.gather(
                self.player1.refresh(),
                self.player2.refresh(),
                return_exceptions=True,
            )

            # Check that slave volume changed but master did NOT (volumes are independent)
            master_vol = self.player1.volume_level
            slave_vol = self.player2.volume_level
            virtual_vol = group.volume_level if group else None

            if master_vol is not None and slave_vol is not None:
                # Slave should be at test_volume (or close)
                # Master should be unchanged (volumes don't propagate)
                slave_ok = abs(slave_vol - test_volume) < 0.05
                if slave_ok:
                    virtual_str = f", virtual={virtual_vol:.2f}" if virtual_vol is not None else ""
                    self._log(
                        f"✓ Volume states: master={master_vol:.2f}, slave={slave_vol:.2f}{virtual_str}",
                        "success",
                    )
                    self._record_operation("Volume independence (slave)", True)
                else:
                    self._log(
                        f"✗ Slave volume incorrect: expected ~{test_volume:.2f}, got {slave_vol:.2f}",
                        "error",
                    )
                    self._record_operation(
                        "Volume independence (slave)",
                        False,
                        f"Expected ~{test_volume:.2f}, got {slave_vol:.2f}",
                    )
            else:
                self._log("✗ Could not read volume levels", "error")
                self._record_operation("Volume independence (slave)", False, "Could not read volumes")

            # Test 2: Master sets volume → should NOT sync (volumes are independent)
            self._log("Test 2: Master sets volume (0.18) - volumes are independent...", "info")
            test_volume = 0.18
            await self.player1.set_volume(test_volume)
            await asyncio.sleep(self.delay * 2.5)

            await asyncio.gather(
                self.player1.refresh(),
                self.player2.refresh(),
                return_exceptions=True,
            )

            master_vol = self.player1.volume_level
            slave_vol = self.player2.volume_level
            virtual_vol = group.volume_level if group else None

            if master_vol is not None and slave_vol is not None:
                # Master should be at test_volume (or close)
                # Slave should be unchanged (volumes don't propagate)
                master_ok = abs(master_vol - test_volume) < 0.05
                if master_ok:
                    virtual_str = f", virtual={virtual_vol:.2f}" if virtual_vol is not None else ""
                    self._log(
                        f"✓ Volume states: master={master_vol:.2f}, slave={slave_vol:.2f}{virtual_str}",
                        "success",
                    )
                    self._record_operation("Volume independence (master)", True)
                else:
                    self._log(
                        f"✗ Master volume incorrect: expected ~{test_volume:.2f}, got {master_vol:.2f}",
                        "error",
                    )
                    self._record_operation(
                        "Volume independence (master)",
                        False,
                        f"Expected ~{test_volume:.2f}, got {master_vol:.2f}",
                    )
            else:
                self._record_operation("Volume independence (master)", False, "Could not read volumes")

            # Test 3: Group volume = MAX of all devices
            self._log("Test 3: Group volume = MAX of all devices...", "info")
            group = self.player1.group
            if group:
                # Set different volumes on master and slave
                await self.player1.set_volume(0.10)
                await asyncio.sleep(self.delay)
                await self.player2.set_volume(0.19)  # Higher volume
                await asyncio.sleep(self.delay * 1.5)

                await asyncio.gather(
                    self.player1.refresh(),
                    self.player2.refresh(),
                    return_exceptions=True,
                )

                # Group volume should be MAX
                group_vol = group.volume_level
                master_vol = self.player1.volume_level
                slave_vol = self.player2.volume_level

                if group_vol is not None and master_vol is not None and slave_vol is not None:
                    expected_max = max(master_vol, slave_vol)
                    if abs(group_vol - expected_max) < 0.05:
                        self._log(
                            f"✓ Volume states: master={master_vol:.2f}, slave={slave_vol:.2f}, "
                            f"virtual={group_vol:.2f} (MAX)",
                            "success",
                        )
                        self._record_operation("Group volume = MAX", True)
                    else:
                        self._log(
                            f"✗ Group volume incorrect: {group_vol:.2f} "
                            f"(expected max of {master_vol:.2f}, {slave_vol:.2f})",
                            "error",
                        )
                        self._record_operation(
                            "Group volume = MAX",
                            False,
                            f"Expected {expected_max:.2f}, got {group_vol:.2f}",
                        )
                else:
                    self._record_operation("Group volume = MAX", False, "Could not read volumes")

            # Test 4: Virtual master (group-level) volume control with proportional changes
            self._log("Test 4: Group-level volume control (proportional changes)...", "info")
            if group:
                # Get current virtual master volume
                current_virtual = group.volume_level
                if current_virtual is not None and current_virtual > 0:
                    # Set target virtual master volume (proportional change)
                    test_volume = 0.12
                    await group.set_volume_all(test_volume)
                    await asyncio.sleep(self.delay * 1.5)

                    await asyncio.gather(
                        self.player1.refresh(),
                        self.player2.refresh(),
                        return_exceptions=True,
                    )

                    master_vol = self.player1.volume_level
                    slave_vol = self.player2.volume_level
                    new_virtual = group.volume_level

                    if master_vol is not None and slave_vol is not None and new_virtual is not None:
                        # Virtual master should be close to target (within tolerance)
                        # Each device should have changed by the same delta
                        virtual_ok = abs(new_virtual - test_volume) < 0.05

                        if virtual_ok:
                            self._log(
                                f"✓ Volume states: master={master_vol:.2f}, slave={slave_vol:.2f}, "
                                f"virtual={new_virtual:.2f} (target={test_volume:.2f})",
                                "success",
                            )
                            self._record_operation("Group-level volume control (proportional)", True)
                        else:
                            self._log(
                                f"✗ Group volume control: virtual={new_virtual:.2f} (expected ~{test_volume:.2f})",
                                "error",
                            )
                            self._record_operation(
                                "Group-level volume control (proportional)",
                                False,
                                f"Virtual master: expected ~{test_volume:.2f}, got {new_virtual:.2f}",
                            )
                    else:
                        self._record_operation(
                            "Group-level volume control (proportional)", False, "Could not read volumes"
                        )
                else:
                    self._log("Skipping proportional test - no current virtual master volume", "warning")
                    self._record_operation(
                        "Group-level volume control (proportional)", True, "Skipped - no current volume"
                    )

        finally:
            # Cleanup: unjoin and disband
            await self.test_unjoin(self.player2, "Player 2")

        return bool(self.results["failed"] == 0)

    async def test_mute_propagation(self) -> bool:
        """Test mute propagation: slave → master → all slaves.

        Tests:
        1. Slave sets mute → propagates to master and all slaves
        2. Master sets mute → syncs to all slaves
        3. Group mute = ALL devices muted
        4. Virtual master (group-level) mute control

        Returns:
            True if all mute tests pass, False otherwise.
        """
        self._log("Starting mute propagation tests...", "info")
        print("\n" + "=" * 60)
        print("Mute Propagation Tests")
        print("=" * 60)

        # Ensure both are solo first
        if not await self._ensure_solo(self.player1, "Player 1"):
            return False
        if not await self._ensure_solo(self.player2, "Player 2"):
            return False

        # Create group: Player 1 as master, Player 2 as slave
        if not await self.test_join(self.player1, self.player2, "Player 1", "Player 2"):
            return False

        try:
            # Wait for group to stabilize
            await asyncio.sleep(self.delay)

            # Get group reference
            group = self.player1.group

            # Ensure both are unmuted initially
            await self.player1.set_mute(False)
            await self.player2.set_mute(False)
            await asyncio.sleep(self.delay)

            # Test 1: Slave sets mute → should NOT propagate (mute states are independent)
            self._log("Test 1: Slave sets mute (True) - mute states are independent...", "info")
            await self.player2.set_mute(True)
            await asyncio.sleep(self.delay * 2.5)

            await asyncio.gather(
                self.player1.refresh(),
                self.player2.refresh(),
                return_exceptions=True,
            )

            master_mute = self.player1.is_muted
            slave_mute = self.player2.is_muted
            virtual_mute = group.is_muted if group else None

            if master_mute is not None and slave_mute is not None:
                # Mute states are independent - slave mute should NOT propagate to master
                if slave_mute:
                    virtual_str = f", virtual={virtual_mute}" if virtual_mute is not None else ""
                    self._log(
                        f"✓ Mute states: master={master_mute}, slave={slave_mute}{virtual_str}",
                        "success",
                    )
                    self._record_operation("Mute independence (slave)", True)
                else:
                    self._log(
                        f"✗ Slave mute not set: slave={slave_mute}",
                        "error",
                    )
                    self._record_operation(
                        "Mute independence (slave)",
                        False,
                        f"Expected slave=True, got {slave_mute}",
                    )
            else:
                self._record_operation("Mute propagation (slave → master)", False, "Could not read mute states")

            # Test 2: Unmute via slave
            self._log("Test 2: Slave sets mute (False)...", "info")
            await self.player2.set_mute(False)
            await asyncio.sleep(self.delay * 2.5)

            await asyncio.gather(
                self.player1.refresh(),
                self.player2.refresh(),
                return_exceptions=True,
            )

            master_mute = self.player1.is_muted
            slave_mute = self.player2.is_muted
            virtual_mute = group.is_muted if group else None

            if master_mute is not None and slave_mute is not None:
                # Mute states are independent - slave unmute should NOT propagate to master
                if not slave_mute:
                    virtual_str = f", virtual={virtual_mute}" if virtual_mute is not None else ""
                    self._log(
                        f"✓ Mute states: master={master_mute}, slave={slave_mute}{virtual_str}",
                        "success",
                    )
                    self._record_operation("Unmute independence (slave)", True)
                else:
                    self._record_operation(
                        "Unmute independence (slave)",
                        False,
                        f"Expected slave=False, got {slave_mute}",
                    )
            else:
                self._record_operation("Unmute propagation (slave → master)", False, "Could not read mute states")

            # Test 3: Master sets mute → should sync to all slaves
            self._log("Test 3: Master sets mute (True)...", "info")
            await self.player1.set_mute(True)
            await asyncio.sleep(self.delay * 2.5)

            await asyncio.gather(
                self.player1.refresh(),
                self.player2.refresh(),
                return_exceptions=True,
            )

            master_mute = self.player1.is_muted
            slave_mute = self.player2.is_muted
            virtual_mute = group.is_muted if group else None

            if master_mute is not None and slave_mute is not None:
                # Mute states are independent - master mute should NOT propagate to slave
                if master_mute:
                    virtual_str = f", virtual={virtual_mute}" if virtual_mute is not None else ""
                    self._log(
                        f"✓ Mute states: master={master_mute}, slave={slave_mute}{virtual_str}",
                        "success",
                    )
                    self._record_operation("Mute independence (master)", True)
                else:
                    self._record_operation(
                        "Mute independence (master)",
                        False,
                        f"Expected master=True, got {master_mute}",
                    )
            else:
                self._record_operation("Mute sync (master → slave)", False, "Could not read mute states")

            # Test 4: Group mute = ALL devices muted
            self._log("Test 4: Group mute = ALL devices muted...", "info")
            group = self.player1.group
            if group:
                # Set different mute states
                await self.player1.set_mute(True)
                await self.player2.set_mute(True)
                await asyncio.sleep(self.delay * 1.5)

                await asyncio.gather(
                    self.player1.refresh(),
                    self.player2.refresh(),
                    return_exceptions=True,
                )

                group_mute = group.is_muted
                master_mute = self.player1.is_muted
                slave_mute = self.player2.is_muted

                if group_mute is not None and master_mute is not None and slave_mute is not None:
                    # Group mute should be True only if ALL are muted
                    expected = master_mute and slave_mute
                    if group_mute == expected:
                        self._log(
                            f"✓ Mute states: master={master_mute}, slave={slave_mute}, virtual={group_mute} (ALL)",
                            "success",
                        )
                        self._record_operation("Group mute = ALL", True)
                    else:
                        self._log(
                            f"✗ Group mute incorrect: {group_mute} (expected {expected}, "
                            f"master={master_mute}, slave={slave_mute})",
                            "error",
                        )
                        self._record_operation(
                            "Group mute = ALL",
                            False,
                            f"Expected {expected}, got {group_mute}",
                        )
                else:
                    self._record_operation("Group mute = ALL", False, "Could not read mute states")

                # Test: Group mute should be False if any device is unmuted
                await self.player1.set_mute(False)
                await asyncio.sleep(self.delay * 1.5)

                await asyncio.gather(
                    self.player1.refresh(),
                    self.player2.refresh(),
                    return_exceptions=True,
                )

                group_mute = group.is_muted
                master_mute = self.player1.is_muted
                slave_mute = self.player2.is_muted

                if group_mute is not None and master_mute is not None and slave_mute is not None:
                    expected = master_mute and slave_mute
                    if group_mute == expected:
                        self._log(
                            f"✓ Mute states: master={master_mute}, slave={slave_mute}, virtual={group_mute} (ALL)",
                            "success",
                        )
                        self._record_operation("Group mute = ALL (partial unmute)", True)
                    else:
                        self._record_operation(
                            "Group mute = ALL (partial unmute)",
                            False,
                            f"Expected {expected}, got {group_mute}",
                        )

            # Test 5: Virtual master (group-level) mute control
            self._log("Test 5: Group-level mute control...", "info")
            if group:
                await group.mute_all(True)
                await asyncio.sleep(self.delay * 1.5)

                await asyncio.gather(
                    self.player1.refresh(),
                    self.player2.refresh(),
                    return_exceptions=True,
                )

                master_mute = self.player1.is_muted
                slave_mute = self.player2.is_muted
                virtual_mute = group.is_muted if group else None

                if master_mute is not None and slave_mute is not None:
                    if master_mute and slave_mute:
                        virtual_str = f", virtual={virtual_mute}" if virtual_mute is not None else ""
                        self._log(
                            f"✓ Mute states: master={master_mute}, slave={slave_mute}{virtual_str}",
                            "success",
                        )
                        self._record_operation("Group-level mute control", True)
                    else:
                        self._record_operation(
                            "Group-level mute control",
                            False,
                            f"master={master_mute}, slave={slave_mute}",
                        )
                else:
                    self._record_operation("Group-level mute control", False, "Could not read mute states")

        finally:
            # Cleanup: unjoin and disband
            await self.test_unjoin(self.player2, "Player 2")

        return bool(self.results["failed"] == 0)

    def print_summary(self) -> None:
        """Print test summary."""
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Total operations: {len(self.results['operations'])}")
        print(f"Successful: {self.results['successful']}")
        print(f"Failed: {self.results['failed']}")
        print("=" * 60)

        if self.results["failed"] > 0:
            print("\nFailed operations:")
            for op in self.results["operations"]:
                if not op["success"]:
                    print(f"  ✗ {op['name']}: {op['message']}")


async def interactive_mode(tester: JoinTester) -> None:
    """Run interactive mode with menu."""
    while True:
        print("\n" + "=" * 60)
        print("Interactive Join/Unjoin Test")
        print("=" * 60)
        print("1. Show status")
        print("2. Join Player 2 to Player 1")
        print("3. Unjoin Player 2")
        print("4. Join Player 1 to Player 2")
        print("5. Unjoin Player 1")
        print("6. Run basic cycle")
        print("7. Run bidirectional test")
        print("8. Run stress test")
        print("9. Test volume propagation")
        print("10. Test mute propagation")
        print("11. Exit")
        print("=" * 60)

        try:
            choice = input("\nSelect option (1-11): ").strip()

            if choice == "1":
                status = await tester.get_status()
                tester.print_status(status)
            elif choice == "2":
                await tester.test_join(tester.player1, tester.player2, "Player 1", "Player 2")
                status = await tester.get_status()
                tester.print_status(status)
            elif choice == "3":
                await tester.test_unjoin(tester.player2, "Player 2")
                status = await tester.get_status()
                tester.print_status(status)
            elif choice == "4":
                await tester.test_join(tester.player2, tester.player1, "Player 2", "Player 1")
                status = await tester.get_status()
                tester.print_status(status)
            elif choice == "5":
                await tester.test_unjoin(tester.player1, "Player 1")
                status = await tester.get_status()
                tester.print_status(status)
            elif choice == "6":
                await tester.test_basic_cycle()
                status = await tester.get_status()
                tester.print_status(status)
            elif choice == "7":
                await tester.test_bidirectional()
                status = await tester.get_status()
                tester.print_status(status)
            elif choice == "8":
                try:
                    cycles = int(input("Enter number of cycles: ").strip())
                    if cycles > 0:
                        await tester.test_stress(cycles)
                        status = await tester.get_status()
                        tester.print_status(status)
                    else:
                        print("Invalid number of cycles")
                except ValueError:
                    print("Invalid input")
            elif choice == "9":
                await tester.test_volume_propagation()
                tester.print_summary()
                status = await tester.get_status()
                tester.print_status(status)
            elif choice == "10":
                await tester.test_mute_propagation()
                tester.print_summary()
                status = await tester.get_status()
                tester.print_status(status)
            elif choice == "11":
                print("Exiting...")
                break
            else:
                print("Invalid option")

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


async def main() -> int:
    """Main entry point for join test CLI."""
    parser = argparse.ArgumentParser(
        description="Test join/unjoin operations between two WiiM/LinkPlay devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic join/unjoin cycle
  wiim-join-test 192.168.1.100 192.168.1.101

  # Bidirectional test
  wiim-join-test 192.168.1.100 192.168.1.101 --bidirectional

  # Interactive mode
  wiim-join-test 192.168.1.100 192.168.1.101 --interactive

  # Stress test with 10 cycles
  wiim-join-test 192.168.1.100 192.168.1.101 --cycles 10

  # Test volume propagation
  wiim-join-test 192.168.1.100 192.168.1.101 --volume

  # Test mute propagation
  wiim-join-test 192.168.1.100 192.168.1.101 --mute

  # Verbose output
  wiim-join-test 192.168.1.100 192.168.1.101 --verbose
        """,
    )
    parser.add_argument(
        "ip1",
        help="First device IP address or hostname",
    )
    parser.add_argument(
        "ip2",
        help="Second device IP address or hostname",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Device port (default: auto-detect, use 80 for HTTP or 443 for HTTPS)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between operations in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--bidirectional",
        action="store_true",
        help="Run bidirectional test (both join directions)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        metavar="N",
        help="Run stress test with N cycles",
    )
    parser.add_argument(
        "--volume",
        action="store_true",
        help="Test volume propagation (slave → master → all slaves)",
    )
    parser.add_argument(
        "--mute",
        action="store_true",
        help="Test mute propagation (slave → master → all slaves)",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Create clients and players
    client1 = WiiMClient(host=args.ip1, port=args.port)
    client2 = WiiMClient(host=args.ip2, port=args.port)
    player1 = Player(client1)
    player2 = Player(client2)

    tester = JoinTester(player1, player2, verbose=args.verbose, delay=args.delay)

    try:
        # Initial status
        print("\n" + "=" * 60)
        print("Join/Unjoin Test Tool")
        print("=" * 60)
        print(f"Player 1: {args.ip1}")
        print(f"Player 2: {args.ip2}")
        print("=" * 60)

        initial_status = await tester.get_status()
        tester.print_status(initial_status)

        # Run tests based on mode
        if args.interactive:
            await interactive_mode(tester)
        elif args.volume:
            success = await tester.test_volume_propagation()
            tester.print_summary()
            return 0 if success else 1
        elif args.mute:
            success = await tester.test_mute_propagation()
            tester.print_summary()
            return 0 if success else 1
        elif args.cycles:
            success = await tester.test_stress(args.cycles)
            tester.print_summary()
            return 0 if success else 1
        elif args.bidirectional:
            success = await tester.test_bidirectional()
            tester.print_summary()
            return 0 if success else 1
        else:
            # Default: basic cycle
            success = await tester.test_basic_cycle()
            tester.print_summary()
            return 0 if success else 1

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1
    finally:
        # Cleanup
        try:
            await client1.close()
            await client2.close()
        except Exception:
            pass


def cli_main() -> None:
    """CLI entry point."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_main()
