# API Reference

Complete API reference for the `pywiim` library.

## Table of Contents

- [WiiMClient](#wiimclient)
- [Player](#player)
- [Models](#models)
- [Exceptions](#exceptions)
- [API Mixins](#api-mixins)
  - [DeviceAPI](#deviceapi)
  - [PlaybackAPI](#playbackapi)
  - [GroupAPI](#groupapi)
  - [EQAPI](#eqapi)
  - [PresetAPI](#presetapi)
  - [DiagnosticsAPI](#diagnosticsapi)
  - [BluetoothAPI](#bluetoothapi)
  - [AudioSettingsAPI](#audiosettingsapi)
  - [LMSAPI](#lmsapi)
  - [MiscAPI](#miscapi)
  - [FirmwareAPI](#firmwareapi)
  - [TimerAPI](#timerapi)

## WiiMClient

Main client class that composes all API mixins.

### Initialization

```python
from pywiim import WiiMClient

client = WiiMClient(
    host="192.168.1.100",
    port=80,                    # Optional, default: 80
    timeout=5.0,                # Optional, default: 5.0
    ssl_context=None,           # Optional, for advanced use
    session=None,               # Optional, shared aiohttp session
    capabilities=None,          # Optional, pre-detected capabilities
)
```

### Properties

- `host: str` - Device hostname or IP address
- `base_url: str | None` - Base URL used for last successful request
- `capabilities: dict[str, Any]` - Device capabilities dictionary

### Methods

#### Connection Management

```python
async def close() -> None:
    """Close the client and clean up resources."""
```

#### Device Information

```python
async def get_device_info() -> dict[str, Any]:
    """Get device information as dictionary."""

async def get_device_info_model() -> DeviceInfo:
    """Get device information as Pydantic model."""

async def get_firmware_version() -> str:
    """Get device firmware version."""

async def get_mac_address() -> str:
    """Get device MAC address."""
```

#### Player Status

```python
async def get_player_status() -> dict[str, Any]:
    """Get player status with automatic capability detection."""

async def get_player_status_model() -> PlayerStatus:
    """Get player status as Pydantic model."""
```

## Player

High-level player interface with state caching and convenient properties.

### Initialization

```python
from pywiim import Player, WiiMClient

client = WiiMClient("192.168.1.100")
player = Player(client)

# Refresh state cache
await player.refresh()
```

### Properties

#### Available Sources

```python
player.available_sources  # list[str] | None
```

Returns list of user-selectable physical inputs plus the current source (when active):

1. **Always included**: Physical/hardware sources (Bluetooth, USB, Line In, Optical, Coax, AUX, HDMI) - user-selectable
2. **Conditionally included**: Current source (when active) - includes streaming services (AirPlay, Spotify, etc.) and multi-room follower sources. NOT user-selectable but included for correct UI state display
3. **NOT included**: Inactive streaming services - can't be manually selected and aren't currently playing
4. **Always excluded**: WiFi (it's the network connection, not a selectable source)

**Smart Detection Logic:**
- If `InputList` is provided: Filters device's `InputList` to remove unconfigured services
- If `plm_support` is available: Parses bitmask to detect physical inputs
- Fallback: Uses model-based detection for common inputs

**Why this matters**: Devices report all possible sources in their `InputList`, but streaming services aren't actually usable until you've logged in. This property returns only the sources that will actually work.

**Example:**
```python
await player.refresh()
sources = player.available_sources

# When idle (nothing playing):
# Returns: ["bluetooth", "line_in", "optical"]

# When playing from AirPlay:
# Returns: ["bluetooth", "line_in", "optical", "AirPlay"]

# When playing from Spotify:
# Returns: ["bluetooth", "line_in", "optical", "Spotify"]

# When following another device in multi-room:
# Returns: ["bluetooth", "line_in", "optical", "Master Bedroom"]

# Note: Source names preserve their original casing for proper UI display
```

#### EQ Presets

```python
player.eq_preset  # str | None
```

Current EQ preset name from cached status.

#### Multiroom / Group Role

```python
player.role  # str - "solo", "master", or "slave"
player.is_solo  # bool - True if not in a group
player.is_master  # bool - True if group master
player.is_slave  # bool - True if slave in a group
player.group  # Group | None - Group object (for multi-player scenarios)
```

**Role Detection** - SINGLE source of truth:
- Role comes from device API state via `detect_role()` function
- Updated during `refresh()` from actual device multiroom status
- Cached in `player._detected_role` field
- **Independent of Group objects** - Group objects are for linking Player objects in Home Assistant, role reflects actual device state

**Example:**
```python
await player.refresh()
if player.is_master:
    print(f"Master with {len(player.group.slaves)} linked Player objects")
    # Note: In standalone monitoring, group.slaves may be empty
    # but is_master will still be True based on device API state
```

**Important:** 
- `player.role` reads device state, NOT Group object relationships
- Group objects (`player.group`) are optional and used by coordinators (like HA) to link Player objects
- A master device shows `is_master=True` even if no slave Player objects exist
- Role is always accurate regardless of whether Player objects are linked

#### Other Properties

```python
player.volume_level  # float | None (0.0-1.0)
player.is_muted  # bool | None
player.play_state  # str | None ("play", "pause", "idle", "load")
player.source  # str | None
player.media_title  # str | None
player.media_artist  # str | None
player.media_album  # str | None
player.media_image_url  # str | None (cover art URL)
player.media_sample_rate  # int | None (Hz)
player.media_bit_depth  # int | None (bits)
player.media_bit_rate  # int | None (kbps)
player.media_codec  # str | None (e.g., "flac", "mp3", "aac")
player.upnp_health_status  # dict[str, Any] | None (health statistics)
player.upnp_is_healthy  # bool | None (True/False/None)
player.upnp_miss_rate  # float | None (0.0-1.0, miss rate)
player.shuffle  # bool | None
player.repeat  # str | None ("one", "all", "off")
```

#### UPnP Health Properties

UPnP health tracking monitors whether UPnP events are reliably catching state changes. Only available when UPnP client is provided to Player.

```python
# Health status dictionary (None if UPnP not enabled)
health = player.upnp_health_status
# Returns: {
#     "is_healthy": True,
#     "miss_rate": 0.05,  # 5% miss rate
#     "detected_changes": 20,
#     "missed_changes": 1,
#     "has_enough_samples": True
# }

# Simple health check
is_healthy = player.upnp_is_healthy  # True/False/None

# Miss rate (0.0 = perfect, 1.0 = all missed)
miss_rate = player.upnp_miss_rate  # 0.05 = 5% miss rate
```

**Note**: UPnP health tracking requires:
- UPnP client passed to `Player(..., upnp_client=upnp_client)`
- UPnP events being subscribed (via `UpnpEventer`)
- Player refresh being called regularly

#### Cover Art Methods

```python
# Fetch cover art image (with caching)
result = await player.fetch_cover_art(url=None)  # Returns (bytes, content_type) | None
# If url is None, uses current track's cover art URL
# If no URL available, fetches WiiM logo as fallback

# Get just the image bytes (convenience method)
image_bytes = await player.get_cover_art_bytes(url=None)  # Returns bytes | None
```

**Cover Art Features:**
- ✅ Automatic caching (in-memory, 1 hour TTL, max 10 images per player)
- ✅ Uses client's HTTP session for fetching
- ✅ Handles expired URLs gracefully
- ✅ Returns both image bytes and content type
- ✅ Cache cleanup on fetch (removes expired entries)
- ✅ Automatic WiiM logo fallback when no cover art available

### Properties

#### Connection Info

```python
player.host  # str - Device hostname or IP address
player.port  # int - Device port number
player.timeout  # float - Network timeout in seconds
```

### Methods

```python
# State management
await player.refresh()  # Fetch latest state from device

# Playback control
await player.play()
await player.pause()
await player.stop()
await player.set_volume(volume: float)  # 0.0-1.0
await player.set_mute(muted: bool)
await player.set_source(source: str)
await player.clear_playlist()
await player.set_shuffle(enabled: bool)  # Preserves repeat state

# EQ control
await player.set_eq_preset(preset: str)
await player.get_eq()  # Returns dict[str, Any]
await player.get_eq_presets()  # Returns list[str]
await player.get_eq_status()  # Returns bool

# Audio output control
await player.set_audio_output_mode(mode: str | int)  # "Line Out" or 0-4

# LED control
await player.set_led(enabled: bool)
await player.set_led_brightness(brightness: int)  # 0-100

# Audio settings
await player.set_channel_balance(balance: float)  # -1.0 to 1.0

# Status and metadata fetchers
await player.get_multiroom_status()  # Returns dict[str, Any]
await player.get_audio_output_status()  # Returns dict[str, Any] | None
await player.get_meta_info()  # Returns dict[str, Any]

# Bluetooth workflow
await player.get_bluetooth_history()  # Returns list[dict[str, Any]]
await player.connect_bluetooth_device(mac_address: str)
await player.disconnect_bluetooth_device()
await player.get_bluetooth_pair_status()  # Returns dict[str, Any]
await player.scan_for_bluetooth_devices(duration: int = 3)  # Returns list[dict[str, Any]]

# Output selection (hardware modes + paired BT devices)
outputs = player.available_outputs  # Returns list[str]
bt_devices = player.bluetooth_output_devices  # Returns list[dict[str, str]]
await player.audio.select_output("Optical Out")  # Hardware mode
await player.audio.select_output("BT: Sony Speaker")  # Specific BT device

# Device management
await player.reboot()
await player.sync_time(ts: int | None = None)
```

### When to Use `refresh()`

**Command methods do NOT call `refresh()` internally.** State updates happen via UPnP events and coordinator polling in integrations.

#### ✅ Use `refresh()` for:

```python
# 1. One-off scripts without polling
player = Player(WiiMClient("192.168.1.100"))
await player.play()
await player.refresh()  # Get fresh state
print(f"Playing: {player.media_title}")

# 2. Initial state fetch
await player.refresh()  # Populate state cache
print(f"Volume: {player.volume_level}")

# 3. Explicit verification in tests
await player.set_volume(0.5)
await player.refresh()
assert player.volume_level == 0.5
```

#### ❌ Don't use `refresh()` after commands in integrations:

```python
# Integration with coordinator/polling
await player.play()
# ❌ await player.refresh()  # Unnecessary!
# State updates via:
# - UPnP events (immediate)
# - Coordinator polling (5-10 seconds)
```

**See also**: `docs/design/OPERATION_PATTERNS.md` for detailed patterns

## Models

### DeviceInfo

Device information model.

```python
class DeviceInfo:
    uuid: str
    name: str | None
    model: str | None
    firmware: str | None
    mac: str | None
    ip: str | None
    preset_key: str | None
    input_list: list[str] | None  # Available input sources from InputList field
    plm_support: str | int | None  # Bitmask for physical input sources (smart detection)
```

**Note on `input_list` and `plm_support`:**

- `input_list`: Direct list of available sources from device's `InputList` field in `getStatusEx`. May be `None` if device doesn't provide it.
- `plm_support`: Bitmask indicating which physical inputs are available (from `plm_support` field in `getStatusEx`). Used for smart detection when `input_list` is not available. Bit positions:
  - bit1: LineIn (Aux)
  - bit2: Bluetooth
  - bit3: USB
  - bit4: Optical
  - bit6: Coaxial
  - bit8: LineIn 2
  - bit15: USBDAC (not a selectable source)

### PlayerStatus

Player status model.

```python
class PlayerStatus:
    play_state: str | None
    volume: float | None
    mute: bool | None
    source: str | None
    position: int | None
    duration: int | None
    title: str | None
    artist: str | None
    album: str | None
    image_url: str | None
```

## Exceptions

### WiiMError

Base exception for all WiiM errors.

```python
class WiiMError(Exception):
    """Base exception for WiiM errors."""
```

### WiiMRequestError

Raised when HTTP request fails.

```python
class WiiMRequestError(WiiMError):
    """Raised when HTTP request fails."""
    endpoint: str | None
    attempts: int
    last_error: Exception | None
    device_info: dict[str, str] | None
```

### WiiMResponseError

Raised when device returns error response.

```python
class WiiMResponseError(WiiMError):
    """Raised when device returns error response."""
    endpoint: str | None
    last_error: Exception | None
    device_info: dict[str, str] | None
```

### WiiMTimeoutError

Raised when request times out.

```python
class WiiMTimeoutError(WiiMRequestError):
    """Raised when request times out."""
```

### WiiMConnectionError

Raised when connection fails.

```python
class WiiMConnectionError(WiiMRequestError):
    """Raised when connection fails."""
```

### WiiMInvalidDataError

Raised when response data is invalid.

```python
class WiiMInvalidDataError(WiiMError):
    """Raised when response data is invalid."""
```

## API Mixins

All mixin methods are available directly on `WiiMClient` instances.

### DeviceAPI

Device information and LED control.

```python
# Device information
await client.get_device_info()
await client.get_device_info_model()
await client.get_firmware_version()
await client.get_mac_address()

# LED control
await client.set_led(enabled: bool)
await client.set_led_brightness(brightness: int)  # 0-100
```

### PlaybackAPI

Playback and volume control.

```python
# Playback control
await client.play()
await client.pause()
await client.resume()
await client.stop()
await client.next_track()
await client.previous_track()
await client.seek(position: int)  # seconds

# Volume control
await client.set_volume(volume: float)  # 0.0-1.0
await client.set_mute(muted: bool)

# Source control
await client.set_source(source: str)

# Playback modes
await client.set_loop_mode(mode: str)  # "none", "one", "all"

# Media playback
await client.play_url(url: str)
await client.play_playlist(playlist_url: str)
await client.play_notification(url: str)

# Metadata
await client.get_meta_info()
```

### GroupAPI

Multiroom group management.

```python
# Group status
await client.get_multiroom_status()
await client.get_slaves()

# Group management
await client.create_group()
await client.delete_group()
await client.join_slave(master_ip: str)
await client.leave_group()
await client.kick_slave(slave_ip: str)
await client.mute_slave(slave_ip: str, muted: bool)

# Properties
client.is_master  # bool
client.is_slave   # bool
client.group_master  # str | None
client.group_slaves  # list[str]
```

### EQAPI

Equalizer control.

```python
# EQ presets
await client.set_eq_preset(preset: str)  # "flat", "classical", "jazz", etc.
await client.get_eq_presets()  # Returns list[str] of available preset names

# Custom EQ
await client.set_eq_custom(
    bass: int,      # -12 to 12
    treble: int,    # -12 to 12
    balance: float  # -1.0 to 1.0
)

# EQ status
await client.get_eq()
await client.set_eq_enabled(enabled: bool)
await client.get_eq_status()
```

### PresetAPI

Preset management.

```python
# Presets
await client.get_presets()  # Returns list of preset dicts
await client.get_max_preset_slots()  # Returns int
await client.play_preset(preset: int)  # 1-based preset number
```

### DiagnosticsAPI

Device diagnostics and maintenance.

```python
await client.reboot()
await client.sync_time()
await client.send_command(command: str)  # Raw command
```

### BluetoothAPI

Bluetooth device management.

```python
# Scanning
await client.start_bluetooth_discovery(duration: int = 3)
await client.get_bluetooth_discovery_result()
await client.scan_for_bluetooth_devices(duration: int = 3)
await client.is_bluetooth_scan_in_progress()
await client.get_bluetooth_device_count()
await client.clear_bluetooth_discovery_result()

# Connection
await client.connect_bluetooth_device(mac: str)
await client.disconnect_bluetooth_device()
await client.get_bluetooth_pair_status()
await client.get_bluetooth_history()
```

### AudioSettingsAPI

Advanced audio settings.

```python
# SPDIF
await client.get_spdif_sample_rate()
await client.set_spdif_switch_delay(delay_ms: int)
await client.is_spdif_output_active()

# Channel balance
await client.get_channel_balance()
await client.set_channel_balance(balance: float)  # -1.0 to 1.0
await client.center_channel_balance()

# Audio output
await client.get_audio_output_status()
await client.set_audio_output_hardware_mode(mode: str)

# Status
await client.get_audio_settings_status()
```

### LMSAPI

Lyrion Music Server integration.

```python
# Server discovery
await client.discover_lms_servers()
await client.get_discovered_servers()

# Connection
await client.connect_to_lms_server(server_address: str)
await client.set_auto_connect_enabled(enabled: bool)
await client.is_auto_connect_enabled()
await client.get_connected_server()
await client.get_default_server()
await client.get_connection_state()
await client.is_connected_to_lms()

# Setup helper
await client.setup_lms_connection(
    server_address: str,
    auto_connect: bool = True
)

# State
await client.get_squeezelite_state()
```

### MiscAPI

Miscellaneous device controls.

```python
# Touch buttons
await client.set_buttons_enabled(enabled: bool)
await client.enable_touch_buttons()
await client.disable_touch_buttons()
await client.are_touch_buttons_enabled()

# LED (alternative method)
await client.set_led_switch(enabled: bool)

# Capabilities
await client.get_device_capabilities()
```

### FirmwareAPI

Firmware information and updates.

```python
# Version parsing
client.parse_firmware_version(version_str: str) -> dict[str, Any]
client.compare_firmware_versions(v1: str, v2: str) -> int

# Firmware info
await client.get_firmware_info()
await client.check_for_updates()
await client.get_update_status()
await client.is_firmware_version_at_least(version: str) -> bool
```

### TimerAPI

Sleep timer and alarm clock features (WiiM devices only).

#### Sleep Timer

```python
# Set sleep timer (in seconds)
await client.set_sleep_timer(seconds: int)  # 0=immediate, -1=cancel
await client.get_sleep_timer()  # Returns int (remaining seconds)
await client.cancel_sleep_timer()  # Cancel active timer
```

#### Alarm Clock

WiiM devices support 3 independent alarm slots (indices 0-2).

```python
# Set alarm (time in UTC, HHMMSS format)
await client.set_alarm(
    alarm_id=0,  # 0-2
    trigger=2,  # ALARM_TRIGGER_DAILY
    operation=1,  # ALARM_OP_PLAYBACK
    time="073000",  # 07:30:00 UTC
    day=None,  # Required for once/weekly/monthly triggers
    url=None  # Optional playback URL
)

# Get specific alarm or all alarms
await client.get_alarm(alarm_id=0)
await client.get_alarms()  # Returns list of 3 alarm configs

# Delete alarm
await client.delete_alarm(alarm_id=0)

# Stop currently ringing alarm
await client.stop_current_alarm()

# Sync device time (for offline devices)
await client.sync_time(timestamp="20250117120000")  # YYYYMMDDHHMMSS UTC
```

**Alarm Trigger Types:**
- `ALARM_TRIGGER_CANCEL` (0) - Cancel alarm
- `ALARM_TRIGGER_ONCE` (1) - One-time (day=YYYYMMDD)
- `ALARM_TRIGGER_DAILY` (2) - Every day
- `ALARM_TRIGGER_WEEKLY` (3) - Every week (day="00"-"06" for Sun-Sat)
- `ALARM_TRIGGER_WEEKLY_BITMASK` (4) - Week bitmask (day="7F"=all, "01"=Sun only)
- `ALARM_TRIGGER_MONTHLY` (5) - Every month (day="01"-"31")

**Alarm Operations:**
- `ALARM_OP_SHELL` (0) - Execute shell command
- `ALARM_OP_PLAYBACK` (1) - Play audio/ring
- `ALARM_OP_STOP` (2) - Stop playback

**Note:** All times are in UTC. Applications must handle timezone conversion.

## Usage Examples

### Basic Usage

```python
import asyncio
from pywiim import WiiMClient

async def main():
    client = WiiMClient("192.168.1.100")
    
    # Get device info
    info = await client.get_device_info_model()
    print(f"Device: {info.name} ({info.model})")
    
    # Get status
    status = await client.get_player_status()
    print(f"Playing: {status.get('play_state')}")
    
    # Control playback
    await client.set_volume(0.5)
    await client.play()
    
    await client.close()

asyncio.run(main())
```

### Error Handling

```python
from pywiim import WiiMClient, WiiMError, WiiMRequestError

async def main():
    client = WiiMClient("192.168.1.100")
    
    try:
        await client.play()
    except WiiMRequestError as e:
        print(f"Request failed: {e}")
        print(f"Endpoint: {e.endpoint}")
        print(f"Attempts: {e.attempts}")
    except WiiMError as e:
        print(f"WiiM error: {e}")
    finally:
        await client.close()
```

### Capability Detection

```python
async def main():
    client = WiiMClient("192.168.1.100")
    
    # Capabilities are auto-detected on first use
    info = await client.get_device_info_model()
    
    # Check capabilities
    if client.capabilities.get("supports_presets"):
        presets = await client.get_presets()
        print(f"Found {len(presets)} presets")
    
    await client.close()
```

## Output Selection (Hardware + Bluetooth)

WiiM devices support multiple audio output modes, and pywiim provides unified output selection that includes both hardware modes and already paired Bluetooth devices.

### Available Outputs

Get all available outputs (hardware modes + paired BT devices):

```python
# List all outputs
outputs = player.available_outputs
# Example: ["Line Out", "Optical Out", "Coax Out", "Bluetooth Out", "BT: Sony Speaker", "BT: JBL Headphones"]

# Just get hardware modes
hardware_modes = player.available_output_modes
# Example: ["Line Out", "Optical Out", "Coax Out", "Bluetooth Out"]

# Just get paired Bluetooth output devices
bt_devices = player.bluetooth_output_devices
# Example: [
#     {"name": "Sony Speaker", "mac": "AA:BB:CC:DD:EE:FF", "connected": True},
#     {"name": "JBL Headphones", "mac": "11:22:33:44:55:66", "connected": False}
# ]
```

### Select Output

Use `select_output()` to switch to any output (hardware mode or specific BT device):

```python
# Select hardware output mode
await player.audio.select_output("Optical Out")
await player.audio.select_output("Line Out")

# Select specific Bluetooth device (auto-switches to BT mode and connects)
await player.audio.select_output("BT: Sony Speaker")
await player.audio.select_output("BT: JBL Headphones")

# Check current output
current_mode = player.audio_output_mode  # e.g., "Optical Out"
is_bt_active = player.is_bluetooth_output_active  # True if BT output mode is active
```

### Complete Example

```python
from pywiim import Player, WiiMClient

async def demo_output_selection():
    player = Player(WiiMClient("192.168.1.100"))
    await player.refresh()
    
    # Show all available outputs
    print("Available outputs:")
    for output in player.available_outputs:
        print(f"  - {output}")
    
    # Select Optical output
    await player.audio.select_output("Optical Out")
    print(f"Switched to: {player.audio_output_mode}")
    
    # Show paired Bluetooth devices
    print("\nPaired Bluetooth output devices:")
    for device in player.bluetooth_output_devices:
        status = "🔗 Connected" if device["connected"] else "⊗ Paired"
        print(f"  {status} {device['name']} ({device['mac']})")
    
    # Select specific Bluetooth device
    if player.bluetooth_output_devices:
        first_device = player.bluetooth_output_devices[0]
        await player.audio.select_output(f"BT: {first_device['name']}")
        print(f"Connected to: {first_device['name']}")
```

### Home Assistant Integration

For Home Assistant `select` entity:

```python
class WiiMOutputSelectEntity(SelectEntity):
    """Select entity for output selection."""
    
    @property
    def options(self) -> list[str]:
        """Return available output options."""
        return self.coordinator.data.available_outputs
    
    @property
    def current_option(self) -> str | None:
        """Return current output."""
        player = self.coordinator.data
        
        # Check if BT output is active and which device is connected
        if player.is_bluetooth_output_active:
            for device in player.bluetooth_output_devices:
                if device["connected"]:
                    return f"BT: {device['name']}"
            return "Bluetooth Out"
        
        return player.audio_output_mode
    
    async def async_select_option(self, option: str) -> None:
        """Change the selected output."""
        await self.coordinator.data.audio.select_output(option)
        await self.coordinator.async_request_refresh()
```

