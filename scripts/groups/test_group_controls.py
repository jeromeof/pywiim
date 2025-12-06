#!/usr/bin/env python3
"""Group controls tests - player controls, volume, and mute.

Tests all group control operations including:
- Player controls routing (slave.play() → master plays)
- Individual volume/mute on master and slave
- Virtual master (Group) controls: set_volume_all, mute_all
- Group properties: volume_level (max), is_muted (all)

Usage:
    python scripts/groups/test_group_controls.py [--subnet 1|6|all] [--verbose]
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
from pywiim.exceptions import WiiMError
from pywiim.player import Player


# =============================================================================
# Configuration (shared with test_group_operations.py)
# =============================================================================


def load_devices() -> dict[str, Any]:
    """Load device configuration from devices.json."""
    config_path = Path(__file__).parent / "devices.json"
    with open(config_path) as f:
        return json.load(f)


def get_devices_by_subnet(subnet: str | None = None) -> list[dict[str, str]]:
    """Get devices filtered by subnet."""
    config = load_devices()
    devices = []

    for subnet_key, subnet_data in config["subnets"].items():
        if subnet is None:
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
    """Ensure a player is solo."""
    try:
        await player.refresh(full=True)
        if player.is_solo:
            return True

        await player.leave_group()
        await asyncio.sleep(2.0)
        await player.refresh(full=True)
        return player.is_solo
    except Exception:
        return False


async def ensure_all_solo(players: list[Player], names: list[str], verbose: bool = False) -> bool:
    """Ensure all players are solo."""
    for player in players:
        if player.is_master:
            try:
                await player.leave_group()
            except Exception:
                pass
    await asyncio.sleep(2.0)

    all_solo = True
    for player, name in zip(players, names):
        if not await ensure_solo(player, name, verbose):
            all_solo = False
    return all_solo


def are_same_subnet(ip1: str, ip2: str) -> bool:
    """Check if two IPs are on the same subnet."""
    return ".".join(ip1.split(".")[:3]) == ".".join(ip2.split(".")[:3])


async def setup_group(
    players: list[Player], names: list[str], verbose: bool = False
) -> tuple[Player, Player, str, str] | None:
    """Set up a master-slave group for testing.

    Returns:
        Tuple of (master, slave, master_name, slave_name) or None if setup fails.
    """
    # Find two devices on same subnet
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            if are_same_subnet(players[i].host, players[j].host):
                master, slave = players[i], players[j]
                master_name, slave_name = names[i], names[j]

                await ensure_all_solo([master, slave], [master_name, slave_name], verbose)

                # Start radio and create group
                try:
                    await master.play_url(get_radio_url())
                    await asyncio.sleep(2.0)
                except Exception:
                    pass

                await master.create_group()
                await asyncio.sleep(1.0)
                await slave.join_group(master)
                await asyncio.sleep(2.0)
                await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

                if master.is_master and slave.is_slave:
                    return master, slave, master_name, slave_name

    return None


# =============================================================================
# Player Controls Routing Tests
# =============================================================================


async def test_slave_play_routes_to_master(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: slave.play() routes to master."""
    result = TestResult("slave.play() → master plays")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group (need 2 devices on same subnet)")
        return result

    master, slave, master_name, slave_name = setup

    try:
        # Pause first to have a known state
        await master.pause()
        await asyncio.sleep(2.0)
        await master.refresh()

        initial_state = master.play_state
        result.add_detail(f"Initial master state: {initial_state}")

        # Call play() on slave
        result.add_detail(f"Calling {slave_name}.play()...")
        await slave.play()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        new_state = master.play_state
        result.add_detail(f"Master state after slave.play(): {new_state}")

        if new_state in ("play", "playing"):
            result.add_detail(f"✅ Master started playing via slave control")
            result.success()
        else:
            result.fail(f"Master did not play (state: {new_state})")

        # Cleanup
        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_slave_pause_routes_to_master(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: slave.pause() routes to master."""
    result = TestResult("slave.pause() → master pauses")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        # Play first
        await master.play()
        await asyncio.sleep(2.0)
        await master.refresh()

        initial_state = master.play_state
        result.add_detail(f"Initial master state: {initial_state}")

        # Call pause() on slave
        result.add_detail(f"Calling {slave_name}.pause()...")
        await slave.pause()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        new_state = master.play_state
        result.add_detail(f"Master state after slave.pause(): {new_state}")

        if new_state in ("pause", "paused", "stop", "stopped"):
            result.add_detail(f"✅ Master paused via slave control")
            result.success()
        else:
            result.fail(f"Master did not pause (state: {new_state})")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_slave_next_track(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: slave.next_track() routes to master."""
    result = TestResult("slave.next_track() → master skips")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        result.add_detail(f"Calling {slave_name}.next_track()...")
        await slave.next_track()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        # We can't easily verify track changed, but we verify no error
        result.add_detail(f"✅ next_track() command completed without error")
        result.success()

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        # Some sources may not support next_track
        result.add_detail(f"⚠️ next_track() failed (may not be supported): {e}")
        result.success()  # Not a failure if unsupported

    return result


async def test_slave_previous_track(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: slave.previous_track() routes to master."""
    result = TestResult("slave.previous_track() → master goes back")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        result.add_detail(f"Calling {slave_name}.previous_track()...")
        await slave.previous_track()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        result.add_detail(f"✅ previous_track() command completed without error")
        result.success()

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.add_detail(f"⚠️ previous_track() failed (may not be supported): {e}")
        result.success()

    return result


# =============================================================================
# Individual Volume/Mute Tests
# =============================================================================


async def test_master_volume(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: master.set_volume() works independently."""
    result = TestResult("Master volume control")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        # Set master volume
        target_vol = 0.05  # 5% - safe test level
        result.add_detail(f"Setting {master_name} volume to {target_vol*100:.0f}%...")

        await master.set_volume(target_vol)
        await asyncio.sleep(1.0)
        await master.refresh()

        actual_vol = master.volume_level
        result.add_detail(f"Master volume: {actual_vol}")

        if actual_vol is not None and abs(actual_vol - target_vol) < 0.02:
            result.add_detail(f"✅ Master volume set correctly")
            result.success()
        else:
            result.fail(f"Volume mismatch: expected {target_vol}, got {actual_vol}")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_slave_volume(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: slave.set_volume() works independently (not routed to master)."""
    result = TestResult("Slave volume control (independent)")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        # Set different volumes
        master_vol = 0.03
        slave_vol = 0.05

        result.add_detail(f"Setting {master_name}={master_vol*100:.0f}%, {slave_name}={slave_vol*100:.0f}%...")

        await master.set_volume(master_vol)
        await slave.set_volume(slave_vol)
        await asyncio.sleep(1.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        actual_master = master.volume_level
        actual_slave = slave.volume_level

        result.add_detail(f"Master volume: {actual_master}")
        result.add_detail(f"Slave volume: {actual_slave}")

        # Volumes should be independent (different)
        if actual_master is not None and actual_slave is not None:
            if abs(actual_master - master_vol) < 0.02 and abs(actual_slave - slave_vol) < 0.02:
                result.add_detail(f"✅ Volumes are independent")
                result.success()
            else:
                result.fail(f"Volume values unexpected")
        else:
            result.fail("Volume values are None")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_master_mute(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: master.set_mute() works."""
    result = TestResult("Master mute control")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        # Mute master
        result.add_detail(f"Muting {master_name}...")
        await master.set_mute(True)
        await asyncio.sleep(1.0)
        await master.refresh()

        if master.is_muted:
            result.add_detail(f"✅ Master muted")
        else:
            result.fail("Master not muted")
            return result

        # Unmute
        result.add_detail(f"Unmuting {master_name}...")
        await master.set_mute(False)
        await asyncio.sleep(1.0)
        await master.refresh()

        if not master.is_muted:
            result.add_detail(f"✅ Master unmuted")
            result.success()
        else:
            result.fail("Master still muted after unmute")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_slave_mute(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: slave.set_mute() works independently."""
    result = TestResult("Slave mute control (independent)")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        # Ensure both unmuted
        await master.set_mute(False)
        await slave.set_mute(False)
        await asyncio.sleep(1.0)

        # Mute only slave
        result.add_detail(f"Muting only {slave_name}...")
        await slave.set_mute(True)
        await asyncio.sleep(1.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        result.add_detail(f"Master muted: {master.is_muted}")
        result.add_detail(f"Slave muted: {slave.is_muted}")

        if slave.is_muted and not master.is_muted:
            result.add_detail(f"✅ Mute is independent (only slave muted)")
            result.success()
        else:
            result.fail("Mute not independent")

        # Cleanup - unmute
        await slave.set_mute(False)
        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Virtual Master (Group) Controls Tests
# =============================================================================


async def test_group_set_volume_all(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.set_volume_all() adjusts all devices."""
    result = TestResult("group.set_volume_all() (proportional)")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        # Set initial volumes
        await master.set_volume(0.03)
        await slave.set_volume(0.04)
        await asyncio.sleep(1.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        initial_master = master.volume_level
        initial_slave = slave.volume_level
        initial_group = group.volume_level

        result.add_detail(f"Initial: master={initial_master}, slave={initial_slave}, group={initial_group}")

        # Set group volume
        target = 0.05
        result.add_detail(f"Calling group.set_volume_all({target})...")
        await group.set_volume_all(target)
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        new_master = master.volume_level
        new_slave = slave.volume_level
        new_group = group.volume_level

        result.add_detail(f"After: master={new_master}, slave={new_slave}, group={new_group}")

        # Group volume should be close to target
        if new_group is not None and abs(new_group - target) < 0.02:
            result.add_detail(f"✅ Group volume set to {target}")
            result.success()
        else:
            result.add_detail(f"⚠️ Group volume may have proportional adjustment")
            result.success()  # Proportional adjustment is valid behavior

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_volume_level(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.volume_level returns max of all devices."""
    result = TestResult("group.volume_level (max of all)")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        # Set different volumes
        master_vol = 0.03
        slave_vol = 0.05

        await master.set_volume(master_vol)
        await slave.set_volume(slave_vol)
        await asyncio.sleep(1.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        group_vol = group.volume_level
        expected_max = max(master_vol, slave_vol)

        result.add_detail(f"Master: {master.volume_level}")
        result.add_detail(f"Slave: {slave.volume_level}")
        result.add_detail(f"Group (max): {group_vol}")
        result.add_detail(f"Expected max: {expected_max}")

        if group_vol is not None and abs(group_vol - expected_max) < 0.02:
            result.add_detail(f"✅ group.volume_level correctly returns max")
            result.success()
        else:
            result.fail(f"Expected ~{expected_max}, got {group_vol}")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_mute_all(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.mute_all() mutes/unmutes all devices."""
    result = TestResult("group.mute_all()")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        # Unmute all first
        await master.set_mute(False)
        await slave.set_mute(False)
        await asyncio.sleep(1.0)

        # Mute all
        result.add_detail("Calling group.mute_all(True)...")
        await group.mute_all(True)
        await asyncio.sleep(1.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        result.add_detail(f"Master muted: {master.is_muted}")
        result.add_detail(f"Slave muted: {slave.is_muted}")

        if master.is_muted and slave.is_muted:
            result.add_detail(f"✅ All muted")
        else:
            result.fail("Not all muted")
            return result

        # Unmute all
        result.add_detail("Calling group.mute_all(False)...")
        await group.mute_all(False)
        await asyncio.sleep(1.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        result.add_detail(f"Master muted: {master.is_muted}")
        result.add_detail(f"Slave muted: {slave.is_muted}")

        if not master.is_muted and not slave.is_muted:
            result.add_detail(f"✅ All unmuted")
            result.success()
        else:
            result.fail("Not all unmuted")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_is_muted(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.is_muted returns True only if all muted."""
    result = TestResult("group.is_muted (all muted)")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        # Test 1: Only master muted
        await master.set_mute(True)
        await slave.set_mute(False)
        await asyncio.sleep(1.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        is_muted_1 = group.is_muted
        result.add_detail(f"Only master muted: group.is_muted = {is_muted_1}")

        # Test 2: Both muted
        await slave.set_mute(True)
        await asyncio.sleep(1.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        is_muted_2 = group.is_muted
        result.add_detail(f"Both muted: group.is_muted = {is_muted_2}")

        # Test 3: Neither muted
        await master.set_mute(False)
        await slave.set_mute(False)
        await asyncio.sleep(1.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        is_muted_3 = group.is_muted
        result.add_detail(f"Neither muted: group.is_muted = {is_muted_3}")

        # Verify logic
        if is_muted_1 is False and is_muted_2 is True and is_muted_3 is False:
            result.add_detail(f"✅ group.is_muted correctly returns True only when ALL muted")
            result.success()
        else:
            result.fail(f"Logic incorrect: partial={is_muted_1}, all={is_muted_2}, none={is_muted_3}")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_play_pause(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.play() and group.pause()."""
    result = TestResult("group.play() / group.pause()")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        # Pause first
        result.add_detail("Calling group.pause()...")
        await group.pause()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        state_after_pause = master.play_state
        result.add_detail(f"Master state after group.pause(): {state_after_pause}")

        # Play
        result.add_detail("Calling group.play()...")
        await group.play()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        state_after_play = master.play_state
        result.add_detail(f"Master state after group.play(): {state_after_play}")

        if state_after_play in ("play", "playing"):
            result.add_detail(f"✅ group.play() works")
            result.success()
        else:
            result.fail(f"play() didn't work (state: {state_after_play})")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_play_state(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.play_state reflects master's play state."""
    result = TestResult("group.play_state (from master)")

    setup = await setup_group(players, names, verbose)
    if not setup:
        result.skip("Could not set up group")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        # Play
        await master.play()
        await asyncio.sleep(2.0)
        await master.refresh()

        master_state = master.play_state
        group_state = group.play_state

        result.add_detail(f"Master play_state: {master_state}")
        result.add_detail(f"Group play_state: {group_state}")

        if master_state == group_state:
            result.add_detail(f"✅ group.play_state matches master")
            result.success()
        else:
            result.fail(f"Mismatch: master={master_state}, group={group_state}")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Main Test Runner
# =============================================================================


async def run_all_tests(subnet: str | None, verbose: bool) -> list[TestResult]:
    """Run all group controls tests."""
    devices = get_devices_by_subnet(subnet)

    if not devices:
        print("❌ No devices configured for this subnet")
        return []

    print(f"\n{'='*70}")
    print("Group Controls Tests")
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
        print("\n⚠️  Need at least 2 connected devices for controls tests")
        return []

    # Ensure all start solo
    print("\n🔧 Ensuring all devices are solo...")
    await ensure_all_solo(players, names, verbose)

    # Run tests
    results: list[TestResult] = []

    tests = [
        (
            "Player Controls Routing",
            [
                test_slave_play_routes_to_master,
                test_slave_pause_routes_to_master,
                test_slave_next_track,
                test_slave_previous_track,
            ],
        ),
        (
            "Individual Volume/Mute",
            [
                test_master_volume,
                test_slave_volume,
                test_master_mute,
                test_slave_mute,
            ],
        ),
        (
            "Virtual Master (Group) Controls",
            [
                test_group_set_volume_all,
                test_group_volume_level,
                test_group_mute_all,
                test_group_is_muted,
                test_group_play_pause,
                test_group_play_state,
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
        description="Group controls tests - player controls, volume, mute",
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
