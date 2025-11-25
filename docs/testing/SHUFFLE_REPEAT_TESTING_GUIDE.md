# Shuffle/Repeat Testing Guide

This guide explains how to systematically test shuffle and repeat controls across different sources to identify what works and what doesn't.

## Background

Shuffle and repeat support has been a thorny issue in pywiim, with multiple fixes over time:

- **v2.1.2**: Fixed loop_mode interpretation (Issue #111)
- **v2.1.1**: Changed to blacklist approach (permissive by default)
- **v1.0.71**: Added source-aware shuffle/repeat control

Despite these fixes, the relationship between sources, content types, and shuffle/repeat support isn't fully understood. **This testing helps us nail it down once and for all.**

## Key Insight: Content Type Matters

The source alone doesn't determine shuffle/repeat support. **Content type matters!**

Examples:
- **Spotify Album** (on-demand): Shuffle/repeat may work
- **Spotify Radio** (algorithmic): Shuffle/repeat may NOT work
- **TuneIn Podcast** (on-demand): Might support controls
- **TuneIn Live Radio** (streaming): Doesn't support controls

## Testing Strategy

### 1. Environment Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Ensure you have a WiiM device on the network
# Note the device IP address
```

### 2. Run the Test Script

```bash
python scripts/test-shuffle-repeat-by-source.py <device_ip>

# Example:
python scripts/test-shuffle-repeat-by-source.py 192.168.1.100
```

### 3. Interactive Testing Process

The script provides an interactive menu:

```
Options:
  [t] Test current source
  [r] Print results summary
  [q] Quit and save results
```

**Workflow:**

1. Use the WiiM app to start playing content from a source
2. In the test script, press `[t]` to test current source
3. Provide a descriptive name when prompted:
   ```
   Describe what's playing (source + content type): Spotify Album - Rumors by Fleetwood Mac
   ```
4. Script will:
   - Check library's prediction (shuffle_supported, repeat_supported)
   - Test enabling shuffle
   - Test disabling shuffle
   - Test repeat modes (all, one, off)
   - Check if state is preserved when toggling
   - Compare prediction vs reality
5. Repeat for different sources and content types

### 4. Sources and Content Types to Test

#### High Priority

| Source | Content Type | Example |
|--------|-------------|---------|
| Spotify | Album | "Spotify Album - Rumors" |
| Spotify | Radio/Mix | "Spotify Radio - Daily Mix 1" |
| Amazon Music | Album | "Amazon Music Album - 1989" |
| Amazon Music | Station | "Amazon Music Station - Pop Hits" |
| TuneIn | Live Radio | "TuneIn - BBC Radio 1" |
| TuneIn | Podcast | "TuneIn Podcast - The Daily" |
| USB | Folder | "USB - Music Folder" |
| Line In | Physical | "Line In - CD Player" |
| AirPlay | Album | "AirPlay - Apple Music Album" |
| AirPlay | Radio | "AirPlay - Apple Music Radio" |

#### Medium Priority

| Source | Content Type | Example |
|--------|-------------|---------|
| Tidal | Album | "Tidal Album - The Dark Side" |
| Qobuz | Album | "Qobuz Album - Kind of Blue" |
| Deezer | Playlist | "Deezer Playlist - Top 50" |
| Bluetooth | Phone | "Bluetooth - iPhone Music" |
| Optical | External | "Optical - TV Audio" |
| DLNA | Media Server | "DLNA - Plex Library" |

#### Low Priority

| Source | Content Type | Example |
|--------|-------------|---------|
| Pandora | Station | "Pandora - Classic Rock" |
| iHeartRadio | Station | "iHeartRadio - Z100" |
| Preset | Saved Station | "Preset 1 - NPR" |

### 5. What the Script Tests

For each source, the script:

1. **Records initial state**:
   - Source name
   - Play state
   - Current shuffle state
   - Current repeat mode
   - Loop mode value

2. **Checks library prediction**:
   - `shuffle_supported` (what library thinks)
   - `repeat_supported` (what library thinks)

3. **Tests shuffle**:
   - Enable shuffle → verify state changed
   - Disable shuffle → verify state changed
   - Check if repeat mode was preserved

4. **Tests repeat**:
   - Set repeat "all" → verify
   - Set repeat "one" → verify
   - Set repeat "off" → verify
   - Check if shuffle state was preserved

5. **Compares prediction vs reality**:
   - Did shuffle actually work when library said it would?
   - Did repeat actually work when library said it would?
   - Flags mismatches for further investigation

### 6. Understanding Results

#### Test Output

```
📊 Testing Source: spotify
📝 Content: Spotify Album - Rumors

📋 Initial State:
   Source: spotify
   Play State: play
   Shuffle: False
   Repeat: off
   Loop Mode: 0

🔮 Library Prediction:
   Shuffle Supported: True
   Repeat Supported: True

🎲 Testing Shuffle Controls:
   → Setting shuffle ON...
      ✓ Shuffle state: True
      ✓ Loop mode: 4
      ✓ Repeat preserved: True
   → Setting shuffle OFF...
      ✓ Shuffle state: False
      ✓ Loop mode: 0
      ✅ Shuffle controls WORK

🔁 Testing Repeat Controls:
   → Setting repeat ALL...
      ✓ Repeat mode: all
      ✓ Loop mode: 2
   ...
      ✅ Repeat controls WORK

📊 Assessment:
   ✅ Shuffle: WORKS
   ✅ Repeat: WORKS
```

#### Result Symbols

- ✅ = Control works as expected
- ❌ = Control does not work
- ⚠️ = Test failed or results unclear
- 🔮 = Library prediction (may be wrong!)

### 7. Analyzing Results

After testing multiple sources, review the JSON results file:

```bash
# Results are saved to:
tests/shuffle-repeat-results/shuffle_repeat_test_<model>_<timestamp>.json
```

Look for:

1. **Consistent patterns**: Sources/content types that always work or never work
2. **Prediction mismatches**: Where the library is wrong
3. **Content-type differences**: Same source, different behavior based on content
4. **Loop mode values**: What loop_mode values correspond to what states

### 8. Using Results to Improve the Library

#### Update the Blacklist

Based on test results, update `pywiim/player/properties.py`:

```python
def _is_device_controlled_source(self) -> bool:
    """Check if current source allows device-controlled playback."""
    source = self.source
    if source is None:
        return False
    
    source_lower = source.lower()
    
    # Blacklist: Sources where device CANNOT control shuffle/repeat
    external_controlled = {
        "tunein",        # Radio streams - confirmed by testing
        "iheartradio",   # Radio streams - confirmed by testing
        "multiroom",     # Slave device - cannot control
        # Add more based on test results
    }
    
    if source_lower in external_controlled:
        return False
    
    # Additional checks for radio-like keywords
    radio_keywords = ["radio", "stream"]
    if any(keyword in source_lower for keyword in radio_keywords):
        return False
    
    return True
```

#### Document Findings

Update `docs/design/SHUFFLE_REPEAT_SUPPORT.md` with:
- Which sources work
- Which content types within sources have different behavior
- Known exceptions
- Recommended approach for integrations

#### Update Tests

Update `tests/unit/test_player.py` to reflect findings:

```python
@pytest.mark.asyncio
async def test_shuffle_supported_sources(mock_client):
    """Test shuffle_supported based on empirical testing results."""
    player = Player(mock_client)
    
    # Confirmed working sources (from test results)
    working_sources = ["spotify", "usb", "line_in", "optical"]
    for source in working_sources:
        status = PlayerStatus(source=source, play_state="play")
        player._status_model = status
        assert player.shuffle_supported is True
    
    # Confirmed non-working sources (from test results)
    non_working_sources = ["tunein", "iheartradio"]
    for source in non_working_sources:
        status = PlayerStatus(source=source, play_state="play")
        player._status_model = status
        assert player.shuffle_supported is False
```

## Best Practices

1. **Test systematically**: Don't skip sources, test each one
2. **Be specific**: "Spotify Album" vs "Spotify Radio" matters
3. **Note anomalies**: If behavior is weird, note it in the description
4. **Test multiple times**: Some sources may be flaky
5. **Save results**: Don't lose your test data!

## Expected Findings

Based on LinkPlay architecture (CHANGELOG v1.0.71):

### Likely to Work
- USB local files
- Physical inputs (Line In, Optical, Coax)
- Bluetooth (if device is controller)
- On-demand content (albums, playlists)

### Likely NOT to Work
- Live radio streams
- Algorithmic radio (Spotify Radio, Pandora)
- AirPlay (iOS controls it)
- Content where the app/service controls playback

### Needs Testing
- Spotify albums vs radio
- Amazon Music albums vs stations
- Tidal, Qobuz, Deezer
- DLNA sources
- Podcasts

## Troubleshooting

### Script shows "No active source detected"

The device isn't playing anything. Start playback in the WiiM app first.

### Shuffle/Repeat test fails immediately

The source might be blacklisted or the library correctly predicted it won't work. Check the error message.

### Results seem inconsistent

Some sources may have timing issues. Try:
- Waiting a few seconds after starting playback
- Letting content play for a bit before testing
- Testing the same source multiple times

### Script crashes

Check:
- Device is on network and accessible
- Virtual environment is activated
- No network issues

## Contributing Results

If you complete comprehensive testing:

1. Share your JSON results files
2. Document any surprising findings
3. Suggest blacklist updates based on patterns
4. Note any content-type-specific behavior

This helps improve pywiim for everyone!

## Questions?

If you're unsure about:
- How to describe content: Be as specific as possible
- Whether to test something: When in doubt, test it!
- Interpreting results: Look at the "Assessment" section in output

The goal is to build empirical knowledge of what actually works, so we can make the library as accurate as possible.

