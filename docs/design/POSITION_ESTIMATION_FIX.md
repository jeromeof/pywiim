# Position Estimation Fix - Smooth Progress Tracking

## Date: 2024-11-21

## Problem Statement

Media position tracking was causing "jumpy" updates in UI, where position would snap back and forth between values instead of incrementing smoothly. This affected user experience in Home Assistant and other integrations.

### Root Cause

The position estimation logic had a critical bug that compared HTTP polling results to the **original base position** instead of the **current estimated position**. This caused unnecessary resets even when drift was minimal.

**Example of the bug:**
```
t=0:  HTTP poll → position=50, base=50, start=0
t=1:  Timer estimates: 50 + 1 = 51  ✓
t=2:  Timer estimates: 50 + 2 = 52  ✓
t=3:  HTTP poll → position=53
      Check: abs(53 - 50) = 3 > 2  ← BUG: Compares to BASE (50), not estimated (52)!
      → RESETS base to 53  ← UI jumps from 52 → 53!
```

The problem: Even though our internal timer correctly estimated 52 and HTTP said 53 (only 1 second difference), the code reset because it was comparing to the stale base of 50.

## Solution

### 1. Compare to Current Estimate, Not Base

Changed the logic to compare HTTP position to what we **currently think** the position is:

```python
# OLD CODE (buggy)
if abs(pos_int - self._estimation_base_position) > 2:
    # Reset - compares to old base position

# NEW CODE (fixed)
estimated_now = self._estimation_base_position + (timestamp - self._estimation_start_time)
drift = abs(pos_int - estimated_now)
if drift > POSITION_SYNC_TOLERANCE:
    # Reset only if HTTP differs significantly from our CURRENT estimate
```

### 2. Increased Tolerance (Hysteresis)

Changed tolerance from 2 seconds to 3 seconds, matching modern media player UX standards:

```python
POSITION_SYNC_TOLERANCE = 3  # seconds
```

**Rationale**: For UI display, 1-3 second accuracy is perfectly acceptable. Users don't notice small differences, but they DO notice jumpiness. Smoothness > Precision.

### 3. Fixed Order of Operations

Position estimation needs metadata for track change detection, so moved the call to AFTER state merging:

```python
# OLD (broken)
if "position" in data:
    self._http_state["position"] = TimestampedField(...)
    self._update_position_estimation(position_value, ts)  # ← Too early!
    
self._merge_state()  # ← Metadata merged here

# NEW (fixed)
if "position" in data:
    self._http_state["position"] = TimestampedField(...)
    
self._merge_state()  # ← Merge first

# Now position estimation can see the metadata
if "position" in data:
    self._update_position_estimation(position_value, ts)  # ← After merge!
```

### 4. Design Philosophy

The fix follows industry best practices from VLC, Spotify, YouTube, etc:

**HTTP polling is CONFIRMATION, not CORRECTION** (unless drift is significant)

- Internal timer is the primary source of truth while playing
- HTTP polls confirm we're on track (within 3s)
- Only reset on:
  - Large drift (> 3s)
  - Track changes
  - Seeks (> 10s jumps)
  - Play state changes

This provides smooth second-by-second updates without jitter.

## Test Results

### Unit Tests

Created comprehensive test suite (`tests/unit/test_position_estimation.py`) with 11 tests:

✓ Small drift keeps smooth estimation (no reset)
✓ Large drift triggers reset
✓ Track changes always reset
✓ Seeks (forward/backward) always reset
✓ Smooth progression between polls
✓ HTTP confirmation within tolerance
✓ No jitter on consecutive polls
✓ Position clamped to duration
✓ Negative position handling
✓ None position stops estimation

**All 11 tests pass** ✅

### Integration Tests

Tested against real device (192.168.1.116):

**Before Fix:**
- Position would jump erratically
- UI felt unresponsive
- Values changed back and forth

**After Fix:**
```
Reading 1: Position=235s, Progress=87.4%
Reading 2: Position=237s, Progress=88.1%
Reading 3: Position=239s, Progress=88.8%
Reading 4: Position=241s, Progress=89.6%
Reading 5: Position=243s, Progress=90.3%
```

**Smooth progression:** 235 → 237 → 239 → 241 → 243 seconds ✅

Position increases by ~2 seconds per reading (as expected with 1s intervals + HTTP overhead).

### Regression Tests

All existing tests continue to pass:
- ✅ 26/26 state synchronization tests
- ✅ No breaking changes to existing functionality

## Technical Details

### When Reset Happens

| Condition | Tolerance | Action | Reason |
|-----------|-----------|--------|--------|
| Track change | Always | Reset | New track, reset to position 0 |
| Seek backward | > 2s jump back | Reset | User skipped backward |
| Seek forward | > 10s jump forward | Reset | User skipped forward |
| Large drift | > 3s difference | Reset | Position correction needed |
| Small drift | ≤ 3s difference | **Keep smooth** | HTTP confirms we're close enough |

### Key Parameters

```python
POSITION_SYNC_TOLERANCE = 3  # Don't reset if within 3 seconds
SEEK_BACKWARD_THRESHOLD = 2  # Detect seeks > 2 seconds backward
SEEK_FORWARD_THRESHOLD = 10  # Detect seeks > 10 seconds forward
```

### Logging

Added debug logging to track behavior:

```python
_LOGGER.debug("Position within tolerance: estimated=%ds, http=%ds, drift=%ds - keeping smooth timer")
_LOGGER.debug("Resetting position estimation: drift_exceeded (estimated=103s, http=110s, drift=7s)")
```

## Benefits

1. **Smooth UI Updates**: Position increments steadily without jumps
2. **Better UX**: Progress bars move smoothly like modern media players
3. **Reduced Callbacks**: Fewer state change notifications (less CPU)
4. **Tolerance-Based**: Small network delays don't cause position resets
5. **Industry Standard**: Matches behavior of VLC, Spotify, YouTube

## Migration Impact

**Breaking Changes**: None

The fix is transparent to existing code. All public APIs remain the same:
- `Player.media_position` still returns current position
- Position timer still runs every second
- Callbacks still fire on position changes

The improvement is purely internal to `StateSynchronizer._update_position_estimation()`.

## Future Improvements

Potential enhancements to consider:

1. **Adaptive Tolerance**: Increase tolerance based on network latency
2. **Drift Correction**: Gradually adjust timer speed if consistent drift detected
3. **Predictive Positioning**: Use playback rate to improve accuracy
4. **UPnP Integration**: Better handling when UPnP events become available

## References

- Issue: Media progress tracking feels "jumpy" in Home Assistant
- Test File: `tests/unit/test_position_estimation.py`
- Integration Test: `tests/test_media_progress.py`
- Code: `pywiim/state.py::StateSynchronizer._update_position_estimation()`

## Conclusion

The position estimation fix provides smooth, professional media progress tracking that matches user expectations from modern media players. The 3-second tolerance strikes the right balance between accuracy and smooth UX, while the timer-based estimation provides second-by-second updates without unnecessary HTTP polling.

**Result**: Smooth position tracking, happy users! 🎉

