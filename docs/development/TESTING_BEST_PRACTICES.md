# Testing Best Practices for pywiim

## Overview

This document outlines testing best practices, test organization, and coverage goals for the pywiim library. It provides guidance on what to test, how to organize tests, and what testing strategies work best for this type of library.

## Current Testing State

### Existing Test Infrastructure

✅ **What's Already in Place:**
- pytest configuration with async support (`pytest-asyncio`)
- Test fixtures for mocking (`conftest.py`)
- Unit test structure (`tests/unit/`)
- Integration test structure (`tests/integration/`)
- Mock fixtures for client, session, capabilities
- Integration test fixtures for real devices
- Test markers (`@pytest.mark.integration`, `@pytest.mark.slow`)

✅ **Existing Tests:**

**Core Tests:**
- `test_client.py` - Client initialization and capability detection
- `test_exceptions.py` - Exception hierarchy
- `test_models.py` - Pydantic models validation
- `test_capabilities.py` - Capability detection logic
- `test_state.py` - State synchronization
- `test_discovery.py` - Device discovery
- `test_normalize.py` - Normalization helpers
- `test_group_helpers.py` - Group utilities
- `test_polling.py` - Polling strategies
- `test_backoff.py` - Backoff controllers
- `test_parser.py` - Response parsing
- `test_player.py` - Player functionality
- `test_role.py` - Role management
- `test_group.py` - Group functionality (unit level)

**API Mixin Tests:**
- `api/test_base.py` - Base HTTP client
- `api/test_parser.py` - Response parsing
- `api/test_endpoints.py` - Endpoint abstraction
- `api/test_device.py` - Device API
- `api/test_playback.py` - Playback API
- `api/test_group.py` - Group API
- `api/test_eq.py` - EQ API
- `api/test_preset.py` - Preset API
- `api/test_bluetooth.py` - Bluetooth API
- `api/test_audio_settings.py` - Audio settings
- `api/test_lms.py` - LMS integration
- `api/test_misc.py` - Miscellaneous API
- `api/test_firmware.py` - Firmware API
- `api/test_timer.py` - Timer API
- `api/test_ssl.py` - SSL/TLS handling

**UPnP Tests:**
- `upnp/test_client.py` - UPnP client
- `upnp/test_eventer.py` - UPnP event handling

**Integration Tests:**
- `test_real_device.py` - Integration tests with real devices

### Gaps in Current Testing

❌ **Missing Test Coverage:**
- `api/test_diagnostics.py` - Diagnostics API (reboot, time sync, raw commands)

## Test Organization Strategy

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── README.md                # Testing guide
│
├── unit/                    # Fast unit tests with mocks
│   ├── __init__.py
│   ├── test_client.py       # ✅ Client initialization
│   ├── test_exceptions.py   # ✅ Exception hierarchy
│   ├── test_models.py       # ✅ Pydantic models
│   ├── test_capabilities.py # ✅ Capability detection
│   ├── test_state.py        # ✅ State synchronization
│   ├── test_discovery.py    # ✅ Device discovery
│   ├── test_normalize.py    # ✅ Normalization helpers
│   ├── test_group_helpers.py # ✅ Group utilities
│   ├── test_polling.py      # ✅ Polling strategies
│   ├── test_backoff.py      # ✅ Backoff controllers
│   ├── test_parser.py       # ✅ Response parsing
│   ├── test_player.py       # ✅ Player functionality
│   ├── test_role.py         # ✅ Role management
│   ├── test_group.py        # ✅ Group functionality
│   │
│   ├── api/                 # API mixin tests
│   │   ├── __init__.py
│   │   ├── test_base.py     # ✅ Base HTTP client
│   │   ├── test_parser.py   # ✅ Response parsing
│   │   ├── test_endpoints.py # ✅ Endpoint abstraction
│   │   ├── test_device.py   # ✅ Device API
│   │   ├── test_playback.py # ✅ Playback API
│   │   ├── test_group.py    # ✅ Group API
│   │   ├── test_eq.py       # ✅ EQ API
│   │   ├── test_preset.py   # ✅ Preset API
│   │   ├── test_bluetooth.py # ✅ Bluetooth API
│   │   ├── test_audio_settings.py # ✅ Audio settings
│   │   ├── test_lms.py      # ✅ LMS integration
│   │   ├── test_misc.py     # ✅ Misc API
│   │   ├── test_firmware.py # ✅ Firmware API
│   │   ├── test_timer.py    # ✅ Timer API
│   │   ├── test_ssl.py      # ✅ SSL/TLS handling
│   │   └── test_diagnostics.py # ❌ Missing - Diagnostics API
│   │
│   └── upnp/                # UPnP tests
│       ├── test_client.py   # ✅ UPnP client
│       └── test_eventer.py  # ✅ UPnP event handling
│
└── integration/             # Tests with real devices
    ├── __init__.py
    └── test_real_device.py  # ✅ Integration tests
```

## Test Categories and Best Practices

### 1. Unit Tests (Fast, Isolated, Mocked)

**Purpose:** Test individual functions and classes in isolation with mocked dependencies.

**Best Practices:**
- ✅ Use mocks for all external dependencies (HTTP, UPnP, network)
- ✅ Test one thing at a time (single responsibility)
- ✅ Test both success and failure paths
- ✅ Test edge cases and boundary conditions
- ✅ Keep tests fast (< 100ms each)
- ✅ Use descriptive test names: `test_<function>_<scenario>_<expected_result>`

**Example Structure:**
```python
@pytest.mark.asyncio
async def test_set_volume_valid_range(mock_client):
    """Test setting volume within valid range."""
    mock_client._request = AsyncMock(return_value={"status": "ok"})
    
    await mock_client.set_volume(0.5)
    
    mock_client._request.assert_called_once()
    call_args = mock_client._request.call_args
    assert "vol" in str(call_args)

@pytest.mark.asyncio
async def test_set_volume_out_of_range(mock_client):
    """Test setting volume outside valid range raises error."""
    with pytest.raises(ValueError, match="Volume must be"):
        await mock_client.set_volume(1.5)
```

**Priority Modules for Unit Tests:**
1. ✅ **Models** (`test_models.py`) - Pydantic validation, field aliases, defaults
2. ✅ **Base API Client** (`test_base.py`) - HTTP transport, retry logic, error handling
3. ✅ **Parser** (`test_parser.py`) - Response parsing, data transformation
4. ✅ **Capabilities** (`test_capabilities.py`) - Vendor detection, capability probing
5. ✅ **API Mixins** - All API modules have comprehensive tests (except diagnostics)

### 2. Integration Tests (Real Devices)

**Purpose:** Test actual communication with real devices to catch protocol issues.

**Best Practices:**
- ✅ Use environment variables for device configuration
- ✅ Skip tests if device not available (don't fail CI)
- ✅ Mark slow tests that change device state
- ✅ Restore device state after tests when possible
- ✅ Test happy paths and common scenarios
- ✅ Test with different device types (WiiM, Audio Pro, etc.)

**Example Structure:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_player_status_real_device(real_device_client, integration_test_marker):
    """Test getting player status from real device."""
    status = await real_device_client.get_player_status()
    
    assert status is not None
    assert "play_state" in status or "state" in status
```

**Priority Integration Tests:**
1. ✅ **Device Communication** - Basic connectivity, protocol detection (covered in `test_real_device.py`)
2. ✅ **Capability Detection** - Real device capability probing (covered in `test_real_device.py`)
3. ✅ **UPnP Events** - Real-time event subscriptions (covered in `upnp/test_eventer.py`)
4. ✅ **Discovery** - SSDP/UPnP discovery (covered in `test_discovery.py`)

Note: UPnP event handling is tested at the unit level. Integration tests focus on real device communication scenarios.

### 3. Test Fixtures and Mocking Strategy

**Current Fixtures (Good):**
- `mock_client` - Pre-configured client with mocked session
- `mock_capabilities` - Device capabilities dict
- `mock_device_info` - DeviceInfo model
- `mock_player_status` - PlayerStatus model
- `real_device_client` - Real device connection

**Recommended Additional Fixtures:**
```python
@pytest.fixture
def mock_http_response_success():
    """Mock successful HTTP response."""
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={"status": "ok"})
    return response

@pytest.fixture
def mock_http_response_error():
    """Mock error HTTP response."""
    response = MagicMock()
    response.status = 500
    response.json = AsyncMock(side_effect=aiohttp.ClientError("Server error"))
    return response

@pytest.fixture
def mock_upnp_device():
    """Mock UPnP device for event testing."""
    # Mock UPnP device structure
    pass

@pytest.fixture
def sample_device_responses():
    """Sample API responses for different device types."""
    return {
        "wiim_pro": {...},
        "audio_pro_mkii": {...},
    }
```

## Testing Best Practices by Module Type

### API Mixin Modules

**What to Test:**
1. **Method Signatures** - Correct parameters, return types
2. **HTTP Request Construction** - Correct endpoints, parameters
3. **Response Parsing** - Data transformation, model creation
4. **Error Handling** - Exception types, error messages
5. **Capability Gating** - Methods that check capabilities before execution
6. **Edge Cases** - Invalid inputs, None values, empty responses

**Example Test Pattern:**
```python
class TestPlaybackAPI:
    """Test PlaybackAPI mixin methods."""
    
    @pytest.mark.asyncio
    async def test_play_success(self, mock_client):
        """Test successful play command."""
        mock_client._request = AsyncMock(return_value={"status": "ok"})
        
        await mock_client.play()
        
        mock_client._request.assert_called_once()
        # Verify correct endpoint was called
    
    @pytest.mark.asyncio
    async def test_play_network_error(self, mock_client):
        """Test play command with network error."""
        mock_client._request = AsyncMock(side_effect=WiiMConnectionError("Connection failed"))
        
        with pytest.raises(WiiMConnectionError):
            await mock_client.play()
```

### Pydantic Models

**What to Test:**
1. **Field Validation** - Required fields, type validation
2. **Field Aliases** - API key mapping (e.g., `DeviceName` → `name`)
3. **Default Values** - Optional fields with defaults
4. **Extra Fields** - Forward compatibility (`extra="allow"`)
5. **Field Validators** - Custom validation logic
6. **Serialization** - Model to dict conversion

**Example Test Pattern:**
```python
class TestDeviceInfo:
    """Test DeviceInfo model."""
    
    def test_device_info_required_fields(self):
        """Test DeviceInfo with required fields."""
        info = DeviceInfo(
            uuid="test-uuid",
            name="Test Device",
            model="WiiM Pro"
        )
        assert info.uuid == "test-uuid"
        assert info.name == "Test Device"
    
    def test_device_info_field_aliases(self):
        """Test DeviceInfo field aliases match API keys."""
        info = DeviceInfo(DeviceName="Test", project="WiiM Pro", MAC="AA:BB:CC:DD:EE:FF")
        assert info.name == "Test"
        assert info.model == "WiiM Pro"
        assert info.mac == "AA:BB:CC:DD:EE:FF"
    
    def test_device_info_extra_fields(self):
        """Test DeviceInfo allows extra fields for forward compatibility."""
        info = DeviceInfo(
            uuid="test",
            unknown_field="value"  # Should not raise error
        )
        assert hasattr(info, "unknown_field")
```

### Capability Detection

**What to Test:**
1. **Vendor Detection** - WiiM vs Audio Pro vs Arylic
2. **Device Type Detection** - WiiM device vs legacy device
3. **Generation Detection** - Audio Pro mkii vs w_generation vs original
4. **Endpoint Probing** - Runtime capability testing
5. **Protocol Detection** - HTTP vs HTTPS, port detection
6. **Caching** - Capability caching behavior

**Example Test Pattern:**
```python
class TestWiiMCapabilities:
    """Test capability detection."""
    
    @pytest.mark.asyncio
    async def test_detect_vendor_wiim(self, mock_client):
        """Test detecting WiiM vendor."""
        mock_device_info = DeviceInfo(model="WiiM Pro", firmware="5.0.1")
        mock_client.get_device_info_model = AsyncMock(return_value=mock_device_info)
        
        capabilities = WiiMCapabilities(mock_client)
        result = await capabilities.detect_capabilities()
        
        assert result["vendor"] == "wiim"
        assert result["is_wiim_device"] is True
    
    @pytest.mark.asyncio
    async def test_detect_audio_pro_generation(self, mock_client):
        """Test detecting Audio Pro generation."""
        # Test mkii detection
        # Test w_generation detection
        # Test original detection
        pass
```

### State Synchronization

**What to Test:**
1. **State Updates** - State changes from API calls
2. **State Callbacks** - Callback invocation on state changes
3. **State Merging** - Merging partial state updates
4. **State Validation** - Valid state transitions
5. **UPnP Integration** - State updates from UPnP events

### Error Handling

**What to Test:**
1. **Exception Types** - Correct exception for each error scenario
2. **Exception Messages** - Helpful error messages with context
3. **Retry Logic** - Retry on transient errors
4. **Timeout Handling** - Timeout exceptions
5. **Connection Errors** - Network failures
6. **Response Errors** - Invalid responses, parsing errors

## Coverage Goals

### Target Coverage Levels

- **Overall Coverage:** 85%+ (aim for 90%+)
- **Core Modules:** 95%+ (client, base API, models, exceptions)
- **API Mixins:** 85%+ (all API methods)
- **Utilities:** 90%+ (helpers, normalization, parsing)
- **CLI Tools:** 70%+ (lower priority, integration-focused)

### Coverage Exclusions

**Acceptable to Exclude:**
- CLI entry points (`if __name__ == "__main__"`)
- Deprecated code paths
- Platform-specific code that can't be tested
- Integration test fixtures

**Use Coverage Comments:**
```python
def some_function():
    # pragma: no cover - CLI entry point
    if __name__ == "__main__":
        main()
```

## Test Execution Strategy

### Running Tests

```bash
# Run all unit tests (fast)
pytest tests/unit/ -v

# Run all tests with coverage
pytest tests/unit/ --cov=pywiim --cov-report=html --cov-report=term

# Run integration tests (requires device)
WIIM_TEST_DEVICE=192.168.1.100 pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_playback.py -v

# Run specific test
pytest tests/unit/test_playback.py::TestPlaybackAPI::test_play_success -v

# Run tests matching pattern
pytest tests/unit/ -k "volume" -v

# Run fast tests only (skip slow integration tests)
pytest tests/ -v -m "not slow"
```

### CI/CD Integration

**Recommended CI Strategy:**
1. **Unit Tests** - Run on every commit (fast, no external dependencies)
2. **Integration Tests** - Run on PRs and nightly builds (requires device)
3. **Coverage Reports** - Generate and track coverage trends
4. **Linting** - Run ruff, mypy, black checks

**Example GitHub Actions:**
```yaml
# Run unit tests on every push
- name: Run unit tests
  run: pytest tests/unit/ --cov=pywiim --cov-report=xml

# Run integration tests on schedule or manual trigger
- name: Run integration tests
  env:
    WIIM_TEST_DEVICE: ${{ secrets.WIIM_TEST_DEVICE }}
  run: pytest tests/integration/ -v
```

## Test Data Management

### Mock Responses

**Current Approach:**
- Mock responses are defined inline in test files using fixtures and `AsyncMock`
- Test data is created programmatically in `conftest.py` and individual test files
- This approach keeps tests self-contained and easy to understand

**Optional: Store Sample Responses (Future Enhancement):**
If you want to store sample API responses for reference or reuse:
- Create `tests/fixtures/responses/` directory
- Store JSON responses from real devices
- Use for testing parsers and models
- Update when API changes

**Example Helper (if using fixtures directory):**
```python
# tests/helpers.py
def load_fixture_response(name: str) -> dict:
    """Load a fixture response JSON file."""
    path = Path(__file__).parent / "fixtures" / "responses" / f"{name}.json"
    return json.loads(path.read_text())
```

## Testing Async Code

### Best Practices for Async Tests

1. **Always use `@pytest.mark.asyncio`** for async test functions
2. **Use `AsyncMock`** for mocking async functions
3. **Test async context managers** properly
4. **Handle async cleanup** in fixtures
5. **Test concurrent operations** when relevant

**Example:**
```python
@pytest.mark.asyncio
async def test_concurrent_requests(mock_client):
    """Test handling concurrent API requests."""
    mock_client._request = AsyncMock(return_value={"status": "ok"})
    
    # Make concurrent requests
    results = await asyncio.gather(
        mock_client.get_player_status(),
        mock_client.get_device_info_model(),
        mock_client.get_volume(),
    )
    
    assert len(results) == 3
    assert mock_client._request.call_count == 3
```

## Property-Based Testing (Optional)

Consider using `hypothesis` for property-based testing of:
- Data normalization functions
- State transitions
- Model validation
- Parser edge cases

**Example:**
```python
from hypothesis import given, strategies as st

@given(volume=st.floats(min_value=0.0, max_value=1.0))
def test_volume_normalization(volume):
    """Test volume normalization with any valid float."""
    normalized = normalize_volume(volume)
    assert 0.0 <= normalized <= 1.0
```

## Test Maintenance

### Keeping Tests Up to Date

1. **Update tests when API changes** - Don't let tests become stale
2. **Review test failures carefully** - Don't just fix tests, understand failures
3. **Refactor tests** - Keep tests DRY, use fixtures effectively
4. **Remove obsolete tests** - Delete tests for removed features
5. **Document test assumptions** - Use docstrings to explain test intent

### Test Review Checklist

When reviewing test PRs:
- [ ] Tests are fast (< 100ms each)
- [ ] Tests are isolated (no shared state)
- [ ] Tests cover both success and failure paths
- [ ] Tests use descriptive names
- [ ] Tests have docstrings explaining purpose
- [ ] Mocks are properly configured
- [ ] Edge cases are covered
- [ ] Integration tests are marked appropriately

## Summary: Current Test Status

### ✅ Completed Test Coverage

**Core Foundation:**
- ✅ `test_client.py` - Client initialization and capability detection
- ✅ `test_exceptions.py` - Exception hierarchy
- ✅ `test_models.py` - Pydantic models validation
- ✅ `test_base.py` - Core HTTP transport layer
- ✅ `test_parser.py` - Response parsing logic
- ✅ `test_capabilities.py` - Device compatibility detection

**API Modules:**
- ✅ `test_playback.py` - Playback API
- ✅ `test_device.py` - Device information API
- ✅ `test_group.py` - Multiroom functionality (both unit and api)
- ✅ `test_eq.py` - Equalizer API
- ✅ `test_preset.py` - Preset API
- ✅ `test_bluetooth.py` - Bluetooth API
- ✅ `test_audio_settings.py` - Audio settings
- ✅ `test_lms.py` - LMS integration
- ✅ `test_misc.py` - Miscellaneous API
- ✅ `test_firmware.py` - Firmware API
- ✅ `test_timer.py` - Timer API
- ✅ `test_ssl.py` - SSL/TLS handling

**Supporting Modules:**
- ✅ `test_state.py` - State synchronization
- ✅ `test_discovery.py` - Device discovery
- ✅ `test_normalize.py` - Data normalization
- ✅ `test_group_helpers.py` - Group utilities
- ✅ `test_polling.py` - Polling strategies
- ✅ `test_backoff.py` - Backoff controllers
- ✅ `test_player.py` - Player functionality
- ✅ `test_role.py` - Role management

**UPnP:**
- ✅ `upnp/test_client.py` - UPnP client
- ✅ `upnp/test_eventer.py` - UPnP event handling

**Integration:**
- ✅ `test_real_device.py` - Integration tests with real devices

### ❌ Remaining Gaps

**Missing Tests:**
- ❌ `api/test_diagnostics.py` - Diagnostics API (reboot, time sync, raw commands)

### Next Steps

1. **Add diagnostics test** - Create `tests/unit/api/test_diagnostics.py` to cover the DiagnosticsAPI mixin
2. **Expand coverage** - Review existing tests and identify areas that need more comprehensive coverage
3. **Integration test expansion** - Consider adding more integration test scenarios as needed

## Conclusion

The pywiim test suite is comprehensive and covers the vast majority of functionality. The test infrastructure is well-organized with:

1. **Comprehensive unit tests** - Fast, isolated tests with mocks covering all major modules
2. **Integration tests** - Real device validation for end-to-end scenarios
3. **UPnP tests** - Coverage for UPnP client and event handling
4. **Good organization** - Clear structure with unit/api/upnp separation
5. **Maintainability** - Well-documented tests with descriptive names

**Remaining work:**
- Add diagnostics API test (`api/test_diagnostics.py`)
- Continue expanding coverage depth where needed
- Monitor and maintain test suite as the codebase evolves

The test suite provides a solid foundation for maintaining code quality and preventing regressions.

