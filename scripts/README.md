# Utility Scripts

This directory contains utility scripts for development, release management, and debugging.

## Testing

**All tests (unit and integration) are now managed via pytest.** See `tests/README.md` for the testing guide.

Quick reference:
```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests by tier
pytest tests/integration/ -m smoke -v      # Basic connectivity
pytest tests/integration/ -m playback -v   # Play/pause/next/prev
pytest tests/integration/ -m controls -v   # Shuffle/repeat
pytest tests/integration/ -m features -v   # EQ, presets, outputs
pytest tests/integration/ -m groups -v     # Multi-room

# Run all pre-release tests
pytest tests/integration/ -m prerelease -v
```

Configure test devices in `tests/devices.yaml`.

## Release Scripts

### `release.sh`

Automated release script that runs all checks, bumps version, and pushes to git.

```bash
./scripts/release.sh patch   # Bump patch version (default)
./scripts/release.sh minor   # Bump minor version
./scripts/release.sh major   # Bump major version
```

**What it does:**
1. Formats code with `black` and `isort`
2. Runs linting with `ruff`
3. Runs type checking with `mypy`
4. Runs tests with `pytest`
5. Bumps version in `pyproject.toml` and `pywiim/__init__.py`
6. Commits changes with version bump message
7. Creates git tag and pushes

### `prerelease-check.sh`

Pre-release integration test runner.

```bash
./scripts/prerelease-check.sh 192.168.1.115
```

### `publish.sh`

Manual PyPI publishing (rarely needed - GitHub Actions handles this automatically).

### `create_releases_for_tags.sh`

Creates GitHub releases for existing git tags.

### `generate_changelog.py`

Generates changelog entries from git commits.

## Authentication Setup

### `gh-auth-token.sh`

Sets up GitHub CLI authentication.

### `setup_pypi_auth.sh`

Configures PyPI authentication for manual publishing.

## Git Hooks

### `pre-push.sh`

Git pre-push hook script. Runs automatically when pushing (if configured).

## Subdirectories

### `manual/`

Interactive test scripts that require human interaction:
- `interactive-playback-test.py` - Menu-driven playback control testing
- `test-shuffle-repeat-by-source.py` - Source-specific shuffle/repeat testing

These tests cannot be automated and require real-time observation.

### `test_mcp_server.py`

End-to-end test of the MCP server. Spawns `wiim-mcp`, sends tool calls, and prints results.

```bash
python scripts/test_mcp_server.py
```

Without a real device, runs initialize, tools/list, and wiim_discover (using configured devices). With `WIIM_TEST_DEVICE` set, also tests wiim_status, wiim_sources, wiim_volume:

```bash
WIIM_TEST_DEVICE=192.168.1.115 python scripts/test_mcp_server.py
```

### `debug/`

Debugging utilities for troubleshooting:
- `test_http_volume.py` - Debug HTTP volume responses
- `test_upnp_volume.py` - Debug UPnP volume implementation
- `test_queue.py` - Debug queue handling

## Recommended Pre-Release Workflow

```bash
# 1. Configure your test device in tests/devices.yaml

# 2. Run smoke tests (always works)
pytest tests/integration/ -m smoke -v

# 3. Start media on device, then run playback tests
pytest tests/integration/ -m playback -v

# 4. Play an album (not radio), run controls tests
pytest tests/integration/ -m controls -v

# 5. Run feature tests
pytest tests/integration/ -m features -v

# 6. Check test reports
cat tests/test_reports.json

# 7. Do the release
./scripts/release.sh patch
```

## Configuration

Test device configuration is in `tests/devices.yaml`:
```yaml
default_device: 192.168.1.115
group:
  master: 192.168.1.115
  slaves:
    - 192.168.1.116
settings:
  max_test_volume: 0.15
```
