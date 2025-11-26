# Utility Scripts

This directory contains utility scripts for development and testing.

## Scripts

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

**Note**: This is a development/testing script, not part of the package distribution.

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
- Perfect for manual verification and exploration

**Note**: Press Ctrl+C or enter 'q' to quit.

### Shuffle/Repeat Testing Scripts

Two scripts for testing shuffle/repeat controls across different sources and content types.

#### `test-shuffle-repeat-once.py` - Quick Testing

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
- Perfect for quick verification

#### `test-shuffle-repeat-by-source.py` - Comprehensive Testing

**Usage**:
```bash
python scripts/test-shuffle-repeat-by-source.py 192.168.1.100
```

**Features**:
- Interactive testing across multiple sources and content types
- Tests shuffle and repeat controls systematically
- Compares library predictions vs actual behavior
- Records detailed results including loop_mode values
- Identifies prediction mismatches (where library is wrong)
- Saves comprehensive JSON results for analysis
- Helps understand content-type-specific behavior (e.g., Spotify album vs radio)

**Why This Matters**:
Shuffle and repeat support has been problematic. Content type matters! Spotify albums may support 
controls while Spotify radio may not. These scripts help systematically test and document what 
actually works.

**Workflow**:
1. Start the script
2. Use WiiM app to play content from a source
3. Return to script and press `[t]` to test current source
4. Describe what's playing: "Spotify Album - Rumors by Fleetwood Mac"
5. Script tests shuffle/repeat and records results
6. Repeat for different sources and content types
7. Press `[q]` to save results and see summary

**Results**: Saved to `tests/shuffle-repeat-results/` with detailed JSON data.

**Documentation**: See `tests/shuffle-repeat-results/README.md` for full testing guide.

### `release.sh`

Automated release script that runs linting, formatting, version bumping, and git push in one command.

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
7. Pushes to remote repository

**Note**: The script will exit early if any step fails (linting errors, test failures, etc.). All checks must pass before version bump and push.

