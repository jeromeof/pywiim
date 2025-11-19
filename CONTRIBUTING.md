# Contributing to pywiim

Thank you for your interest in contributing to pywiim! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites
- Python 3.11 or higher
- Git
- Virtual environment (recommended)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/mjcumming/pywiim.git
cd pywiim

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### 1. Plan Your Changes
- Review existing issues and discussions
- Document your changes in an issue or PR description
- Update architecture docs if needed

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 3. Make Your Changes
- Follow coding standards (see DEVELOPMENT.md)
- Write tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 4. Test Your Changes
```bash
# Format code
make format

# Lint code
make lint

# Type check
make typecheck

# Run tests
make test

# Check coverage
pytest --cov=pywiim --cov-report=html
```

### 5. Self-Review
Before submitting a PR, review your changes using the checklist below.

### 6. Submit Pull Request
- Push your branch to GitHub
- Create a pull request with a clear description
- Reference any related issues
- Wait for code review

## Code Review Checklist

Before submitting a PR, ensure:

- [ ] Code follows HA patterns (if applicable to integration)
- [ ] Handles device variations (capability checks, graceful fallbacks)
- [ ] Includes appropriate logging (context, decisions, errors)
- [ ] Has tests (unit tests for new code)
- [ ] Type hints complete (all functions typed)
- [ ] Documentation updated (docstrings, README if needed)
- [ ] No blocking operations (all I/O is async)
- [ ] Error handling comprehensive (specific exceptions, context)
- [ ] Code formatted (Black, Ruff checks pass)
- [ ] No device assumptions (capability checks, not hardcoded)

## Coding Standards

See DEVELOPMENT.md for detailed coding standards. Key points:

- **Formatting**: Black (120 char line length)
- **Linting**: Ruff (E, W, F, I, B, C4, UP rules)
- **Type Checking**: mypy (strict mode where possible)
- **File Size**: 400 LOC soft limit, 600 LOC hard limit
- **Documentation**: Google-style docstrings for all public APIs

## Testing Guidelines

### Unit Tests
- Mock all external dependencies (HTTP, UPnP)
- Test all API endpoints
- Test error handling paths
- Test model validation
- Test capability detection

### Test Structure
- Mirror source structure in `tests/unit/`
- Use descriptive test names
- Group related tests in classes
- Use fixtures for common setup

### Example Test
```python
import pytest
from unittest.mock import AsyncMock, patch

from pywiim.client import WiiMClient


@pytest.mark.asyncio
async def test_get_player_status():
    """Test getting player status from device."""
    client = WiiMClient("192.168.1.100")
    
    with patch.object(client, "_request") as mock_request:
        mock_request.return_value = {"play_status": "play", "vol": 50}
        
        status = await client.get_player_status()
        
        assert status.play_state == "play"
        assert status.volume == 50
```

## Documentation

### Code Documentation
- All public APIs must have docstrings (Google style)
- Complex logic should have inline comments explaining "why"
- Type hints required for all function signatures

### User Documentation
- Update README.md for user-facing changes
- Update API reference if public API changes
- Update examples if usage changes

### Architecture Documentation
- Update ARCHITECTURE.md for design changes
- Update DEVICE_REGISTRY.md for device-specific changes
- Document trade-offs and decisions

## Commit Messages

Follow conventional commit format:

```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Examples:
```
feat(api): add support for EQ presets

Add ability to set and retrieve EQ presets via API.

Closes #123
```

```
fix(upnp): handle connection errors gracefully

Previously, UPnP connection errors would crash the client.
Now they are caught and logged with device context.

Fixes #456
```

## Pull Request Process

1. **Create PR**: Push your branch and create a pull request
2. **Description**: Provide clear description of changes
3. **Tests**: Ensure all tests pass
4. **CI**: Wait for CI checks to pass
5. **Review**: Address review comments
6. **Merge**: Maintainer will merge when approved

## Reporting Issues

### Bug Reports
Include:
- Description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Device information (model, firmware)
- Logs (with sensitive data redacted)

### Feature Requests
Include:
- Description of the feature
- Use case / motivation
- Proposed implementation (if applicable)

## Device Testing

If you have access to WiiM or LinkPlay devices:

1. Test on your device model
2. Test on different firmware versions if possible
3. Document any device-specific quirks
4. Update DEVICE_REGISTRY.md with findings

## Questions?

- Open a discussion on GitHub
- Check existing issues and discussions
- Review documentation in docs/

Thank you for contributing to pywiim!

