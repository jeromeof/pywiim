#!/usr/bin/env python3
"""Test script to verify if Spotify reports mode=0 (the "idle" source bug).

This script monitors a WiiM device while Spotify is playing to see if:
1. Device reports mode=0 during playback
2. This causes source to be set to "idle" instead of "spotify"

Usage:
    python scripts/test-spotify-mode-bug.py <device_ip>

Instructions:
1. Start playing Spotify on your WiiM device
2. Run this script
3. Watch what mode values are reported
4. Try pausing/resuming from Spotify app
5. Try changing tracks

Expected results if bug exists:
- mode="0" appears during playback
- source gets set to "idle" instead of "spotify"

Expected results if bug doesn't exist:
- mode="31" (or other valid mode) during playback
- source correctly shows "spotify"
"""

import asyncio
import sys
from datetime import datetime

from pywiim import WiiMClient


async def monitor_spotify(ip: str, duration: int = 60):
    """Monitor device state while Spotify is playing."""
    print(f"🎵 Monitoring Spotify State on {ip}")
    print(f"⏱️  Will monitor for {duration} seconds")
    print()
    print("Instructions:")
    print("1. Make sure Spotify is playing on your WiiM device")
    print("2. Try pausing/resuming from Spotify app")
    print("3. Try changing tracks")
    print()
    print("-" * 80)

    async with WiiMClient(ip) as client:
        start_time = asyncio.get_event_loop().time()
        iteration = 0
        mode_history = {}  # Track mode values we see

        while (asyncio.get_event_loop().time() - start_time) < duration:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")

            try:
                # Get raw status
                status = await client.get_player_status()

                if not status:
                    print(f"[{timestamp}] ❌ No status returned")
                    await asyncio.sleep(2)
                    continue

                # Extract key fields
                mode = status.mode
                source = status.source
                play_state = status.play_state
                title = status.title
                artist = status.artist
                vendor = getattr(status, "vendor", None)

                # Track mode values
                mode_key = f"mode={mode}"
                if mode_key not in mode_history:
                    mode_history[mode_key] = 0
                mode_history[mode_key] += 1

                # Check for the bug
                bug_detected = False
                if mode == "0" and play_state in ("play", "playing"):
                    bug_detected = True

                # Print status
                status_icon = "🚨" if bug_detected else "✓"
                print(
                    f"[{timestamp}] {status_icon} #{iteration:3d} | mode={mode:3s} | source={source:10s} | "
                    f"state={play_state:8s} | {artist} - {title}"
                )

                if bug_detected:
                    print(f"           {'':8s} ⚠️  BUG DETECTED: mode=0 while playing!")
                    print(f"           {'':8s} ⚠️  This will cause source to be set to 'idle'")

                # Extra detail if interesting
                if vendor and vendor.lower() not in (source or "").lower():
                    print(f"           {'':8s} 📝 vendor='{vendor}' (may override source)")

            except Exception as e:
                print(f"[{timestamp}] ❌ Error: {e}")

            await asyncio.sleep(2)  # Poll every 2 seconds

        print()
        print("-" * 80)
        print("📊 Summary:")
        print()
        print("Mode values observed:")
        for mode_key, count in sorted(mode_history.items()):
            print(f"  {mode_key}: {count} times")

        print()
        if "mode=0" in mode_history:
            print("🚨 BUG CONFIRMED: Device reported mode=0 during monitoring")
            print("   This would cause the 'state remains idle' bug in HA integration")
            print("   The fix in pywiim v2.1.18 prevents mode=0 from setting source='idle'")
        else:
            print("✅ Bug NOT observed: Device never reported mode=0")
            print("   Either:")
            print("   - This device doesn't have the bug")
            print("   - Spotify wasn't playing during test")
            print("   - Bug only happens in specific scenarios")


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/test-spotify-mode-bug.py <device_ip>")
        print()
        print("Example:")
        print("  python scripts/test-spotify-mode-bug.py 192.168.1.115")
        print()
        print("Make sure Spotify is playing on the device before running!")
        sys.exit(1)

    ip = sys.argv[1]

    try:
        asyncio.run(monitor_spotify(ip))
    except KeyboardInterrupt:
        print()
        print("⏹️  Monitoring stopped by user")


if __name__ == "__main__":
    main()
