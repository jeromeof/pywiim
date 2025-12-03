"""CLI tool for testing group join/unjoin operations and metadata propagation.

This tool tests:
- Creating groups (SOLO → MASTER)
- Joining players to groups (SOLO → SLAVE)
- Leaving groups (SLAVE → SOLO, MASTER → SOLO)
- Metadata propagation from master to slaves

Device States (mutually exclusive):
- SOLO: Not in a group
- MASTER: Leading a group (has slaves)
- SLAVE: Following a master in a group

Note on testing approach:
The library now handles all state updates automatically (no waiting/polling needed).
However, this test code performs defensive verification by:
1. Checking library state immediately after operations (should be correct)
2. Optionally refreshing from device to verify device state matches library state

The wait/refresh in tests is for VERIFICATION, not because it's required for library usage.
For normal library usage, users just call the operation - library handles everything.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Any

from ..client import WiiMClient
from ..player import Player

_LOGGER = logging.getLogger(__name__)


class GroupTester:
    """Test group operations and metadata propagation."""

    def __init__(self, master: Player, slaves: list[Player], verbose: bool = False) -> None:
        """Initialize group tester.

        Args:
            master: Master player for the group.
            slaves: List of slave players to join.
            verbose: Enable verbose output.
        """
        self.master = master
        self.slaves = slaves
        self.verbose = verbose
        self.results: dict[str, Any] = {
            "tests": [],
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }

    def _log(self, message: str, level: str = "info") -> None:
        """Log a message."""
        if self.verbose or level in ("error", "warning"):
            print(f"[{level.upper()}] {message}")
        if level == "error":
            _LOGGER.error(message)
        elif level == "warning":
            _LOGGER.warning(message)
        elif level == "debug":
            _LOGGER.debug(message)
        else:
            _LOGGER.info(message)

    def _record_test(self, name: str, passed: bool, message: str = "", skipped: bool = False) -> None:
        """Record a test result."""
        status = "SKIPPED" if skipped else ("PASS" if passed else "FAIL")
        self.results["tests"].append(
            {
                "name": name,
                "status": status,
                "message": message,
            }
        )
        if skipped:
            self.results["skipped"] += 1
        elif passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1

        icon = "✓" if passed else ("⊘" if skipped else "✗")
        print(f"  {icon} {name}: {message or status}")

    async def test_initial_state(self) -> None:
        """Test initial state - all players should be solo."""
        self._log("Testing initial state...")
        try:
            # Refresh all players
            await asyncio.gather(
                self.master.refresh(),
                *[slave.refresh() for slave in self.slaves],
                return_exceptions=True,
            )

            # Check leader player is solo
            if self.master.is_solo:
                self._record_test("Leader player initial state", True, "SOLO")
            else:
                self._record_test(
                    "Leader player initial state",
                    False,
                    f"Role is {self.master.role.upper()} (expected SOLO)",
                )

            # Check follower players are solo
            for i, slave in enumerate(self.slaves):
                if slave.is_solo:
                    self._record_test(f"Follower {i + 1} initial state", True, "SOLO")
                else:
                    self._record_test(
                        f"Follower {i + 1} initial state",
                        False,
                        f"Role is {slave.role.upper()} (expected SOLO)",
                    )
        except Exception as e:
            self._record_test("Initial state check", False, str(e))

    async def test_create_group(self) -> None:
        """Test creating a group."""
        self._log("Testing group creation...")
        try:
            # Library handles state updates automatically
            group = await self.master.create_group()

            # Verify: Check library state is correct (should be immediate)
            if group is not None and self.master.is_master:
                self._record_test("Create group", True, f"Leader became MASTER at {self.master.host}")
            else:
                self._record_test("Create group", False, f"Failed: role is {self.master.role.upper()}, expected MASTER")
        except Exception as e:
            self._record_test("Create group", False, str(e))

    async def test_join_slaves(self) -> None:
        """Test joining followers to the group."""
        self._log("Testing follower join operations...")
        if not self.master.group:
            self._record_test("Join followers", False, "No group exists (create group first)", skipped=True)
            return

        for i, slave in enumerate(self.slaves):
            try:
                # Library handles all preconditions and state updates automatically
                await slave.join_group(self.master)

                # Defensive verification: Check library state matches expected
                if slave.is_slave and slave.group == self.master.group:
                    self._record_test(f"Join follower {i + 1}", True, "Became SLAVE in group")
                else:
                    self._record_test(
                        f"Join follower {i + 1}",
                        False,
                        f"Role is {slave.role.upper()}, in group: {slave.group is not None}",
                    )

                # Optional: Verify device state matches library state
                # (this is defensive - library should already be correct)
                await asyncio.sleep(0.5)
                await slave.refresh()

                if not slave.is_slave:
                    self._log(
                        f"WARNING: Device state mismatch - library says SLAVE, device says {slave.role.upper()}",
                        "warning",
                    )
            except Exception as e:
                self._record_test(f"Join follower {i + 1}", False, str(e))

    async def test_group_state(self) -> None:
        """Test group state after all slaves joined."""
        self._log("Testing group state...")
        if not self.master.group:
            self._record_test("Group state", False, "No group exists", skipped=True)
            return

        try:
            group = self.master.group
            expected_size = 1 + len(self.slaves)

            if group.size == expected_size:
                self._record_test("Group size", True, f"Group has {group.size} players")
            else:
                self._record_test(
                    "Group size",
                    False,
                    f"Expected {expected_size} players, got {group.size}",
                )

            # Check all players are in the group
            all_players = group.all_players
            if len(all_players) == expected_size:
                self._record_test("All players in group", True)
            else:
                self._record_test(
                    "All players in group",
                    False,
                    f"Expected {expected_size} players, got {len(all_players)}",
                )
        except Exception as e:
            self._record_test("Group state", False, str(e))

    async def test_metadata_propagation(self) -> None:
        """Test metadata propagation from master to slaves."""
        self._log("Testing metadata propagation...")
        if not self.master.group:
            self._record_test("Metadata propagation", False, "No group exists", skipped=True)
            return

        try:
            # Refresh all players to get latest state
            await asyncio.gather(
                self.master.refresh(),
                *[slave.refresh() for slave in self.slaves],
                return_exceptions=True,
            )

            # Get master metadata
            master_metadata = {
                "title": self.master.media_title,
                "artist": self.master.media_artist,
                "album": self.master.media_album,
                "position": self.master.media_position,
                "duration": self.master.media_duration,
                "play_state": self.master.play_state,
            }

            self._log(f"Master metadata: {master_metadata}", "debug")

            # Check if master has metadata
            has_metadata = any(
                [
                    master_metadata["title"],
                    master_metadata["artist"],
                    master_metadata["album"],
                ]
            )

            if not has_metadata:
                self._record_test(
                    "Metadata propagation",
                    True,
                    "Skipped - master has no metadata to propagate",
                    skipped=True,
                )
                return

            # Wait a bit for propagation (metadata sync can take time)
            await asyncio.sleep(2)

            # Refresh slaves again to get propagated metadata
            await asyncio.gather(
                *[slave.refresh() for slave in self.slaves],
                return_exceptions=True,
            )

            # Check each slave's metadata
            all_match = True
            for i, slave in enumerate(self.slaves):
                slave_metadata = {
                    "title": slave.media_title,
                    "artist": slave.media_artist,
                    "album": slave.media_album,
                    "position": slave.media_position,
                    "play_state": slave.play_state,
                }

                self._log(f"Slave {i + 1} metadata: {slave_metadata}", "debug")

                # Compare metadata (position may differ slightly due to timing)
                title_match = slave_metadata["title"] == master_metadata["title"]
                artist_match = slave_metadata["artist"] == master_metadata["artist"]
                album_match = slave_metadata["album"] == master_metadata["album"]
                play_state_match = slave_metadata["play_state"] == master_metadata["play_state"]

                if title_match and artist_match and album_match and play_state_match:
                    self._record_test(
                        f"Metadata propagation slave {i + 1}",
                        True,
                        "Title/Artist/Album/State match",
                    )
                else:
                    all_match = False
                    mismatches = []
                    if not title_match:
                        mismatches.append(f"title: '{slave_metadata['title']}' != '{master_metadata['title']}'")
                    if not artist_match:
                        mismatches.append(f"artist: '{slave_metadata['artist']}' != '{master_metadata['artist']}'")
                    if not album_match:
                        mismatches.append(f"album: '{slave_metadata['album']}' != '{master_metadata['album']}'")
                    if not play_state_match:
                        mismatches.append(
                            f"play_state: '{slave_metadata['play_state']}' != '{master_metadata['play_state']}'"
                        )
                    self._record_test(
                        f"Metadata propagation slave {i + 1}",
                        False,
                        f"Mismatches: {', '.join(mismatches)}",
                    )

            if all_match:
                self._record_test("Metadata propagation (all slaves)", True, "All slaves match master metadata")
        except Exception as e:
            self._record_test("Metadata propagation", False, str(e))

    async def test_leave_group_slaves(self) -> None:
        """Test leaving group as followers."""
        self._log("Testing follower leave operations...")
        if not self.master.group:
            self._record_test("Leave group (followers)", False, "No group exists", skipped=True)
            return

        # Leave in reverse order
        for i, slave in enumerate(reversed(self.slaves)):
            try:
                if not slave.is_slave:
                    self._record_test(
                        f"Leave follower {len(self.slaves) - i}",
                        True,
                        "Already not in group",
                        skipped=True,
                    )
                    continue

                # Library handles state updates automatically
                await slave.leave_group()

                # Defensive verification: Check library state is correct
                if slave.is_solo:
                    self._record_test(f"Leave follower {len(self.slaves) - i}", True, "Became SOLO")
                else:
                    self._record_test(
                        f"Leave follower {len(self.slaves) - i}",
                        False,
                        f"Role is {slave.role.upper()} (expected SOLO)",
                    )

                # Optional: Verify device state matches library state
                await asyncio.sleep(0.5)
                await slave.refresh()

                if not slave.is_solo:
                    self._log(
                        f"WARNING: Device state mismatch - library says SOLO, device says {slave.role.upper()}",
                        "warning",
                    )
            except Exception as e:
                self._record_test(f"Leave follower {len(self.slaves) - i}", False, str(e))

    async def test_leave_group_master(self) -> None:
        """Test leaving group as leader (disbands group)."""
        self._log("Testing leader leave (disband group)...")
        if not self.master.group:
            self._record_test("Leave group (leader)", True, "No group exists", skipped=True)
            return

        try:
            # Library handles disband and state updates automatically
            await self.master.leave_group()

            # Defensive verification: Check library state is correct
            if self.master.is_solo:
                self._record_test("Leave group (leader)", True, "MASTER became SOLO, group disbanded")
            else:
                self._record_test(
                    "Leave group (leader)",
                    False,
                    f"Role is {self.master.role.upper()} (expected SOLO)",
                )

            # Optional: Verify device state matches library state
            await asyncio.sleep(0.5)
            await self.master.refresh()

            if not self.master.is_solo:
                self._log(
                    f"WARNING: Device state mismatch - library says SOLO, device says {self.master.role.upper()}",
                    "warning",
                )
        except Exception as e:
            self._record_test("Leave group (leader)", False, str(e))

    async def test_final_state(self) -> None:
        """Test final state - all players should be solo again."""
        self._log("Testing final state...")
        try:
            # Refresh all players
            await asyncio.gather(
                self.master.refresh(),
                *[slave.refresh() for slave in self.slaves],
                return_exceptions=True,
            )

            # Check leader player is solo
            if self.master.is_solo:
                self._record_test("Final state - leader", True, "SOLO")
            else:
                self._record_test(
                    "Final state - leader",
                    False,
                    f"Role is {self.master.role.upper()} (expected SOLO)",
                )

            # Check follower players are solo
            for i, slave in enumerate(self.slaves):
                if slave.is_solo:
                    self._record_test(f"Final state - follower {i + 1}", True, "SOLO")
                else:
                    self._record_test(
                        f"Final state - follower {i + 1}",
                        False,
                        f"Role is {slave.role.upper()} (expected SOLO)",
                    )
        except Exception as e:
            self._record_test("Final state check", False, str(e))

    async def run_all_tests(self, pause_between_operations: float = 0.0) -> dict[str, Any]:
        """Run all group tests.

        Args:
            pause_between_operations: Seconds to pause between operations (for visual verification).
        """
        print("\n" + "=" * 60)
        print("Group Join/Unjoin Test Suite")
        print("=" * 60)
        print(f"Leader Player: {self.master.host}")
        print(f"Follower Players: {[s.host for s in self.slaves]}")
        if pause_between_operations > 0:
            print(f"Pause between operations: {pause_between_operations}s (for visual verification)")
        print("=" * 60 + "\n")

        # Test sequence
        await self.test_initial_state()
        if pause_between_operations > 0:
            await asyncio.sleep(pause_between_operations)

        await self.test_create_group()
        if pause_between_operations > 0:
            await asyncio.sleep(pause_between_operations)

        await self.test_join_slaves()
        if pause_between_operations > 0:
            await asyncio.sleep(pause_between_operations)

        await self.test_group_state()
        if pause_between_operations > 0:
            await asyncio.sleep(pause_between_operations)

        await self.test_metadata_propagation()
        if pause_between_operations > 0:
            await asyncio.sleep(pause_between_operations)

        await self.test_leave_group_slaves()
        if pause_between_operations > 0:
            await asyncio.sleep(pause_between_operations)

        await self.test_leave_group_master()
        if pause_between_operations > 0:
            await asyncio.sleep(pause_between_operations)

        await self.test_final_state()

        return self.results

    def print_summary(self) -> None:
        """Print test summary."""
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Total tests: {len(self.results['tests'])}")
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")
        print(f"Skipped: {self.results['skipped']}")
        print("=" * 60)

        if self.results["failed"] > 0:
            print("\nFailed tests:")
            for test in self.results["tests"]:
                if test["status"] == "FAIL":
                    print(f"  ✗ {test['name']}: {test['message']}")


async def show_detailed_status(players: list[Player], pause: float = 5.0) -> None:
    """Show detailed status of all players and pause for visual verification.

    Args:
        players: List of all players to show status for.
        pause: Seconds to pause for visual verification.
    """
    # Refresh all players
    await asyncio.gather(*[p.refresh() for p in players], return_exceptions=True)

    print("\n" + "-" * 60)
    print("Current State:")
    print("-" * 60)
    for i, player in enumerate(players):
        role = player.role.upper()
        name = player.name or player.host
        group_info = ""
        if player.is_master and player.group:
            group_info = f" (slaves: {len(player.group.slaves)})"
        elif player.is_slave and player.group:
            master_name = player.group.master.name or player.group.master.host
            group_info = f" (master: {master_name})"

        print(f"  Player {i + 1} ({name}): {role}{group_info}")
    print("-" * 60)

    if pause > 0:
        print(f"Pausing {pause}s for visual verification in WiiM app...")
        await asyncio.sleep(pause)


async def run_interactive_tests(tester: GroupTester, master: Player, slaves: list[Player]) -> None:
    """Run interactive tests with detailed status display.

    Args:
        tester: GroupTester instance.
        master: Master player.
        slaves: List of slave players.
    """
    all_players = [master] + slaves
    pause = 5.0

    print("\n" + "=" * 60)
    print("Interactive Group Join/Unjoin Test")
    print("=" * 60)
    print(f"Leader: {master.host}")
    for i, slave in enumerate(slaves):
        print(f"Follower {i + 1}: {slave.host}")
    print("=" * 60)

    # Initial state
    print("\n📋 Initial State")
    await show_detailed_status(all_players, pause)

    # Test 1: Create group
    print("\n1️⃣  Creating group on leader...")
    group = await master.create_group()
    print(f"   ✓ Group created: {master.host} is now ready to accept followers")
    await show_detailed_status(all_players, pause)

    # Test 2: Join followers one by one
    for i, slave in enumerate(slaves):
        print(f"\n{i + 2}️⃣  Joining follower {i + 1} ({slave.host}) to leader...")
        await slave.join_group(master)
        print(f"   ✓ Follower {i + 1} joined group")
        await show_detailed_status(all_players, pause)

    # Test 3: Show group state
    print("\n📊 Group State:")
    print(f"   Group size: {group.size} players")
    print(f"   Master: {master.host}")
    print(f"   Slaves: {[s.host for s in group.slaves]}")
    await asyncio.sleep(pause)

    # Test 4: Leave followers one by one
    for i, slave in enumerate(slaves):
        print(f"\n🚪 Follower {i + 1} ({slave.host}) leaving group...")
        await slave.leave_group()
        print(f"   ✓ Follower {i + 1} left group, now solo")
        await show_detailed_status(all_players, pause)

    # Final state
    print("\n📋 Final State")
    await show_detailed_status(all_players, pause)

    print("\n✅ Interactive test complete!")


async def main() -> int:
    """Main entry point for group test CLI."""
    parser = argparse.ArgumentParser(
        description="Test group join/unjoin operations and metadata propagation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with one master and one slave
  wiim-group-test 192.168.1.100 192.168.1.101

  # Test with one master and multiple slaves
  wiim-group-test 192.168.1.100 192.168.1.101 192.168.1.102

  # Verbose output
  wiim-group-test 192.168.1.100 192.168.1.101 --verbose

  # HTTPS devices
  wiim-group-test 192.168.1.100 192.168.1.101 --port 443

  # Interactive mode with 5-second pauses for visual verification
  wiim-group-test 192.168.1.100 192.168.1.101 192.168.1.102 --interactive

  # Automated with pauses for visual verification
  wiim-group-test 192.168.1.100 192.168.1.101 192.168.1.102 --pause 5
        """,
    )
    parser.add_argument(
        "master_ip",
        help="Master device IP address or hostname",
    )
    parser.add_argument(
        "slave_ips",
        nargs="+",
        help="Slave device IP addresses or hostnames",
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
        "--pause",
        "-p",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="Pause between operations (for visual verification in WiiM app, e.g., --pause 5)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode with detailed status after each operation",
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
    master_client = WiiMClient(host=args.master_ip, port=args.port)
    master = Player(master_client)

    slave_clients = [WiiMClient(host=ip, port=args.port) for ip in args.slave_ips]
    slaves = [Player(client) for client in slave_clients]

    tester = GroupTester(master, slaves, verbose=args.verbose)

    try:
        if args.interactive:
            # Interactive mode with detailed status
            await run_interactive_tests(tester, master, slaves)
            return 0
        else:
            # Automated mode
            summary = await tester.run_all_tests(pause_between_operations=args.pause)
            tester.print_summary()

            # Return exit code based on results
            if summary["failed"] > 0:
                return 1
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
        await master_client.close()
        for client in slave_clients:
            await client.close()


def cli_main() -> None:
    """CLI entry point."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_main()
