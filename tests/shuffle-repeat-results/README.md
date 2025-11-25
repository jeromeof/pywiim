# Shuffle/Repeat Testing Results

This directory contains test results from systematic shuffle/repeat testing across different sources and content types.

## Purpose

To systematically test and document which sources and content types support shuffle/repeat controls, helping to finally resolve the long-standing shuffle/repeat issues documented in the CHANGELOG.

## Key Insight

**Content type matters!** For example:
- Spotify albums (on-demand content) may support shuffle/repeat controls
- Spotify radio stations (algorithmic streaming) may NOT support shuffle/repeat controls

The same applies to other services - the source alone doesn't tell the full story.

## Test Results Format

Each test run generates a JSON file with the following structure:

```json
{
  "device_name": "Living Room",
  "device_model": "WiiM Pro",
  "device_firmware": "4.8.731953",
  "device_ip": "192.168.1.100",
  "test_start": "2025-11-25T10:30:00",
  "test_end": "2025-11-25T11:15:00",
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

## How to Test

### 1. Run the Test Script

```bash
# Activate venv first
source .venv/bin/activate

# Run interactive testing
python scripts/test-shuffle-repeat-by-source.py 192.168.1.100
```

### 2. Test Different Sources

For each source you want to test:

1. Use the WiiM app (or other app) to start playing content
2. Return to the test script
3. Choose option `[t]` to test current source
4. Provide a descriptive name like: `Spotify Album - Fleetwood Mac`
5. Script will test shuffle and repeat controls
6. Repeat for different sources and content types

### 3. Important Content Types to Test

#### Spotify
- ✓ Album playback
- ✓ Playlist playback
- ✓ Radio station
- ✓ Artist Radio

#### Amazon Music
- ✓ Album playback
- ✓ Playlist playback
- ✓ Station

#### TuneIn / iHeartRadio
- ✓ Live radio station
- ✓ Podcast

#### USB / Local Files
- ✓ Folder playback
- ✓ Playlist

#### Physical Inputs
- ✓ Line In
- ✓ Optical
- ✓ Bluetooth

#### AirPlay
- ✓ Apple Music album
- ✓ Apple Music radio
- ✓ Podcast

### 4. Review Results

After testing, the script will:
- Save detailed JSON results
- Print a summary showing what works and what doesn't
- Highlight prediction mismatches (where the library is wrong)

## Analysis

After collecting test results, review them to:

1. **Identify patterns**: Which sources/content types consistently work or don't work?
2. **Find prediction mismatches**: Where is the library incorrectly predicting support?
3. **Update the blacklist**: Based on results, update `pywiim/player/properties.py`'s `_is_device_controlled_source()` method
4. **Document exceptions**: Some sources may need content-type-aware logic

## Expected Patterns

Based on LinkPlay architecture (from CHANGELOG v1.0.71):

### Should Work (Device is Control Point)
- USB local files
- Physical inputs (Line In, Optical, Coax)
- Local playlists

### May Not Work (External Control)
- AirPlay (iOS device controls)
- Bluetooth (source device controls)
- Spotify Radio (algorithmic, not queue-based)
- Live radio streams (TuneIn, iHeartRadio)
- Spotify Connect on some content types

### Needs Testing
- Spotify albums/playlists
- Amazon Music albums/playlists
- Tidal, Qobuz, Deezer
- DLNA sources

## Historical Context

From CHANGELOG:
- **v2.1.2 (Issue #111)**: Fixed loop_mode interpretation for WiiM/Arylic devices
- **v2.1.1**: Changed to blacklist approach (permissive by default)
- **v1.0.71**: Added source-aware shuffle/repeat support

The goal is to use empirical testing to refine the blacklist and document what actually works.

