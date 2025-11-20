# Group Smart Routing - Testing Notes

## Changes Made

This document describes changes made to support automatic playback command routing and cross-notification for multiroom groups, and how to test them with real devices.

### 1. Playback Command Routing

**What changed:**
- Slave players now automatically route playback commands (`play()`, `pause()`, `stop()`, `next_track()`, `previous_track()`, `resume()`) through the Group object to the master
- No longer sends commands directly to slave devices (which would be ignored)
- Raises `WiiMError` if slave has no group object (edge case)

**Implementation:** `pywiim/player/media.py`

### 2. Cross-Notification for Volume/Mute

**What changed:**
- When a slave's volume or mute changes, both the slave's and master's callbacks fire
- Enables immediate virtual group entity updates without polling lag
- Master's callback doesn't fire twice when master changes its own volume

**Implementation:** `pywiim/player/volume.py`

### 3. Group Object Design

**Verified:**
- Properties compute dynamically (no caching): `volume_level`, `is_muted`, `play_state`
- Methods delegate to master: `play()`, `pause()`, etc.
- All behavior works as designed

**Implementation:** `pywiim/group.py`

## Testing with Real Devices

### Test Scenarios

#### Scenario 1: Slave Playback Routing

**Setup:**
- Create a group with 1 master + 1+ slaves
- Ensure Player objects are linked (provide `player_finder` callback)

**Test:**
```python
# Call playback command on slave
await slave_player.pause()

# Verify:
# - Master actually pauses (check physical device)
# - All slaves pause (synced from master)
# - Master's callback fired
# - Virtual group entity updated immediately
```

**Expected behavior:**
- Command routes through `slave.group.pause()` → `master.pause()`
- Master executes command and syncs to all slaves
- No errors, playback stops on all devices

#### Scenario 2: Cross-Notification Volume

**Setup:**
- Create a group with 1 master + 2+ slaves
- Set up virtual group entity listening to master's coordinator

**Test:**
```python
# Get initial group volume
initial_volume = master.group.volume_level  # MAX of all devices

# Change slave volume
await slave_player.set_volume(0.8)

# Verify:
# - Slave's callback fired (slave entity updates)
# - Master's callback fired (virtual entity updates immediately)
# - group.volume_level recomputes correctly (MAX of all)
# - Virtual entity shows new volume without waiting for poll
```

**Expected behavior:**
- Both callbacks fire
- Virtual entity updates within milliseconds
- No polling lag

#### Scenario 3: Unlinked Slave (Edge Case)

**Setup:**
- Create a slave device that thinks it's in a group
- Don't provide `player_finder` or don't link Player objects

**Test:**
```python
# Slave without group object
slave._detected_role = "slave"  # Device reports as slave
slave.group  # None - no Player linking

# Try playback command
try:
    await slave.play()
except WiiMError as e:
    # Should raise with message "Slave player not linked to group"
    print(f"Expected error: {e}")
```

**Expected behavior:**
- Raises `WiiMError` with clear message
- Debug log shows the issue
- Graceful failure

#### Scenario 4: Group Volume Aggregation

**Setup:**
- Create a group with master + 2 slaves
- Set different volumes on each device

**Test:**
```python
# Set different volumes
await master.set_volume(0.6)
await slave1.set_volume(0.4)
await slave2.set_volume(0.8)  # Highest

# Check group volume
group_volume = master.group.volume_level
assert group_volume == 0.8  # Should be MAX

# Check group mute
await slave1.set_mute(True)
assert master.group.is_muted == False  # Not all muted

await master.set_mute(True)
await slave2.set_mute(True)
assert master.group.is_muted == True  # All muted now
```

**Expected behavior:**
- `group.volume_level` always returns MAX
- `group.is_muted` only True when ALL muted
- Computed dynamically on access

### Integration Test Review

The following integration tests should be reviewed/verified with real devices:

1. **`test_group_role_detection`** - ✅ No changes needed
   - Tests role detection and Player linking
   - Works as before

2. **`test_group_volume_and_mute_propagation`** - ✅ No changes needed
   - Tests `group.set_volume_all()` and `group.mute_all()`
   - Uses Group object methods directly (still works)

3. **`test_slave_playback_via_group`** (line 590) - ✅ No changes needed
   - Calls `slave.group.next_track()` which still works
   - Uses Group object directly

### New Integration Tests Needed

Consider adding these integration tests:

1. **Test slave direct playback routing:**
```python
async def test_slave_playback_routes_to_master(multi_device_testbed):
    """Test that slave playback commands route to master."""
    master = multi_device_testbed["master"]
    slave = multi_device_testbed["slaves"][0]
    
    # Create group
    await _create_group(master, [slave])
    
    # Start playback on master
    # ... start some test audio ...
    
    # Pause via slave
    await slave.pause()
    
    # Verify master paused
    await _refresh_players([master, slave])
    assert master.play_state == "pause"
```

2. **Test cross-notification callbacks:**
```python
async def test_slave_volume_fires_master_callback(multi_device_testbed):
    """Test that slave volume changes fire master callback."""
    master = multi_device_testbed["master"]
    slave = multi_device_testbed["slaves"][0]
    
    master_callback_count = {"count": 0}
    def master_callback():
        master_callback_count["count"] += 1
    
    master._on_state_changed = master_callback
    
    # Create group
    await _create_group(master, [slave])
    
    # Reset counter after group creation callbacks
    master_callback_count["count"] = 0
    
    # Change slave volume
    await slave.set_volume(0.5)
    
    # Verify master callback fired
    assert master_callback_count["count"] >= 1
```

## Manual Testing Checklist

When testing with physical devices:

- [ ] Slave playback commands (play/pause/next/previous) work correctly
- [ ] Master physically responds when slave entity receives commands
- [ ] Slave volume changes update virtual group entity immediately
- [ ] Group volume correctly shows MAX of all devices
- [ ] Group mute correctly requires ALL devices muted
- [ ] No errors in logs during normal operation
- [ ] Edge case: unlinked slave shows clear error message

## Monitoring

Watch for these log messages during testing:

```
[DEBUG] Slave <host> has no group object, cannot route playback command
[DEBUG] Auto-linking slave <slave_host> to master <master_host>
```

These indicate:
1. A slave tried to use playback without a group (edge case)
2. Player objects are being linked correctly on refresh

## Unit Test Coverage

Added unit tests in `tests/unit/test_player.py`:

- `test_slave_playback_routes_to_master` - Verifies routing works
- `test_slave_without_group_raises_error` - Verifies edge case handling
- `test_slave_volume_fires_master_callback` - Verifies cross-notification
- `test_master_volume_only_fires_own_callback` - Verifies no duplicate callbacks

All tests pass (770 unit tests total).

## Documentation Updated

- `docs/integration/HA_INTEGRATION.md` - Added "Virtual Group Entity Implementation" and "Event Propagation Model" sections
- `docs/integration/API_REFERENCE.md` - Added comprehensive "Group Object" documentation

## Summary

The changes enable a cleaner integration pattern where:
- Integrations just call `player.pause()` on any entity
- pywiim handles routing automatically
- Virtual entities update immediately via cross-notification
- No polling lag, no manual refresh needed

