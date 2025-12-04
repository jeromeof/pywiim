#!/usr/bin/env python3
"""Diagnostic script to isolate EQ preset reversion issue.

This script tests whether EQ presets actually persist on the device, or if
the reversion is caused by refresh() overwriting optimistic updates.

Key tests:
1. Direct API calls only (no player.refresh())
2. Multiple check intervals to identify timing of reversion
3. Compare cached state vs actual device state

Usage:
    python scripts/diagnose-eq-reversion.py <device_ip>

Example:
    python scripts/diagnose-eq-reversion.py 192.168.1.115
"""

import asyncio
import sys
import time
from datetime import datetime
from typing import Any

from pywiim import WiiMClient
from pywiim.player import Player


def timestamp() -> str:
    """Return current timestamp for logging."""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


async def get_eq_direct(client: WiiMClient) -> dict[str, Any]:
    """Get EQ state directly from device API (bypassing cache)."""
    return await client.get_eq()


async def diagnose_eq_reversion(ip: str) -> None:
    """Diagnose EQ preset reversion issue."""
    print(f"\n{'='*70}")
    print(f"🔬 EQ Reversion Diagnostic on {ip}")
    print(f"{'='*70}\n")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Initial setup
        print(f"[{timestamp()}] Connecting and getting initial state...")
        await player.refresh(full=True)

        if not player.supports_eq:
            print("   ⚠️  EQ not supported on this device")
            return

        # Get available presets
        eq_presets = await player.audio.get_eq_presets()
        if not eq_presets:
            print("   ⚠️  No EQ presets available")
            return

        print(f"   Available presets: {', '.join(eq_presets)}")

        # Get current state
        initial_preset = player.eq_preset
        print(f"   Current preset: {initial_preset}")

        # Get initial state via direct API
        initial_eq_data = await get_eq_direct(client)
        initial_api_name = initial_eq_data.get("Name") or initial_eq_data.get("name")
        print(f"   Direct API preset: {initial_api_name}")

        # Find a different preset to test with
        test_preset = None
        for preset in eq_presets:
            if preset.lower() != (initial_preset or "").lower():
                test_preset = preset
                break

        if not test_preset:
            print("   ⚠️  Only one preset available, cannot test switching")
            return

        print(f"\n   Will test with preset: '{test_preset}'")
        print(f"   (Currently: '{initial_preset}')\n")

        # =====================================================================
        # TEST 1: Set EQ and check via direct API (NO refresh)
        # =====================================================================
        print(f"{'='*70}")
        print("TEST 1: Direct API monitoring (NO player.refresh())")
        print(f"{'='*70}\n")

        print(f"[{timestamp()}] Setting EQ preset to '{test_preset}' via player.set_eq_preset()...")
        await player.set_eq_preset(test_preset)

        cached_after_set = player._status_model.eq_preset if player._status_model else None
        print(f"[{timestamp()}] Cached state after set (optimistic): '{cached_after_set}'")

        # Check device state at multiple intervals WITHOUT refresh()
        check_times = [0.5, 1, 2, 3, 5, 10, 15, 20]
        print(f"\n   Checking device state at intervals: {check_times} seconds")
        print(f"   (NOT calling player.refresh() - only direct API calls)\n")

        start_time = time.time()
        last_check = 0

        for check_at in check_times:
            wait_time = check_at - last_check
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            last_check = check_at

            # Direct API call to get actual device state
            eq_data = await get_eq_direct(client)
            api_name = eq_data.get("Name") or eq_data.get("name")

            # Check cached state (should still be the optimistic update)
            cached_now = player._status_model.eq_preset if player._status_model else None

            elapsed = time.time() - start_time

            # Determine status
            if api_name and api_name.lower() == test_preset.lower():
                status = "✅ Matches target"
            elif api_name and api_name.lower() == (initial_preset or "").lower():
                status = "❌ REVERTED to original!"
            else:
                status = f"⚠️ Different: {api_name}"

            print(f"[{timestamp()}] {elapsed:.1f}s - API: '{api_name}' | Cache: '{cached_now}' | {status}")

        print()

        # =====================================================================
        # TEST 2: Set EQ and then call refresh() - does it overwrite?
        # =====================================================================
        print(f"{'='*70}")
        print("TEST 2: Does refresh() overwrite the EQ change?")
        print(f"{'='*70}\n")

        # First, set back to initial preset
        print(f"[{timestamp()}] Resetting to initial preset '{initial_preset}'...")
        await player.set_eq_preset(initial_preset)
        await asyncio.sleep(2)

        # Now set to test preset
        print(f"[{timestamp()}] Setting EQ to '{test_preset}'...")
        await player.set_eq_preset(test_preset)

        cached_before_refresh = player._status_model.eq_preset if player._status_model else None
        print(f"[{timestamp()}] Cached before refresh: '{cached_before_refresh}'")

        # Check device state via direct API BEFORE refresh
        eq_data = await get_eq_direct(client)
        api_before_refresh = eq_data.get("Name") or eq_data.get("name")
        print(f"[{timestamp()}] Device state before refresh: '{api_before_refresh}'")

        # Now call refresh()
        print(f"\n[{timestamp()}] Calling player.refresh()...")
        await player.refresh()

        cached_after_refresh = player._status_model.eq_preset if player._status_model else None
        print(f"[{timestamp()}] Cached after refresh: '{cached_after_refresh}'")

        # Check device state via direct API AFTER refresh
        eq_data = await get_eq_direct(client)
        api_after_refresh = eq_data.get("Name") or eq_data.get("name")
        print(f"[{timestamp()}] Device state after refresh: '{api_after_refresh}'")

        # Analysis
        print(f"\n{'='*70}")
        print("ANALYSIS")
        print(f"{'='*70}\n")

        if cached_before_refresh != cached_after_refresh:
            print("⚠️  FINDING: refresh() overwrote the cached EQ preset!")
            print(f"   Before refresh: '{cached_before_refresh}'")
            print(f"   After refresh:  '{cached_after_refresh}'")
            print()
            if api_before_refresh and api_before_refresh.lower() == test_preset.lower():
                print("   Device DID accept the change, but refresh() fetched stale data")
                print("   This is a CACHING ISSUE in pywiim")
            else:
                print("   Device may not have accepted the change")
        else:
            print("✅ refresh() did NOT overwrite the cached EQ preset")
            print(f"   Cached state consistent: '{cached_after_refresh}'")

        if api_before_refresh != api_after_refresh:
            print(f"\n⚠️  Device state changed after refresh!")
            print(f"   Before: '{api_before_refresh}'")
            print(f"   After:  '{api_after_refresh}'")
        else:
            print(f"\n✅ Device state stable: '{api_after_refresh}'")

        # =====================================================================
        # TEST 3: Full monitoring with refresh()
        # =====================================================================
        print(f"\n{'='*70}")
        print("TEST 3: Monitoring with refresh() calls")
        print(f"{'='*70}\n")

        # Reset first
        await player.set_eq_preset(initial_preset)
        await asyncio.sleep(2)

        print(f"[{timestamp()}] Setting EQ to '{test_preset}'...")
        await player.set_eq_preset(test_preset)

        print(f"   Monitoring for 20 seconds with refresh() every 2 seconds...\n")

        start_time = time.time()
        for i in range(10):
            await asyncio.sleep(2)

            # Direct API check
            eq_data = await get_eq_direct(client)
            api_name = eq_data.get("Name") or eq_data.get("name")

            # Refresh and check cached
            await player.refresh()
            cached_now = player.eq_preset

            elapsed = time.time() - start_time

            # Status
            match_target = api_name and api_name.lower() == test_preset.lower()
            match_cache = api_name and cached_now and api_name.lower() == cached_now.lower()

            if match_target and match_cache:
                status = "✅ All match target"
            elif not match_target:
                status = "❌ DEVICE REVERTED"
            elif not match_cache:
                status = "⚠️ Cache mismatch"
            else:
                status = "?"

            print(f"[{timestamp()}] {elapsed:.1f}s - Device: '{api_name}' | Cache: '{cached_now}' | {status}")

        # =====================================================================
        # SUMMARY
        # =====================================================================
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}\n")

        print("This diagnostic helps identify:")
        print("1. Whether the device actually accepts and keeps EQ changes")
        print("2. Whether refresh() overwrites optimistic updates with stale data")
        print("3. The timing of any reversion (device-side vs cache-side)")
        print()
        print("If device reverts: Hardware/firmware issue with EQ persistence")
        print("If cache reverts but device keeps: pywiim caching issue")
        print("If both stay consistent: EQ is working, original issue was timing/content-related")

        # Restore original preset
        print(f"\n[{timestamp()}] Restoring original preset '{initial_preset}'...")
        await player.set_eq_preset(initial_preset)
        await asyncio.sleep(1)
        print(f"[{timestamp()}] Done!")

    except Exception as e:
        print(f"   ✗ Diagnostic failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/diagnose-eq-reversion.py <device_ip>")
        print("Example: python scripts/diagnose-eq-reversion.py 192.168.1.115")
        sys.exit(1)

    ip = sys.argv[1]
    await diagnose_eq_reversion(ip)


if __name__ == "__main__":
    asyncio.run(main())
