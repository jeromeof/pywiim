# Player State Architecture - Data Flow & Source of Truth

## Overview

The Player tracks state from **TWO sources** simultaneously:
1. **HTTP Polling** - periodic queries (e.g., every 5 seconds)
2. **UPnP Events** - real-time push notifications when state changes

These two sources are merged together to provide the most current state.

## The Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                            │
│  (monitor, properties, commands - what users/code interact with)    │
└────────────────────────┬────────────────────────────────────────────┘
                         │ reads from
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MERGE LAYER (NEW)                             │
│                     StateSynchronizer                                │
│  ┌────────────────┐      ┌─────────────┐      ┌─────────────────┐  │
│  │  HTTP State    │      │   MERGED    │      │   UPnP State    │  │
│  │  (polling)     │─────▶│   STATE     │◀─────│   (events)      │  │
│  │  5s intervals  │      │ (live truth)│      │   real-time     │  │
│  └────────────────┘      └─────────────┘      └─────────────────┘  │
│         │                       │                      │             │
│         │ Conflict Resolution:  │                      │             │
│         │  • play_state: prefer UPnP (immediate)       │             │
│         │  • metadata: prefer HTTP (complete)          │             │
│         │  • position: estimate between updates        │             │
│         └───────────────────────┴──────────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                         │ updates (for backwards compat)
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CACHE LAYER (LEGACY)                            │
│                    Player._status_model                              │
│  ┌───────────────────────────────────────────────────────────┐      │
│  │  Cached PlayerStatus (updated from merged state)          │      │
│  │  • Originally: only updated during HTTP polling           │      │
│  │  • Now: synced from merged state for backwards compat     │      │
│  └───────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
                 (Used to be read by properties
                  - now deprecated, but kept
                  for backwards compatibility)
```

## Data Flow: Step by Step

### 1. HTTP Polling (Every 5 seconds)

```python
# In monitor_loop or periodic refresh:
await player.refresh()  # StateManager.refresh()
    │
    ├─▶ status = client.get_player_status_model()  # HTTP call to device
    │
    ├─▶ _state_synchronizer.update_from_http(status_dict)
    │   │   Stores data in: _http_state = {
    │   │       "play_state": TimestampedField(value="play", source="http", timestamp=123456),
    │   │       "volume": TimestampedField(...),
    │   │       "title": TimestampedField(...),
    │   │       ...
    │   │   }
    │   └─▶ _merge_state()  # Merge HTTP + UPnP → _merged_state
    │
    └─▶ _status_model = status  # Update cache (legacy)
        └─▶ Sync _status_model from merged state (for backwards compat)
```

### 2. UPnP Events (Real-time, when changes occur)

```python
# When device sends UPnP event:
upnp_callback(changes)  # changes = {"play_state": "stop", "volume": 50}
    │
    └─▶ player.apply_diff(changes)  # StateManager.apply_diff()
        │
        ├─▶ _state_synchronizer.update_from_upnp(changes)
        │   │   Stores data in: _upnp_state = {
        │   │       "play_state": TimestampedField(value="stop", source="upnp", timestamp=123457),
        │   │       "volume": TimestampedField(...),
        │   │       ...
        │   │   }
        │   └─▶ _merge_state()  # Merge HTTP + UPnP → _merged_state
        │
        └─▶ Update _status_model from merged state (for backwards compat)
```

### 3. Reading State (Properties)

**BEFORE (Broken):**
```python
@property
def play_state(self) -> str | None:
    # ❌ WRONG: Only reads cached HTTP data (5s stale)
    return self._status_model.play_state
```

**AFTER (Fixed):**
```python
@property
def play_state(self) -> str | None:
    # ✅ CORRECT: Reads merged state (HTTP + UPnP)
    merged = self._state_synchronizer.get_merged_state()
    return merged.get("play_state")
```

## Source of Truth: StateSynchronizer._merged_state

The **single source of truth** is:

```python
StateSynchronizer._merged_state  # SynchronizedState object
```

This contains **merged data** from both HTTP and UPnP, resolved using smart conflict resolution:

### Conflict Resolution Rules

When both HTTP and UPnP have data for the same field:

| Field | Priority | Reason |
|-------|----------|--------|
| `play_state` | **UPnP** > HTTP | Real-time state changes are immediate via UPnP |
| `volume` | **UPnP** > HTTP | Volume changes are immediate via UPnP |
| `muted` | **UPnP** > HTTP | Mute changes are immediate via UPnP |
| `position` | **UPnP** > HTTP | UPnP fires on track start, then estimated locally |
| `duration` | **UPnP** > HTTP | UPnP fires on track start |
| `title` | **HTTP** > UPnP | HTTP metadata is more complete |
| `artist` | **HTTP** > UPnP | HTTP metadata is more complete |
| `album` | **HTTP** > UPnP | HTTP metadata is more complete |
| `image_url` | **HTTP** > UPnP | HTTP artwork URLs are more reliable |
| `source` | **HTTP** > UPnP | HTTP source reporting is more accurate |

**Exception:** For Spotify, metadata ONLY comes from UPnP events. HTTP API does not provide Spotify metadata.

### Freshness Windows

Data is considered "fresh" for different durations:

```python
FRESHNESS_WINDOWS = {
    "play_state": 5.0,   # Changes frequently
    "position": 2.0,      # Changes very frequently  
    "volume": 10.0,       # Changes less frequently
    "title": 30.0,        # Changes less frequently
    "source": 60.0,       # Changes rarely
}
```

If data exceeds its freshness window, it's considered stale and the other source is preferred.

## What We Cache and Why

### 1. `StateSynchronizer._merged_state` (Primary State)
**What:** Merged HTTP + UPnP data with timestamps and source tracking
**Why:** Single source of truth, real-time accurate
**Updated:** Immediately on HTTP poll OR UPnP event

### 2. `Player._status_model` (Legacy Cache)
**What:** Raw HTTP API response, synced with merged state
**Why:** Backwards compatibility - older code may still read this
**Updated:** 
- Every HTTP poll (refresh)
- After UPnP events (synced from merged state)

### 3. `Player._device_info` (Device Info Cache)
**What:** Device capabilities, firmware, model, etc.
**Why:** Rarely changes, expensive to query
**Updated:** Every HTTP poll (refresh)

### 4. Other Caches
- `_audio_output_status` - Audio output config (rare changes)
- `_eq_presets` - Available EQ presets (rare changes)
- `_metadata` - Audio quality info (changes per track)
- `_bluetooth_history` - Paired BT devices (checked every 60s)
- `_cover_art_cache` - Downloaded album art images (1hr TTL)

## Position Estimation: Now Unified! ✅

Position estimation is now **centralized** in one place:

### StateSynchronizer Position Estimation (The One Source)
```python
StateSynchronizer._get_estimated_position()
    _estimation_base_position = 100  # Last known position
    _estimation_start_time = 123456  # When we got that position
    
    # While playing:
    elapsed = now - _estimation_start_time
    estimated = _estimation_base_position + elapsed
```

### How Other Components Use It

**Player.media_position Property:**
```python
@property
def media_position(self):
    # Reads position from merged state (already estimated)
    merged = self._state_synchronizer.get_merged_state()
    return merged.get("position")  # ✅ Single source of truth
```

**Player Position Timer:**
```python
async def _position_timer_loop(self):
    # Ticks position forward in StateSynchronizer, triggers callbacks
    position = self._state_synchronizer.tick_position_estimation()
    # ✅ Explicitly updates estimation every second (fills in between HTTP polls)
    if position_changed:
        self._on_state_changed()  # Notify clients
```

**Result:** One estimation algorithm, multiple consumers. Clean architecture! ✅

### How Position Updates Between HTTP Polls

While playing, position needs to be updated every second even though HTTP polls only happen every 5 seconds:

```
Time 0: HTTP poll → position = 100
         ↓ StateSynchronizer stores: base_position=100, start_time=0

Time 1: Timer tick → tick_position_estimation()
         ↓ Calculates: 100 + (1 - 0) = 101
         ↓ Updates _last_position = 101
         ↓ Triggers callback → Monitor displays 101

Time 2: Timer tick → tick_position_estimation()  
         ↓ Calculates: 100 + (2 - 0) = 102
         ↓ Updates _last_position = 102
         ↓ Triggers callback → Monitor displays 102

Time 5: HTTP poll → position = 105
         ↓ Updates: base_position=105, start_time=5
         ↓ (Accounts for any drift that accumulated)
```

The timer **fills in the gaps** between HTTP polls, providing smooth second-by-second updates.

## Why Did We Have This Mess?

### Historical Evolution:

**Phase 1:** Simple HTTP polling only
```python
Player._status_model = await client.get_status()
```

**Phase 2:** Added UPnP events (needed real-time updates)
```python
# Problem: HTTP cache is stale, UPnP events need to update it
```

**Phase 3:** Added StateSynchronizer to merge both sources
```python
StateSynchronizer merges HTTP + UPnP intelligently
```

**Phase 4:** Properties never updated to use StateSynchronizer
```python
# ❌ Properties still reading old cache
# ❌ UPnP events updating merged state, but nobody reading it
# ❌ Monitor shows stale data from cache
```

**Phase 5 (NOW):** Fixed properties to read merged state
```python
# ✅ Properties now read from StateSynchronizer
# ✅ Real-time UPnP updates now visible
# ✅ Cache kept for backwards compatibility only
```

## Summary: What's the Source of Truth?

| Component | Source of Truth | Why |
|-----------|----------------|-----|
| **Real-time state** | `StateSynchronizer._merged_state` | Merges HTTP + UPnP with conflict resolution |
| **Player properties** | Read from `_merged_state` | Always current, real-time accurate |
| **Legacy cache** | `Player._status_model` | Synced from merged state, backwards compat |
| **Device info** | `Player._device_info` | Cached, updated every poll |

## What We Cleaned Up ✅

1. ✅ **Removed duplicate position estimation** - Only StateSynchronizer version remains
2. ✅ **All properties now read from merged state** - Real-time UPnP updates work
3. ✅ **Position timer simplified** - Now reads from StateSynchronizer
4. ✅ **Removed 9 duplicate tracking fields from Player** - Much cleaner architecture

## Future Improvements (Optional)

1. **Deprecate direct `_status_model` access** - Force all reads through properties
2. **Consider removing `_status_model` entirely** - It's now just a synced copy for backwards compat
3. **Add deprecation warnings** - Warn if code tries to access `_status_model` directly

## Recommendation: Read State the Right Way

**DO:**
```python
play_state = player.play_state  # Reads from merged state ✅
volume = player.volume_level     # Reads from merged state ✅
title = player.media_title       # Reads from merged state ✅
```

**DON'T:**
```python
play_state = player._status_model.play_state  # Bypasses merge logic ❌
```

The properties are now the **correct API** - they hide the complexity of the merge layer.

