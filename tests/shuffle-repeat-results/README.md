# Shuffle/Repeat Testing Results

This directory contains test results from systematic shuffle/repeat testing across different sources and content types.

## Purpose

To systematically test and document which sources and content types support shuffle/repeat controls, helping to refine the library's blacklist and ensure accurate predictions.

## Key Insight

**Content type matters!** For example:
- Spotify albums (on-demand content) may support shuffle/repeat controls
- Spotify radio stations (algorithmic streaming) may NOT support shuffle/repeat controls

The same applies to other services - the source alone doesn't tell the full story.

## Testing Tools

### Quick Testing (Single Source)

Use when you want to quickly test the current playing source:

```bash
source .venv/bin/activate
python scripts/test-shuffle-repeat-once.py <device_ip> "<content_description>"
```

**Example:**
```bash
python scripts/test-shuffle-repeat-once.py 192.168.1.115 "Spotify Album - Rumors"
```

Tests shuffle and repeat on the current source, shows results, and restores initial state.

### Comprehensive Testing (Multiple Sources)

Use for systematic testing across many sources with persistent results:

```bash
source .venv/bin/activate
python scripts/test-shuffle-repeat-by-source.py <device_ip>
```

**Interactive workflow:**
1. Script connects to device and starts interactive session
2. Start playing content on device (via WiiM app or other app)
3. Return to script and press `[t]` to test current source
4. Provide descriptive name: `Spotify Album - Fleetwood Mac`
5. Script tests shuffle and repeat controls
6. Repeat for different sources and content types
7. Press `[r]` to view summary or `[q]` to quit and save

**Results saved to:** `tests/shuffle-repeat-results/shuffle_repeat_test_<model>_<timestamp>.json`

## Test Results Format

```json
{
  "device_name": "Living Room",
  "device_model": "WiiM Pro",
  "source_tests": [
    {
      "source_name": "spotify",
      "content_description": "Spotify Album - Rumors",
      "shuffle_supported_predicted": true,
      "repeat_supported_predicted": true,
      "shuffle_actually_works": true,
      "repeat_actually_works": true,
      ...
    }
  ],
  "summary": {
    "sources_tested": 5,
    "shuffle_works_count": 3,
    "repeat_works_count": 3,
    "prediction_mismatches": [...]
  }
}
```

## Testing Checklist

### High Priority Sources

**Spotify:**
- [ ] Album - "Spotify Album - Rumors by Fleetwood Mac"
- [ ] Playlist - "Spotify Playlist - My Liked Songs"
- [ ] Radio - "Spotify Radio - Daily Mix 1"
- [ ] Podcast - "Spotify Podcast - The Daily"

**Amazon Music:**
- [ ] Album - "Amazon Music Album - 1989"
- [ ] Playlist - "Amazon Music Playlist - Top 50"
- [ ] Station - "Amazon Music Station - Pop Hits"

**Local Storage:**
- [ ] USB Folder - "USB - Music/Rock Folder"
- [ ] USB Playlist - "USB - Favorites.m3u"

**Physical Inputs:**
- [ ] Line In - "Line In - CD Player"
- [ ] Optical - "Optical - TV Audio"
- [ ] Bluetooth - "Bluetooth - iPhone Music App"

**AirPlay:**
- [ ] Apple Music Album - "AirPlay - Apple Music Album"
- [ ] Apple Music Radio - "AirPlay - Apple Music 1 Radio"

**TuneIn:**
- [ ] Live Radio - "TuneIn - BBC Radio 1"
- [ ] Podcast - "TuneIn Podcast - Serial"

### Medium Priority

**Tidal, Qobuz, Deezer:**
- [ ] Album playback
- [ ] Playlist playback
- [ ] Radio/Discovery

**DLNA:**
- [ ] Media Server Album
- [ ] Network Share Folder

## Expected Patterns

Based on LinkPlay architecture:

### ✅ Should Work (Device Controls)
- USB, SD card (local files)
- Physical inputs (Line In, Optical, Coax)
- On-demand albums and playlists (queue-based)

### ❌ Should NOT Work (External Control)
- Live radio streams (no queue to shuffle)
- Algorithmic radio (no fixed queue)
- AirPlay (iOS controls it)
- Multiroom slaves (can't control master)

### ❓ Needs Testing
- Spotify albums vs radio
- Amazon Music albums vs stations
- Tidal, Qobuz, Deezer
- DLNA sources

## After Testing

1. **Review Results**: Look for patterns and prediction mismatches
2. **Update Blacklist**: Modify `pywiim/player/properties.py` if needed
3. **Document Findings**: Update design docs with empirical results

## Historical Context

From CHANGELOG:
- **v2.1.2**: Fixed loop_mode interpretation for WiiM/Arylic devices
- **v2.1.1**: Changed to blacklist approach (permissive by default)
- **v1.0.71**: Added source-aware shuffle/repeat support

The goal is to use empirical testing to refine predictions and document what actually works.