# Group Test CLI: Usage Guide

## Overview

The `wiim-group-test` CLI tool tests group join/unjoin operations and metadata propagation with multiple WiiM devices. This is a standalone CLI tool for focused group testing.

> **Note**: For comprehensive tiered testing including groups, see the [Unified Test Runner](../testing/REAL-DEVICE-TESTING.md#unified-test-runner) (`scripts/run_tests.py --tier groups`).

## Features

✅ **Multi-player support**: Test with 2, 3, or more players  
✅ **Automated testing**: Run full test suite automatically  
✅ **Visual verification**: Pause between operations to check WiiM app  
✅ **Interactive mode**: Step-by-step with detailed status display  
✅ **Defensive verification**: Checks library state matches device state  
✅ **Metadata propagation**: Tests metadata sync from master to slaves

## Installation

The CLI tool is installed automatically with pywiim:

```bash
pip install pywiim
```

Or if developing from source, it's available after installation:

```bash
pip install -e .
```

## Usage

### Basic Test (2 players)

```bash
wiim-group-test 192.168.1.115 192.168.1.116
```

### Test with 3+ Players

```bash
wiim-group-test 192.168.1.115 192.168.1.116 192.168.1.68
```

### HTTPS Devices

```bash
wiim-group-test 192.168.1.115 192.168.1.116 --port 443
```

### With Pauses (Visual Verification)

```bash
wiim-group-test 192.168.1.115 192.168.1.116 192.168.1.68 --pause 5
```

Pauses 5 seconds between operations so you can verify in the WiiM app.

### Interactive Mode

```bash
wiim-group-test 192.168.1.115 192.168.1.116 192.168.1.68 --interactive
```

Shows detailed status after each operation with 5-second pauses:

```
1️⃣  Creating group on leader...
   ✓ Group created: 192.168.1.115 is now ready to accept followers

Current State:
------------------------------------------------------------
  Player 1 (Outdoor): MASTER (slaves: 0)
  Player 2 (Master Bedroom): SOLO
  Player 3 (Main Floor Speakers): SOLO
------------------------------------------------------------
Pausing 5s for visual verification in WiiM app...

2️⃣  Joining follower 1 (192.168.1.116) to leader...
   ✓ Follower 1 joined group

Current State:
------------------------------------------------------------
  Player 1 (Outdoor): MASTER (slaves: 1)
  Player 2 (Master Bedroom): SLAVE (master: Outdoor)
  Player 3 (Main Floor Speakers): SOLO
------------------------------------------------------------
```

### Verbose Output

```bash
wiim-group-test 192.168.1.115 192.168.1.116 --verbose
```

Shows debug logs from the library.

## Test Sequence

The automated test suite runs these tests in order:

1. **Initial State**: Verify all players are SOLO
2. **Create Group**: Leader creates group (becomes MASTER)
3. **Join Followers**: Each follower joins (becomes SLAVE)
4. **Group State**: Verify group size and membership
5. **Metadata Propagation**: Check if metadata syncs (if playing)
6. **Leave Followers**: Each follower leaves (becomes SOLO)
7. **Leave Leader**: Leader disbands (becomes SOLO, or skipped if already disbanded)
8. **Final State**: Verify all players are SOLO

## Example Output

```
============================================================
Group Join/Unjoin Test Suite
============================================================
Leader Player: 192.168.1.115
Follower Players: ['192.168.1.116', '192.168.1.68']
Pause between operations: 5.0s (for visual verification)
============================================================

  ✓ Leader player initial state: SOLO
  ✓ Follower 1 initial state: SOLO
  ✓ Follower 2 initial state: SOLO
  ✓ Create group: Leader became MASTER at 192.168.1.115
  ✓ Join follower 1: Became SLAVE in group
  ✓ Join follower 2: Became SLAVE in group
  ✓ Group size: Group has 3 players
  ✓ All players in group: PASS
  ✓ Metadata propagation (all slaves): All slaves match master metadata
  ✓ Leave follower 2: Became SOLO
  ✓ Leave follower 1: Became SOLO
  ✓ Leave group (leader): MASTER became SOLO, group disbanded
  ✓ Final state - leader: SOLO
  ✓ Final state - follower 1: SOLO
  ✓ Final state - follower 2: SOLO

============================================================
Test Summary
============================================================
Total tests: 15
Passed: 15
Failed: 0
Skipped: 0
============================================================
```

## What the Library Does Automatically

The library handles all complexity:

- ✅ **Preconditions**: Automatically disbands/leaves groups as needed
- ✅ **State Updates**: Updates Group objects immediately after API success
- ✅ **Callbacks**: Calls `on_state_changed` for framework integration
- ✅ **Auto-disband**: Disbands empty groups (master with no slaves)

## Test Verification

Tests verify:

1. **Library state** is correct immediately after operations
2. **Device state** matches library state (defensive verification)
3. **Group membership** is correct (master knows slaves, slaves know master)
4. **Metadata propagation** works (if devices are playing)

## Command-Line Options

```
positional arguments:
  master_ip             Master device IP address or hostname
  slave_ips            Slave device IP addresses or hostnames (one or more)

optional arguments:
  --port PORT          Device port (default: auto-detect, use 80 for HTTP or 443 for HTTPS)
  --verbose, -v        Enable verbose logging
  --pause SECONDS, -p  Pause between operations (for visual verification in WiiM app)
  --interactive, -i    Interactive mode with detailed status after each operation
```

## Debugging

### What to Check in WiiM App

When using `--pause` or `--interactive`:

1. **After create_group**: Leader should show "ready" (may still show solo)
2. **After join**: Follower should show "grouped" icon
3. **After leave**: Follower should return to normal (ungrouped)
4. **Final**: All players should be ungrouped

### Common Issues

**If tests fail**:
1. Check devices are on same network
2. Ensure port is correct (80 for HTTP, 443 for HTTPS)
3. Try disbanding any existing groups first (use WiiM app)
4. Check device firmware is up to date
5. Use `--verbose` to see detailed error messages

**If group persists after test**:
- Tests auto-disband at the end
- If interrupted (Ctrl+C), manually disband in WiiM app

## Comparison with Unified Test Runner

| Feature | `wiim-group-test` | `run_tests.py --tier groups` |
|---------|-------------------|------------------------------|
| Focus | Group operations only | Comprehensive tiered testing |
| Metadata testing | ✅ Yes | ✅ Yes |
| Interactive mode | ✅ Yes | ❌ No |
| Visual verification | ✅ Yes (--pause) | ❌ No |
| Integration with other tests | ❌ No | ✅ Yes (tiers 1-6) |
| Device configuration | Command-line only | YAML config file |
| Best for | Quick group testing | Pre-release validation |

## Summary

The `wiim-group-test` CLI tool demonstrates that the `pywiim` library correctly handles:
- Creating groups
- Joining players (with automatic preconditions)
- Leaving groups
- Auto-disbanding empty groups
- Maintaining sync between library and device state
- Metadata propagation from master to slaves

Users of the library can simply call operations - the library handles all complexity automatically.

