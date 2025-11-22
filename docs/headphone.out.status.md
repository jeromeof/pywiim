# Headphone Output Support - FIXED (Matching HA Integration)

**Issue:** [#86 - Add headphone to Audio Output selections](https://github.com/mjcumming/wiim/issues/86)

**Date:** 2025.11.22

**Status:** ✅ **RESOLVED** (Matching Home Assistant integration fix from ~2 weeks ago)

## Summary

The WiiM Ultra has a physical 3.5mm headphone jack on the front panel. Mode 4 is used for BOTH Headphone Out and Bluetooth Out, distinguished by the `source` field:
- `hardware=4` + `source=0` = **Headphone Out**
- `hardware=4` + `source=1` = **Bluetooth Out**

## What Was Fixed

### The Solution (From HA Integration)

The fix implemented in the Home Assistant integration (~2 weeks ago) uses **context-dependent detection**:

```python
# For WiiM Ultra devices only:
if hardware_mode == 4:
    if source == 0:
        return "Headphone Out"
    elif source == 1:
        return "Bluetooth Out"
```

### Files Modified in PyWiim:

- `pywiim/player/properties.py`
  - Added special handling in `audio_output_mode` property
  - Checks if device is Ultra AND hardware=4
  - Returns "Headphone Out" when source=0, "Bluetooth Out" when source=1
  
- `pywiim/api/constants.py`
  - Mode 4 defaults to "Bluetooth Out" in mapping
  - Special handling done at runtime in properties
  - Added comment explaining Ultra-specific behavior
  
- Documentation updates:
  - `README.md`
  - `CHANGELOG.md`
  - `docs/design/API_DESIGN_PATTERNS.md`

## The Correct Mode Mapping

```python
# hardware field (setAudioOutputHardwareMode:N)
0 = Line Out (undocumented)
1 = Optical Out (SPDIF)
2 = Line Out (AUX - primary)
3 = Coax Out  
4 = Bluetooth Out OR Headphone Out (context-dependent on Ultra)
    - WiiM Ultra with source=0: Headphone Out
    - WiiM Ultra with source=1: Bluetooth Out
    - Other devices: Bluetooth Out

# source field (separate from hardware)
0 = Bluetooth output disabled (or using headphones on Ultra)
1 = Bluetooth output active
```

## How It Works Now

### Detect Current Output:

```python
# When headphones are selected on Ultra:
# {"hardware": "4", "source": "0", "audiocast": "0"}
status = await client.get_audio_output_status()

# This returns "Headphone Out" for Ultra devices:
mode_name = player.audio_output_mode  # Returns "Headphone Out"

# When Bluetooth is active on Ultra:
# {"hardware": "4", "source": "1", "audiocast": "0"}
# This returns "Bluetooth Out"
```

### Select Headphone Output:

```python
# By name (for Ultra devices):
await player.audio.select_output("Headphone Out")

# This sends hardware=4 and ensures source=0 (disconnects BT if needed)
```

### Available Outputs for WiiM Ultra:

```python
outputs = player.available_output_modes
# Returns: ["Line Out", "Optical Out", "Coax Out", "Bluetooth Out", "Headphone Out", "HDMI Out"]
```

## Comparison with HA Integration

**Home Assistant Integration** (wiim-source):
- ✅ Special handling in `get_current_output_mode()` 
- ✅ Checks Ultra model + source field
- ✅ "Headphone Out" in selectable modes for Ultra

**PyWiim Library** (now):
- ✅ Special handling in `audio_output_mode` property
- ✅ Checks Ultra model + source field  
- ✅ "Headphone Out" in available_output_modes for Ultra
- ✅ **MATCHES HA INTEGRATION APPROACH**

## All Tests Passing ✅

- All audio output API tests pass
- All player property tests pass
- Linter clean

## References

- GitHub Issue: https://github.com/mjcumming/wiim/issues/86
- Home Assistant Integration: `/home/mike/projects/wiim-source/`
- WiiM API Documentation: Section 2.10 Audio Output Control

