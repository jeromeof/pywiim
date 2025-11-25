#!/usr/bin/env python3
"""Comprehensive shuffle/repeat testing across different sources and content types.

This script systematically tests shuffle and repeat controls across different
sources and content types to identify what works and what doesn't. This helps
finally nail down the thorny shuffle/repeat support issues.

Key insight: Content type matters! For example:
- Spotify album (on-demand) may support controls
- Spotify radio (algorithmic) may NOT support controls

Usage:
    python scripts/test-shuffle-repeat-by-source.py <device_ip>

Example:
    python scripts/test-shuffle-repeat-by-source.py 192.168.1.100

The script will:
1. Check what sources are available on the device
2. For each source, test shuffle and repeat controls
3. Record detailed results including:
   - Whether controls are supported (library prediction)
   - Whether controls actually work (real testing)
   - Loop mode values before/after commands
   - Any errors encountered
4. Generate a comprehensive report

You can pause testing at any time and manually:
- Switch sources on the device
- Start different content types
- Resume testing when ready
"""

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pywiim import WiiMClient
from pywiim.player import Player


@dataclass
class SourceTest:
    """Results from testing a single source."""

    source_name: str
    content_description: str  # E.g., "Spotify Album", "Spotify Radio", "USB Playlist"
    timestamp: str

    # Pre-test state
    initial_source: str | None
    initial_play_state: str | None
    initial_shuffle: bool | None
    initial_repeat: str | None
    initial_loop_mode: int | None

    # Support prediction (from library)
    shuffle_supported_predicted: bool
    repeat_supported_predicted: bool

    # Shuffle test results
    shuffle_test_attempted: bool
    shuffle_enable_success: bool | None
    shuffle_disable_success: bool | None
    shuffle_state_after_enable: bool | None
    shuffle_state_after_disable: bool | None
    shuffle_loop_mode_after_enable: int | None
    shuffle_loop_mode_after_disable: int | None
    shuffle_error: str | None

    # Repeat test results
    repeat_test_attempted: bool
    repeat_all_success: bool | None
    repeat_one_success: bool | None
    repeat_off_success: bool | None
    repeat_mode_after_all: str | None
    repeat_mode_after_one: str | None
    repeat_mode_after_off: str | None
    repeat_loop_mode_after_all: int | None
    repeat_loop_mode_after_one: int | None
    repeat_loop_mode_after_off: int | None
    repeat_error: str | None

    # State preservation tests
    repeat_preserved_during_shuffle: bool | None
    shuffle_preserved_during_repeat: bool | None

    # Final assessment
    shuffle_actually_works: bool | None
    repeat_actually_works: bool | None
    notes: str


@dataclass
class TestSession:
    """Complete test session results."""

    device_name: str
    device_model: str
    device_firmware: str
    device_ip: str
    test_start: str
    test_end: str | None
    source_tests: list[SourceTest]
    errors: list[str]
    summary: dict[str, Any]


class ShuffleRepeatTester:
    """Comprehensive shuffle/repeat testing across sources."""

    def __init__(self, ip: str):
        self.ip = ip
        self.client = WiiMClient(ip, timeout=5.0)
        self.player = Player(self.client)
        self.session: TestSession | None = None
        self.output_dir = Path("tests/shuffle-repeat-results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """Initialize connection and start test session."""
        try:
            print(f"\n{'=' * 80}")
            print(f"🎵 Shuffle/Repeat Source Testing - {self.ip}")
            print(f"{'=' * 80}\n")

            print("📡 Connecting to device...")
            await self.player.refresh()

            if not self.player.name:
                print("❌ Failed to connect to device")
                return False

            print(f"   ✓ Device: {self.player.name}")
            print(f"   ✓ Model: {self.player.model}")
            print(f"   ✓ Firmware: {self.player.firmware}")
            print(f"   ✓ Vendor: {self.player.client._capabilities.get('vendor', 'unknown')}")

            # Initialize test session
            self.session = TestSession(
                device_name=self.player.name or "Unknown",
                device_model=self.player.model or "Unknown",
                device_firmware=self.player.firmware or "Unknown",
                device_ip=self.ip,
                test_start=datetime.now().isoformat(),
                test_end=None,
                source_tests=[],
                errors=[],
                summary={},
            )

            return True

        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def test_current_source(self, content_description: str) -> SourceTest | None:
        """Test shuffle/repeat on whatever source is currently playing.

        Args:
            content_description: User description of current content
                                (e.g., "Spotify Album - Fleetwood Mac")
        """
        try:
            # Refresh state
            await self.player.refresh()
            await asyncio.sleep(0.5)

            source = self.player.source
            play_state = self.player.play_state

            if not source:
                print("   ⚠️  No active source detected")
                return None

            print(f"\n{'─' * 80}")
            print(f"📊 Testing Source: {source}")
            print(f"📝 Content: {content_description}")
            print(f"{'─' * 80}\n")

            # Record initial state
            initial_shuffle = self.player.shuffle_state
            initial_repeat = self.player.repeat_mode
            initial_loop_mode = self.player._status_model.loop_mode if self.player._status_model else None

            print(f"📋 Initial State:")
            print(f"   Source: {source}")
            print(f"   Play State: {play_state}")
            print(f"   Shuffle: {initial_shuffle}")
            print(f"   Repeat: {initial_repeat}")
            print(f"   Loop Mode: {initial_loop_mode}")

            # Check library prediction
            shuffle_supported_pred = self.player.shuffle_supported
            repeat_supported_pred = self.player.repeat_supported

            print(f"\n🔮 Library Prediction:")
            print(f"   Shuffle Supported: {shuffle_supported_pred}")
            print(f"   Repeat Supported: {repeat_supported_pred}")

            # Create test result
            test = SourceTest(
                source_name=source,
                content_description=content_description,
                timestamp=datetime.now().isoformat(),
                initial_source=source,
                initial_play_state=play_state,
                initial_shuffle=initial_shuffle,
                initial_repeat=initial_repeat,
                initial_loop_mode=initial_loop_mode,
                shuffle_supported_predicted=shuffle_supported_pred,
                repeat_supported_predicted=repeat_supported_pred,
                shuffle_test_attempted=False,
                shuffle_enable_success=None,
                shuffle_disable_success=None,
                shuffle_state_after_enable=None,
                shuffle_state_after_disable=None,
                shuffle_loop_mode_after_enable=None,
                shuffle_loop_mode_after_disable=None,
                shuffle_error=None,
                repeat_test_attempted=False,
                repeat_all_success=None,
                repeat_one_success=None,
                repeat_off_success=None,
                repeat_mode_after_all=None,
                repeat_mode_after_one=None,
                repeat_mode_after_off=None,
                repeat_loop_mode_after_all=None,
                repeat_loop_mode_after_one=None,
                repeat_loop_mode_after_off=None,
                repeat_error=None,
                repeat_preserved_during_shuffle=None,
                shuffle_preserved_during_repeat=None,
                shuffle_actually_works=None,
                repeat_actually_works=None,
                notes="",
            )

            # Test shuffle
            await self._test_shuffle(test, initial_repeat)

            # Small delay between tests
            await asyncio.sleep(0.5)

            # Test repeat
            await self._test_repeat(test, initial_shuffle)

            # Final assessment
            self._assess_results(test)

            # Restore initial state
            print("\n🔄 Restoring initial state...")
            await self._restore_state(initial_shuffle, initial_repeat)

            return test

        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback

            traceback.print_exc()
            if self.session:
                self.session.errors.append(f"{source}: {e}")
            return None

    async def _test_shuffle(self, test: SourceTest, initial_repeat: str | None) -> None:
        """Test shuffle controls."""
        print(f"\n🎲 Testing Shuffle Controls:")
        test.shuffle_test_attempted = True

        try:
            # Test: Enable shuffle
            print("   → Setting shuffle ON...")
            await self.player.set_shuffle(True)
            await asyncio.sleep(1.0)
            await self.player.refresh()

            test.shuffle_enable_success = True
            test.shuffle_state_after_enable = self.player.shuffle_state
            test.shuffle_loop_mode_after_enable = (
                self.player._status_model.loop_mode if self.player._status_model else None
            )

            repeat_after_shuffle_on = self.player.repeat_mode
            test.repeat_preserved_during_shuffle = repeat_after_shuffle_on == initial_repeat

            print(f"      ✓ Shuffle state: {test.shuffle_state_after_enable}")
            print(f"      ✓ Loop mode: {test.shuffle_loop_mode_after_enable}")
            print(f"      ✓ Repeat preserved: {test.repeat_preserved_during_shuffle}")

            # Test: Disable shuffle
            await asyncio.sleep(0.5)
            print("   → Setting shuffle OFF...")
            await self.player.set_shuffle(False)
            await asyncio.sleep(1.0)
            await self.player.refresh()

            test.shuffle_disable_success = True
            test.shuffle_state_after_disable = self.player.shuffle_state
            test.shuffle_loop_mode_after_disable = (
                self.player._status_model.loop_mode if self.player._status_model else None
            )

            print(f"      ✓ Shuffle state: {test.shuffle_state_after_disable}")
            print(f"      ✓ Loop mode: {test.shuffle_loop_mode_after_disable}")

            # Assessment
            shuffle_toggle_worked = (
                test.shuffle_state_after_enable == True and test.shuffle_state_after_disable == False
            )
            test.shuffle_actually_works = shuffle_toggle_worked

            if shuffle_toggle_worked:
                print(f"      ✅ Shuffle controls WORK")
            else:
                print(f"      ⚠️  Shuffle controls may not work properly")
                test.notes += "Shuffle state did not toggle as expected. "

        except Exception as e:
            test.shuffle_enable_success = False
            test.shuffle_error = str(e)
            test.shuffle_actually_works = False
            print(f"      ❌ Shuffle test failed: {e}")

    async def _test_repeat(self, test: SourceTest, initial_shuffle: bool | None) -> None:
        """Test repeat controls."""
        print(f"\n🔁 Testing Repeat Controls:")
        test.repeat_test_attempted = True

        try:
            # Test: Repeat ALL
            print("   → Setting repeat ALL...")
            await self.player.set_repeat("all")
            await asyncio.sleep(1.0)
            await self.player.refresh()

            test.repeat_all_success = True
            test.repeat_mode_after_all = self.player.repeat_mode
            test.repeat_loop_mode_after_all = self.player._status_model.loop_mode if self.player._status_model else None

            shuffle_after_all = self.player.shuffle_state

            print(f"      ✓ Repeat mode: {test.repeat_mode_after_all}")
            print(f"      ✓ Loop mode: {test.repeat_loop_mode_after_all}")
            print(f"      ✓ Shuffle: {shuffle_after_all}")

            # Test: Repeat ONE
            await asyncio.sleep(0.5)
            print("   → Setting repeat ONE...")
            await self.player.set_repeat("one")
            await asyncio.sleep(1.0)
            await self.player.refresh()

            test.repeat_one_success = True
            test.repeat_mode_after_one = self.player.repeat_mode
            test.repeat_loop_mode_after_one = self.player._status_model.loop_mode if self.player._status_model else None

            shuffle_after_one = self.player.shuffle_state

            print(f"      ✓ Repeat mode: {test.repeat_mode_after_one}")
            print(f"      ✓ Loop mode: {test.repeat_loop_mode_after_one}")
            print(f"      ✓ Shuffle: {shuffle_after_one}")

            # Test: Repeat OFF
            await asyncio.sleep(0.5)
            print("   → Setting repeat OFF...")
            await self.player.set_repeat("off")
            await asyncio.sleep(1.0)
            await self.player.refresh()

            test.repeat_off_success = True
            test.repeat_mode_after_off = self.player.repeat_mode
            test.repeat_loop_mode_after_off = self.player._status_model.loop_mode if self.player._status_model else None

            shuffle_after_off = self.player.shuffle_state

            print(f"      ✓ Repeat mode: {test.repeat_mode_after_off}")
            print(f"      ✓ Loop mode: {test.repeat_loop_mode_after_off}")
            print(f"      ✓ Shuffle: {shuffle_after_off}")

            # Check shuffle preservation
            test.shuffle_preserved_during_repeat = (
                shuffle_after_all == initial_shuffle
                and shuffle_after_one == initial_shuffle
                and shuffle_after_off == initial_shuffle
            )
            print(f"      ✓ Shuffle preserved: {test.shuffle_preserved_during_repeat}")

            # Assessment
            repeat_modes_correct = (
                test.repeat_mode_after_all == "all"
                and test.repeat_mode_after_one == "one"
                and test.repeat_mode_after_off == "off"
            )
            test.repeat_actually_works = repeat_modes_correct

            if repeat_modes_correct:
                print(f"      ✅ Repeat controls WORK")
            else:
                print(f"      ⚠️  Repeat controls may not work properly")
                test.notes += "Repeat modes did not change as expected. "

        except Exception as e:
            test.repeat_all_success = False
            test.repeat_error = str(e)
            test.repeat_actually_works = False
            print(f"      ❌ Repeat test failed: {e}")

    def _assess_results(self, test: SourceTest) -> None:
        """Generate final assessment."""
        print(f"\n📊 Assessment:")

        # Compare prediction vs reality
        shuffle_pred_match = test.shuffle_supported_predicted == test.shuffle_actually_works
        repeat_pred_match = test.repeat_supported_predicted == test.repeat_actually_works

        if test.shuffle_actually_works:
            print(f"   ✅ Shuffle: WORKS")
        elif test.shuffle_actually_works == False:
            print(f"   ❌ Shuffle: DOES NOT WORK")
        else:
            print(f"   ⚠️  Shuffle: UNKNOWN (test failed)")

        if not shuffle_pred_match and test.shuffle_actually_works is not None:
            pred_str = "supported" if test.shuffle_supported_predicted else "not supported"
            actual_str = "works" if test.shuffle_actually_works else "doesn't work"
            print(f"      ⚠️  Library predicted {pred_str}, but it actually {actual_str}!")
            test.notes += f"Shuffle prediction mismatch! "

        if test.repeat_actually_works:
            print(f"   ✅ Repeat: WORKS")
        elif test.repeat_actually_works == False:
            print(f"   ❌ Repeat: DOES NOT WORK")
        else:
            print(f"   ⚠️  Repeat: UNKNOWN (test failed)")

        if not repeat_pred_match and test.repeat_actually_works is not None:
            pred_str = "supported" if test.repeat_supported_predicted else "not supported"
            actual_str = "works" if test.repeat_actually_works else "doesn't work"
            print(f"      ⚠️  Library predicted {pred_str}, but it actually {actual_str}!")
            test.notes += f"Repeat prediction mismatch! "

    async def _restore_state(self, initial_shuffle: bool | None, initial_repeat: str | None) -> None:
        """Restore initial shuffle/repeat state."""
        try:
            if initial_shuffle is not None:
                await self.player.set_shuffle(initial_shuffle)
                await asyncio.sleep(0.3)

            if initial_repeat is not None:
                await self.player.set_repeat(initial_repeat)
                await asyncio.sleep(0.3)

            print("   ✓ State restored")
        except Exception as e:
            print(f"   ⚠️  Could not fully restore state: {e}")

    def save_results(self) -> Path:
        """Save test results to JSON file."""
        if not self.session:
            raise RuntimeError("No test session to save")

        self.session.test_end = datetime.now().isoformat()

        # Generate summary
        self.session.summary = self._generate_summary()

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shuffle_repeat_test_{self.session.device_model}_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w") as f:
            json.dump(asdict(self.session), f, indent=2)

        return filepath

    def _generate_summary(self) -> dict[str, Any]:
        """Generate test summary."""
        if not self.session:
            return {}

        sources_tested = len(self.session.source_tests)
        shuffle_works = sum(1 for t in self.session.source_tests if t.shuffle_actually_works)
        repeat_works = sum(1 for t in self.session.source_tests if t.repeat_actually_works)

        prediction_mismatches = []
        for t in self.session.source_tests:
            if t.shuffle_actually_works is not None and t.shuffle_supported_predicted != t.shuffle_actually_works:
                prediction_mismatches.append(
                    f"{t.source_name} ({t.content_description}): "
                    f"Shuffle predicted {t.shuffle_supported_predicted}, "
                    f"actually works: {t.shuffle_actually_works}"
                )
            if t.repeat_actually_works is not None and t.repeat_supported_predicted != t.repeat_actually_works:
                prediction_mismatches.append(
                    f"{t.source_name} ({t.content_description}): "
                    f"Repeat predicted {t.repeat_supported_predicted}, "
                    f"actually works: {t.repeat_actually_works}"
                )

        return {
            "sources_tested": sources_tested,
            "shuffle_works_count": shuffle_works,
            "repeat_works_count": repeat_works,
            "prediction_mismatches": prediction_mismatches,
            "errors_count": len(self.session.errors),
        }

    def print_summary(self) -> None:
        """Print test summary."""
        if not self.session:
            return

        print(f"\n{'=' * 80}")
        print("📊 TEST SUMMARY")
        print(f"{'=' * 80}\n")

        print(f"Device: {self.session.device_name} ({self.session.device_model})")
        print(f"Firmware: {self.session.device_firmware}")
        print(f"Tests completed: {len(self.session.source_tests)}\n")

        print("Results by Source:")
        print(f"{'─' * 80}")

        for test in self.session.source_tests:
            shuffle_icon = (
                "✅" if test.shuffle_actually_works else "❌" if test.shuffle_actually_works == False else "⚠️"
            )
            repeat_icon = "✅" if test.repeat_actually_works else "❌" if test.repeat_actually_works == False else "⚠️"

            print(f"\n{test.source_name} - {test.content_description}")
            print(f"  Shuffle: {shuffle_icon}  Repeat: {repeat_icon}")

            if test.notes:
                print(f"  Notes: {test.notes}")

        # Prediction mismatches
        summary = self.session.summary
        if summary.get("prediction_mismatches"):
            print(f"\n{'─' * 80}")
            print("⚠️  Prediction Mismatches (Library needs updating!):")
            for mismatch in summary["prediction_mismatches"]:
                print(f"  • {mismatch}")

        # Errors
        if self.session.errors:
            print(f"\n{'─' * 80}")
            print("❌ Errors encountered:")
            for error in self.session.errors:
                print(f"  • {error}")

        print(f"\n{'=' * 80}\n")

    async def run_interactive(self) -> None:
        """Run interactive testing session."""
        if not await self.initialize():
            return

        print(f"\n{'=' * 80}")
        print("📖 INTERACTIVE TESTING MODE")
        print(f"{'=' * 80}\n")
        print("Instructions:")
        print("1. Start playing content on the device (use WiiM app or other app)")
        print("2. Come back here and describe what's playing")
        print("3. Script will test shuffle/repeat on that source")
        print("4. Repeat for different sources and content types")
        print("\nContent Type Examples:")
        print("  • 'Spotify Album - Rumors by Fleetwood Mac'")
        print("  • 'Spotify Radio - Rock Mix'")
        print("  • 'USB - Local Playlist'")
        print("  • 'TuneIn - BBC Radio 1'")
        print("  • 'AirPlay - Apple Music Album'")
        print(f"\n{'=' * 80}\n")

        try:
            while True:
                print("\nOptions:")
                print("  [t] Test current source")
                print("  [r] Print results summary")
                print("  [q] Quit and save results")

                choice = input("\nYour choice: ").strip().lower()

                if choice == "q":
                    break
                elif choice == "r":
                    self.print_summary()
                elif choice == "t":
                    description = input("\nDescribe what's playing " "(source + content type): ").strip()

                    if not description:
                        print("⚠️  Description required")
                        continue

                    test = await self.test_current_source(description)
                    if test and self.session:
                        self.session.source_tests.append(test)
                else:
                    print("⚠️  Invalid choice")

        except KeyboardInterrupt:
            print("\n\n⚠️  Testing interrupted by user")

        # Save and summarize
        if self.session and self.session.source_tests:
            filepath = self.save_results()
            print(f"\n💾 Results saved to: {filepath}")
            self.print_summary()
        else:
            print("\n⚠️  No tests completed")

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.client.close()


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test-shuffle-repeat-by-source.py <device_ip>")
        print("\nExample:")
        print("  python scripts/test-shuffle-repeat-by-source.py 192.168.1.100")
        print("\nThis will start an interactive testing session where you can")
        print("test shuffle/repeat on different sources and content types.")
        sys.exit(1)

    device_ip = sys.argv[1]
    tester = ShuffleRepeatTester(device_ip)

    try:
        await tester.run_interactive()
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
        sys.exit(1)
