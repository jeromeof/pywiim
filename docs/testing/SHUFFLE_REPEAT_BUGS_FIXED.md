# Shuffle/Repeat Bugs - Investigation and Fixes

## Summary

Through systematic testing and comparison with the WiiM app, we discovered and fixed **THREE CRITICAL BUGS** that made shuffle/repeat completely non-functional.

## The Bugs

### Bug #1: Wrong API Endpoint (CRITICAL)
**Symptom**: Commands sent, no effect  
**Root Cause**: Library called `setLoopMode:X` which doesn't exist  
**Correct API**: `setPlayerCmd:loopmode:X`  
**Discovery**: Curl testing showed device returned "unknown command" for `setLoopMode:`  
**Fix**: Changed `API_ENDPOINT_LOOPMODE` in `constants.py`

### Bug #2: Wrong Parsing Logic
**Symptom**: Shuffle showed as repeat, repeat showed as shuffle  
**Root Cause**: Reading used legacy bitfield logic, writing used vendor mappings  
**Example**: WiiM loop_mode=3 read as shuffle=False, repeat=True (WRONG)  
**Correct**: loop_mode=3 = shuffle=True, repeat=False  
**Fix**: Changed `shuffle_state` and `repeat_mode` properties to use `mapping.from_loop_mode()`

### Bug #3: Invalid Validation
**Symptom**: "Invalid loop_mode: 3" errors  
**Root Cause**: Hardcoded validation `(0,1,2,4,5,6)` from legacy bitfield  
**Reality**: WiiM uses 0-4, Arylic uses 0-5, different vendors vary  
**Fix**: Accept all reasonable loop_mode values (0-10)

## Discovery Process

### Initial Observation
User reported: "When I change shuffle in WiiM app, monitor shows it - but shuffle shows as repeat!"

### Systematic Testing

1. **Test with Python library**: Failed silently
2. **Test with curl**: `curl -k "https://IP/httpapi.asp?command=setPlayerCmd:loopmode:3"` → ✅ WORKED!
3. **Compare APIs**: 
   - WiiM app: `setPlayerCmd:loopmode:3` ✅
   - Our library: `setLoopMode:3` ❌ "unknown command"

### Content-Type Discovery

Testing different Spotify content revealed the `vendor` field contains URIs:
- **Album**: `spotify:album:0gI6zLhhO1X5hH8uHzZ97s` → Shuffle YES
- **Playlist**: `spotify:playlist:37i9dQZF1E4nBVJCaUBWcR` → Shuffle YES
- **Podcast**: `spotify:show:5Eez65bpNJSDLCYQb7yck5` → Shuffle NO
- **Audiobook**: `spotify:show:6LnvdvTsvdXo4yZ5DlWLKE` → Shuffle NO

This explains how the WiiM app knows to hide shuffle/repeat for podcasts!

## Testing Results

### Before Fixes
```
✅ Commands sent (no error)
❌ No effect on device (wrong endpoint)
❌ Values swapped (wrong parsing)
❌ loop_mode=3 rejected (wrong validation)
```

### After Fixes
```
✅ Shuffle ON/OFF works
✅ Repeat ALL/ONE/OFF works
✅ Values read correctly
✅ Spotify albums: shuffle_supported = True
✅ Spotify podcasts: shuffle_supported = False
```

## Implementation

### Files Changed
1. `pywiim/api/constants.py` - Fixed API endpoint
2. `pywiim/api/playback.py` - Fixed validation
3. `pywiim/player/properties.py` - Fixed parsing + added Spotify content detection
4. `pywiim/api/loop_mode.py` - Added loop_mode=5 handling

### Key Code Changes

**API Endpoint (constants.py)**:
```python
# Before (WRONG)
API_ENDPOINT_LOOPMODE = "/httpapi.asp?command=setLoopMode:"

# After (CORRECT)
API_ENDPOINT_LOOPMODE = "/httpapi.asp?command=setPlayerCmd:loopmode:"
```

**Parsing (properties.py)**:
```python
# Before (WRONG - bitfield logic)
is_shuffle = bool(loop_val & 4)

# After (CORRECT - vendor mapping)
from ..api.loop_mode import get_loop_mode_mapping
mapping = get_loop_mode_mapping(vendor)
shuffle, _, _ = mapping.from_loop_mode(loop_val)
```

**Spotify Content Detection (properties.py)**:
```python
if source_lower == "spotify":
    vendor_uri = getattr(self.player._status_model, "vendor", None)
    if vendor_uri and isinstance(vendor_uri, str):
        # Podcasts/audiobooks - no shuffle
        if vendor_uri.startswith("spotify:show:"):
            return False
    return True  # Albums/playlists - shuffle works
```

## Impact

### For Users
- ✅ Shuffle and repeat controls now actually work
- ✅ Home Assistant buttons work correctly
- ✅ Podcast/audiobook shuffle controls hidden (like WiiM app)

### For Home Assistant Integration
- ✅ `shuffle_supported` returns correct value
- ✅ Can show/hide shuffle button based on content type
- ✅ No more "command sent but nothing happens"

### For Other Sources
All sources that support shuffle/repeat now work:
- ✅ Spotify (albums/playlists)
- ✅ USB
- ✅ Local files
- ✅ Other streaming services (Tidal, Qobuz, etc. - needs testing)

## Testing Tools Created

1. `scripts/test-shuffle-repeat-once.py` - Quick single test
2. `scripts/test-shuffle-repeat-by-source.py` - Comprehensive source-by-source testing
3. `scripts/test-all-loop-modes.py` - Discover loop_mode mappings
4. `scripts/test-spotify-content-types.py` - Verify Spotify content detection
5. `scripts/test-shuffle-debug.py` - Debug what commands are sent

## Lessons Learned

1. **Test against the raw API**: Curl testing revealed the endpoint was wrong
2. **Compare with working app**: WiiM app used different endpoint than us
3. **Content type matters**: Same source (Spotify) behaves differently based on content
4. **Vendor mappings are critical**: Can't use generic bitfield logic
5. **Silent failures are dangerous**: Device returned "OK" but ignored our commands

## References

- CHANGELOG v2.1.2 - Previous loop_mode fix (bitfield → vendor mappings for WRITING)
- CHANGELOG v1.0.71 - Source-aware shuffle/repeat (first attempt)
- WiiM HTTP API docs - Loop mode values per vendor
- GitHub Issue #111 - Original shuffle/repeat bug reports

