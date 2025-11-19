# Testing Guide

This directory contains both unit tests (with mocks) and integration tests (with real devices).

## Unit Tests

Unit tests use mocks to test functionality without requiring a real device. They are fast and can be run in CI/CD.

Run unit tests:
```bash
pytest tests/unit/ -v
```

## Integration Tests

Integration tests require a real WiiM device on your network. They test actual device communication.

### Setup

1. **Set environment variable** with your device IP:
   ```bash
   export WIIM_TEST_DEVICE=192.168.1.100
   ```

2. **Optional: Set port** (default is 80):
   ```bash
   export WIIM_TEST_PORT=443
   ```

3. **Optional: Enable HTTPS** (for devices that require HTTPS):
   ```bash
   export WIIM_TEST_HTTPS=true
   ```

### Running Integration Tests

Run all integration tests:
```bash
pytest tests/integration/ -v
```

Run a specific integration test:
```bash
pytest tests/integration/test_real_device.py::TestRealDevice::test_device_connection -v
```

Run only fast integration tests (skip slow ones):
```bash
pytest tests/integration/ -v -m "not slow"
```

### Multi-Device Group Validation

Use the dedicated multi-room test when you have at least two physical players:

1. Provide the master and slave IPs:
   ```bash
   export WIIM_TEST_GROUP_MASTER=192.168.1.115
   export WIIM_TEST_GROUP_SLAVES="192.168.1.116,192.168.1.117"
   ```
   (Set `WIIM_TEST_PORT` / `WIIM_TEST_HTTPS` if your devices require HTTPS.)

2. Run the test suite:
   ```bash
   pytest tests/integration/test_multiroom_group.py -v
   ```

This suite:
- Forces SOLO → MASTER transitions and validates `get_device_group_info()`
- Verifies slaves inherit the virtual master metadata relationship
- Exercises `Group.set_volume_all()` and `Group.mute_all()` propagation rules
- Confirms `Group.next_track()/previous_track()` route to the physical master

> Tip: start playback before running so next/previous commands succeed.

### Test Markers

- `@pytest.mark.integration` - Marks tests as integration tests (requires real device)
- `@pytest.mark.slow` - Marks tests that take longer to run (may change device state)

### Example Test Session

```bash
# Set device IP
export WIIM_TEST_DEVICE=192.168.1.100

# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/unit/ --cov=pywiim --cov-report=html
```

## Writing New Tests

### Unit Test Example

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from pywiim.client import WiiMClient

@pytest.mark.asyncio
async def test_my_feature(mock_client):
    """Test my feature with mocked client."""
    mock_client._request = AsyncMock(return_value={"status": "ok"})
    
    result = await mock_client.some_method()
    
    assert result == {"status": "ok"}
```

### Integration Test Example

```python
import pytest
from pywiim.client import WiiMClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_feature_real_device(real_device_client, integration_test_marker):
    """Test my feature with real device."""
    result = await real_device_client.some_method()
    
    assert result is not None
```

## Test Coverage

Target: 90%+ coverage for core functionality.

Generate coverage report:
```bash
pytest tests/unit/ --cov=pywiim --cov-report=html --cov-report=term
```

View HTML report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Continuous Integration

Integration tests are automatically skipped in CI unless `WIIM_TEST_DEVICE` is set. This allows:
- Unit tests to run in all CI environments
- Integration tests to run only when explicitly enabled (e.g., in nightly builds)

