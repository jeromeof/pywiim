#!/usr/bin/env python3
"""Test script to verify optimistic group notifications.

This script demonstrates that when a slave joins a group, BOTH the slave
and the master receive immediate state change notifications without waiting
for polling or device confirmation.

Usage:
    python scripts/test-optimistic-group-notification.py <master_ip> <slave_ip>

Example:
    python scripts/test-optimistic-group-notification.py 192.168.1.100 192.168.1.101
"""

import asyncio
import sys
from datetime import datetime

from pywiim import WiiMClient
from pywiim.player import Player


class NotificationTracker:
    """Track state change notifications for a player."""

    def __init__(self, player_name: str):
        self.player_name = player_name
        self.notifications = []

    def callback(self):
        """Callback to record when notifications occur."""
        timestamp = datetime.now()
        role = "UNKNOWN"
        if hasattr(self, "player"):
            role = self.player.role

        self.notifications.append(
            {
                "timestamp": timestamp,
                "role": role,
            }
        )
        print(f"  [{timestamp.strftime('%H:%M:%S.%f')[:-3]}] 🔔 {self.player_name} notified (role={role})")


async def test_optimistic_notifications(master_ip: str, slave_ip: str):
    """Test that both master and slave get notified immediately on join."""

    print("\n" + "=" * 70)
    print("Testing Optimistic Group Notifications")
    print("=" * 70)

    # Create clients
    master_client = WiiMClient(master_ip)
    slave_client = WiiMClient(slave_ip)

    # Create notification trackers
    master_tracker = NotificationTracker("MASTER")
    slave_tracker = NotificationTracker("SLAVE")

    # Create players with callbacks
    master = Player(master_client, on_state_changed=master_tracker.callback)
    slave = Player(slave_client, on_state_changed=slave_tracker.callback)

    # Store player references for role tracking
    master_tracker.player = master
    slave_tracker.player = slave

    try:
        print("\n📋 Step 1: Initial state (ensure both devices are solo)")
        print("-" * 70)

        # Ensure devices are solo
        await master.refresh()
        await slave.refresh()

        if master.is_master:
            print("  ℹ️  Master is already master, disbanding...")
            await master.leave_group()
            await asyncio.sleep(1)
            await master.refresh()

        if slave.is_slave:
            print("  ℹ️  Slave is already in group, leaving...")
            await slave.leave_group()
            await asyncio.sleep(1)
            await slave.refresh()

        print(f"  ✓ Master ({master_ip}): {master.role}")
        print(f"  ✓ Slave ({slave_ip}): {slave.role}")

        # Clear any notifications from setup
        master_tracker.notifications.clear()
        slave_tracker.notifications.clear()

        print("\n📋 Step 2: Create group on master")
        print("-" * 70)
        start_time = datetime.now()
        print(f"  ⏱️  Starting at {start_time.strftime('%H:%M:%S.%f')[:-3]}")

        await master.create_group()

        print("  ✓ Group created")
        print(f"  ✓ Master role: {master.role}")
        print(f"  ✓ Master has group object: {master.group is not None}")

        # Clear notifications from group creation
        master_tracker.notifications.clear()
        slave_tracker.notifications.clear()

        print("\n📋 Step 3: Have slave join group (watch for notifications)")
        print("-" * 70)
        join_start = datetime.now()
        print(f"  ⏱️  Starting join at {join_start.strftime('%H:%M:%S.%f')[:-3]}")
        print("  📡 Calling slave.join_group(master)...")

        # This is the critical operation - watch for notifications
        await slave.join_group(master)

        join_end = datetime.now()
        print(f"  ⏱️  Join completed at {join_end.strftime('%H:%M:%S.%f')[:-3]}")
        join_duration = (join_end - join_start).total_seconds()
        print(f"  ⏱️  Total duration: {join_duration:.3f}s")

        print("\n📊 Results:")
        print("-" * 70)

        # Check immediate state (no refresh)
        print("\n  📍 Immediate state (no refresh/polling):")
        print(f"     Master role: {master.role}")
        print(f"     Slave role: {slave.role}")
        print(f"     Master group size: {master.group.size if master.group else 0}")
        print(f"     Slave in master's group: {slave in (master.group.slaves if master.group else [])}")

        # Notification analysis
        print("\n  🔔 Notifications received:")
        print(f"     Master notifications: {len(master_tracker.notifications)}")
        print(f"     Slave notifications: {len(slave_tracker.notifications)}")

        if master_tracker.notifications:
            for i, notif in enumerate(master_tracker.notifications, 1):
                delta_ms = (notif["timestamp"] - join_start).total_seconds() * 1000
                print(f"       #{i}: +{delta_ms:.1f}ms (role={notif['role']})")

        if slave_tracker.notifications:
            for i, notif in enumerate(slave_tracker.notifications, 1):
                delta_ms = (notif["timestamp"] - join_start).total_seconds() * 1000
                print(f"       #{i}: +{delta_ms:.1f}ms (role={notif['role']})")

        # Verification
        print("\n  ✅ Verification:")
        master_notified = len(master_tracker.notifications) > 0
        slave_notified = len(slave_tracker.notifications) > 0
        master_correct_role = master.role == "master"
        slave_correct_role = slave.role == "slave"
        slave_in_group = slave in (master.group.slaves if master.group else [])

        print(f"     {'✓' if master_notified else '✗'} Master received notification: {master_notified}")
        print(f"     {'✓' if slave_notified else '✗'} Slave received notification: {slave_notified}")
        print(f"     {'✓' if master_correct_role else '✗'} Master role is 'master': {master_correct_role}")
        print(f"     {'✓' if slave_correct_role else '✗'} Slave role is 'slave': {slave_correct_role}")
        print(f"     {'✓' if slave_in_group else '✗'} Slave in master's group: {slave_in_group}")

        all_passed = all(
            [
                master_notified,
                slave_notified,
                master_correct_role,
                slave_correct_role,
                slave_in_group,
            ]
        )

        if all_passed:
            print("\n  🎉 SUCCESS! Both master and slave were notified optimistically!")
            print("     No polling or refresh required - state updates were immediate.")
        else:
            print("\n  ❌ FAILED! Some verifications did not pass.")

        # Optional: verify device state matches library state
        print("\n📋 Step 4: Verify device state (optional)")
        print("-" * 70)
        print("  ℹ️  Refreshing from devices to verify...")

        await master.refresh()
        await slave.refresh()

        print(f"     Master role from device: {master.role}")
        print(f"     Slave role from device: {slave.role}")
        print(f"     Device state matches library: {master.role == 'master' and slave.role == 'slave'}")

        # Cleanup
        print("\n📋 Step 5: Cleanup")
        print("-" * 70)
        print("  🧹 Disbanding group...")
        await master.leave_group()
        print("  ✓ Cleanup complete")

        return 0 if all_passed else 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        await master_client.close()
        await slave_client.close()


async def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print(__doc__)
        return 1

    master_ip = sys.argv[1]
    slave_ip = sys.argv[2]

    return await test_optimistic_notifications(master_ip, slave_ip)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
