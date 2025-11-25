# Shuffle/Repeat Testing Checklist

Use this checklist to systematically test shuffle and repeat controls across sources and content types.

## Quick Start

```bash
source .venv/bin/activate
python scripts/test-shuffle-repeat-by-source.py <device_ip>
```

## Testing Matrix

### High Priority Sources

#### Spotify
- [ ] **Album** - "Spotify Album - Rumors by Fleetwood Mac"
- [ ] **Playlist** - "Spotify Playlist - My Liked Songs"
- [ ] **Radio** - "Spotify Radio - Daily Mix 1"
- [ ] **Artist Radio** - "Spotify Artist Radio - Fleetwood Mac"
- [ ] **Podcast** - "Spotify Podcast - The Daily"

#### Amazon Music
- [ ] **Album** - "Amazon Music Album - 1989 by Taylor Swift"
- [ ] **Playlist** - "Amazon Music Playlist - Top 50"
- [ ] **Station** - "Amazon Music Station - Pop Hits"
- [ ] **Radio** - "Amazon Music Radio - My Soundtrack"

#### TuneIn
- [ ] **Live Radio** - "TuneIn - BBC Radio 1"
- [ ] **Live Radio (Talk)** - "TuneIn - NPR News"
- [ ] **Podcast** - "TuneIn Podcast - Serial"
- [ ] **Music Station** - "TuneIn - Classic FM"

#### Local Storage
- [ ] **USB Folder** - "USB - Music/Rock Folder"
- [ ] **USB Playlist** - "USB - Favorites.m3u"
- [ ] **SD Card** - "SD Card - Albums Folder"

#### Physical Inputs
- [ ] **Line In** - "Line In - CD Player"
- [ ] **Optical** - "Optical - TV Audio"
- [ ] **Coaxial** - "Coaxial - External DAC"
- [ ] **Bluetooth** - "Bluetooth - iPhone Music App"

#### AirPlay
- [ ] **Apple Music Album** - "AirPlay - Apple Music Album"
- [ ] **Apple Music Radio** - "AirPlay - Apple Music 1 Radio"
- [ ] **Podcast** - "AirPlay - Apple Podcasts"
- [ ] **YouTube Music** - "AirPlay - YouTube Music"

### Medium Priority Sources

#### Tidal
- [ ] **Album** - "Tidal Album - Kind of Blue"
- [ ] **Playlist** - "Tidal Playlist - Jazz Classics"
- [ ] **Radio** - "Tidal Radio - My Daily Discovery"

#### Qobuz
- [ ] **Album** - "Qobuz Album - The Dark Side of the Moon"
- [ ] **Playlist** - "Qobuz Playlist - Best of Classical"

#### Deezer
- [ ] **Album** - "Deezer Album - Random Access Memories"
- [ ] **Playlist** - "Deezer Playlist - Flow"
- [ ] **Radio** - "Deezer Radio - Artist Radio"

#### DLNA
- [ ] **Media Server Album** - "DLNA - Plex Server Album"
- [ ] **Media Server Playlist** - "DLNA - Plex Playlist"
- [ ] **Network Share** - "DLNA - NAS Music Folder"

### Low Priority Sources

#### Pandora
- [ ] **Station** - "Pandora - Classic Rock Station"

#### iHeartRadio
- [ ] **Live Radio** - "iHeartRadio - Z100 New York"
- [ ] **Podcast** - "iHeartRadio Podcast"

#### Presets
- [ ] **Preset 1** - "Preset 1 - NPR"
- [ ] **Preset 2** - "Preset 2 - BBC Radio 4"

## What to Record for Each Test

When testing each source, the script automatically records:

- ✅ **Library Prediction**: Does pywiim think it's supported?
- ✅ **Actual Behavior**: Does shuffle/repeat actually work?
- ✅ **Loop Mode Values**: What loop_mode values are used?
- ✅ **State Preservation**: Is state preserved when toggling?
- ✅ **Prediction Mismatches**: Where library is wrong

## Expected Patterns

### Should Work ✅
- USB, SD card (local files)
- Physical inputs (Line In, Optical, Coax, Bluetooth as sink)
- On-demand albums and playlists (queue-based)
- HTTP streaming (direct URLs)

### Should NOT Work ❌
- Live radio streams (no queue to shuffle)
- Algorithmic radio (no fixed queue)
- AirPlay (iOS controls it)
- Multiroom slaves (can't control master)

### Unknown / Needs Testing ❓
- Spotify albums vs radio (content type difference)
- Amazon Music albums vs stations
- Tidal, Qobuz, Deezer
- DLNA sources
- Podcasts (varies by source)

## Tips for Good Testing

1. **Be Specific**: "Spotify Album" vs "Spotify Radio" matters
2. **Wait for Playback**: Let content start playing before testing
3. **Note Anomalies**: If behavior is weird, mention it
4. **Test Multiple Times**: Some sources may be inconsistent
5. **Save Everything**: Results are valuable data!

## After Testing

1. **Review Results**: Look for patterns and anomalies
2. **Check Mismatches**: Where was the library wrong?
3. **Update Blacklist**: Based on findings (if needed)
4. **Share Results**: Help improve pywiim for everyone!

## Questions During Testing?

- **"What if the source changes?"** Test the new source as a separate entry
- **"What if it's playing but paused?"** Start playback first
- **"What if the test fails?"** That's useful data! Script records it
- **"Should I test the same source twice?"** Yes! Different content types matter

## Results Location

Results saved to: `tests/shuffle-repeat-results/shuffle_repeat_test_<model>_<timestamp>.json`

View summary: Press `[r]` in the script or check the JSON file.

## Documentation

- **Testing Guide**: `docs/testing/SHUFFLE_REPEAT_TESTING_GUIDE.md`
- **Design Doc**: `docs/design/SHUFFLE_REPEAT_SUPPORT.md`
- **Results README**: `tests/shuffle-repeat-results/README.md`
- **Script**: `scripts/test-shuffle-repeat-by-source.py`

---

## Example Session

```bash
$ python scripts/test-shuffle-repeat-by-source.py 192.168.1.116

🎵 Shuffle/Repeat Source Testing - 192.168.1.116
📡 Connecting to device...
   ✓ Device: Living Room
   ✓ Model: WiiM Pro
   ✓ Firmware: 4.8.731953

📖 INTERACTIVE TESTING MODE

Options:
  [t] Test current source
  [r] Print results summary
  [q] Quit and save results

Your choice: t

Describe what's playing (source + content type): Spotify Album - Rumors

📊 Testing Source: spotify
📝 Content: Spotify Album - Rumors

🎲 Testing Shuffle Controls:
   → Setting shuffle ON...
      ✓ Shuffle state: True
      ✅ Shuffle controls WORK

🔁 Testing Repeat Controls:
   → Setting repeat ALL...
      ✓ Repeat mode: all
      ✅ Repeat controls WORK

📊 Assessment:
   ✅ Shuffle: WORKS
   ✅ Repeat: WORKS

# Continue testing more sources...
```

Happy testing! 🎯

