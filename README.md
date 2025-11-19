# pywiim

Comprehensive Python library for WiiM and LinkPlay device communication, providing complete control over multiroom audio systems through HTTP API, UPnP events, and advanced features like queue management, alarms, and real-time state synchronization.

[![CI](https://github.com/mjcumming/pywiim/actions/workflows/ci.yml/badge.svg)](https://github.com/mjcumming/pywiim/actions/workflows/ci.yml) [![Security](https://github.com/mjcumming/pywiim/actions/workflows/security.yml/badge.svg)](https://github.com/mjcumming/pywiim/actions/workflows/security.yml) [![PyPI version](https://img.shields.io/pypi/v/pywiim)](https://pypi.org/project/pywiim/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/pywiim)](https://pypi.org/project/pywiim/) [![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](https://mypy.readthedocs.io/) [![Linting: ruff](https://img.shields.io/badge/linting-ruff-yellow.svg)](https://github.com/astral-sh/ruff)

## Overview

`pywiim` is the comprehensive Python library for WiiM and LinkPlay-based audio devices, supporting everything from basic playback control to advanced features like multiroom synchronization, alarm clocks, and intelligent queue management. Built for reliability and ease of use in production environments.

## Features

### Core Functionality
- **Complete HTTP API Client** - Full implementation of WiiM/LinkPlay HTTP API
  - Official and unofficial endpoints
  - Automatic capability detection
  - Multi-vendor support (WiiM, Arylic, Audio Pro, generic LinkPlay)
  - HTTPS support for Audio Pro MkII+ devices
- **UPnP Integration** - Real-time event subscriptions for instant state updates
  - Automatic event handling with zero configuration
  - Intelligent HTTP polling fallback
  - Seamless state synchronization
- **Fully Async** - Modern async/await API throughout
- **Type Safety** - Comprehensive type annotations for excellent IDE support
- **Production Ready** - Robust error handling with custom exception types

### Media Control & Playback
- Full playback control (play, pause, resume, stop)
- Track navigation (next, previous, seek)
- Play URLs, playlists, and notifications
- Play presets (1-20)
- **Queue Management** - Add to queue or insert next (requires UPnP)
  - Enqueue songs without interrupting playback
  - Build playlists dynamically
  - Insert urgent tracks to play next

### Volume & Audio Control
- Individual volume control (0.0-1.0)
- Group volume synchronization
- Mute/unmute
- Channel balance control
- **Audio Output Mode Selection** (WiiM only) - Line/Optical/Coax/Bluetooth/HDMI
- SPDIF settings and sample rate detection

### Source Management
- Smart source detection
- Source switching (WiFi, Bluetooth, Line-in, Optical, Coaxial, USB, HDMI)
- Streaming service sources (Spotify, AirPlay, DLNA, Amazon Music, Tidal, Qobuz, Deezer, etc.)
- Internet radio sources (iHeartRadio, Pandora, TuneIn)

### Multiroom Audio
- Create, join, and leave multiroom groups
- Automatic group state synchronization
- Role detection (solo/master/slave)
- Synchronized group volume control
- Master-slave coordination

### Equalizer (EQ)
- EQ preset selection
- Custom EQ with 10-band control
- Enable/disable EQ
- Get EQ status and available presets

### Presets
- Play presets (1-20)
- Get preset information
- Preset slot detection

### Timer & Alarm Clock (WiiM Only)
- **Sleep Timer** - Stop playback after specified time
  - Set timer in seconds
  - Cancel active timer
  - Query remaining time
- **Alarm Clock** - 3 independent alarm slots
  - Daily, weekly, monthly, or one-time alarms
  - Wake to music from URL
  - Flexible scheduling with day/time patterns

### Bluetooth
- Scan for Bluetooth devices
- Connect/disconnect Bluetooth devices
- Bluetooth discovery results

### LMS (Logitech Media Server) Integration
- Discover LMS servers on network
- Connect to LMS server
- Auto-connect configuration
- Squeezelite state management

### Device Management
- Complete device information (model, firmware, MAC, UUID)
- Device reboot capability
- Touch button control
- Firmware update support
- Time synchronization for offline devices

### Discovery & Diagnostics
- SSDP/UPnP device discovery
- Network scanning fallback
- Comprehensive diagnostic tool
- Feature verification tool
- Real-time monitoring tool

### Device Compatibility

**Universal Features** (All LinkPlay Devices):
- Playback control, volume, sources, EQ, multiroom, presets, Bluetooth, LMS integration

**WiiM-Enhanced Features** (WiiM Devices Only):
- Alarm clocks & sleep timers
- Audio output mode selection (Line/Optical/Coax/Bluetooth/HDMI)
- Enhanced metadata and capabilities

**Note:** The library automatically detects device capabilities and adapts functionality accordingly.

## Installation

Install `pywiim` to use the command-line tools for discovering, testing, and monitoring your WiiM/LinkPlay devices, or to use the Python library in your projects.

### Prerequisites

- Python 3.11 or later
- pip (usually included with Python)

**Installing Python:**
- **Linux/macOS**: Usually pre-installed. If not, use your package manager or download from [python.org](https://www.python.org/downloads/)
- **Windows**: Download from [python.org](https://www.python.org/downloads/) and check "Add Python to PATH" during installation

### Install pywiim

```bash
pip install pywiim
```

The CLI tools (`wiim-discover`, `wiim-diagnostics`, `wiim-monitor`, `wiim-verify`) are automatically installed and available in your PATH.

**Verify installation:**
```bash
wiim-discover --help
```

**Note for Windows users:** If the commands are not found after installation, ensure Python's Scripts directory is in your PATH (usually `C:\Users\YourName\AppData\Local\Programs\Python\Python3X\Scripts`), or restart your terminal.

## Command-Line Tools

The library includes four powerful CLI tools that are automatically installed with `pywiim`. These tools provide an easy way to discover, diagnose, monitor, and test your WiiM/LinkPlay devices without writing any code.

### Quick Start

1. **Discover devices on your network:**
   ```bash
   wiim-discover
   ```

2. **Test a device** (replace `192.168.1.100` with your device IP):
   ```bash
   wiim-verify 192.168.1.100
   ```

3. **Monitor a device in real-time:**
   ```bash
   wiim-monitor 192.168.1.100
   ```

4. **Run diagnostics:**
   ```bash
   wiim-diagnostics 192.168.1.100
   ```

### 1. Device Discovery (`wiim-discover`)

Discover all WiiM/LinkPlay devices on your network using SSDP/UPnP or network scanning.

**What it does:**
- Automatically finds all WiiM and LinkPlay-based devices on your local network
- Validates discovered devices by testing their API
- Displays device information (name, model, firmware, IP, MAC, UUID)
- Supports multiple discovery methods for maximum compatibility

**Usage:**
```bash
# Basic discovery (SSDP/UPnP)
wiim-discover

# Output as JSON (useful for scripting)
wiim-discover --output json

# Skip API validation (faster, less detailed)
wiim-discover --no-validate

# Verbose logging
wiim-discover --verbose

# Custom SSDP timeout
wiim-discover --ssdp-timeout 10
```

**Options:**
- `--ssdp-timeout <seconds>` - SSDP discovery timeout (default: 5)
- `--no-validate` - Skip API validation of discovered devices
- `--output <text|json>` - Output format (default: text)
- `--verbose, -v` - Enable verbose logging

**Example Output:**
```
🔍 Discovering WiiM/LinkPlay devices via SSDP...

Device: WiiM Mini
  IP Address: 192.168.1.100:80
  Protocol: HTTP
  Model: WiiM Mini
  Firmware: 4.8.123456
  MAC Address: AA:BB:CC:DD:EE:FF
  UUID: 12345678-1234-1234-1234-123456789abc
  Vendor: WiiM
  Discovered via: SSDP
  Status: Validated ✓
```

See [Discovery Documentation](docs/user/DISCOVERY.md) for more information.

### 2. Diagnostic Tool (`wiim-diagnostics`)

Comprehensive diagnostic tool for troubleshooting device issues and gathering information for support.

**What it does:**
- Gathers complete device information (model, firmware, MAC, UUID, capabilities)
- Tests all API endpoints to verify functionality
- Tests feature support (presets, EQ, multiroom, Bluetooth, etc.)
- Generates detailed JSON reports for sharing with developers
- Identifies errors and warnings

**Usage:**
```bash
# Basic diagnostic
wiim-diagnostics 192.168.1.100

# Save report to file (for sharing with support)
wiim-diagnostics 192.168.1.100 --output report.json

# HTTPS device
wiim-diagnostics 192.168.1.100 --port 443

# Verbose output
wiim-diagnostics 192.168.1.100 --verbose
```

**Options:**
- `<device_ip>` - Device IP address or hostname (required)
- `--port <port>` - Device port (default: 80, use 443 for HTTPS)
- `--output <file>` - Save report to JSON file
- `--verbose` - Enable detailed logging

**What it tests:**
- Device information retrieval
- Capability detection
- All status endpoints
- Feature support detection
- API endpoint availability
- Error conditions

**Example Output:**
```
🔍 Starting comprehensive device diagnostic...
   Device: 192.168.1.100:80

📋 Gathering device information...
   ✓ Device: WiiM Mini (WiiM Mini)
   ✓ Firmware: 4.8.123456
   ✓ MAC: AA:BB:CC:DD:EE:FF

🔧 Detecting device capabilities...
   ✓ Vendor: WiiM
   ✓ Device Type: WiiM
   ✓ Supports EQ: Yes
   ✓ Supports Presets: Yes
   ...
```

See [Diagnostics Documentation](docs/user/DIAGNOSTICS.md) for more information.

### 3. Real-time Monitor (`wiim-monitor`)

Monitor your device in real-time with adaptive polling and UPnP event support.

**What it does:**
- Displays live device status with automatic updates
- Uses UPnP events for instant updates when available
- Falls back to adaptive HTTP polling
- Shows play state, volume, mute, track info, and playback position
- Displays device role in multiroom groups
- Tracks statistics (poll count, state changes, UPnP events)

**Usage:**
```bash
# Basic monitoring
wiim-monitor 192.168.1.100

# Specify callback host for UPnP (if auto-detection fails)
wiim-monitor 192.168.1.100 --callback-host 192.168.1.254

# Verbose logging
wiim-monitor 192.168.1.100 --verbose

# Custom log level
wiim-monitor 192.168.1.100 --log-level DEBUG
```

**Options:**
- `<device_ip>` - Device IP address or hostname (required)
- `--callback-host <ip>` - Override UPnP callback host (auto-detected by default)
- `--verbose, -v` - Enable verbose logging
- `--log-level <level>` - Set log level (DEBUG, INFO, WARNING, ERROR)

**What it displays:**
- Play state (playing, paused, stopped)
- Volume level and mute status
- Current track (title, artist, album)
- Playback position and duration
- Device role (solo/master/slave)
- Group information (if in a group)
- Update source (polling or UPnP event)
- Statistics on exit

**Example Output:**
```
🎵 Monitoring WiiM Mini (192.168.1.100)...
   UPnP: Enabled ✓ (events: 0)
   Polling: Adaptive (interval: 2.0s)

📊 Status:
   State: playing
   Volume: 50% (muted: No)
   Source: wifi
   Role: solo

🎶 Track:
   Title: Song Title
   Artist: Artist Name
   Album: Album Name
   Position: 1:23 / 3:45

[UPnP] State changed: volume → 55%
```

Press `Ctrl+C` to stop monitoring and view statistics.

### 4. Feature Verification (`wiim-verify`)

Comprehensive testing tool that verifies all device features and endpoints with safety constraints.

**What it does:**
- Tests all playback controls (play, pause, stop, next, previous)
- Tests volume controls (safely, never exceeds 10%)
- Tests source switching
- Tests audio output modes
- Tests EQ controls (if supported)
- Tests group operations (if applicable)
- Tests preset playback
- Tests all status endpoints
- Saves and restores original device state
- Generates detailed test report

**Usage:**
```bash
# Basic verification
wiim-verify 192.168.1.100

# Verbose output (shows detailed test data)
wiim-verify 192.168.1.100 --verbose

# HTTPS device
wiim-verify 192.168.1.100 --port 443
```

**Options:**
- `<device_ip>` - Device IP address or hostname (required)
- `--port <port>` - Device port (default: 80, use 443 for HTTPS)
- `--verbose, -v` - Enable verbose output (shows detailed test data)

**Safety Features:**
- Volume never exceeds 10% during testing
- Original device state is saved and restored
- Non-destructive testing (doesn't disrupt normal use)
- Graceful error handling

**What it tests:**
- Status endpoints (get_player_status, get_device_info, etc.)
- Playback controls (play, pause, resume, stop, next, previous)
- Volume controls (set_volume, set_mute)
- Source controls (set_source, get_source)
- Audio output controls (set_audio_output_mode)
- EQ controls (get_eq, set_eq_preset, set_eq_custom, etc.)
- Group operations (create_group, join_group, leave_group)
- Preset operations (play_preset)
- And more...

**Example Output:**
```
💾 Saving original device state...
   ✓ Volume: 0.5
   ✓ Mute: False
   ✓ Source: wifi
   ✓ Play state: playing

📊 Testing Status Endpoints...
   ✓ get_player_status
   ✓ get_player_status_model
   ✓ get_meta_info

▶️  Testing Playback Controls...
   ✓ play
   ✓ pause
   ✓ resume
   ✓ stop
   ✓ next_track
   ✓ previous_track

🔊 Testing Volume Controls (max 10%)...
   ✓ set_volume (5%)
   ✓ set_volume (10%)
   ✓ set_mute (True)
   ✓ set_mute (False)

...

🔄 Restoring original device state...
   ✓ Volume restored
   ✓ Mute restored
   ✓ Source restored

============================================================
Total tests: 45
✅ Passed: 42
❌ Failed: 0
⊘ Skipped: 3
```

**Exit Codes:**
- `0` - All tests passed
- `1` - One or more tests failed or interrupted

## Quick Start

Using the Python API:

```python
import asyncio
from pywiim import WiiMClient

async def main():
    # Create client
    client = WiiMClient("192.168.1.100")
    
    # Get device info
    device_info = await client.get_device_info_model()
    print(f"Device: {device_info.name} ({device_info.model})")
    
    # Get player status
    status = await client.get_player_status()
    print(f"Playing: {status.get('play_state')}")
    
    # Control playback
    await client.set_volume(0.5)
    await client.play()
    
    # Set audio output mode (WiiM devices only)
    if client.capabilities.get("supports_audio_output", False):
        await client.set_audio_output_mode("Optical Out")
        # Or use integer: await client.set_audio_output_mode(1)
    
    # Clean up
    await client.close()

asyncio.run(main())
```

## Audio Output Selection

WiiM devices support selecting different audio output modes. This feature is available on all WiiM devices (WiiM Mini, WiiM Pro, WiiM Pro Plus, WiiM Amp, WiiM Ultra).

### Available Output Modes

Different WiiM models support different output combinations:

- **WiiM Mini**: Line Out, Optical Out
- **WiiM Pro/Pro Plus**: Line Out, Optical Out, Coax Out, Bluetooth Out
- **WiiM Amp**: Line Out (integrated amplifier, no digital outputs)
- **WiiM Ultra**: Line Out, Optical Out, Coax Out, Bluetooth Out, HDMI Out

### Usage Examples

```python
import asyncio
from pywiim import WiiMClient

async def main():
    client = WiiMClient("192.168.1.100")
    
    # Check if device supports audio output control
    if client.capabilities.get("supports_audio_output", False):
        # Get current output mode
        status = await client.get_audio_output_status()
        print(f"Current output: {status}")
        
        # Set output mode using friendly name
        await client.set_audio_output_mode("Optical Out")
        await client.set_audio_output_mode("Line Out")
        await client.set_audio_output_mode("Coax Out")
        await client.set_audio_output_mode("Bluetooth Out")
        
        # Or use integer mode (0-4)
        await client.set_audio_output_mode(0)  # Line Out
        await client.set_audio_output_mode(1)  # Optical Out
        await client.set_audio_output_mode(3)  # Coax Out
        await client.set_audio_output_mode(4)  # Bluetooth Out
        
        # Convert between names and integers
        mode_int = client.audio_output_name_to_mode("Optical Out")  # Returns 1
        mode_name = client.audio_output_mode_to_name(1)  # Returns "Optical Out"
    
    await client.close()

asyncio.run(main())
```

### Using the Player Class

The `Player` class provides convenient properties for output selection:

```python
from pywiim import Player

async def main():
    player = Player("192.168.1.100")
    await player.refresh()
    
    # Get current output mode
    current_mode = player.audio_output_mode  # e.g., "Optical Out"
    print(f"Current output: {current_mode}")
    
    # Get available output modes for this device
    available = player.available_output_modes
    print(f"Available modes: {available}")
    # Example: ["Line Out", "Optical Out", "Coax Out", "Bluetooth Out"]
    
    # Set output mode
    await player.set_audio_output_mode("Optical Out")
    
    # Check if Bluetooth output is active
    if player.is_bluetooth_output_active:
        print("Bluetooth output is currently active")
    
    await player.close()

asyncio.run(main())
```

## Queue Management

Queue management allows you to add media to the playback queue instead of replacing the current track. This feature requires UPnP AVTransport actions and is useful for building playlists or adding songs to an existing queue.

### Overview

Queue management supports three operations:
- **Add to queue** - Append media to the end of the queue
- **Insert next** - Insert media after the current track (plays next)
- **Play with enqueue** - Play URL with optional enqueue behavior

### Requirements

Queue management requires:
- **UPnP client** - Must be created and passed to `Player`
- **AVTransport service** - Device must support UPnP AVTransport (all WiiM devices do)

### Basic Usage

Queue management requires a UPnP client. Create the UPnP client and pass it to the Player:

```python
import asyncio
from pywiim import WiiMClient, Player, UpnpClient

async def main():
    # Create HTTP client
    http_client = WiiMClient("192.168.1.100")
    
    # Create UPnP client (required for queue management)
    description_url = f"http://192.168.1.100:49152/description.xml"
    upnp_client = await UpnpClient.create("192.168.1.100", description_url)
    
    # Create player with UPnP client
    player = Player(http_client, upnp_client=upnp_client)
    
    # Add songs to queue
    await player.add_to_queue("http://example.com/song1.mp3")
    await player.add_to_queue("http://example.com/song2.mp3")
    
    # Insert song after current track
    await player.insert_next("http://example.com/urgent.mp3")
    
    # Play URL with enqueue option
    await player.play_url("http://example.com/song3.mp3", enqueue="add")
    
    # Clean up
    await http_client.close()

asyncio.run(main())
```

### Methods

#### `add_to_queue(url, metadata="")`

Add a URL to the end of the playback queue.

```python
# Add songs to queue
await player.add_to_queue("http://example.com/song1.mp3")
await player.add_to_queue("http://example.com/song2.mp3")

# With optional DIDL-Lite metadata
await player.add_to_queue(
    "http://example.com/song.mp3",
    metadata="<DIDL-Lite>...</DIDL-Lite>"
)
```

#### `insert_next(url, metadata="")`

Insert a URL after the current track (will play next).

```python
# Insert urgent song to play next
await player.insert_next("http://example.com/urgent.mp3")
```

#### `play_url(url, enqueue="replace|add|next|play")`

Play a URL with optional enqueue behavior.

```python
# Default: replace current (uses HTTP API)
await player.play_url("http://example.com/song.mp3")

# Add to end of queue (uses UPnP)
await player.play_url("http://example.com/song.mp3", enqueue="add")

# Insert after current (uses UPnP)
await player.play_url("http://example.com/song.mp3", enqueue="next")

# Play immediately (uses HTTP API, same as default)
await player.play_url("http://example.com/song.mp3", enqueue="play")
```

### Error Handling

Queue management methods will raise `WiiMError` if:
- UPnP client is not available (not passed to `Player.__init__()`)
- UPnP AVTransport service is not available
- Device doesn't support queue operations

**Best Practice:** Check for UPnP client availability before using queue features:

```python
if player._upnp_client:
    await player.add_to_queue("http://example.com/song.mp3")
else:
    # Fallback to regular play
    await player.play_url("http://example.com/song.mp3")
```

### Notes

- Queue management methods (`add_to_queue`, `insert_next`) and the `enqueue` parameter in `play_url()` require a UPnP client
- Without a UPnP client, these operations will raise a `WiiMError` with a helpful error message
- The UPnP client can be shared between `UpnpEventer` (for events) and `Player` (for queue management)
- See [Home Assistant Integration Guide](docs/integration/HA_INTEGRATION.md) for integration examples

## Audio Output Selection

### Output Mode Reference

| Mode | Integer | Description |
|------|---------|-------------|
| Line Out | 0 | Analog line output (RCA) |
| Optical Out | 1 | Digital optical output (TOSLINK) |
| Line Out (alt) | 2 | Alternative line out mode (some devices) |
| Coax Out | 3 | Digital coaxial output |
| Bluetooth Out | 4 | Bluetooth audio output |

**Note:** Bluetooth output takes precedence over hardware output mode when active. The `get_audio_output_status()` method returns both `hardware` (hardware output mode) and `source` (Bluetooth output status).

## Known Device Behaviors

### Play vs Resume on Streaming Sources

When playing streaming content (Spotify, Amazon Music, web radio, etc.), LinkPlay devices distinguish between "start playback" and "resume from pause":

- **`play()`** - Start playback (may restart track from beginning when paused)
- **`resume()`** - Resume from paused position (continues where paused)
- **`media_play_pause()`** - Intelligently chooses resume() when paused, play() when stopped

**Issue**: On streaming sources like Amazon Music, calling `play()` on a paused track restarts it from the beginning instead of resuming (Issue [#102](https://github.com/mjcumming/wiim/issues/102)).

**Solution**: Use `resume()` to continue from current position, or use `media_play_pause()` which handles this automatically.

**For Home Assistant integrations**: Use `media_play_pause()` for the `media_play_pause` service to avoid restarting tracks:

```python
# In Home Assistant media player entity
async def async_media_play_pause(self) -> None:
    """Toggle play/pause."""
    await self.coordinator.player.media_play_pause()  # ✅ Handles resume correctly
```

**For direct control**:

```python
# Check state before resuming
if player.play_state in ('pause', 'paused'):
    await player.resume()  # Continue from current position
else:
    await player.play()    # Start playback
```

### WebRadio/WiFi Source Stop Behavior

When playing web radio or WiFi streaming sources, the `stop()` command may not work as expected. Some devices immediately return to "playing" state after being stopped (Issues [#49](https://github.com/mjcumming/wiim/issues/49), [#45](https://github.com/mjcumming/wiim/issues/45)).

**Workaround**: Use `pause()` instead of `stop()` for web radio streams:

```python
# Check source before stopping
if player.source and player.source.lower() in ['wifi', 'webradio', 'iheartradio', 'pandora', 'tunein']:
    await player.pause()  # More reliable for web streams
else:
    await player.stop()
```

**For Home Assistant integrations**: You can implement this logic in your `async_media_stop()` method to provide better UX for web radio users.

**Background**: These behaviors originate from the underlying LinkPlay firmware and are present across all LinkPlay-based devices (WiiM, Arylic, Audio Pro, etc.). The library provides the raw API methods plus convenience methods to help you handle these quirks.

## Documentation

### User Guides
- [Discovery Guide](docs/user/DISCOVERY.md) - Device discovery via SSDP/UPnP
- [Diagnostics Guide](docs/user/DIAGNOSTICS.md) - Using the diagnostic tool
- [Real-time Monitor Guide](docs/user/MONITOR.md) - Real-time device monitoring

### Integration Guides
- [Home Assistant Integration](docs/integration/HA_INTEGRATION.md) - Complete guide for HA integrations
  - DataUpdateCoordinator patterns
  - Adaptive polling strategies
  - UPnP event integration
  - Queue management
  - Source-aware shuffle/repeat control
- [API Reference](docs/integration/API_REFERENCE.md) - Complete API documentation

### Technical Documentation
- [LinkPlay Architecture](docs/technical/LINKPLAY_ARCHITECTURE.md) - **In-depth analysis of LinkPlay/WiiM streaming architecture**
  - "Split Brain" control authority model
  - Transport protocol analysis (AirPlay, Spotify, USB, Bluetooth)
  - Hardware constraints (A98 SoM, RAM limits, queue management)
  - Why shuffle/repeat controls work differently for different sources
  - Integration strategies for automation systems

### Design Documentation
- [Architecture & Data Flow](docs/design/ARCHITECTURE_DATA_FLOW.md) - System architecture
- [State Management](docs/design/STATE_MANAGEMENT.md) - State synchronization patterns
- [Operation Patterns](docs/design/OPERATION_PATTERNS.md) - Common operation patterns

## Development Setup

See [SETUP.md](SETUP.md) for detailed development setup instructions.

Quick start:
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/unit/ -v

# Run code quality checks
make lint typecheck
```

## Project Status

✅ **Core Features Complete:**
- HTTP API client with all mixins
- UPnP client and event handling
- Capability detection system
- State synchronization
- Diagnostic tool
- Comprehensive test suite

✅ **Code Quality:**
- Major refactoring completed (24% reduction in largest file)
- Improved error handling and logging
- Enhanced type hints across codebase
- All large files properly documented

🚧 **Package Finalization:**
- Package metadata ready
- Build testing pending (requires build tools)

## Acknowledgments

This library was made possible by the work of many developers who have reverse-engineered and documented the WiiM/LinkPlay API. We would like to acknowledge the following projects and resources that provided valuable API information and implementation insights:

### Libraries and Implementations
- **[python-linkplay](https://pypi.org/project/python-linkplay/)** - Python library for LinkPlay devices that provided insights into state detection and API patterns (enhanced state detection logic from v0.2.9)
- **[linkplay-cli](https://github.com/ramikg/linkplay-cli)** - Command-line tool for LinkPlay devices (provided SSL certificate reference for Audio Pro devices)
- **[WiiM HTTP API OpenAPI Specification](https://github.com/cvdlinden/wiim-httpapi)** - Comprehensive OpenAPI 3.0 specification for WiiM HTTP API endpoints
- **[Home Assistant WiiM Integration](https://github.com/mjcumming/wiim)** - Production-tested implementation that informed many design decisions, polling strategies, and state management patterns
- **[WiiM Play](https://github.com/shumatech/wiimplay)** - UPnP-based implementation that provided UPnP integration insights
- **Vellmon LinkPlay library** - Provided valuable API information and patterns for LinkPlay device communication
- **[Home Assistant LinkPlay Custom Component](https://github.com/nagyrobi/home-assistant-custom-components-linkplay)** - Custom Home Assistant integration for LinkPlay devices
- **[LinkPlay A31 Alternative Firmware](https://github.com/hn/linkplay-a31)** - Alternative firmware project that provided insights into LinkPlay hardware capabilities

### Official Documentation
- [Arylic LinkPlay API Documentation](https://developer.arylic.com/httpapi/) - Official LinkPlay protocol documentation
- [WiiM HTTP API PDF](https://www.wiimhome.com/pdf/HTTP%20API%20for%20WiiM%20Products.pdf) - Official WiiM API documentation

### Additional Resources
- Various GitHub repositories and community contributions that helped document the LinkPlay protocol and WiiM-specific enhancements
- The LinkPlay and WiiM developer communities for sharing API discoveries and reverse-engineering efforts

If you know of other libraries or resources that should be acknowledged, please [open an issue](https://github.com/mjcumming/pywiim/issues) or submit a pull request.

## License

MIT License
