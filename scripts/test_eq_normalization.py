#!/usr/bin/env python3
"""Test EQ preset normalization against real device.

Tests that EQ preset names with spaces, hyphens, underscores, and typos
are properly normalized and work with the device.
"""

from __future__ import annotations

import asyncio
import sys

from pywiim.client import WiiMClient


async def test_eq_normalization(ip: str) -> None:
    """Test EQ preset normalization with various input formats."""
    client = WiiMClient(ip)

    print(f"\n🔧 Testing EQ preset normalization on {ip}")
    print("=" * 60)

    # Test cases: (input, expected_normalized_key, description)
    test_cases = [
        ("bassreducer", "bassreducer", "Direct key (no normalization needed)"),
        ("bass reducer", "bassreducer", "Space-separated"),
        ("base reducer", "bassreducer", "Typo: 'base' -> 'bass'"),
        ("Bass Reducer", "bassreducer", "Display name (capitalized)"),
        ("bass_reducer", "bassreducer", "Underscore-separated"),
        ("bass-reducer", "bassreducer", "Hyphen-separated"),
        ("acoustic", "acoustic", "Simple preset (no spaces)"),
        ("Acoustic", "acoustic", "Simple preset (capitalized)"),
    ]

    # Get current EQ preset to restore later
    try:
        current_eq = await client.get_eq()
        original_preset = None
        if isinstance(current_eq, dict):
            original_preset = (
                current_eq.get("Name")
                or current_eq.get("name")
                or current_eq.get("preset")
                or current_eq.get("EQPreset")
            )
        print(f"📊 Current EQ preset: {original_preset or 'Unknown'}")
    except Exception as e:
        print(f"⚠️  Could not get current EQ preset: {e}")
        original_preset = None

    print("\n🧪 Testing normalization:")
    passed = 0
    failed = 0

    for input_preset, expected_key, description in test_cases:
        try:
            # Test normalization (without actually setting on device)
            normalized = client._normalize_eq_preset_name(input_preset)
            if normalized == expected_key:
                print(f"  ✓ {description:30} '{input_preset}' -> '{normalized}'")
                passed += 1
            else:
                print(
                    f"  ✗ {description:30} '{input_preset}' -> '{normalized}' (expected '{expected_key}')"
                )
                failed += 1
        except ValueError as e:
            print(f"  ✗ {description:30} '{input_preset}' -> ERROR: {e}")
            failed += 1

    print(f"\n📈 Normalization tests: {passed} passed, {failed} failed")

    # Test actual device calls with problematic formats
    print("\n🔌 Testing actual device calls:")
    device_test_cases = [
        ("bass reducer", "Space-separated format"),
        ("base reducer", "Typo format (base -> bass)"),
        ("Bass Reducer", "Display name format"),
    ]

    device_passed = 0
    device_failed = 0

    for input_preset, description in device_test_cases:
        try:
            print(f"  Testing: {description} ('{input_preset}')")
            await client.set_eq_preset(input_preset)
            await asyncio.sleep(0.5)

            # Verify it was set
            verify_eq = await client.get_eq()
            if isinstance(verify_eq, dict):
                set_name = (
                    verify_eq.get("Name")
                    or verify_eq.get("name")
                    or verify_eq.get("preset")
                    or verify_eq.get("EQPreset")
                    or "Unknown"
                )
                print(f"    ✓ Set successfully (device reports: '{set_name}')")
                device_passed += 1
            else:
                print(f"    ⚠️  Set but couldn't verify (response: {verify_eq})")
                device_passed += 1
        except ValueError as e:
            print(f"    ✗ Normalization failed: {e}")
            device_failed += 1
        except Exception as e:
            print(f"    ✗ Device call failed: {e}")
            device_failed += 1

    print(f"\n📈 Device tests: {device_passed} passed, {device_failed} failed")

    # Restore original preset if we had one
    if original_preset:
        try:
            print(f"\n🔄 Restoring original EQ preset: {original_preset}")
            # Normalize the original preset name in case it has spaces
            normalized_original = client._normalize_eq_preset_name(original_preset)
            await client.set_eq_preset(normalized_original)
            print("  ✓ Restored")
        except Exception as e:
            print(f"  ⚠️  Could not restore: {e}")

    print("\n" + "=" * 60)
    total_passed = passed + device_passed
    total_failed = failed + device_failed
    print(f"📊 Summary: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        sys.exit(1)


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test EQ preset normalization")
    parser.add_argument(
        "ip",
        nargs="?",
        default="192.168.1.116",
        help="Device IP address (default: 192.168.1.116)",
    )
    args = parser.parse_args()

    await test_eq_normalization(args.ip)


if __name__ == "__main__":
    asyncio.run(main())

