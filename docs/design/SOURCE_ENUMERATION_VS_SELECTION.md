# Source Enumeration vs Selection

## Overview

WiiM devices have a **two-layer source system** that creates an important distinction between sources that can be **enumerated** (listed) and sources that can be **selected** (switched to).

## The Two Layers

### Layer 1: Physical Inputs (Enumerable)
These are the **physical and connection-level inputs** that the device reports as available in `input_list` from `getStatusEx`:

- **WiFi/Network** - Internet streaming input
- **Bluetooth** - Bluetooth audio input  
- **Line In** - Analog audio input
- **Optical** - Digital optical input
- **Coaxial** - Digital coaxial input
- **USB** - USB audio input (some devices)
- **HDMI** - HDMI audio input (some devices)

These are **enumerable** - the device reports them in `input_list` because they represent physical hardware connections.

### Layer 2: Services/Content (Selectable but not always enumerable)
These are **streaming services and protocols** that can be selected but may not appear in `input_list`:

- **Amazon Music** - Streaming service
- **Spotify** - Streaming service  
- **Tidal** - Streaming service
- **Qobuz** - Streaming service
- **Deezer** - Streaming service
- **AirPlay** - Apple casting protocol
- **DLNA** - Network media protocol
- **iHeartRadio** - Internet radio service
- **Other streaming services** - Various internet radio and streaming services

These are **selectable** - you can switch to them using `switchmode:`, but they may not appear in `input_list` because they're not physical inputs.

**Note on Presets**: Presets (saved stations/playlists) are **NOT** input sources. They should be handled via media browser functionality:
- Use `get_presets()` to retrieve the list of presets (returns list of dicts with number, name, url, picurl)
- Use `play_preset(preset_number)` to play a preset
- Presets should be exposed in Home Assistant's media browser, not as selectable input sources

## Key Distinction

### Enumerable Sources (`input_list`)
- **Source**: `getStatusEx` API response
- **Field**: `input_list` in `DeviceInfo`
- **Contains**: Physical hardware inputs only
- **Purpose**: Shows what physical inputs are available on the device
- **Example**: `["wifi", "bluetooth", "line_in", "optical"]`

### User-Selectable Sources (For Home Assistant UI)
- **Source**: Physical inputs that users can manually select + current source (if active and not a physical input)
- **Field**: `Player.available_sources` property in pywiim
- **Contains**: Physical/hardware inputs + current source (when active and not already in list)
- **Purpose**: Sources to show in Home Assistant's input_source dropdown
- **Example (idle)**: `["bluetooth", "line_in", "usb", "optical", "coaxial"]`
- **Example (playing AirPlay)**: `["bluetooth", "line_in", "usb", "optical", "coaxial", "AirPlay"]`
- **Example (playing Spotify)**: `["bluetooth", "line_in", "usb", "optical", "coaxial", "Spotify"]`
- **Example (multi-room follower)**: `["bluetooth", "line_in", "optical", "Master Bedroom"]`
- **Note**: Physical inputs are always included (user-selectable). Current source is conditionally included only when active (for proper UI state display). Source names preserve their original casing for proper UI display.

## Implementation Pattern

### For Home Assistant UI (User-Selectable Sources)

The Home Assistant WiiM integration should show **physical/hardware inputs** (user-selectable) plus 
the **current source** (when active) in the input_source dropdown:

- ✅ Line In, USB, Bluetooth, Optical, Coaxial, HDMI (always shown - user can manually select these)
- ✅ Current source (shown when active - AirPlay, Spotify, multi-room follower name, etc.)
- ❌ Inactive streaming services (AirPlay, Spotify, Tidal, Amazon, etc. - NOT shown unless currently active)

**Why always show physical inputs?** These are the sources users can manually select.

**Why include current source?** For streaming services like AirPlay or Spotify, you don't manually 
"select" them as an input - an external app activates them automatically. For multi-room, a follower 
device shows the master's name as its source. Including the current source (when active) ensures Home 
Assistant correctly displays what's actually playing, preventing "Unknown" sources or UI mismatches.

**Why NOT always show AirPlay/DLNA?** While these don't require account configuration, they're still 
not user-selectable inputs - they're activated by external devices/apps. We only show them when active 
so the UI accurately reflects the current state without cluttering the dropdown with non-selectable options.

### Correct Pattern (Current)

```python
# Get physical inputs + current source (if active)
available_sources = player.available_sources

# For Home Assistant: Use this list directly for input_source dropdown
# Example when idle: ["bluetooth", "line_in", "usb", "optical"]
# Example when playing AirPlay: ["bluetooth", "line_in", "usb", "optical", "AirPlay"]
# Example when playing Spotify: ["bluetooth", "line_in", "usb", "optical", "Spotify"]
# Example when multi-room follower: ["bluetooth", "line_in", "optical", "Master Bedroom"]

# Note: Source names preserve their original casing for proper UI display
```