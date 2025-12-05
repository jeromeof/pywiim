# Group Smart Routing - Testing Guide

## Overview

This document describes the automatic playback command routing and cross-notification features for multiroom groups, and how to test them with real devices.

## Architecture

The library implements smart routing for group operations:

1. **Playback Command Routing**: Slave players automatically route playback commands through the Group object to the master
2. **Cross-Notification**: When a slave's volume or mute changes, both the slave's and master's callbacks fire
3. **Dynamic Properties**: Group properties compute dynamically (no caching) for real-time accuracy

### 1. Playback Command Routing

**How it works:**
- Slave players automatically route playback commands (`play()`, `pause()`, `stop()`, `next_track()`, `previous_track()`, `resume()`) through the Group object to the master
- Commands are never sent directly to slave devices (which would be ignored)
- Raises `WiiMError` if slave has no group object (edge case)

**Implementation:** `pywiim/player/media.py`

**Usage:**
```python
# Works seamlessly - library handles routing automatically
await slave_player.pause()  # Routes to master.group.pause() → master.pause()
```

### 2. Cross-Notification for Volume/Mute

**How it works:**
- When a slave's volume or mute changes, both the slave's and master's callbacks fire
- Enables immediate virtual group entity updates without polling lag
- Master's callback doesn't fire twice when master changes its own volume

**Implementation:** `pywiim/player/volume.py`

**Usage:**
```python
# Set up callbacks
def on_slave_changed():
    print("Slave state changed")

def on_master_changed():
    print("Master state changed (virtual group entity)")

slave._on_state_changed = on_slave_changed
master._on_state_changed = on_master_changed

# Change slave volume - both callbacks fire
await slave.set_volume(0.8)  # Both callbacks fire
```

### 3. Group Object Design

**How it works:**
- Properties compute dynamically (no caching): `volume_level`, `is_muted`, `play_state`
- Methods delegate to master: `play()`, `pause()`, etc.
- Volume aggregation: `group.volume_level` returns MAX of all devices
- Mute aggregation: `group.is_muted` returns True only when ALL devices muted

**Implementation:** `pywiim/group.py`

**Usage:**
```python
# Dynamic properties - always current
group_volume = master.group.volume_level  # MAX of all devices
group_muted = master.group.is_muted  # True only if ALL muted

# Methods delegate to master
await master.group.pause()  # Calls master.pause()
await slave.group.pause()   # Also calls master.pause() (via routing)
```

## Testing with Real Devices

### Quick Test: CLI Tool

The easiest way to test group routing is with the CLI tool:

```bash
# Test with 2 devices
wiim-group-test 192.168.1.115 192.168.1.116 --interactive

# Test with 3+ devices
wiim-group-test 192.168.1.115 192.168.1.116 192.168.1.68 --interactive
```

This tests the full group lifecycle including routing and metadata propagation.

### Comprehensive Test: Unified Test Runner

For comprehensive testing including routing:

```bash
python scripts/run_tests.py --tier groups --master 192.168.1.115 --slave 192.168.1.116 --yes
```

This runs 9 group tests including command routing verification.

### Manual Test Scenarios

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

### Integration Tests

The following integration tests verify routing behavior:

1. **`test_group_role_detection`** - ✅ Verified
   - Tests role detection and Player linking
   - Located in `tests/integration/test_multiroom_group.py`

2. **`test_group_volume_and_mute_propagation`** - ✅ Verified
   - Tests `group.set_volume_all()` and `group.mute_all()`
   - Located in `tests/integration/test_multiroom_group.py`

3. **`test_slave_playback_via_group`** - ✅ Verified
   - Tests slave playback commands route to master
   - Located in `tests/integration/test_multiroom_group.py`

### Unit Tests

Unit tests in `tests/unit/test_player.py` verify routing logic:

- `test_slave_playback_routes_to_master` - Verifies routing works
- `test_slave_without_group_raises_error` - Verifies edge case handling
- `test_slave_volume_fires_master_callback` - Verifies cross-notification
- `test_master_volume_only_fires_own_callback` - Verifies no duplicate callbacks

All unit tests pass (770+ unit tests total).

## Manual Testing Checklist

When testing with physical devices:

- [ ] Slave playback commands (play/pause/next/previous) work correctly
- [ ] Master physically responds when slave entity receives commands
- [ ] Slave volume changes update virtual group entity immediately
- [ ] Group volume correctly shows MAX of all devices
- [ ] Group mute correctly requires ALL devices muted
- [ ] No errors in logs during normal operation
- [ ] Edge case: unlinked slave shows clear error message
- [ ] Metadata propagation works (master → slaves)
- [ ] Group disband works correctly (all return to SOLO)

## Monitoring

Watch for these log messages during testing:

```
[DEBUG] Slave <host> has no group object, cannot route playback command
[DEBUG] Auto-linking slave <slave_host> to master <master_host>
```

These indicate:
1. A slave tried to use playback without a group (edge case)
2. Player objects are being linked correctly on refresh

## Testing Tools

### CLI Tool

```bash
# Quick interactive test
wiim-group-test 192.168.1.115 192.168.1.116 --interactive

# Automated test with pauses
wiim-group-test 192.168.1.115 192.168.1.116 --pause 5
```

### Unified Test Runner

```bash
# Comprehensive group tests (Tier 5)
python scripts/run_tests.py --tier groups --master 192.168.1.115 --slave 192.168.1.116 --yes
```

### Integration Tests

```bash
# Run multiroom group integration tests
export WIIM_TEST_GROUP_MASTER=192.168.1.115
export WIIM_TEST_GROUP_SLAVES="192.168.1.116,192.168.1.117"
pytest tests/integration/test_multiroom_group.py -v
```

## Summary

The routing architecture enables a cleaner integration pattern where:

- ✅ Integrations just call `player.pause()` on any entity
- ✅ pywiim handles routing automatically
- ✅ Virtual entities update immediately via cross-notification
- ✅ No polling lag, no manual refresh needed
- ✅ Group properties compute dynamically (always current)
- ✅ Edge cases handled gracefully with clear error messages

## Related Documentation

- `docs/integration/HA_INTEGRATION.md` - Virtual Group Entity Implementation and Event Propagation Model
- `docs/integration/API_REFERENCE.md` - Comprehensive Group Object documentation
- `docs/testing/GROUP_TEST_CLI.md` - CLI tool usage guide
- `docs/testing/REAL-DEVICE-TESTING.md` - Unified test runner guide

