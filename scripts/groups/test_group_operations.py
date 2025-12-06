#!/usr/bin/env python3
"""Group operations tests - join/leave all permutations.

Tests all group join/leave operations including:
- Basic operations (create, join, leave, disband)
- Join permutations (solo→master, solo→slave, master→master, slave→different master)
- Leave permutations (slave leaves, master leaves/disbands, last slave auto-disband)
- Expected failures (subnet mismatch, wmrm_version incompatibility)
- Multiple devices in various orders

Usage:
    python scripts/groups/test_group_operations.py [--subnet 1|6|all] [--verbose]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, "reconfigure") else None

from pywiim.client import WiiMClient
from pywiim.exceptions import WiiMError, WiiMGroupCompatibilityError
from pywiim.player import Player


# =============================================================================
# Configuration
# =============================================================================


def load_devices() -> dict[str, Any]:
    """Load device configuration from devices.json."""
    config_path = Path(__file__).parent / "devices.json"
    with open(config_path) as f:
        return json.load(f)


def get_devices_by_subnet(subnet: str | None = None) -> list[dict[str, str]]:
    """Get devices filtered by subnet.

    Args:
        subnet: "1" for 192.168.1.x, "6" for 192.168.6.x, None for all

    Returns:
        List of device dicts with 'ip' and 'name' keys
    """
    config = load_devices()
    devices = []

    for subnet_key, subnet_data in config["subnets"].items():
        if subnet is None:
            # All devices
            devices.extend(subnet_data["devices"])
        elif subnet == "1" and "192.168.1" in subnet_key:
            devices.extend(subnet_data["devices"])
        elif subnet == "6" and "192.168.6" in subnet_key:
            devices.extend(subnet_data["devices"])

    return devices


def get_radio_url() -> str:
    """Get test radio URL from config."""
    config = load_devices()
    return config.get("test_radio_url", "http://ice1.somafm.com/groovesalad-128-mp3")


# =============================================================================
# Test Result Tracking
# =============================================================================


class TestResult:
    """Track test results."""

    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.skipped = False
        self.error: str | None = None
        self.details: list[str] = []

    def add_detail(self, detail: str) -> None:
        self.details.append(detail)

    def fail(self, error: str) -> None:
        self.passed = False
        self.error = error

    def success(self) -> None:
        self.passed = True

    def skip(self, reason: str) -> None:
        self.skipped = True
        self.error = reason


# =============================================================================
# Helper Functions
# =============================================================================


async def ensure_solo(player: Player, name: str, verbose: bool = False) -> bool:
    """Ensure a player is solo, leave group if needed."""
    try:
        await player.refresh(full=True)
        if player.is_solo:
            if verbose:
                print(f"   ✓ {name} is solo")
            return True

        if verbose:
            print(f"   ⚠️  {name} is {player.role}, leaving group...")
        await player.leave_group()
        await asyncio.sleep(2.0)
        await player.refresh(full=True)

        if player.is_solo:
            if verbose:
                print(f"   ✅ {name} left group successfully")
            return True
        else:
            print(f"   ❌ {name} failed to leave group (still {player.role})")
            return False
    except Exception as e:
        print(f"   ❌ Error ensuring {name} is solo: {e}")
        return False


async def ensure_all_solo(players: list[Player], names: list[str], verbose: bool = False) -> bool:
    """Ensure all players are solo."""
    if verbose:
        print("   Ensuring all devices are solo...")

    # Disband masters first
    for player, name in zip(players, names):
        if player.is_master:
            try:
                await player.leave_group()
            except Exception:
                pass
    await asyncio.sleep(2.0)

    # Then handle remaining
    all_solo = True
    for player, name in zip(players, names):
        if not await ensure_solo(player, name, verbose):
            all_solo = False

    return all_solo


async def print_status(players: list[Player], names: list[str]) -> None:
    """Print current status for all players."""
    print("\n   📊 Current Status:")
    for player, name in zip(players, names):
        await player.refresh()
        role = player.role.upper()
        if player.is_master:
            group_size = player.group.size if player.group else 1
            slave_count = len(player.group.slaves) if player.group else 0
            print(f"      {name}: {role} - Group size: {group_size} ({slave_count} slaves)")
        elif player.is_slave:
            master_host = player.group.master.host if player.group and player.group.master else "unknown"
            print(f"      {name}: {role} - Master: {master_host}")
        else:
            print(f"      {name}: {role}")


def are_same_subnet(ip1: str, ip2: str) -> bool:
    """Check if two IPs are on the same subnet."""
    return ".".join(ip1.split(".")[:3]) == ".".join(ip2.split(".")[:3])


async def start_radio(player: Player, name: str) -> bool:
    """Start a radio station on a player for testing."""
    try:
        await player.play_url(get_radio_url())
        await asyncio.sleep(2.0)
        await player.refresh()
        return True
    except Exception as e:
        print(f"   ⚠️  Failed to start radio on {name}: {e}")
        return False


# =============================================================================
# Basic Operations Tests
# =============================================================================


async def test_create_group(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Create a group on a solo device.

    Note: A master with no slaves is still "solo" per the device API (group=0).
    This test verifies the group object is created and ready for slaves.
    """
    result = TestResult("Create group (prepares for slaves)")

    if len(players) < 1:
        result.skip("Need at least 1 device")
        return result

    try:
        player = players[0]
        name = names[0]

        await ensure_solo(player, name, verbose)

        result.add_detail(f"Creating group on {name}...")
        group = await player.create_group()
        await asyncio.sleep(1.0)
        await player.refresh(full=True)

        # A master with no slaves is still "solo" per the device API
        # The group object should exist but role remains solo until slaves join
        if player.group is not None:
            result.add_detail(f"✅ Group created on {name} (role={player.role}, ready for slaves)")
            result.success()
        else:
            result.fail(f"Group object not created on {name}")

        # Cleanup
        await player.leave_group()
        await asyncio.sleep(1.0)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_basic_join_leave(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Basic join and leave flow."""
    result = TestResult("Basic join/leave (2 devices)")

    if len(players) < 2:
        result.skip("Need at least 2 devices")
        return result

    # Find two devices on same subnet
    master_idx, slave_idx = None, None
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            if are_same_subnet(players[i].host, players[j].host):
                master_idx, slave_idx = i, j
                break
        if master_idx is not None:
            break

    if master_idx is None:
        result.skip("No two devices on same subnet")
        return result

    master, slave = players[master_idx], players[slave_idx]
    master_name, slave_name = names[master_idx], names[slave_idx]

    try:
        await ensure_all_solo([master, slave], [master_name, slave_name], verbose)

        # Create group and join
        result.add_detail(f"Creating group on {master_name}...")
        await master.create_group()
        await asyncio.sleep(1.0)

        result.add_detail(f"Joining {slave_name} to {master_name}...")
        await slave.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

        if master.is_master and slave.is_slave:
            result.add_detail(f"✅ Join successful: {master_name} (master), {slave_name} (slave)")
        else:
            result.fail(f"Join failed: {master_name}={master.role}, {slave_name}={slave.role}")
            return result

        # Leave
        result.add_detail(f"Leaving: {slave_name}...")
        await slave.leave_group()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

        if slave.is_solo:
            result.add_detail(f"✅ {slave_name} left successfully")
            result.success()
        else:
            result.fail(f"Leave failed: {slave_name} is {slave.role}")

        # Cleanup
        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Join Permutation Tests
# =============================================================================


async def test_solo_joins_master(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Solo device joins a device that has called create_group().

    Note: A device that has called create_group() but has no slaves is still "solo"
    per the device API. It becomes "master" when the first slave joins.
    """
    result = TestResult("Solo joins device with group")

    if len(players) < 2:
        result.skip("Need at least 2 devices")
        return result

    # Find two devices on same subnet
    master_idx, slave_idx = None, None
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            if are_same_subnet(players[i].host, players[j].host):
                master_idx, slave_idx = i, j
                break
        if master_idx is not None:
            break

    if master_idx is None:
        result.skip("No two devices on same subnet")
        return result

    target, solo = players[master_idx], players[slave_idx]
    target_name, solo_name = names[master_idx], names[slave_idx]

    try:
        await ensure_all_solo([target, solo], [target_name, solo_name], verbose)

        # Start radio on target for realistic test
        await start_radio(target, target_name)

        # Create group on target (prepares it to accept slaves)
        result.add_detail(f"Creating group on {target_name} (preparing for slaves)...")
        await target.create_group()
        await asyncio.sleep(1.0)
        await target.refresh(full=True)
        result.add_detail(f"  {target_name} role after create_group: {target.role}")

        # Solo joins target - this is where target becomes master
        result.add_detail(f"{solo_name} (solo) joining {target_name}...")
        await solo.join_group(target)
        await asyncio.sleep(2.0)
        await asyncio.gather(target.refresh(full=True), solo.refresh(full=True))

        if target.is_master and solo.is_slave:
            if solo.group and solo.group.master.host == target.host:
                result.add_detail(f"✅ {solo_name} successfully joined {target_name}")
                result.add_detail(f"✅ {target_name} is now master (has slave)")
                result.success()
            else:
                result.fail("Solo joined but group structure incorrect")
        else:
            result.fail(f"Join failed: {target_name}={target.role}, {solo_name}={solo.role}")

        # Cleanup
        await ensure_all_solo([target, solo], [target_name, solo_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_solo_joins_slave(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Solo device joins a slave (slave should leave and become master)."""
    result = TestResult("Solo joins Slave (slave becomes master)")

    if len(players) < 3:
        result.skip("Need at least 3 devices")
        return result

    # Find three devices on same subnet
    same_subnet = []
    for i, p in enumerate(players):
        for j in range(i + 1, len(players)):
            if are_same_subnet(p.host, players[j].host):
                if i not in same_subnet:
                    same_subnet.append(i)
                if j not in same_subnet:
                    same_subnet.append(j)

    if len(same_subnet) < 3:
        result.skip("Need 3 devices on same subnet")
        return result

    master = players[same_subnet[0]]
    slave = players[same_subnet[1]]
    solo = players[same_subnet[2]]
    master_name = names[same_subnet[0]]
    slave_name = names[same_subnet[1]]
    solo_name = names[same_subnet[2]]

    try:
        await ensure_all_solo([master, slave, solo], [master_name, slave_name, solo_name], verbose)

        # Setup: Create group with master and slave
        await start_radio(master, master_name)
        await master.create_group()
        await asyncio.sleep(1.0)
        await slave.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

        if not (master.is_master and slave.is_slave):
            result.fail("Failed to setup initial group")
            return result

        result.add_detail(f"Initial: {master_name} (master), {slave_name} (slave)")

        # Solo joins slave - slave should leave its group and become master
        result.add_detail(f"{solo_name} (solo) joining {slave_name} (slave)...")
        result.add_detail(f"Expected: {slave_name} leaves group, becomes master, {solo_name} joins as slave")

        await solo.join_group(slave)
        await asyncio.sleep(3.0)
        await asyncio.gather(master.refresh(full=True), slave.refresh(full=True), solo.refresh(full=True))

        # Verify: slave is now master, solo is slave, original master is solo
        if slave.is_master and solo.is_slave and master.is_solo:
            result.add_detail(f"✅ {slave_name} left and became master")
            result.add_detail(f"✅ {solo_name} joined as slave")
            result.add_detail(f"✅ {master_name} is now solo (group disbanded)")
            result.success()
        else:
            result.fail(
                f"Unexpected: {master_name}={master.role}, " f"{slave_name}={slave.role}, {solo_name}={solo.role}"
            )

        # Cleanup
        await ensure_all_solo([master, slave, solo], [master_name, slave_name, solo_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_master_joins_master(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Master A joins Master B (A should disband and join B).

    Requires 4 devices: 2 for Group A (master + slave), 2 for Group B (master + slave).
    A master with no slaves is still "solo" per the device API.
    """
    result = TestResult("Master joins Master (auto-disband and join)")

    if len(players) < 4:
        result.skip("Need at least 4 devices (2 per group)")
        return result

    # Find four devices on same subnet
    same_subnet = []
    for i, p in enumerate(players):
        for j in range(i + 1, len(players)):
            if are_same_subnet(p.host, players[j].host):
                if i not in same_subnet:
                    same_subnet.append(i)
                if j not in same_subnet:
                    same_subnet.append(j)

    if len(same_subnet) < 4:
        result.skip("Need 4 devices on same subnet")
        return result

    master_a = players[same_subnet[0]]
    slave_a = players[same_subnet[1]]
    master_b = players[same_subnet[2]]
    slave_b = players[same_subnet[3]]
    name_a = names[same_subnet[0]]
    name_slave_a = names[same_subnet[1]]
    name_b = names[same_subnet[2]]
    name_slave_b = names[same_subnet[3]]

    all_players = [master_a, slave_a, master_b, slave_b]
    all_names = [name_a, name_slave_a, name_b, name_slave_b]

    try:
        await ensure_all_solo(all_players, all_names, verbose)

        # Setup: Create two real groups (each with master + slave)
        # Group A: master_a + slave_a
        result.add_detail(f"Creating Group A: {name_a} (master) + {name_slave_a} (slave)")
        await start_radio(master_a, name_a)
        await master_a.create_group()
        await asyncio.sleep(1.0)
        await slave_a.join_group(master_a)
        await asyncio.sleep(2.0)

        # Group B: master_b + slave_b
        result.add_detail(f"Creating Group B: {name_b} (master) + {name_slave_b} (slave)")
        await master_b.create_group()
        await asyncio.sleep(1.0)
        await slave_b.join_group(master_b)
        await asyncio.sleep(2.0)

        await asyncio.gather(*[p.refresh(full=True) for p in all_players])

        if not (master_a.is_master and slave_a.is_slave and master_b.is_master and slave_b.is_slave):
            result.fail(
                f"Setup failed: {name_a}={master_a.role}, {name_slave_a}={slave_a.role}, "
                f"{name_b}={master_b.role}, {name_slave_b}={slave_b.role}"
            )
            return result

        # Master A joins Master B
        result.add_detail(f"{name_a} (master) joining {name_b} (master)...")
        result.add_detail(f"Expected: {name_a} disbands Group A, joins Group B as slave")

        await master_a.join_group(master_b)
        await asyncio.sleep(3.0)
        await asyncio.gather(*[p.refresh(full=True) for p in all_players])

        # Verify: master_b is master, master_a is slave, slave_a is solo (disbanded), slave_b still slave
        if master_b.is_master and master_a.is_slave and slave_a.is_solo and slave_b.is_slave:
            result.add_detail(f"✅ {name_a} disbanded Group A and joined Group B as slave")
            result.add_detail(f"✅ {name_slave_a} is now solo (Group A disbanded)")
            result.add_detail(f"✅ {name_slave_b} still in Group B")
            result.success()
        else:
            result.fail(
                f"Unexpected: {name_a}={master_a.role}, {name_slave_a}={slave_a.role}, "
                f"{name_b}={master_b.role}, {name_slave_b}={slave_b.role}"
            )

        # Cleanup
        await ensure_all_solo(all_players, all_names, False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_slave_joins_different_master(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Slave leaves current group and joins a different master."""
    result = TestResult("Slave joins different Master")

    if len(players) < 3:
        result.skip("Need at least 3 devices")
        return result

    # Find three devices on same subnet
    same_subnet = []
    for i, p in enumerate(players):
        for j in range(i + 1, len(players)):
            if are_same_subnet(p.host, players[j].host):
                if i not in same_subnet:
                    same_subnet.append(i)
                if j not in same_subnet:
                    same_subnet.append(j)

    if len(same_subnet) < 3:
        result.skip("Need 3 devices on same subnet")
        return result

    master_a = players[same_subnet[0]]
    master_b = players[same_subnet[1]]
    slave = players[same_subnet[2]]
    name_a = names[same_subnet[0]]
    name_b = names[same_subnet[1]]
    name_slave = names[same_subnet[2]]

    try:
        await ensure_all_solo([master_a, master_b, slave], [name_a, name_b, name_slave], verbose)

        # Setup: slave in Group A
        result.add_detail(f"Creating Group A: {name_a} (master) + {name_slave} (slave)")
        await start_radio(master_a, name_a)
        await master_a.create_group()
        await asyncio.sleep(1.0)
        await slave.join_group(master_a)
        await asyncio.sleep(2.0)

        # Create Group B
        result.add_detail(f"Creating Group B: {name_b} (master)")
        await master_b.create_group()
        await asyncio.sleep(1.0)

        await asyncio.gather(master_a.refresh(full=True), master_b.refresh(full=True), slave.refresh(full=True))

        if not (master_a.is_master and slave.is_slave):
            result.fail("Failed to setup initial group")
            return result

        # Slave switches to Group B
        result.add_detail(f"{name_slave} (slave of A) joining {name_b} (master B)...")

        await slave.join_group(master_b)
        await asyncio.sleep(2.0)
        await asyncio.gather(master_a.refresh(full=True), master_b.refresh(full=True), slave.refresh(full=True))

        # Verify: slave is now in Group B
        if master_b.is_master and slave.is_slave and slave.group.master.host == master_b.host:
            result.add_detail(f"✅ {name_slave} switched from Group A to Group B")
            result.success()
        else:
            result.fail(f"Switch failed: {name_slave}={slave.role}")

        # Cleanup
        await ensure_all_solo([master_a, master_b, slave], [name_a, name_b, name_slave], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Expected Failure Tests
# =============================================================================


async def test_cross_subnet_fails(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Cross-subnet grouping should fail."""
    result = TestResult("Cross-subnet join fails (expected)")

    # Find two devices on DIFFERENT subnets
    diff_subnet = None
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            if not are_same_subnet(players[i].host, players[j].host):
                diff_subnet = (i, j)
                break
        if diff_subnet:
            break

    if not diff_subnet:
        result.skip("All devices on same subnet")
        return result

    master = players[diff_subnet[0]]
    slave = players[diff_subnet[1]]
    master_name = names[diff_subnet[0]]
    slave_name = names[diff_subnet[1]]

    try:
        await ensure_all_solo([master, slave], [master_name, slave_name], verbose)

        master_subnet = ".".join(master.host.split(".")[:3])
        slave_subnet = ".".join(slave.host.split(".")[:3])
        result.add_detail(f"Testing cross-subnet: {master_name} ({master_subnet}) ↔ {slave_name} ({slave_subnet})")

        await master.create_group()
        await asyncio.sleep(1.0)

        # Attempt cross-subnet join
        result.add_detail(f"Attempting join (should fail)...")
        await slave.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

        # Should still be solo (join failed)
        if slave.is_solo:
            result.add_detail(f"✅ Join correctly failed - {slave_name} is still solo")
            result.success()
        else:
            result.fail(f"Unexpected: cross-subnet join succeeded ({slave_name} is {slave.role})")

        # Cleanup
        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except WiiMGroupCompatibilityError as e:
        result.add_detail(f"✅ WiiMGroupCompatibilityError raised: {e}")
        result.success()
    except Exception as e:
        result.fail(f"Unexpected exception: {e}")

    return result


# =============================================================================
# Leave Permutation Tests
# =============================================================================


async def test_slave_leaves(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Slave leaves, master remains master (if other slaves exist) or becomes solo."""
    result = TestResult("Slave leaves group")

    if len(players) < 2:
        result.skip("Need at least 2 devices")
        return result

    # Find two devices on same subnet
    same_subnet = None
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            if are_same_subnet(players[i].host, players[j].host):
                same_subnet = (i, j)
                break
        if same_subnet:
            break

    if not same_subnet:
        result.skip("No two devices on same subnet")
        return result

    master = players[same_subnet[0]]
    slave = players[same_subnet[1]]
    master_name = names[same_subnet[0]]
    slave_name = names[same_subnet[1]]

    try:
        await ensure_all_solo([master, slave], [master_name, slave_name], verbose)

        # Setup group
        await start_radio(master, master_name)
        await master.create_group()
        await asyncio.sleep(1.0)
        await slave.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

        result.add_detail(f"Initial: {master_name} (master), {slave_name} (slave)")

        # Slave leaves
        result.add_detail(f"{slave_name} leaving group...")
        await slave.leave_group()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

        if slave.is_solo and master.is_solo:
            result.add_detail(f"✅ {slave_name} left, {master_name} auto-disbanded (no slaves)")
            result.success()
        elif slave.is_solo and master.is_master:
            result.add_detail(f"✅ {slave_name} left, {master_name} still master")
            result.success()
        else:
            result.fail(f"{slave_name}={slave.role}, {master_name}={master.role}")

        # Cleanup
        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_master_leaves_disbands(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Master leaves = entire group disbands."""
    result = TestResult("Master leaves (disbands all)")

    if len(players) < 2:
        result.skip("Need at least 2 devices")
        return result

    # Find two devices on same subnet
    same_subnet = None
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            if are_same_subnet(players[i].host, players[j].host):
                same_subnet = (i, j)
                break
        if same_subnet:
            break

    if not same_subnet:
        result.skip("No two devices on same subnet")
        return result

    master = players[same_subnet[0]]
    slave = players[same_subnet[1]]
    master_name = names[same_subnet[0]]
    slave_name = names[same_subnet[1]]

    try:
        await ensure_all_solo([master, slave], [master_name, slave_name], verbose)

        # Setup group
        await start_radio(master, master_name)
        await master.create_group()
        await asyncio.sleep(1.0)
        await slave.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

        result.add_detail(f"Initial: {master_name} (master), {slave_name} (slave)")

        # Master leaves (disbands)
        result.add_detail(f"{master_name} (master) leaving group...")
        await master.leave_group()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

        if master.is_solo and slave.is_solo:
            result.add_detail(f"✅ Group disbanded: both devices now solo")
            result.success()
        else:
            result.fail(f"{master_name}={master.role}, {slave_name}={slave.role}")

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_disband(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.disband() releases all members."""
    result = TestResult("Group disband (3 devices)")

    if len(players) < 3:
        result.skip("Need at least 3 devices")
        return result

    # Find three devices on same subnet
    same_subnet = []
    for i, p in enumerate(players):
        for j in range(i + 1, len(players)):
            if are_same_subnet(p.host, players[j].host):
                if i not in same_subnet:
                    same_subnet.append(i)
                if j not in same_subnet:
                    same_subnet.append(j)

    if len(same_subnet) < 3:
        result.skip("Need 3 devices on same subnet")
        return result

    master = players[same_subnet[0]]
    slave1 = players[same_subnet[1]]
    slave2 = players[same_subnet[2]]
    name_m = names[same_subnet[0]]
    name_s1 = names[same_subnet[1]]
    name_s2 = names[same_subnet[2]]

    try:
        await ensure_all_solo([master, slave1, slave2], [name_m, name_s1, name_s2], verbose)

        # Setup 3-device group
        await start_radio(master, name_m)
        await master.create_group()
        await asyncio.sleep(1.0)
        await slave1.join_group(master)
        await asyncio.sleep(2.0)
        await slave2.join_group(master)
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave1.refresh(full=True), slave2.refresh(full=True))

        if not (master.is_master and slave1.is_slave and slave2.is_slave):
            result.fail("Failed to setup 3-device group")
            return result

        result.add_detail(f"Group: {name_m} (master), {name_s1} + {name_s2} (slaves)")
        result.add_detail(f"Group size: {master.group.size}")

        # Disband
        result.add_detail("Calling group.disband()...")
        await master.group.disband()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(full=True), slave1.refresh(full=True), slave2.refresh(full=True))

        if master.is_solo and slave1.is_solo and slave2.is_solo:
            result.add_detail(f"✅ All 3 devices are now solo")
            result.success()
        else:
            result.fail(f"{name_m}={master.role}, {name_s1}={slave1.role}, {name_s2}={slave2.role}")

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Multiple Device Tests
# =============================================================================


async def test_multiple_joins_leaves(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Multiple devices joining and leaving in various orders."""
    result = TestResult("Multiple joins/leaves sequence")

    if len(players) < 3:
        result.skip("Need at least 3 devices")
        return result

    # Find three devices on same subnet
    same_subnet = []
    for i, p in enumerate(players):
        for j in range(i + 1, len(players)):
            if are_same_subnet(p.host, players[j].host):
                if i not in same_subnet:
                    same_subnet.append(i)
                if j not in same_subnet:
                    same_subnet.append(j)

    if len(same_subnet) < 3:
        result.skip("Need 3 devices on same subnet")
        return result

    d1 = players[same_subnet[0]]
    d2 = players[same_subnet[1]]
    d3 = players[same_subnet[2]]
    n1 = names[same_subnet[0]]
    n2 = names[same_subnet[1]]
    n3 = names[same_subnet[2]]

    try:
        await ensure_all_solo([d1, d2, d3], [n1, n2, n3], verbose)

        # Step 1: d1 creates group, d2 joins
        result.add_detail(f"Step 1: {n1} creates group, {n2} joins")
        await start_radio(d1, n1)
        await d1.create_group()
        await asyncio.sleep(1.0)
        await d2.join_group(d1)
        await asyncio.sleep(2.0)
        await asyncio.gather(d1.refresh(), d2.refresh())

        if not (d1.is_master and d2.is_slave):
            result.fail("Step 1 failed")
            return result
        result.add_detail(f"   ✓ {n1}=master, {n2}=slave")

        # Step 2: d3 joins
        result.add_detail(f"Step 2: {n3} joins")
        await d3.join_group(d1)
        await asyncio.sleep(2.0)
        await asyncio.gather(d1.refresh(), d2.refresh(), d3.refresh())

        if not (d1.is_master and d2.is_slave and d3.is_slave):
            result.fail("Step 2 failed")
            return result
        result.add_detail(f"   ✓ Group size: {d1.group.size}")

        # Step 3: d2 leaves
        result.add_detail(f"Step 3: {n2} leaves")
        await d2.leave_group()
        await asyncio.sleep(2.0)
        await asyncio.gather(d1.refresh(), d2.refresh(), d3.refresh())

        if not (d1.is_master and d2.is_solo and d3.is_slave):
            result.fail("Step 3 failed")
            return result
        result.add_detail(f"   ✓ {n2}=solo, group size: {d1.group.size}")

        # Step 4: d2 rejoins
        result.add_detail(f"Step 4: {n2} rejoins")
        await d2.join_group(d1)
        await asyncio.sleep(2.0)
        await asyncio.gather(d1.refresh(), d2.refresh(), d3.refresh())

        if not (d1.is_master and d2.is_slave and d3.is_slave):
            result.fail("Step 4 failed")
            return result
        result.add_detail(f"   ✓ Group restored, size: {d1.group.size}")

        result.success()

        # Cleanup
        await ensure_all_solo([d1, d2, d3], [n1, n2, n3], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Main Test Runner
# =============================================================================


async def run_all_tests(subnet: str | None, verbose: bool) -> list[TestResult]:
    """Run all group operations tests."""
    devices = get_devices_by_subnet(subnet)

    if not devices:
        print("❌ No devices configured for this subnet")
        return []

    print(f"\n{'='*70}")
    print("Group Operations Tests")
    print(f"{'='*70}")
    print(f"Testing {len(devices)} device(s):")
    for d in devices:
        print(f"   • {d.get('name', d['ip'])} ({d['ip']})")
    print()

    # Connect to devices
    clients: list[WiiMClient] = []
    players: list[Player] = []
    names: list[str] = []

    print("📱 Connecting to devices...")
    for device in devices:
        ip = device["ip"]
        try:
            client = WiiMClient(host=ip)
            player = Player(client)
            await player.refresh(full=True)
            device_info = await player.get_device_info()
            name = device_info.name or device.get("name", ip)
            clients.append(client)
            players.append(player)
            names.append(name)
            print(f"   ✓ {name} ({ip}) - {device_info.model}")
        except Exception as e:
            print(f"   ❌ Failed to connect to {ip}: {e}")

    if len(players) < 2:
        print("\n⚠️  Need at least 2 connected devices for most tests")

    # Ensure all start solo
    print("\n🔧 Ensuring all devices are solo...")
    await ensure_all_solo(players, names, verbose)

    # Run tests
    results: list[TestResult] = []

    tests = [
        (
            "Basic Operations",
            [
                test_create_group,
                test_basic_join_leave,
            ],
        ),
        (
            "Join Permutations",
            [
                test_solo_joins_master,
                test_solo_joins_slave,
                test_master_joins_master,
                test_slave_joins_different_master,
            ],
        ),
        (
            "Expected Failures",
            [
                test_cross_subnet_fails,
            ],
        ),
        (
            "Leave Permutations",
            [
                test_slave_leaves,
                test_master_leaves_disbands,
                test_group_disband,
            ],
        ),
        (
            "Multiple Devices",
            [
                test_multiple_joins_leaves,
            ],
        ),
    ]

    for category_name, category_tests in tests:
        print(f"\n{'─'*70}")
        print(f"📋 {category_name}")
        print(f"{'─'*70}")

        for test_func in category_tests:
            result = await test_func(players, names, verbose)
            results.append(result)

            if result.skipped:
                print(f"   ⏭️  SKIP: {result.name} - {result.error}")
            elif result.passed:
                print(f"   ✅ PASS: {result.name}")
            else:
                print(f"   ❌ FAIL: {result.name}")
                if result.error:
                    print(f"      Error: {result.error}")

            if verbose:
                for detail in result.details:
                    print(f"      {detail}")

    # Final cleanup
    print(f"\n{'─'*70}")
    print("🧹 Final cleanup...")
    await ensure_all_solo(players, names, False)

    # Close connections
    for client in clients:
        try:
            await client.close()
        except Exception:
            pass

    return results


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Group operations tests - join/leave all permutations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--subnet",
        choices=["1", "6", "all"],
        default="all",
        help="Subnet to test: 1 (192.168.1.x), 6 (192.168.6.x), or all",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed test output",
    )

    args = parser.parse_args()
    subnet = None if args.subnet == "all" else args.subnet

    results = await run_all_tests(subnet, args.verbose)

    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}\n")

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)

    print(f"Total: {len(results)} tests")
    print(f"   ✅ Passed:  {passed}")
    print(f"   ❌ Failed:  {failed}")
    print(f"   ⏭️  Skipped: {skipped}")

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r.passed and not r.skipped:
                print(f"   ❌ {r.name}: {r.error}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
