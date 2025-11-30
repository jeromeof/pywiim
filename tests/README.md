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

### Test Suites

Integration tests are organized into two suites:

#### Core Integration Tests (`test_real_device.py`)

Fast, safe tests that validate basic Player functionality. These are read-only or use minimal state changes with automatic restoration.

**Run core tests:**
```bash
pytest tests/integration/test_real_device.py -v
# Or with marker:
pytest tests/integration/ -v -m "core"
```

**What they test:**
- Device connection and capability detection
- Player initialization and refresh
- Property access and state caching
- Volume/mute reading (safe operations)
- Source and audio output mode reading

#### Pre-Release Integration Tests (`test_prerelease.py`)

Comprehensive tests that validate all major Player functionality. These tests change device state and restore it afterward. Run these before important releases.

**Run pre-release tests:**
```bash
pytest tests/integration/test_prerelease.py -v
# Or with marker:
pytest tests/integration/ -v -m "prerelease"
```

**What they test:**
- Full playback controls (play/pause/resume/next/previous)
- Shuffle and repeat controls with state preservation
- Volume and mute controls with restoration
- Source switching
- Audio output mode switching
- State synchronization and cache consistency
- Error handling

**Pre-release check script:**
```bash
# Run comprehensive pre-release validation
bash scripts/prerelease-check.sh 192.168.1.100
```

### Running Integration Tests

Run all integration tests:
```bash
pytest tests/integration/ -v
```

Run only core tests (fast, safe):
```bash
pytest tests/integration/ -v -m "core"
```

Run only pre-release tests (comprehensive):
```bash
pytest tests/integration/ -v -m "prerelease"
```

Run only fast integration tests (skip slow ones):
```bash
pytest tests/integration/ -v -m "not slow"
```

Skip destructive tests (ones that change device state):
```bash
pytest tests/integration/ -v -m "not destructive"
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
- `@pytest.mark.core` - Marks tests as core integration tests (fast, safe)
- `@pytest.mark.prerelease` - Marks tests as pre-release integration tests (comprehensive)
- `@pytest.mark.slow` - Marks tests that take longer to run (may change device state)
- `@pytest.mark.destructive` - Marks tests that change device state (require restoration)

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

### Integration Test Examples

**Core test (read-only, safe):**
```python
import pytest
from pywiim.player import Player

@pytest.mark.integration
@pytest.mark.core
@pytest.mark.asyncio
async def test_my_feature_core(real_device_player, integration_test_marker):
    """Test my feature with real device (safe, read-only)."""
    player = real_device_player
    await player.refresh()
    
    result = await player.some_method()
    assert result is not None
```

**Pre-release test (comprehensive, with state restoration):**
```python
import pytest
from pywiim.player import Player

@pytest.mark.integration
@pytest.mark.prerelease
@pytest.mark.asyncio
async def test_my_feature_comprehensive(real_device_player, integration_test_marker):
    """Test my feature comprehensively with state restoration."""
    player = real_device_player
    await player.refresh()
    
    # Save initial state
    initial_value = await player.get_some_value()
    
    try:
        # Test feature
        await player.set_some_value(new_value)
        result = await player.get_some_value()
        assert result == new_value
    finally:
        # Restore initial state
        if initial_value is not None:
            await player.set_some_value(initial_value)
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

