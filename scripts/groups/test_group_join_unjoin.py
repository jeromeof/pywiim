#!/usr/bin/env python3
"""Test group join/unjoin operations with known devices.

Tests group operations:
- Join devices to form a group (first device becomes master, others join as slaves)
- Unjoin devices (slaves leave, master disbands)
- Verify state changes at each step

Usage:
    python scripts/test_group_join_unjoin.py 192.168.1.115 192.168.1.116 192.168.1.117
"""

import argparse
import asyncio
import sys
from typing import Any

# Ensure output is flushed immediately
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, "reconfigure") else None

from pywiim.client import WiiMClient
from pywiim.exceptions import WiiMError
from pywiim.player import Player


async def ensure_solo(player: Player, name: str) -> bool:
    """Ensure a player is solo, leave group if needed.

    Args:
        player: Player to check.
        name: Player name for logging.

    Returns:
        True if player is solo, False otherwise.
    """
    try:
        await player.refresh(full=True)
        if player.is_solo:
            print(f"   ✓ {name} is solo")
            return True

        # Player is in a group, try to leave
        print(f"   ⚠️  {name} is {player.role}, leaving group...")
        await player.leave_group()
        await asyncio.sleep(2.0)
        await player.refresh(full=True)

        if player.is_solo:
            print(f"   ✅ {name} left group successfully")
            return True
        else:
            print(f"   ❌ {name} failed to leave group (still {player.role})")
            return False
    except Exception as e:
        print(f"   ❌ Error ensuring {name} is solo: {e}")
        return False


async def print_group_status(players: list[Player], names: list[str]) -> None:
    """Print current group status for all players.

    Args:
        players: List of players.
        names: List of player names.
    """
    print("\n📊 Current Group Status:")
    for player, name in zip(players, names):
        await player.refresh()
        role = player.role.upper()
        if player.is_master:
            group_size = player.group.size if player.group else 1
            slave_count = len(player.group.slaves) if player.group else 0
            print(f"   {name} ({player.host}): {role} - Group size: {group_size} (1 master, {slave_count} slaves)")
        elif player.is_slave:
            master_host = player.group.master.host if player.group and player.group.master else "unknown"
            print(f"   {name} ({player.host}): {role} - Master: {master_host}")
        else:
            print(f"   {name} ({player.host}): {role}")


async def test_group_join_unjoin(device_ips: list[str]) -> dict[str, Any]:
    """Test group join/unjoin operations.

    Args:
        device_ips: List of device IP addresses to test.

    Returns:
        Dictionary with test results.
    """
    print(f"\n{'='*70}")
    print("Group Join/Unjoin Test")
    print(f"{'='*70}\n")
    print(f"Testing {len(device_ips)} device(s): {', '.join(device_ips)}\n")
    sys.stdout.flush()

    result = {
        "device_ips": device_ips,
        "device_names": [],
        "initial_states": {},
        "join_tests": {},
        "unjoin_tests": {},
        "errors": [],
    }

    clients: list[WiiMClient] = []
    players: list[Player] = []
    names: list[str] = []

    try:
        # Connect to all devices
        print("📱 Connecting to devices...")
        sys.stdout.flush()
        for ip in device_ips:
            client = WiiMClient(host=ip)
            player = Player(client)
            await player.refresh(full=True)
            device_info = await player.get_device_info()
            name = device_info.name or ip
            players.append(player)
            clients.append(client)
            names.append(name)
            result["device_names"].append(name)
            print(f"   ✓ {name} ({ip}) - {device_info.model} - Firmware: {device_info.firmware}")
        sys.stdout.flush()

        if len(players) < 2:
            print("\n⚠️  Need at least 2 devices to test group operations")
            result["errors"].append("Need at least 2 devices")
            return result

        # Step 1: Ensure all devices are solo
        print("\n🔧 Step 1: Ensuring all devices are solo...")
        sys.stdout.flush()
        all_solo = True
        for player, name in zip(players, names):
            if not await ensure_solo(player, name):
                all_solo = False
        sys.stdout.flush()

        if not all_solo:
            result["errors"].append("Failed to ensure all devices are solo")
            return result

        await print_group_status(players, names)
        sys.stdout.flush()

        # Step 2: Test joining devices (first becomes master, others join as slaves)
        print("\n🔗 Step 2: Testing group join...")
        sys.stdout.flush()

        master = players[0]
        master_name = names[0]
        slaves = players[1:]
        slave_names = names[1:]

        print(f"   Master: {master_name} ({master.host})")
        for slave, slave_name in zip(slaves, slave_names):
            print(f"   Slave: {slave_name} ({slave.host})")

        # Join each slave to the master
        join_results = {}
        for idx, (slave, slave_name) in enumerate(zip(slaves, slave_names), 1):
            try:
                print(f"\n   Joining {slave_name} to {master_name}...")
                sys.stdout.flush()

                # Check initial state
                await slave.refresh()
                initial_role = slave.role
                result["join_tests"][f"join_{idx}"] = {
                    "slave": slave_name,
                    "master": master_name,
                    "initial_role": initial_role,
                    "success": False,
                    "error": None,
                }

                # Perform join
                await slave.join_group(master)
                await asyncio.sleep(2.0)  # Wait for state to propagate

                # Verify join
                await slave.refresh(full=True)
                await master.refresh(full=True)

                if slave.is_slave and master.is_master:
                    if slave.group and slave.group.master.host == master.host:
                        print(f"   ✅ {slave_name} successfully joined {master_name}")
                        result["join_tests"][f"join_{idx}"]["success"] = True
                    else:
                        print(f"   ⚠️  {slave_name} joined but group structure incorrect")
                        result["join_tests"][f"join_{idx}"]["error"] = "Group structure incorrect"
                else:
                    print(f"   ❌ Join failed: {slave_name} is {slave.role}, {master_name} is {master.role}")
                    result["join_tests"][f"join_{idx}"][
                        "error"
                    ] = f"Roles incorrect: slave={slave.role}, master={master.role}"

                await print_group_status(players, names)
                sys.stdout.flush()

            except Exception as e:
                print(f"   ❌ Error joining {slave_name}: {e}")
                result["join_tests"][f"join_{idx}"]["error"] = str(e)
                result["errors"].append(f"Join error for {slave_name}: {e}")
                import traceback

                traceback.print_exc()

        # Step 3: Test unjoining (slaves leave, then master disbands)
        print("\n🔓 Step 3: Testing group unjoin...")
        sys.stdout.flush()

        # Unjoin slaves first (in reverse order)
        for idx, (slave, slave_name) in enumerate(reversed(list(zip(slaves, slave_names))), 1):
            try:
                print(f"\n   Unjoining {slave_name}...")
                sys.stdout.flush()

                await slave.refresh()
                initial_role = slave.role
                result["unjoin_tests"][f"unjoin_slave_{idx}"] = {
                    "player": slave_name,
                    "initial_role": initial_role,
                    "success": False,
                    "error": None,
                }

                # Perform unjoin
                await slave.leave_group()
                await asyncio.sleep(2.0)  # Wait for state to propagate

                # Verify unjoin
                await slave.refresh(full=True)
                if master.group:
                    await master.refresh(full=True)

                if slave.is_solo:
                    print(f"   ✅ {slave_name} successfully left group")
                    result["unjoin_tests"][f"unjoin_slave_{idx}"]["success"] = True
                else:
                    print(f"   ❌ Unjoin failed: {slave_name} is still {slave.role}")
                    result["unjoin_tests"][f"unjoin_slave_{idx}"]["error"] = f"Still {slave.role}"

                await print_group_status(players, names)
                sys.stdout.flush()

            except Exception as e:
                print(f"   ❌ Error unjoining {slave_name}: {e}")
                result["unjoin_tests"][f"unjoin_slave_{idx}"]["error"] = str(e)
                result["errors"].append(f"Unjoin error for {slave_name}: {e}")
                import traceback

                traceback.print_exc()

        # Finally, unjoin master (should disband any remaining group)
        try:
            print(f"\n   Unjoining master {master_name}...")
            sys.stdout.flush()

            await master.refresh()
            initial_role = master.role
            result["unjoin_tests"]["unjoin_master"] = {
                "player": master_name,
                "initial_role": initial_role,
                "success": False,
                "error": None,
            }

            # Perform unjoin
            await master.leave_group()
            await asyncio.sleep(2.0)  # Wait for state to propagate

            # Verify unjoin
            await master.refresh(full=True)

            if master.is_solo:
                print(f"   ✅ {master_name} successfully left group (disbanded)")
                result["unjoin_tests"]["unjoin_master"]["success"] = True
            else:
                print(f"   ❌ Unjoin failed: {master_name} is still {master.role}")
                result["unjoin_tests"]["unjoin_master"]["error"] = f"Still {master.role}"

            await print_group_status(players, names)
            sys.stdout.flush()

        except Exception as e:
            print(f"   ❌ Error unjoining {master_name}: {e}")
            result["unjoin_tests"]["unjoin_master"]["error"] = str(e)
            result["errors"].append(f"Unjoin error for {master_name}: {e}")
            import traceback

            traceback.print_exc()

        print("\n✅ Group join/unjoin tests completed")
        sys.stdout.flush()

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        result["errors"].append(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
    finally:
        # Cleanup: ensure all devices are solo
        print("\n🧹 Cleanup: Ensuring all devices are solo...")
        sys.stdout.flush()
        for player, name in zip(players, names):
            try:
                await ensure_solo(player, name)
            except Exception:
                pass
        sys.stdout.flush()

        # Close all clients
        for client in clients:
            await client.close()

    return result


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test group join/unjoin operations with known devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "device_ips",
        nargs="+",
        help="Device IP addresses to test (first becomes master, others join as slaves)",
    )

    args = parser.parse_args()

    if len(args.device_ips) < 2:
        print("❌ Error: Need at least 2 device IP addresses")
        print("Usage: python scripts/test_group_join_unjoin.py IP1 IP2 [IP3 ...]")
        return 1

    result = await test_group_join_unjoin(args.device_ips)

    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}\n")

    # Join test summary
    if result["join_tests"]:
        print("Join Tests:")
        for test_name, test_result in result["join_tests"].items():
            status = "✅" if test_result.get("success") else "❌"
            slave = test_result.get("slave", "unknown")
            master = test_result.get("master", "unknown")
            error = test_result.get("error")
            if error:
                print(f"  {status} {slave} → {master}: {error}")
            else:
                print(f"  {status} {slave} → {master}")

    # Unjoin test summary
    if result["unjoin_tests"]:
        print("\nUnjoin Tests:")
        for test_name, test_result in result["unjoin_tests"].items():
            status = "✅" if test_result.get("success") else "❌"
            player = test_result.get("player", "unknown")
            error = test_result.get("error")
            if error:
                print(f"  {status} {player}: {error}")
            else:
                print(f"  {status} {player}")

    # Errors
    if result["errors"]:
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  ❌ {error}")

    # Overall status
    all_joins_success = all(t.get("success", False) for t in result["join_tests"].values())
    all_unjoins_success = all(t.get("success", False) for t in result["unjoin_tests"].values())
    no_errors = len(result["errors"]) == 0

    if all_joins_success and all_unjoins_success and no_errors:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed or had errors")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
