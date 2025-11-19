#!/usr/bin/env python3
"""Interactive test script for manually testing play/pause/shuffle/repeat controls.

This script provides an interactive menu for manually testing playback controls
on real WiiM devices.

Usage:
    python scripts/interactive-playback-test.py <device_ip>

Example:
    python scripts/interactive-playback-test.py 192.168.1.100
"""

import asyncio
import sys

from pywiim import WiiMClient
from pywiim.player import Player
from pywiim.exceptions import WiiMError


def print_menu():
    """Print the interactive menu."""
    print("\n" + "=" * 60)
    print("🎵 Interactive Playback Control Test")
    print("=" * 60)
    print("\nCommands:")
    print("  1 - Play")
    print("  2 - Pause")
    print("  3 - Resume")
    print("  4 - Stop")
    print("  5 - Next Track")
    print("  6 - Previous Track")
    print("  s - Show Current Status")
    print("  h+ - Shuffle ON")
    print("  h- - Shuffle OFF")
    print("  r0 - Repeat OFF")
    print("  r1 - Repeat ONE")
    print("  ra - Repeat ALL")
    print("  q - Quit")
    print("=" * 60)


async def show_status(player: Player):
    """Display current player status."""
    await player.refresh()

    print("\n" + "─" * 60)
    print("📊 Current Status:")
    print("─" * 60)
    print(f"  Device: {player.name}")
    print(f"  State: {player.play_state}")
    print(f"  Volume: {player.volume_level}")
    print(f"  Muted: {player.is_muted}")
    print(f"  Source: {player.source}")
    print(f"  Shuffle: {player.shuffle_state}")
    print(f"  Repeat: {player.repeat_mode}")

    if player.media_title:
        print(f"\n  Now Playing:")
        print(f"    Title: {player.media_title}")
        if player.media_artist:
            print(f"    Artist: {player.media_artist}")
        if player.media_album:
            print(f"    Album: {player.media_album}")
        if player.media_duration:
            print(f"    Duration: {player.media_duration}s")
        if player.media_position:
            print(f"    Position: {player.media_position}s")

    print("─" * 60)


async def interactive_test(ip: str):
    """Run interactive test session."""
    print(f"\n🎵 Connecting to {ip}...")

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Initial connection
        await player.refresh()

        if not player.device_info:
            raise WiiMError("Failed to get device info")

        print(f"✓ Connected to: {player.name}")
        print(f"  Model: {player.model}")
        print(f"  Firmware: {player.firmware}")

        # Show initial status
        await show_status(player)

        # Interactive loop
        while True:
            print_menu()
            command = input("\nEnter command: ").strip().lower()

            try:
                if command == "q":
                    print("\n👋 Goodbye!")
                    break

                elif command == "1":
                    print("▶️  Playing...")
                    await player.play()
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "2":
                    print("⏸️  Pausing...")
                    await player.pause()
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "3":
                    print("▶️  Resuming...")
                    await player.resume()
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "4":
                    print("⏹️  Stopping...")
                    await player.stop()
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "5":
                    print("⏭️  Next track...")
                    await player.next_track()
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "6":
                    print("⏮️  Previous track...")
                    await player.previous_track()
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "s":
                    await show_status(player)

                elif command == "h+":
                    print("🔀 Enabling shuffle...")
                    await player.set_shuffle(True)
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "h-":
                    print("➡️  Disabling shuffle...")
                    await player.set_shuffle(False)
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "r0":
                    print("🔁 Setting repeat OFF...")
                    await player.set_repeat("off")
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "r1":
                    print("🔂 Setting repeat ONE...")
                    await player.set_repeat("one")
                    await asyncio.sleep(1)
                    await show_status(player)

                elif command == "ra":
                    print("🔁 Setting repeat ALL...")
                    await player.set_repeat("all")
                    await asyncio.sleep(1)
                    await show_status(player)

                else:
                    print(f"❌ Unknown command: {command}")

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback

                traceback.print_exc()

    finally:
        await client.close()


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/interactive-playback-test.py <device_ip>")
        print("\nExample:")
        print("  python scripts/interactive-playback-test.py 192.168.1.100")
        sys.exit(1)

    device_ip = sys.argv[1]
    await interactive_test(device_ip)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
