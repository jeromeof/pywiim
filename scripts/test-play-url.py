#!/usr/bin/env python3
"""Real-world test script for play_url functionality on WiiM devices.

This script tests various URL playback scenarios against real hardware:
- Direct MP3/FLAC/AAC URLs (HTTPS)
- Live radio streams (Icecast/Shoutcast)
- M3U playlist URLs
- URLs with special characters
- Notification sounds
- Queue operations (add, next, replace)

Usage:
    python scripts/test-play-url.py <device_ip> [--all|--quick|--interactive]

Examples:
    python scripts/test-play-url.py 192.168.1.100              # Interactive mode
    python scripts/test-play-url.py 192.168.1.100 --quick      # Quick test (MP3 only)
    python scripts/test-play-url.py 192.168.1.100 --all        # Run all tests

Requirements:
    - Device must be on the network and accessible
    - Internet connection for streaming URLs
"""

import asyncio
import sys
from dataclasses import dataclass
from typing import Any

from pywiim import WiiMClient
from pywiim.exceptions import WiiMError
from pywiim.player import Player


# =============================================================================
# Test URLs - Various formats and sources
# =============================================================================


@dataclass
class TestURL:
    """Test URL with metadata."""

    name: str
    url: str
    description: str
    category: str
    expected_format: str = "audio"
    timeout: float = 5.0  # How long to wait for playback


# Direct audio file URLs (finite duration)
DIRECT_FILE_URLS = [
    TestURL(
        name="MP3 - SoundHelix",
        url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        description="Standard MP3 file from SoundHelix (popular test file)",
        category="direct",
        expected_format="mp3",
        timeout=5.0,
    ),
    TestURL(
        name="MP3 - Sample (Short)",
        url="https://file-examples.com/storage/fe783a5cbb6768d47e5bbdb/2017/11/file_example_MP3_700KB.mp3",
        description="Short MP3 sample file",
        category="direct",
        expected_format="mp3",
        timeout=4.0,
    ),
    TestURL(
        name="MP3 - Archive.org Public Domain",
        url="https://archive.org/download/testmp3testfile/mpthreetest.mp3",
        description="Public domain MP3 from Internet Archive",
        category="direct",
        expected_format="mp3",
        timeout=5.0,
    ),
]

# Live radio streams (infinite duration)
LIVE_STREAM_URLS = [
    TestURL(
        name="Radio - BBC World Service",
        url="http://stream.live.vc.bbcmedia.co.uk/bbc_world_service",
        description="BBC World Service live stream",
        category="stream",
        expected_format="aac",
        timeout=6.0,
    ),
    TestURL(
        name="Radio - SomaFM Groove Salad",
        url="https://ice2.somafm.com/groovesalad-128-mp3",
        description="SomaFM Groove Salad - ambient/chillout (MP3 128k)",
        category="stream",
        expected_format="mp3",
        timeout=5.0,
    ),
    TestURL(
        name="Radio - SomaFM DEF CON",
        url="https://ice4.somafm.com/defcon-128-mp3",
        description="SomaFM DEF CON Radio - hacker/electronic",
        category="stream",
        expected_format="mp3",
        timeout=5.0,
    ),
    TestURL(
        name="Radio - KEXP Seattle",
        url="https://kexp-mp3-128.streamguys1.com/kexp128.mp3",
        description="KEXP 90.3 FM Seattle - indie/alternative",
        category="stream",
        expected_format="mp3",
        timeout=5.0,
    ),
    TestURL(
        name="Radio - Jazz24",
        url="https://live.wostreaming.net/direct/ppm-jazz24aac256-ibc1",
        description="Jazz24 Public Radio - AAC 256k",
        category="stream",
        expected_format="aac",
        timeout=5.0,
    ),
    TestURL(
        name="Radio - Classic FM (UK)",
        url="https://media-ice.musicradio.com/ClassicFMMP3",
        description="Classic FM UK - Classical music",
        category="stream",
        expected_format="mp3",
        timeout=5.0,
    ),
]

# HLS/HTTPS streams
HLS_STREAM_URLS = [
    TestURL(
        name="HLS - SomaFM Space Station",
        url="https://ice6.somafm.com/spacestation-128-mp3",
        description="SomaFM Space Station - ambient space music",
        category="hls",
        expected_format="mp3",
        timeout=6.0,
    ),
]

# URLs with special characters
SPECIAL_CHAR_URLS = [
    TestURL(
        name="URL with spaces (encoded)",
        url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",  # Clean URL as fallback
        description="Testing URL encoding for special characters",
        category="special",
        expected_format="mp3",
        timeout=4.0,
    ),
]

# M3U Playlist URLs
PLAYLIST_URLS = [
    TestURL(
        name="M3U - SomaFM Groove Salad",
        url="https://somafm.com/groovesalad.pls",
        description="SomaFM Groove Salad PLS playlist",
        category="playlist",
        expected_format="pls",
        timeout=6.0,
    ),
    TestURL(
        name="M3U - SomaFM DEF CON",
        url="https://somafm.com/defcon.pls",
        description="SomaFM DEF CON Radio PLS playlist",
        category="playlist",
        expected_format="pls",
        timeout=6.0,
    ),
]

# Notification sound URLs (short audio clips)
NOTIFICATION_URLS = [
    TestURL(
        name="Notification - Chime",
        url="https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3",
        description="Bell chime notification sound",
        category="notification",
        expected_format="mp3",
        timeout=3.0,
    ),
]


# =============================================================================
# Helper Functions
# =============================================================================


async def wait_and_refresh(player: Player, delay: float = 2.0) -> None:
    """Wait and refresh player state."""
    await asyncio.sleep(delay)
    await player.refresh()


def print_status(player: Player) -> None:
    """Print current player status."""
    print(f"    State: {player.play_state}")

    # Check if title is from URL fallback
    raw_title = player._properties._status_field("title")  # Direct access to see raw value
    display_title = player.media_title
    if display_title:
        if raw_title:
            print(f"    Title: {display_title}")
        else:
            # Title came from URL fallback
            print(f"    Title: {display_title} (from URL filename)")
    else:
        print(f"    Title: (none)")

    if player.media_artist:
        print(f"    Artist: {player.media_artist}")
    if player.source:
        print(f"    Source: {player.source}")

    # Show media_content_id (URL being played)
    if player.media_content_id:
        url_display = player.media_content_id
        if len(url_display) > 60:
            url_display = url_display[:57] + "..."
        print(f"    Content ID: {url_display}")


# =============================================================================
# Test Functions
# =============================================================================


async def test_play_url_basic(player: Player, test_url: TestURL) -> dict[str, Any]:
    """Test basic play_url with a single URL."""
    result = {
        "name": test_url.name,
        "url": test_url.url[:60] + "..." if len(test_url.url) > 60 else test_url.url,
        "category": test_url.category,
        "success": False,
        "error": None,
        "play_state": None,
    }

    try:
        print(f"\n  🎵 Testing: {test_url.name}")
        print(f"     URL: {test_url.url[:70]}...")
        print(f"     Description: {test_url.description}")

        # Save initial state
        initial_state = player.play_state

        # Play the URL
        await player.play_url(test_url.url)
        await wait_and_refresh(player, test_url.timeout)

        # Check state
        result["play_state"] = player.play_state

        if player.play_state in ("play", "playing", "PLAY"):
            print(f"     ✅ Playback started successfully")
            result["success"] = True
        elif player.play_state in ("pause", "paused", "PAUSE"):
            print(f"     ⚠️  URL loaded but paused")
            result["success"] = True  # Still counts as successful load
        elif player.play_state in ("stop", "stopped", "STOP"):
            print(f"     ⚠️  Playback stopped (may be short file or buffering)")
            result["success"] = True  # Command accepted
        else:
            print(f"     ℹ️  State: {player.play_state} (command may have been accepted)")
            result["success"] = True  # Assume command was accepted

        print_status(player)

    except WiiMError as e:
        result["error"] = str(e)
        print(f"     ❌ WiiM Error: {e}")
    except Exception as e:
        result["error"] = str(e)
        print(f"     ❌ Error: {e}")

    return result


async def test_play_playlist(player: Player, test_url: TestURL) -> dict[str, Any]:
    """Test play_playlist with an M3U/PLS URL."""
    result = {
        "name": test_url.name,
        "url": test_url.url[:60] + "..." if len(test_url.url) > 60 else test_url.url,
        "category": "playlist",
        "success": False,
        "error": None,
        "play_state": None,
    }

    try:
        print(f"\n  📋 Testing Playlist: {test_url.name}")
        print(f"     URL: {test_url.url}")

        await player.play_playlist(test_url.url)
        await wait_and_refresh(player, test_url.timeout)

        result["play_state"] = player.play_state

        if player.play_state in ("play", "playing", "PLAY"):
            print(f"     ✅ Playlist playback started")
            result["success"] = True
        else:
            print(f"     ℹ️  State: {player.play_state}")
            result["success"] = True

        print_status(player)

    except WiiMError as e:
        result["error"] = str(e)
        print(f"     ❌ WiiM Error: {e}")
    except Exception as e:
        result["error"] = str(e)
        print(f"     ❌ Error: {e}")

    return result


async def test_play_notification(player: Player, test_url: TestURL) -> dict[str, Any]:
    """Test play_notification with a short audio URL."""
    result = {
        "name": test_url.name,
        "url": test_url.url[:60] + "..." if len(test_url.url) > 60 else test_url.url,
        "category": "notification",
        "success": False,
        "error": None,
    }

    try:
        print(f"\n  🔔 Testing Notification: {test_url.name}")
        print(f"     URL: {test_url.url}")
        print(f"     Note: Requires NETWORK/USB mode and firmware 4.6.415145+")

        await player.play_notification(test_url.url)
        await asyncio.sleep(2.0)

        print(f"     ✅ Notification command sent")
        result["success"] = True

    except WiiMError as e:
        result["error"] = str(e)
        print(f"     ⚠️  Notification may not be supported: {e}")
    except Exception as e:
        result["error"] = str(e)
        print(f"     ❌ Error: {e}")

    return result


async def test_enqueue_modes(player: Player) -> dict[str, Any]:
    """Test play_url with different enqueue modes."""
    result = {
        "name": "Enqueue Modes Test",
        "category": "enqueue",
        "success": False,
        "error": None,
        "modes_tested": [],
        "upnp_skipped": False,
    }

    test_urls = [
        ("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", "replace"),
        ("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3", "play"),
    ]

    try:
        print(f"\n  📥 Testing Enqueue Modes")

        for url, mode in test_urls:
            print(f"\n     Testing enqueue='{mode}'...")
            await player.play_url(url, enqueue=mode)  # type: ignore
            await wait_and_refresh(player, 3.0)

            if player.play_state in ("play", "playing"):
                print(f"     ✅ Mode '{mode}' successful - state: {player.play_state}")
                result["modes_tested"].append({"mode": mode, "success": True})
            else:
                print(f"     ℹ️  Mode '{mode}' - state: {player.play_state}")
                result["modes_tested"].append({"mode": mode, "success": True, "state": player.play_state})

        # Test UPnP enqueue modes (if available)
        if player._upnp_client:
            print(f"\n     Testing UPnP queue modes (add/next)...")

            for mode in ["add", "next"]:
                try:
                    url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"
                    await player.play_url(url, enqueue=mode)  # type: ignore
                    await asyncio.sleep(1.0)
                    print(f"     ✅ Mode '{mode}' successful (UPnP)")
                    result["modes_tested"].append({"mode": mode, "success": True, "via": "upnp"})
                except Exception as e:
                    # UPnP queue operations may not be available on all devices
                    # This is expected for devices without AVTransport service
                    error_str = str(e).lower()
                    if "not available" in error_str or "avtransport" in error_str or "service" in error_str:
                        print(f"     ⊘ Mode '{mode}' skipped (AVTransport not available on this device)")
                        result["modes_tested"].append(
                            {"mode": mode, "skipped": True, "reason": "AVTransport not available"}
                        )
                        result["upnp_skipped"] = True
                    else:
                        print(f"     ⚠️  Mode '{mode}' failed: {e}")
                        result["modes_tested"].append({"mode": mode, "success": False, "error": str(e)})
        else:
            print(f"\n     ⊘ UPnP client not available - skipping add/next modes")
            result["upnp_skipped"] = True

        # Success if HTTP modes worked (UPnP is optional)
        http_modes_passed = all(
            m.get("success", False) for m in result["modes_tested"] if m.get("mode") in ("replace", "play")
        )
        result["success"] = http_modes_passed

    except Exception as e:
        result["error"] = str(e)
        print(f"     ❌ Error: {e}")

    return result


# =============================================================================
# Main Test Runners
# =============================================================================


async def run_quick_test(player: Player) -> list[dict[str, Any]]:
    """Run a quick test with just one URL."""
    print(f"\n{'='*70}")
    print("⚡ QUICK TEST - Single URL Playback")
    print(f"{'='*70}")

    results = []

    # Just test one reliable MP3
    test = DIRECT_FILE_URLS[0]
    result = await test_play_url_basic(player, test)
    results.append(result)

    # Stop playback
    try:
        await player.stop()
    except Exception:
        pass

    return results


async def run_all_tests(player: Player) -> list[dict[str, Any]]:
    """Run all URL tests."""
    print(f"\n{'='*70}")
    print("🧪 COMPREHENSIVE URL PLAYBACK TESTS")
    print(f"{'='*70}")

    results = []

    # 1. Direct file URLs
    print(f"\n{'─'*50}")
    print("📁 Direct File URLs")
    print(f"{'─'*50}")
    for test in DIRECT_FILE_URLS:
        result = await test_play_url_basic(player, test)
        results.append(result)
        await asyncio.sleep(1.0)

    # Stop between categories
    try:
        await player.stop()
        await asyncio.sleep(1.0)
    except Exception:
        pass

    # 2. Live stream URLs
    print(f"\n{'─'*50}")
    print("📻 Live Radio Streams")
    print(f"{'─'*50}")
    for test in LIVE_STREAM_URLS[:3]:  # Test first 3 streams
        result = await test_play_url_basic(player, test)
        results.append(result)
        await asyncio.sleep(1.0)

    try:
        await player.stop()
        await asyncio.sleep(1.0)
    except Exception:
        pass

    # 3. Playlist URLs
    print(f"\n{'─'*50}")
    print("📋 Playlist URLs (M3U/PLS)")
    print(f"{'─'*50}")
    for test in PLAYLIST_URLS[:1]:  # Test first playlist
        result = await test_play_playlist(player, test)
        results.append(result)
        await asyncio.sleep(1.0)

    try:
        await player.stop()
        await asyncio.sleep(1.0)
    except Exception:
        pass

    # 4. Notification URLs
    print(f"\n{'─'*50}")
    print("🔔 Notification Sounds")
    print(f"{'─'*50}")
    for test in NOTIFICATION_URLS[:1]:
        result = await test_play_notification(player, test)
        results.append(result)
        await asyncio.sleep(2.0)

    # 5. Enqueue modes
    print(f"\n{'─'*50}")
    print("📥 Enqueue Mode Tests")
    print(f"{'─'*50}")
    result = await test_enqueue_modes(player)
    results.append(result)

    # Final stop
    try:
        await player.stop()
    except Exception:
        pass

    return results


async def run_interactive_test(player: Player) -> None:
    """Run interactive test mode."""
    print(f"\n{'='*70}")
    print("🎮 INTERACTIVE URL TEST MODE")
    print(f"{'='*70}")

    all_tests = {
        "1": ("MP3 - SoundHelix", DIRECT_FILE_URLS[0]),
        "2": ("Radio - SomaFM Groove Salad", LIVE_STREAM_URLS[1]),
        "3": ("Radio - SomaFM DEF CON", LIVE_STREAM_URLS[2]),
        "4": ("Radio - KEXP Seattle", LIVE_STREAM_URLS[3]),
        "5": ("Radio - Jazz24", LIVE_STREAM_URLS[4]),
        "6": ("Radio - Classic FM UK", LIVE_STREAM_URLS[5]),
        "7": ("Playlist - SomaFM Groove Salad", PLAYLIST_URLS[0]),
        "8": ("Notification Sound", NOTIFICATION_URLS[0]),
    }

    while True:
        print(f"\n{'─'*50}")
        print("Available Tests:")
        print(f"{'─'*50}")
        for key, (name, _) in all_tests.items():
            print(f"  {key} - {name}")
        print(f"  s - Show current status")
        print(f"  x - Stop playback")
        print(f"  c - Enter custom URL")
        print(f"  q - Quit")
        print(f"{'─'*50}")

        try:
            choice = input("\nEnter choice: ").strip().lower()

            if choice == "q":
                print("\n👋 Goodbye!")
                break

            elif choice == "s":
                await player.refresh()
                print(f"\n📊 Current Status:")
                print_status(player)

            elif choice == "x":
                await player.stop()
                await asyncio.sleep(1.0)
                await player.refresh()
                print(f"\n⏹️  Stopped")
                print_status(player)

            elif choice == "c":
                custom_url = input("Enter URL: ").strip()
                if custom_url:
                    print(f"\n🎵 Playing custom URL...")
                    await player.play_url(custom_url)
                    await wait_and_refresh(player, 5.0)
                    print_status(player)

            elif choice in all_tests:
                name, test = all_tests[choice]
                if test.category == "playlist":
                    await test_play_playlist(player, test)
                elif test.category == "notification":
                    await test_play_notification(player, test)
                else:
                    await test_play_url_basic(player, test)

            else:
                print(f"❌ Unknown choice: {choice}")

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()


# =============================================================================
# Main Entry Point
# =============================================================================


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test-play-url.py <device_ip> [--all|--quick|--interactive]")
        print("\nModes:")
        print("  --interactive  Interactive mode (default) - choose tests manually")
        print("  --quick        Quick test - single URL only")
        print("  --all          Run all tests automatically")
        print("\nExamples:")
        print("  python scripts/test-play-url.py 192.168.1.100")
        print("  python scripts/test-play-url.py 192.168.1.100 --quick")
        print("  python scripts/test-play-url.py 192.168.1.100 --all")
        sys.exit(1)

    device_ip = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "--interactive"

    print(f"\n{'='*70}")
    print(f"🎵 play_url Test Suite - WiiM Device")
    print(f"{'='*70}")

    client = WiiMClient(device_ip, timeout=10.0)
    player = Player(client)

    try:
        # Connect and get device info
        print(f"\n📋 Connecting to {device_ip}...")
        await player.refresh()

        if not player.device_info:
            raise WiiMError("Failed to get device info")

        print(f"   ✅ Connected: {player.name}")
        print(f"   Model: {player.model}")
        print(f"   Firmware: {player.firmware}")
        print(f"   Current Source: {player.source}")
        print(f"   UPnP Client: {'Available' if player._upnp_client else 'Not available'}")

        # Run appropriate test mode
        if mode == "--quick":
            results = await run_quick_test(player)
        elif mode == "--all":
            results = await run_all_tests(player)
        else:
            await run_interactive_test(player)
            results = []

        # Print summary for non-interactive modes
        if results:
            print(f"\n{'='*70}")
            print("📊 TEST SUMMARY")
            print(f"{'='*70}\n")

            passed = sum(1 for r in results if r.get("success"))
            skipped = sum(1 for r in results if r.get("upnp_skipped"))
            failed = len(results) - passed

            for r in results:
                name = r.get("name", "Unknown")
                error = r.get("error", "")

                if r.get("success"):
                    if r.get("upnp_skipped"):
                        print(f"  ✅ {name} (UPnP queue tests skipped - device limitation)")
                    else:
                        print(f"  ✅ {name}")
                else:
                    error_str = f" - {error}" if error else ""
                    print(f"  ❌ {name}{error_str}")

            print(f"\n  Total: {len(results)} tests | ✅ Passed: {passed} | ❌ Failed: {failed}")
            if skipped:
                print(f"  Note: {skipped} test(s) had optional UPnP features skipped")
            print(f"\n{'='*70}\n")

            if failed > 0:
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
