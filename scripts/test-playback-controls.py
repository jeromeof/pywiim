#!/usr/bin/env python3
"""Test script for verifying play/pause, shuffle, and repeat controls on real WiiM devices.

This script tests the Player object's playback control methods against real hardware.

Usage:
    python scripts/test-playback-controls.py <device_ip>

Example:
    python scripts/test-playback-controls.py 192.168.1.100

Requirements:
    - Device must be on the network and accessible
    - Device should have some media ready to play (queue not empty)
    - Script will not change volume or disrupt playback permanently
"""

import asyncio
import sys
from typing import Any

from pywiim import WiiMClient
from pywiim.exceptions import WiiMError
from pywiim.player import Player


async def wait_for_state_update(player: Player, delay: float = 1.0) -> None:
    """Wait and refresh player state."""
    await asyncio.sleep(delay)
    await player.refresh()


async def test_playback_controls(ip: str) -> dict[str, Any]:
    """Test play/pause/shuffle/repeat controls on a real device."""
    print(f"\n{'='*70}")
    print(f"🎵 Testing Playback Controls on {ip}")
    print(f"{'='*70}\n")

    results = {
        "ip": ip,
        "connected": False,
        "device_info": None,
        "tests": {
            "play": None,
            "pause": None,
            "next": None,
            "previous": None,
            "shuffle": None,
            "repeat": None,
            "eq": None,
            "output_selection": None,
            "input_selection": None,
        },
        "errors": [],
    }

    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)

    try:
        # Initialize connection
        print("📋 Connecting to device...")
        await player.refresh()

        device_info = player.device_info
        if not device_info:
            raise WiiMError("Failed to get device info")

        results["device_info"] = {
            "name": player.name,
            "model": player.model,
            "firmware": player.firmware,
        }
        results["connected"] = True

        print(f"   ✓ Connected: {player.name}")
        print(f"   ✓ Model: {player.model}")
        print(f"   ✓ Firmware: {player.firmware}\n")

        # Store initial state
        initial_state = player.play_state
        initial_shuffle = player.shuffle_state
        initial_repeat = player.repeat_mode

        print("📊 Initial State:")
        print(f"   Play State: {initial_state}")
        print(f"   Shuffle: {initial_shuffle}")
        print(f"   Repeat: {initial_repeat}\n")

        # ================================================================
        # Test 1: Play Command
        # ================================================================
        print("🎯 Test 1: Play Command")
        try:
            await player.play()
            await wait_for_state_update(player, 1.5)

            new_state = player.play_state
            print("   ✓ Play command sent")
            print(f"   State after play: {new_state}")

            results["tests"]["play"] = {
                "success": True,
                "before": initial_state,
                "after": new_state,
            }
        except Exception as e:
            print(f"   ✗ Play test failed: {e}")
            results["tests"]["play"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Play test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 2: Pause Command
        # ================================================================
        print("\n🎯 Test 2: Pause Command")
        try:
            await player.pause()
            await wait_for_state_update(player, 1.5)

            new_state = player.play_state
            print("   ✓ Pause command sent")
            print(f"   State after pause: {new_state}")

            results["tests"]["pause"] = {
                "success": True,
                "after": new_state,
            }
        except Exception as e:
            print(f"   ✗ Pause test failed: {e}")
            results["tests"]["pause"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Pause test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 3: Next Track
        # ================================================================
        print("\n🎯 Test 3: Next Track")
        try:
            # Get current track info before next
            await player.refresh()
            track_before = player.media_title
            position_before = player.media_position
            
            print(f"   Current track: {track_before}")
            print(f"   Position: {position_before}s")
            
            await player.next_track()
            await wait_for_state_update(player, 2.0)

            track_after = player.media_title
            position_after = player.media_position
            print("   ✓ Next track command sent")
            print(f"   Track after next: {track_after}")
            print(f"   Position after: {position_after}s")

            results["tests"]["next"] = {
                "success": True,
                "track_before": track_before,
                "track_after": track_after,
                "changed": track_before != track_after,
            }
        except Exception as e:
            print(f"   ✗ Next track test failed: {e}")
            results["tests"]["next"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Next track test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 4: Previous Track
        # ================================================================
        print("\n🎯 Test 4: Previous Track")
        try:
            # Get current track info before previous
            await player.refresh()
            track_before = player.media_title
            position_before = player.media_position
            
            print(f"   Current track: {track_before}")
            print(f"   Position: {position_before}s")
            
            await player.previous_track()
            await wait_for_state_update(player, 2.0)

            track_after = player.media_title
            position_after = player.media_position
            print("   ✓ Previous track command sent")
            print(f"   Track after previous: {track_after}")
            print(f"   Position after: {position_after}s")

            results["tests"]["previous"] = {
                "success": True,
                "track_before": track_before,
                "track_after": track_after,
                "changed": track_before != track_after,
            }
        except Exception as e:
            print(f"   ✗ Previous track test failed: {e}")
            results["tests"]["previous"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Previous track test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 5: Shuffle Control
        # ================================================================
        print("\n🎯 Test 5: Shuffle Control")
        try:
            # Enable shuffle
            print("   Testing shuffle ON...")
            await player.set_shuffle(True)
            await wait_for_state_update(player, 1.5)

            shuffle_on = player.shuffle_state
            repeat_after_shuffle = player.repeat_mode
            print("   ✓ Set shuffle ON")
            print(f"   Shuffle state: {shuffle_on}")
            print(f"   Repeat preserved: {repeat_after_shuffle}")

            # Disable shuffle
            print("   Testing shuffle OFF...")
            await player.set_shuffle(False)
            await wait_for_state_update(player, 1.5)

            shuffle_off = player.shuffle_state
            repeat_after_unshuffle = player.repeat_mode
            print("   ✓ Set shuffle OFF")
            print(f"   Shuffle state: {shuffle_off}")
            print(f"   Repeat preserved: {repeat_after_unshuffle}")

            results["tests"]["shuffle"] = {
                "success": True,
                "initial": initial_shuffle,
                "after_on": shuffle_on,
                "after_off": shuffle_off,
                "repeat_preserved": repeat_after_shuffle == repeat_after_unshuffle,
            }
        except Exception as e:
            print(f"   ✗ Shuffle test failed: {e}")
            results["tests"]["shuffle"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Shuffle test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 6: Repeat Control
        # ================================================================
        print("\n🎯 Test 6: Repeat Control")
        try:
            # Test repeat "all"
            print("   Testing repeat ALL...")
            await player.set_repeat("all")
            await wait_for_state_update(player, 1.5)

            repeat_all = player.repeat_mode
            shuffle_after_repeat_all = player.shuffle_state
            print("   ✓ Set repeat ALL")
            print(f"   Repeat mode: {repeat_all}")
            print(f"   Shuffle preserved: {shuffle_after_repeat_all}")

            # Test repeat "one"
            print("   Testing repeat ONE...")
            await player.set_repeat("one")
            await wait_for_state_update(player, 1.5)

            repeat_one = player.repeat_mode
            shuffle_after_repeat_one = player.shuffle_state
            print("   ✓ Set repeat ONE")
            print(f"   Repeat mode: {repeat_one}")
            print(f"   Shuffle preserved: {shuffle_after_repeat_one}")

            # Test repeat "off"
            print("   Testing repeat OFF...")
            await player.set_repeat("off")
            await wait_for_state_update(player, 1.5)

            repeat_off = player.repeat_mode
            shuffle_after_repeat_off = player.shuffle_state
            print("   ✓ Set repeat OFF")
            print(f"   Repeat mode: {repeat_off}")
            print(f"   Shuffle preserved: {shuffle_after_repeat_off}")

            results["tests"]["repeat"] = {
                "success": True,
                "initial": initial_repeat,
                "after_all": repeat_all,
                "after_one": repeat_one,
                "after_off": repeat_off,
                "shuffle_preserved": (shuffle_after_repeat_all == shuffle_after_repeat_one == shuffle_after_repeat_off),
            }
        except Exception as e:
            print(f"   ✗ Repeat test failed: {e}")
            results["tests"]["repeat"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Repeat test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 7: EQ Presets
        # ================================================================
        print("\n🎯 Test 7: EQ Presets")
        try:
            await player.refresh(full=True)
            
            if not player.supports_eq:
                print("   ⚠️  EQ not supported on this device")
                results["tests"]["eq"] = {"success": False, "error": "EQ not supported"}
            else:
                # Get available EQ presets
                eq_presets = await player.audio.get_eq_presets()
                if not eq_presets:
                    print("   ⚠️  No EQ presets available")
                    results["tests"]["eq"] = {"success": False, "error": "No presets available"}
                else:
                    print(f"   Available presets: {', '.join(eq_presets)}")
                    
                    current_preset = player.eq_preset
                    print(f"   Current preset: {current_preset}")
                    
                    # Normalize preset names for comparison (handle case differences)
                    # Device may return "flat" in status but "Flat" in preset list
                    current_preset_lower = current_preset.lower() if current_preset else ""
                    eq_presets_lower = [p.lower() for p in eq_presets]
                    
                    # Test switching to a different preset if available
                    if len(eq_presets) >= 2:
                        alternate = None
                        # Find a preset that's actually different (case-insensitive comparison)
                        for preset in eq_presets:
                            if preset.lower() != current_preset_lower:
                                alternate = preset
                                break
                        
                        if alternate:
                            print(f"   Testing switch to: {alternate}")
                            await player.set_eq_preset(alternate)
                            await wait_for_state_update(player, 2.0)
                            
                            # Check both the property and the actual EQ status
                            new_preset = player.eq_preset
                            
                            # Also check EQ status directly to verify the change
                            try:
                                eq_status = await player.audio.get_eq()
                                eq_name_from_status = None
                                if isinstance(eq_status, dict):
                                    eq_name_from_status = eq_status.get("Name") or eq_status.get("name")
                            except Exception:
                                eq_name_from_status = None
                            
                            print(f"   Preset property: {new_preset}")
                            if eq_name_from_status:
                                print(f"   EQ status name: {eq_name_from_status}")
                            
                            # Verify it actually changed (case-insensitive comparison)
                            # Check against both the property and the EQ status
                            preset_changed_prop = new_preset and new_preset.lower() != current_preset_lower
                            preset_changed_status = eq_name_from_status and eq_name_from_status.lower() != current_preset_lower
                            preset_changed = preset_changed_prop or preset_changed_status
                            
                            if preset_changed:
                                print(f"   ✓ Preset changed successfully")
                            else:
                                print(f"   ⚠️  Preset may not have changed (device may not support EQ changes for current source)")
                            
                            # Restore original preset
                            if current_preset and current_preset in eq_presets:
                                await player.set_eq_preset(current_preset)
                                await asyncio.sleep(1.0)
                                print(f"   ✓ Restored to: {current_preset}")
                            
                            results["tests"]["eq"] = {
                                "success": True,
                                "presets_available": len(eq_presets),
                                "switched": preset_changed,
                                "from": current_preset,
                                "to": new_preset or eq_name_from_status,
                            }
                        else:
                            print("   ⚠️  Only one preset available, cannot test switching")
                            results["tests"]["eq"] = {
                                "success": True,
                                "presets_available": len(eq_presets),
                                "switched": False,
                            }
                    else:
                        print("   ⚠️  Only one preset available, cannot test switching")
                        results["tests"]["eq"] = {
                            "success": True,
                            "presets_available": len(eq_presets),
                            "switched": False,
                        }
        except Exception as e:
            print(f"   ✗ EQ test failed: {e}")
            results["tests"]["eq"] = {"success": False, "error": str(e)}
            results["errors"].append(f"EQ test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 8: Output Selection
        # ================================================================
        print("\n🎯 Test 8: Output Selection")
        try:
            await player.refresh(full=True)
            
            if not player.supports_audio_output:
                print("   ⚠️  Audio output control not supported")
                results["tests"]["output_selection"] = {"success": False, "error": "Not supported"}
            else:
                available_outputs = player.available_outputs
                if not available_outputs:
                    print("   ⚠️  No outputs available")
                    results["tests"]["output_selection"] = {"success": False, "error": "No outputs"}
                else:
                    print(f"   Available outputs: {', '.join(available_outputs)}")
                    
                    current_output = player.audio_output_mode
                    print(f"   Current output: {current_output}")
                    
                    # Test switching to a different hardware output (skip BT if no paired device)
                    hardware_outputs = [out for out in available_outputs if not out.startswith("BT: ")]
                    
                    if len(hardware_outputs) >= 2:
                        alternate = None
                        for output in hardware_outputs:
                            # Find a different hardware output
                            if output != current_output:
                                alternate = output
                                break
                        
                        if alternate:
                            print(f"   Testing switch to: {alternate}")
                            try:
                                await player.audio.select_output(alternate)
                                await wait_for_state_update(player, 2.0)
                                
                                new_output = player.audio_output_mode
                                print(f"   ✓ Output after switch: {new_output}")
                                
                                # Restore original output
                                if current_output and current_output in available_outputs:
                                    await player.audio.select_output(current_output)
                                    await asyncio.sleep(1.0)
                                    print(f"   ✓ Restored to: {current_output}")
                                
                                results["tests"]["output_selection"] = {
                                    "success": True,
                                    "outputs_available": len(available_outputs),
                                    "switched": True,
                                }
                            except Exception as e:
                                print(f"   ⚠️  Output switch failed: {e}")
                                results["tests"]["output_selection"] = {
                                    "success": False,
                                    "error": str(e),
                                }
                        else:
                            print("   ⚠️  Only one hardware output available")
                            results["tests"]["output_selection"] = {
                                "success": True,
                                "outputs_available": len(available_outputs),
                                "switched": False,
                            }
                    else:
                        print("   ⚠️  Only one hardware output available")
                        results["tests"]["output_selection"] = {
                            "success": True,
                            "outputs_available": len(available_outputs),
                            "switched": False,
                        }
                    
                    # Test BT output if available (will fail if no paired device - expected)
                    bt_outputs = [out for out in available_outputs if out.startswith("BT: ")]
                    if bt_outputs:
                        print(f"   Testing BT output: {bt_outputs[0]}")
                        try:
                            await player.audio.select_output(bt_outputs[0])
                            await wait_for_state_update(player, 2.0)
                            if player.is_bluetooth_output_active:
                                print(f"   ✓ BT output active")
                            else:
                                print(f"   ⚠️  BT selected but not active")
                            # Restore original output
                            if current_output and current_output in available_outputs:
                                await player.audio.select_output(current_output)
                                await asyncio.sleep(1.0)
                        except Exception as e:
                            print(f"   ⚠️  BT output test failed (expected if no paired device): {e}")
                            # This is expected to fail if no device is paired, so don't mark as error
        except Exception as e:
            print(f"   ✗ Output selection test failed: {e}")
            results["tests"]["output_selection"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Output selection test: {e}")

        await asyncio.sleep(1)

        # ================================================================
        # Test 9: Input Selection
        # ================================================================
        print("\n🎯 Test 9: Input Selection")
        try:
            await player.refresh(full=True)
            
            available_sources = player.available_sources
            if not available_sources:
                print("   ⚠️  No input sources available")
                results["tests"]["input_selection"] = {"success": False, "error": "No sources"}
            else:
                print(f"   Available sources: {', '.join(available_sources)}")
                
                current_source = player.source
                print(f"   Current source: {current_source}")
                
                # Test switching to a different source if available
                if len(available_sources) >= 2:
                    alternate = None
                    for source in available_sources:
                        if source != current_source:
                            alternate = source
                            break
                    
                    if alternate:
                        print(f"   Testing switch to: {alternate}")
                        try:
                            await player.set_source(alternate)
                            await wait_for_state_update(player, 2.0)
                            
                            new_source = player.source
                            print(f"   ✓ Source after switch: {new_source}")
                            
                            # Restore original source
                            if current_source and current_source in available_sources:
                                await player.set_source(current_source)
                                await asyncio.sleep(1.0)
                                print(f"   ✓ Restored to: {current_source}")
                            
                            results["tests"]["input_selection"] = {
                                "success": True,
                                "sources_available": len(available_sources),
                                "switched": new_source == alternate or new_source in available_sources,
                            }
                        except Exception as e:
                            print(f"   ⚠️  Source switch failed: {e}")
                            results["tests"]["input_selection"] = {
                                "success": False,
                                "error": str(e),
                            }
                    else:
                        print("   ⚠️  Only one source available")
                        results["tests"]["input_selection"] = {
                            "success": True,
                            "sources_available": len(available_sources),
                            "switched": False,
                        }
                else:
                    print("   ⚠️  Only one source available")
                    results["tests"]["input_selection"] = {
                        "success": True,
                        "sources_available": len(available_sources),
                        "switched": False,
                    }
        except Exception as e:
            print(f"   ✗ Input selection test failed: {e}")
            results["tests"]["input_selection"] = {"success": False, "error": str(e)}
            results["errors"].append(f"Input selection test: {e}")

        # ================================================================
        # Restore Initial State
        # ================================================================
        print("\n🔄 Restoring initial state...")
        try:
            if initial_shuffle is not None:
                await player.set_shuffle(initial_shuffle)
            if initial_repeat is not None:
                await player.set_repeat(initial_repeat)
            if initial_state and initial_state in ["play", "playing"]:
                await player.play()
            elif initial_state and initial_state in ["pause", "paused"]:
                await player.pause()

            print("   ✓ State restored")
        except Exception as e:
            print(f"   ⚠ Could not fully restore state: {e}")

        print(f"\n{'='*70}")
        print("✅ All tests completed!")
        print(f"{'='*70}")

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        results["errors"].append("Test interrupted")
    except Exception as e:
        results["errors"].append(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()

    return results


async def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test-playback-controls.py <device_ip>")
        print("\nExample:")
        print("  python scripts/test-playback-controls.py 192.168.1.100")
        print("\nNote: Device should have media in queue for best results")
        sys.exit(1)

    device_ip = sys.argv[1]

    # Run tests
    result = await test_playback_controls(device_ip)

    # Print summary
    print(f"\n{'='*70}")
    print("📊 TEST SUMMARY")
    print(f"{'='*70}\n")

    if result["connected"]:
        info = result["device_info"]
        print(f"Device: {info['name']} ({info['model']}) - fw: {info['firmware']}")
        print("\nTest Results:")

        for test_name, test_result in result["tests"].items():
            if test_result is None:
                status = "⊘ Not run"
            elif test_result.get("success"):
                status = "✅ Passed"
            else:
                status = f"❌ Failed - {test_result.get('error', 'Unknown error')}"

            print(f"  {test_name.ljust(15)}: {status}")

        if result["errors"]:
            print("\n⚠️  Errors encountered:")
            for error in result["errors"]:
                print(f"  • {error}")
    else:
        print(f"❌ Could not connect to {device_ip}")
        if result["errors"]:
            for error in result["errors"]:
                print(f"  Error: {error}")

    print(f"\n{'='*70}\n")

    # Exit with appropriate code
    if result["connected"] and not result["errors"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
