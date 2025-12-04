# Multi-Device Group Test Scripts

These scripts are for testing multi-room grouping functionality.
They require 2+ physical devices on the network.

## Scripts

### `test_group_join_unjoin.py`

Tests group join and unjoin operations.

### `test-group-real-devices.py`

Comprehensive group testing script.

### `test-master-slave-basic.py`

Basic master/slave relationship testing.

## Prerequisites

- 2+ WiiM/LinkPlay devices on the network
- Devices should NOT be in a group before starting
- Configure device IPs in the scripts or via environment variables

## Future: Tier 5 Integration

These scripts will be integrated into the unified test runner (`run_tests.py`)
as Tier 5 (Groups) tests. The integration will support:

- `python scripts/run_tests.py --tier groups`
- Automatic group creation and dissolution
- Volume propagation testing
- Command routing (slave → master) testing
- Virtual master detection

## Environment Variables

For pytest integration tests:
```bash
export WIIM_TEST_GROUP_MASTER=192.168.1.115
export WIIM_TEST_GROUP_SLAVES="192.168.1.116,192.168.1.117"
pytest tests/integration/test_multiroom_group.py -v
```

