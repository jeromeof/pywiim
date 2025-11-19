# Group Test CLI: Usage Guide

## Overview

The `wiim-group-test` CLI tool tests group join/unjoin operations with multiple WiiM devices.

## Features

✅ **Multi-player support**: Test with 2, 3, or more players
✅ **Automated testing**: Run full test suite automatically  
✅ **Visual verification**: Pause between operations to check WiiM app
✅ **Interactive mode**: Step-by-step with detailed status display
✅ **Defensive verification**: Checks library state matches device state

## Usage

### Basic Test (2 players)

```bash
wiim-group-test 192.168.1.115 192.168.1.116 --port 443
```

### Test with 3 Players

```bash
wiim-group-test 192.168.1.115 192.168.1.116 192.168.1.68 --port 443
```

### With Pauses (Visual Verification)

```bash
wiim-group-test 192.168.1.115 192.168.1.116 192.168.1.68 --pause 5 --port 443
```

Pauses 5 seconds between operations so you can verify in the WiiM app.

### Interactive Mode

```bash
wiim-group-test 192.168.1.115 192.168.1.116 192.168.1.68 --interactive --port 443
```

Shows detailed status after each operation:
```
1️⃣  Creating group on leader...
   ✓ Group created

Current State:
------------------------------------------------------------
  Player 1 (Outdoor): MASTER (slaves: 0)
  Player 2 (Master Bedroom): SOLO
  Player 3 (Main Floor Speakers): SOLO
------------------------------------------------------------
Pausing 5s for visual verification in WiiM app...

2️⃣  Joining follower 1 to leader...
   ✓ Follower 1 joined group

Current State:
------------------------------------------------------------
  Player 1 (Outdoor): MASTER (slaves: 1)
  Player 2 (Master Bedroom): SLAVE (master: Outdoor)
  Player 3 (Main Floor Speakers): SOLO
------------------------------------------------------------
```

## Test Sequence

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
  ✓ Create group: Leader became MASTER
  ✓ Join follower 1: Became SLAVE in group
  ✓ Join follower 2: Became SLAVE in group
  ✓ Group size: Group has 3 players
  ✓ All players in group: PASS
  ✓ Leave follower 2: Became SOLO
  ✓ Leave follower 1: Became SOLO
  ✓ Final state - leader: SOLO
  ✓ Final state - follower 1: SOLO
  ✓ Final state - follower 2: SOLO

============================================================
Test Summary
============================================================
Total tests: 13
Passed: 13
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

## Debugging

### Verbose Mode

```bash
wiim-group-test 192.168.1.115 192.168.1.116 --verbose --port 443
```

Shows debug logs from the library.

### What to Check in WiiM App

When using `--pause` or `--interactive`:

1. **After create_group**: Leader should show "ready" (may still show solo)
2. **After join**: Follower should show "grouped" icon
3. **After leave**: Follower should return to normal (ungrouped)
4. **Final**: All players should be ungrouped

## Common Issues

**If tests fail**:
1. Check devices are on same network
2. Ensure HTTPS port (443) is correct
3. Try disbanding any existing groups first (use WiiM app)
4. Check device firmware is up to date

**If group persists after test**:
- Tests auto-disband at the end
- If interrupted (Ctrl+C), manually disband in WiiM app

## Summary

The test script demonstrates that the `pywiim` library correctly handles:
- Creating groups
- Joining players (with automatic preconditions)
- Leaving groups
- Auto-disbanding empty groups
- Maintaining sync between library and device state

Users of the library can simply call operations - the library handles all complexity automatically.

