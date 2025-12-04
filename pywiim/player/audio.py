"""Audio configuration - EQ, output modes, LED, etc."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import Player

_LOGGER = logging.getLogger(__name__)


class AudioConfiguration:
    """Manages audio configuration."""

    def __init__(self, player: Player) -> None:
        """Initialize audio configuration.

        Args:
            player: Parent Player instance.
        """
        self.player = player

    async def set_source(self, source: str) -> None:
        """Set audio input source.

        Args:
            source: Source to switch to.
        """
        # Call API (raises on failure)
        await self.player.client.set_source(source)

        # Update cached state immediately (optimistic)
        # If API returns success, we trust the device changed
        if self.player._status_model:
            self.player._status_model.source = source.lower()

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def set_audio_output_mode(self, mode: str | int) -> None:
        """Set audio output mode by friendly name or integer.

        Args:
            mode: Either a friendly name string or mode integer (0-4).
        """
        # Call API (raises on failure)
        await self.player.client.set_audio_output_mode(mode)

        # Refresh to update audio output status cache
        # Use full=True to ensure audio output status is fetched
        await self.player.refresh(full=True)

        # Call callback to notify state change (audio output status changed)
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def select_output(self, output: str) -> None:
        """Select an output by name (hardware mode or specific BT device).

        This method handles both hardware output modes and specific Bluetooth devices:
        - Hardware modes: "Line Out", "Optical Out", "Coax Out", "Headphone Out"
        - BT devices: "BT: Device Name" (must be already paired)
        - "Bluetooth Out": Activates last connected BT device

        When selecting a BT device:
        1. Connects to the specific device (this automatically activates BT output mode)

        Args:
            output: Output name from available_outputs list

        Raises:
            ValueError: If output name is not recognized or device not paired

        Example:
            # Select hardware output
            await player.audio.select_output("Optical Out")
            await player.audio.select_output("Headphone Out")

            # Select specific BT device
            await player.audio.select_output("BT: Sony Speaker")
        """
        # Check if it's a Bluetooth device selection
        if output.startswith("BT: "):
            device_name = output[4:]  # Remove "BT: " prefix

            # Find the device in paired devices
            bt_devices = self.player._properties.bluetooth_output_devices
            matching_device = None
            for device in bt_devices:
                if device["name"] == device_name:
                    matching_device = device
                    break

            if not matching_device:
                raise ValueError(
                    f"Bluetooth device '{device_name}' not found in paired devices. "
                    f"Available BT devices: {[d['name'] for d in bt_devices]}"
                )

            # Connect to the specific device (this automatically activates BT output mode)
            await self.player.connect_bluetooth_device(matching_device["mac"])

        elif output.lower() in ("bluetooth out", "bluetooth"):
            # Generic Bluetooth Out - connect to the last connected device
            bt_devices = self.player._properties.bluetooth_output_devices
            if not bt_devices:
                raise ValueError("No paired Bluetooth devices found. Pair a device first.")

            # Find the last connected device (ct=1) or first in list
            last_device = next((d for d in bt_devices if d.get("connected")), bt_devices[0])
            await self.player.connect_bluetooth_device(last_device["mac"])

        else:
            # It's a hardware output mode (Line Out, Optical Out, Coax Out, Headphone Out, etc.)
            # If Bluetooth is currently active, disconnect it first
            if self.player.is_bluetooth_output_active:
                try:
                    await self.player.disconnect_bluetooth_device()
                except Exception:
                    # If disconnect fails, continue anyway - the hardware mode change might still work
                    pass

            # Set the hardware output mode
            await self.set_audio_output_mode(output)

    async def set_led(self, enabled: bool) -> None:
        """Set LED on/off state.

        Args:
            enabled: True to enable LED, False to disable.
        """
        await self.player.client.set_led(enabled)

    async def set_led_brightness(self, brightness: int) -> None:
        """Set LED brightness level.

        Args:
            brightness: Brightness level from 0 to 100.
        """
        if not 0 <= brightness <= 100:
            raise ValueError(f"Brightness must be between 0 and 100, got {brightness}")
        await self.player.client.set_led_brightness(brightness)

    async def set_channel_balance(self, balance: float) -> None:
        """Set channel balance (left/right stereo balance).

        Args:
            balance: Balance value from -1.0 to 1.0.
        """
        if not -1.0 <= balance <= 1.0:
            raise ValueError(f"Balance must be between -1.0 and 1.0, got {balance}")
        await self.player.client.set_channel_balance(balance)

    async def set_eq_preset(self, preset: str) -> None:
        """Set equalizer preset.

        Args:
            preset: Preset name. Can be any case (e.g., "jazz", "Jazz", "JAZZ")
                   or display name from get_eq_presets() (e.g., "Jazz").
                   The method normalizes the preset name internally.
        """
        import asyncio
        import time

        # Normalize preset name using client's normalization (handles any case)
        normalized_preset = self.player.client._normalize_eq_preset_name(preset)

        # Call API (raises on failure)
        await self.player.client.set_eq_preset(preset)

        # Update cached state immediately (optimistic) with normalized preset
        if self.player._status_model:
            self.player._status_model.eq_preset = normalized_preset

        # Track when EQ was set for preserving optimistic update during refresh
        # Device status endpoint returns stale EQ data for many seconds
        self.player._last_eq_preset_set_time = time.time()

        # Verify by querying the authoritative EQ endpoint after a brief delay
        # This ensures we have the correct value even if status endpoint is stale
        try:
            await asyncio.sleep(0.3)  # Brief delay for device to apply
            eq_data = await self.player.client.get_eq()
            verified_preset = eq_data.get("Name") or eq_data.get("name")
            if verified_preset and self.player._status_model:
                self.player._status_model.eq_preset = verified_preset
                _LOGGER.debug("EQ preset verified: %s", verified_preset)
        except Exception as err:
            # If verification fails, keep the optimistic update
            _LOGGER.debug("EQ verification failed, keeping optimistic value: %s", err)

        # Call callback to notify state change
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def set_eq_custom(self, eq_values: list[int]) -> None:
        """Set custom 10-band equalizer values.

        Args:
            eq_values: List of exactly 10 integer values.
        """
        # Call API (raises on failure)
        await self.player.client.set_eq_custom(eq_values)

        # Call callback to notify state change (EQ values changed)
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def set_eq_enabled(self, enabled: bool) -> None:
        """Enable or disable the equalizer.

        Args:
            enabled: True to enable EQ, False to disable.
        """
        # Call API (raises on failure)
        await self.player.client.set_eq_enabled(enabled)

        # Call callback to notify state change (EQ enabled/disabled)
        if self.player._on_state_changed:
            self.player._on_state_changed()

    async def get_eq(self) -> dict[str, Any]:
        """Get current equalizer band values."""
        return await self.player.client.get_eq()

    async def get_eq_presets(self) -> list[str]:
        """Get list of available equalizer presets."""
        return await self.player.client.get_eq_presets()

    async def get_eq_status(self) -> bool:
        """Get current equalizer enabled status."""
        return await self.player.client.get_eq_status()

    async def get_multiroom_status(self) -> dict[str, Any]:
        """Get multiroom group status information."""
        return await self.player.client.get_multiroom_status()

    async def get_audio_output_status(self) -> dict[str, Any] | None:
        """Get current audio output status.

        Fetches audio output status from the device and updates the player's
        internal cache so that audio_output_mode property works correctly.

        Returns:
            Dict with audio output info (hardware, source, etc.), or None if not supported.
        """
        status = await self.player.client.get_audio_output_status()
        # Update player's internal cache so audio_output_mode property works
        self.player._audio_output_status = status
        return status

    async def get_meta_info(self) -> dict[str, Any]:
        """Get detailed metadata information about current track."""
        return await self.player.client.get_meta_info()
