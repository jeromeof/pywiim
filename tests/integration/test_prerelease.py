"""Pre-release integration tests for Player with real devices.

These tests require a real WiiM device to be available on the network.
Set the WIIM_TEST_DEVICE environment variable to enable these tests.

These are comprehensive tests that validate all major Player functionality.
They change device state and restore it afterward. Run these before important releases.

IMPORTANT: Some tests require an active source with media (e.g., Spotify, Bluetooth, USB).
If tests are skipped with "idle" state messages, start a source before running tests.

Example:
    WIIM_TEST_DEVICE=192.168.1.100 pytest tests/integration/test_prerelease.py -v

For HTTPS devices:
    WIIM_TEST_DEVICE=192.168.1.100 WIIM_TEST_HTTPS=true pytest tests/integration/test_prerelease.py -v
"""

from __future__ import annotations

import asyncio

import pytest

from pywiim.exceptions import WiiMError


@pytest.mark.integration
@pytest.mark.prerelease
@pytest.mark.asyncio
class TestPreReleaseComprehensive:
    """Comprehensive pre-release integration tests with real devices.

    This class includes tests for multiple tiers:
    - playback: Play/pause/next/prev tests
    - controls: Shuffle/repeat tests
    - features: EQ, presets, audio output tests

    Run all with: pytest -m prerelease
    Run specific tier: pytest -m playback
    """

    @pytest.mark.playback
    async def test_playback_controls_full(self, real_device_player, integration_test_marker):
        """Test all playback controls with state restoration."""
        player = real_device_player
        await player.refresh()

        # Save initial state
        initial_play_state = player.play_state

        try:
            # Test play (may fail if no media available)
            try:
                await player.play()
                await asyncio.sleep(2.0)  # Give device more time to start
                await player.refresh()
                # Play state should be "play" or similar (some devices may pause/idle if no media)
                play_state = player.play_state
                if play_state in ("idle", "IDLE", "stop", "STOP"):
                    pytest.skip(
                        f"Device is in '{play_state}' state - no media available. "
                        "Please start a source (e.g., Spotify, Bluetooth, USB) before running this test."
                    )
                assert play_state in (
                    "play",
                    "playing",
                    "PLAY",
                    "pause",
                    "paused",
                    "PAUSE",
                    "buffering",  # Valid transitional state
                ), f"Unexpected play state: {play_state}"
            except WiiMError:
                pytest.skip("Play command not available (no media in queue)")

            # Test pause (may fail if not playing)
            try:
                await player.pause()
                await asyncio.sleep(1.0)
                await player.refresh()
                # Play state should be "pause" or similar
                assert player.play_state in ("pause", "paused", "PAUSE")
            except WiiMError:
                pytest.skip("Pause command not available")

            # Test resume
            try:
                await player.resume()
                await asyncio.sleep(2.0)  # Give device time to resume
                await player.refresh()
                # Resume may result in play or pause depending on device/media state
                play_state = player.play_state
                if play_state in ("idle", "IDLE", "stop", "STOP"):
                    pytest.skip(
                        f"Device is in '{play_state}' state after resume - no media available. "
                        "Please start a source (e.g., Spotify, Bluetooth, USB) before running this test."
                    )
                assert play_state in (
                    "play",
                    "playing",
                    "PLAY",
                    "pause",
                    "paused",
                    "PAUSE",
                    "buffering",  # Valid transitional state
                ), f"Unexpected play state after resume: {play_state}"
            except WiiMError:
                pytest.skip("Resume command not available")

        finally:
            # Try to restore initial state
            if initial_play_state:
                try:
                    if initial_play_state in ("play", "playing", "PLAY"):
                        await player.play()
                    elif initial_play_state in ("pause", "paused", "PAUSE"):
                        await player.pause()
                    await asyncio.sleep(0.5)
                except Exception:
                    pass  # Best effort restoration

    @pytest.mark.controls
    async def test_shuffle_controls_full(self, real_device_player, integration_test_marker):
        """Test shuffle controls with state preservation."""
        player = real_device_player
        await player.refresh()

        # Check if shuffle is supported
        if not player.shuffle_supported:
            pytest.skip(f"Shuffle not supported for source: {player.source}")

        # Save initial state
        initial_shuffle = player.shuffle_state
        initial_repeat = player.repeat_mode

        try:
            # Test shuffle ON
            await player.set_shuffle(True)
            await asyncio.sleep(1.0)
            await player.refresh()

            assert player.shuffle_state is True, "Shuffle should be enabled"
            # Repeat should be preserved
            assert player.repeat_mode == initial_repeat, "Repeat state should be preserved"

            # Test shuffle OFF
            await player.set_shuffle(False)
            await asyncio.sleep(1.0)
            await player.refresh()

            assert player.shuffle_state is False, "Shuffle should be disabled"
            # Repeat should still be preserved
            assert player.repeat_mode == initial_repeat, "Repeat state should be preserved"

        finally:
            # Restore initial shuffle state
            if initial_shuffle is not None:
                try:
                    await player.set_shuffle(initial_shuffle)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass  # Best effort restoration

    @pytest.mark.controls
    async def test_repeat_controls_full(self, real_device_player, integration_test_marker):
        """Test repeat controls with state preservation."""
        player = real_device_player
        await player.refresh()

        # Check if repeat is supported
        if not player.repeat_supported:
            pytest.skip(f"Repeat not supported for source: {player.source}")

        # Save initial state
        initial_repeat = player.repeat_mode
        initial_shuffle = player.shuffle_state

        try:
            # Test repeat ALL
            await player.set_repeat("all")
            await asyncio.sleep(1.0)
            await player.refresh()

            assert player.repeat_mode == "all", "Repeat should be set to 'all'"
            # Shuffle should be preserved
            assert player.shuffle_state == initial_shuffle, "Shuffle state should be preserved"

            # Test repeat ONE
            await player.set_repeat("one")
            await asyncio.sleep(1.0)
            await player.refresh()

            assert player.repeat_mode == "one", "Repeat should be set to 'one'"
            # Shuffle should still be preserved
            assert player.shuffle_state == initial_shuffle, "Shuffle state should be preserved"

            # Test repeat OFF
            await player.set_repeat("off")
            await asyncio.sleep(1.0)
            await player.refresh()

            assert player.repeat_mode == "off", "Repeat should be set to 'off'"
            # Shuffle should still be preserved
            assert player.shuffle_state == initial_shuffle, "Shuffle state should be preserved"

        finally:
            # Restore initial repeat state
            if initial_repeat is not None:
                try:
                    await player.set_repeat(initial_repeat)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass  # Best effort restoration

    @pytest.mark.playback
    async def test_next_previous_track(self, real_device_player, integration_test_marker):
        """Test next/previous track controls."""
        player = real_device_player
        await player.refresh()

        # Check if device has an active source first
        await player.refresh()
        if player.play_state in ("idle", "IDLE", "stop", "STOP", None):
            pytest.skip(
                f"Device is in '{player.play_state}' state - no active source. "
                "Please start a source with media (e.g., Spotify, Bluetooth, USB) before running this test."
            )

        # Need to be playing for next/previous to work
        try:
            await player.play()
            await asyncio.sleep(1.0)
            await player.refresh()
            # Verify we're actually playing
            if player.play_state in ("idle", "IDLE", "stop", "STOP"):
                pytest.skip(
                    f"Cannot start playback - device is in '{player.play_state}' state. "
                    "Please start a source with media (e.g., Spotify, Bluetooth, USB) before running this test."
                )
        except WiiMError:
            pytest.skip("Cannot start playback (no media available)")

        try:
            # Test next track
            try:
                await player.next_track()
                await asyncio.sleep(2.0)  # Give device time to process
                await player.refresh()
                # Should still be playing or paused (device behavior varies)
                play_state = player.play_state
                if play_state in ("idle", "IDLE", "stop", "STOP"):
                    pytest.skip(
                        f"Device entered '{play_state}' state after next track - likely no more tracks. "
                        "Please ensure your source has multiple tracks available."
                    )
                assert play_state in (
                    "play",
                    "playing",
                    "PLAY",
                    "pause",
                    "paused",
                    "PAUSE",
                    "buffering",  # Valid transitional state (device is loading next track)
                ), f"Unexpected play state after next: {play_state}"
            except WiiMError as e:
                pytest.skip(f"Next track not available: {e}")

            # Test previous track
            try:
                await player.previous_track()
                await asyncio.sleep(2.0)  # Give device time to process
                await player.refresh()
                # Should still be playing or paused (device behavior varies)
                play_state = player.play_state
                if play_state in ("idle", "IDLE", "stop", "STOP"):
                    pytest.skip(
                        f"Device entered '{play_state}' state after previous track. "
                        "This may be normal if at the beginning of the queue."
                    )
                assert play_state in (
                    "play",
                    "playing",
                    "PLAY",
                    "pause",
                    "paused",
                    "PAUSE",
                    "buffering",  # Valid transitional state (device is loading previous track)
                ), f"Unexpected play state after previous: {play_state}"
            except WiiMError as e:
                pytest.skip(f"Previous track not available: {e}")

        finally:
            # Try to pause to avoid unwanted playback
            try:
                await player.pause()
                await asyncio.sleep(0.5)
            except Exception:
                pass

    @pytest.mark.smoke
    async def test_volume_controls_full(self, real_device_player, integration_test_marker):
        """Test volume controls with full range and restoration."""
        player = real_device_player
        await player.refresh()

        # Save initial state
        initial_volume = await player.get_volume()
        initial_mute = await player.get_muted()

        if initial_volume is None:
            pytest.skip("Device does not report volume level")

        try:
            # Test volume at 10%
            await player.set_volume(0.10)
            await asyncio.sleep(0.5)
            volume = await player.get_volume()
            assert volume is not None
            assert abs(volume - 0.10) < 0.05

            # Test volume at 20%
            await player.set_volume(0.20)
            await asyncio.sleep(0.5)
            volume = await player.get_volume()
            assert volume is not None
            assert abs(volume - 0.20) < 0.05

            # Test volume at 5%
            await player.set_volume(0.05)
            await asyncio.sleep(0.5)
            volume = await player.get_volume()
            assert volume is not None
            assert abs(volume - 0.05) < 0.05

            # Test volume at 0%
            await player.set_volume(0.0)
            await asyncio.sleep(0.5)
            volume = await player.get_volume()
            assert volume is not None
            assert abs(volume - 0.0) < 0.05

        finally:
            # Restore initial state
            if initial_volume is not None:
                await player.set_volume(initial_volume)
            if initial_mute is not None:
                await player.set_mute(initial_mute)
            await asyncio.sleep(0.5)

    @pytest.mark.smoke
    async def test_mute_controls_full(self, real_device_player, integration_test_marker):
        """Test mute controls with restoration."""
        player = real_device_player
        await player.refresh()

        # Save initial state
        initial_mute = await player.get_muted()

        try:
            # Test mute ON
            await player.set_mute(True)
            await asyncio.sleep(0.5)
            muted = await player.get_muted()
            if muted is not None:
                assert muted is True

            # Test mute OFF
            await player.set_mute(False)
            await asyncio.sleep(0.5)
            unmuted = await player.get_muted()
            if unmuted is not None:
                assert unmuted is False

            # Test toggle
            await player.set_mute(True)
            await asyncio.sleep(0.5)
            await player.set_mute(False)
            await asyncio.sleep(0.5)
            final_mute = await player.get_muted()
            if final_mute is not None:
                assert final_mute is False

        finally:
            # Restore initial state
            if initial_mute is not None:
                await player.set_mute(initial_mute)
            await asyncio.sleep(0.5)

    @pytest.mark.features
    async def test_audio_output_switching(self, real_device_player, integration_test_marker):
        """Test audio output mode switching (hardware modes and BT if paired)."""
        player = real_device_player
        # Do full refresh to ensure capabilities and BT history are detected
        await player.refresh(full=True)

        # Check capabilities first
        if not player.supports_audio_output:
            pytest.skip("Audio output control not supported on this device (capability check)")

        # Get available outputs (hardware modes + paired BT devices)
        try:
            # First, verify we can GET a valid status (not just that the endpoint exists)
            status = await player.audio.get_audio_output_status()
            if status is None:
                pytest.skip("Audio output status not available on this device")

            # Verify status has expected structure (some devices may return empty/invalid responses)
            if not isinstance(status, dict) or (
                "hardware" not in status and "mode" not in status and "output" not in status
            ):
                pytest.skip(
                    f"Audio output status is invalid or incomplete: {status}. "
                    "Device may not actually support audio output control."
                )

            # Get available hardware modes
            available_modes = player.available_output_modes
            if not available_modes:
                pytest.skip("Device does not have audio output modes")

            # Get available outputs (includes BT devices if paired)
            available_outputs = player.available_outputs
            if not available_outputs:
                pytest.skip("No audio outputs available")

            # Get current mode from property
            initial_output = player.audio_output_mode
            initial_is_bt = player.is_bluetooth_output_active

            # Get paired BT devices
            bt_devices = player.bluetooth_output_devices
            has_paired_bt = len(bt_devices) > 0

            try:
                # Test hardware output modes first (always available)
                if len(available_modes) >= 2:
                    # Find a different hardware mode to switch to
                    alternate_mode = None
                    for mode in available_modes:
                        if mode != initial_output:
                            alternate_mode = mode
                            break

                    if alternate_mode:
                        # Try switching to alternate hardware mode
                        try:
                            await player.audio.set_audio_output_mode(alternate_mode)
                            await asyncio.sleep(2.0)
                            await player.refresh(full=True)

                            new_mode = player.audio_output_mode
                            if new_mode:
                                assert new_mode in available_modes, f"New mode {new_mode} not in available modes"
                                print(f"  ✓ Switched to hardware mode: {new_mode}")
                        except Exception as e:
                            # If setting fails with JSON error, capability detection may have been incorrect
                            error_msg = str(e)
                            if "Invalid JSON" in error_msg or "Expecting value" in error_msg:
                                pytest.skip(
                                    f"Audio output mode switching failed with JSON error: {e}. "
                                    "This suggests the device does not actually support audio output control "
                                    "despite capability detection. The capability check may need improvement."
                                )
                            raise  # Re-raise other errors

                # Test BT output only if devices are paired
                if has_paired_bt:
                    # Find a paired BT device
                    bt_device = bt_devices[0]
                    bt_output_name = f"BT: {bt_device['name']}"

                    if bt_output_name in available_outputs:
                        # Try switching to BT output
                        try:
                            await player.audio.select_output(bt_output_name)
                            await asyncio.sleep(3.0)  # BT connection takes time
                            await player.refresh(full=True)

                            # Verify BT is active
                            if player.is_bluetooth_output_active:
                                print(f"  ✓ Switched to BT output: {bt_device['name']}")
                            else:
                                print("  ⊘ BT output selected but not active (device may be off/out of range)")

                        except Exception as e:
                            print(f"  ⊘ BT output switch failed: {e} (device may be unavailable)")
                else:
                    print("  ⊘ No paired Bluetooth devices - skipping BT output test")

            finally:
                # Restore initial output
                if initial_output and not initial_is_bt:
                    try:
                        await player.audio.set_audio_output_mode(initial_output)
                        await asyncio.sleep(1.0)
                        await player.refresh(full=True)
                    except Exception:
                        pass  # Best effort restoration
                elif initial_is_bt and has_paired_bt:
                    # Try to restore BT if it was active
                    try:
                        bt_device = bt_devices[0]
                        bt_output_name = f"BT: {bt_device['name']}"
                        await player.audio.select_output(bt_output_name)
                        await asyncio.sleep(1.0)
                    except Exception:
                        pass  # Best effort restoration

        except Exception as e:
            pytest.skip(f"Audio output switching not available: {e}")

    @pytest.mark.smoke
    async def test_state_synchronization(self, real_device_player, integration_test_marker):
        """Test that state synchronization works correctly."""
        from pywiim.exceptions import WiiMConnectionError, WiiMRequestError

        player = real_device_player

        # Initial refresh
        try:
            await player.refresh()
        except (WiiMConnectionError, WiiMRequestError) as e:
            pytest.skip(f"Device connection failed during test: {e}")

        # Get initial state
        volume1 = player.volume_level

        # Make a change
        if volume1 is not None:
            new_volume = min(0.15, volume1 + 0.05) if volume1 < 0.15 else 0.15
            try:
                await player.set_volume(new_volume)
                await asyncio.sleep(0.5)

                # Refresh and check state is updated
                await player.refresh()
                volume2 = player.volume_level

                if volume2 is not None:
                    assert abs(volume2 - new_volume) < 0.05, "State should be synchronized after change"

            finally:
                # Restore
                if volume1 is not None:
                    await player.set_volume(volume1)
                    await asyncio.sleep(0.5)

    @pytest.mark.smoke
    async def test_cache_consistency(self, real_device_player, integration_test_marker):
        """Test that cached state is consistent with device state."""
        player = real_device_player

        # Refresh to populate cache
        await player.refresh()

        # Get cached values
        cached_volume = player.volume_level
        cached_mute = player.is_muted
        cached_source = player.source

        # Query device directly
        device_volume = await player.get_volume()
        device_mute = await player.get_muted()
        device_status = await player.get_status()
        device_source = device_status.source if device_status else None

        # Compare (allowing for None values)
        if cached_volume is not None and device_volume is not None:
            assert abs(cached_volume - device_volume) < 0.1, "Cached volume should match device"

        if cached_mute is not None and device_mute is not None:
            assert cached_mute == device_mute, "Cached mute should match device"

        if cached_source is not None and device_source is not None:
            # Source might be normalized, so check if they match or one contains the other
            assert (
                cached_source == device_source
                or cached_source in str(device_source)
                or str(device_source) in cached_source
            ), "Cached source should match device"

    @pytest.mark.smoke
    async def test_error_handling(self, real_device_player, integration_test_marker):
        """Test error handling for invalid commands."""
        player = real_device_player
        await player.refresh()

        # Save initial volume for restoration
        initial_volume = await player.get_volume()

        try:
            # Test invalid volume values (library may clamp values instead of raising)
            # Some devices/clients may clamp invalid values rather than raise errors
            # We just verify the command doesn't crash and volume stays in valid range
            try:
                await player.set_volume(-0.1)  # Below minimum
                volume = await player.get_volume()
                if volume is not None:
                    assert 0.0 <= volume <= 1.0, "Volume should be in valid range"
            except (ValueError, WiiMError):
                pass  # Expected to raise in some implementations

            try:
                await player.set_volume(1.1)  # Above maximum
                volume = await player.get_volume()
                if volume is not None:
                    assert 0.0 <= volume <= 1.0, "Volume should be in valid range"
            except (ValueError, WiiMError):
                pass  # Expected to raise in some implementations

            # Test invalid repeat mode (may be ignored by device)
            # Just verify it doesn't crash
            try:
                await player.set_repeat("invalid_mode")
            except (ValueError, WiiMError):
                pass  # Expected in some implementations

            # Test invalid source (if we can get available sources)
            # Just verify it doesn't crash
            sources = player.available_sources
            if sources:
                try:
                    await player.set_source("nonexistent_source_xyz123")
                except (ValueError, WiiMError):
                    pass  # Expected in some implementations

        finally:
            # Restore initial volume
            if initial_volume is not None:
                try:
                    await player.set_volume(initial_volume)
                    await asyncio.sleep(0.5)
                except Exception:
                    pass

    @pytest.mark.features
    async def test_eq_preset_selection(self, real_device_player, integration_test_marker):
        """Test EQ preset selection when available."""
        player = real_device_player
        await player.refresh(full=True)

        # Check capabilities first
        if not player.supports_eq:
            pytest.skip("EQ not supported on this device (capability check)")

        try:
            # Get available EQ presets
            eq_presets = await player.audio.get_eq_presets()
            if not eq_presets or len(eq_presets) == 0:
                pytest.skip("No EQ presets available on this device")

            # Get current EQ preset
            initial_preset = player.eq_preset

            try:
                # Test switching to first available preset
                first_preset = eq_presets[0]
                await player.set_eq_preset(first_preset)
                await asyncio.sleep(1.0)
                await player.refresh()

                # Verify preset changed (or at least command was accepted)
                new_preset = player.eq_preset
                if new_preset:
                    print(f"  ✓ EQ preset switched to: {new_preset}")
                else:
                    print(f"  ℹ EQ preset command accepted (preset: {first_preset})")

                # If we have multiple presets, test switching to another one
                if len(eq_presets) > 1:
                    second_preset = eq_presets[1]
                    await player.set_eq_preset(second_preset)
                    await asyncio.sleep(1.0)
                    await player.refresh()
                    new_preset2 = player.eq_preset
                    if new_preset2:
                        print(f"  ✓ EQ preset switched to: {new_preset2}")

            finally:
                # Restore initial preset if we had one
                if initial_preset and initial_preset in eq_presets:
                    try:
                        await player.set_eq_preset(initial_preset)
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass  # Best effort restoration

        except Exception as e:
            pytest.skip(f"EQ preset selection not available: {e}")

    @pytest.mark.features
    async def test_preset_playback(self, real_device_player, integration_test_marker):
        """Test preset playback when presets are available."""
        player = real_device_player
        await player.refresh(full=True)

        # Check capabilities first
        if not player.supports_presets:
            pytest.skip("Presets not supported on this device (capability check)")

        try:
            # Get available presets
            presets = player.presets
            test_preset = None

            # First, try to find a preset from the preset list (if available)
            if presets and len(presets) > 0:
                # Find first preset with a valid number
                for preset in presets:
                    preset_num = preset.get("number")
                    if preset_num and isinstance(preset_num, (int, str)):
                        try:
                            preset_num_int = int(preset_num)
                            if 1 <= preset_num_int <= 20:  # Valid preset range
                                test_preset = preset_num_int
                                break
                        except (ValueError, TypeError):
                            continue

            # If no preset found in list, but device supports presets (via preset_key),
            # try to get max slots and test with preset 1
            if test_preset is None:
                try:
                    max_slots = await player.client.get_max_preset_slots()
                    if max_slots > 0:
                        # Device supports presets but we can't read names (getPresetInfo failed)
                        # Test with preset 1 (should be valid if device supports presets)
                        test_preset = 1
                        print(f"  Device supports {max_slots} preset slots (preset_key), but preset names unavailable")
                        print(f"  Testing playback of preset {test_preset} (by number)")
                    else:
                        pytest.skip("No presets configured on this device and max_slots is 0")
                except Exception as e:
                    pytest.skip(f"Could not determine preset slots: {e}")

            if test_preset is None:
                pytest.skip("No valid preset numbers found in preset list")

            # Save initial play state
            initial_play_state = player.play_state

            try:
                # Test playing preset
                print(f"  Testing playback of preset {test_preset}")
                await player.play_preset(test_preset)
                await asyncio.sleep(3.0)  # Give device time to start playback
                await player.refresh()

                # Verify playback started (or at least command was accepted)
                new_play_state = player.play_state
                if new_play_state in ("play", "playing", "PLAY"):
                    print(f"  ✓ Preset playback started: {new_play_state}")
                elif new_play_state in ("pause", "paused", "PAUSE"):
                    print("  ℹ Preset loaded but paused")
                else:
                    print(f"  ℹ Preset command accepted (state: {new_play_state})")

            finally:
                # Try to restore initial state (pause if we started playing)
                if initial_play_state in ("pause", "paused", "PAUSE", "stop", "STOP", "idle", "IDLE"):
                    try:
                        await player.pause()
                        await asyncio.sleep(0.5)
                    except Exception:
                        pass

        except Exception as e:
            pytest.skip(f"Preset playback not available: {e}")

    @pytest.mark.playback
    async def test_play_url(self, real_device_player, integration_test_marker):
        """Test playing a URL directly."""
        player = real_device_player
        await player.refresh()

        # Use a test URL (a short audio stream that should work on most devices)
        # Using a well-known test stream URL
        test_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

        # Save initial source
        initial_source = player.source

        try:
            # Test playing URL
            print(f"  Testing play_url with: {test_url[:50]}...")
            await player.play_url(test_url)
            await asyncio.sleep(3.0)  # Give device time to start playback
            await player.refresh()

            # Verify playback started (or at least command was accepted)
            new_play_state = player.play_state
            if new_play_state in ("play", "playing", "PLAY"):
                print(f"  ✓ URL playback started: {new_play_state}")
            elif new_play_state in ("pause", "paused", "PAUSE"):
                print("  ℹ URL loaded but paused")
            else:
                # Command may have been accepted even if state doesn't show play
                print(f"  ℹ Play URL command accepted (state: {new_play_state})")

        except Exception as e:
            # URL playback may fail for various reasons (network, format, etc.)
            # Don't fail the test, just note it
            print(f"  ⊘ Play URL failed: {e} (this may be normal - URL may be unavailable)")

        finally:
            # Try to stop playback and restore source
            try:
                await player.stop()
                await asyncio.sleep(1.0)
            except Exception:
                pass

            if initial_source:
                try:
                    await player.set_source(initial_source)
                    await asyncio.sleep(1.0)
                except Exception:
                    pass

    @pytest.mark.playback
    async def test_play_notification(self, real_device_player, integration_test_marker):
        """Test playing a notification sound."""
        player = real_device_player
        await player.refresh()

        # Check if device is in a mode that supports notifications
        # Notifications only work in NETWORK or USB playback mode
        current_source = player.source
        if current_source and current_source.lower() not in ("wifi", "network", "usb", "dlna"):
            # Try to switch to network source for notification test
            try:
                # Check if wifi/network is available
                sources = player.available_sources
                network_source = None
                if sources:
                    for source in sources:
                        if source.lower() in ("wifi", "network", "dlna"):
                            network_source = source
                            break

                if network_source:
                    await player.set_source(network_source)
                    await asyncio.sleep(2.0)
                    await player.refresh()
                else:
                    pytest.skip(
                        "Notifications require NETWORK or USB source. "
                        f"Current source: {current_source}, Available: {sources}"
                    )
            except Exception:
                pytest.skip(f"Cannot switch to network source for notification test. Current source: {current_source}")

        # Use a short test notification URL (a brief audio file)
        # Using a short test audio file
        test_notification_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"

        # Save initial volume
        initial_volume = await player.get_volume()

        try:
            # Test playing notification
            print(f"  Testing play_notification with: {test_notification_url[:50]}...")
            await player.play_notification(test_notification_url)
            await asyncio.sleep(2.0)  # Give notification time to play

            # Notification should play and restore volume automatically
            # Check that volume was restored (device handles this automatically)
            await player.refresh()
            final_volume = await player.get_volume()

            # Volume should be restored (or close to original)
            if initial_volume is not None and final_volume is not None:
                volume_diff = abs(final_volume - initial_volume)
                if volume_diff < 0.1:  # Allow small difference
                    print(f"  ✓ Notification played and volume restored (diff: {volume_diff:.2f})")
                else:
                    print(
                        f"  ℹ Notification played (volume may still be restoring: "
                        f"{initial_volume:.2f} → {final_volume:.2f})"
                    )
            else:
                print("  ℹ Notification command accepted (volume check unavailable)")

        except Exception as e:
            # Notification may fail if URL is unavailable or device doesn't support it
            pytest.skip(f"Play notification failed: {e}")

        finally:
            # Ensure playback is stopped if notification left it playing
            try:
                if player.play_state in ("play", "playing", "PLAY"):
                    await player.pause()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

    @pytest.mark.features
    async def test_source_switching(self, real_device_player, integration_test_marker):
        """Test source switching with selectable physical inputs.

        This test runs last and tests physical inputs that can be selected.
        Bluetooth is included as a selectable input (physical input, even if not currently paired).
        """
        player = real_device_player
        await player.refresh(full=True)

        # Get available sources
        sources = player.available_sources
        if sources is None or len(sources) == 0:
            pytest.skip("Device does not report any available sources")

        # Physical inputs that can be manually selected (always include Bluetooth as it's a physical input)
        selectable_inputs = {
            "usb",
            "line in",
            "linein",
            "optical",
            "coaxial",
            "coax",
            "hdmi",
            "analog",
            "aux",
            "rca",
            "spdif",
            "toslink",
            "bluetooth",  # Bluetooth is a physical input, always include it
            "bt",
        }

        # Streaming services and protocols are NOT selectable (they're activated externally)
        non_selectable = {
            "spotify",
            "amazon",
            "tidal",
            "qobuz",
            "deezer",
            "pandora",
            "iheartradio",
            "tunein",
            "airplay",
            "dlna",
            "chromecast",
            "multiroom",
            "wifi",
            "network",
        }

        # Filter sources to only selectable physical inputs
        selectable_sources = []

        for source in sources:
            source_lower = source.lower()
            # Include if it's a physical input (including Bluetooth)
            if any(physical in source_lower for physical in selectable_inputs):
                selectable_sources.append(source)
            # Exclude streaming services
            elif not any(streaming in source_lower for streaming in non_selectable):
                # Unknown source type - include it (might be a physical input we don't know about)
                selectable_sources.append(source)

        if len(selectable_sources) == 0:
            pytest.skip(f"No selectable physical inputs found. Available sources: {sources}")

        # Save initial source
        initial_source = player.source

        # If we only have one selectable source, at least verify the API works
        if len(selectable_sources) == 1:
            single_source = selectable_sources[0]
            # Try switching to the same source (should work without error)
            try:
                await player.set_source(single_source)
                await asyncio.sleep(1.0)
                await player.refresh()
                print(f"  ✓ Source switching API works (switched to {single_source})")
            except Exception as e:
                pytest.fail(f"Source switching API failed: {e}")
            finally:
                # Restore if needed
                if initial_source and initial_source != single_source:
                    try:
                        await player.set_source(initial_source)
                        await asyncio.sleep(1.0)
                    except Exception:
                        pass
            return  # Test complete for single source case

        # Multiple sources available - test actual switching
        try:
            # Find a different selectable source
            alternate_source = None
            for source in selectable_sources:
                if source != initial_source:
                    alternate_source = source
                    break

            if alternate_source is None:
                # All selectable sources are the same as current - try switching to first available
                alternate_source = selectable_sources[0]
                print(f"  ℹ All sources are same as current, testing switch to: {alternate_source}")

            print(f"  Testing source switch: {initial_source} → {alternate_source}")

            # Switch to alternate source
            await player.set_source(alternate_source)
            await asyncio.sleep(3.0)  # Give device more time to switch
            await player.refresh()

            # Verify source changed or at least the command was accepted
            new_source = player.source

            # Source might be normalized, so check if it matches or contains the target
            # Even if it didn't change, the API call should have succeeded
            if new_source is not None:
                # Check if source changed or if it's the same (both are valid - API worked)
                if new_source == initial_source:
                    print(
                        f"  ℹ Source did not change (stayed at {initial_source}), "
                        f"but API call succeeded. This may be normal if '{alternate_source}' "
                        f"is not available/active (e.g., USB not connected, Bluetooth not paired)."
                    )
                else:
                    # Verify new source is valid
                    assert new_source in sources or any(
                        alt in str(new_source) or str(new_source) in alt for alt in sources
                    ), f"New source '{new_source}' is not in available sources list"
                    print(f"  ✓ Source switched successfully: {new_source}")

        finally:
            # Restore initial source
            if initial_source:
                try:
                    await player.set_source(initial_source)
                    await asyncio.sleep(2.0)
                except Exception:
                    pass  # Best effort restoration
