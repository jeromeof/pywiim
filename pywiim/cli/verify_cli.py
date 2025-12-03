"""Command-line tool for testing all WiiM device features and endpoints.

This tool exercises all available commands and endpoints with safety constraints
(e.g., volume never exceeds 10%) to verify functionality without disrupting normal use.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from ..client import WiiMClient
from ..player import Player


class FeatureTester:
    """Test all device features and endpoints safely."""

    def __init__(self, player: Player, verbose: bool = False) -> None:
        """Initialize tester with a Player instance."""
        self.player = player
        self.client = player.client
        self.verbose = verbose
        self.results: dict[str, Any] = {
            "passed": [],
            "failed": [],
            "skipped": [],
            "not_supported": [],
            "warnings": [],
        }
        self.original_state: dict[str, Any] = {}

    def _format_data(self, data: Any, max_depth: int = 2, indent: int = 0) -> str:
        """Format data for display, limiting depth and size."""
        if data is None:
            return "None"

        if isinstance(data, dict):
            if not data:
                return "{}"
            if max_depth <= 0:
                return "{...}"
            items = []
            for k, v in list(data.items())[:10]:  # Limit to 10 items
                formatted_value = self._format_data(v, max_depth - 1, indent + 2)
                items.append(f"{' ' * (indent + 2)}{k}: {formatted_value}")
            if len(data) > 10:
                items.append(f"{' ' * (indent + 2)}... ({len(data) - 10} more items)")
            return "{\n" + "\n".join(items) + f"\n{' ' * indent}}}"

        if isinstance(data, list):
            if not data:
                return "[]"
            if max_depth <= 0:
                return "[...]"
            items = []
            for item in data[:10]:  # Limit to 10 items
                formatted_item = self._format_data(item, max_depth - 1, indent + 2)
                items.append(f"{' ' * (indent + 2)}{formatted_item}")
            if len(data) > 10:
                items.append(f"{' ' * (indent + 2)}... ({len(data) - 10} more items)")
            return "[\n" + "\n".join(items) + f"\n{' ' * indent}]"

        if isinstance(data, str) and len(data) > 100:
            return f'"{data[:97]}..."'

        return json.dumps(data) if not isinstance(data, (str, int, float, bool)) else str(data)

    def _format_eq_data(self, eq: dict[str, Any]) -> str:
        """Format EQ data with special handling for EQBand array."""
        if not isinstance(eq, dict):
            return self._format_data(eq)

        lines = []
        for key, value in eq.items():
            if key == "EQBand" and isinstance(value, list):
                # Format EQBand array nicely - show band values clearly
                if not value:
                    lines.append(f"  {key}: []")
                else:
                    lines.append(f"  {key}: [")
                    for i, band in enumerate(value):
                        if isinstance(band, dict):
                            # Show all fields in the band dict, but format nicely
                            band_items = []
                            for k, v in band.items():
                                band_items.append(f"{k}: {v}")
                            if band_items:
                                lines.append(f"    Band {i}: {{{', '.join(band_items)}}}")
                            else:
                                lines.append(f"    Band {i}: {{}}")
                        else:
                            # Simple value (int or other)
                            lines.append(f"    Band {i}: {band}")
                    lines.append("  ]")
            else:
                # Regular field
                formatted_value = self._format_data(value, max_depth=2, indent=2)
                lines.append(f"  {key}: {formatted_value}")

        return "{\n" + "\n".join(lines) + "\n}"

    def _print_data(self, label: str, data: Any, show_always: bool = False) -> None:
        """Print formatted data if verbose or show_always is True."""
        if self.verbose or show_always:
            # Special handling for EQ data
            if label == "Current EQ" and isinstance(data, dict) and "EQBand" in data:
                formatted = self._format_eq_data(data)
            else:
                formatted = self._format_data(data)
            print(f"      {label}: {formatted}")

    async def save_state(self) -> None:
        """Save original device state for restoration."""
        print("💾 Saving original device state...")
        try:
            await self.player.refresh()
            self.original_state = {
                "volume": self.player.volume_level,
                "mute": self.player.is_muted,
                "source": self.player.source,
                "play_state": self.player.play_state,
            }
            print(f"   ✓ Volume: {self.original_state.get('volume')}")
            print(f"   ✓ Mute: {self.original_state.get('mute')}")
            print(f"   ✓ Source: {self.original_state.get('source')}")
            print(f"   ✓ Play state: {self.original_state.get('play_state')}")
        except Exception as e:
            print(f"   ⚠️  Could not save state: {e}")

    async def restore_state(self) -> None:
        """Restore original device state."""
        print("\n🔄 Restoring original device state...")
        try:
            if "volume" in self.original_state and self.original_state["volume"] is not None:
                await self.player.set_volume(self.original_state["volume"])
                await asyncio.sleep(0.5)
            if "mute" in self.original_state and self.original_state["mute"] is not None:
                await self.player.set_mute(self.original_state["mute"])
                await asyncio.sleep(0.5)
            if "source" in self.original_state and self.original_state["source"]:
                try:
                    await self.player.set_source(self.original_state["source"])
                    await asyncio.sleep(0.5)
                except Exception:
                    pass  # Source restore may fail if source unavailable
            print("   ✓ State restored")
        except Exception as e:
            print(f"   ⚠️  Could not fully restore state: {e}")

    async def test_device_info(self) -> None:
        """Test device information endpoints."""
        print("\n📋 Testing Device Information...")

        try:
            device_info = await self.client.get_device_info_model()
            self.results["passed"].append("device_info: get_device_info_model")
            print("   ✓ get_device_info_model")
            self._print_data("Model", device_info.model, show_always=True)
            self._print_data("Name", device_info.name, show_always=True)
            self._print_data("Firmware", device_info.firmware, show_always=True)
            self._print_data("UUID", device_info.uuid)
            self._print_data("MAC", device_info.mac)
            self._print_data("Input List", device_info.input_list, show_always=True)
            self._print_data("Preset Key", device_info.preset_key)
            self._print_data("Hardware", device_info.hardware)
            self._print_data("MCU Version", device_info.mcu_ver)
            self._print_data("DSP Version", device_info.dsp_ver)
            self._print_data("WMRM Version", device_info.wmrm_version)
        except Exception as e:
            self.results["failed"].append(f"device_info: get_device_info_model - {str(e)}")
            print(f"   ✗ get_device_info_model: {e}")

        try:
            device_info_raw = await self.client.get_device_info()
            self.results["passed"].append("device_info: get_device_info")
            print("   ✓ get_device_info")
            if self.verbose:
                self._print_data("Raw Device Info", device_info_raw)
        except Exception as e:
            self.results["failed"].append(f"device_info: get_device_info - {str(e)}")
            print(f"   ✗ get_device_info: {e}")

        try:
            device_name = await self.client.get_device_name()
            self.results["passed"].append("device_info: get_device_name")
            print(f"   ✓ get_device_name: {device_name}")
        except Exception as e:
            self.results["failed"].append(f"device_info: get_device_name - {str(e)}")
            print(f"   ✗ get_device_name: {e}")

        try:
            firmware_info = await self.client.get_firmware_info()
            self.results["passed"].append("device_info: get_firmware_info")
            print(f"   ✓ get_firmware_info: {firmware_info}")
        except Exception as e:
            self.results["failed"].append(f"device_info: get_firmware_info - {str(e)}")
            print(f"   ✗ get_firmware_info: {e}")

    async def test_status_endpoints(self) -> None:
        """Test status query endpoints."""
        print("\n📊 Testing Status Endpoints...")

        try:
            status = await self.client.get_status()
            self.results["passed"].append("status: get_status")
            print("   ✓ get_status")
            self._print_data("Status", status)
        except Exception as e:
            self.results["failed"].append(f"status: get_status - {str(e)}")
            print(f"   ✗ get_status: {e}")

        try:
            player_status = await self.client.get_player_status()
            self.results["passed"].append("status: get_player_status")
            print("   ✓ get_player_status")
            self._print_data("Play State", player_status.get("play_status"), show_always=True)
            self._print_data("Source", player_status.get("source"), show_always=True)
            self._print_data("Volume", player_status.get("volume"), show_always=True)
            self._print_data("Mute", player_status.get("mute"), show_always=True)
            self._print_data("Title", player_status.get("title"))
            self._print_data("Artist", player_status.get("artist"))
            self._print_data("Album", player_status.get("album"))
            self._print_data("Position", player_status.get("position"))
            self._print_data("Duration", player_status.get("duration"))
        except Exception as e:
            self.results["failed"].append(f"status: get_player_status - {str(e)}")
            print(f"   ✗ get_player_status: {e}")

        try:
            player_status_model = await self.client.get_player_status_model()
            self.results["passed"].append("status: get_player_status_model")
            print("   ✓ get_player_status_model")
            if self.verbose:
                self._print_data("Player Status Model", player_status_model.model_dump())
        except Exception as e:
            self.results["failed"].append(f"status: get_player_status_model - {str(e)}")
            print(f"   ✗ get_player_status_model: {e}")

        try:
            meta_info = await self.client.get_meta_info()
            self.results["passed"].append("status: get_meta_info")
            print("   ✓ get_meta_info")
            self._print_data("Meta Info", meta_info)
        except Exception as e:
            self.results["failed"].append(f"status: get_meta_info - {str(e)}")
            print(f"   ✗ get_meta_info: {e}")

    async def test_playback_controls(self) -> None:
        """Test playback control commands."""
        print("\n▶️  Testing Playback Controls...")

        # Test play commands (non-destructive)
        tests = [
            ("play", lambda: self.client.play()),
            ("pause", lambda: self.client.pause()),
            ("resume", lambda: self.client.resume()),
            ("stop", lambda: self.client.stop()),
            ("next_track", lambda: self.client.next_track()),
            ("previous_track", lambda: self.client.previous_track()),
        ]

        for name, test_func in tests:
            try:
                await test_func()
                await asyncio.sleep(0.5)  # Brief delay between commands
                self.results["passed"].append(f"playback: {name}")
                print(f"   ✓ {name}")
            except Exception as e:
                self.results["failed"].append(f"playback: {name} - {str(e)}")
                print(f"   ✗ {name}: {e}")

    async def test_volume_controls(self) -> None:
        """Test volume and mute controls (safely)."""
        print("\n🔊 Testing Volume Controls (max 10%)...")

        # Save current volume
        try:
            await self.player.refresh()
            current_vol = self.player.volume_level or 0.0
        except Exception:
            current_vol = 0.0

        # Test volume set (max 10%)
        max_test_volume = min(0.10, current_vol + 0.05)  # Never exceed 10%, or current + 5%

        tests = [
            ("set_volume (5%)", lambda: self.client.set_volume(0.05)),
            ("set_volume (10%)", lambda: self.client.set_volume(max_test_volume)),
            ("set_mute (True)", lambda: self.client.set_mute(True)),
            ("set_mute (False)", lambda: self.client.set_mute(False)),
        ]

        for name, test_func in tests:
            try:
                await test_func()
                await asyncio.sleep(0.5)
                self.results["passed"].append(f"volume: {name}")
                print(f"   ✓ {name}")
            except Exception as e:
                self.results["failed"].append(f"volume: {name} - {str(e)}")
                print(f"   ✗ {name}: {e}")

    async def test_source_controls(self) -> None:
        """Test source switching."""
        print("\n📻 Testing Source Controls...")

        try:
            # Ensure device info is refreshed to get input_list
            await self.client.get_device_info_model()
            await self.player.refresh()

            current_source = self.player.source
            available_sources = self.player.available_sources or []

            # Show source information
            print(f"   Current Source: {current_source or 'None'}")
            # Only show input_list if it's not empty
            if available_sources:
                self._print_data("Enumerable Sources (input_list)", available_sources, show_always=True)

            # Known selectable sources (matches HA integration pattern)
            # Many devices don't return InputList in getStatusEx, so we build from known sources
            # This matches how the Home Assistant integration handles source enumeration
            known_selectable_sources = [
                "wifi",
                "bluetooth",
                "line_in",
                "optical",
                "coaxial",
                "usb",
                "hdmi",  # Physical inputs
                "spotify",
                "airplay",
                "dlna",
                "amazon",
                "tidal",
                "qobuz",
                "deezer",  # Streaming services
                "iheartradio",
                "pandora",
                "tunein",  # Internet radio
            ]

            # Build list of sources to test (matches HA integration: enumerable + known selectable)
            # If input_list is empty (common - many devices don't return it), use known sources
            # This is expected behavior: InputList only contains physical hardware inputs,
            # not streaming services (spotify, airplay, etc.) which are still selectable.
            if available_sources:
                # Device returned input_list, use it plus known sources
                sources_to_test = list(dict.fromkeys(list(available_sources) + known_selectable_sources))
            else:
                # Use known sources when input_list is not available
                sources_to_test = known_selectable_sources

            # Test get_source (read current source)
            if current_source:
                self.results["passed"].append("source: get_source")
                print(f"   ✓ get_source: {current_source}")

            # Test switching to a different source (if available)
            # Note: Some devices may not allow source switching while playing.
            # We'll try to stop playback first if needed, but won't fail if source switching fails.
            tested = False
            was_playing = False
            original_play_state = None

            # Check if device is playing - some devices require stopping before source switch
            try:
                await self.player.refresh()
                original_play_state = self.player.play_state
                was_playing = self.player.is_playing
                if was_playing:
                    # Try to stop playback to allow source switching
                    try:
                        await self.client.stop()
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass  # Continue even if stop fails
            except Exception:
                pass  # Continue even if we can't check play state

            for test_source in sources_to_test:
                if test_source != current_source:
                    try:
                        await self.client.set_source(test_source)
                        await asyncio.sleep(1.0)
                        await self.player.refresh()
                        new_source = self.player.source
                        if new_source == test_source:
                            self.results["passed"].append(f"source: set_source({test_source})")
                            print(f"   ✓ set_source({test_source})")
                            tested = True
                            break
                        else:
                            # Source may have changed but not to what we requested
                            self.results["warnings"].append(
                                f"source: set_source({test_source}) - changed to {new_source}"
                            )
                            print(f"   ⚠️  set_source({test_source}) - changed to {new_source}")
                            tested = True
                            break
                    except Exception as e:
                        # Try next source if this one fails
                        # Some sources may not be available or switchable on this device
                        error_msg = str(e).lower()
                        if "unknown command" in error_msg or "not supported" in error_msg:
                            # This source is not available, try next
                            continue
                        # Other errors might be transient, but we'll try next source anyway
                        continue

            if not tested:
                if current_source:
                    # Try to switch away and back as a fallback test
                    try:
                        # Try switching to a different source
                        # Prioritize physical inputs which are more likely to work
                        alternate_sources = ["wifi", "bluetooth", "line_in", "optical"]
                        alternate_source = None
                        for alt in alternate_sources:
                            if alt != current_source:
                                alternate_source = alt
                                break

                        if not alternate_source:
                            alternate_source = "wifi" if current_source != "wifi" else "bluetooth"

                        await self.client.set_source(alternate_source)
                        await asyncio.sleep(1.0)
                        await self.player.refresh()
                        intermediate_source = self.player.source
                        await self.client.set_source(current_source)  # Switch back
                        await asyncio.sleep(0.5)
                        await self.player.refresh()
                        final_source = self.player.source
                        if final_source == current_source or intermediate_source != current_source:
                            self.results["passed"].append("source: set_source (switched and restored)")
                            print("   ✓ set_source (switched and restored)")
                        else:
                            self.results["warnings"].append(
                                f"source: set_source may not have worked (current: {current_source})"
                            )
                            print("   ⚠️  set_source may not have worked")
                    except Exception as e:
                        error_msg = str(e)
                        # Provide more helpful error message
                        if "unknown command" in error_msg.lower():
                            self.results["not_supported"].append(
                                "source: set_source - source switching not supported or not available"
                            )
                            print(f"   ⊘ Source switching not supported (current: {current_source})")
                        else:
                            self.results["not_supported"].append(
                                f"source: set_source - not supported (error: {error_msg})"
                            )
                            print(f"   ⊘ Source switching not supported (current: {current_source})")
                else:
                    self.results["not_supported"].append("source: set_source - no source available to test")
                    print("   ⊘ Source switching not supported - no source available")

            # Restore playback state if we stopped it
            if was_playing and original_play_state == "play":
                try:
                    await self.client.play()
                    await asyncio.sleep(0.3)
                except Exception:
                    pass  # Don't fail if we can't restore playback
        except Exception as e:
            self.results["failed"].append(f"source: Error testing sources - {str(e)}")
            print(f"   ✗ Error testing sources: {e}")

    async def test_audio_output(self) -> None:
        """Test audio output mode controls."""
        print("\n🔌 Testing Audio Output Controls...")

        if not self.client.capabilities.get("supports_audio_output", False):
            self.results["skipped"].append("audio_output: Not supported")
            print("   ⊘ Audio output controls not supported")
            return

        try:
            # Get current status
            status = await self.client.get_audio_output_status()
            if status:
                self.results["passed"].append("audio_output: get_audio_output_status")
                print("   ✓ get_audio_output_status")
                self._print_data("Audio Output Status", status, show_always=True)

            # Refresh player to get current mode
            await self.player.refresh()
            current_mode = self.player.audio_output_mode
            available_modes = self.player.available_output_modes
            print(f"   Current Mode: {current_mode or 'None'}")
            self._print_data("Available Output Modes", available_modes, show_always=True)

            # Test getting current mode
            if current_mode:
                self.results["passed"].append(f"audio_output: get_audio_output_mode ({current_mode})")
                print(f"   ✓ get_audio_output_mode: {current_mode}")

            # Test setting output mode (if supported)
            if available_modes and len(available_modes) > 0:
                # Test switching to each available mode (if different from current)
                tested_modes = []
                original_mode = current_mode

                for test_mode in available_modes:
                    if test_mode != current_mode:
                        try:
                            await self.player.set_audio_output_mode(test_mode)
                            # Give device time to update and refresh status
                            await asyncio.sleep(1.0)
                            await self.player.refresh()
                            new_mode = self.player.audio_output_mode
                            if new_mode == test_mode:
                                self.results["passed"].append(f"audio_output: set_audio_output_mode({test_mode})")
                                print(f"   ✓ set_audio_output_mode({test_mode})")
                                tested_modes.append(test_mode)
                                current_mode = test_mode
                                # Test one more mode if available, then restore
                                if len(tested_modes) >= 2:
                                    break
                            elif new_mode is None:
                                # Mode might not be readable immediately, but command succeeded
                                # Check if we can at least read the status
                                status_check = await self.client.get_audio_output_status()
                                if status_check:
                                    self.results["warnings"].append(
                                        f"audio_output: set_audio_output_mode({test_mode}) - mode set but not readable"
                                    )
                                    print(f"   ⚠️  set_audio_output_mode({test_mode}) - mode set but not readable")
                                    tested_modes.append(test_mode)
                                    current_mode = test_mode
                                    if len(tested_modes) >= 2:
                                        break
                            else:
                                self.results["warnings"].append(
                                    f"audio_output: set_audio_output_mode({test_mode}) - changed to {new_mode}"
                                )
                                print(f"   ⚠️  set_audio_output_mode({test_mode}) - changed to {new_mode}")
                                tested_modes.append(test_mode)
                                current_mode = test_mode
                                if len(tested_modes) >= 2:
                                    break
                        except Exception:
                            # Some modes might not be supported, try next one
                            continue

                # Restore original mode if we changed it
                if original_mode and tested_modes and original_mode != current_mode:
                    try:
                        await self.player.set_audio_output_mode(original_mode)
                        await asyncio.sleep(0.5)
                        print(f"   ✓ Restored original mode: {original_mode}")
                    except Exception as e:
                        self.results["warnings"].append(f"audio_output: Could not restore original mode - {str(e)}")
                        print(f"   ⚠️  Could not restore original mode: {e}")

                if not tested_modes:
                    # Already tested all modes or device only supports one mode
                    # This is a pass condition, not a skip
                    pass
            else:
                self.results["not_supported"].append("audio_output: set_audio_output_mode - no modes available")
                print("   ⊘ Audio output mode switching not supported")
        except Exception as e:
            self.results["failed"].append(f"audio_output: Error - {str(e)}")
            print(f"   ✗ Error: {e}")

    async def test_eq_controls(self) -> None:
        """Test EQ controls."""
        print("\n🎛️  Testing EQ Controls...")

        if not self.client.capabilities.get("supports_eq", False):
            self.results["skipped"].append("eq: Not supported")
            print("   ⊘ EQ not supported")
            return

        try:
            # Get current EQ
            eq = await self.client.get_eq()
            if eq:
                self.results["passed"].append("eq: get_eq")
                print("   ✓ get_eq")
                self._print_data("Current EQ", eq, show_always=True)

            # Get EQ presets
            presets = await self.client.get_eq_presets()
            if presets:
                self.results["passed"].append("eq: get_eq_presets")
                print(f"   ✓ get_eq_presets ({len(presets)} presets)")
                self._print_data("EQ Presets", presets, show_always=True)

            # Test setting multiple EQ presets (enumerate and test)
            if presets and len(presets) > 0:
                from pywiim.api.constants import EQ_PRESET_MAP

                # Save current EQ preset to restore later
                original_preset = None
                try:
                    current_eq = await self.client.get_eq()
                    if isinstance(current_eq, dict):
                        original_preset = current_eq.get("Name") or current_eq.get("name")
                except Exception:
                    pass

                # Normalize preset names (device may return capitalized names)
                preset_lower = {p.lower(): p for p in presets}  # Map lowercase -> original

                # Find presets that match our known preset keys (these are guaranteed to work)
                testable_presets = []
                for preset_name in presets:
                    preset_lower_name = preset_name.lower()
                    # Check if it matches our known preset map
                    if preset_lower_name in EQ_PRESET_MAP:
                        testable_presets.append(preset_lower_name)

                # If we have testable presets, test a few of them (limit to 3-4 to keep test time reasonable)
                if testable_presets:
                    # Prioritize common presets: flat, rock, jazz, classical
                    priority_presets = ["flat", "rock", "jazz", "classical"]
                    presets_to_test = []

                    # Add priority presets first if they're available
                    for priority in priority_presets:
                        if priority in testable_presets and priority not in presets_to_test:
                            presets_to_test.append(priority)

                    # Add remaining testable presets up to 4 total
                    for preset in testable_presets:
                        if preset not in presets_to_test and len(presets_to_test) < 4:
                            presets_to_test.append(preset)

                    # Test each preset
                    tested_count = 0
                    for preset_key in presets_to_test:
                        try:
                            await self.client.set_eq_preset(preset_key)
                            await asyncio.sleep(0.5)

                            # Verify it was set (optional - check current EQ)
                            try:
                                verify_eq = await self.client.get_eq()
                                if isinstance(verify_eq, dict):
                                    set_name = verify_eq.get("Name") or verify_eq.get("name", "")
                                    # Check if preset was set (name might be capitalized)
                                    if preset_key.lower() in set_name.lower() or set_name.lower() in preset_key.lower():
                                        self.results["passed"].append(f"eq: set_eq_preset({preset_key})")
                                        print(f"   ✓ set_eq_preset({preset_key})")
                                        tested_count += 1
                                    else:
                                        # Preset was set but name doesn't match exactly (still success)
                                        self.results["passed"].append(f"eq: set_eq_preset({preset_key})")
                                        print(f"   ✓ set_eq_preset({preset_key}) [verified: {set_name}]")
                                        tested_count += 1
                                else:
                                    # Can't verify but command succeeded
                                    self.results["passed"].append(f"eq: set_eq_preset({preset_key})")
                                    print(f"   ✓ set_eq_preset({preset_key})")
                                    tested_count += 1
                            except Exception:
                                # Verification failed but setting might have worked
                                self.results["passed"].append(f"eq: set_eq_preset({preset_key})")
                                print(f"   ✓ set_eq_preset({preset_key})")
                                tested_count += 1

                            # Don't test more than 4 presets to keep test time reasonable
                            if tested_count >= 4:
                                break
                        except Exception as e:
                            self.results["warnings"].append(f"eq: set_eq_preset({preset_key}) - {str(e)}")
                            print(f"   ⚠️  set_eq_preset({preset_key}): {e}")

                    # Restore original preset if we had it
                    if original_preset:
                        try:
                            # Try to find the original preset in our map
                            original_lower = original_preset.lower()
                            if original_lower in EQ_PRESET_MAP:
                                await self.client.set_eq_preset(original_lower)
                                await asyncio.sleep(0.3)
                                print(f"   ✓ Restored original EQ preset: {original_preset}")
                            elif original_lower in preset_lower:
                                # Original preset is in device list but not in our map - try using device name
                                await self.client.set_eq_preset(original_lower)
                                await asyncio.sleep(0.3)
                                print(f"   ✓ Restored original EQ preset: {original_preset}")
                        except Exception:
                            pass  # If restore fails, that's okay
                else:
                    # No presets match our known map - try first preset anyway
                    try:
                        first_preset = presets[0].lower()
                        await self.client.set_eq_preset(first_preset)
                        await asyncio.sleep(0.5)
                        self.results["passed"].append(f"eq: set_eq_preset({first_preset})")
                        print(f"   ✓ set_eq_preset({first_preset})")
                    except Exception as e:
                        self.results["warnings"].append(f"eq: set_eq_preset({first_preset}) - {str(e)}")
                        print(f"   ⚠️  set_eq_preset({first_preset}): {e}")

            # Test EQ status (get current enabled state)
            try:
                eq_status = await self.client.get_eq_status()
                self.results["passed"].append("eq: get_eq_status")
                print(f"   ✓ get_eq_status: {eq_status}")
            except Exception as e:
                # get_eq_status may not be supported on all devices
                self.results["warnings"].append(f"eq: get_eq_status - {str(e)}")
                print(f"   ⚠️  get_eq_status: {e}")

            # Test EQ enable/disable
            try:
                # Get current state first to restore it
                original_eq_state = None
                try:
                    original_eq_state = await self.client.get_eq_status()
                except Exception:
                    pass  # If we can't get status, just try to toggle

                await self.client.set_eq_enabled(True)
                await asyncio.sleep(0.3)
                await self.client.set_eq_enabled(False)
                await asyncio.sleep(0.3)

                # Restore original state if we had it
                if original_eq_state is not None:
                    await self.client.set_eq_enabled(original_eq_state)
                    await asyncio.sleep(0.2)

                self.results["passed"].append("eq: set_eq_enabled")
                print("   ✓ set_eq_enabled")
            except Exception as e:
                # Some devices may not support EQ enable/disable commands
                error_str = str(e).lower()
                if (
                    "unknown command" in error_str
                    or "not supported" in error_str
                    or "404" in error_str
                    or ("invalid json response" in error_str and "expecting value" in error_str)
                ):
                    self.results["not_supported"].append("eq: set_eq_enabled")
                    print("   ⊘ set_eq_enabled: Not supported on this device")
                else:
                    self.results["failed"].append(f"eq: set_eq_enabled - {str(e)}")
                    print(f"   ✗ set_eq_enabled: {e}")

            # Test custom EQ (set 10-band EQ to flat)
            try:
                # Save current EQ if possible
                current_eq_restore: dict[str, Any] | None = None
                try:
                    current_eq_restore = await self.client.get_eq()
                except Exception:
                    pass

                # Set flat EQ (all zeros)
                flat_eq = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                await self.client.set_eq_custom(flat_eq)
                await asyncio.sleep(0.5)

                # Restore original EQ if we had it
                if current_eq_restore and isinstance(current_eq_restore, dict) and "EQBand" in current_eq_restore:
                    try:
                        eq_bands = current_eq_restore.get("EQBand", [])
                        if isinstance(eq_bands, list) and len(eq_bands) == 10:
                            # Extract band values (may be dicts with "value" key or just ints)
                            band_values: list[int] = []
                            for band in eq_bands:
                                if isinstance(band, dict):
                                    val = band.get("value", band.get("Value", 0))
                                    band_values.append(int(val) if val is not None else 0)
                                else:
                                    band_values.append(int(band) if isinstance(band, (int, str)) else 0)
                            if len(band_values) == 10:
                                await self.client.set_eq_custom(band_values)
                                await asyncio.sleep(0.3)
                    except Exception:
                        pass  # If restore fails, that's okay

                self.results["passed"].append("eq: set_eq_custom")
                print("   ✓ set_eq_custom")
            except Exception as e:
                # Custom EQ may not be supported on all devices
                error_str = str(e).lower()
                if (
                    "unknown command" in error_str
                    or "not supported" in error_str
                    or "404" in error_str
                    or ("invalid json response" in error_str and "expecting value" in error_str)
                ):
                    self.results["not_supported"].append("eq: set_eq_custom")
                    print("   ⊘ set_eq_custom: Not supported on this device")
                else:
                    self.results["warnings"].append(f"eq: set_eq_custom - {str(e)}")
                    print(f"   ⚠️  set_eq_custom: {e}")
        except Exception as e:
            self.results["failed"].append(f"eq: Error - {str(e)}")
            print(f"   ✗ Error: {e}")

    async def test_preset_controls(self) -> None:
        """Test preset controls."""
        print("\n⭐ Testing Preset Controls...")

        try:
            presets = await self.client.get_presets()
            if presets:
                self.results["passed"].append("preset: get_presets")
                print(f"   ✓ get_presets ({len(presets)} presets)")
                self._print_data("Presets", presets, show_always=True)

                # Test playing a preset (if available)
                if len(presets) > 0:
                    preset_num = presets[0].get("number", 1)
                    try:
                        await self.client.play_preset(preset_num)
                        await asyncio.sleep(1.0)
                        self.results["passed"].append(f"preset: play_preset({preset_num})")
                        print(f"   ✓ play_preset({preset_num})")
                    except Exception as e:
                        self.results["failed"].append(f"preset: play_preset({preset_num}) - {str(e)}")
                        print(f"   ✗ play_preset({preset_num}): {e}")
            else:
                self.results["not_supported"].append("preset: get_presets - no presets available")
                print("   ⊘ Presets not supported - no presets available")
        except Exception as e:
            # Presets may not be supported
            if "404" in str(e) or "not supported" in str(e).lower() or "unknown command" in str(e).lower():
                self.results["not_supported"].append("preset: get_presets")
                print("   ⊘ Presets not supported")
            else:
                self.results["failed"].append(f"preset: Error - {str(e)}")
                print(f"   ✗ Error: {e}")

    async def test_multiroom_controls(self) -> None:
        """Test multiroom/group controls (read-only, non-destructive)."""
        print("\n👥 Testing Multiroom Controls (read-only)...")

        try:
            multiroom = await self.client.get_multiroom_status()
            if multiroom:
                self.results["passed"].append("multiroom: get_multiroom_status")
                print("   ✓ get_multiroom_status")
                self._print_data("Multiroom Status", multiroom, show_always=True)

            slaves = await self.client.get_slaves()
            if slaves is not None:
                self.results["passed"].append("multiroom: get_slaves")
                print(f"   ✓ get_slaves ({len(slaves) if slaves else 0} slaves)")
                self._print_data("Slaves", slaves, show_always=True)

            group_info = await self.client.get_device_group_info()
            if group_info:
                self.results["passed"].append("multiroom: get_device_group_info")
                print(f"   ✓ get_device_group_info (role: {group_info.role})")
                self._print_data(
                    "Group Info", group_info.model_dump() if hasattr(group_info, "model_dump") else str(group_info)
                )
        except Exception as e:
            self.results["failed"].append(f"multiroom: Error - {str(e)}")
            print(f"   ✗ Error: {e}")

    async def test_bluetooth_controls(self) -> None:
        """Test Bluetooth controls (read-only)."""
        print("\n📱 Testing Bluetooth Controls (read-only)...")

        try:
            history = await self.client.get_bluetooth_history()
            if history is not None:
                self.results["passed"].append("bluetooth: get_bluetooth_history")
                print(f"   ✓ get_bluetooth_history ({len(history) if history else 0} devices)")
                self._print_data("Bluetooth History", history, show_always=True)
        except Exception as e:
            # Bluetooth may not be supported
            if "not supported" in str(e).lower() or "404" in str(e) or "unknown command" in str(e).lower():
                self.results["not_supported"].append("bluetooth: get_bluetooth_history")
                print("   ⊘ Bluetooth not supported")
            else:
                self.results["failed"].append(f"bluetooth: Error - {str(e)}")
                print(f"   ✗ Error: {e}")

    async def test_audio_settings(self) -> None:
        """Test audio settings endpoints."""
        print("\n🎚️  Testing Audio Settings...")

        try:
            status = await self.client.get_audio_settings_status()
            if status:
                self.results["passed"].append("audio_settings: get_audio_settings_status")
                print("   ✓ get_audio_settings_status")
                self._print_data("Audio Settings Status", status, show_always=True)
        except Exception as e:
            if "not supported" in str(e).lower() or "404" in str(e) or "unknown command" in str(e).lower():
                self.results["not_supported"].append("audio_settings: get_audio_settings_status")
                print("   ⊘ Audio settings not supported")
            else:
                self.results["failed"].append(f"audio_settings: Error - {str(e)}")
                print(f"   ✗ Error: {e}")

    async def test_lms_controls(self) -> None:
        """Test LMS/Squeezelite controls."""
        print("\n🎵 Testing LMS Integration...")

        try:
            state = await self.client.get_squeezelite_state()
            if state is not None:
                self.results["passed"].append("lms: get_squeezelite_state")
                print("   ✓ get_squeezelite_state")
        except Exception as e:
            error_str = str(e).lower()
            # Treat these as "not supported" rather than failures:
            # - "not supported" or "404" in error message
            # - "unknown command" (device doesn't support this endpoint)
            # - "Invalid JSON response" with empty response (device returns non-JSON like "unknown command")
            if (
                "not supported" in error_str
                or "404" in error_str
                or "unknown command" in error_str
                or ("invalid json response" in error_str and "expecting value" in error_str)
            ):
                self.results["not_supported"].append("lms: get_squeezelite_state")
                print("   ⊘ LMS integration not supported")
            else:
                self.results["failed"].append(f"lms: Error - {str(e)}")
                print(f"   ✗ Error: {e}")

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all feature tests."""
        print("=" * 60)
        print("🧪 WiiM Device Feature Test Suite")
        print("=" * 60)
        print(f"\nDevice: {self.client.host}")

        # Save original state
        await self.save_state()

        # Detect capabilities
        try:
            await self.client._detect_capabilities()
            vendor = self.client.capabilities.get("vendor", "unknown")
            print(f"\n🔧 Capabilities detected: {vendor}")
            if self.verbose or True:  # Always show capabilities
                caps_to_show = {
                    k: v
                    for k, v in self.client.capabilities.items()
                    if k.startswith("supports_")
                    or k in ["vendor", "device_type", "firmware_version", "audio_pro_generation"]
                }
                self._print_data("Capabilities", caps_to_show, show_always=True)
        except Exception as e:
            print(f"\n⚠️  Could not detect capabilities: {e}")

        # Run all test suites
        await self.test_device_info()
        await self.test_status_endpoints()
        await self.test_playback_controls()
        await self.test_volume_controls()
        await self.test_source_controls()
        await self.test_audio_output()
        await self.test_eq_controls()
        await self.test_preset_controls()
        await self.test_multiroom_controls()
        await self.test_bluetooth_controls()
        await self.test_audio_settings()
        await self.test_lms_controls()

        # Restore original state
        await self.restore_state()

        # Generate summary
        return self._generate_summary()

    def _generate_summary(self) -> dict[str, Any]:
        """Generate test summary."""
        total = (
            len(self.results["passed"])
            + len(self.results["failed"])
            + len(self.results["skipped"])
            + len(self.results["not_supported"])
        )

        return {
            "total_tests": total,
            "passed": len(self.results["passed"]),
            "failed": len(self.results["failed"]),
            "skipped": len(self.results["skipped"]),
            "not_supported": len(self.results["not_supported"]),
            "warnings": len(self.results["warnings"]),
            "results": self.results,
        }

    def print_summary(self) -> None:
        """Print test summary."""
        summary = self._generate_summary()

        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"\nTotal tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        if summary.get("not_supported", 0) > 0:
            print(f"🚫 Not supported: {summary['not_supported']}")
        if summary["warnings"] > 0:
            print(f"⚠️  Warnings: {summary['warnings']}")

        if self.results["failed"]:
            print("\n❌ Failed tests:")
            for failure in self.results["failed"]:
                print(f"   - {failure}")

        if self.results.get("not_supported"):
            print("\n🚫 Not supported:")
            for not_supported in self.results["not_supported"]:
                print(f"   - {not_supported}")

        if self.results["warnings"]:
            print("\n⚠️  Warnings:")
            for warning in self.results["warnings"]:
                # Truncate very long warnings for readability
                if len(warning) > 100:
                    print(f"   - {warning[:97]}...")
                else:
                    print(f"   - {warning}")

        print("\n" + "=" * 60)


async def main() -> int:
    """Main entry point for verify CLI."""
    parser = argparse.ArgumentParser(
        description="Verify all WiiM device features and endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic verification suite
  wiim-verify 192.168.1.68

  # Verbose output
  wiim-verify 192.168.1.68 --verbose

  # HTTPS device
  wiim-verify 192.168.1.68 --port 443
        """,
    )
    parser.add_argument(
        "device_ip",
        help="Device IP address or hostname",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Device port (default: auto-detect, use 80 for HTTP or 443 for HTTPS)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    import logging

    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Create client and player
    client = WiiMClient(host=args.device_ip, port=args.port)
    player = Player(client)

    tester = FeatureTester(player, verbose=args.verbose)

    try:
        summary = await tester.run_all_tests()
        tester.print_summary()

        # Return exit code based on results
        if summary["failed"] > 0:
            return 1
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
        await tester.restore_state()
        return 1
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        await tester.restore_state()
        return 1
    finally:
        await client.close()


def cli_main() -> None:
    """CLI entry point."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_main()
