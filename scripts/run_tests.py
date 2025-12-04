#!/usr/bin/env python3
"""
pywiim Unified Test Runner
==========================

A configurable test runner for pywiim that supports multiple test tiers,
device profiles, and provides verbose real-time output.

Usage:
    python scripts/run_tests.py --tier smoke                    # Run smoke tests on default device
    python scripts/run_tests.py --tier smoke --device 192.168.1.115
    python scripts/run_tests.py --tier playback --device 192.168.1.115
    python scripts/run_tests.py --tier controls                 # Shuffle/repeat tests
    python scripts/run_tests.py --tier features                 # EQ, outputs, presets
    python scripts/run_tests.py --tier groups                   # Multi-room tests
    python scripts/run_tests.py --all --device 192.168.1.115    # All tiers on device
    python scripts/run_tests.py --prerelease                    # Tiers 1-4 on default
    python scripts/run_tests.py --list-devices                  # Show configured devices

Test Tiers:
    1. smoke     - Basic connectivity, volume, mute (any device, any state)
    2. playback  - Play/pause/next/prev (requires media playing)
    3. controls  - Shuffle/repeat (requires album/playlist, not radio)
    4. features  - EQ, outputs, presets (device-specific capabilities)
    5. groups    - Multi-room grouping (requires 2+ devices)
    6. advanced  - Bluetooth output, edge cases (manual setup required)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import yaml

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Terminal Colors and Formatting
# =============================================================================


class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

    # Background
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


class Symbols:
    """Unicode symbols for output."""

    CHECK = "✓"
    CROSS = "✗"
    CIRCLE = "○"
    ARROW = "→"
    DOT = "•"
    STAR = "★"
    WARNING = "⚠"
    INFO = "ℹ"
    PLAY = "▶"
    PAUSE = "⏸"
    STOP = "⏹"
    SPEAKER = "🔊"
    MUTE = "🔇"
    LINK = "🔗"
    CLOCK = "⏱"
    GEAR = "⚙"
    ROCKET = "🚀"
    PACKAGE = "📦"


def colorize(text: str, *codes: str) -> str:
    """Apply color codes to text."""
    return f"{''.join(codes)}{text}{Colors.RESET}"


def log_header(title: str, char: str = "═") -> None:
    """Print a section header."""
    width = 70
    line = char * width
    print()
    print(colorize(line, Colors.BLUE, Colors.BOLD))
    print(colorize(f"  {title}", Colors.BLUE, Colors.BOLD))
    print(colorize(line, Colors.BLUE, Colors.BOLD))
    print()


def log_subheader(title: str) -> None:
    """Print a subsection header."""
    print()
    print(colorize(f"  {Symbols.ARROW} {title}", Colors.CYAN, Colors.BOLD))
    print(colorize("  " + "─" * 60, Colors.DIM))


def log_info(message: str, indent: int = 4) -> None:
    """Print an info message."""
    prefix = " " * indent
    print(f"{prefix}{colorize(Symbols.INFO, Colors.BLUE)} {message}")


def log_success(message: str, indent: int = 4) -> None:
    """Print a success message."""
    prefix = " " * indent
    print(f"{prefix}{colorize(Symbols.CHECK, Colors.GREEN)} {colorize(message, Colors.GREEN)}")


def log_warning(message: str, indent: int = 4) -> None:
    """Print a warning message."""
    prefix = " " * indent
    print(f"{prefix}{colorize(Symbols.WARNING, Colors.YELLOW)} {colorize(message, Colors.YELLOW)}")


def log_error(message: str, indent: int = 4) -> None:
    """Print an error message."""
    prefix = " " * indent
    print(f"{prefix}{colorize(Symbols.CROSS, Colors.RED)} {colorize(message, Colors.RED)}")


def log_skip(message: str, indent: int = 4) -> None:
    """Print a skip message."""
    prefix = " " * indent
    print(f"{prefix}{colorize(Symbols.CIRCLE, Colors.DIM)} {colorize(message, Colors.DIM)}")


def log_step(step: str, status: str = "", indent: int = 4) -> None:
    """Print a step with optional status."""
    prefix = " " * indent
    if status:
        print(f"{prefix}{colorize(Symbols.DOT, Colors.CYAN)} {step} {colorize(status, Colors.DIM)}")
    else:
        print(f"{prefix}{colorize(Symbols.DOT, Colors.CYAN)} {step}")


def log_progress(current: int, total: int, label: str) -> None:
    """Print a progress indicator."""
    pct = (current / total) * 100 if total > 0 else 0
    bar_width = 30
    filled = int(bar_width * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"    [{colorize(bar, Colors.CYAN)}] {current}/{total} {label} ({pct:.0f}%)")


def log_device_info(name: str, model: str, ip: str, firmware: str = "") -> None:
    """Print device information."""
    print(f"    {colorize('Device:', Colors.DIM)} {colorize(name, Colors.BOLD)}")
    print(f"    {colorize('Model:', Colors.DIM)}  {model}")
    print(f"    {colorize('IP:', Colors.DIM)}     {ip}")
    if firmware:
        print(f"    {colorize('FW:', Colors.DIM)}     {firmware}")


def log_test_result(test_name: str, passed: bool, duration: float, message: str = "") -> None:
    """Print a test result."""
    if passed:
        status = colorize(f"{Symbols.CHECK} PASS", Colors.GREEN)
    else:
        status = colorize(f"{Symbols.CROSS} FAIL", Colors.RED)

    duration_str = colorize(f"({duration:.2f}s)", Colors.DIM)
    print(f"    {status} {test_name} {duration_str}")
    if message and not passed:
        print(f"         {colorize(message, Colors.RED)}")


def prompt_user(message: str, options: str = "Enter/s") -> str:
    """Prompt user for input with colorful formatting."""
    print()
    print(colorize(f"  {Symbols.WARNING} {message}", Colors.YELLOW))
    print()
    response = input(colorize(f"  [{options}]: ", Colors.CYAN))
    return response.strip().lower()


# =============================================================================
# Configuration and Data Classes
# =============================================================================


class TestTier(Enum):
    """Test tier definitions."""

    SMOKE = 1
    PLAYBACK = 2
    CONTROLS = 3
    FEATURES = 4
    GROUPS = 5
    ADVANCED = 6


@dataclass
class DeviceConfig:
    """Configuration for a test device."""

    ip: str
    name: str
    model: str = "unknown"
    capabilities: list[str] = field(default_factory=list)
    group_role: str = ""
    notes: str = ""


@dataclass
class TestConfig:
    """Overall test configuration."""

    devices: list[DeviceConfig] = field(default_factory=list)
    default_device: str = ""
    default_group: dict[str, Any] = field(default_factory=dict)
    timeouts: dict[str, float] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    passed: bool
    duration: float
    message: str = ""
    skipped: bool = False


@dataclass
class TierResult:
    """Result of a test tier."""

    tier: TestTier
    tests: list[TestResult] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0

    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.passed and not t.skipped)

    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if not t.passed and not t.skipped)

    @property
    def skipped(self) -> int:
        return sum(1 for t in self.tests if t.skipped)

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


def load_config(config_path: Path | None = None) -> TestConfig:
    """Load test configuration from YAML file."""
    if config_path is None:
        config_path = PROJECT_ROOT / "scripts" / "test_devices.yaml"

    if not config_path.exists():
        log_warning(f"Config file not found: {config_path}")
        return TestConfig()

    with open(config_path) as f:
        data = yaml.safe_load(f)

    devices = []
    for d in data.get("devices", []):
        devices.append(
            DeviceConfig(
                ip=d.get("ip", ""),
                name=d.get("name", ""),
                model=d.get("model", "unknown"),
                capabilities=d.get("capabilities", []),
                group_role=d.get("group_role", ""),
                notes=d.get("notes", ""),
            )
        )

    return TestConfig(
        devices=devices,
        default_device=data.get("default_device", ""),
        default_group=data.get("default_group", {}),
        timeouts=data.get("timeouts", {}),
        settings=data.get("settings", {}),
    )


def get_device_config(config: TestConfig, ip: str) -> DeviceConfig | None:
    """Get device configuration by IP."""
    for device in config.devices:
        if device.ip == ip:
            return device
    return None


# =============================================================================
# Test Runner Core
# =============================================================================


class TestRunner:
    """Main test runner class."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.results: list[TierResult] = []
        self.player = None
        self.client = None
        # Group test attributes
        self.master = None
        self.slave = None
        self.master_client = None
        self.slave_client = None
        self.group = None

    async def connect_device(self, ip: str) -> bool:
        """Connect to a device and create player instance."""
        from pywiim import Player, WiiMClient
        from pywiim.exceptions import WiiMConnectionError, WiiMError

        log_step(f"Connecting to {ip}...")

        try:
            self.client = WiiMClient(host=ip, timeout=self.config.timeouts.get("connect", 5.0))
            self.player = Player(self.client)

            # Refresh to verify connection and get device info
            await self.player.refresh(full=True)

            device_info = await self.player.get_device_info()
            log_success(f"Connected to {device_info.name}")
            log_device_info(
                name=device_info.name,
                model=device_info.model,
                ip=ip,
                firmware=device_info.firmware,
            )
            return True

        except WiiMConnectionError as e:
            log_error(f"Connection failed: {e}")
            return False
        except WiiMError as e:
            log_error(f"Device error: {e}")
            return False
        except Exception as e:
            log_error(f"Unexpected error: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from device."""
        if self.client:
            try:
                await self.client.close()
            except Exception:
                pass
            self.client = None
            self.player = None

    async def run_test(
        self,
        name: str,
        test_func: Callable,
        *args,
        **kwargs,
    ) -> TestResult:
        """Run a single test with timing and error handling."""
        start = time.time()

        try:
            log_step(f"Running: {name}")
            await test_func(*args, **kwargs)
            duration = time.time() - start
            log_test_result(name, passed=True, duration=duration)
            return TestResult(name=name, passed=True, duration=duration)

        except AssertionError as e:
            duration = time.time() - start
            msg = str(e) or "Assertion failed"
            log_test_result(name, passed=False, duration=duration, message=msg)
            return TestResult(name=name, passed=False, duration=duration, message=msg)

        except SkipTest as e:
            duration = time.time() - start
            log_skip(f"{name}: {e}")
            return TestResult(name=name, passed=True, duration=duration, skipped=True, message=str(e))

        except Exception as e:
            duration = time.time() - start
            log_test_result(name, passed=False, duration=duration, message=str(e))
            return TestResult(name=name, passed=False, duration=duration, message=str(e))

    async def run_tier(self, tier: TestTier, device_ip: str) -> TierResult:
        """Run all tests for a tier."""
        result = TierResult(tier=tier)
        result.start_time = time.time()

        tier_name = tier.name.title()
        log_header(f"TIER {tier.value}: {tier_name} Tests", "═")

        # Connect to device
        if not await self.connect_device(device_ip):
            log_error("Cannot run tests - device connection failed")
            result.end_time = time.time()
            return result

        try:
            # Get tests for this tier
            tests = self._get_tier_tests(tier)

            if not tests:
                log_warning(f"No tests defined for tier {tier_name}")
                result.end_time = time.time()
                return result

            log_info(f"Running {len(tests)} tests...")
            print()

            # Run each test
            for test_name, test_func in tests:
                test_result = await self.run_test(test_name, test_func)
                result.tests.append(test_result)

                # Inter-test delay
                delay = self.config.settings.get("inter_test_delay", 0.5)
                if delay > 0:
                    await asyncio.sleep(delay)

        finally:
            await self.disconnect()

        result.end_time = time.time()
        return result

    async def run_group_tier(self, master_ip: str, slave_ip: str) -> TierResult:
        """Run group tests with master and slave devices."""
        from pywiim import Player, WiiMClient

        result = TierResult(tier=TestTier.GROUPS)
        result.start_time = time.time()

        log_header("TIER 5: Group Tests (Multi-Device)", "═")

        # Connect to master
        log_step(f"Connecting to master ({master_ip})...")
        try:
            self.master_client = WiiMClient(host=master_ip, timeout=self.config.timeouts.get("connect", 5.0))
            self.master = Player(self.master_client)
            await self.master.refresh(full=True)
            master_info = await self.master.get_device_info()
            log_success(f"Master: {master_info.name} ({master_info.model})")
        except Exception as e:
            log_error(f"Failed to connect to master: {e}")
            result.end_time = time.time()
            return result

        # Connect to slave
        log_step(f"Connecting to slave ({slave_ip})...")
        try:
            self.slave_client = WiiMClient(host=slave_ip, timeout=self.config.timeouts.get("connect", 5.0))
            self.slave = Player(self.slave_client)
            await self.slave.refresh(full=True)
            slave_info = await self.slave.get_device_info()
            log_success(f"Slave: {slave_info.name} ({slave_info.model})")
        except Exception as e:
            log_error(f"Failed to connect to slave: {e}")
            if self.master_client:
                await self.master_client.close()
            result.end_time = time.time()
            return result

        print()
        log_device_info(
            name=f"{master_info.name} (MASTER)",
            model=master_info.model,
            ip=master_ip,
            firmware=master_info.firmware,
        )
        print()
        log_device_info(
            name=f"{slave_info.name} (SLAVE)",
            model=slave_info.model,
            ip=slave_ip,
            firmware=slave_info.firmware,
        )

        try:
            # Get group tests
            tests = self._get_group_tests()

            log_info(f"Running {len(tests)} group tests...")
            print()

            # Run each test
            for test_name, test_func in tests:
                test_result = await self.run_test(test_name, test_func)
                result.tests.append(test_result)

                # Inter-test delay
                delay = self.config.settings.get("inter_test_delay", 0.5)
                if delay > 0:
                    await asyncio.sleep(delay)

        finally:
            # Cleanup: ensure devices are solo
            try:
                if self.master and not self.master.is_solo:
                    log_step("Cleanup: Ensuring master is solo...")
                    await self.master.leave_group()
                    await asyncio.sleep(1.0)
                if self.slave and not self.slave.is_solo:
                    log_step("Cleanup: Ensuring slave is solo...")
                    await self.slave.leave_group()
                    await asyncio.sleep(1.0)
            except Exception:
                pass

            # Close connections
            if self.master_client:
                await self.master_client.close()
            if self.slave_client:
                await self.slave_client.close()

            self.master = None
            self.slave = None
            self.master_client = None
            self.slave_client = None
            self.group = None

        result.end_time = time.time()
        return result

    def _get_tier_tests(self, tier: TestTier) -> list[tuple[str, Callable]]:
        """Get test functions for a tier."""
        if tier == TestTier.SMOKE:
            return self._get_smoke_tests()
        elif tier == TestTier.PLAYBACK:
            return self._get_playback_tests()
        elif tier == TestTier.CONTROLS:
            return self._get_controls_tests()
        elif tier == TestTier.FEATURES:
            return self._get_features_tests()
        elif tier == TestTier.GROUPS:
            return self._get_group_tests()
        elif tier == TestTier.ADVANCED:
            return self._get_advanced_tests()
        return []

    # =========================================================================
    # Tier 1: Smoke Tests
    # =========================================================================

    def _get_smoke_tests(self) -> list[tuple[str, Callable]]:
        """Get smoke test functions."""
        return [
            ("test_device_info", self._test_device_info),
            ("test_capabilities_detected", self._test_capabilities_detected),
            ("test_volume_read", self._test_volume_read),
            ("test_volume_set", self._test_volume_set),
            ("test_mute_read", self._test_mute_read),
            ("test_mute_toggle", self._test_mute_toggle),
            ("test_state_properties", self._test_state_properties),
            ("test_source_read", self._test_source_read),
        ]

    async def _test_device_info(self) -> None:
        """Test getting device info."""
        info = await self.player.get_device_info()
        assert info is not None, "Device info is None"
        assert info.name, "Device name is empty"
        assert info.model, "Device model is empty"
        log_info(f"Device: {info.name} ({info.model})", indent=8)

    async def _test_capabilities_detected(self) -> None:
        """Test that capabilities are detected."""
        caps = self.player.client.capabilities
        assert caps is not None, "Capabilities not detected"

        # Log detected capabilities
        cap_list = []
        if caps.get("supports_eq"):
            cap_list.append("EQ")
        if caps.get("supports_presets"):
            cap_list.append("Presets")
        if caps.get("supports_audio_output"):
            cap_list.append("Audio Output")
        if caps.get("supports_enhanced_grouping"):
            cap_list.append("Grouping")

        log_info(f"Capabilities: {', '.join(cap_list) or 'Basic'}", indent=8)

    async def _test_volume_read(self) -> None:
        """Test reading volume."""
        volume = await self.player.get_volume()
        assert volume is not None, "Volume is None"
        assert 0.0 <= volume <= 1.0, f"Volume {volume} out of range [0, 1]"
        log_info(f"Current volume: {volume:.0%}", indent=8)

    async def _test_volume_set(self) -> None:
        """Test setting volume (with restoration)."""
        initial_volume = await self.player.get_volume()

        # Set to safe test volume
        max_vol = self.config.settings.get("max_test_volume", 0.15)
        test_volume = min(0.10, max_vol)

        try:
            await self.player.set_volume(test_volume)
            await asyncio.sleep(0.5)

            new_volume = await self.player.get_volume()
            assert new_volume is not None, "Volume read failed after set"
            assert abs(new_volume - test_volume) < 0.05, f"Volume mismatch: {new_volume} != {test_volume}"
            log_info(f"Set volume to {test_volume:.0%}, read back {new_volume:.0%}", indent=8)

        finally:
            # Restore original volume
            if initial_volume is not None:
                await self.player.set_volume(initial_volume)
                await asyncio.sleep(0.3)

    async def _test_mute_read(self) -> None:
        """Test reading mute state."""
        muted = await self.player.get_muted()
        # Mute can be None on some devices
        log_info(f"Mute state: {muted}", indent=8)

    async def _test_mute_toggle(self) -> None:
        """Test toggling mute (with restoration)."""
        initial_mute = await self.player.get_muted()

        try:
            # Mute
            await self.player.set_mute(True)
            await asyncio.sleep(0.5)
            muted = await self.player.get_muted()
            if muted is not None:
                assert muted is True, "Device should be muted"

            # Unmute
            await self.player.set_mute(False)
            await asyncio.sleep(0.5)
            unmuted = await self.player.get_muted()
            if unmuted is not None:
                assert unmuted is False, "Device should be unmuted"

            log_info("Mute toggle working", indent=8)

        finally:
            # Restore original state
            if initial_mute is not None:
                await self.player.set_mute(initial_mute)
                await asyncio.sleep(0.3)

    async def _test_state_properties(self) -> None:
        """Test state properties return correct types."""
        await self.player.refresh()

        # Check boolean properties
        assert isinstance(self.player.is_playing, bool), "is_playing should be bool"
        assert isinstance(self.player.is_paused, bool), "is_paused should be bool"
        assert isinstance(self.player.is_idle, bool), "is_idle should be bool"

        # Check state property
        state = self.player.state
        assert state in ("playing", "paused", "idle", "buffering", "unknown"), f"Invalid state: {state}"

        log_info(f"State: {state} (is_playing={self.player.is_playing})", indent=8)

    async def _test_source_read(self) -> None:
        """Test reading current source."""
        await self.player.refresh()
        source = self.player.source
        # Source can be None if nothing playing
        log_info(f"Current source: {source or '(none)'}", indent=8)

    # =========================================================================
    # Tier 2: Playback Tests
    # =========================================================================

    def _get_playback_tests(self) -> list[tuple[str, Callable]]:
        """Get playback test functions."""
        return [
            ("test_playback_state_check", self._test_playback_state_check),
            ("test_pause_command", self._test_pause_command),
            ("test_resume_command", self._test_resume_command),
            ("test_next_track", self._test_next_track),
            ("test_previous_track", self._test_previous_track),
        ]

    async def _test_playback_state_check(self) -> None:
        """Check if device has active media."""
        await self.player.refresh()
        state = self.player.play_state

        if state in ("idle", "IDLE", "stop", "STOP", None):
            raise SkipTest(f"Device is {state or 'idle'} - no media playing. " "Start playback on the device first.")

        log_info(f"Playback state: {state}", indent=8)
        if self.player.media_title:
            log_info(f"Now playing: {self.player.media_title}", indent=8)

    async def _test_pause_command(self) -> None:
        """Test pause command."""
        await self.player.pause()
        await asyncio.sleep(1.0)
        await self.player.refresh()

        state = self.player.play_state
        if state not in ("pause", "paused", "PAUSE"):
            log_warning(f"State after pause: {state}", indent=8)
        else:
            log_info(f"Paused successfully", indent=8)

    async def _test_resume_command(self) -> None:
        """Test resume/play command."""
        await self.player.play()
        await asyncio.sleep(1.5)
        await self.player.refresh()

        state = self.player.play_state
        if state not in ("play", "playing", "PLAY", "buffering"):
            log_warning(f"State after resume: {state}", indent=8)
        else:
            log_info(f"Resumed successfully", indent=8)

    async def _test_next_track(self) -> None:
        """Test next track command."""
        initial_title = self.player.media_title

        await self.player.next_track()
        await asyncio.sleep(2.0)
        await self.player.refresh()

        new_title = self.player.media_title
        if initial_title and new_title and initial_title != new_title:
            log_info(f"Track changed: {new_title}", indent=8)
        else:
            log_info("Next track command sent", indent=8)

    async def _test_previous_track(self) -> None:
        """Test previous track command."""
        await self.player.previous_track()
        await asyncio.sleep(2.0)
        await self.player.refresh()
        log_info("Previous track command sent", indent=8)

    # =========================================================================
    # Tier 3: Controls Tests (Shuffle/Repeat)
    # =========================================================================

    def _get_controls_tests(self) -> list[tuple[str, Callable]]:
        """Get shuffle/repeat test functions."""
        return [
            ("test_shuffle_supported", self._test_shuffle_supported),
            ("test_repeat_supported", self._test_repeat_supported),
            ("test_shuffle_toggle", self._test_shuffle_toggle),
            ("test_repeat_modes", self._test_repeat_modes),
            ("test_shuffle_preserves_repeat", self._test_shuffle_preserves_repeat),
        ]

    async def _test_shuffle_supported(self) -> None:
        """Check if shuffle is supported for current source."""
        await self.player.refresh()

        if not self.player.shuffle_supported:
            raise SkipTest(
                f"Shuffle not supported for source: {self.player.source}. "
                "This is normal for line-in, Bluetooth input, or radio stations."
            )

        log_info(f"Shuffle supported for {self.player.source}", indent=8)

    async def _test_repeat_supported(self) -> None:
        """Check if repeat is supported for current source."""
        await self.player.refresh()

        if not self.player.repeat_supported:
            raise SkipTest(
                f"Repeat not supported for source: {self.player.source}. "
                "This is normal for line-in, Bluetooth input, or radio stations."
            )

        log_info(f"Repeat supported for {self.player.source}", indent=8)

    async def _test_shuffle_toggle(self) -> None:
        """Test toggling shuffle on and off."""
        if not self.player.shuffle_supported:
            raise SkipTest("Shuffle not supported")

        initial_shuffle = self.player.shuffle_state

        try:
            # Enable shuffle
            await self.player.set_shuffle(True)
            await asyncio.sleep(1.0)
            await self.player.refresh()

            assert self.player.shuffle_state is True, "Shuffle should be ON"
            log_info("Shuffle ON", indent=8)

            # Disable shuffle
            await self.player.set_shuffle(False)
            await asyncio.sleep(1.0)
            await self.player.refresh()

            assert self.player.shuffle_state is False, "Shuffle should be OFF"
            log_info("Shuffle OFF", indent=8)

        finally:
            # Restore
            if initial_shuffle is not None:
                await self.player.set_shuffle(initial_shuffle)
                await asyncio.sleep(0.5)

    async def _test_repeat_modes(self) -> None:
        """Test cycling through repeat modes."""
        if not self.player.repeat_supported:
            raise SkipTest("Repeat not supported")

        initial_repeat = self.player.repeat_mode

        try:
            for mode in ["all", "one", "off"]:
                await self.player.set_repeat(mode)
                await asyncio.sleep(1.0)
                await self.player.refresh()

                assert self.player.repeat_mode == mode, f"Repeat should be {mode}, got {self.player.repeat_mode}"
                log_info(f"Repeat: {mode}", indent=8)

        finally:
            # Restore
            if initial_repeat is not None:
                await self.player.set_repeat(initial_repeat)
                await asyncio.sleep(0.5)

    async def _test_shuffle_preserves_repeat(self) -> None:
        """Test that changing shuffle doesn't affect repeat."""
        if not self.player.shuffle_supported or not self.player.repeat_supported:
            raise SkipTest("Shuffle or repeat not supported")

        initial_shuffle = self.player.shuffle_state
        initial_repeat = self.player.repeat_mode

        try:
            # Set known repeat state
            await self.player.set_repeat("all")
            await asyncio.sleep(0.5)

            # Toggle shuffle
            await self.player.set_shuffle(True)
            await asyncio.sleep(1.0)
            await self.player.refresh()

            # Repeat should still be "all"
            assert self.player.repeat_mode == "all", f"Repeat changed to {self.player.repeat_mode}"
            log_info("Shuffle change preserved repeat state", indent=8)

        finally:
            # Restore
            if initial_shuffle is not None:
                await self.player.set_shuffle(initial_shuffle)
            if initial_repeat is not None:
                await self.player.set_repeat(initial_repeat)
            await asyncio.sleep(0.5)

    # =========================================================================
    # Tier 4: Features Tests (EQ, Outputs, Presets)
    # =========================================================================

    def _get_features_tests(self) -> list[tuple[str, Callable]]:
        """Get feature test functions."""
        return [
            ("test_eq_support_check", self._test_eq_support_check),
            ("test_eq_presets_list", self._test_eq_presets_list),
            ("test_eq_preset_switch", self._test_eq_preset_switch),
            ("test_audio_output_support", self._test_audio_output_support),
            ("test_presets_list", self._test_presets_list),
        ]

    async def _test_eq_support_check(self) -> None:
        """Check if EQ is supported."""
        await self.player.refresh(full=True)

        if not self.player.supports_eq:
            raise SkipTest("EQ not supported on this device")

        log_info("EQ supported", indent=8)

    async def _test_eq_presets_list(self) -> None:
        """Test listing EQ presets."""
        if not self.player.supports_eq:
            raise SkipTest("EQ not supported")

        presets = await self.player.audio.get_eq_presets()
        assert presets, "No EQ presets available"

        log_info(f"EQ presets: {', '.join(presets[:5])}{'...' if len(presets) > 5 else ''}", indent=8)

    async def _test_eq_preset_switch(self) -> None:
        """Test switching EQ presets."""
        if not self.player.supports_eq:
            raise SkipTest("EQ not supported")

        presets = await self.player.audio.get_eq_presets()
        if not presets or len(presets) < 2:
            raise SkipTest("Need at least 2 EQ presets to test switching")

        initial_preset = self.player.eq_preset

        try:
            # Switch to a different preset
            target = presets[0] if presets[0] != initial_preset else presets[1]
            await self.player.set_eq_preset(target)
            await asyncio.sleep(1.0)
            await self.player.refresh()

            log_info(f"Switched to EQ preset: {self.player.eq_preset}", indent=8)

        finally:
            # Restore
            if initial_preset and initial_preset in presets:
                await self.player.set_eq_preset(initial_preset)
                await asyncio.sleep(0.5)

    async def _test_audio_output_support(self) -> None:
        """Check audio output support."""
        await self.player.refresh(full=True)

        if not self.player.supports_audio_output:
            raise SkipTest("Audio output control not supported")

        modes = self.player.available_output_modes
        log_info(f"Output modes: {', '.join(modes) if modes else 'None'}", indent=8)

    async def _test_presets_list(self) -> None:
        """Test listing presets (favorites)."""
        if not self.player.supports_presets:
            raise SkipTest("Presets not supported")

        presets = self.player.presets
        count = len(presets) if presets else 0
        log_info(f"Presets configured: {count}", indent=8)

    # =========================================================================
    # Tier 5: Group Tests (Multi-Device)
    # =========================================================================

    def _get_group_tests(self) -> list[tuple[str, Callable]]:
        """Get group test functions."""
        return [
            ("test_group_ensure_solo", self._test_group_ensure_solo),
            ("test_group_create", self._test_group_create),
            ("test_group_slave_join", self._test_group_slave_join),
            ("test_group_roles_detected", self._test_group_roles_detected),
            ("test_group_metadata_propagation", self._test_group_metadata_propagation),
            ("test_group_volume_propagation", self._test_group_volume_propagation),
            ("test_group_mute_propagation", self._test_group_mute_propagation),
            ("test_group_slave_command_routing", self._test_group_slave_command_routing),
            ("test_group_disband", self._test_group_disband),
        ]

    async def _test_group_ensure_solo(self) -> None:
        """Ensure all devices are solo before testing."""
        if not self.master or not self.slave:
            raise SkipTest("Group tests require master and slave devices")

        # Ensure master is solo
        await self.master.refresh(full=True)
        if not self.master.is_solo:
            log_info(f"Master is {self.master.role}, leaving group...", indent=8)
            await self.master.leave_group()
            await asyncio.sleep(2.0)
            await self.master.refresh(full=True)

        # Ensure slave is solo
        await self.slave.refresh(full=True)
        if not self.slave.is_solo:
            log_info(f"Slave is {self.slave.role}, leaving group...", indent=8)
            await self.slave.leave_group()
            await asyncio.sleep(2.0)
            await self.slave.refresh(full=True)

        assert self.master.is_solo, f"Master should be solo, got {self.master.role}"
        assert self.slave.is_solo, f"Slave should be solo, got {self.slave.role}"
        log_info(f"Master ({self.master.host}) is solo", indent=8)
        log_info(f"Slave ({self.slave.host}) is solo", indent=8)

    async def _test_group_create(self) -> None:
        """Test creating a group on master (prepares for slaves to join)."""
        if not self.master:
            raise SkipTest("Group tests require master device")

        self.group = await self.master.create_group()
        await asyncio.sleep(1.0)
        await self.master.refresh(full=True)

        # Note: Master may still be "solo" until a slave actually joins
        # The create_group() call prepares the device to accept slaves
        log_info(f"Group created on {self.master.host} (role: {self.master.role})", indent=8)
        log_info("Master will become 'master' role when slave joins", indent=8)

    async def _test_group_slave_join(self) -> None:
        """Test slave joining the group."""
        if not self.master or not self.slave:
            raise SkipTest("Group tests require master and slave devices")

        await self.slave.join_group(self.master)
        await asyncio.sleep(3.0)  # Give time for join to complete
        await asyncio.gather(
            self.master.refresh(full=True),
            self.slave.refresh(full=True),
        )

        assert self.slave.is_slave, f"Slave should be slave, got {self.slave.role}"
        log_info(f"Slave ({self.slave.host}) joined group", indent=8)

    async def _test_group_roles_detected(self) -> None:
        """Test that roles are detected correctly."""
        if not self.master or not self.slave:
            raise SkipTest("Group tests require master and slave devices")

        await asyncio.gather(
            self.master.refresh(full=True),
            self.slave.refresh(full=True),
        )

        log_info(f"Master role: {self.master.role}", indent=8)
        log_info(f"Slave role: {self.slave.role}", indent=8)

        assert self.master.is_master, f"Master should be master, got {self.master.role}"
        assert self.slave.is_slave, f"Slave should be slave, got {self.slave.role}"

        # Check slave knows its master
        if self.slave.group and self.slave.group.master:
            log_info(f"Slave's master: {self.slave.group.master.host}", indent=8)

    async def _test_group_metadata_propagation(self) -> None:
        """Test that metadata propagates from master to slave."""
        if not self.master or not self.slave:
            raise SkipTest("Group tests require master and slave devices")

        # Refresh both to get current metadata
        await asyncio.gather(
            self.master.refresh(),
            self.slave.refresh(),
        )

        # Get master metadata
        master_title = self.master.media_title
        master_artist = self.master.media_artist
        master_album = self.master.media_album
        master_state = self.master.play_state

        log_info(f"Master: '{master_title}' by {master_artist}", indent=8)
        log_info(f"Master state: {master_state}", indent=8)

        # Get slave metadata
        slave_title = self.slave.media_title
        slave_artist = self.slave.media_artist
        slave_album = self.slave.media_album
        slave_state = self.slave.play_state

        log_info(f"Slave: '{slave_title}' by {slave_artist}", indent=8)
        log_info(f"Slave state: {slave_state}", indent=8)

        # Check propagation
        title_match = master_title == slave_title
        artist_match = master_artist == slave_artist
        state_match = master_state == slave_state

        if title_match:
            log_success("Title matches", indent=8)
        else:
            log_warning(f"Title mismatch: master='{master_title}' vs slave='{slave_title}'", indent=8)

        if artist_match:
            log_success("Artist matches", indent=8)
        else:
            log_warning(f"Artist mismatch: master='{master_artist}' vs slave='{slave_artist}'", indent=8)

        if state_match:
            log_success("Play state matches", indent=8)
        else:
            log_warning(f"State mismatch: master='{master_state}' vs slave='{slave_state}'", indent=8)

        # Also check virtual master (group) metadata if available
        if self.master.group:
            group_title = self.master.group.media_title if hasattr(self.master.group, "media_title") else None
            if group_title:
                log_info(f"Group (virtual master) title: '{group_title}'", indent=8)

    async def _test_group_volume_propagation(self) -> None:
        """Test volume propagation in group."""
        if not self.master or not self.slave:
            raise SkipTest("Group tests require master and slave devices")

        max_vol = self.config.settings.get("max_test_volume", 0.15)
        test_vol = min(0.05, max_vol)  # Use 5% or max test volume

        # Save initial volumes
        await asyncio.gather(
            self.master.refresh(),
            self.slave.refresh(),
        )
        initial_master_vol = self.master.volume_level
        initial_slave_vol = self.slave.volume_level

        try:
            # Set master volume
            await self.master.set_volume(test_vol)
            await asyncio.sleep(1.0)
            await self.master.refresh()

            master_vol = self.master.volume_level
            log_info(f"Set master volume to {test_vol:.0%}, got {master_vol:.0%}", indent=8)

            # Set slave volume
            await self.slave.set_volume(test_vol + 0.02)
            await asyncio.sleep(1.0)
            await self.slave.refresh()

            slave_vol = self.slave.volume_level
            log_info(f"Set slave volume to {test_vol + 0.02:.0%}, got {slave_vol:.0%}", indent=8)

            # Test group volume (if group object available)
            if self.master.group:
                group_vol = self.master.group.volume_level
                log_info(f"Group volume (max of all): {group_vol:.0%}", indent=8)

        finally:
            # Restore volumes
            if initial_master_vol is not None:
                await self.master.set_volume(initial_master_vol)
            if initial_slave_vol is not None:
                await self.slave.set_volume(initial_slave_vol)
            await asyncio.sleep(0.5)

    async def _test_group_mute_propagation(self) -> None:
        """Test mute propagation in group."""
        if not self.master or not self.slave:
            raise SkipTest("Group tests require master and slave devices")

        # Save initial mute states
        await asyncio.gather(
            self.master.refresh(),
            self.slave.refresh(),
        )
        initial_master_mute = self.master.is_muted
        initial_slave_mute = self.slave.is_muted

        try:
            # Test group mute_all if available
            if self.master.group:
                await self.master.group.mute_all(True)
                await asyncio.sleep(1.0)
                await asyncio.gather(
                    self.master.refresh(),
                    self.slave.refresh(),
                )

                log_info(f"After mute_all(True): master={self.master.is_muted}, slave={self.slave.is_muted}", indent=8)

                await self.master.group.mute_all(False)
                await asyncio.sleep(1.0)
                await asyncio.gather(
                    self.master.refresh(),
                    self.slave.refresh(),
                )

                log_info(f"After mute_all(False): master={self.master.is_muted}, slave={self.slave.is_muted}", indent=8)
            else:
                log_info("Group object not available, testing individual mute", indent=8)
                await self.master.set_mute(True)
                await asyncio.sleep(0.5)
                await self.master.set_mute(False)

        finally:
            # Restore mute states
            if initial_master_mute is not None:
                await self.master.set_mute(initial_master_mute)
            if initial_slave_mute is not None:
                await self.slave.set_mute(initial_slave_mute)
            await asyncio.sleep(0.5)

    async def _test_group_slave_command_routing(self) -> None:
        """Test that commands on slave route to master."""
        if not self.master or not self.slave:
            raise SkipTest("Group tests require master and slave devices")

        # Get initial master state
        await self.master.refresh()
        initial_state = self.master.play_state

        # Try pause from slave
        log_info("Sending pause command from slave...", indent=8)
        try:
            await self.slave.pause()
            await asyncio.sleep(2.0)
            await self.master.refresh()

            master_state = self.master.play_state
            log_info(f"Master state after slave.pause(): {master_state}", indent=8)

            # Try play from slave
            log_info("Sending play command from slave...", indent=8)
            await self.slave.play()
            await asyncio.sleep(2.0)
            await self.master.refresh()

            master_state = self.master.play_state
            log_info(f"Master state after slave.play(): {master_state}", indent=8)

        except Exception as e:
            log_warning(f"Command routing test: {e}", indent=8)

    async def _test_group_disband(self) -> None:
        """Test disbanding the group."""
        if not self.master:
            raise SkipTest("Group tests require master device")

        # Disband group
        if self.master.group:
            await self.master.group.disband()
        else:
            await self.master.leave_group()

        await asyncio.sleep(2.0)
        await asyncio.gather(
            self.master.refresh(full=True),
            self.slave.refresh(full=True) if self.slave else asyncio.sleep(0),
        )

        assert self.master.is_solo, f"Master should be solo after disband, got {self.master.role}"
        log_info(f"Master ({self.master.host}) is now solo", indent=8)

        if self.slave:
            assert self.slave.is_solo, f"Slave should be solo after disband, got {self.slave.role}"
            log_info(f"Slave ({self.slave.host}) is now solo", indent=8)

    # =========================================================================
    # Tier 6: Advanced Tests
    # =========================================================================

    def _get_advanced_tests(self) -> list[tuple[str, Callable]]:
        """Get advanced test functions."""
        return [
            ("test_advanced_not_implemented", self._test_advanced_not_implemented),
        ]

    async def _test_advanced_not_implemented(self) -> None:
        """Placeholder for advanced tests."""
        raise SkipTest("Advanced tests require manual setup - use interactive mode")

    # =========================================================================
    # Results
    # =========================================================================

    def print_summary(self) -> None:
        """Print test summary."""
        log_header("TEST SUMMARY", "═")

        total_passed = 0
        total_failed = 0
        total_skipped = 0
        total_duration = 0.0

        for tier_result in self.results:
            tier_name = tier_result.tier.name.title()

            if tier_result.total == 0:
                print(f"    TIER {tier_result.tier.value}: {tier_name}")
                print(colorize("        (no tests run)", Colors.DIM))
            else:
                status = (
                    colorize(f"{Symbols.CHECK} PASSED", Colors.GREEN)
                    if tier_result.failed == 0
                    else colorize(f"{Symbols.CROSS} FAILED", Colors.RED)
                )
                print(f"    TIER {tier_result.tier.value}: {tier_name}  {status}")
                print(
                    f"        Passed: {colorize(str(tier_result.passed), Colors.GREEN)}  "
                    f"Failed: {colorize(str(tier_result.failed), Colors.RED)}  "
                    f"Skipped: {colorize(str(tier_result.skipped), Colors.DIM)}  "
                    f"Time: {tier_result.duration:.1f}s"
                )

            total_passed += tier_result.passed
            total_failed += tier_result.failed
            total_skipped += tier_result.skipped
            total_duration += tier_result.duration
            print()

        print(colorize("  " + "─" * 60, Colors.DIM))
        print()

        if total_failed == 0:
            print(f"    {colorize(f'{Symbols.CHECK} ALL TESTS PASSED', Colors.GREEN, Colors.BOLD)}")
        else:
            print(f"    {colorize(f'{Symbols.CROSS} SOME TESTS FAILED', Colors.RED, Colors.BOLD)}")

        print()
        print(
            f"    Total: {total_passed + total_failed + total_skipped} tests  "
            f"({colorize(f'{total_passed} passed', Colors.GREEN)}, "
            f"{colorize(f'{total_failed} failed', Colors.RED)}, "
            f"{colorize(f'{total_skipped} skipped', Colors.DIM)})"
        )
        print(f"    Duration: {total_duration:.1f} seconds")
        print()


class SkipTest(Exception):
    """Exception to skip a test."""

    pass


# =============================================================================
# Main Entry Point
# =============================================================================


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="pywiim Unified Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--tier",
        choices=["smoke", "playback", "controls", "features", "groups", "advanced"],
        help="Test tier to run",
    )
    parser.add_argument(
        "--device",
        "-d",
        help="Device IP address to test",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Run all applicable tiers on the device",
    )
    parser.add_argument(
        "--prerelease",
        action="store_true",
        help="Run pre-release test suite (tiers 1-4)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List configured test devices",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to test configuration file",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts (assume device is ready)",
    )
    parser.add_argument(
        "--master",
        help="Master device IP for group tests",
    )
    parser.add_argument(
        "--slave",
        help="Slave device IP for group tests",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # List devices mode
    if args.list_devices:
        log_header("Configured Test Devices", "═")
        for device in config.devices:
            caps = ", ".join(device.capabilities) if device.capabilities else "auto-detect"
            print(f"    {colorize(device.ip, Colors.CYAN)}  {device.name}")
            print(f"        Model: {device.model}  Capabilities: {caps}")
            if device.notes:
                print(f"        {colorize(device.notes, Colors.DIM)}")
            print()

        if config.default_device:
            print(f"    Default device: {colorize(config.default_device, Colors.GREEN)}")
        return 0

    # Determine device
    device_ip = args.device or config.default_device
    if not device_ip:
        log_error("No device specified. Use --device or set default_device in config.")
        return 1

    # Determine tiers to run
    tiers: list[TestTier] = []

    if args.tier:
        tier_map = {
            "smoke": TestTier.SMOKE,
            "playback": TestTier.PLAYBACK,
            "controls": TestTier.CONTROLS,
            "features": TestTier.FEATURES,
            "groups": TestTier.GROUPS,
            "advanced": TestTier.ADVANCED,
        }
        tiers = [tier_map[args.tier]]
    elif args.prerelease:
        tiers = [TestTier.SMOKE, TestTier.PLAYBACK, TestTier.CONTROLS, TestTier.FEATURES]
    elif args.all:
        tiers = [TestTier.SMOKE, TestTier.PLAYBACK, TestTier.CONTROLS, TestTier.FEATURES]
    else:
        # Default to smoke tests
        tiers = [TestTier.SMOKE]

    # Print header
    log_header(f"{Symbols.ROCKET} pywiim Test Runner", "═")
    print(f"    Date:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"    Device:  {device_ip}")
    print(f"    Tiers:   {', '.join(t.name.title() for t in tiers)}")

    # Show group config if running group tests
    if TestTier.GROUPS in tiers:
        master_ip = args.master or config.default_group.get("master")
        slave_ips = config.default_group.get("slaves", [])
        slave_ip = args.slave or (slave_ips[0] if slave_ips else None)
        print(f"    Master:  {master_ip or '(not configured)'}")
        print(f"    Slave:   {slave_ip or '(not configured)'}")
    print()

    # Check for prerequisites
    if TestTier.PLAYBACK in tiers or TestTier.CONTROLS in tiers:
        print()
        log_warning("PREREQUISITES", indent=4)
        print()
        if TestTier.PLAYBACK in tiers:
            print(f"    {Symbols.DOT} Tier 2 (Playback): Device must have media playing")
        if TestTier.CONTROLS in tiers:
            print(f"    {Symbols.DOT} Tier 3 (Controls): Must be playing an album/playlist (NOT radio)")
            print(f"      {colorize('Radio stations and artist mixes do not support shuffle/repeat!', Colors.DIM)}")
        print()

        if args.yes:
            log_info("Skipping confirmation (--yes flag)", indent=4)
        else:
            try:
                response = prompt_user("Press Enter when device is ready, or 's' to skip these tiers", "Enter/s")
                if response == "s":
                    tiers = [t for t in tiers if t not in (TestTier.PLAYBACK, TestTier.CONTROLS)]
                    if not tiers:
                        log_warning("All tiers skipped. Nothing to run.")
                        return 0
            except EOFError:
                # Non-interactive mode, proceed with tests
                log_info("Non-interactive mode - proceeding with tests", indent=4)

    # Run tests
    runner = TestRunner(config)

    for tier in tiers:
        if tier == TestTier.GROUPS:
            # Group tests need master and slave
            master_ip = args.master or config.default_group.get("master")
            slave_ips = config.default_group.get("slaves", [])
            slave_ip = args.slave or (slave_ips[0] if slave_ips else None)

            if not master_ip or not slave_ip:
                log_error("Group tests require --master and --slave, or default_group in config")
                log_info("Example: python run_tests.py --tier groups --master 192.168.1.115 --slave 192.168.1.116")
                continue

            result = await runner.run_group_tier(master_ip, slave_ip)
            runner.results.append(result)
        else:
            result = await runner.run_tier(tier, device_ip)
            runner.results.append(result)

    # Print summary
    runner.print_summary()

    # Return exit code
    total_failed = sum(r.failed for r in runner.results)
    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print()
        log_warning("Test interrupted by user")
        sys.exit(130)
