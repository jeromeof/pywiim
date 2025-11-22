#!/usr/bin/env python3
"""Test role detection logic with real devices.

Tests the optimized role detection that avoids expensive getDeviceInfo calls
by using fast status-based indicators (mode=99 or source=multiroom).
"""

import asyncio
import logging
import sys
from typing import Any

from pywiim import Player, WiiMClient

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

_LOGGER = logging.getLogger(__name__)


async def test_device_role_detection(host: str, expected_role: str) -> dict[str, Any]:
    """Test role detection for a single device.

    Args:
        host: Device IP address
        expected_role: Expected role ("master", "slave", or "solo")

    Returns:
        Dictionary with test results
    """
    _LOGGER.info("=" * 80)
    _LOGGER.info("Testing device: %s (expected role: %s)", host, expected_role.upper())
    _LOGGER.info("=" * 80)

    results: dict[str, Any] = {
        "host": host,
        "expected_role": expected_role,
        "detected_role": None,
        "status_indicators": {},
        "role_check_triggered": False,
        "errors": [],
    }

    try:
        client = WiiMClient(host)
        player = Player(client)

        # Initial refresh (fast path - no full refresh)
        _LOGGER.info("\n1. Initial refresh (fast path, full=False)...")
        await player.refresh(full=False)

        # Check status indicators
        status = player._status_model
        if status:
            results["status_indicators"] = {
                "mode": status.mode,
                "source": status.source,
                "group": status.group,
                "master_uuid": status.master_uuid,
                "master_ip": status.master_ip,
            }
            _LOGGER.info("   Status indicators:")
            _LOGGER.info("     - mode: %s", status.mode)
            _LOGGER.info("     - source: %s", status.source)
            _LOGGER.info("     - group: %s", status.group)
            _LOGGER.info("     - master_uuid: %s", status.master_uuid)
            _LOGGER.info("     - master_ip: %s", status.master_ip)

            # Check if indicators suggest slave
            is_multiroom_mode = str(status.mode) == "99"
            is_multiroom_source = status.source and str(status.source).lower() == "multiroom"
            is_potential_slave = is_multiroom_mode or is_multiroom_source

            _LOGGER.info("\n   Slave indicators:")
            _LOGGER.info("     - mode == '99': %s", is_multiroom_mode)
            _LOGGER.info("     - source == 'multiroom': %s", is_multiroom_source)
            _LOGGER.info("     - potential_slave: %s", is_potential_slave)

        # Check detected role
        detected_role = player.role
        results["detected_role"] = detected_role
        _LOGGER.info("\n   Detected role: %s", detected_role.upper())

        # Check if device_info was fetched (should only happen if indicators triggered)
        has_device_info = player._device_info is not None
        _LOGGER.info("   Device info cached: %s", has_device_info)

        # Check if role check was triggered
        # (This is determined by whether we have device_info or group object)
        has_group = player._group is not None
        results["role_check_triggered"] = is_potential_slave or has_group or has_device_info
        _LOGGER.info("   Role check triggered: %s", results["role_check_triggered"])
        if results["role_check_triggered"]:
            reasons = []
            if is_potential_slave:
                reasons.append("potential slave indicators")
            if has_group:
                reasons.append("group object exists")
            if has_device_info:
                reasons.append("device info cached")
            _LOGGER.info("     Reasons: %s", ", ".join(reasons))

        # Verify role matches expected
        if detected_role == expected_role:
            _LOGGER.info("\n   ✓ Role detection CORRECT: %s", detected_role.upper())
        else:
            error_msg = f"Role mismatch: expected {expected_role.upper()}, got {detected_role.upper()}"
            results["errors"].append(error_msg)
            _LOGGER.error("\n   ✗ Role detection FAILED: %s", error_msg)

        # Full refresh to verify master detection
        if expected_role == "master":
            _LOGGER.info("\n2. Full refresh (full=True) to verify master detection...")
            await player.refresh(full=True)

            detected_role_after_full = player.role
            _LOGGER.info("   Detected role after full refresh: %s", detected_role_after_full.upper())

            if detected_role_after_full == "master":
                _LOGGER.info("   ✓ Master detection CORRECT after full refresh")
            else:
                error_msg = f"Master not detected after full refresh: got {detected_role_after_full.upper()}"
                results["errors"].append(error_msg)
                _LOGGER.error("   ✗ Master detection FAILED: %s", error_msg)

            # Check slave list
            if player._group and player._group.slaves:
                _LOGGER.info("   Slaves in group: %s", [s.host for s in player._group.slaves])
            else:
                _LOGGER.warning("   No slaves found in group object")

        # Get group info directly to verify
        _LOGGER.info("\n3. Direct get_device_group_info() call...")
        group_info = await client.get_device_group_info()
        _LOGGER.info("   Role from get_device_group_info(): %s", group_info.role.upper())
        _LOGGER.info("   Master host: %s", group_info.master_host)
        _LOGGER.info("   Slave hosts: %s", group_info.slave_hosts)
        _LOGGER.info("   Slave count: %s", group_info.slave_count)

        # Note: get_device_group_info() may return SOLO for slaves that don't have master info
        # This is expected behavior - slaves often don't know who their master is
        # Our role detection logic overrides this based on fast indicators (mode=99 or source=multiroom)
        if group_info.role == expected_role:
            _LOGGER.info("   ✓ Direct role check CORRECT")
        elif expected_role == "slave" and group_info.role == "solo":
            _LOGGER.info(
                "   ⚠ Direct role check returned SOLO (expected for slaves without master info) - "
                "our logic correctly overrides this to SLAVE based on fast indicators"
            )
        else:
            error_msg = f"Direct role check mismatch: expected {expected_role.upper()}, got {group_info.role.upper()}"
            results["errors"].append(error_msg)
            _LOGGER.error("   ✗ Direct role check FAILED: %s", error_msg)

        await client.close()

    except Exception as e:
        error_msg = f"Error testing device {host}: {e}"
        results["errors"].append(error_msg)
        _LOGGER.exception(error_msg)

    return results


async def test_coordination(slave_ip: str, master_ip: str) -> dict[str, Any]:
    """Test coordination: when slave is detected, trigger master detection on all players.

    This simulates what a coordinator (like Home Assistant) would do:
    1. Create players for all known devices
    2. When a slave is detected, check all other players to find the master
    3. Verify master is correctly detected
    """
    _LOGGER.info("\n" + "=" * 80)
    _LOGGER.info("TESTING COORDINATION: Slave Detection → Master Detection")
    _LOGGER.info("=" * 80)

    results: dict[str, Any] = {
        "slave_detected": False,
        "master_detected": False,
        "errors": [],
    }

    # Create players for both devices
    slave_client = WiiMClient(slave_ip)
    master_client = WiiMClient(master_ip)

    # Registry to simulate coordinator's player registry
    player_registry: dict[str, Player] = {}

    def player_finder(host: str) -> Player | None:
        """Find player by host (simulates coordinator's player registry)."""
        return player_registry.get(host)

    slave_player = Player(slave_client, player_finder=player_finder)
    master_player = Player(master_client, player_finder=player_finder)

    player_registry[slave_ip] = slave_player
    player_registry[master_ip] = master_player

    try:
        # Step 1: Refresh slave device (fast path)
        _LOGGER.info("\n1. Refreshing slave device (%s) - should detect as SLAVE...", slave_ip)
        await slave_player.refresh(full=False)

        slave_role = slave_player.role
        _LOGGER.info("   Slave role after refresh: %s", slave_role.upper())

        if slave_role == "slave":
            results["slave_detected"] = True
            _LOGGER.info("   ✓ Slave correctly detected")
        else:
            error_msg = f"Slave not detected: got {slave_role.upper()}, expected SLAVE"
            results["errors"].append(error_msg)
            _LOGGER.error("   ✗ %s", error_msg)
            return results

        # Step 2: When slave is detected, coordinator should check all other players
        _LOGGER.info("\n2. Slave detected! Coordinator should now check all other players...")
        _LOGGER.info("   Checking master device (%s) for master role...", master_ip)

        # Coordinator would call get_device_group_info() on all other players
        # to find which one is the master
        master_group_info = await master_client.get_device_group_info()
        _LOGGER.info("   Master group info role: %s", master_group_info.role.upper())
        _LOGGER.info("   Master group info slave hosts: %s", master_group_info.slave_hosts)

        if master_group_info.role == "master":
            results["master_detected"] = True
            _LOGGER.info("   ✓ Master correctly detected via get_device_group_info()")

            # Now refresh the master player to update its role
            _LOGGER.info("\n3. Refreshing master device to update its role...")
            await master_player.refresh(full=True)  # Full refresh to get device_info

            master_role = master_player.role
            _LOGGER.info("   Master role after refresh: %s", master_role.upper())

            if master_role == "master":
                _LOGGER.info("   ✓ Master role correctly set in player object")
            else:
                error_msg = f"Master role not set correctly: got {master_role.upper()}, expected MASTER"
                results["errors"].append(error_msg)
                _LOGGER.error("   ✗ %s", error_msg)
        else:
            error_msg = f"Master not detected: got {master_group_info.role.upper()}, expected MASTER"
            results["errors"].append(error_msg)
            _LOGGER.error("   ✗ %s", error_msg)

        # Step 3: Verify group linking
        _LOGGER.info("\n4. Verifying group linking...")
        if master_player._group and slave_player in master_player._group.slaves:
            _LOGGER.info("   ✓ Slave correctly linked to master's group")
        else:
            _LOGGER.warning("   ⚠ Slave not linked to master's group (player_finder may need to link)")

    except Exception as e:
        error_msg = f"Error in coordination test: {e}"
        results["errors"].append(error_msg)
        _LOGGER.exception(error_msg)
    finally:
        await slave_client.close()
        await master_client.close()

    return results


async def main() -> None:
    """Main test function."""
    if len(sys.argv) < 3:
        print("Usage: test_role_detection.py <slave_ip> <master_ip>")
        print("Example: test_role_detection.py 192.168.1.115 192.168.1.116")
        sys.exit(1)

    slave_ip = sys.argv[1]
    master_ip = sys.argv[2]

    _LOGGER.info("Testing Role Detection Logic")
    _LOGGER.info("=" * 80)
    _LOGGER.info("Slave device: %s", slave_ip)
    _LOGGER.info("Master device: %s", master_ip)
    _LOGGER.info("=" * 80)

    # Test individual device role detection
    slave_results = await test_device_role_detection(slave_ip, "slave")
    master_results = await test_device_role_detection(master_ip, "master")

    # Test coordination (slave detection → master detection)
    coordination_results = await test_coordination(slave_ip, master_ip)

    # Summary
    _LOGGER.info("\n" + "=" * 80)
    _LOGGER.info("TEST SUMMARY")
    _LOGGER.info("=" * 80)

    all_errors = []
    for results in [slave_results, master_results]:
        host = results["host"]
        expected = results["expected_role"]
        detected = results["detected_role"]
        errors = results["errors"]

        _LOGGER.info("\n%s (%s):", host, expected.upper())
        _LOGGER.info("  Detected role: %s", detected.upper() if detected else "None")
        _LOGGER.info("  Status indicators:")
        for key, value in results.get("status_indicators", {}).items():
            _LOGGER.info("    - %s: %s", key, value)
        _LOGGER.info("  Role check triggered: %s", results.get("role_check_triggered", False))

        if errors:
            _LOGGER.error("  ERRORS:")
            for error in errors:
                _LOGGER.error("    - %s", error)
            all_errors.extend(errors)
        else:
            _LOGGER.info("  ✓ No errors")

    # Coordination test results
    _LOGGER.info("\nCoordination Test:")
    _LOGGER.info("  - Slave detected: %s", coordination_results.get("slave_detected", False))
    _LOGGER.info("  - Master detected: %s", coordination_results.get("master_detected", False))
    if coordination_results.get("errors"):
        _LOGGER.error("  ERRORS:")
        for error in coordination_results["errors"]:
            _LOGGER.error("    - %s", error)
        all_errors.extend(coordination_results["errors"])
    else:
        _LOGGER.info("  ✓ No errors")

    if all_errors:
        _LOGGER.error("\n✗ TEST FAILED: %d error(s) found", len(all_errors))
        sys.exit(1)
    else:
        _LOGGER.info("\n✓ ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
