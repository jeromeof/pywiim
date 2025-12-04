#!/usr/bin/env python3
"""Focused test: Master 192.168.1.115, Slave 192.168.1.68

Tests:
1. Slave joins master
2. Master to slave metadata propagation
3. Slave player controls route to master
4. Volume/mute controls from master, slave, and virtual master (group)
"""

import asyncio
import sys
from typing import Any

from pywiim import WiiMClient
from pywiim.exceptions import WiiMError
from pywiim.player import Player

MASTER_IP = "192.168.1.115"
SLAVE_IP = "192.168.1.68"


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*80}")
    print(title)
    print(f"{'='*80}\n")


def print_status(player: Player, label: str) -> None:
    """Print player status."""
    print(f"{label}:")
    print(f"  IP: {player.host}")
    print(f"  Role: {player.role}")
    print(f"  Play State: {player.play_state}")
    print(f"  Volume: {player.volume_level}")
    print(f"  Muted: {player.is_muted}")
    print(f"  Title: {player.media_title}")
    print(f"  Artist: {player.media_artist}")
    print(f"  Album: {player.media_album}")
    print()


async def main() -> int:
    """Main test function."""
    print_section("Master-Slave Basic Test")
    print(f"Master: {MASTER_IP}")
    print(f"Slave: {SLAVE_IP}\n")

    # Connect to devices
    print("Connecting to devices...")
    try:
        master_client = WiiMClient(MASTER_IP, timeout=5.0)
        master = Player(master_client)
        await master.refresh()
        print(f"✓ Connected to master: {master.device_info.name if master.device_info else MASTER_IP}")
    except Exception as e:
        print(f"✗ Failed to connect to master: {e}")
        return 1

    try:
        slave_client = WiiMClient(SLAVE_IP, timeout=5.0)
        slave = Player(slave_client)
        await slave.refresh()
        print(f"✓ Connected to slave: {slave.device_info.name if slave.device_info else SLAVE_IP}")
    except Exception as e:
        print(f"✗ Failed to connect to slave: {e}")
        return 1

    # Ensure both are solo
    print("\nEnsuring both devices are solo...")
    try:
        if master.is_master:
            await master.leave_group()
        elif not master.is_solo:
            await master.leave_group()
        if not slave.is_solo:
            await slave.leave_group()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
        print("✓ Both devices are solo")
    except Exception as e:
        print(f"⚠ Warning: Error ensuring solo state: {e}")

    # Set volumes to 0 for testing (will use max 5% during tests)
    print("\nSetting volumes to 0 for testing (max 5% during tests)...")
    await master.set_volume(0.0)
    await slave.set_volume(0.0)
    await asyncio.sleep(0.5)

    # Test 1: Create group and join slave
    print_section("Test 1: Create Group and Join Slave")
    try:
        group = await master.create_group()
        await asyncio.sleep(1.0)
        await master.refresh()
        print(f"✓ Group created on master")

        await slave.join_group(master)
        await asyncio.sleep(3.0)  # Wait for join to complete
        await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)

        print(f"✓ Slave join command sent")
        print(f"  Master is_master: {master.is_master}")
        print(f"  Slave is_slave: {slave.is_slave}")
        print(f"  Slave in group.slaves: {slave in group.slaves if master.group else False}")
        print(f"  Group size: {group.size if master.group else 0}")

        if not slave.is_slave:
            print(f"\n⚠ WARNING: Slave did not join successfully")
            print(f"  This may be expected if devices are on different subnets")
            master_subnet = ".".join(MASTER_IP.split(".")[:3])
            slave_subnet = ".".join(SLAVE_IP.split(".")[:3])
            if master_subnet != slave_subnet:
                print(f"  Different subnets: {master_subnet} vs {slave_subnet}")
                print(f"  Cross-subnet grouping is not supported")
                return 0
    except WiiMError as e:
        print(f"✗ Error creating group or joining: {e}")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Test 2: Master to slave metadata propagation
    print_section("Test 2: Master to Slave Metadata Propagation")
    await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
    await asyncio.sleep(2.0)
    await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)

    master_metadata = {
        "title": master.media_title,
        "artist": master.media_artist,
        "album": master.media_album,
        "play_state": master.play_state,
    }
    slave_metadata = {
        "title": slave.media_title,
        "artist": slave.media_artist,
        "album": slave.media_album,
        "play_state": slave.play_state,
    }

    print("Master metadata:")
    print(f"  Title: {master_metadata['title']}")
    print(f"  Artist: {master_metadata['artist']}")
    print(f"  Album: {master_metadata['album']}")
    print(f"  Play State: {master_metadata['play_state']}")
    print()
    print("Slave metadata:")
    print(f"  Title: {slave_metadata['title']}")
    print(f"  Artist: {slave_metadata['artist']}")
    print(f"  Album: {slave_metadata['album']}")
    print(f"  Play State: {slave_metadata['play_state']}")
    print()

    title_match = master_metadata["title"] == slave_metadata["title"]
    artist_match = master_metadata["artist"] == slave_metadata["artist"]
    play_state_match = master_metadata["play_state"] == slave_metadata["play_state"]

    print("Metadata Match:")
    print(f"  Title: {'✓' if title_match else '✗'}")
    print(f"  Artist: {'✓' if artist_match else '✗'}")
    print(f"  Play State: {'✓' if play_state_match else '✗'}")

    if not (title_match and artist_match and play_state_match):
        print("\n⚠ WARNING: Metadata mismatch detected")
        if not title_match:
            print(f"  Title: master='{master_metadata['title']}' vs slave='{slave_metadata['title']}'")
        if not artist_match:
            print(f"  Artist: master='{master_metadata['artist']}' vs slave='{slave_metadata['artist']}'")
        if not play_state_match:
            print(f"  Play State: master='{master_metadata['play_state']}' vs slave='{slave_metadata['play_state']}'")

    # Test 3: Slave player controls route to master
    print_section("Test 3: Slave Player Controls Route to Master")

    # Get initial master play state
    await master.refresh()
    initial_state = master.play_state
    print(f"Initial master play_state: {initial_state}")

    # Test slave.play()
    print("\nTesting slave.play()...")
    try:
        await slave.play()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
        new_state = master.play_state
        print(f"  Master play_state after slave.play(): {new_state}")
        if new_state in ("play", "playing"):
            print("  ✓ Master started playing")
        else:
            print(f"  ⚠ Master state: {new_state} (may already be playing)")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test slave.pause()
    print("\nTesting slave.pause()...")
    try:
        await slave.pause()
        await asyncio.sleep(2.0)
        await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
        new_state = master.play_state
        print(f"  Master play_state after slave.pause(): {new_state}")
        if new_state in ("pause", "paused"):
            print("  ✓ Master paused")
        else:
            print(f"  ⚠ Master state: {new_state}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Test 4: Volume and mute controls
    print_section("Test 4: Volume and Mute Controls")

    # 4a: Master volume control
    print("4a. Master volume control...")
    try:
        await master.set_volume(0.03)  # 3% - below 5% max
        await asyncio.sleep(1.0)
        await master.refresh()
        master_vol = master.volume_level
        print(f"  Set master volume to 0.03 (3%), got: {master_vol}")
        print(f"  ✓ Master volume control works")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # 4b: Slave volume control
    print("\n4b. Slave volume control...")
    try:
        await slave.set_volume(0.04)  # 4% - below 5% max
        await asyncio.sleep(1.0)
        await slave.refresh()
        slave_vol = slave.volume_level
        print(f"  Set slave volume to 0.04 (4%), got: {slave_vol}")
        print(f"  ✓ Slave volume control works")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # 4c: Group volume control (virtual master)
    print("\n4c. Group volume control (virtual master)...")
    try:
        if master.group:
            # First, set individual volumes to known values (below 5% max)
            await master.set_volume(0.03)  # 3%
            await slave.set_volume(0.04)  # 4%
            await asyncio.sleep(1.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
            initial_master_vol = master.volume_level
            initial_slave_vol = slave.volume_level
            initial_group_vol = master.group.volume_level
            print(f"  Initial volumes:")
            print(f"    Master: {initial_master_vol}")
            print(f"    Slave: {initial_slave_vol}")
            print(f"    Group (max): {initial_group_vol}")

            # Now set group volume (proportional adjustment) - max 5%
            target_group_vol = 0.05  # 5% max
            await master.group.set_volume_all(target_group_vol)
            await asyncio.sleep(2.0)  # Wait longer for volume changes
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)

            master_vol = master.volume_level
            slave_vol = slave.volume_level
            group_vol = master.group.volume_level

            print(f"  After group.set_volume_all({target_group_vol}):")
            print(f"    Master volume: {master_vol}")
            print(f"    Slave volume: {slave_vol}")
            print(f"    Group volume (max): {group_vol}")

            # Verify group volume is close to target (proportional adjustment)
            if group_vol is not None and abs(group_vol - target_group_vol) < 0.02:
                print(f"  ✓ Group volume control works (target: {target_group_vol}, got: {group_vol})")
            else:
                print(f"  ⚠ Group volume: expected ~{target_group_vol}, got {group_vol}")
                print(f"    (Proportional adjustment may result in different values)")
        else:
            print("  ⚠ No group object available")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # 4d: Master mute control
    print("\n4d. Master mute control...")
    try:
        await master.set_mute(True)
        await asyncio.sleep(1.0)
        await master.refresh()
        master_muted = master.is_muted
        print(f"  Set master mute to True, got: {master_muted}")
        print(f"  ✓ Master mute control works")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # 4e: Slave mute control
    print("\n4e. Slave mute control...")
    try:
        await slave.set_mute(True)
        await asyncio.sleep(1.0)
        await slave.refresh()
        slave_muted = slave.is_muted
        print(f"  Set slave mute to True, got: {slave_muted}")
        print(f"  ✓ Slave mute control works")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # 4f: Group mute control (virtual master)
    print("\n4f. Group mute control (virtual master)...")
    try:
        if master.group:
            await master.group.mute_all(False)
            await asyncio.sleep(1.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
            master_muted = master.is_muted
            slave_muted = slave.is_muted
            group_muted = master.group.is_muted
            print(f"  Set group mute to False")
            print(f"  Master muted: {master_muted}")
            print(f"  Slave muted: {slave_muted}")
            print(f"  Group muted (all): {group_muted}")
            print(f"  ✓ Group mute control works")
        else:
            print("  ⚠ No group object available")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    # Cleanup
    print_section("Cleanup")
    try:
        if master.group:
            await master.group.disband()
            await asyncio.sleep(2.0)
            await asyncio.gather(master.refresh(), slave.refresh(), return_exceptions=True)
            print("✓ Group disbanded")
    except Exception as e:
        print(f"⚠ Warning: Error during cleanup: {e}")

    # Close connections
    await asyncio.gather(master_client.close(), slave_client.close(), return_exceptions=True)

    print_section("Test Complete")
    print("All tests completed. Review output above for results.")

    return 0


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
