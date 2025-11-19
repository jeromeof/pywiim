# UPnP Event Health Tracking

## Overview

The UPnP health tracking system monitors the reliability of UPnP events by detecting when HTTP polling discovers state changes that UPnP events should have (but didn't) report.

This solves a fundamental challenge with UPnP/DLNA: **UPnP has no heartbeat or keepalive mechanism**, making it impossible to detect if events are working using time-based methods alone.

## The Problem

### Why Time-Based Detection Fails

**Naive Approach:**
```python
# ❌ WRONG: Time-based detection
if time_since_last_upnp_event > 5.0:
    upnp_working = False  # Assume broken
```

**Why It Fails:**
- **False Negative**: When device is idle (not playing), there are no state changes, so no UPnP events are sent
- An idle device with working UPnP will be incorrectly flagged as "broken"
- Can't distinguish between "UPnP is broken" vs "UPnP is working but device is idle"

### The Solution: Change-Based Detection

**Smart Approach:**
```python
# ✅ CORRECT: Change-based detection
if polling_detected_change and not upnp_reported_change:
    missed_changes += 1  # Evidence that UPnP missed something
```

**Why It Works:**
- Only checks UPnP health when there's actual proof (a missed change)
- Idle device = no changes = no false negatives
- Active device with broken UPnP = missed changes = correctly detected
- Self-healing: Can detect when UPnP recovers

## How It Works

### 1. State Monitoring

The health tracker monitors specific fields that UPnP should **always** notify about:

```python
UPNP_MONITORED_FIELDS = {
    "play_state",  # play/pause/stop always fires UPnP event
    "volume",      # Volume changes always fire UPnP event
    "muted",       # Mute changes always fire UPnP event
    "title",       # Track changes include metadata updates
    "artist",      # Track changes include metadata updates
    "album",       # Track changes include metadata updates
}
```

**Note:** We deliberately **don't** monitor `position`/`duration` because:
- UPnP only sends these on track start, not continuously during playback
- Position during playback is estimated locally, not via UPnP events

### 2. Change Detection Flow

```
┌─────────────────┐
│  HTTP Poll #1   │  play_state: "pause", volume: 50
└────────┬────────┘
         │ (store state)
         ▼
┌─────────────────┐
│  HTTP Poll #2   │  play_state: "play", volume: 60  ← CHANGE DETECTED!
└────────┬────────┘
         │
         ├─► Check: Did UPnP report play_state="play"?
         │          ├─ Yes (within 2s) → ✅ UPnP caught it
         │          └─ No → ❌ UPnP missed it (missed_changes++)
         │
         └─► Check: Did UPnP report volume=60?
                    ├─ Yes (within 2s) → ✅ UPnP caught it
                    └─ No → ❌ UPnP missed it (missed_changes++)
```

### 3. Health Assessment

The tracker uses **hysteresis** to avoid flapping between healthy/unhealthy:

```python
if miss_rate > 50%:  # More than half of changes missed
    status = UNHEALTHY  # Mark as degraded
elif miss_rate < 20%:  # Catching most changes
    status = HEALTHY    # Mark as healthy
# Between 20-50%: Keep current status (hysteresis)
```

### 4. Adaptive Polling Response

When UPnP is detected as unhealthy:

```python
# Normal polling (UPnP working)
interval = 5.0  # Poll every 5 seconds (when playing)

# Fast polling (UPnP degraded)
if is_playing and not upnp_healthy:
    interval = 1.0  # Poll every 1 second to compensate
```

## Implementation

### Core Class: `UpnpHealthTracker`

Located in `pywiim/upnp/health.py`:

```python
from pywiim.upnp.health import UpnpHealthTracker

# Initialize tracker
tracker = UpnpHealthTracker(
    grace_period=2.0,  # Wait 2 seconds for UPnP event to arrive
    min_samples=3,     # Need 3 changes before making decisions
)

# After each HTTP poll
tracker.on_poll_update({
    "play_state": player.play_state,
    "volume": player.volume,
    "muted": player.muted,
    "title": player.media_title,
    "artist": player.media_artist,
    "album": player.media_album,
})

# When UPnP event arrives
tracker.on_upnp_event({
    "play_state": player.play_state,
    "volume": player.volume,
    # ... same fields
})

# Check health status
if tracker.is_healthy:
    print("✅ UPnP working!")
else:
    print("❌ UPnP degraded, switching to fast polling")

# Get detailed statistics
stats = tracker.statistics
print(f"Miss rate: {stats['miss_rate']*100:.1f}%")
print(f"Caught: {stats['detected_changes']-stats['missed_changes']}/{stats['detected_changes']}")
```

### Integration with Monitor CLI

The `PlayerMonitor` in `pywiim/cli/monitor_cli.py` automatically:

1. **Initializes tracker** when UPnP is enabled
2. **Updates on poll** after each `player.refresh()`
3. **Updates on event** when UPnP callback fires
4. **Adapts polling** based on health status
5. **Displays status** in TUI with visual indicators

### Visual Status Indicators

The monitor CLI displays UPnP health with clear visual feedback:

```
🟢 HEALTHY    - UPnP catching >80% of changes (working well)
🔴 DEGRADED   - UPnP missing >50% of changes (polling compensating)
⚪ LEARNING   - Not enough data yet (need 3+ changes to assess)
```

Example output:
```
📡 Polling: 1.0s  |  Polls: 42  |  UPnP: 🟢 HEALTHY (15/16 caught, 6% miss)  |  Changes: 8
```

## Key Features

### 1. Grace Period for Race Conditions

HTTP polls and UPnP events arrive asynchronously. The tracker uses a **2-second grace period**:

```python
# Poll detects change at T=0
poll_state = {"volume": 60}

# UPnP event arrives at T=1.5 (within grace period)
upnp_state = {"volume": 60}

# Result: ✅ UPnP caught the change (arrived within 2 seconds)
```

This handles:
- Network latency variations
- Asynchronous timing between poll and event
- Brief delays in event delivery

### 2. Minimum Sample Requirement

The tracker requires **at least 3 detected changes** before making health decisions:

```python
if detected_changes < 3:
    status = "LEARNING"  # Not enough data yet
```

This prevents:
- False positives from single missed events
- Premature health assessments
- Noise from transient issues

### 3. Self-Healing / Recovery Detection

When UPnP recovers (e.g., after device reboot, network issue resolves):

```python
# UPnP was unhealthy (60% miss rate)
# New changes arrive and UPnP catches them
# Miss rate drops to 15%

if miss_rate < 20% and previously_unhealthy:
    status = HEALTHY
    reset_statistics()  # Give fresh start
    log("🟢 UPnP events RECOVERED")
```

### 4. Statistics Reset

When UPnP recovers, statistics are reset to avoid "poisoned metrics":

```python
tracker.reset_statistics()  # Clear old miss data
```

This ensures:
- Old failures don't prevent recovery detection
- Fresh assessment after recovery
- Accurate health status going forward

## Design Decisions

### Why Not Monitor Position/Duration?

UPnP events **only send position/duration on track start**, not continuously:

```
Track Change Event:
✅ TransportState: PLAYING
✅ CurrentTrackDuration: 180
✅ RelativeTimePosition: 0

During Playback:
❌ No position updates sent
❌ Position estimated locally
```

If we monitored position, we'd get massive false positives (polling sees position changes, UPnP doesn't send them).

### Why 2-Second Grace Period?

Empirical testing showed:
- Network latency typically < 500ms
- Event processing delay typically < 500ms
- 2 seconds provides comfortable margin
- Rarely causes false negatives

Could be configurable in future if needed.

### Why 50% Threshold for Unhealthy?

Conservative threshold to avoid false positives:
- Occasional missed event (< 20%) = acceptable
- Consistent missing (> 50%) = clearly broken
- 20-50% = hysteresis zone (avoid flapping)

### Why Hysteresis (20-50% Gap)?

Prevents "flapping" between states:

```
Without hysteresis:
50% → UNHEALTHY
49% → HEALTHY
50% → UNHEALTHY (flapping!)

With hysteresis:
50% → UNHEALTHY
49% → stay UNHEALTHY (hysteresis)
19% → HEALTHY (clear improvement)
```

## Usage Examples

### Example 1: Healthy UPnP

```
Poll #1: play_state=pause, volume=50
Poll #2: play_state=play, volume=50   (change detected: play_state)
UPnP:    play_state=play               (within 2 seconds)
Result:  ✅ Caught (1/1)

Poll #3: play_state=play, volume=60   (change detected: volume)
UPnP:    volume=60                     (within 2 seconds)
Result:  ✅ Caught (2/2)

Status:  🟢 HEALTHY (2/2 caught, 0% miss)
```

### Example 2: Degraded UPnP

```
Poll #1: play_state=pause, volume=50
Poll #2: play_state=play, volume=50   (change detected: play_state)
UPnP:    (no event)
Result:  ❌ Missed (0/1)

Poll #3: play_state=play, volume=60   (change detected: volume)
UPnP:    (no event)
Result:  ❌ Missed (0/2)

Poll #4: play_state=play, title="New Song"  (change detected: title)
UPnP:    (no event)
Result:  ❌ Missed (0/3)

Status:  🔴 DEGRADED (0/3 caught, 100% miss)
Action:  → Switch to 1-second polling
```

### Example 3: Recovery

```
(Previously: 0/5 caught, 100% miss, DEGRADED)

Poll #6: play_state=pause  (change detected)
UPnP:    play_state=pause  (event arrived!)
Result:  ✅ Caught (1/6, miss rate now 83%)

Poll #7: play_state=play   (change detected)
UPnP:    play_state=play   (event arrived!)
Result:  ✅ Caught (2/7, miss rate now 71%)

Poll #8: volume=70         (change detected)
UPnP:    volume=70         (event arrived!)
Result:  ✅ Caught (3/8, miss rate now 62%)

... more successful catches ...

Poll #12: title="Song"     (change detected)
UPnP:     title="Song"     (event arrived!)
Result:   ✅ Caught (7/12, miss rate now 42%)

... continue improving ...

Poll #15: volume=80        (change detected)
UPnP:     volume=80        (event arrived!)
Result:   ✅ Caught (10/15, miss rate now 33%)

... miss rate crosses 20% threshold ...

Poll #18: play_state=play  (change detected)
UPnP:     play_state=play  (event arrived!)
Result:   ✅ Caught (13/18, miss rate now 28% → still improving)

Poll #20: volume=75        (change detected)
UPnP:     volume=75        (event arrived!)
Result:   ✅ Caught (15/20, miss rate now 25%)

Poll #22: title="New"      (change detected)
UPnP:     title="New"      (event arrived!)
Result:   ✅ Caught (17/22, miss rate now 23%)

Poll #24: volume=80        (change detected)
UPnP:     volume=80        (event arrived!)
Result:   ✅ Caught (19/24, miss rate now 21%)

Poll #25: play_state=pause (change detected)
UPnP:     play_state=pause (event arrived!)
Result:   ✅ Caught (20/25, miss rate now 20%)

Poll #26: volume=85        (change detected)
UPnP:     volume=85        (event arrived!)
Result:   ✅ Caught (21/26, miss rate now 19% ← CROSSED THRESHOLD!)

Status:   🟢 HEALTHY (21/26 caught, 19% miss)
Action:   → Log "UPnP RECOVERED", reset statistics, reduce polling
```

## Testing

### Manual Testing

Use the monitor CLI to observe health tracking:

```bash
python -m pywiim.cli.monitor 192.168.1.100 --callback-host 192.168.1.50
```

Then perform actions on the device:
1. **Change volume** → Watch for UPnP events
2. **Play/pause** → Watch for UPnP events
3. **Change track** → Watch for UPnP events

The TUI will show:
```
📡 Polling: 5.0s  |  UPnP: 🟢 HEALTHY (8/9 caught, 11% miss)
```

### Simulate Degraded UPnP

To test the degraded path, you can:
1. Use wrong callback host (UPnP won't receive events)
2. Block UPnP port on firewall
3. Disconnect network temporarily

The monitor should detect degraded state and switch to 1-second polling.

## Future Enhancements

### Possible Improvements

1. **Configurable Thresholds**
   ```python
   tracker = UpnpHealthTracker(
       unhealthy_threshold=0.5,  # 50% miss rate
       healthy_threshold=0.2,    # 20% miss rate
   )
   ```

2. **Per-Field Tracking**
   - Track miss rates separately for volume, play_state, metadata
   - Identify which fields are unreliable

3. **Temporal Analysis**
   - Weight recent misses more heavily than old ones
   - Detect intermittent vs permanent failures

4. **Automatic Resubscription**
   - If degraded for extended period, try resubscribing
   - May fix subscription issues without restart

5. **Telemetry Export**
   - Export health metrics for monitoring
   - Integration with Home Assistant diagnostics

## Related Documentation

- [UPNP_INTEGRATION.md](UPNP_INTEGRATION.md) - Overall UPnP integration architecture
- [STATE_MANAGEMENT.md](STATE_MANAGEMENT.md) - How HTTP and UPnP state is merged
- [POLLING_STRATEGY.md](../design/POLLING_STRATEGY.md) - Adaptive polling intervals

## References

- DLNA DMR specification (no heartbeat/keepalive defined)
- Home Assistant DLNA DMR integration (similar patterns)
- UPnP Device Architecture v2.0

