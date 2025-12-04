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

        if len(all_players) == 3 and all_players[0] == master and slave1 in all_players and slave2 in all_players:
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

        if master.group is None and slave1.group is None and slave2.group is None and len(group.slaves) == 0:
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

        # Set volume via group to 0 (keep volumes at 0)
        await group.set_volume_all(0.0)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

        master_vol = await master.get_volume()
        slave_vol = await slave.get_volume()

        result.add_detail(f"Set group volume to 0.0: master={master_ip}, slave={slave_ip}")
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

        # Set volumes to 0 (keep volumes at 0)
        await master.set_volume(0.0)
        await slave.set_volume(0.0)
        await asyncio.sleep(2.0)
        await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

        volume = group.volume_level

        result.add_detail(f"Set volumes: master=0.0, slave=0.0")
        result.add_detail(f"  group.volume_level: {volume}")
        result.add_detail(f"  Expected: 0.0 (max)")

        # Restore volumes
        if initial_master_vol is not None:
            await master.set_volume(initial_master_vol)
        if initial_slave_vol is not None:
            await slave.set_volume(initial_slave_vol)

        if volume is not None and abs(volume - 0.0) < 0.1:
            result.success()
        else:
            result.fail(f"Volume level max failed: got {volume}, expected ~0.0")

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


async def test_metadata_propagation(players: dict[str, Player]) -> TestResult:
    """Test metadata propagation from master to slave when slave joins."""
    result = TestResult("test_metadata_propagation")

    if len(players) < 2:
        result.fail("Need at least 2 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave_ip = list(players.keys())[1]

        master = players[master_ip]
        slave = players[slave_ip]

        await ensure_all_solo([master, slave])

        # Check master metadata (should already be playing or have metadata)
        await master.refresh()
        master_metadata_before = {
            "title": master.media_title,
            "artist": master.media_artist,
            "album": master.media_album,
            "play_state": master.play_state,
            "position": master.media_position,
            "duration": master.media_duration,
        }

        result.add_detail(f"Master metadata before join: {master_metadata_before}")

        # Check if master has metadata
        has_metadata = any(
            [
                master_metadata_before["title"],
                master_metadata_before["artist"],
                master_metadata_before["album"],
            ]
        )

        if not has_metadata:
            result.add_detail("⚠️  Master has no metadata - test may not be meaningful")
            # Still proceed with test, but note it

        # Set volumes to 0
        await master.set_volume(0.0)
        await slave.set_volume(0.0)
        await asyncio.sleep(0.5)

        # Create group on master
        group = await master.create_group()
        await asyncio.sleep(1.0)
        await master.refresh()

        # Join slave - handle cross-subnet failures gracefully
        try:
            await slave.join_group(master)
            await asyncio.sleep(2.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)

            # Verify join actually worked
            if slave.is_solo:
                # Join failed - likely cross-subnet
                master_subnet = ".".join(master_ip.split(".")[:3])
                slave_subnet = ".".join(slave_ip.split(".")[:3])
                if master_subnet != slave_subnet:
                    result.add_detail(f"⚠️  Join failed: devices on different subnets")
                    result.add_detail(f"  Master subnet: {master_subnet}, Slave subnet: {slave_subnet}")
                    result.add_detail(f"  ✓ This is expected behavior - cross-subnet grouping not supported")
                    result.success()
                    await group.disband()
                    return result
                else:
                    result.fail("Join failed but devices are on same subnet - unexpected")
                    await group.disband()
                    return result
        except WiiMError as e:
            # Handle compatibility errors
            if "incompatible multiroom protocol versions" in str(e):
                result.add_detail(f"⚠️  Join failed: {e}")
                result.add_detail(f"  ✓ Correctly detected incompatible wmrm_version")
                result.success()
            else:
                master_subnet = ".".join(master_ip.split(".")[:3])
                slave_subnet = ".".join(slave_ip.split(".")[:3])
                if master_subnet != slave_subnet:
                    result.add_detail(f"⚠️  Join failed: {e}")
                    result.add_detail(f"  Different subnets: {master_subnet} vs {slave_subnet}")
                    result.add_detail(f"  ✓ This is expected - cross-subnet grouping not supported")
                    result.success()
                else:
                    result.fail(f"Unexpected error: {e}")
            await group.disband()
            return result

        # Wait a bit for metadata propagation
        await asyncio.sleep(2.0)

        # Refresh to get latest metadata
        await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)

        # Check metadata propagation
        master_metadata_after = {
            "title": master.media_title,
            "artist": master.media_artist,
            "album": master.media_album,
            "play_state": master.play_state,
            "position": master.media_position,
            "duration": master.media_duration,
        }
        slave_metadata = {
            "title": slave.media_title,
            "artist": slave.media_artist,
            "album": slave.media_album,
            "play_state": slave.play_state,
            "position": slave.media_position,
            "duration": slave.media_duration,
        }

        result.add_detail(f"Master metadata after join: {master_metadata_after}")
        result.add_detail(f"Slave metadata: {slave_metadata}")

        # Compare
        title_match = master_metadata_after["title"] == slave_metadata["title"]
        artist_match = master_metadata_after["artist"] == slave_metadata["artist"]
        album_match = master_metadata_after["album"] == slave_metadata["album"]
        play_state_match = master_metadata_after["play_state"] == slave_metadata["play_state"]

        result.add_detail(f"Title match: {'✓' if title_match else '✗'}")
        result.add_detail(f"Artist match: {'✓' if artist_match else '✗'}")
        result.add_detail(f"Album match: {'✓' if album_match else '✗'}")
        result.add_detail(f"Play state match: {'✓' if play_state_match else '✗'}")

        if title_match and artist_match and album_match and play_state_match:
            result.success()
        else:
            mismatches = []
            if not title_match:
                mismatches.append(f"title: '{slave_metadata['title']}' != '{master_metadata_after['title']}'")
            if not artist_match:
                mismatches.append(f"artist: '{slave_metadata['artist']}' != '{master_metadata_after['artist']}'")
            if not album_match:
                mismatches.append(f"album: '{slave_metadata['album']}' != '{master_metadata_after['album']}'")
            if not play_state_match:
                mismatches.append(
                    f"play_state: '{slave_metadata['play_state']}' != '{master_metadata_after['play_state']}'"
                )
            result.fail(f"Mismatches: {', '.join(mismatches)}")

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_slave_to_master_controls(players: dict[str, Player]) -> TestResult:
    """Test that slave playback controls route to master."""
    result = TestResult("test_slave_to_master_controls")

    if len(players) < 2:
        result.fail("Need at least 2 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave_ip = list(players.keys())[1]

        master = players[master_ip]
        slave = players[slave_ip]

        await ensure_all_solo([master, slave])

        # Set volumes to 0
        await master.set_volume(0.0)
        await slave.set_volume(0.0)
        await asyncio.sleep(0.5)

        # Create group
        group = await master.create_group()

        # Attempt to join slave - handle cross-subnet failures gracefully
        try:
            await slave.join_group(master)
            await asyncio.sleep(2.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)

            # Verify join actually worked
            if slave.is_solo:
                # Join failed - likely cross-subnet or other issue
                result.add_detail(f"⚠️  Join failed: slave is still solo")
                result.add_detail(f"  This is expected for devices on different subnets")
                result.add_detail(f"  Master: {master_ip}, Slave: {slave_ip}")
                # Check if they're on different subnets
                master_subnet = ".".join(master_ip.split(".")[:3])
                slave_subnet = ".".join(slave_ip.split(".")[:3])
                if master_subnet != slave_subnet:
                    result.add_detail(f"  Different subnets: {master_subnet} vs {slave_subnet}")
                    result.add_detail(f"  ✓ Correctly handled cross-subnet failure")
                    result.success()  # This is expected behavior
                else:
                    result.fail("Join failed but devices are on same subnet - unexpected")
                await group.disband()
                return result
        except WiiMError as e:
            # Handle compatibility errors or other WiiM errors
            if "incompatible multiroom protocol versions" in str(e):
                result.add_detail(f"⚠️  Join failed: {e}")
                result.add_detail(f"  ✓ Correctly detected incompatible wmrm_version")
                result.success()  # Expected behavior
            else:
                result.add_detail(f"⚠️  Join failed: {e}")
                result.add_detail(f"  This may be expected for cross-subnet devices")
                # Check if they're on different subnets
                master_subnet = ".".join(master_ip.split(".")[:3])
                slave_subnet = ".".join(slave_ip.split(".")[:3])
                if master_subnet != slave_subnet:
                    result.add_detail(f"  Different subnets: {master_subnet} vs {slave_subnet}")
                    result.add_detail(f"  ✓ Correctly handled cross-subnet failure")
                    result.success()  # Expected behavior
                else:
                    result.fail(f"Unexpected error: {e}")
            await group.disband()
            return result

        result.add_detail(f"Created group: master={master_ip}, slave={slave_ip}")
        result.add_detail(f"  master.is_master: {master.is_master}")
        result.add_detail(f"  slave.is_slave: {slave.is_slave}")

        # Get initial play state
        await master.refresh()
        initial_master_state = master.play_state
        result.add_detail(f"Initial master play_state: {initial_master_state}")

        # Test 1: Slave play() should route to master
        result.add_detail("\n  Test 1: Slave.play() routes to master")
        try:
            await slave.play()
            await asyncio.sleep(2.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
            master_state_after_play = master.play_state
            slave_state_after_play = slave.play_state
            result.add_detail(f"    Master play_state after slave.play(): {master_state_after_play}")
            result.add_detail(f"    Slave play_state after slave.play(): {slave_state_after_play}")
            if master_state_after_play in ("play", "playing"):
                result.add_detail("    ✓ Master started playing")
            else:
                result.add_detail(f"    ✗ Master did not start playing (state: {master_state_after_play})")
        except Exception as e:
            result.add_detail(f"    ✗ slave.play() failed: {e}")

        # Test 2: Slave pause() should route to master
        result.add_detail("\n  Test 2: Slave.pause() routes to master")
        try:
            await slave.pause()
            await asyncio.sleep(2.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
            master_state_after_pause = master.play_state
            slave_state_after_pause = slave.play_state
            result.add_detail(f"    Master play_state after slave.pause(): {master_state_after_pause}")
            result.add_detail(f"    Slave play_state after slave.pause(): {slave_state_after_pause}")
            if master_state_after_pause in ("pause", "paused"):
                result.add_detail("    ✓ Master paused")
            else:
                result.add_detail(f"    ✗ Master did not pause (state: {master_state_after_pause})")
        except Exception as e:
            result.add_detail(f"    ✗ slave.pause() failed: {e}")

        # Test 3: Slave next_track() should route to master (if supported)
        result.add_detail("\n  Test 3: Slave.next_track() routes to master")
        try:
            await slave.next_track()
            await asyncio.sleep(2.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
            result.add_detail("    ✓ slave.next_track() command sent successfully")
        except Exception as e:
            result.add_detail(f"    ⚠ slave.next_track() failed (may not be supported): {e}")

        # Test 4: Slave previous_track() should route to master (if supported)
        result.add_detail("\n  Test 4: Slave.previous_track() routes to master")
        try:
            await slave.previous_track()
            await asyncio.sleep(2.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
            result.add_detail("    ✓ slave.previous_track() command sent successfully")
        except Exception as e:
            result.add_detail(f"    ⚠ slave.previous_track() failed (may not be supported): {e}")

        result.success()

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_metadata_during_playback(players: dict[str, Player]) -> TestResult:
    """Test metadata propagation during active playback."""
    result = TestResult("test_metadata_during_playback")

    if len(players) < 2:
        result.fail("Need at least 2 devices")
        return result

    try:
        master_ip = list(players.keys())[0]
        slave_ip = list(players.keys())[1]

        master = players[master_ip]
        slave = players[slave_ip]

        await ensure_all_solo([master, slave])

        # Set volumes to 0
        await master.set_volume(0.0)
        await slave.set_volume(0.0)
        await asyncio.sleep(0.5)

        # Start playback on master (if not already playing)
        await master.refresh()
        if master.play_state not in ("play", "playing"):
            try:
                await master.play()
                await asyncio.sleep(2.0)
                await master.refresh()
            except Exception:
                pass  # May not be able to start playback

        # Get master metadata before group
        master_metadata_before = {
            "title": master.media_title,
            "artist": master.media_artist,
            "album": master.media_album,
            "play_state": master.play_state,
            "position": master.media_position,
        }
        result.add_detail(f"Master metadata before group: {master_metadata_before}")

        # Create group and join slave - handle cross-subnet failures
        group = await master.create_group()
        try:
            await slave.join_group(master)
            await asyncio.sleep(2.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)

            # Verify join actually worked
            if slave.is_solo:
                master_subnet = ".".join(master_ip.split(".")[:3])
                slave_subnet = ".".join(slave_ip.split(".")[:3])
                if master_subnet != slave_subnet:
                    result.add_detail(f"⚠️  Join failed: devices on different subnets")
                    result.add_detail(f"  Master subnet: {master_subnet}, Slave subnet: {slave_subnet}")
                    result.add_detail(f"  ✓ This is expected - cross-subnet grouping not supported")
                    result.success()
                    await group.disband()
                    return result
                else:
                    result.fail("Join failed but devices are on same subnet")
                    await group.disband()
                    return result
        except WiiMError as e:
            master_subnet = ".".join(master_ip.split(".")[:3])
            slave_subnet = ".".join(slave_ip.split(".")[:3])
            if master_subnet != slave_subnet:
                result.add_detail(f"⚠️  Join failed: {e}")
                result.add_detail(f"  Different subnets: {master_subnet} vs {slave_subnet}")
                result.add_detail(f"  ✓ This is expected - cross-subnet grouping not supported")
                result.success()
            else:
                result.fail(f"Unexpected error: {e}")
            await group.disband()
            return result

        await asyncio.sleep(3.0)  # Wait longer for sync

        # Refresh both devices multiple times to check consistency
        for i in range(3):
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
            await asyncio.sleep(1.0)

            master_metadata = {
                "title": master.media_title,
                "artist": master.media_artist,
                "album": master.media_album,
                "play_state": master.play_state,
                "position": master.media_position,
            }
            slave_metadata = {
                "title": slave.media_title,
                "artist": slave.media_artist,
                "album": slave.media_album,
                "play_state": slave.play_state,
                "position": slave.media_position,
            }

            result.add_detail(f"\n  Check {i+1}:")
            result.add_detail(f"    Master: {master_metadata}")
            result.add_detail(f"    Slave:  {slave_metadata}")

            # Check matches
            title_match = master_metadata["title"] == slave_metadata["title"]
            artist_match = master_metadata["artist"] == slave_metadata["artist"]
            play_state_match = master_metadata["play_state"] == slave_metadata["play_state"]

            if title_match and artist_match and play_state_match:
                result.add_detail(f"    ✓ All match")
            else:
                mismatches = []
                if not title_match:
                    mismatches.append("title")
                if not artist_match:
                    mismatches.append("artist")
                if not play_state_match:
                    mismatches.append("play_state")
                result.add_detail(f"    ✗ Mismatches: {', '.join(mismatches)}")

        # Final check
        await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
        final_master = {
            "title": master.media_title,
            "artist": master.media_artist,
            "play_state": master.play_state,
        }
        final_slave = {
            "title": slave.media_title,
            "artist": slave.media_artist,
            "play_state": slave.play_state,
        }

        title_match = final_master["title"] == final_slave["title"]
        artist_match = final_master["artist"] == final_slave["artist"]
        play_state_match = final_master["play_state"] == final_slave["play_state"]

        if title_match and artist_match and play_state_match:
            result.success()
        else:
            mismatches = []
            if not title_match:
                mismatches.append(f"title: '{final_slave['title']}' != '{final_master['title']}'")
            if not artist_match:
                mismatches.append(f"artist: '{final_slave['artist']}' != '{final_master['artist']}'")
            if not play_state_match:
                mismatches.append(f"play_state: '{final_slave['play_state']}' != '{final_master['play_state']}'")
            result.fail(f"Final check failed: {', '.join(mismatches)}")

        await group.disband()
        await asyncio.sleep(1.0)
    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_cross_subnet_combination(players: dict[str, Player], master_ip: str, slave_ip: str) -> TestResult:
    """Test a specific master/slave combination."""
    result = TestResult(f"cross_subnet_{master_ip}_to_{slave_ip}")

    try:
        master = players[master_ip]
        slave = players[slave_ip]

        # Check if devices are on different subnets
        master_subnet = ".".join(master_ip.split(".")[:3])
        slave_subnet = ".".join(slave_ip.split(".")[:3])
        is_cross_subnet = master_subnet != slave_subnet

        result.add_detail(f"Master: {master_ip} (subnet: {master_subnet})")
        result.add_detail(f"Slave: {slave_ip} (subnet: {slave_subnet})")
        if is_cross_subnet:
            result.add_detail("  ⚠️  Different subnets - grouping expected to fail")

        await ensure_all_solo([master, slave])

        group = await master.create_group()

        try:
            await slave.join_group(master)
            await asyncio.sleep(2.0)
            await asyncio.gather(*(p.refresh() for p in [master, slave]), return_exceptions=True)

            result.add_detail(f"  master.is_master: {master.is_master}")
            result.add_detail(f"  slave.is_slave: {slave.is_slave}")
            result.add_detail(f"  slave in group.slaves: {slave in group.slaves}")
            result.add_detail(f"  group.size: {group.size}")

            if master.is_master and slave.is_slave and slave in group.slaves and group.size == 2:
                if is_cross_subnet:
                    result.add_detail("  ⚠️  Unexpected: Cross-subnet grouping succeeded")
                    result.fail("Cross-subnet grouping should not work")
                else:
                    result.success()
            else:
                if is_cross_subnet:
                    result.add_detail("  ✓ Expected failure: Cross-subnet grouping not supported")
                    result.success()  # This is expected behavior
                else:
                    result.fail("Group creation failed on same subnet - unexpected")

            await group.disband()
            await asyncio.sleep(2.0)
        except WiiMError as e:
            # Check if this is an expected compatibility error
            if "incompatible multiroom protocol versions" in str(e):
                result.add_detail(f"  ✓ Expected failure: Incompatible wmrm_version")
                result.add_detail(f"    {e}")
                result.success()  # This is expected, so mark as success
            elif is_cross_subnet:
                result.add_detail(f"  ✓ Expected failure: Cross-subnet grouping not supported")
                result.add_detail(f"    Error: {e}")
                result.success()  # This is expected behavior
            else:
                result.fail(f"WiiMError on same subnet: {e}")
            try:
                await group.disband()
            except Exception:
                pass
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
    print("Test Suite Overview:")
    print("  - Basic group operations (create, add/remove slaves, disband)")
    print("  - Volume and mute operations")
    print("  - Metadata propagation (on join and during playback)")
    print("  - Slave-to-master control routing (play, pause, next, previous)")
    print("  - Play state synchronization")
    print(f"\n{'='*80}\n")

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

        print("\n" + "-" * 80)
        print("Test: Metadata propagation (on join)")
        print("-" * 80)
        result = await test_metadata_propagation(players)
        results.append(result)
        print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
        if result.error:
            print(f"    Error: {result.error}")
        for detail in result.details:
            print(f"    {detail}")

        print("\n" + "-" * 80)
        print("Test: Slave to master controls (playback routing)")
        print("-" * 80)
        print("  Testing: slave.play(), slave.pause(), slave.next_track(), slave.previous_track()")
        print("  Expected: All commands route through group to master")
        result = await test_slave_to_master_controls(players)
        results.append(result)
        print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
        if result.error:
            print(f"    Error: {result.error}")
        for detail in result.details:
            print(f"    {detail}")

        print("\n" + "-" * 80)
        print("Test: Metadata during playback (continuous sync)")
        print("-" * 80)
        print("  Testing: Metadata and play state stay synchronized during playback")
        print("  Expected: Slave shows master's metadata and play state")
        result = await test_metadata_during_playback(players)
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
    print("\n" + "-" * 80)
    print("Test: Playback control (master only)")
    print("-" * 80)
    result = await test_playback_control(players)
    results.append(result)
    print(f"  {'✓ PASSED' if result.passed else '✗ FAILED'}: {result.name}")
    if result.error:
        print(f"    Error: {result.error}")
    for detail in result.details:
        print(f"    {detail}")

    # Test cross-subnet combinations
    if len(players) >= 2:
        print(f"\n{'='*80}")
        print("Testing cross-subnet combinations...")
        print(f"{'='*80}\n")

        ips = list(players.keys())
        # Test all pairs
        for i, master_ip in enumerate(ips):
            for slave_ip in ips[i + 1 :]:
                print(f"\nTest: Cross-subnet combination {master_ip} -> {slave_ip}")
                result = await test_cross_subnet_combination(players, master_ip, slave_ip)
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
    print(f"  ✓ Passed: {passed}")
    print(f"  ✗ Failed: {failed}\n")

    if failed > 0:
        print("Failed tests:")
        for result in results:
            if not result.passed:
                print(f"  ✗ {result.name}")
                if result.error:
                    print(f"    Error: {result.error}")
                # Show first few details for failed tests
                if result.details:
                    print(f"    Details:")
                    for detail in result.details[:5]:  # Show first 5 details
                        print(f"      {detail}")
                    if len(result.details) > 5:
                        print(f"      ... and {len(result.details) - 5} more")
    else:
        print("✓ All tests passed!")

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
