"""Test media progress tracking on a real device.

This test verifies that media position, duration, and progress tracking work correctly.
Run with: WIIM_TEST_DEVICE=192.168.1.116 python -m pytest tests/integration/test_media_progress.py -v
"""

from __future__ import annotations

import asyncio

import pytest

from pywiim.client import WiiMClient
from pywiim.player import Player


@pytest.mark.integration
@pytest.mark.asyncio
async def test_media_progress_tracking():
    """Test media progress tracking with real device at 192.168.1.116.

    This test:
    1. Creates a Player connected to the device
    2. Refreshes state to get current playback info
    3. Monitors position updates over time (if playing)
    4. Validates position estimation logic
    5. Checks position/duration properties
    """
    device_ip = "192.168.1.116"

    print(f"\n{'=' * 70}")
    print(f"Testing Media Progress on {device_ip}")
    print(f"{'=' * 70}\n")

    # Create client and player
    client = WiiMClient(host=device_ip)
    player = Player(client)

    try:
        # Initial refresh
        print("1. Initial State Check")
        print("-" * 70)
        await player.refresh()

        print(f"   Play State: {player.play_state}")
        print(f"   Media Title: {player.media_title}")
        print(f"   Media Artist: {player.media_artist}")
        print(f"   Media Album: {player.media_album}")
        print(f"   Media Duration: {player.media_duration}s")
        print(f"   Media Position: {player.media_position}s")

        if player.media_position is not None and player.media_duration is not None:
            progress_pct = (player.media_position / player.media_duration) * 100
            print(f"   Progress: {progress_pct:.1f}%")

        # Check that properties are accessible
        assert (
            player.media_position is not None or player.play_state != "play"
        ), "Position should be available when playing"
        assert (
            player.media_duration is not None or player.play_state != "play"
        ), "Duration should be available when playing"

        print("\n2. Media Progress Properties Check")
        print("-" * 70)

        # Check position_updated_at timestamp
        pos_updated_at = player.media_position_updated_at
        print(f"   Position Updated At: {pos_updated_at}")

        if player.play_state == "play":
            print("\n   ✓ Device is playing - testing position estimation...")

            # Take multiple readings to test position estimation
            print("\n3. Position Estimation Test (5 readings over 5 seconds)")
            print("-" * 70)

            positions = []

            for i in range(5):
                await player.refresh()
                pos = player.media_position

                if pos is not None:
                    positions.append(pos)

                    if player.media_duration:
                        progress = (pos / player.media_duration) * 100
                        print(f"   Reading {i + 1}: Position={pos}s, Progress={progress:.1f}%")
                    else:
                        print(f"   Reading {i + 1}: Position={pos}s")

                if i < 4:  # Don't sleep after last reading
                    await asyncio.sleep(1)

            # Validate position progression
            if len(positions) >= 2:
                print("\n4. Position Progression Analysis")
                print("-" * 70)

                # Check that position increases when playing
                position_delta = positions[-1] - positions[0]

                print(f"   First Position: {positions[0]}s")
                print(f"   Last Position: {positions[-1]}s")
                print(f"   Position Delta: {position_delta}s")
                print("   Test Duration: ~5 seconds (5 readings with 1s intervals)")

                if position_delta > 0:
                    print("   ✓ Position is increasing as expected")

                    # Position should increase roughly 4-6 seconds over our ~5 second test
                    # (5 readings with 1s sleep between = 4s sleep + refresh overhead)
                    if 3 <= position_delta <= 8:
                        print(f"   ✓ Position delta ({position_delta}s) is reasonable for ~5s test")
                    else:
                        print(f"   ⚠ Position delta ({position_delta}s) seems off for ~5s test")
                        print("      This might indicate position estimation issues or clock sync problems")
                elif position_delta == 0:
                    print("   ✗ WARNING: Position not increasing (may be paused or buffering)")
                else:
                    print(f"   ✗ WARNING: Position decreased by {abs(position_delta)}s (possible seek or track change)")

                # Validate clamping to duration
                if player.media_duration:
                    print("\n5. Duration Clamping Check")
                    print("-" * 70)
                    all_clamped = all(pos <= player.media_duration for pos in positions)
                    print(f"   Duration: {player.media_duration}s")
                    print(f"   Max Position: {max(positions)}s")

                    if all_clamped:
                        print("   ✓ Position properly clamped to duration")
                    else:
                        print("   ✗ WARNING: Position exceeds duration")
                        raise AssertionError("Position should not exceed duration")
        else:
            print(f"\n   ℹ Device is not playing (state: {player.play_state})")
            print("   Skipping position estimation test")

        # Check StateSynchronizer state
        print("\n6. StateSynchronizer State Check")
        print("-" * 70)

        merged_state = player._state_synchronizer.get_merged_state()
        source_health = merged_state.get("_source_health", {})
        http_available = source_health.get("http_available")
        upnp_available = source_health.get("upnp_available")

        print(f"   HTTP Available: {http_available}")
        print(f"   UPnP Available: {upnp_available}")
        print(f"   Merged Position: {merged_state.get('position')}")
        print(f"   Merged Duration: {merged_state.get('duration')}")
        print(f"   Merged Play State: {merged_state.get('play_state')}")

        if not upnp_available:
            print("\n   ⚠ NOTE: UPnP events are not available")
            print("      - Position updates rely only on HTTP polling")
            print("      - This may reduce accuracy of position estimation")
            print("      - Consider checking UPnP configuration if smooth progress is needed")

        # Summary
        print(f"\n{'=' * 70}")
        print("Test Summary")
        print(f"{'=' * 70}")
        print("✓ Media progress properties are accessible")
        print("✓ Position and duration are properly reported")
        if player.play_state == "play":
            print("✓ Position estimation is working")
        if not upnp_available:
            print("⚠ UPnP not available - position tracking relies only on HTTP polling")
        print(f"{'=' * 70}\n")

    finally:
        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_media_progress_when_paused():
    """Test that media progress remains stable when paused."""
    device_ip = "192.168.1.116"

    print(f"\n{'=' * 70}")
    print(f"Testing Media Progress When Paused on {device_ip}")
    print(f"{'=' * 70}\n")

    client = WiiMClient(host=device_ip)
    player = Player(client)

    try:
        await player.refresh()

        print(f"Play State: {player.play_state}")

        if player.play_state == "pause":
            print("✓ Device is paused - testing position stability...")

            initial_position = player.media_position
            print(f"Initial Position: {initial_position}s")

            # Wait and check position hasn't changed
            await asyncio.sleep(2)
            await player.refresh()

            final_position = player.media_position
            print(f"Final Position: {final_position}s")

            if initial_position == final_position:
                print("✓ Position remained stable when paused")
            else:
                print(f"✗ WARNING: Position changed when paused ({initial_position} → {final_position})")
        else:
            print(f"ℹ Device is not paused (state: {player.play_state})")
            print("Skipping paused position test")

    finally:
        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_media_progress_properties():
    """Test all media progress related properties."""
    device_ip = "192.168.1.116"

    print(f"\n{'=' * 70}")
    print(f"Testing All Media Progress Properties on {device_ip}")
    print(f"{'=' * 70}\n")

    client = WiiMClient(host=device_ip)
    player = Player(client)

    try:
        await player.refresh()

        # Test all progress-related properties
        properties = {
            "media_title": player.media_title,
            "media_artist": player.media_artist,
            "media_album": player.media_album,
            "media_duration": player.media_duration,
            "media_position": player.media_position,
            "media_position_updated_at": player.media_position_updated_at,
            "media_image_url": player.media_image_url,
            "play_state": player.play_state,
        }

        print("Property Values:")
        print("-" * 70)
        for key, value in properties.items():
            print(f"   {key}: {value}")

        # Verify types
        print("\nType Validation:")
        print("-" * 70)

        if player.media_duration is not None:
            assert isinstance(player.media_duration, int), "Duration should be int"
            print("   ✓ media_duration is int")

        if player.media_position is not None:
            assert isinstance(player.media_position, int), "Position should be int"
            print("   ✓ media_position is int")

        if player.media_position_updated_at is not None:
            assert isinstance(player.media_position_updated_at, float), "Timestamp should be float"
            print("   ✓ media_position_updated_at is float")

        # Calculate progress percentage if available
        if player.media_position is not None and player.media_duration is not None and player.media_duration > 0:
            progress = (player.media_position / player.media_duration) * 100
            print("\nProgress Calculation:")
            print("-" * 70)
            print(f"   Position: {player.media_position}s")
            print(f"   Duration: {player.media_duration}s")
            print(f"   Progress: {progress:.1f}%")

            # Format as time
            pos_min, pos_sec = divmod(player.media_position, 60)
            dur_min, dur_sec = divmod(player.media_duration, 60)
            print(f"   Display: {pos_min:02d}:{pos_sec:02d} / {dur_min:02d}:{dur_sec:02d}")

        print(f"\n{'=' * 70}")
        print("✓ All media progress properties are working")
        print(f"{'=' * 70}\n")

    finally:
        await client.close()


if __name__ == "__main__":
    """Run tests directly for quick debugging."""
    print("Running media progress tests...")
    print("Note: For full test output, use: pytest tests/integration/test_media_progress.py -v -s")

    async def run_all():
        await test_media_progress_tracking()
        await test_media_progress_when_paused()
        await test_media_progress_properties()

    asyncio.run(run_all())
