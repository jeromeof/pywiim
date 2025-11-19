# Real Device Testing Guide

This guide covers testing pywiim functionality against real WiiM/LinkPlay devices.

## Prerequisites

1. Ensure the virtual environment is activated:
```bash
cd /home/mike/projects/pywiim
source .venv/bin/activate
```

2. Find your device IP address (check your router or WiiM app)

3. Ensure device is on the network and accessible

## Quick Verification - Play/Pause/Shuffle/Repeat

### ✅ Unit Tests (All Passed)

All unit tests for play/pause/shuffle/repeat methods have been verified:

```bash
# Run specific playback control tests
pytest tests/unit/test_player.py::TestPlayerPlaybackControl -v

# Results: 6/6 tests passed ✓
# - test_play ✓
# - test_pause ✓
# - test_set_shuffle ✓
# - test_set_shuffle_off ✓
# - test_set_repeat ✓
# - test_set_repeat_off ✓
```

### 🎯 Automated Real Device Testing

Use the automated test script to verify all playback controls:

```bash
python scripts/test-playback-controls.py <device_ip>
```

**Example:**
```bash
python scripts/test-playback-controls.py 192.168.1.100
```

**What it tests:**
- ✅ Play command
- ✅ Pause command
- ✅ Shuffle ON/OFF (verifies state preservation)
- ✅ Repeat modes: OFF/ONE/ALL (verifies state preservation)
- ✅ Automatic state restoration after tests

**Expected output:**
```
🎵 Testing Playback Controls on 192.168.1.100
======================================================================

📋 Connecting to device...
   ✓ Connected: Living Room
   ✓ Model: WiiM Mini
   ✓ Firmware: 4.8.502906

📊 Initial State:
   Play State: play
   Shuffle: False
   Repeat: off

🎯 Test 1: Play Command
   ✓ Play command sent
   State after play: play

🎯 Test 2: Pause Command
   ✓ Pause command sent
   State after pause: pause

🎯 Test 3: Shuffle Control
   Testing shuffle ON...
   ✓ Set shuffle ON
   Shuffle state: True
   Repeat preserved: off
   Testing shuffle OFF...
   ✓ Set shuffle OFF
   Shuffle state: False
   Repeat preserved: off

🎯 Test 4: Repeat Control
   Testing repeat ALL...
   ✓ Set repeat ALL
   Repeat mode: all
   Shuffle preserved: False
   Testing repeat ONE...
   ✓ Set repeat ONE
   Repeat mode: one
   Shuffle preserved: False
   Testing repeat OFF...
   ✓ Set repeat OFF
   Repeat mode: off
   Shuffle preserved: False

🔄 Restoring initial state...
   ✓ State restored

======================================================================
✅ All tests completed!
======================================================================
```

### 🎮 Interactive Manual Testing

For hands-on manual testing and exploration:

```bash
python scripts/interactive-playback-test.py <device_ip>
```

**Example:**
```bash
python scripts/interactive-playback-test.py 192.168.1.100
```

**Features:**
- Interactive menu-driven interface
- Real-time status display
- Manual control of all playback functions

**Available commands:**
```
  1  - Play
  2  - Pause
  3  - Resume
  4  - Stop
  5  - Next Track
  6  - Previous Track
  s  - Show Current Status
  h+ - Shuffle ON
  h- - Shuffle OFF
  r0 - Repeat OFF
  r1 - Repeat ONE
  ra - Repeat ALL
  q  - Quit
```

## Method Details

### Play/Pause Methods

**Available methods:**
```python
await player.play()      # Start playback
await player.pause()     # Pause playback
await player.resume()    # Resume from pause
await player.stop()      # Stop playback
```

**Properties:**
```python
player.play_state        # Returns: "play", "pause", "stop", etc.
```

### Shuffle Control

**Methods:**
```python
await player.set_shuffle(True)   # Enable shuffle
await player.set_shuffle(False)  # Disable shuffle
```

**Properties:**
```python
player.shuffle_state     # Returns: True/False/None
player.shuffle          # Alias for shuffle_state
```

**Important:** Setting shuffle preserves the current repeat mode.

### Repeat Control

**Methods:**
```python
await player.set_repeat("off")   # Disable repeat
await player.set_repeat("one")   # Repeat current track
await player.set_repeat("all")   # Repeat all tracks
```

**Properties:**
```python
player.repeat_mode      # Returns: "off", "one", "all", or None
player.repeat          # Alias for repeat_mode
```

**Important:** Setting repeat preserves the current shuffle state.

## Loop Mode Mapping

Under the hood, shuffle and repeat are controlled by a single `loop_mode` value:

| Mode | Shuffle | Repeat | loop_mode Value |
|------|---------|--------|-----------------|
| Normal | Off | Off | 0 |
| Repeat One | Off | One | 1 |
| Repeat All | Off | All | 2 |
| Shuffle | On | Off | 4 |
| Shuffle + Repeat One | On | One | 5 |
| Shuffle + Repeat All | On | All | 6 |

The Player class automatically manages these combinations to preserve state when you change shuffle or repeat individually.

## Troubleshooting

### Device not responding
- Verify device IP address
- Check device is powered on and connected to network
- Try pinging the device: `ping <device_ip>`
- Check firewall settings

### Tests fail but device works manually
- Ensure device has media in queue
- Try refreshing player state: `await player.refresh()`
- Check device firmware is up to date

### State not updating
- Allow 1-2 seconds for state changes to propagate
- Call `await player.refresh()` to force state update
- Some older firmware versions may have delays

## Integration Test Configuration

For pytest integration tests:

```bash
# Set environment variable
export WIIM_TEST_DEVICE=192.168.1.100

# Run integration tests
pytest tests/integration/test_real_device.py -v -m integration

# For HTTPS devices
export WIIM_TEST_HTTPS=true
pytest tests/integration/test_real_device.py -v -m integration
```

## Multi-Device Group Validation

Use the multi-room regression test to prove master/slave logic, volume/mute propagation, and command routing:

### Environment

```bash
export WIIM_TEST_GROUP_MASTER=192.168.1.115
export WIIM_TEST_GROUP_SLAVES="192.168.1.116,192.168.1.117"
# Optional overrides reused from single-device tests:
export WIIM_TEST_PORT=443
export WIIM_TEST_HTTPS=true
```

### Test Run

```bash
pytest tests/integration/test_multiroom_group.py -v
```

### What It Verifies

- SOLO ➜ MASTER ➜ SLAVE transitions via `Player.create_group()` / `join_group()`
- `get_device_group_info()` consistency for master and every slave
- Virtual master state feeding slaves (metadata + source pointer)
- Group volume/mute rules (`Group.set_volume_all` & `Group.mute_all`)
- Routing of `Group.next_track()` / `Group.previous_track()` back to the physical master

### Checklist Before Running

1. All devices reachable on the same network (no existing group sessions)
2. Optional: start playback so next/previous commands succeed
3. Virtualenv activated:  
   ```bash
   cd /home/mike/projects/pywiim
   source .venv/bin/activate
   ```
4. Run the test and watch the console for PASS/SKIP results. Any assertion failure indicates a regression in the group handling rules.

## Next Steps

After verifying basic playback controls:
1. Test group operations (if you have multiple devices)
2. Test preset playback
3. Test URL/stream playback
4. Test volume and mute controls
5. Test EQ settings

See `docs/testing/` for more testing guides.

