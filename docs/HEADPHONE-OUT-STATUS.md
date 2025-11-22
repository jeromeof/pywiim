# Headphone Output Support - Status and Next Steps

**Issue:** [#86 - Add headphone to Audio Output selections](https://github.com/mjcumming/wiim/issues/86)

**Date:** 2025.11.22

## Summary

The WiiM Ultra has a physical 3.5mm headphone jack on the front panel, but the integration was missing "Headphone Out" from the available output modes list. This has been partially addressed.

## What Was Done

### 1. Added "Headphone Out" to Available Output Modes

**Files Modified:**
- `pywiim/player/properties.py` - Added "Headphone Out" to WiiM Ultra output list
- `pywiim/cli/diagnostics.py` - Added "Headphone Out" to diagnostics output list
- `README.md` - Updated documentation
- `CHANGELOG.md` - Updated changelog
- `docs/design/API_DESIGN_PATTERNS.md` - Enhanced documentation about unknown modes
- `tests/unit/test_player.py` - Added test assertion for "Headphone Out"

### 2. Created Diagnostic Script

Created `scripts/test-headphone-mode.py` to help discover the actual hardware mode number that the WiiM API reports when headphones are selected.

## Current Status

✅ **Completed:**
- "Headphone Out" now appears in available output modes for WiiM Ultra
- All tests pass
- Documentation updated

❌ **Still Unknown:**
- **Hardware mode number for headphone output** (likely 5 or 6+)
- **Hardware mode number for HDMI output** (also likely 5 or 6+)

## The Problem

The WiiM API uses numeric codes to identify different output modes:
- `0` = Line Out (undocumented)
- `1` = Optical Out (SPDIF)
- `2` = Line Out (AUX) - primary
- `3` = Coax Out
- `4` = Bluetooth Out (via `source` field)
- `?` = **Headphone Out** (UNKNOWN)
- `?` = **HDMI Out** (UNKNOWN)

Without knowing the correct mode numbers, the integration cannot:
1. Properly detect when headphone output is selected
2. Allow switching to headphone output programmatically
3. Display the correct output mode when headphones are in use

## Next Steps

### For the User (WiiM Ultra Owner)

To discover the headphone mode number, please run:

```bash
# Activate virtual environment
source .venv/bin/activate

# Test 1: With headphones plugged in and selected
python3 scripts/test-headphone-mode.py YOUR_ULTRA_IP

# Test 2: With HDMI selected (if you have HDMI eARC connected)
python3 scripts/test-headphone-mode.py YOUR_ULTRA_IP

# Test 3: With other outputs for reference
# Switch between Line Out, Optical, Coax and run the script each time
```

The script will show the `hardware` field value from the API response. Report these values in the GitHub issue.

### For the Developer

Once the mode numbers are known:

1. Add constants to `pywiim/api/constants.py`:
   ```python
   AUDIO_OUTPUT_MODE_HEADPHONE_OUT = 5  # Or whatever the discovered value is
   AUDIO_OUTPUT_MODE_HDMI_OUT = 6  # Or whatever the discovered value is
   ```

2. Add mappings to `AUDIO_OUTPUT_MODE_MAP`:
   ```python
   AUDIO_OUTPUT_MODE_MAP: dict[int, str] = {
       # ... existing mappings ...
       AUDIO_OUTPUT_MODE_HEADPHONE_OUT: "Headphone Out",
       AUDIO_OUTPUT_MODE_HDMI_OUT: "HDMI Out",
   }
   ```

3. Add reverse mappings to `AUDIO_OUTPUT_MODE_NAME_TO_INT`:
   ```python
   "headphone out": AUDIO_OUTPUT_MODE_HEADPHONE_OUT,
   "headphone": AUDIO_OUTPUT_MODE_HEADPHONE_OUT,
   "hdmi out": AUDIO_OUTPUT_MODE_HDMI_OUT,
   "hdmi": AUDIO_OUTPUT_MODE_HDMI_OUT,
   "hdmi arc": AUDIO_OUTPUT_MODE_HDMI_OUT,
   ```

4. Update tests in `tests/unit/api/test_playback.py` to verify the new mappings

5. Test with actual hardware

## Why This Matters

From the GitHub issue:
> "I'm currently using an Ultra with hard-wired outputs. Selecting headphones from the Ultra front panel returns 'Bluetooth Out' from the integration."

This means users cannot:
- See the correct output mode when using headphones
- Switch to headphone output from Home Assistant or automation scripts
- Properly monitor their audio setup

## References

- GitHub Issue: https://github.com/mjcumming/wiim/issues/86
- WiiM API Documentation: Section 2.10 Audio Output Control
- Design Doc: `docs/design/API_DESIGN_PATTERNS.md` (WiiM Ultra Unknown Modes section)

