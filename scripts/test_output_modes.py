#!/usr/bin/env python3
"""Test output mode selection for a WiiM device."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pywiim.client import WiiMClient
from pywiim.player import Player


async def test_output_modes(host: str):
    """Test output mode selection.

    Args:
        host: IP address or hostname of the device to test.
    """

    print(f"Connecting to {host}...")
    client = WiiMClient(host)
    player = Player(client)

    try:
        # Aggressive full refresh to get all data
        print("\n=== Refreshing device state (full refresh) ===")
        await player.refresh(full=True)

        # Also explicitly fetch audio output status to ensure it's fresh
        await player.audio.get_audio_output_status()

        # Refresh BT history explicitly
        await player.get_bluetooth_history()

        # One more full refresh to ensure everything is synced
        await player.refresh(full=True)

        print(f"\nDevice: {player.name} ({player.model})")
        print(f"Current output mode: {player.audio_output_mode}")
        print(f"Current output mode (int): {player.audio_output_mode_int}")

        # Check BT history
        print("\n=== Bluetooth History ===")
        bt_history = await player.get_bluetooth_history()
        print(f"Total BT devices in history: {len(bt_history)}")
        for device in bt_history:
            role = device.get("role", "Unknown")
            name = device.get("name", "Unknown")
            mac = device.get("ad", "Unknown")
            connected = device.get("ct") == 1
            print(f"  - {name} ({mac}) - Role: {role}, Connected: {connected}")

        # Check BT output devices
        print("\n=== Bluetooth Output Devices (Audio Sinks) ===")
        bt_output_devices = player.bluetooth_output_devices
        print(f"BT output devices: {len(bt_output_devices)}")
        for device in bt_output_devices:
            print(f"  - {device['name']} ({device['mac']}) - Connected: {device['connected']}")

        # Check available output modes
        print("\n=== Available Output Modes (hardware) ===")
        available_modes = player.available_output_modes
        print(f"Available modes: {available_modes}")

        # Check available outputs (combined)
        print("\n=== Available Outputs (combined) ===")
        available_outputs = player.available_outputs
        print(f"Available outputs: {available_outputs}")

        # Test selecting each output
        print("\n=== Testing Output Selection ===")
        for output in available_outputs:
            print(f"\nSelecting: {output}")
            try:
                # Aggressive refresh before selection
                await player.refresh(full=True)
                await player.audio.get_audio_output_status()
                status_before = await player.client.get_audio_output_status()
                print(f"  Before: hardware={status_before.get('hardware')}, source={status_before.get('source')}")

                await player.audio.select_output(output)
                # Wait longer for the change to take effect
                await asyncio.sleep(2)

                # Aggressive refresh after selection
                await player.refresh(full=True)
                await player.audio.get_audio_output_status()

                # Also fetch status directly
                status_after = await player.client.get_audio_output_status()
                # Check cached status
                cached_status = player._audio_output_status
                current_mode = player.audio_output_mode
                print(f"  After: hardware={status_after.get('hardware')}, source={status_after.get('source')}")
                if cached_status:
                    print(f"  Cached: hardware={cached_status.get('hardware')}, source={cached_status.get('source')}")
                print(f"  ✓ Success - Current mode: {current_mode}")
            except Exception as e:
                print(f"  ✗ Error: {e}")
                # After error, check what the current state is
                try:
                    await player.refresh(full=True)
                    status_after_error = await player.client.get_audio_output_status()
                    cached_after_error = player._audio_output_status
                    current_mode_after_error = player.audio_output_mode
                    print(
                        f"  After error - Status: hardware={status_after_error.get('hardware') if status_after_error else None}, source={status_after_error.get('source') if status_after_error else None}"
                    )
                    if cached_after_error:
                        print(
                            f"  After error - Cached: hardware={cached_after_error.get('hardware')}, source={cached_after_error.get('source')}"
                        )
                    else:
                        print(f"  After error - Cached: None (cleared)")
                    print(f"  After error - Current mode: {current_mode_after_error}")
                except Exception as refresh_err:
                    print(f"  Failed to refresh after error: {refresh_err}")
                import traceback

                traceback.print_exc()

        # Final state with aggressive refresh
        print("\n=== Final State ===")
        await player.refresh(full=True)
        await player.audio.get_audio_output_status()
        print(f"Final output mode: {player.audio_output_mode}")
        print(f"Final output mode (int): {player.audio_output_mode_int}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test output mode selection for a WiiM device")
    parser.add_argument(
        "host",
        nargs="?",
        default="192.168.1.68",
        help="IP address or hostname of the device to test (default: 192.168.1.68)",
    )
    args = parser.parse_args()

    asyncio.run(test_output_modes(args.host))
