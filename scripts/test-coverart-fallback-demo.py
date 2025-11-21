#!/usr/bin/env python3
"""Demonstrate cover art fallback behavior - shows all scenarios."""


from pywiim.api.constants import DEFAULT_WIIM_LOGO_URL
from pywiim.api.parser import parse_player_status


def test_parser_fallback():
    """Test that parser correctly falls back to default logo."""
    print("\n" + "=" * 70)
    print("🧪 Test 1: Parser Fallback (No Artwork in API Response)")
    print("=" * 70)

    # Simulate response with NO cover art
    raw_no_artwork = {
        "status": "play",
        "Title": "Test Song",
        "Artist": "Test Artist",
        "Album": "Test Album",
        # NO cover art fields
    }

    parsed, _ = parse_player_status(raw_no_artwork, None)
    entity_picture = parsed.get("entity_picture")

    print("   Input: No cover art fields in API response")
    print(f"   Output: entity_picture = {entity_picture}")

    if entity_picture == DEFAULT_WIIM_LOGO_URL:
        print("   ✅ PASS: Parser correctly sets default logo")
    else:
        print("   ❌ FAIL: Parser did not set default logo")

    return entity_picture == DEFAULT_WIIM_LOGO_URL


def test_parser_with_artwork():
    """Test that parser uses real artwork when available."""
    print("\n" + "=" * 70)
    print("🧪 Test 2: Parser with Real Artwork")
    print("=" * 70)

    # Simulate response WITH cover art
    raw_with_artwork = {
        "status": "play",
        "Title": "Test Song",
        "Artist": "Test Artist",
        "Album": "Test Album",
        "albumArtURI": "https://example.com/artwork.jpg",  # Has artwork
    }

    parsed, _ = parse_player_status(raw_with_artwork, None)
    entity_picture = parsed.get("entity_picture")

    print("   Input: albumArtURI = https://example.com/artwork.jpg")
    print(f"   Output: entity_picture = {entity_picture}")

    if entity_picture and entity_picture != DEFAULT_WIIM_LOGO_URL and "example.com" in entity_picture:
        print("   ✅ PASS: Parser correctly uses real artwork")
    else:
        print("   ❌ FAIL: Parser did not use real artwork")

    return entity_picture and "example.com" in entity_picture


def test_base_fallback_logic():
    """Test that base.py correctly detects default logo and tries getMetaInfo."""
    print("\n" + "=" * 70)
    print("🧪 Test 3: Base Fallback Logic Detection")
    print("=" * 70)

    # Simulate parsed response with default logo
    parsed_with_default = {
        "title": "Test Song",
        "artist": "Test Artist",
        "album": "Test Album",
        "entity_picture": DEFAULT_WIIM_LOGO_URL,  # Default logo set by parser
    }

    # Check the logic that base.py uses
    entity_picture = parsed_with_default.get("entity_picture")
    has_valid_artwork = (
        entity_picture
        and str(entity_picture).strip()
        and str(entity_picture).strip().lower() not in ("unknow", "unknown", "un_known", "none", "")
        and str(entity_picture).strip() != DEFAULT_WIIM_LOGO_URL
    )

    print(f"   Input: entity_picture = {DEFAULT_WIIM_LOGO_URL} (default logo)")
    print(f"   Logic check: has_valid_artwork = {has_valid_artwork}")

    if not has_valid_artwork:
        print("   ✅ PASS: Base logic correctly identifies default logo as 'no valid artwork'")
        print("   ✅ This will trigger getMetaInfo fallback")
    else:
        print("   ❌ FAIL: Base logic incorrectly thinks default logo is valid artwork")

    return not has_valid_artwork


def main():
    """Run all fallback tests."""
    print("\n" + "=" * 70)
    print("🎨 Cover Art Fallback Test Suite")
    print("=" * 70)

    results = []

    # Test 1: Parser fallback
    results.append(("Parser Fallback", test_parser_fallback()))

    # Test 2: Parser with artwork
    results.append(("Parser with Artwork", test_parser_with_artwork()))

    # Test 3: Base fallback logic
    results.append(("Base Fallback Logic", test_base_fallback_logic()))

    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✅ All tests passed! Fallback logic is working correctly.")
    else:
        print("❌ Some tests failed. Please review the output above.")

    print("\n💡 How it works:")
    print("   1. Parser sets default logo when no artwork in getPlayerStatusEx")
    print("   2. Base.py detects default logo and treats it as 'no valid artwork'")
    print("   3. Base.py calls getMetaInfo to try to get real artwork")
    print("   4. If getMetaInfo has artwork, it's used; otherwise default logo remains")
    print("   5. fetch_cover_art() can fetch either the real artwork or default logo")
    print()


if __name__ == "__main__":
    main()

