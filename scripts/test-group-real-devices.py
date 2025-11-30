#!/usr/bin/env python3
"""Test group functionality against real devices.

Tests group operations from test_group.py against actual WiiM devices.
Tests various combinations of devices as master/slave.

Usage:
    python scripts/test-group-real-devices.py
"""

import asyncio
import sys
from typing import Any

from pywiim import WiiMClient
from pywiim.exceptions import WiiMError
from pywiim.player import Player


# Device IPs to test
DEVICE_IPS = [
    "192.168.1.115",
    "192.168.1.116",
    "192.168.1.68",
    "192.168.6.50",
    "192.168.6.95",
]


class TestResult:
    """Track test results."""

    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: str | None = None
        self.details: list[str] = []

    def add_detail(self, detail: str) -> None:
        """Add a detail line."""
        self.details.append(detail)

    def fail(self, error: str) -> None:
        """Mark test as failed."""
        self.passed = False
        self.error = error

    def success(self) -> None:
        """Mark test as passed."""
        self.passed = True


async def connect_to_devices(ips: list[str]) -> dict[str, Player]:
    """Connect to all devices and return Player objects."""
    print(f"\n{'='*80}")
    print("Connecting to devices...")
    print(f"{'='*80}\n")

    players: dict[str, Player] = {}

    for ip in ips:
        try:
            print(f"Connecting to {ip}...", end=" ", flush=True)
            client = WiiMClient(ip, timeout=5.0)
            player = Player(client)
            await player.refresh()
            device_info = await player.client.get_device_info_model()
            players[ip] = player
            print(f"✓ Connected: {device_info.name} ({device_info.model})")
        except Exception as e:
            print(f"✗ Failed: {e}")
            continue

    print(f"\nConnected to {len(players)} device(s)\n")
    return players


async def ensure_solo(player: Player) -> None:
    """Ensure a player is in solo mode."""
    try:
        if player.is_master:
            await player.leave_group()
        elif not player.is_solo:
            await player.leave_group()
        await asyncio.sleep(1.0)
        await player.refresh()
    except Exception:
        pass


async def ensure_all_solo(players: list[Player]) -> None:
    """Ensure all players are in solo mode."""
    print("Ensuring all devices are in solo mode...")
    # Disband masters first
    for player in players:
        if player.is_master:
            try:
                await player.leave_group()
            except Exception:
                pass
    await asyncio.sleep(2.0)
    # Then handle any remaining slaves
    for player in players:
        if not player.is_solo:
            try:
                await player.leave_group()
            except Exception:
                pass
    await asyncio.sleep(2.0)
    # Refresh all
    await asyncio.gather(*(player.refresh() for player in players), return_exceptions=True)
    print("All devices in solo mode\n")


async def test_group_init(players: dict[str, Player]) -> TestResult:
    """Test Group initialization."""
    result = TestResult("test_group_init")

    if len(players) < 1:
        result.fail("Need at least 1 device")
        return result

    try:
        master_ip = list(players.keys())[0]
        master = players[master_ip]

        await ensure_solo(master)
        await master.refresh()

        group = await master.create_group()
        await master.refresh()

        result.add_detail(f"Created group with master {master_ip}")
        result.add_detail(f"  master == master: {group.master == master}")
        result.add_detail(f"  len(slaves) == 0: {len(group.slaves) == 0}")
        result.add_detail(f"  size == 1: {group.size == 1}")
        result.add_detail(f"  master.group == group: {master.group == group}")

        if group.master == master and len(group.slaves) == 0 and group.size == 1 and master.group == group:
            result.success()
        else:
            result.fail("Group initialization failed")

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_all_players(players: dict[str, Player]) -> TestResult:
    """Test all_players property."""
    result = TestResult("test_group_all_players")

    if len(players) < 3:
        result.fail("Need at least 3 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave1_ip = list(players.keys())[1]
        slave2_ip = list(players.keys())[2]

        master = players[master_ip]
        slave1 = players[slave1_ip]
        slave2 = players[slave2_ip]

        await ensure_all_solo([master, slave1, slave2])

        group = await master.create_group()
        await slave1.join_group(master)
        await slave2.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave1, slave2]), return_exceptions=True)

        all_players = group.all_players
        result.add_detail(f"Created group: master={master_ip}, slaves=[{slave1_ip}, {slave2_ip}]")
        result.add_detail(f"  len(all_players) == 3: {len(all_players) == 3}")
        result.add_detail(f"  all_players[0] == master: {all_players[0] == master}")
        result.add_detail(f"  slave1 in all_players: {slave1 in all_players}")
        result.add_detail(f"  slave2 in all_players: {slave2 in all_players}")

        if (
            len(all_players) == 3
            and all_players[0] == master
            and slave1 in all_players
            and slave2 in all_players
        ):
            result.success()
        else:
            result.fail("all_players property failed")

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_add_slave(players: dict[str, Player]) -> TestResult:
    """Test adding a slave."""
    result = TestResult("test_add_slave")

    if len(players) < 2:
        result.fail("Need at least 2 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave_ip = list(players.keys())[1]

        master = players[master_ip]
        slave = players[slave_ip]

        await ensure_all_solo([master, slave])

        group = await master.create_group()
        await slave.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

        result.add_detail(f"Created group: master={master_ip}, slave={slave_ip}")
        result.add_detail(f"  slave in group.slaves: {slave in group.slaves}")
        result.add_detail(f"  group.size == 2: {group.size == 2}")
        result.add_detail(f"  slave.group == group: {slave.group == group}")

        if slave in group.slaves and group.size == 2 and slave.group == group:
            result.success()
        else:
            result.fail("Add slave failed")

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_remove_slave(players: dict[str, Player]) -> TestResult:
    """Test removing a slave."""
    result = TestResult("test_remove_slave")

    if len(players) < 2:
        result.fail("Need at least 2 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave_ip = list(players.keys())[1]

        master = players[master_ip]
        slave = players[slave_ip]

        await ensure_all_solo([master, slave])

        group = await master.create_group()
        await slave.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

        await slave.leave_group()
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

        result.add_detail(f"Created group and removed slave: master={master_ip}, slave={slave_ip}")
        result.add_detail(f"  slave not in group.slaves: {slave not in group.slaves}")
        result.add_detail(f"  group.size == 1: {group.size == 1}")
        result.add_detail(f"  slave.group is None: {slave.group is None}")

        if slave not in group.slaves and group.size == 1 and slave.group is None:
            result.success()
        else:
            result.fail("Remove slave failed")

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_disband(players: dict[str, Player]) -> TestResult:
    """Test disbanding a group."""
    result = TestResult("test_disband")

    if len(players) < 3:
        result.fail("Need at least 3 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave1_ip = list(players.keys())[1]
        slave2_ip = list(players.keys())[2]

        master = players[master_ip]
        slave1 = players[slave1_ip]
        slave2 = players[slave2_ip]

        await ensure_all_solo([master, slave1, slave2])

        group = await master.create_group()
        await slave1.join_group(master)
        await slave2.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave1, slave2]), return_exceptions=True)

        await group.disband()
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave1, slave2]), return_exceptions=True)

        result.add_detail(f"Created and disbanded group: master={master_ip}, slaves=[{slave1_ip}, {slave2_ip}]")
        result.add_detail(f"  master.group is None: {master.group is None}")
        result.add_detail(f"  slave1.group is None: {slave1.group is None}")
        result.add_detail(f"  slave2.group is None: {slave2.group is None}")
        result.add_detail(f"  len(group.slaves) == 0: {len(group.slaves) == 0}")

        if (
            master.group is None
            and slave1.group is None
            and slave2.group is None
            and len(group.slaves) == 0
        ):
            result.success()
        else:
            result.fail("Disband failed")

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_set_volume_all(players: dict[str, Player]) -> TestResult:
    """Test setting volume on all devices."""
    result = TestResult("test_set_volume_all")

    if len(players) < 2:
        result.fail("Need at least 2 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave_ip = list(players.keys())[1]

        master = players[master_ip]
        slave = players[slave_ip]

        await ensure_all_solo([master, slave])

        # Get initial volumes for restoration
        initial_master_vol = await master.get_volume()
        initial_slave_vol = await slave.get_volume()

        group = await master.create_group()
        await slave.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

        # Set volume via group
        await group.set_volume_all(0.5)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

        master_vol = await master.get_volume()
        slave_vol = await slave.get_volume()

        result.add_detail(f"Set group volume to 0.5: master={master_ip}, slave={slave_ip}")
        result.add_detail(f"  master volume: {master_vol}")
        result.add_detail(f"  slave volume: {slave_vol}")

        # Restore volumes
        if initial_master_vol is not None:
            await master.set_volume(initial_master_vol)
        if initial_slave_vol is not None:
            await slave.set_volume(initial_slave_vol)

        if master_vol is not None and slave_vol is not None:
            result.success()
        else:
            result.fail("Volume setting failed - volumes are None")

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_volume_level_max(players: dict[str, Player]) -> TestResult:
    """Test getting group volume (max of all devices)."""
    result = TestResult("test_volume_level_max")

    if len(players) < 2:
        result.fail("Need at least 2 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave_ip = list(players.keys())[1]

        master = players[master_ip]
        slave = players[slave_ip]

        await ensure_all_solo([master, slave])

        # Get initial volumes for restoration
        initial_master_vol = await master.get_volume()
        initial_slave_vol = await slave.get_volume()

        group = await master.create_group()
        await slave.join_group(master)
        await asyncio.sleep(2.0)

        # Set different volumes
        await master.set_volume(0.5)
        await slave.set_volume(0.75)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

        volume = group.volume_level

        result.add_detail(f"Set volumes: master=0.5, slave=0.75")
        result.add_detail(f"  group.volume_level: {volume}")
        result.add_detail(f"  Expected: 0.75 (max)")

        # Restore volumes
        if initial_master_vol is not None:
            await master.set_volume(initial_master_vol)
        if initial_slave_vol is not None:
            await slave.set_volume(initial_slave_vol)

        if volume is not None and abs(volume - 0.75) < 0.1:
            result.success()
        else:
            result.fail(f"Volume level max failed: got {volume}, expected ~0.75")

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_is_muted_all(players: dict[str, Player]) -> TestResult:
    """Test checking if all devices are muted."""
    result = TestResult("test_is_muted_all")

    if len(players) < 2:
        result.fail("Need at least 2 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave_ip = list(players.keys())[1]

        master = players[master_ip]
        slave = players[slave_ip]

        await ensure_all_solo([master, slave])

        # Get initial mute states for restoration
        initial_master_mute = await master.get_muted()
        initial_slave_mute = await slave.get_muted()

        group = await master.create_group()
        await slave.join_group(master)
        await asyncio.sleep(2.0)

        # Mute all
        await group.mute_all(True)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

        is_muted = group.is_muted

        result.add_detail(f"Muted all devices: master={master_ip}, slave={slave_ip}")
        result.add_detail(f"  group.is_muted: {is_muted}")
        result.add_detail(f"  Expected: True")

        # Restore mute states
        if initial_master_mute is not None:
            await master.set_mute(initial_master_mute)
        if initial_slave_mute is not None:
            await slave.set_mute(initial_slave_mute)

        if is_muted is True:
            result.success()
        else:
            result.fail(f"Mute check failed: got {is_muted}, expected True")

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_playback_control(players: dict[str, Player]) -> TestResult:
    """Test group playback control."""
    result = TestResult("test_playback_control")

    if len(players) < 1:
        result.fail("Need at least 1 device")
        return result

    try:
        master_ip = list(players.keys())[0]
        master = players[master_ip]

        await ensure_solo(master)

        group = await master.create_group()
        await asyncio.sleep(1.0)
        await master.refresh()

        # Test play
        try:
            await group.play()
            await asyncio.sleep(1.0)
            result.add_detail("✓ play() command sent")
        except Exception as e:
            result.add_detail(f"✗ play() failed: {e}")

        # Test pause
        try:
            await group.pause()
            await asyncio.sleep(1.0)
            result.add_detail("✓ pause() command sent")
        except Exception as e:
            result.add_detail(f"✗ pause() failed: {e}")

        result.success()

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def run_test_combinations(players: dict[str, Player]) -> list[TestResult]:
    """Run tests with various device combinations."""
    results: list[TestResult] = []

    if len(players) < 1:
        print("No devices available for testing")
        return results

    print(f"\n{'='*80}")
    print("Running group tests...")
    print(f"{'='*80}\n")

    # Test 1: Single device (master only)
    print("Test: Group initialization (single device)")
    result = await test_group_init(players)
    results.append(result)
    print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
    if result.error:
        print(f"    Error: {result.error}")
    for detail in result.details:
        print(f"    {detail}")

    if len(players) >= 2:
        # Test 2: Two devices (master + slave)
        print("\nTest: Add slave")
        result = await test_add_slave(players)
        results.append(result)
        print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
        if result.error:
            print(f"    Error: {result.error}")
        for detail in result.details:
            print(f"    {detail}")

        print("\nTest: Remove slave")
        result = await test_remove_slave(players)
        results.append(result)
        print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
        if result.error:
            print(f"    Error: {result.error}")
        for detail in result.details:
            print(f"    {detail}")

        print("\nTest: Set volume all")
        result = await test_set_volume_all(players)
        results.append(result)
        print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
        if result.error:
            print(f"    Error: {result.error}")
        for detail in result.details:
            print(f"    {detail}")

        print("\nTest: Volume level max")
        result = await test_volume_level_max(players)
        results.append(result)
        print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
        if result.error:
            print(f"    Error: {result.error}")
        for detail in result.details:
            print(f"    {detail}")

        print("\nTest: Is muted all")
        result = await test_is_muted_all(players)
        results.append(result)
        print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
        if result.error:
            print(f"    Error: {result.error}")
        for detail in result.details:
            print(f"    {detail}")

    if len(players) >= 3:
        # Test 3: Three devices (master + 2 slaves)
        print("\nTest: All players property")
        result = await test_group_all_players(players)
        results.append(result)
        print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
        if result.error:
            print(f"    Error: {result.error}")
        for detail in result.details:
            print(f"    {detail}")

        print("\nTest: Disband")
        result = await test_disband(players)
        results.append(result)
        print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
        if result.error:
            print(f"    Error: {result.error}")
        for detail in result.details:
            print(f"    {detail}")

    # Test playback control (works with any number of devices)
    print("\nTest: Playback control")
    result = await test_playback_control(players)
    results.append(result)
    print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
    if result.error:
        print(f"    Error: {result.error}")
    for detail in result.details:
        print(f"    {detail}")

    return results


async def main() -> int:
    """Main test function."""
    print("=" * 80)
    print("Group Functionality Test - Real Devices")
    print("=" * 80)
    print(f"\nTesting devices: {', '.join(DEVICE_IPS)}")

    # Connect to devices
    players = await connect_to_devices(DEVICE_IPS)

    if not players:
        print("No devices could be connected. Exiting.")
        return 1

    # Ensure all devices start in solo mode
    await ensure_all_solo(list(players.values()))

    # Run tests
    results = await run_test_combinations(players)

    # Cleanup - ensure all devices are solo
    print(f"\n{'='*80}")
    print("Cleanup: Ensuring all devices are in solo mode...")
    print(f"{'='*80}\n")
    await ensure_all_solo(list(players.values()))

    # Close connections
    print("Closing connections...")
    await asyncio.gather(*(player.client.close() for player in players.values()), return_exceptions=True)

    # Summary
    print(f"\n{'='*80}")
    print("Test Summary")
    print(f"{'='*80}\n")

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print(f"Total tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}\n")

    if failed > 0:
        print("Failed tests:")
        for result in results:
            if not result.passed:
                print(f"  ✗ {result.name}")
                if result.error:
                    print(f"    {result.error}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

