# Utility Scripts

This directory contains utility scripts for development, testing, and release management.

## Release & Publishing Scripts

### `release.sh`

Automated release script that runs all checks, bumps version, and pushes to git.

**Usage**:
```bash
# Bump patch version (default)
./scripts/release.sh

# Or explicitly specify bump type
./scripts/release.sh patch
./scripts/release.sh minor
./scripts/release.sh major
```

**What it does**:
1. Formats code with `black` and `isort`
2. Runs linting with `ruff`
3. Runs type checking with `mypy`
4. Runs tests with `pytest`
5. Bumps version in both `pyproject.toml` and `pywiim/__init__.py`
6. Commits changes with a version bump message
7. Creates a git tag
8. Pushes to remote repository

**Note**: The script will exit early if any step fails. All checks must pass before version bump and push.

### `publish.sh`

Manual PyPI publishing script (rarely needed - GitHub Actions handles this automatically).

**Usage**:
```bash
./scripts/publish.sh
```

**Note**: Normally you don't need this. After pushing a tag, GitHub Actions automatically publishes to PyPI.

### `create_releases_for_tags.sh`

Creates GitHub releases for existing git tags that don't have releases yet.

**Usage**:
```bash
./scripts/create_releases_for_tags.sh
```

### `generate_changelog.py`

Generates changelog entries from git commits.

**Usage**:
```bash
python scripts/generate_changelog.py
```

## Authentication Setup Scripts

### `gh-auth-token.sh`

Sets up GitHub CLI authentication.

**Usage**:
```bash
./scripts/gh-auth-token.sh
```

### `setup_pypi_auth.sh`

Configures PyPI authentication for manual publishing.

**Usage**:
```bash
./scripts/setup_pypi_auth.sh
```

## Git Hooks

### `pre-push.sh`

Git pre-push hook script.

**Usage**: Automatically runs when pushing (if configured as a git hook).

## Device Testing Scripts

### `test_my_devices.py`

Quick test script for testing pywiim against real devices.

**Usage**:
```bash
# Test a single device
python scripts/test_my_devices.py 192.168.1.100

# Test multiple devices
python scripts/test_my_devices.py 192.168.1.100 192.168.1.101
```

**Features**:
- Connects to devices
- Gets device information
- Detects capabilities
- Tests basic features
- Shows summary

### `test-playback-controls.py`

Automated test script for verifying play/pause, shuffle, and repeat controls on real devices.

**Usage**:
```bash
python scripts/test-playback-controls.py 192.168.1.100
```

**Features**:
- Tests play/pause commands
- Tests shuffle on/off with state preservation
- Tests repeat modes (off/one/all) with state preservation
- Restores initial device state after testing
- Provides detailed test results summary

**Requirements**: Device should have media in queue for best results.

### `interactive-playback-test.py`

Interactive manual testing tool for playback controls.

**Usage**:
```bash
python scripts/interactive-playback-test.py 192.168.1.100
```

**Features**:
- Interactive menu-driven interface
- Manual control of play/pause/stop/resume
- Next/previous track controls
- Shuffle and repeat mode controls
- Real-time status display

**Note**: Press Ctrl+C or enter 'q' to quit.

## Shuffle/Repeat Testing Scripts

### `test-shuffle-repeat-once.py`

Quick non-interactive test of shuffle/repeat controls for the current source.

**Usage**:
```bash
python scripts/test-shuffle-repeat-once.py <device_ip> "<content_description>"

# Example:
python scripts/test-shuffle-repeat-once.py 192.168.1.115 "Spotify Album - Rumors"
```

**Features**:
- Quick non-interactive test of current source
- Tests shuffle and repeat controls
- Shows library predictions vs actual behavior
- Restores initial state after testing

### `test-shuffle-repeat-by-source.py`

Comprehensive interactive testing across multiple sources and content types.

**Usage**:
```bash
python scripts/test-shuffle-repeat-by-source.py 192.168.1.100
```

**Features**:
- Interactive testing across multiple sources and content types
- Tests shuffle and repeat controls systematically
- Compares library predictions vs actual behavior
- Records detailed results including loop_mode values
- Saves comprehensive JSON results for analysis

**Workflow**:
1. Start the script
2. Use WiiM app to play content from a source
3. Return to script and press `[t]` to test current source
4. Describe what's playing: "Spotify Album - Rumors by Fleetwood Mac"
5. Script tests shuffle/repeat and records results
6. Repeat for different sources and content types
7. Press `[q]` to save results and see summary

**Results**: Saved to `tests/shuffle-repeat-results/` with detailed JSON data.
