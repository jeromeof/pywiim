# Testing Guide

This directory contains both unit tests (with mocks) and integration tests (with real devices).

## Quick Start

```bash
# Run unit tests (fast, no device needed)
pytest tests/unit/ -v

# Run integration tests (requires real device)
pytest tests/integration/ -v
```

## Test Structure

```
tests/
├── unit/                    # Mocked unit tests (run in CI)
├── integration/             # Real device tests (require hardware)
│   ├── test_real_device.py  # Smoke tests (Tier 1)
│   ├── test_prerelease.py   # Playback/controls/features tests (Tiers 2-4)
│   ├── test_multiroom_group.py  # Group tests (Tier 5)
│   └── test_media_progress.py   # Media progress tests
├── devices.yaml             # Device configuration
├── test_reports.json        # Auto-generated test results (gitignored)
└── conftest.py              # Fixtures and configuration
```

## Configuration

Edit `tests/devices.yaml` to configure your test devices:

```yaml
default_device: 192.168.1.115

group:
  master: 192.168.1.115
  slaves:
    - 192.168.1.116

settings:
  max_test_volume: 0.15
```

Environment variables override the config file:
- `WIIM_TEST_DEVICE` - Override default device
- `WIIM_TEST_GROUP_MASTER` - Override group master
- `WIIM_TEST_GROUP_SLAVES` - Override group slaves (comma-separated)

## Test Tiers

Integration tests are organized into tiers based on prerequisites:

| Tier | Marker | Tests | Prerequisites |
|------|--------|-------|---------------|
| 1 | `smoke` | Connectivity, volume, mute | Any device state |
| 2 | `playback` | Play/pause/next/prev | Media playing |
| 3 | `controls` | Shuffle/repeat | Album/playlist (not radio) |
| 4 | `features` | EQ, presets, outputs | Device-specific |
| 5 | `groups` | Multi-room grouping | 2+ devices |

### Running Specific Tiers

```bash
# Run only smoke tests (always safe)
pytest tests/integration/ -m smoke -v

# Run playback tests (start media first)
pytest tests/integration/ -m playback -v

# Run shuffle/repeat tests (play an album first)
pytest tests/integration/ -m controls -v

# Run feature tests (EQ, presets, outputs)
pytest tests/integration/ -m features -v

# Run group tests (requires multiple devices)
pytest tests/integration/ -m groups -v

# Run all comprehensive tests
pytest tests/integration/ -m prerelease -v

# Combine tiers
pytest tests/integration/ -m "smoke or playback" -v
```

## Test Reports

Integration tests automatically save results to `tests/test_reports.json` (gitignored).

View the report:
```bash
cat tests/test_reports.json
```

Example output:
```json
{
  "last_updated": "2025-12-06T14:30:00",
  "device": "192.168.1.115",
  "tiers": {
    "smoke": {"last_run": "2025-12-06T14:30:00", "passed": 8, "failed": 0, "success": true},
    "playback": {"last_run": "2025-12-05T10:15:00", "passed": 5, "failed": 0, "success": true}
  }
}
```

## Pre-Release Checklist

Before releasing, run tests based on what code changed:

| Changed Code | Run Tiers |
|--------------|-----------|
| `pywiim/client.py` | All (core dependency) |
| `pywiim/player/media.py` | smoke, playback |
| `pywiim/player/audio.py` | smoke, features |
| `pywiim/player/group.py` | smoke, groups |
| `pywiim/player/controls.py` | smoke, controls |
| Docs only | None |

Quick pre-release suite:
```bash
# Run smoke + playback + controls
pytest tests/integration/ -m "smoke or playback or controls" -v
```

## Unit Tests

Unit tests use mocks and run without hardware. They are fast and CI-safe.

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=pywiim --cov-report=html
```

## Integration Tests

Integration tests require real WiiM devices on your network.

### Setup

1. Configure devices in `tests/devices.yaml`, or
2. Set environment variable: `export WIIM_TEST_DEVICE=192.168.1.100`

### Running Tests

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific tier
pytest tests/integration/ -m smoke -v

# Skip integration tests (CI mode)
pytest tests/unit/ -v  # Just run unit tests
```

### Multi-Device Group Tests

For group tests, configure master and slaves:

```yaml
# In tests/devices.yaml
group:
  master: 192.168.1.115
  slaves:
    - 192.168.1.116
    - 192.168.1.117
```

Or via environment:
```bash
export WIIM_TEST_GROUP_MASTER=192.168.1.115
export WIIM_TEST_GROUP_SLAVES="192.168.1.116,192.168.1.117"
pytest tests/integration/ -m groups -v
```

## Test Quality Guidelines

### Behavior Tests vs Mock Verification

**Prefer behavior tests** that verify business logic over shallow mock verification.

```python
# GOOD: Tests actual behavior
async def test_play_updates_state_and_triggers_callback(self, mock_client):
    callback_called = []
    player = Player(mock_client, on_state_changed=lambda: callback_called.append(True))
    
    await player.play()
    
    assert player._status_model.play_state == "play"  # Business logic
    assert len(callback_called) == 1  # Callback fired

# AVOID: Just verifies mock was called
async def test_play(self, mock_client):
    await player.play()
    mock_client.play.assert_called_once()  # Shallow
```

### What to Test

**Focus on business logic:**
- State synchronization and merging
- Optimistic updates
- Callback notifications
- Error handling and recovery
- Role transitions (solo → master → slave)
- Source conflict resolution

## Interactive/Manual Tests

Tests requiring human observation are in `scripts/manual/`:
- `interactive-playback-test.py` - Menu-driven playback testing
- `test-shuffle-repeat-by-source.py` - Source-specific shuffle/repeat testing

These cannot be automated and are not part of the pytest suite.

## Coverage

Target: 90%+ coverage for core functionality.

```bash
pytest tests/unit/ --cov=pywiim --cov-report=html --cov-report=term
open htmlcov/index.html  # View report
```

## Continuous Integration

Integration tests are automatically skipped in CI unless device is configured:
- Unit tests run on every push
- Integration tests only run when `WIIM_TEST_DEVICE` is set
