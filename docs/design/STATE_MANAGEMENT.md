# State Management

## Overview

WiiM devices provide state information through two sources:
1. **HTTP Polling**: Periodic requests to getStatusEx/getPlayerStatusEx
2. **UPnP Events**: Real-time event notifications via LastChange XML

These sources can provide overlapping, conflicting, stale, or missing data. This document describes how the library manages state synchronization, play state identification, and position tracking.

## Table of Contents

1. [State Synchronization](#state-synchronization) - Merging HTTP and UPnP data
2. [Play State Identification](#play-state-identification) - Determining correct play state
3. [Position Tracking](#position-tracking) - Hybrid position estimation

---

## State Synchronization

### Problem Statement

#### Challenges

1. **Overlapping Data**: Both sources provide volume, play state, position, metadata
2. **Conflicting Data**: HTTP and UPnP may report different values simultaneously
3. **Stale Data**: One source may be outdated while the other is fresh
4. **Missing Data**: One source may not provide certain fields (e.g., Audio Pro MkII HTTP doesn't provide volume)
5. **Source Availability**: One source may be temporarily unavailable
6. **Metadata Issues**: Metadata can be incomplete, malformed, or cleared during transitions

#### Real-World Scenarios

- **Scenario 1**: UPnP event arrives with volume=50%, but HTTP poll 2 seconds later shows volume=60%
  - **Question**: Which is correct? Should we trust the more recent one?
  
- **Scenario 2**: HTTP poll returns complete metadata (title, artist, album), but UPnP event has empty metadata
  - **Question**: Is UPnP clearing metadata because device stopped, or is it a transient issue?
  
- **Scenario 3**: UPnP events stop arriving (subscription failed), but HTTP polling continues
  - **Question**: Should we trust HTTP data, or mark UPnP fields as stale?
  
- **Scenario 4**: Audio Pro MkII - HTTP doesn't provide volume, only UPnP does
  - **Question**: How do we merge when one source is missing data?

### Design Pattern: Timestamped State Merging with Source Priority

#### Core Principles

1. **Timestamp Everything**: Every state update includes a timestamp
2. **Source Tracking**: Track which source provided each field
3. **Freshness Windows**: Define time windows for considering data "fresh"
4. **Source Priority**: Define priority rules for conflict resolution
5. **Graceful Degradation**: Use available source when other is unavailable
6. **Metadata Preservation**: Don't clear metadata during transitions unless confirmed

#### State Model

```python
@dataclass
class TimestampedField:
    """A field value with source and timestamp."""
    value: Any
    source: str  # "http" or "upnp"
    timestamp: float
    confidence: float = 1.0  # 0.0-1.0, based on source reliability and freshness

@dataclass
class SynchronizedState:
    """Merged state from HTTP and UPnP sources."""
    # Transport state
    play_state: TimestampedField | None = None
    position: TimestampedField | None = None
    duration: TimestampedField | None = None
    
    # Media metadata
    title: TimestampedField | None = None
    artist: TimestampedField | None = None
    album: TimestampedField | None = None
    image_url: TimestampedField | None = None
    
    # Volume and mute
    volume: TimestampedField | None = None
    muted: TimestampedField | None = None
    
    # Source
    source: TimestampedField | None = None
    
    # Source health tracking
    http_last_update: float | None = None
    upnp_last_update: float | None = None
    http_available: bool = True
    upnp_available: bool = True
```

### Synchronization Rules

#### Rule 1: Freshness Windows

Define time windows for considering data "fresh":

```python
FRESHNESS_WINDOWS = {
    "play_state": 5.0,  # 5 seconds - changes frequently
    "position": 2.0,  # 2 seconds - changes very frequently
    "volume": 10.0,  # 10 seconds - changes less frequently
    "muted": 10.0,  # 10 seconds
    "metadata": 30.0,  # 30 seconds - changes less frequently
    "source": 60.0,  # 60 seconds - changes rarely
}
```

#### Rule 2: Source Priority by Field Type

Different fields have different source priorities:

```python
SOURCE_PRIORITY = {
    # Real-time fields: UPnP preferred (more timely)
    "play_state": ["upnp", "http"],  # UPnP events are immediate
    "position": ["upnp", "http"],  # UPnP on track start, local timer estimates, HTTP polls periodically to correct
    "volume": ["upnp", "http"],  # UPnP volume changes are immediate
    
    # Metadata: HTTP preferred (more complete, less likely to be cleared)
    "title": ["http", "upnp"],  # HTTP metadata is more reliable
    "artist": ["http", "upnp"],
    "album": ["http", "upnp"],
    "image_url": ["http", "upnp"],
    
    # Source: HTTP preferred (more accurate)
    "source": ["http", "upnp"],
    
    # Duration: UPnP on track start, HTTP polls periodically
    "duration": ["upnp", "http"],
}
```

#### Rule 3: Conflict Resolution

When both sources have data for the same field:

1. **Check Freshness**: If one is stale (outside freshness window), use the fresh one
2. **Check Priority**: If both fresh, use source priority
3. **Check Confidence**: If same priority, use higher confidence
4. **Fallback**: If all equal, use most recent

```python
def resolve_conflict(
    http_field: TimestampedField | None,
    upnp_field: TimestampedField | None,
    field_name: str,
    now: float,
) -> TimestampedField | None:
    """Resolve conflict between HTTP and UPnP data."""
    if not http_field and not upnp_field:
        return None
    if not http_field:
        return upnp_field
    if not upnp_field:
        return http_field
    
    # Both present - resolve conflict
    freshness_window = FRESHNESS_WINDOWS.get(field_name, 10.0)
    http_fresh = (now - http_field.timestamp) < freshness_window
    upnp_fresh = (now - upnp_field.timestamp) < freshness_window
    
    # If one is stale, use the fresh one
    if http_fresh and not upnp_fresh:
        return http_field
    if upnp_fresh and not http_fresh:
        return upnp_field
    
    # Both fresh - use priority
    priority = SOURCE_PRIORITY.get(field_name, ["upnp", "http"])
    if priority[0] == "upnp" and upnp_fresh:
        return upnp_field
    if priority[0] == "http" and http_fresh:
        return http_field
    
    # Same priority - use most recent
    if upnp_field.timestamp > http_field.timestamp:
        return upnp_field
    return http_field
```

#### Rule 4: Metadata Preservation

Metadata should not be cleared unless we're certain the device stopped:

```python
def should_clear_metadata(
    http_play_state: str | None,
    upnp_play_state: str | None,
    current_metadata: dict[str, TimestampedField],
) -> bool:
    """Determine if metadata should be cleared."""
    # Don't clear if device is playing or transitioning
    playing_states = ["play", "playing", "transitioning", "loading"]
    
    http_playing = http_play_state and any(
        state in http_play_state.lower() for state in playing_states
    )
    upnp_playing = upnp_play_state and any(
        state in upnp_play_state.lower() for state in playing_states
    )
    
    # Only clear if both sources confirm stopped
    if not http_playing and not upnp_playing:
        return True
    
    return False
```

#### Rule 5: Source Availability Tracking

Track when sources become unavailable:

```python
SOURCE_TIMEOUTS = {
    "http": 30.0,  # HTTP poll timeout (30 seconds)
    "upnp": 300.0,  # UPnP event timeout (5 minutes - events only on changes)
}

def update_source_availability(
    state: SynchronizedState,
    now: float,
) -> None:
    """Update source availability flags."""
    # HTTP is available if we got data recently
    if state.http_last_update:
        state.http_available = (now - state.http_last_update) < SOURCE_TIMEOUTS["http"]
    else:
        state.http_available = False
    
    # UPnP is available if we got events recently
    # Note: UPnP has no heartbeat, so we use a longer timeout
    if state.upnp_last_update:
        state.upnp_available = (now - state.upnp_last_update) < SOURCE_TIMEOUTS["upnp"]
    else:
        state.upnp_available = False
```

### Special Cases

#### Case 1: Audio Pro MkII (HTTP doesn't provide volume)

```python
# HTTP poll returns no volume field
# UPnP provides volume
# Solution: Use UPnP volume, mark HTTP as not providing this field
if device_type == "audio_pro_mkii":
    SOURCE_PRIORITY["volume"] = ["upnp"]  # Only UPnP available
```

#### Case 2: Metadata Cleared During Transition

```python
# UPnP event arrives with empty metadata
# But HTTP poll 1 second ago had complete metadata
# Device is still playing (play_state = "play")
# Solution: Don't clear metadata, keep HTTP metadata
if play_state in ["play", "playing"]:
    # Preserve existing metadata
    pass
```

#### Case 3: UPnP Events Stop (Subscription Failed)

```python
# UPnP events haven't arrived in 5 minutes
# HTTP polling continues
# Solution: Mark UPnP fields as stale, use HTTP data
if not upnp_available:
    # Use HTTP data for all fields
    # Log warning about UPnP unavailability
    pass
```

---

## Play State Identification

### Overview

Determining the correct player state (play, pause, stop, idle) is one of the most challenging aspects of the library because:

1. **Different Sources**: HTTP API and UPnP events provide state information
2. **Different Field Names**: Each source uses different field names
3. **Different Value Formats**: Each source uses different value formats
4. **Device Variations**: Some devices don't provide state via HTTP (Audio Pro MkII)
5. **State Normalization**: Values need normalization across sources
6. **Conflicting States**: Sources may report different states simultaneously
7. **Stale State**: One source may be outdated while the other is fresh

### HTTP API State Identification

#### Field Names

The HTTP API uses multiple field names for play state, requiring mapping:

```python
# Multiple field names map to play_status
STATUS_MAP = {
    "status": "play_status",
    "state": "play_status",
    "player_state": "play_status",
}

# Parser checks all possible field names
play_state_val = raw.get("state") or raw.get("player_state") or raw.get("status")
```

#### Value Formats

HTTP API returns various value formats that need normalization:

**Raw Values:**
- `"play"` - Playing
- `"pause"` - Paused
- `"stop"` - Stopped (device value)
- `"none"` - Idle (must be converted to "idle")
- `"load"` - Loading/transitioning
- `"playing"` - Playing (variation)
- `"paused"` - Paused (variation)
- `"stopped"` - Stopped (variation)

**Normalization Logic:**
```python
# From pywiim/state.py
STANDARD_PLAY_STATES = {
    "play": "play",
    "playing": "play",
    "pause": "pause",
    "paused": "pause",
    "paused playback": "pause",
    "stop": "pause",  # Modern UX: stop == pause (position maintained either way)
    "stopped": "pause",  # Modern UX: stop == pause (position maintained either way)
    "idle": "idle",
    "none": "idle",  # HTTP API uses "none" for idle
    "no media present": "idle",
    "load": "load",
    "loading": "load",
    "transitioning": "load",
    "buffering": "load",
}
```

**Normalized Values (User-Facing):**
- `"play"` - Playing
- `"pause"` - Paused (includes device "stop" state for modern UX)
- `"idle"` - Idle (converted from "none", no media loaded)
- `"load"` - Loading/transitioning/buffering

**Rationale for stop→pause mapping:**
Modern streaming devices maintain playback position whether "paused" or "stopped". Users think in terms of "playing" vs "not playing", not three separate states. This aligns with Home Assistant conventions (no STATE_STOPPED) and Sonos behavior (IDLE state for empty queue).

#### Device-Specific Behavior

**WiiM Devices:**
- ✅ HTTP provides play_state via `getPlayerStatusEx` or `getStatusEx`
- ✅ Values: "play", "pause", "stop" (→ "pause"), "none" (→ "idle")

**Audio Pro Original:**
- ✅ HTTP provides play_state via `getStatusEx`
- ✅ Values: "play", "pause", "stop" (→ "pause"), "none" (→ "idle")

**Audio Pro MkII:**
- ❌ HTTP does NOT provide play_state
- ✅ Must use UPnP for play_state
- ⚠️ **Critical**: HTTP polling will never have play_state for MkII

**Audio Pro W-Generation:**
- ✅ HTTP provides play_state via `getPlayerStatusEx` or `getStatusEx`
- ✅ Values: "play", "pause", "stop" (→ "pause"), "none" (→ "idle")

### UPnP State Identification

#### Field Names

UPnP uses `TransportState` variable in AVTransport service:

```python
# UPnP LastChange XML parsing
if var_name == "TransportState":
    changes["play_state"] = var_value.lower().replace("_", " ")
```

#### Value Formats

UPnP uses DLNA standard state values with underscores:

**Raw UPnP Values:**
- `"PLAYING"` - Playing
- `"PAUSED_PLAYBACK"` - Paused
- `"STOPPED"` - Stopped
- `"TRANSITIONING"` - Transitioning between states
- `"NO_MEDIA_PRESENT"` - No media loaded (idle)
- `"LOADING"` - Loading media

**Normalization Logic:**
```python
# UPnP values: "PAUSED_PLAYBACK" → "paused playback" → "paused"
var_value.lower().replace("_", " ")
# Then normalize to standard values
```

**Normalized Values:**
- `"playing"` - Playing
- `"paused playback"` or `"paused"` - Paused
- `"stopped"` - Stopped (device value, maps to "pause")
- `"transitioning"` - Transitioning
- `"no media present"` or `"idle"` - Idle
- `"loading"` - Loading

#### UPnP State Mapping

Need to map UPnP states to standard states:

```python
UPNP_STATE_MAP = {
    "playing": "play",
    "paused playback": "pause",
    "paused": "pause",
    "stopped": "pause",  # Modern UX: stop == pause
    "no media present": "idle",
    "transitioning": "load",  # or "transitioning"
    "loading": "load",
}
```

### State Identification Rules

#### Rule 1: Source Availability

1. If only one source has state → use that source
2. If both sources have state → apply conflict resolution
3. If neither source has state → return None (unknown)

#### Rule 2: Freshness Check

1. Check if each source is fresh (within freshness window)
2. If one is stale and one is fresh → use fresh one
3. If both are stale → use most recent (or mark as unavailable)

#### Rule 3: Source Priority

1. For play_state: UPnP preferred (more timely)
2. If both fresh and same priority → use most recent
3. If priority differs → use higher priority source

#### Rule 4: State Normalization

1. Normalize HTTP values: "none" → "idle", lowercase
2. Normalize UPnP values: "PAUSED_PLAYBACK" → "paused", lowercase, replace underscores
3. Map to standard values: "playing" → "play", "paused playback" → "pause"
4. Handle transition states: "load", "loading", "transitioning"

#### Rule 5: Device-Specific Behavior

1. **Audio Pro MkII**: HTTP never provides play_state → always use UPnP
2. **Audio Pro Original**: HTTP provides play_state → prefer HTTP when fresh
3. **WiiM Devices**: Both sources available → use priority rules
4. **Arylic Devices**: Both sources available → use priority rules

### Key Takeaways

1. **HTTP Field Names**: Multiple field names ("state", "status", "player_state") need mapping
2. **HTTP Value Normalization**: "none" → "idle", lowercase all values
3. **UPnP Value Normalization**: Replace underscores, lowercase, map to standard values
4. **Device Variations**: Audio Pro MkII doesn't provide HTTP play_state
5. **Source Priority**: UPnP preferred for play_state (more timely)
6. **Freshness Windows**: 5 seconds for play_state (changes frequently)
7. **Transition States**: Special handling for "load", "loading", "transitioning"
8. **Conflict Resolution**: Freshness > Priority > Recency

---

## Position Tracking

### Overview

The `pywiim` library uses a **hybrid approach** for tracking playback position that combines local estimation with periodic polling corrections. This provides smooth position updates while maintaining accuracy and reducing network traffic.

### Problem Statement

#### The Challenge

Playback position is a continuously changing value that needs to be:
- **Smooth**: Updates should appear continuous, not jumpy
- **Accurate**: Must reflect actual device position
- **Efficient**: Minimize network traffic and device load
- **Responsive**: Handle manual seeks and track changes immediately

#### Previous Approach (Polling Only)

The original implementation polled the device every 1 second during playback:
- ✅ Always accurate (no drift)
- ✅ Handles seeks automatically
- ❌ High network overhead (1 request/second)
- ❌ 1-second update latency (jumpy UI)
- ❌ Not smooth for user interfaces

#### UPnP Events Approach

UPnP events could theoretically provide position updates, but:
- ❌ WiiM devices don't send position updates in UPnP events during continuous playback
- ❌ Events only occur on discrete state changes (play/pause/stop)
- ❌ Position updates are only available via HTTP polling

### Solution: Hybrid Position Tracking with Active Timer

#### How It Works

1. **Active Timer**: Background async task updates position every 1 second while playing
2. **Local Estimation**: Position is estimated locally based on elapsed time
3. **Periodic Correction**: Device is polled every 5 seconds to correct any drift
4. **Seek Detection**: Position jumps (>2s backward or >10s forward) reset estimation
5. **Track Change Detection**: Metadata changes reset estimation
6. **Automatic Callbacks**: Timer triggers `on_state_changed` callback when position changes

#### Implementation Details

```python
# Position estimation state
_estimated_position: int | None = None
_estimation_start_time: float | None = None
_estimation_base_position: int | None = None

# Position timer (for active updates)
_position_timer_task: asyncio.Task | None = None
_position_timer_running: bool = False

# Active timer loop (runs in background while playing)
async def _position_timer_loop(self):
    while self._position_timer_running:
        if is_playing and estimation_base is not None:
            elapsed = time.time() - estimation_start_time
            estimated = estimation_base + int(elapsed)
            # Update position and trigger callback every second
            if position_changed_by_1_second:
                self._estimated_position = estimated
                self._on_state_changed()  # Notify clients
        await asyncio.sleep(1.0)

# When device provides new position (from polling/UPnP):
if new_position is not None:
    # Reset estimation base
    estimation_base = new_position
    estimation_start_time = time.time()
    # Start timer if playing (for active updates)
    if is_playing:
        _start_position_timer()
```

#### Key Features

1. **Active Updates**: Background timer updates position every 1 second while playing
2. **Smooth Updates**: Position increments smoothly between polls
3. **Automatic Callbacks**: Timer triggers `on_state_changed` when position changes (for UI updates)
4. **Self-Correcting**: Periodic polling (every 5s) corrects drift
5. **Seek Handling**: Detects position jumps and resets estimation (stops timer)
6. **Track Change Handling**: Resets on metadata changes (stops timer)
7. **Drift Limiting**: Maximum 30 seconds of estimation before requiring correction
8. **Lifecycle Management**: Timer automatically starts/stops based on play state

#### Polling Strategy Changes

**Before (v1.0.6)**:
- Playing: Poll every 1 second
- Idle: Poll every 5 seconds

**After (v1.0.7)**:
- Playing: Poll every 5 seconds (hybrid estimation handles smooth updates)
- Idle: Poll every 5 seconds (unchanged)

**Result**: 80% reduction in network traffic during playback

### Benefits

#### User Experience
- ✅ Smooth position updates (no visible jumps)
- ✅ Real-time UI updates via automatic callbacks
- ✅ Responsive to seeks and track changes
- ✅ Accurate position display

#### Performance
- ✅ 80% less network traffic during playback
- ✅ Reduced device load
- ✅ Lower battery usage for mobile applications

#### Reliability
- ✅ Self-correcting (periodic polling fixes drift)
- ✅ Handles edge cases (seeks, track changes, pauses)
- ✅ Graceful degradation (falls back to polling if estimation fails)

### Edge Cases Handled

#### Manual Seeks
- **Detection**: Position jump >2 seconds backward or >10 seconds forward
- **Action**: Reset estimation base to new position
- **Result**: Position immediately reflects seek

#### Track Changes
- **Detection**: Metadata (title/artist/album) changes
- **Action**: Reset estimation
- **Result**: Position resets to 0 for new track

#### Pauses
- **Detection**: Play state changes to "pause" or "stop"
- **Action**: Return actual position from device (no estimation)
- **Result**: Position stays accurate when paused

#### Drift Accumulation
- **Prevention**: Maximum 30 seconds of estimation before requiring correction
- **Action**: If estimation exceeds limit, return actual position from device
- **Result**: Prevents long-term drift

#### Network Delays
- **Handling**: Estimation continues even if poll is delayed
- **Correction**: Next successful poll corrects any accumulated drift
- **Result**: Resilient to temporary network issues

### Configuration

The hybrid approach is enabled by default and requires no configuration. The polling intervals are:

```python
# From pywiim/polling.py
FAST_POLL_INTERVAL = 5.0  # During playback (with hybrid estimation)
NORMAL_POLL_INTERVAL = 5.0  # When idle
```

These can be adjusted if needed, but 5 seconds provides a good balance between accuracy and efficiency.

### Comparison with Other Libraries

#### Sonos SoCo Library
- Uses similar hybrid approach
- Combines local estimation with periodic polling
- Industry best practice for UPnP/DLNA devices

#### Home Assistant Media Players
- Most use polling-only approach (simpler)
- Some use hybrid approach for better UX
- Hybrid is preferred for smooth UI updates

---

## Caching Architecture

The library uses a **two-layer caching system**:

1. **Player Cache** - Caches `PlayerStatus` and `DeviceInfo` models from HTTP polling
2. **StateSynchronizer** - Merges HTTP polling + UPnP events with conflict resolution

### Player Cache (`_status_model`, `_device_info`)

**What's Cached:**
- `_status_model: PlayerStatus | None` - Complete player status from HTTP API
- `_device_info: DeviceInfo | None` - Device information from HTTP API

**When It's Updated:**
- **HTTP Polling**: `await player.refresh()` queries device and updates cache
- **UPnP Events**: `player.update_from_upnp(data)` merges UPnP data into cached models via StateSynchronizer

**Access Patterns:**
- **Cached Properties** (synchronous, fast): `player.volume_level`, `player.play_state`, `player.media_title` - read from `_status_model`
- **Async Methods** (always fresh): `await player.get_status()`, `await player.get_device_info()` - query device directly
- **Client Methods** (separate endpoints): `await player.client.get_audio_output_status()` - for data not in status response

### StateSynchronizer (HTTP + UPnP Merging)

**Purpose:**
- Merges data from HTTP polling and UPnP events
- Resolves conflicts (which source is fresher/more reliable)
- Handles stale data and missing sources

**What It Synchronizes:**
- `play_state`, `position`, `duration`
- `volume`, `muted`
- `source`
- `title`, `artist`, `album`, `image_url`

**How It Works:**
1. HTTP polling calls `_state_synchronizer.update_from_http(status_dict)`
2. UPnP events call `_state_synchronizer.update_from_upnp(event_dict)`
3. StateSynchronizer merges both sources with conflict resolution
4. Player updates `_status_model` with merged state

## Related Documentation

- **[UPNP_INTEGRATION.md](UPNP_INTEGRATION.md)** - How UPnP events are integrated
- **[API_DESIGN_PATTERNS.md](API_DESIGN_PATTERNS.md)** - HTTP API reference
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Overall library architecture
- **[HA_INTEGRATION.md](../integration/HA_INTEGRATION.md)** - Polling strategy implementation and usage

