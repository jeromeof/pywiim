# Multi-Room Group Test Scripts

Comprehensive tests for WiiM/LinkPlay multi-room grouping functionality.
Requires 2+ physical devices on the network.

## Quick Start

```bash
# Run all tests on all configured devices
source .venv/bin/activate
python scripts/groups/test_group_operations.py
python scripts/groups/test_group_controls.py
python scripts/groups/test_group_metadata.py

# Run tests for specific subnet only
python scripts/groups/test_group_operations.py --subnet 6 --verbose
```

## Test Files

### `test_group_operations.py` - Join/Leave Permutations

Tests all group operation permutations:

| Category | Tests |
|----------|-------|
| **Basic Operations** | Create group, basic join/leave |
| **Join Permutations** | Solo→Master, Solo→Slave (slave becomes master), Master→Master (auto-disband), Slave→different Master |
| **Expected Failures** | Cross-subnet join (should fail), wmrm_version incompatibility |
| **Leave Permutations** | Slave leaves, Master leaves (disbands), group.disband() |
| **Multiple Devices** | Join/leave sequences with 3+ devices |

### `test_group_controls.py` - Player Controls, Volume, Mute

Tests all control operations:

| Category | Tests |
|----------|-------|
| **Player Controls Routing** | slave.play()→master, slave.pause()→master, slave.next/previous_track() |
| **Individual Volume/Mute** | Master volume, slave volume (independent), master mute, slave mute |
| **Virtual Master Controls** | group.set_volume_all(), group.volume_level (max), group.mute_all(), group.is_muted (all) |

### `test_group_metadata.py` - Metadata Propagation

Tests metadata synchronization:

| Category | Tests |
|----------|-------|
| **Metadata on Join** | Slave gets master metadata immediately on join |
| **During Playback** | Metadata stays synced, play state synchronization |
| **Virtual Master** | group.media_title/artist/album delegate to master |
| **Propagation** | Master propagates to all slaves (3+ devices) |

## Device Configuration

Edit `devices.json` to configure your test devices:

```json
{
  "subnets": {
    "192.168.1.x": {
      "devices": [
        {"ip": "192.168.1.115", "name": "Device 1"},
        {"ip": "192.168.1.116", "name": "Device 2"}
      ]
    },
    "192.168.6.x": {
      "devices": [
        {"ip": "192.168.6.50", "name": "Main Deck", "model": "Arylic H50"}
      ]
    }
  },
  "test_radio_url": "http://ice1.somafm.com/groovesalad-128-mp3"
}
```

## Command-Line Options

All test scripts support:

| Option | Description |
|--------|-------------|
| `--subnet 1` | Test only 192.168.1.x devices |
| `--subnet 6` | Test only 192.168.6.x devices |
| `--subnet all` | Test all devices (default) |
| `--verbose`, `-v` | Show detailed test output |

## Test Requirements

- **2+ devices**: Most tests require at least 2 devices on the same subnet
- **3+ devices**: Some tests (solo→slave, master→master, multi-slave) require 3 devices
- **Same subnet**: Devices must be on the same subnet to group successfully
- **Cross-subnet**: Tests verify cross-subnet grouping correctly fails

## Expected Failures

These scenarios are tested to verify they fail correctly:

1. **Cross-subnet grouping**: Devices on different subnets cannot group
2. **wmrm_version incompatibility**: Gen1 (2.x) cannot group with Gen2+ (4.x)

## Future: Tier 5 Integration

These tests will be integrated into `run_tests.py` as Tier 5 (Groups):

```bash
python scripts/run_tests.py --tier groups
```

## Environment Variables

For pytest integration tests:

```bash
export WIIM_TEST_GROUP_MASTER=192.168.1.115
export WIIM_TEST_GROUP_SLAVES="192.168.1.116,192.168.1.117"
pytest tests/integration/test_multiroom_group.py -v
```
