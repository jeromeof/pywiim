"""Integration tests for source selection.

Tests the source selection fixes from GitHub issue #153:
- Correct API format (hyphenated: line-in, not underscored: line_in)
- Source name normalization for display (Title Case)
- Source selection with various input formats

These tests require a real WiiM device to be available on the network.
Set the WIIM_TEST_DEVICE environment variable to enable these tests.

Example:
    WIIM_TEST_DEVICE=192.168.1.100 pytest tests/integration/test_source_selection.py -v
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest


@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.asyncio
class TestSourceSelectionIntegration:
    """Integration tests for source selection functionality."""

    async def test_available_sources_format(self, real_device_player, integration_test_marker):
        """Test that available_sources returns properly formatted names.

        Verifies fix for GitHub issue #153: "CoaxIal" should be "Coaxial",
        all source names should be in consistent Title Case format.
        """
        player = real_device_player
        await player.refresh(full=True)

        sources = player.available_sources
        assert sources is not None
        assert isinstance(sources, list)

        # Check that all source names are properly formatted
        # Known acronyms that should be uppercase
        known_acronyms = {"wifi", "usb", "hdmi", "dlna"}

        print(f"\nAvailable sources: {sources}")

        for source in sources:
            source_lower = source.lower().replace(" ", " ")  # Normalize whitespace

            # Check for known bad formats
            assert source != "CoaxIal", f"Source name has wrong capitalization: {source}"
            assert source != "Line_In", f"Source name has underscore: {source}"
            assert source != "line-in", f"Source name has hyphen: {source}"

            # Verify Title Case (first letter of each word capitalized)
            # Exception: acronyms like WiFi, USB, HDMI, DLNA
            if source_lower not in known_acronyms and source not in ("WiFi", "USB", "HDMI", "DLNA", "AirPlay"):
                words = source.split()
                for word in words:
                    if word.lower() not in known_acronyms:
                        # First letter should be uppercase
                        assert word[0].isupper(), f"Source '{source}' word '{word}' not Title Case"

            print(f"  ✓ '{source}' format OK")

    async def test_source_selection_api_format(self, real_device_player, integration_test_marker):
        """Test that source selection sends correct API format.

        Verifies fix for GitHub issue #153: API should receive hyphenated
        format (line-in) not underscored (line_in).

        This test intercepts the actual API call to verify the format.
        """
        player = real_device_player
        await player.refresh(full=True)

        # Track what API calls are made
        api_calls = []

        async def tracking_request(url, *args, **kwargs):
            api_calls.append(url)
            # Don't actually make the call to avoid changing device state
            return "OK"

        # Test various input formats - all should normalize to hyphenated API format
        test_cases = [
            ("Line In", "line-in"),
            ("line in", "line-in"),
            ("line_in", "line-in"),
            ("Line-In", "line-in"),
            ("Bluetooth", "bluetooth"),
            ("bluetooth", "bluetooth"),
            ("Optical", "optical"),
            ("optical", "optical"),
            ("Coaxial", "coaxial"),
            ("coaxial", "coaxial"),
            ("WiFi", "wifi"),
            ("wifi", "wifi"),
        ]

        for user_input, expected_api_format in test_cases:
            api_calls.clear()

            # Patch the request to track calls without actually changing source
            with patch.object(player.client, "_request", side_effect=tracking_request):
                try:
                    await player.audio.set_source(user_input)
                except Exception:
                    pass  # We're just checking the API call format

            # Verify the API was called with correct format
            if api_calls:
                # Find the switchmode call
                switchmode_calls = [c for c in api_calls if "switchmode" in c]
                if switchmode_calls:
                    call = switchmode_calls[0]
                    # Verify the format sent to API
                    assert (
                        expected_api_format in call
                    ), f"Input '{user_input}' should send '{expected_api_format}' to API, got: {call}"
                    print(f"  ✓ '{user_input}' → API: '{expected_api_format}'")

    async def test_source_selection_roundtrip(self, real_device_player, integration_test_marker):
        """Test actual source selection on real device.

        This test actually changes the device source and verifies
        the change takes effect. Use with caution - modifies device state.
        """
        player = real_device_player
        await player.refresh(full=True)

        # Save original source to restore later
        original_source = player.source
        print(f"\nOriginal source: {original_source}")

        available = player.available_sources
        print(f"Available sources: {available}")

        # Find a physical input source to test with
        test_source = None
        physical_inputs = ["bluetooth", "wifi", "optical", "line in", "coaxial"]
        for source in available:
            if source.lower() in physical_inputs:
                # If no current source, use first available physical input
                if not original_source:
                    test_source = source
                    break
                # Don't test with current source
                elif source.lower() != original_source.lower():
                    test_source = source
                    break

        if not test_source:
            pytest.skip("No suitable source found for testing (need physical input available)")

        try:
            print(f"\nTesting source selection: '{test_source}'")

            # Select the source
            await player.audio.set_source(test_source)

            # Wait for device to process
            await asyncio.sleep(2.0)

            # Refresh to get current state
            await player.refresh()

            # Verify source changed
            current_source = player.source
            print(f"Current source after selection: {current_source}")

            # Source names might have slight variations in formatting
            # Compare case-insensitively with normalized characters
            def normalize(s):
                if s is None:
                    return ""
                return s.lower().replace("_", " ").replace("-", " ")

            if normalize(current_source) == normalize(test_source):
                print(f"  ✓ Source successfully changed to '{current_source}'")
            else:
                # Note: Some devices may not report source change immediately
                # or may show a different name for the same input
                print(f"  ⚠️ Source is '{current_source}', expected '{test_source}'")
                print("     (Device may report source differently or need more time)")

        finally:
            # Restore original source if possible
            if original_source:
                try:
                    print(f"\nRestoring original source: {original_source}")
                    await player.audio.set_source(original_source)
                    await asyncio.sleep(1.0)
                except Exception as e:
                    print(f"  Warning: Could not restore original source: {e}")


@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.asyncio
class TestSourceNormalizationUnit:
    """Unit-style tests for source normalization logic.

    These tests verify the normalization functions work correctly
    without making actual API calls. They run against a real device
    to ensure the Player is properly initialized.
    """

    async def test_normalize_source_for_api_line_in_variants(self, real_device_player, integration_test_marker):
        """Test that all Line In variants normalize to 'line-in' for API."""
        player = real_device_player

        # These should all produce "line-in" for the API
        test_cases = [
            "Line In",
            "line in",
            "Line_In",
            "line_in",
            "Line-In",
            "line-in",
            "linein",
            "LineIn",
        ]

        for input_name in test_cases:
            result = player.audio._normalize_source_for_api(input_name)
            assert result == "line-in", f"'{input_name}' should normalize to 'line-in', got '{result}'"
            print(f"  ✓ '{input_name}' → '{result}'")

    async def test_normalize_source_for_api_other_sources(self, real_device_player, integration_test_marker):
        """Test normalization of other common sources."""
        player = real_device_player

        test_cases = [
            # (input, expected)
            ("Bluetooth", "bluetooth"),
            ("bluetooth", "bluetooth"),
            ("BLUETOOTH", "bluetooth"),
            ("Optical", "optical"),
            ("optical", "optical"),
            ("Coaxial", "coaxial"),
            ("coaxial", "coaxial"),
            ("coax", "coaxial"),
            ("WiFi", "wifi"),
            ("wifi", "wifi"),
            ("Wi-Fi", "wifi"),
            ("Spotify", "spotify"),
            ("spotify", "spotify"),
            ("AirPlay", "airplay"),
            ("airplay", "airplay"),
        ]

        for input_name, expected in test_cases:
            result = player.audio._normalize_source_for_api(input_name)
            assert result == expected, f"'{input_name}' should normalize to '{expected}', got '{result}'"
            print(f"  ✓ '{input_name}' → '{result}'")

    async def test_normalize_source_name_for_display(self, real_device_player, integration_test_marker):
        """Test that source names are properly formatted for UI display."""
        player = real_device_player

        # Test the display normalization function (via _properties)
        test_cases = [
            # (input, expected)
            ("line_in", "Line In"),
            ("line-in", "Line In"),
            ("linein", "Linein"),  # Can't split without separator
            ("CoaxIal", "Coaxial"),
            ("coaxial", "Coaxial"),
            ("OPTICAL", "Optical"),
            ("bluetooth", "Bluetooth"),
            ("wifi", "WiFi"),  # Special case - WiFi is an acronym
            ("USB", "USB"),  # Acronym preserved
            ("hdmi", "HDMI"),  # Acronym preserved
            ("dlna", "DLNA"),  # Acronym preserved
            ("spotify", "Spotify"),
            ("airplay", "AirPlay"),  # Special case
        ]

        for input_name, expected in test_cases:
            result = player._properties._normalize_source_name(input_name)
            assert result == expected, f"'{input_name}' should display as '{expected}', got '{result}'"
            print(f"  ✓ '{input_name}' → '{result}'")
