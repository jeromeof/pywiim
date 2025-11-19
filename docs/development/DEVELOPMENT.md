# Development Guide

This document outlines coding standards, best practices, and development guidelines for pywiim.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- pip

### Initial Setup

**1. Clone the Repository**

```bash
git clone <repository-url>
cd pywiim
```

**2. Create Virtual Environment**

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

**3. Install Dependencies**

```bash
# Install the package in development mode with dev dependencies
pip install -e ".[dev]"

# Or install dependencies separately:
pip install -e .
pip install -r requirements-dev.txt  # if you create one
```

**4. Verify Installation**

```bash
# Check that pywiim is installed
python -c "import pywiim; print(pywiim.__version__)"

# Run tests
pytest tests/unit/ -v

# Check code quality
make lint
```

### Git Setup

**Initial Commit**

If this is a new repository:

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: pywiim library extraction"
```

**Git Configuration**

Recommended `.git/config` settings:

```ini
[user]
    name = Your Name
    email = your.email@example.com

[core]
    autocrlf = input  # Linux/macOS
    # autocrlf = true  # Windows

[init]
    defaultBranch = main
```

**Branching Strategy**

- `main` - Stable, production-ready code
- `develop` - Development branch
- `feature/*` - Feature branches
- `fix/*` - Bug fix branches

### Environment Variables

For integration testing:

```bash
export WIIM_TEST_DEVICE=192.168.1.100  # Device IP
export WIIM_TEST_PORT=80               # Optional port (default: 80)
export WIIM_TEST_HTTPS=false           # Use HTTPS (default: false)
```

### IDE Setup

**VS Code**

Recommended extensions:
- Python
- Pylance
- Ruff
- Black Formatter

Settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

**PyCharm**

1. Open project
2. Configure Python interpreter: `.venv/bin/python`
3. Enable type checking
4. Configure code style: Black, 120 char line length

### Troubleshooting

**Virtual Environment Issues**

If you have issues with the virtual environment:

```bash
# Remove and recreate
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Import Errors**

If you get import errors:

```bash
# Make sure you're in the virtual environment
which python  # Should show .venv/bin/python

# Reinstall in development mode
pip install -e .
```

**Pre-commit Hook Issues**

If pre-commit hooks fail:

```bash
# Update hooks
pre-commit autoupdate

# Skip hooks for a commit (not recommended)
git commit --no-verify
```

## Development Workflow

### Running Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=pywiim --cov-report=html

# Run integration tests (requires device)
export WIIM_TEST_DEVICE=192.168.1.100
pytest tests/integration/ -v
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type check
make typecheck

# Run all checks
make lint typecheck
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Code Style

### Formatting
- **Tool**: Black
- **Line Length**: 120 characters
- **Target Version**: Python 3.11+
- **Configuration**: See `pyproject.toml`

```bash
# Format code
make format
# or
black pywiim tests
```

### Linting
- **Tool**: Ruff
- **Rules**: E, W, F, I, B, C4, UP
- **Configuration**: See `pyproject.toml`

```bash
# Lint code
make lint
# or
ruff check pywiim tests
```

### Type Checking
- **Tool**: mypy
- **Mode**: Strict where possible
- **Configuration**: See `pyproject.toml`

```bash
# Type check
make typecheck
# or
mypy pywiim
```

### Import Sorting
- **Tool**: isort
- **Known First Party**: pywiim
- **Configuration**: See `pyproject.toml`

```bash
# Sort imports (included in make format)
isort pywiim tests
```

## File Organization

### File Size Limits
- **Soft Limit**: 400 lines of code (LOC)
- **Hard Limit**: 600 LOC
- **Exceeding Hard Limit**: Requires `# pragma: allow-long-file <issue>` and justification

### Module Organization
- **One Responsibility**: Each module should have a single, clear responsibility
- **Clear Boundaries**: No circular dependencies
- **Related Classes**: Can be in same file if closely related

### Directory Structure
```
pywiim/
├── __init__.py          # Public API exports
├── client.py            # Main client facade
├── exceptions.py        # Exception classes
├── models.py            # Pydantic models
├── capabilities.py      # Capability detection
├── cli/                 # Command-line tools
│   ├── diagnostics.py   # Diagnostic tool
│   ├── discovery_cli.py # Discovery tool
│   ├── monitor_cli.py   # Monitoring tool
│   └── ...              # Other CLI tools
├── api/                 # API modules
│   ├── base.py          # Base client
│   ├── parser.py        # Response parser
│   ├── constants.py     # API constants
│   └── ...              # Mixin modules
└── upnp/                # UPnP modules
    ├── client.py        # UPnP client
    ├── eventer.py       # Event manager
    └── state.py         # State management
```

## Naming Conventions

### Classes
- **Style**: PascalCase
- **Examples**: `WiiMClient`, `DeviceCapabilities`, `PlayerStatus`

### Functions
- **Style**: snake_case
- **Examples**: `get_player_status()`, `detect_capabilities()`, `parse_response()`

### Constants
- **Style**: UPPER_SNAKE_CASE
- **Examples**: `DEFAULT_PORT`, `MAX_RETRIES`, `API_ENDPOINT_STATUS`

### Private
- **Style**: Leading underscore
- **Examples**: `_request()`, `_capabilities`, `_parse_data()`

### Type Variables
- **Style**: Single uppercase letter
- **Examples**: `_T`, `_P`, `_R` (for generic types)

## Documentation

### Docstrings
- **Style**: Google style
- **Required**: All public APIs
- **Optional**: Private methods (but recommended for complex logic)

```python
def get_player_status(self) -> PlayerStatus:
    """Get current player status from device.
    
    Retrieves playback state, volume, position, and metadata from the device.
    Uses getPlayerStatusEx endpoint if available, falls back to getStatusEx.
    
    Returns:
        PlayerStatus model with current device state.
        
    Raises:
        WiiMRequestError: If the request fails after retries.
        WiiMResponseError: If the response is invalid.
        
    Example:
        >>> status = await client.get_player_status()
        >>> print(status.play_state)
        'play'
    """
    ...
```

### Inline Comments
- **Purpose**: Explain "why", not "what"
- **When**: Complex logic, non-obvious decisions, workarounds

```python
# Audio Pro MkII doesn't provide volume via HTTP, use UPnP instead
if capabilities.audio_pro_generation == "mkii":
    return await self._get_volume_upnp()
```

### Type Hints
- **Required**: All function signatures
- **Style**: Use `from __future__ import annotations` for forward references
- **Models**: Use Pydantic models for data structures

```python
from __future__ import annotations

from typing import Any

def parse_response(
    data: dict[str, Any],
    device_info: DeviceInfo | None = None,
) -> PlayerStatus:
    """Parse API response into PlayerStatus model."""
    ...
```

## Error Handling

### Exception Hierarchy
```python
WiiMError (base)
├── WiiMConnectionError
├── WiiMTimeoutError
├── WiiMRequestError
├── WiiMResponseError
└── WiiMInvalidDataError
```

### Error Context
All exceptions should include device context:

```python
raise WiiMRequestError(
    f"Failed to get player status: {error}",
    endpoint="/httpapi.asp?command=getPlayerStatusEx",
    attempts=3,
    last_error=error,
    device_info={
        "firmware_version": self.device_info.firmware,
        "device_model": self.device_info.model,
        "is_wiim_device": self.capabilities.is_wiim_device,
    },
    operation_context="get_player_status",
)
```

### Graceful Degradation
Never crash on device variations:

```python
# Check capability before calling endpoint
if not self.capabilities.supports_metadata:
    _LOGGER.debug(
        "Device %s does not support metadata endpoint, skipping",
        self.host,
    )
    return None

try:
    return await self._request(API_ENDPOINT_METADATA)
except WiiMRequestError as e:
    # Mark as unsupported and continue
    self.capabilities.supports_metadata = False
    _LOGGER.info(
        "Metadata endpoint not supported on %s, marking as unavailable",
        self.host,
    )
    return None
```

## Logging

### Logger Setup
```python
import logging

_LOGGER = logging.getLogger(__name__)
```

### Logging Standards
- **Context First**: Always include device/host in logs
- **Decision Logging**: Log why decisions were made
- **Error Context**: Include full context in error logs
- **Performance**: Log slow operations (>100ms)

### Log Message Format
```python
# Good: Includes device context
_LOGGER.debug(
    "API call: endpoint=%s, device=%s, firmware=%s, attempt=%d/%d",
    endpoint,
    self.host,
    self.device_info.firmware,
    attempt,
    max_retries,
)

# Good: Logs capability detection
_LOGGER.info(
    "Capability detected: device=%s, endpoint=%s, supported=%s, method=%s",
    self.host,
    "getMetaInfo",
    capabilities.supports_metadata,
    "firmware_check",
)

# Good: Logs state transitions
_LOGGER.info(
    "State transition: device=%s, old_state=%s, new_state=%s, trigger=%s",
    self.host,
    old_state,
    new_state,
    "upnp_event",
)
```

## Testing

### Test Structure
- Mirror source structure in `tests/unit/`
- Use descriptive test names
- Group related tests in classes
- Use fixtures for common setup

### Test Naming
```python
def test_get_player_status_returns_valid_model():
    """Test that get_player_status returns valid PlayerStatus model."""
    ...

def test_get_player_status_handles_timeout():
    """Test that get_player_status handles timeout errors gracefully."""
    ...

class TestCapabilityDetection:
    """Test capability detection for different device types."""
    
    def test_detects_wiim_device(self):
        """Test detection of WiiM devices."""
        ...
    
    def test_detects_audio_pro_mkii(self):
        """Test detection of Audio Pro MkII devices."""
        ...
```

### Mocking
- Mock all external dependencies (HTTP, UPnP)
- Use `unittest.mock` or `pytest-mock`
- Verify mock calls when appropriate

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_get_player_status():
    """Test getting player status."""
    client = WiiMClient("192.168.1.100")
    
    with patch.object(client, "_request") as mock_request:
        mock_request.return_value = {"play_status": "play", "vol": 50}
        
        status = await client.get_player_status()
        
        assert status.play_state == "play"
        assert status.volume == 50
        mock_request.assert_called_once()
```

## Async/Await

### Best Practices
- Use `async`/`await` for all I/O operations
- Use `asyncio.timeout` instead of deprecated `async_timeout`
- Use context managers for resource cleanup
- Avoid blocking operations in event loop

```python
# Good: Async with timeout
async def get_status(self) -> PlayerStatus:
    async with asyncio.timeout(5.0):
        response = await self.session.get(url)
        return await response.json()

# Bad: Blocking operation
async def get_status(self) -> PlayerStatus:
    time.sleep(1)  # Don't do this!
    ...
```

## Capability Detection

### Principles
- **Never Assume**: Always check capabilities before calling endpoints
- **Graceful Fallback**: If endpoint fails, mark as unsupported and continue
- **Firmware Detection**: Detect firmware version and apply known workarounds
- **Log Decisions**: Log how capabilities were determined

### Implementation
```python
# Check capability before API call
if not self.capabilities.supports_metadata:
    return None

# Probe endpoint if capability unknown
if self.capabilities.supports_metadata is None:
    try:
        await self._request(API_ENDPOINT_METADATA)
        self.capabilities.supports_metadata = True
    except WiiMRequestError:
        self.capabilities.supports_metadata = False
        _LOGGER.info("Metadata endpoint not supported")
        return None
```

## Common Patterns

### Retry Logic
```python
max_retries = 3
for attempt in range(1, max_retries + 1):
    try:
        return await self._request(endpoint)
    except WiiMTimeoutError:
        if attempt == max_retries:
            raise
        await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Capability-Aware Requests
```python
async def get_metadata(self) -> TrackMetadata | None:
    """Get track metadata if supported."""
    if not self.capabilities.supports_metadata:
        return None
    return await self._request(API_ENDPOINT_METADATA)
```

### State Management
```python
def apply_state_update(self, changes: dict[str, Any]) -> bool:
    """Apply state changes and return True if changed."""
    changed = False
    for key, value in changes.items():
        if getattr(self.state, key) != value:
            setattr(self.state, key, value)
            changed = True
    return changed
```

## Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/)
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)

