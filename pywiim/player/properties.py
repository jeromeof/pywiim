"""Property getters for player state and metadata."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from ..device_capabilities import filter_plm_inputs, get_device_inputs

if TYPE_CHECKING:
    from . import Player

_LOGGER = logging.getLogger(__name__)


class PlayerProperties:
    """Provides property access to player state and metadata."""

    def __init__(self, player: Player) -> None:
        """Initialize properties.

        Args:
            player: Parent Player instance.
        """
        self.player = player

    # === Volume and Mute ===

    @property
    def volume_level(self) -> float | None:
        """Current volume level (0.0-1.0) from merged HTTP/UPnP state."""
        # Always read from state synchronizer (merges HTTP polling + UPnP events)
        merged = self.player._state_synchronizer.get_merged_state()
        volume = merged.get("volume")
        if volume is not None:
            return max(0.0, min(float(volume), 100.0)) / 100.0

        # Fallback to cached status if synchronizer has no data yet
        if self.player._status_model is None or self.player._status_model.volume is None:
            return None
        return max(0.0, min(float(self.player._status_model.volume), 100.0)) / 100.0

    @property
    def is_muted(self) -> bool | None:
        """Current mute state from merged HTTP/UPnP state."""
        # Always read from state synchronizer (merges HTTP polling + UPnP events)
        merged = self.player._state_synchronizer.get_merged_state()
        mute_val = merged.get("muted")

        # If not in merged state, fall back to cached status
        if mute_val is None and self.player._status_model is not None:
            mute_val = self.player._status_model.mute

        if mute_val is None:
            return None

        if isinstance(mute_val, (bool, int)):
            return bool(int(mute_val))

        mute_str = str(mute_val).strip().lower()
        if mute_str in ("1", "true", "yes", "on"):
            return True
        if mute_str in ("0", "false", "no", "off"):
            return False
        return None

    # === Playback State ===

    @property
    def play_state(self) -> str | None:
        """Current playback state from merged HTTP/UPnP state."""
        # Always read from state synchronizer (merges HTTP polling + UPnP events)
        merged = self.player._state_synchronizer.get_merged_state()
        play_state: str | None = merged.get("play_state")
        if play_state is not None:
            return play_state

        # Fallback to cached status if synchronizer has no data yet
        if self.player._status_model is None:
            return None
        return self.player._status_model.play_state

    # === Media Metadata ===

    def _status_field(self, *names: str) -> str | None:
        """Return the first non-empty attribute from merged state or cached status."""
        # First try merged state (combines HTTP + UPnP)
        merged = self.player._state_synchronizer.get_merged_state()
        for n in names:
            val = merged.get(n)
            if val is not None:
                if isinstance(val, str) and val.strip().lower() in {"unknown", "unknow", "none"}:
                    continue
                if val not in (None, ""):
                    return str(val) if val is not None else None

        # Fallback to cached status if synchronizer has no data yet
        if self.player._status_model is None:
            return None

        for n in names:
            if hasattr(self.player._status_model, n):
                val = getattr(self.player._status_model, n)
                if isinstance(val, str) and val.strip().lower() in {"unknown", "unknow", "none"}:
                    continue
                if val not in (None, ""):
                    return str(val) if val is not None else None
        return None

    @property
    def media_title(self) -> str | None:
        """Current track title from cached status."""
        return self._status_field("title")

    @property
    def media_artist(self) -> str | None:
        """Current track artist from cached status."""
        return self._status_field("artist")

    @property
    def media_album(self) -> str | None:
        """Current track album from cached status."""
        return self._status_field("album", "album_name")

    @property
    def media_duration(self) -> int | None:
        """Current track duration in seconds from cached status."""
        duration = self._status_field("duration")
        try:
            if duration is not None:
                result = int(float(duration))
                if result == 0:
                    return None
                return result
            return None
        except (TypeError, ValueError):
            return None

    @property
    def media_position(self) -> int | None:
        """Current playback position in seconds with hybrid estimation.

        Position estimation is handled by StateSynchronizer, which combines
        HTTP polling data and UPnP events, then estimates position between
        updates when playing.
        """
        # StateSynchronizer already does position estimation - just read it
        merged = self.player._state_synchronizer.get_merged_state()
        position = merged.get("position")

        if position is not None:
            try:
                pos_value = int(float(position))
                if pos_value < 0:
                    return None

                # Clamp to duration if available
                duration_value = self.media_duration
                if duration_value is not None and duration_value > 0:
                    if pos_value > duration_value:
                        pos_value = duration_value

                return pos_value
            except (TypeError, ValueError):
                return None

        return None

    @property
    def media_position_updated_at(self) -> float | None:
        """Timestamp when media position was last updated.

        Returns the timestamp from StateSynchronizer which tracks when position
        was last updated from HTTP or UPnP sources.
        """
        # Get the full state object with timestamp information
        state_obj = self.player._state_synchronizer.get_state_object()

        # Return the position field's timestamp if available
        if state_obj.position and state_obj.position.timestamp:
            return state_obj.position.timestamp

        # Fallback to current time if no position data
        return time.time()

    @property
    def media_image_url(self) -> str | None:
        """Media image URL from cached status."""
        return self._status_field("entity_picture", "cover_url")

    @property
    def media_sample_rate(self) -> int | None:
        """Audio sample rate in Hz from metadata."""
        if self.player._metadata is None:
            return None
        meta_data = self.player._metadata.get("metaData", {})
        # API uses camelCase (sampleRate), but support both formats
        sample_rate = meta_data.get("sampleRate") or meta_data.get("sample_rate")
        if sample_rate is None:
            return None
        try:
            return int(sample_rate)
        except (TypeError, ValueError):
            return None

    @property
    def media_bit_depth(self) -> int | None:
        """Audio bit depth in bits from metadata."""
        if self.player._metadata is None:
            return None
        meta_data = self.player._metadata.get("metaData", {})
        # API uses camelCase (bitDepth), but support both formats
        bit_depth = meta_data.get("bitDepth") or meta_data.get("bit_depth")
        if bit_depth is None:
            return None
        try:
            return int(bit_depth)
        except (TypeError, ValueError):
            return None

    @property
    def media_bit_rate(self) -> int | None:
        """Audio bit rate in kbps from metadata."""
        if self.player._metadata is None:
            return None
        meta_data = self.player._metadata.get("metaData", {})
        # API uses camelCase (bitRate), but support both formats
        bit_rate = meta_data.get("bitRate") or meta_data.get("bit_rate")
        if bit_rate is None:
            return None
        try:
            return int(bit_rate)
        except (TypeError, ValueError):
            return None

    @property
    def media_codec(self) -> str | None:
        """Audio codec from status (e.g., 'flac', 'mp3', 'aac')."""
        if self.player._status_model is None:
            return None
        return getattr(self.player._status_model, "codec", None)

    @property
    def source(self) -> str | None:
        """Current source from merged HTTP/UPnP state."""
        # Always read from state synchronizer (merges HTTP polling + UPnP events)
        merged = self.player._state_synchronizer.get_merged_state()
        source: str | None = merged.get("source")
        if source is not None:
            return source

        # Fallback to cached status if synchronizer has no data yet
        if self.player._status_model is None:
            return None
        return self.player._status_model.source

    # === Shuffle and Repeat Support ===

    def _is_device_controlled_source(self) -> bool:
        """Check if current source allows device-controlled playback (shuffle/repeat).

        Returns:
            True if the WiiM device controls playback (can set shuffle/repeat).
            False if an external device/app controls playback (AirPlay, Bluetooth, etc.).
        """
        source = self.source
        if source is None:
            return False

        source_lower = source.lower()

        # Sources where WiiM device controls playback
        device_controlled = {
            "usb",  # Local USB storage
            "line_in",  # Analog input (if device supports playback control)
            "optical",  # Digital optical input
            "coaxial",  # Digital coaxial input
            "playlist",  # Device playlists
            "preset",  # Saved presets
            "http",  # HTTP streaming
            "udisk",  # USB disk (some devices report as "udisk")
        }

        # External sources where source device/app controls playback
        external_controlled = {
            "airplay",  # iOS/macOS controls shuffle/repeat
            "bluetooth",  # Source device controls shuffle/repeat
            "dlna",  # Source app controls shuffle/repeat
            "chromecast",  # Casting app controls shuffle/repeat
            "spotify",  # Spotify app controls (even via Spotify Connect)
            "tidal",  # Tidal app controls
            "amazon",  # Amazon Music app controls
            "qobuz",  # Qobuz app controls
            "deezer",  # Deezer app controls
            "iheartradio",  # iHeartRadio app controls
            "pandora",  # Pandora app controls
            "tunein",  # TuneIn app controls
            "multiroom",  # Slave device, can't control playback
        }

        # Check explicit lists first
        if source_lower in device_controlled:
            return True
        if source_lower in external_controlled:
            return False

        # Default: assume external control for unknown sources (conservative)
        # This prevents misleading shuffle/repeat controls for new sources
        _LOGGER.debug(
            "Unknown source '%s' - assuming external control (shuffle/repeat not supported). "
            "Please report this source to the library maintainers.",
            source,
        )
        return False

    @property
    def shuffle_supported(self) -> bool:
        """Whether shuffle can be controlled by the device in current state.

        Returns False for external sources (AirPlay, Bluetooth, DLNA, streaming services)
        where the source device/app controls shuffle, not the WiiM device.

        Example:
            ```python
            if player.shuffle_supported:
                await player.set_shuffle(True)
                print(f"Shuffle: {player.shuffle_state}")
            else:
                print("Shuffle controlled by source app")
            ```
        """
        return self._is_device_controlled_source()

    @property
    def repeat_supported(self) -> bool:
        """Whether repeat mode can be controlled by the device in current state.

        Returns False for external sources (AirPlay, Bluetooth, DLNA, streaming services)
        where the source device/app controls repeat, not the WiiM device.

        Example:
            ```python
            if player.repeat_supported:
                await player.set_repeat("all")
                print(f"Repeat: {player.repeat_mode}")
            else:
                print("Repeat controlled by source app")
            ```
        """
        return self._is_device_controlled_source()

    # === Shuffle and Repeat ===

    @property
    def shuffle_state(self) -> bool | None:
        """Shuffle state, or None if not controlled by device.

        Returns None for external sources (AirPlay, Bluetooth, etc.) where
        the WiiM device doesn't control shuffle. Check shuffle_supported first.
        """
        if not self.shuffle_supported:
            return None

        if self.player._status_model is None:
            return None

        shuffle_val = getattr(self.player._status_model, "shuffle", None)
        if shuffle_val is not None:
            if isinstance(shuffle_val, (bool, int)):
                return bool(int(shuffle_val))
            shuffle_str = str(shuffle_val).strip().lower()
            return shuffle_str in {"1", "true", "shuffle"}

        loop_mode = getattr(self.player._status_model, "loop_mode", None)
        if loop_mode is not None:
            try:
                loop_val = int(loop_mode)
                is_shuffle = bool(loop_val & 4)
                return is_shuffle
            except (TypeError, ValueError):
                pass

        play_mode = getattr(self.player._status_model, "play_mode", None)
        if play_mode is not None:
            mode_str = str(play_mode).strip().lower()
            return "shuffle" in mode_str

        return None

    @property
    def repeat_mode(self) -> str | None:
        """Repeat mode ('one', 'all', 'off'), or None if not controlled by device.

        Returns None for external sources (AirPlay, Bluetooth, etc.) where
        the WiiM device doesn't control repeat. Check repeat_supported first.
        """
        if not self.repeat_supported:
            return None

        if self.player._status_model is None:
            return None

        repeat_val = getattr(self.player._status_model, "repeat", None)
        if repeat_val is not None:
            repeat_str = str(repeat_val).strip().lower()
            if repeat_str in {"one", "single", "repeat_one", "repeatone", "1"}:
                return "one"
            elif repeat_str in {"all", "repeat_all", "repeatall", "2"}:
                return "all"
            else:
                return "off"

        loop_mode = getattr(self.player._status_model, "loop_mode", None)
        if loop_mode is not None:
            try:
                loop_val = int(loop_mode)
                is_repeat_one = bool(loop_val & 1)
                is_repeat_all = bool(loop_val & 2)

                # Validate: both bits should never be set simultaneously (invalid state)
                if is_repeat_one and is_repeat_all:
                    _LOGGER.warning(
                        "Invalid loop_mode %d: both repeat_one and repeat_all bits set. " "Defaulting to 'one'",
                        loop_val,
                    )
                    return "one"

                if is_repeat_one:
                    return "one"
                elif is_repeat_all:
                    return "all"
                else:
                    # Neither bit set (normal mode) - explicitly return "off"
                    return "off"
            except (TypeError, ValueError):
                pass

        play_mode = getattr(self.player._status_model, "play_mode", None)
        if play_mode is not None:
            mode_str = str(play_mode).strip().lower()
            if "repeat_one" in mode_str or mode_str in {"one", "single"}:
                return "one"
            elif "repeat_all" in mode_str or mode_str in {"all"}:
                return "all"
            elif "repeat" in mode_str and "shuffle" not in mode_str:
                return "all"

        return "off"

    @property
    def eq_preset(self) -> str | None:
        """Current EQ preset from cached status."""
        if self.player._status_model is None:
            return None
        return self.player._status_model.eq_preset

    @property
    def shuffle(self) -> bool | None:
        """Shuffle state from cached status (alias for shuffle_state)."""
        return self.shuffle_state

    @property
    def repeat(self) -> str | None:
        """Repeat mode from cached status (alias for repeat_mode)."""
        return self.repeat_mode

    @property
    def wifi_rssi(self) -> int | None:
        """Wi-Fi signal strength (RSSI) from cached status."""
        if self.player._status_model is None:
            return None
        return self.player._status_model.wifi_rssi

    # === Available Sources and Outputs ===

    @property
    def available_sources(self) -> list[str] | None:
        """Available input sources from cached device info.

        Returns user-selectable physical inputs plus the current source (if active):

        - Always included: Physical/hardware inputs (Line In, USB, Bluetooth,
          Optical, Coaxial, HDMI, etc.) - these can be manually selected by the user
        - Conditionally included: Current source (when active) - includes streaming
          services (AirPlay, Spotify, Amazon, etc.) and multi-room follower sources
          (e.g., "Master Bedroom"). These are NOT user-selectable but are included
          for correct UI state display
        - NOT included: Inactive streaming services - these can't be manually selected
          and aren't currently playing

        plm_support is the source of truth for physical inputs. input_list is
        used to augment with additional sources when available.
        """
        if self.player._device_info is None:
            return None

        # Streaming services and protocols that are externally activated
        streaming_services = {
            "amazon",
            "spotify",
            "tidal",
            "qobuz",
            "deezer",
            "pandora",
            "iheartradio",
            "tunein",
            "airplay",
            "dlna",
        }

        # Get current source to potentially include if it's a streaming service
        current_source = None
        if self.player._status_model is not None:
            current_source = self.player._status_model.source

        # Start with physical_inputs from plm_support (source of truth)
        physical_inputs = []

        # Parse plm_support bitmask - this is the source of truth for physical inputs
        if self.player._device_info.plm_support is not None:
            try:
                if isinstance(self.player._device_info.plm_support, str):
                    plm_value = (
                        int(self.player._device_info.plm_support.replace("0x", "").replace("0X", ""), 16)
                        if "x" in self.player._device_info.plm_support.lower()
                        else int(self.player._device_info.plm_support)
                    )
                else:
                    plm_value = int(self.player._device_info.plm_support)

                # Parse bitmask to get physical inputs (plm_support is source of truth)
                # Bit mappings per Arylic/LinkPlay documentation (1-based in docs, 0-based in code):
                # bit1 (bit 0): LineIn (Aux support)
                # bit2 (bit 1): Bluetooth support
                # bit3 (bit 2): USB support
                # bit4 (bit 3): Optical support
                # bit6 (bit 5): Coaxial support
                # bit8 (bit 7): LineIn 2 support
                # bit15 (bit 14): USBDAC support (not a selectable source, informational only)
                # Note: Newer devices (e.g., WiiM Ultra) may use additional bits for new inputs (e.g., phono, HDMI)
                if plm_value & (1 << 0):  # bit1: LineIn
                    physical_inputs.append("line_in")
                if plm_value & (1 << 1):  # bit2: Bluetooth
                    physical_inputs.append("bluetooth")
                if plm_value & (1 << 2):  # bit3: USB
                    physical_inputs.append("usb")
                if plm_value & (1 << 3):  # bit4: Optical
                    physical_inputs.append("optical")
                if plm_value & (1 << 5):  # bit6: Coaxial
                    physical_inputs.append("coaxial")
                if plm_value & (1 << 7):  # bit8: LineIn 2
                    physical_inputs.append("line_in_2")
                # Note: bit15 (USBDAC) is not a selectable source, so we don't add it to the list

                # Check for additional bits that might be set (for newer devices like WiiM Ultra)
                # Log all set bits for debugging to identify new bit mappings
                all_set_bits = []
                for bit_pos in range(16):  # Check bits 0-15
                    if plm_value & (1 << bit_pos):
                        all_set_bits.append(f"bit{bit_pos + 1} (bit {bit_pos})")

                if len(all_set_bits) > len(physical_inputs) + 1:  # +1 for USBDAC which we don't add
                    unknown_bits = [
                        b
                        for b in all_set_bits
                        if b
                        not in [
                            "bit1 (bit 0)",
                            "bit2 (bit 1)",
                            "bit3 (bit 2)",
                            "bit4 (bit 3)",
                            "bit6 (bit 5)",
                            "bit8 (bit 7)",
                            "bit15 (bit 14)",
                        ]
                    ]
                    if unknown_bits:
                        _LOGGER.debug(
                            "plm_support has unknown set bits (may indicate new inputs like phono/HDMI): %s",
                            ", ".join(unknown_bits),
                        )

                _LOGGER.debug(
                    "Parsed plm_support: value=%s (0x%x), detected inputs (before filtering): %s, all set bits: %s",
                    self.player._device_info.plm_support,
                    plm_value,
                    physical_inputs,
                    ", ".join(all_set_bits),
                )

                # Filter out spurious inputs based on device model (some devices report incorrect bits)
                # E.g., WiiM Pro reports USB bit but has no USB audio input (USB-C is power only)
                physical_inputs = filter_plm_inputs(physical_inputs, plm_value, self.player._device_info.model)
                if len(physical_inputs) < len(all_set_bits) - 1:  # Some bits were filtered
                    _LOGGER.debug("After device-specific filtering: %s", physical_inputs)
            except (ValueError, TypeError) as e:
                _LOGGER.warning(
                    "Failed to parse plm_support value '%s' for device %s: %s",
                    self.player._device_info.plm_support,
                    self.player.host,
                    e,
                )

        # Augment with input_list for:
        # 1. Current streaming service (if active)
        # 2. Physical inputs missing from plm_support (plm_support may be incomplete in some firmware)
        # plm_support is source of truth, but input_list can fill gaps when plm_support is incomplete
        if self.player._device_info.input_list is not None:
            # Normalize physical_inputs to lowercase set for quick lookup
            physical_inputs_lower = {s.lower() for s in physical_inputs}

            for source in self.player._device_info.input_list:
                if not source:
                    continue

                source_lower = source.lower()

                # Skip wifi variations (unless it's the current source)
                if source_lower == "wifi":
                    if current_source and source_lower == current_source.lower():
                        physical_inputs.append(source)
                    continue

                # Include current source even if it's a streaming service (for state display)
                if current_source and source_lower == current_source.lower():
                    physical_inputs.append(source)
                    continue

                # Skip streaming services and protocols (externally activated)
                # Only include if it's the current source (already handled above)
                if any(svc in source_lower for svc in streaming_services):
                    continue

                # Known physical input names (to identify physical inputs vs streaming services)
                # Includes all physical inputs that may appear in input_list but not in plm_support
                # Note: Some inputs are device-specific (e.g., "phono" is WiiM Ultra only),
                # but it's safe to include them here since they'll only be added if actually
                # present in the device's input_list
                known_physical_input_names = {
                    "line_in",
                    "linein",
                    "aux",
                    "optical",
                    "coaxial",
                    "coax",
                    "usb",
                    "bluetooth",
                    "hdmi",
                    "line_in_2",
                    "linein_2",
                    "phono",  # Phono input (WiiM Ultra specific, but safe to include for all devices)
                }

                # If it's a known physical input and not already in our list, add it
                # This handles cases where plm_support is incomplete but input_list has the inputs
                if source_lower in known_physical_input_names and source_lower not in physical_inputs_lower:
                    physical_inputs.append(source)
                    physical_inputs_lower.add(source_lower)
                    _LOGGER.debug(
                        "Added physical input '%s' from input_list (not in plm_support) for device %s",
                        source,
                        self.player.host,
                    )

        # Augment with device capability database when input_list is not available or empty after filtering
        # plm_support is incomplete/unreliable for both WiiM AND Arylic devices
        # (e.g., Arylic UP2STREAM_AMP_V4 doesn't set line_in bit but has line_in hardware)
        if self.player._device_info.input_list is None or not physical_inputs:
            vendor = self.player.client.capabilities.get("vendor", "").lower() if self.player.client else None
            device_inputs = get_device_inputs(self.player._device_info.model, vendor)

            if device_inputs and device_inputs.inputs:
                _LOGGER.debug(
                    "input_list not available or empty after filtering, "
                    "augmenting with device capability database for %s (vendor: %s)",
                    self.player._device_info.model,
                    vendor,
                )
                # Add model-specific inputs from database (removes duplicates later)
                physical_inputs.extend(device_inputs.inputs)
            elif not physical_inputs:
                # Last resort: no plm_support, no input_list (or all filtered out), no model match
                _LOGGER.debug("No plm_support, input_list, or model match - using default fallback")
                physical_inputs.extend(["bluetooth", "line_in", "optical"])

        # If current source exists and isn't already in our list, add it
        # This handles:
        # - Streaming services when active (AirPlay, Spotify, Amazon, etc.)
        # - Multi-room sources (e.g., device following "Master Bedroom")
        # - Any other non-enumerated sources that are currently playing
        # We include these so the UI can display the current source correctly
        if current_source:
            current_source_lower = current_source.lower()
            physical_inputs_lower_set = {s.lower() for s in physical_inputs}
            if current_source_lower not in physical_inputs_lower_set:
                # Add current source (preserves original casing)
                physical_inputs.append(current_source)
                _LOGGER.debug(
                    "Added current source '%s' to available_sources (not in physical inputs, currently active) for %s",
                    current_source,
                    self.player.host,
                )

        # Remove duplicates while preserving order
        all_sources = list(dict.fromkeys(physical_inputs))
        return all_sources

    @property
    def audio_output_mode(self) -> str | None:
        """Current audio output mode as friendly name."""
        if self.player._audio_output_status is None:
            return None

        hardware_mode = self.player._audio_output_status.get("hardware")
        if hardware_mode is None:
            return None

        source = self.player._audio_output_status.get("source")
        if source == 1 or source == "1":
            return "Bluetooth Out"

        try:
            mode_int = int(hardware_mode) if isinstance(hardware_mode, str) else hardware_mode
        except (ValueError, TypeError):
            return None

        return self.player.client.audio_output_mode_to_name(mode_int)

    @property
    def audio_output_mode_int(self) -> int | None:
        """Current audio output mode as integer."""
        if self.player._audio_output_status is None:
            return None

        source = self.player._audio_output_status.get("source")
        if source == 1 or source == "1":
            return 4

        hardware_mode = self.player._audio_output_status.get("hardware")
        if hardware_mode is None:
            return None

        try:
            return int(hardware_mode) if isinstance(hardware_mode, str) else hardware_mode
        except (ValueError, TypeError):
            return None

    @property
    def available_output_modes(self) -> list[str]:
        """Available audio output modes for this device."""
        if not self.player.client.capabilities.get("supports_audio_output", False):
            return []

        model = None
        if self.player._device_info:
            model = self.player._device_info.model

        if not model:
            return ["Line Out", "Optical Out", "Coax Out", "Bluetooth Out"]

        model_lower = model.lower()

        if "wiim amp" in model_lower:
            return ["Line Out"]
        elif "wiim mini" in model_lower:
            return ["Line Out", "Optical Out"]
        elif "wiim ultra" in model_lower:
            return ["Line Out", "Optical Out", "Coax Out", "Bluetooth Out", "HDMI Out"]
        elif "wiim pro" in model_lower or "wiim" in model_lower:
            return ["Line Out", "Optical Out", "Coax Out", "Bluetooth Out"]
        else:
            return ["Line Out", "Optical Out", "Coax Out", "Bluetooth Out"]

    @property
    def is_bluetooth_output_active(self) -> bool:
        """Check if Bluetooth output is currently active."""
        if self.player._audio_output_status is None:
            return False

        source = self.player._audio_output_status.get("source")
        return source == 1

    @property
    def bluetooth_output_devices(self) -> list[dict[str, str]]:
        """Get paired Bluetooth output devices (Audio Sinks only).

        Returns:
            List of dicts with keys:
            - name: Device name
            - mac: MAC address (normalized from 'ad' field)
            - connected: Boolean indicating if currently connected

        Example:
            [
                {"name": "Sony SRS-XB43", "mac": "AA:BB:CC:DD:EE:FF", "connected": True},
                {"name": "JBL Tune 750", "mac": "11:22:33:44:55:66", "connected": False}
            ]
        """
        if not self.player._bluetooth_history:
            return []

        output_devices = []
        for device in self.player._bluetooth_history:
            # Only include Audio Sink devices (output devices, not input sources)
            role = device.get("role", "")
            if "Audio Sink" not in role:
                continue

            output_devices.append(
                {
                    "name": device.get("name", "Unknown Device"),
                    "mac": device.get("ad", ""),  # API uses 'ad' not 'mac'
                    "connected": device.get("ct") == 1,
                }
            )

        return output_devices

    @property
    def available_outputs(self) -> list[str]:
        """Get all available outputs including hardware modes and paired BT devices.

        This combines hardware output modes (Line Out, Optical, etc.) with
        already paired Bluetooth output devices for a unified selection list.

        Returns:
            List of output names. Bluetooth devices are prefixed with "BT: "

        Example:
            [
                "Line Out",
                "Optical Out",
                "Coax Out",
                "Bluetooth Out",
                "BT: Sony SRS-XB43",
                "BT: JBL Tune 750"
            ]
        """
        outputs = []

        # Add hardware output modes
        outputs.extend(self.available_output_modes)

        # Add paired Bluetooth output devices
        bt_devices = self.bluetooth_output_devices
        for device in bt_devices:
            outputs.append(f"BT: {device['name']}")

        return outputs

    # === UPnP Health ===

    @property
    def upnp_health_status(self) -> dict[str, Any] | None:
        """UPnP event health statistics.

        Returns health tracking information if UPnP is enabled, None otherwise.

        Returns:
            Dictionary with health statistics:
            - is_healthy: bool - Whether UPnP events are working properly
            - miss_rate: float - Fraction of changes missed (0.0-1.0)
            - detected_changes: int - Total changes detected by polling
            - missed_changes: int - Changes polling saw but UPnP didn't
            - has_enough_samples: bool - Whether enough data for reliable health assessment

            None if UPnP is not enabled or health tracker not available.
        """
        if not self.player._upnp_health_tracker:
            return None
        return self.player._upnp_health_tracker.statistics

    @property
    def upnp_is_healthy(self) -> bool | None:
        """Whether UPnP events are working properly.

        Returns:
            True if UPnP is healthy, False if degraded/failed, None if UPnP not enabled.
        """
        if not self.player._upnp_health_tracker:
            return None
        return self.player._upnp_health_tracker.is_healthy

    @property
    def upnp_miss_rate(self) -> float | None:
        """UPnP event miss rate (0.0 = perfect, 1.0 = all missed).

        Returns:
            Fraction of changes missed by UPnP (0.0 to 1.0), or None if UPnP not enabled.
        """
        if not self.player._upnp_health_tracker:
            return None
        return self.player._upnp_health_tracker.miss_rate
