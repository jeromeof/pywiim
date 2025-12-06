#!/usr/bin/env python3
"""Group metadata tests - metadata propagation and synchronization.

Tests metadata propagation including:
- Metadata on join (slave gets master metadata)
- Metadata during playback (continuous sync)
- Virtual master metadata (group delegates to master)
- Play state synchronization

Usage:
    python scripts/groups/test_group_metadata.py [--subnet 1|6|all] [--verbose]
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
# Configuration (shared with other test files)
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


async def setup_group_with_playback(
    players: list[Player], names: list[str], verbose: bool = False
) -> tuple[Player, Player, str, str] | None:
    """Set up a master-slave group with active playback.

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

                # Start radio on master first (important for metadata)
                try:
                    await master.play_url(get_radio_url())
                    await asyncio.sleep(3.0)  # Wait for playback to start
                    await master.refresh()
                except Exception as e:
                    if verbose:
                        print(f"   ⚠️ Failed to start radio: {e}")

                # Create group and join
                await master.create_group()
                await asyncio.sleep(1.0)
                await slave.join_group(master)
                await asyncio.sleep(3.0)  # Wait for join and metadata sync
                await asyncio.gather(master.refresh(full=True), slave.refresh(full=True))

                if master.is_master and slave.is_slave:
                    return master, slave, master_name, slave_name

    return None


def get_metadata(player: Player) -> dict[str, Any]:
    """Get metadata dict from player."""
    return {
        "title": player.media_title,
        "artist": player.media_artist,
        "album": player.media_album,
        "play_state": player.play_state,
        "position": player.media_position,
        "duration": player.media_duration,
    }


def metadata_matches(m1: dict[str, Any], m2: dict[str, Any], fields: list[str] | None = None) -> tuple[bool, list[str]]:
    """Check if two metadata dicts match.

    Args:
        m1: First metadata dict
        m2: Second metadata dict
        fields: Fields to compare (default: title, artist, album, play_state)

    Returns:
        Tuple of (all_match, list_of_mismatches)
    """
    if fields is None:
        fields = ["title", "artist", "album", "play_state"]

    mismatches = []
    for field in fields:
        if m1.get(field) != m2.get(field):
            mismatches.append(f"{field}: '{m1.get(field)}' != '{m2.get(field)}'")

    return len(mismatches) == 0, mismatches


# =============================================================================
# Metadata on Join Tests
# =============================================================================


async def test_slave_gets_metadata_on_join(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Slave gets master's metadata immediately on join."""
    result = TestResult("Slave gets master metadata on join")

    # Find two devices on same subnet
    setup_pair = None
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            if are_same_subnet(players[i].host, players[j].host):
                setup_pair = (i, j)
                break
        if setup_pair:
            break

    if not setup_pair:
        result.skip("Need 2 devices on same subnet")
        return result

    master = players[setup_pair[0]]
    slave = players[setup_pair[1]]
    master_name = names[setup_pair[0]]
    slave_name = names[setup_pair[1]]

    try:
        await ensure_all_solo([master, slave], [master_name, slave_name], verbose)

        # Start playback on master BEFORE joining
        result.add_detail(f"Starting playback on {master_name}...")
        await master.play_url(get_radio_url())
        await asyncio.sleep(3.0)
        await master.refresh()

        master_meta_before = get_metadata(master)
        result.add_detail(f"Master metadata before join:")
        result.add_detail(f"   Title: {master_meta_before['title']}")
        result.add_detail(f"   Artist: {master_meta_before['artist']}")
        result.add_detail(f"   Play state: {master_meta_before['play_state']}")

        has_metadata = any([master_meta_before["title"], master_meta_before["artist"]])
        if not has_metadata:
            result.add_detail("⚠️ Master has no metadata - test may not be meaningful")

        # Create group and join slave
        result.add_detail(f"\nCreating group and joining {slave_name}...")
        await master.create_group()
        await asyncio.sleep(1.0)
        await slave.join_group(master)
        await asyncio.sleep(3.0)  # Wait for metadata propagation
        await asyncio.gather(master.refresh(), slave.refresh())

        master_meta_after = get_metadata(master)
        slave_meta = get_metadata(slave)

        result.add_detail(f"\nMaster metadata after join:")
        result.add_detail(f"   Title: {master_meta_after['title']}")
        result.add_detail(f"   Artist: {master_meta_after['artist']}")
        result.add_detail(f"   Play state: {master_meta_after['play_state']}")

        result.add_detail(f"\nSlave metadata after join:")
        result.add_detail(f"   Title: {slave_meta['title']}")
        result.add_detail(f"   Artist: {slave_meta['artist']}")
        result.add_detail(f"   Play state: {slave_meta['play_state']}")

        # Compare
        matches, mismatches = metadata_matches(master_meta_after, slave_meta)

        if matches:
            result.add_detail(f"\n✅ Slave has same metadata as master")
            result.success()
        else:
            result.add_detail(f"\n⚠️ Metadata mismatches:")
            for m in mismatches:
                result.add_detail(f"   {m}")
            # Note: Some delay in propagation is normal
            result.fail(f"Metadata mismatch: {', '.join(mismatches)}")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Metadata During Playback Tests
# =============================================================================


async def test_metadata_stays_synced(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Metadata stays synchronized during playback."""
    result = TestResult("Metadata stays synced during playback")

    setup = await setup_group_with_playback(players, names, verbose)
    if not setup:
        result.skip("Could not set up group with playback")
        return result

    master, slave, master_name, slave_name = setup

    try:
        result.add_detail("Checking metadata sync over multiple refreshes...")

        all_synced = True

        for i in range(3):
            await asyncio.sleep(2.0)
            await asyncio.gather(master.refresh(), slave.refresh())

            master_meta = get_metadata(master)
            slave_meta = get_metadata(slave)

            matches, mismatches = metadata_matches(master_meta, slave_meta)

            result.add_detail(f"\nCheck {i+1}:")
            result.add_detail(
                f"   Master: '{master_meta['title']}' by {master_meta['artist']} ({master_meta['play_state']})"
            )
            result.add_detail(
                f"   Slave:  '{slave_meta['title']}' by {slave_meta['artist']} ({slave_meta['play_state']})"
            )

            if matches:
                result.add_detail(f"   ✓ Synced")
            else:
                result.add_detail(f"   ✗ Mismatches: {mismatches}")
                all_synced = False

        if all_synced:
            result.add_detail(f"\n✅ Metadata stayed synchronized across all checks")
            result.success()
        else:
            result.fail("Metadata fell out of sync during playback")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_play_state_sync(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Play state stays synchronized."""
    result = TestResult("Play state synchronization")

    setup = await setup_group_with_playback(players, names, verbose)
    if not setup:
        result.skip("Could not set up group with playback")
        return result

    master, slave, master_name, slave_name = setup

    try:
        # Test play
        result.add_detail("Testing play state sync...")

        await master.play()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        master_state = master.play_state
        slave_state = slave.play_state

        result.add_detail(f"After play: master={master_state}, slave={slave_state}")

        play_synced = master_state == slave_state

        # Test pause
        await master.pause()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh())

        master_state = master.play_state
        slave_state = slave.play_state

        result.add_detail(f"After pause: master={master_state}, slave={slave_state}")

        pause_synced = master_state == slave_state

        if play_synced and pause_synced:
            result.add_detail(f"✅ Play state stays synchronized")
            result.success()
        else:
            result.fail(f"Play state not synced (play_sync={play_synced}, pause_sync={pause_synced})")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Virtual Master Metadata Tests
# =============================================================================


async def test_group_media_title(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.media_title delegates to master."""
    result = TestResult("group.media_title (from master)")

    setup = await setup_group_with_playback(players, names, verbose)
    if not setup:
        result.skip("Could not set up group with playback")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        await master.refresh()

        master_title = master.media_title
        group_title = group.media_title  # Should delegate to master

        result.add_detail(f"Master title: {master_title}")
        result.add_detail(f"Group title: {group_title}")

        if master_title == group_title:
            result.add_detail(f"✅ group.media_title matches master")
            result.success()
        else:
            result.fail(f"Mismatch: master='{master_title}', group='{group_title}'")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_media_artist(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.media_artist delegates to master."""
    result = TestResult("group.media_artist (from master)")

    setup = await setup_group_with_playback(players, names, verbose)
    if not setup:
        result.skip("Could not set up group with playback")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        await master.refresh()

        master_artist = master.media_artist
        group_artist = group.media_artist

        result.add_detail(f"Master artist: {master_artist}")
        result.add_detail(f"Group artist: {group_artist}")

        if master_artist == group_artist:
            result.add_detail(f"✅ group.media_artist matches master")
            result.success()
        else:
            result.fail(f"Mismatch: master='{master_artist}', group='{group_artist}'")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_media_album(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: group.media_album delegates to master."""
    result = TestResult("group.media_album (from master)")

    setup = await setup_group_with_playback(players, names, verbose)
    if not setup:
        result.skip("Could not set up group with playback")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        await master.refresh()

        master_album = master.media_album
        group_album = group.media_album

        result.add_detail(f"Master album: {master_album}")
        result.add_detail(f"Group album: {group_album}")

        if master_album == group_album:
            result.add_detail(f"✅ group.media_album matches master")
            result.success()
        else:
            result.fail(f"Mismatch: master='{master_album}', group='{group_album}'")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


async def test_group_all_metadata(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: All group metadata properties match master."""
    result = TestResult("All group metadata properties")

    setup = await setup_group_with_playback(players, names, verbose)
    if not setup:
        result.skip("Could not set up group with playback")
        return result

    master, slave, master_name, slave_name = setup

    try:
        group = master.group
        if not group:
            result.fail("No group object")
            return result

        await master.refresh()

        comparisons = [
            ("media_title", master.media_title, group.media_title),
            ("media_artist", master.media_artist, group.media_artist),
            ("media_album", master.media_album, group.media_album),
            ("play_state", master.play_state, group.play_state),
            ("media_position", master.media_position, group.media_position),
            ("media_duration", master.media_duration, group.media_duration),
        ]

        all_match = True
        for prop, master_val, group_val in comparisons:
            matches = master_val == group_val
            status = "✓" if matches else "✗"
            result.add_detail(f"   {status} {prop}: master='{master_val}' vs group='{group_val}'")
            if not matches:
                all_match = False

        if all_match:
            result.add_detail(f"\n✅ All group metadata properties match master")
            result.success()
        else:
            result.fail("Some properties don't match")

        await ensure_all_solo([master, slave], [master_name, slave_name], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Metadata Propagation Tests
# =============================================================================


async def test_master_propagates_to_slaves(players: list[Player], names: list[str], verbose: bool) -> TestResult:
    """Test: Master's metadata propagates to all slaves."""
    result = TestResult("Master propagates metadata to all slaves")

    # Need at least 3 devices on same subnet
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

        # Start playback on master
        result.add_detail(f"Starting playback on {name_m}...")
        await master.play_url(get_radio_url())
        await asyncio.sleep(3.0)

        # Create group with 2 slaves
        result.add_detail(f"Creating group: {name_m} + {name_s1} + {name_s2}...")
        await master.create_group()
        await asyncio.sleep(1.0)
        await slave1.join_group(master)
        await asyncio.sleep(2.0)
        await slave2.join_group(master)
        await asyncio.sleep(2.0)

        await asyncio.gather(master.refresh(), slave1.refresh(), slave2.refresh())

        master_meta = get_metadata(master)
        slave1_meta = get_metadata(slave1)
        slave2_meta = get_metadata(slave2)

        result.add_detail(f"\nMaster: '{master_meta['title']}' by {master_meta['artist']}")
        result.add_detail(f"Slave1: '{slave1_meta['title']}' by {slave1_meta['artist']}")
        result.add_detail(f"Slave2: '{slave2_meta['title']}' by {slave2_meta['artist']}")

        match1, _ = metadata_matches(master_meta, slave1_meta)
        match2, _ = metadata_matches(master_meta, slave2_meta)

        if match1 and match2:
            result.add_detail(f"\n✅ Both slaves have master's metadata")
            result.success()
        else:
            result.fail(f"Propagation failed (slave1_match={match1}, slave2_match={match2})")

        await ensure_all_solo([master, slave1, slave2], [name_m, name_s1, name_s2], False)

    except Exception as e:
        result.fail(f"Exception: {e}")

    return result


# =============================================================================
# Main Test Runner
# =============================================================================


async def run_all_tests(subnet: str | None, verbose: bool) -> list[TestResult]:
    """Run all group metadata tests."""
    devices = get_devices_by_subnet(subnet)

    if not devices:
        print("❌ No devices configured for this subnet")
        return []

    print(f"\n{'='*70}")
    print("Group Metadata Tests")
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
        print("\n⚠️  Need at least 2 connected devices for metadata tests")
        return []

    # Ensure all start solo
    print("\n🔧 Ensuring all devices are solo...")
    await ensure_all_solo(players, names, verbose)

    # Run tests
    results: list[TestResult] = []

    tests = [
        (
            "Metadata on Join",
            [
                test_slave_gets_metadata_on_join,
            ],
        ),
        (
            "Metadata During Playback",
            [
                test_metadata_stays_synced,
                test_play_state_sync,
            ],
        ),
        (
            "Virtual Master Metadata",
            [
                test_group_media_title,
                test_group_media_artist,
                test_group_media_album,
                test_group_all_metadata,
            ],
        ),
        (
            "Metadata Propagation",
            [
                test_master_propagates_to_slaves,
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
        description="Group metadata tests - metadata propagation and synchronization",
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
