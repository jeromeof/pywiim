# Pre-Release Real Device Testing Strategy

## Current State

### ✅ What We Have
- **Comprehensive unit tests** with mocks - run in CI/CD for every commit
- **Minimal integration tests** (`test_real_device.py`) - 4 basic smoke tests
- **Comprehensive multiroom tests** (`test_multiroom_group.py`) - thorough group testing
- **CLI verification tool** (`wiim-verify`) - comprehensive but manual
- **Various test scripts** - for specific features (playback, shuffle/repeat, etc.)

### ⚠️ Gaps
- **No Player-level integration tests** - only client-level basic tests
- **No playback control integration tests** - play/pause/shuffle/repeat only in scripts
- **No volume/audio integration tests** - only in `wiim-verify` CLI
- **No source switching integration tests**
- **No EQ/preset integration tests**
- **No state management/caching integration tests**
- **Integration tests not part of release process** - only unit tests run

## Recommendation: Expand Integration Tests

### Strategy: Two-Tier Approach

1. **Core Integration Tests** (always run if device available)
   - Expand `test_real_device.py` with essential Player-level tests
   - Keep fast, non-destructive tests
   - Run automatically if `WIIM_TEST_DEVICE` is set

2. **Pre-Release Integration Tests** (optional, before releases)
   - Comprehensive test suite covering all major features
   - Can be run manually before important releases
   - More thorough than core tests, but still automated

## Proposed Test Expansion

### 1. Core Integration Tests (`test_real_device.py`)

Add these essential tests that should run if a device is available:

```python
# Player-level basic operations
- test_player_initialization
- test_player_refresh
- test_player_properties_access

# Playback controls (non-destructive)
- test_playback_state_read
- test_shuffle_repeat_state_read

# Volume controls (safe - low volume only)
- test_volume_read
- test_mute_read
- test_volume_set_safe (max 10%)

# Source and audio
- test_source_list
- test_audio_output_modes
- test_current_source_read

# State management
- test_state_caching
- test_state_refresh
```

### 2. Pre-Release Integration Tests (`test_prerelease.py`)

Create a new comprehensive test suite for pre-release validation:

```python
# Comprehensive playback testing
- test_playback_controls_full (play/pause/stop/resume)
- test_shuffle_controls_full (with state preservation)
- test_repeat_controls_full (all modes, state preservation)
- test_next_previous_track

# Volume and audio
- test_volume_controls_full (with restoration)
- test_mute_controls_full
- test_audio_output_switching

# Source management
- test_source_switching (if multiple sources available)
- test_source_specific_features

# EQ and presets (if supported)
- test_eq_presets
- test_eq_custom_settings
- test_preset_playback

# State management
- test_state_synchronization
- test_cache_consistency
- test_upnp_event_integration

# Error handling
- test_invalid_commands
- test_network_timeout_handling
- test_device_unavailable_handling
```

## Implementation Plan

### Phase 1: Expand Core Tests (High Priority)

**File**: `tests/integration/test_real_device.py`

Add Player-level tests that are:
- Fast (read-only or minimal state changes)
- Safe (restore state, use low volumes)
- Essential for catching basic regressions

**Benefits**:
- Catches Player-level bugs that mocks miss
- Validates state management works with real devices
- Can run more frequently

### Phase 2: Create Pre-Release Suite (Medium Priority)

**File**: `tests/integration/test_prerelease.py`

Comprehensive test suite that:
- Tests all major features end-to-end
- Restores device state after each test
- Can be run manually before releases
- More thorough than core tests

**Benefits**:
- Catches integration issues before release
- Validates complex feature interactions
- Gives confidence before publishing

### Phase 3: Optional Release Integration (Low Priority)

**Option A**: Add to release script with opt-in flag
```bash
# Run with integration tests
bash scripts/release.sh patch --with-integration-tests

# Run without (default)
bash scripts/release.sh patch
```

**Option B**: Separate pre-release script
```bash
# Run before release
bash scripts/prerelease-check.sh
```

**Recommendation**: Start with Option B (separate script), then consider Option A if it proves valuable.

## When to Run Pre-Release Tests

### Always Run Before:
- **Major releases** (X.0.0) - breaking changes
- **Minor releases** (X.Y.0) - new features
- **After significant refactoring** - even for patch releases

### Optional Before:
- **Patch releases** - if they touch core functionality
- **Regular development** - when working on Player/state management

### Not Required:
- **Documentation-only releases**
- **Dependency updates** (unless major)
- **Minor bug fixes** (unless in critical paths)

## Test Organization

### Markers for Test Selection

```python
@pytest.mark.integration          # All integration tests
@pytest.mark.integration.core     # Core tests (fast, safe)
@pytest.mark.integration.prerelease  # Pre-release tests (comprehensive)
@pytest.mark.integration.slow     # Slow tests (state changes, delays)
@pytest.mark.integration.destructive  # Tests that change device state
```

### Running Tests

```bash
# Core integration tests only (fast)
pytest tests/integration/ -m "integration.core" -v

# Pre-release tests (comprehensive)
pytest tests/integration/ -m "integration.prerelease" -v

# All integration tests
pytest tests/integration/ -v

# Skip slow/destructive tests
pytest tests/integration/ -m "not slow and not destructive" -v
```

## Safety Features

All integration tests should:

1. **Save initial state** before making changes
2. **Restore state** after tests (in finally blocks)
3. **Use safe volumes** (max 10-20% during testing)
4. **Skip gracefully** if device unavailable
5. **Handle errors** without leaving device in bad state
6. **Log operations** for debugging

## Example: Expanded Core Test

```python
@pytest.mark.integration
@pytest.mark.integration.core
@pytest.mark.asyncio
async def test_player_volume_controls_safe(real_device_client, integration_test_marker):
    """Test volume controls with safe limits and state restoration."""
    from pywiim.player import Player
    
    player = Player(real_device_client)
    await player.refresh()
    
    # Save initial state
    initial_volume = await player.get_volume()
    initial_mute = await player.get_muted()
    
    try:
        # Test volume read
        volume = await player.get_volume()
        assert volume is not None
        assert 0.0 <= volume <= 1.0
        
        # Test safe volume change (max 10%)
        safe_volume = min(0.10, volume + 0.05) if volume < 0.10 else 0.10
        await player.set_volume(safe_volume)
        await asyncio.sleep(0.5)
        
        new_volume = await player.get_volume()
        assert abs(new_volume - safe_volume) < 0.05
        
        # Test mute toggle
        await player.set_mute(True)
        await asyncio.sleep(0.5)
        assert await player.get_muted() is True
        
        await player.set_mute(False)
        await asyncio.sleep(0.5)
        assert await player.get_muted() is False
        
    finally:
        # Restore initial state
        await player.set_volume(initial_volume)
        await player.set_mute(initial_mute)
        await asyncio.sleep(0.5)
```

## Benefits of This Approach

1. **Catches Real Issues**: Tests against actual device behavior, not just mocks
2. **Validates State Management**: Ensures caching and state sync work correctly
3. **Prevents Regressions**: Catches issues before they reach users
4. **Flexible**: Can run comprehensive tests when needed, fast tests regularly
5. **Non-Blocking**: Doesn't slow down CI/CD, optional for releases
6. **Developer Confidence**: Know it works on real devices before release

## Next Steps

1. **Expand `test_real_device.py`** with Player-level core tests
2. **Create `test_prerelease.py`** with comprehensive test suite
3. **Add test markers** for better organization
4. **Create `scripts/prerelease-check.sh`** for easy pre-release validation
5. **Document** in RELEASE_PROCESS.md when to run pre-release tests

## Questions to Consider

1. **How many devices** should we test against? (Different models, firmware versions)
2. **Should we test** against different device types? (WiiM Mini, Pro, Audio Pro, etc.)
3. **How often** should comprehensive tests run? (Every release? Major releases only?)
4. **Should we automate** running against multiple devices?

## Conclusion

**Yes, you should expand real-world device testing**, but in a structured way:

- ✅ **Expand core integration tests** - catch basic issues early
- ✅ **Create pre-release test suite** - comprehensive validation before releases
- ✅ **Keep it optional** - don't block releases, but make it easy to run
- ✅ **Focus on Player-level** - that's where most user-facing code lives
- ✅ **Make it safe** - always restore device state

This gives you confidence that the library works on real devices without slowing down development or blocking releases.

