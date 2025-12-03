#!/usr/bin/env python3
"""Comprehensive feature testing script for all devices.

Tests all available features:
- Audio output mode switching
- EQ preset selection
- Preset playback
- Cover art fetching
- State properties
- Capability detection
- Bluetooth devices
- Timer functionality
- And more...

Usage:
    python scripts/test_all_features.py 192.168.1.115 192.168.1.116 ...
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


async def test_audio_output_modes(player: Player) -> dict[str, Any]:
    """Test audio output mode switching."""
    print("\n🔊 Testing Audio Output Modes...")
    result = {"tested": False, "modes_available": 0, "switched": False, "errors": []}

    try:
        await player.refresh(full=True)

        if not player.supports_audio_output:
            print("   ⚠️  Audio output control not supported")
            return result

        # Get available modes
        available_modes = player.available_output_modes
        available_outputs = player.available_outputs

        if not available_modes:
            print("   ⚠️  No audio output modes available")
            return result

        result["modes_available"] = len(available_modes)
        print(f"   Available modes: {', '.join(available_modes)}")
        print(f"   Available outputs: {len(available_outputs)}")

        current_mode = player.audio_output_mode
        print(f"   Current mode: {current_mode}")

        # Test switching if multiple modes available
        if len(available_modes) >= 2:
            alternate = None
            for mode in available_modes:
                if mode != current_mode:
                    alternate = mode
                    break

            if alternate:
                print(f"   Testing switch to: {alternate}")
                await player.audio.set_audio_output_mode(alternate)
                await asyncio.sleep(2.0)
                await player.refresh(full=True)

                new_mode = player.audio_output_mode
                if new_mode == alternate or new_mode in available_modes:
                    print(f"   ✅ Switched to: {new_mode}")
                    result["switched"] = True
                else:
                    print(f"   ⚠️  Mode: {new_mode}")

                # Restore
                if current_mode:
                    await player.audio.set_audio_output_mode(current_mode)
                    await asyncio.sleep(1.0)

        # Test BT output if available
        bt_devices = player.bluetooth_output_devices
        if bt_devices:
            print(f"   Paired BT devices: {len(bt_devices)}")
            for bt in bt_devices[:1]:  # Test first one
                bt_name = f"BT: {bt['name']}"
                if bt_name in available_outputs:
                    print(f"   Testing BT output: {bt['name']}")
                    try:
                        await player.audio.select_output(bt_name)
                        await asyncio.sleep(2.0)
                        await player.refresh(full=True)
                        if player.is_bluetooth_output_active:
                            print(f"   ✅ BT output active")
                        else:
                            print(f"   ⚠️  BT selected but not active")
                    except Exception as e:
                        print(f"   ⚠️  BT switch: {e}")

        result["tested"] = True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_eq_presets(player: Player) -> dict[str, Any]:
    """Test EQ preset selection."""
    print("\n🎛️  Testing EQ Presets...")
    result = {"tested": False, "presets_available": 0, "switched": False, "errors": []}

    try:
        await player.refresh(full=True)

        if not player.supports_eq:
            print("   ⚠️  EQ not supported")
            return result

        # Get EQ presets
        eq_presets = await player.audio.get_eq_presets()
        if not eq_presets:
            print("   ⚠️  No EQ presets available")
            return result

        result["presets_available"] = len(eq_presets)
        print(f"   Available presets: {', '.join(eq_presets)}")

        current_preset = player.eq_preset
        print(f"   Current preset: {current_preset}")

        # Test switching
        if len(eq_presets) >= 2:
            alternate = None
            for preset in eq_presets:
                if preset != current_preset:
                    alternate = preset
                    break

            if alternate:
                print(f"   Testing switch to: {alternate}")
                await player.set_eq_preset(alternate)
                await asyncio.sleep(1.0)
                await player.refresh()

                new_preset = player.eq_preset
                if new_preset:
                    print(f"   ✅ Preset: {new_preset}")
                    result["switched"] = True

                # Restore
                if current_preset and current_preset in eq_presets:
                    await player.set_eq_preset(current_preset)
                    await asyncio.sleep(0.5)

        result["tested"] = True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_presets(player: Player) -> dict[str, Any]:
    """Test preset playback."""
    print("\n⭐ Testing Presets...")
    result = {"tested": False, "presets_available": 0, "played": False, "errors": []}

    try:
        await player.refresh(full=True)

        if not player.supports_presets:
            print("   ⚠️  Presets not supported")
            return result

        # Get presets
        presets = player.presets
        if not presets:
            print("   ⚠️  No presets configured")
            return result

        result["presets_available"] = len(presets)
        print(f"   Available presets: {len(presets)}")

        # Find a valid preset number
        test_preset = None
        for preset in presets:
            preset_num = preset.get("number")
            if preset_num:
                try:
                    num = int(preset_num)
                    if 1 <= num <= 20:
                        test_preset = num
                        print(f"   Testing preset {num}: {preset.get('name', 'Unnamed')}")
                        break
                except (ValueError, TypeError):
                    continue

        if test_preset:
            initial_state = player.play_state
            try:
                await player.play_preset(test_preset)
                await asyncio.sleep(3.0)
                await player.refresh()

                new_state = player.play_state
                if new_state in ("play", "playing", "PLAY", "buffering"):
                    print(f"   ✅ Preset playback started")
                    result["played"] = True
                elif new_state in ("pause", "paused", "PAUSE"):
                    print(f"   ℹ️  Preset loaded but paused")
                    result["played"] = True
                else:
                    print(f"   ⚠️  State: {new_state}")

                # Restore
                if initial_state in ("pause", "paused", "PAUSE", "stop", "STOP", "idle", "IDLE"):
                    await player.pause()
                    await asyncio.sleep(0.5)
            except Exception as e:
                print(f"   ⚠️  Preset playback: {e}")

        result["tested"] = True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_cover_art(player: Player) -> dict[str, Any]:
    """Test cover art fetching."""
    print("\n🖼️  Testing Cover Art...")
    result = {"tested": False, "has_art": False, "url": None, "errors": []}

    try:
        await player.refresh()

        image_url = player.media_image_url
        if image_url:
            print(f"   ✅ Cover art URL: {image_url[:60]}...")
            result["has_art"] = True
            result["url"] = image_url
        else:
            print("   ℹ️  No cover art available (may be normal)")

        result["tested"] = True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_state_properties(player: Player) -> dict[str, Any]:
    """Test state properties."""
    print("\n📊 Testing State Properties...")
    result = {"tested": False, "properties": {}, "errors": []}

    try:
        await player.refresh()

        props = {
            "is_playing": player.is_playing,
            "is_paused": player.is_paused,
            "is_idle": player.is_idle,
            "is_buffering": player.is_buffering,
            "state": player.state,
            "play_state": player.play_state,
        }

        result["properties"] = props
        print(f"   is_playing: {props['is_playing']}")
        print(f"   is_paused: {props['is_paused']}")
        print(f"   is_idle: {props['is_idle']}")
        print(f"   is_buffering: {props['is_buffering']}")
        print(f"   state: {props['state']}")

        result["tested"] = True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_capabilities(player: Player) -> dict[str, Any]:
    """Test capability detection."""
    print("\n🎯 Testing Capabilities...")
    result = {"tested": False, "capabilities": {}, "errors": []}

    try:
        await player.refresh(full=True)

        caps = {
            "supports_eq": player.supports_eq,
            "supports_presets": player.supports_presets,
            "supports_audio_output": player.supports_audio_output,
            "supports_metadata": player.supports_metadata,
            "supports_alarms": player.supports_alarms,
            "supports_sleep_timer": player.supports_sleep_timer,
            "supports_led_control": player.supports_led_control,
            "supports_enhanced_grouping": player.supports_enhanced_grouping,
            "supports_upnp": player.supports_upnp,
            "shuffle_supported": player.shuffle_supported,
            "repeat_supported": player.repeat_supported,
        }

        result["capabilities"] = caps

        print("   Supported features:")
        for cap, value in caps.items():
            if value:
                print(f"      ✅ {cap}")

        result["tested"] = True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_bluetooth(player: Player) -> dict[str, Any]:
    """Test Bluetooth functionality."""
    print("\n📱 Testing Bluetooth...")
    result = {"tested": False, "paired_devices": 0, "errors": []}

    try:
        await player.refresh(full=True)

        # Get paired devices
        bt_devices = player.bluetooth_output_devices
        result["paired_devices"] = len(bt_devices)

        if bt_devices:
            print(f"   Paired devices: {len(bt_devices)}")
            for bt in bt_devices[:3]:  # Show first 3
                print(f"      - {bt.get('name', 'Unknown')} ({bt.get('mac', 'N/A')})")
        else:
            print("   ℹ️  No paired Bluetooth devices")

        result["tested"] = True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_timers(player: Player) -> dict[str, Any]:
    """Test timer functionality."""
    print("\n⏰ Testing Timers...")
    result = {"tested": False, "sleep_timer_supported": False, "alarms_supported": False, "errors": []}

    try:
        await player.refresh(full=True)

        result["sleep_timer_supported"] = player.supports_sleep_timer
        result["alarms_supported"] = player.supports_alarms

        if player.supports_sleep_timer:
            print("   ✅ Sleep timer supported")
        else:
            print("   ℹ️  Sleep timer not supported")

        if player.supports_alarms:
            print("   ✅ Alarms supported")
        else:
            print("   ℹ️  Alarms not supported")

        result["tested"] = True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        result["errors"].append(str(e))

    return result


async def test_device_features(
    ip: str, max_volume: float = 0.10, device_num: int = 0, total_devices: int = 0
) -> dict[str, Any]:
    """Test all features on a device."""
    if device_num > 0:
        print(f"\n{'='*70}")
        print(f"[{device_num}/{total_devices}] Testing All Features: {ip}")
    else:
        print(f"\n{'='*70}")
        print(f"Testing All Features: {ip}")
    print(f"{'='*70}\n")
    sys.stdout.flush()

    result = {
        "ip": ip,
        "device_name": None,
        "initial_volume": None,
        "tests": {},
        "errors": [],
    }

    client = WiiMClient(host=ip)
    player = Player(client)

    try:
        # Get device info
        print("📱 Connecting and getting device info...")
        sys.stdout.flush()
        await player.refresh(full=True)
        device_info = await player.get_device_info()
        result["device_name"] = device_info.name
        print(f"📱 Device: {device_info.name} ({device_info.model})")
        print(f"   Firmware: {device_info.firmware}\n")
        sys.stdout.flush()

        # Save and set safe volume
        print("🔊 Setting safe volume...")
        sys.stdout.flush()
        result["initial_volume"] = await player.get_volume()
        if result["initial_volume"] is not None:
            safe_volume = min(
                max_volume, result["initial_volume"] if result["initial_volume"] < max_volume else max_volume
            )
            await player.set_volume(safe_volume)
            await asyncio.sleep(0.5)

        # Run all feature tests with progress indicators
        test_names = [
            "capabilities",
            "state_properties",
            "audio_output",
            "eq_presets",
            "presets",
            "cover_art",
            "bluetooth",
            "timers",
        ]

        for idx, test_name in enumerate(test_names, 1):
            print(f"\n[{idx}/{len(test_names)}] Running {test_name} tests...")
            sys.stdout.flush()

            if test_name == "capabilities":
                result["tests"]["capabilities"] = await test_capabilities(player)
            elif test_name == "state_properties":
                result["tests"]["state_properties"] = await test_state_properties(player)
            elif test_name == "audio_output":
                result["tests"]["audio_output"] = await test_audio_output_modes(player)
            elif test_name == "eq_presets":
                result["tests"]["eq_presets"] = await test_eq_presets(player)
            elif test_name == "presets":
                result["tests"]["presets"] = await test_presets(player)
            elif test_name == "cover_art":
                result["tests"]["cover_art"] = await test_cover_art(player)
            elif test_name == "bluetooth":
                result["tests"]["bluetooth"] = await test_bluetooth(player)
            elif test_name == "timers":
                result["tests"]["timers"] = await test_timers(player)

            sys.stdout.flush()

        print(f"\n✅ Feature tests completed for {ip}")
        sys.stdout.flush()

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        result["errors"].append(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.stdout.flush()
    finally:
        # Restore volume
        if result["initial_volume"] is not None:
            try:
                print("🔄 Restoring initial volume...")
                sys.stdout.flush()
                await player.set_volume(result["initial_volume"])
                await asyncio.sleep(0.5)
            except Exception:
                pass

        await client.close()

    return result


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test all available features on devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "device_ips",
        nargs="+",
        help="Device IP addresses to test",
    )
    parser.add_argument(
        "--max-volume",
        type=float,
        default=0.10,
        help="Maximum volume for testing (default: 10%%)",
    )

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print("Comprehensive Feature Testing")
    print(f"{'='*70}")
    print(f"\nTesting {len(args.device_ips)} device(s)")
    print(f"Max volume: {args.max_volume:.0%}\n")

    results = []
    total = len(args.device_ips)
    for idx, ip in enumerate(args.device_ips, 1):
        result = await test_device_features(ip, args.max_volume, device_num=idx, total_devices=total)
        results.append(result)

    # Summary
    print(f"\n{'='*70}")
    print("FEATURE TEST SUMMARY")
    print(f"{'='*70}\n")

    for result in results:
        print(f"{result['ip']} ({result['device_name']}):")

        for test_name, test_result in result["tests"].items():
            if isinstance(test_result, dict) and test_result.get("tested"):
                status = "✅" if not test_result.get("errors") else "⚠️"
                print(f"  {status} {test_name}")
                if test_result.get("errors"):
                    for error in test_result["errors"]:
                        print(f"      - {error}")
            else:
                print(f"  ⚠️  {test_name} (not tested)")

        if result["errors"]:
            print(f"  Errors: {len(result['errors'])}")
        print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
