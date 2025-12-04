# Utility Scripts

This directory contains utility scripts for development, testing, and release management.

## Test Runner (Primary Testing Tool)

### `run_tests.py`

**The unified test runner for pywiim.** Supports tiered testing with colorful output.

```bash
# List configured devices
python scripts/run_tests.py --list-devices

# Run smoke tests (Tier 1) - always works, no setup needed
python scripts/run_tests.py --tier smoke --device 192.168.1.115

# Run playback tests (Tier 2) - needs media playing
python scripts/run_tests.py --tier playback --device 192.168.1.115 --yes

# Run controls tests (Tier 3) - needs album/playlist (NOT radio)
python scripts/run_tests.py --tier controls --device 192.168.1.115 --yes

# Run features tests (Tier 4) - EQ, outputs, presets
python scripts/run_tests.py --tier features --device 192.168.1.115 --yes

# Run pre-release suite (Tiers 1-4)
python scripts/run_tests.py --prerelease --device 192.168.1.115 --yes

# Run all tiers
python scripts/run_tests.py --all --device 192.168.1.115 --yes
```

**Test Tiers:**
| Tier | Name | Tests | Prerequisites |
|------|------|-------|---------------|
| 1 | Smoke | 8 | None - always works |
| 2 | Playback | 5 | Media playing on device |
| 3 | Controls | 5 | Album/playlist (NOT radio/station) |
| 4 | Features | 5 | Device-specific (EQ, outputs) |
| 5 | Groups | 8 | Multiple devices (--master, --slave) |
| 6 | Advanced | TBD | Manual setup (BT, etc.) |

**Group Tests (Tier 5):**
```bash
# Run group tests with master and slave
python scripts/run_tests.py --tier groups --master 192.168.1.115 --slave 192.168.1.116 --yes
```

Group tests verify:
- Ensure devices start as solo
- Create group on master
- Slave joins group
- Role detection (master/slave)
- Volume propagation
- Mute propagation (mute_all)
- Command routing (slave commands → master)
- Group disband (both return to solo)

**Options:**
- `--device IP` - Specify device IP (default from config)
- `--yes` / `-y` - Skip confirmation prompts
- `--list-devices` - Show configured test devices
- `--config PATH` - Custom config file

### `test_devices.yaml`

Device configuration file for the test runner. Edit this to configure your test devices:

```yaml
devices:
  - ip: 192.168.1.115
    name: "Living Room Pro"
    model: wiim_pro
    capabilities:
      - eq
      - presets
    notes: "Primary test device"

default_device: 192.168.1.115
```

## Release & Publishing Scripts

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

Pre-release integration test runner. Runs pytest integration tests against a real device.

```bash
./scripts/prerelease-check.sh 192.168.1.115
```

### `publish.sh`

Manual PyPI publishing (rarely needed - GitHub Actions handles this automatically).

### `create_releases_for_tags.sh`

Creates GitHub releases for existing git tags.

### `generate_changelog.py`

Generates changelog entries from git commits.

## Authentication Setup Scripts

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
- `test-shuffle-repeat-by-source.py` - Interactive source testing

### `groups/`

Multi-device group testing scripts (for Tier 5 implementation):
- `test_group_join_unjoin.py` - Group join/leave testing
- `test-group-real-devices.py` - Comprehensive group testing
- `test-master-slave-basic.py` - Basic master/slave testing

### `debug/`

Debugging utilities:
- `test_http_volume.py` - Debug HTTP volume responses
- `test_upnp_volume.py` - Debug UPnP volume implementation
- `test_queue.py` - Debug queue handling

## Recommended Pre-Release Workflow

```bash
# 1. Run smoke tests on primary device
python scripts/run_tests.py --tier smoke --device 192.168.1.115

# 2. Start media playing on device, then run playback tests
python scripts/run_tests.py --tier playback --device 192.168.1.115 --yes

# 3. Ensure album/playlist is playing (NOT radio), run controls tests
python scripts/run_tests.py --tier controls --device 192.168.1.115 --yes

# 4. Run feature tests
python scripts/run_tests.py --tier features --device 192.168.1.115 --yes

# 5. Or run all at once with --prerelease
python scripts/run_tests.py --prerelease --device 192.168.1.115 --yes

# 6. Do the release
./scripts/release.sh patch
```
