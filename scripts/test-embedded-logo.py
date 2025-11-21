#!/usr/bin/env python3
"""Test the embedded base64 SVG fallback logo."""

import asyncio
import sys
from pathlib import Path

from pywiim import WiiMClient
from pywiim.player import Player
from pywiim.api.constants import DEFAULT_WIIM_LOGO_URL
from pywiim.api.parser import parse_player_status


def test_data_uri():
    """Test that the logo is a valid data URI."""
    print("\n" + "=" * 80)
    print("Testing Embedded Logo Data URI")
    print("=" * 80 + "\n")
    
    print(f"Logo Type: {'data:' if DEFAULT_WIIM_LOGO_URL.startswith('data:') else 'http:'}")
    print(f"Logo Size: {len(DEFAULT_WIIM_LOGO_URL):,} bytes")
    print(f"First 80 chars: {DEFAULT_WIIM_LOGO_URL[:80]}")
    print()
    
    if DEFAULT_WIIM_LOGO_URL.startswith("data:image/svg+xml;base64,"):
        print("✅ Valid SVG data URI format")
        
        # Extract and decode base64
        import base64
        base64_data = DEFAULT_WIIM_LOGO_URL.split(",", 1)[1]
        try:
            svg_content = base64.b64decode(base64_data).decode('utf-8')
            print(f"✅ Valid base64 encoding ({len(svg_content)} bytes decoded)")
            
            # Check if it's valid SVG
            if "<svg" in svg_content and "</svg>" in svg_content:
                print("✅ Valid SVG structure")
            else:
                print("❌ Invalid SVG structure")
                
            # Show a snippet
            print(f"\nSVG Preview (first 200 chars):")
            print(f"  {svg_content[:200]}...")
            
        except Exception as e:
            print(f"❌ Failed to decode base64: {e}")
    else:
        print("⚠️  Not a data URI - using external URL")
    
    print()


def test_parser_fallback():
    """Test that parser correctly sets fallback logo when no artwork."""
    print("=" * 80)
    print("Testing Parser Fallback Logic")
    print("=" * 80 + "\n")
    
    # Test 1: No artwork fields at all
    print("Test 1: getPlayerStatusEx with NO artwork fields")
    raw_response_no_art = {
        "type": "0",
        "ch": "0",
        "mode": "1",
        "status": "play",
        "curpos": "10000",
        "totlen": "200000",
        "Title": "Test Song",
        "Artist": "Test Artist",
        "Album": "Test Album",
        "vol": "20",
        "mute": "0"
    }
    
    parsed, _ = parse_player_status(raw_response_no_art)
    entity_picture = parsed.get("entity_picture")
    
    print(f"  Result: entity_picture = {entity_picture[:50]}..." if entity_picture and len(entity_picture) > 50 else f"  Result: entity_picture = {entity_picture}")
    
    if entity_picture == DEFAULT_WIIM_LOGO_URL:
        print("  ✅ PASS: Parser correctly set fallback logo\n")
    else:
        print(f"  ❌ FAIL: Expected fallback logo\n")
    
    # Test 2: Invalid artwork values (unknow, unknown, etc.)
    print("Test 2: getPlayerStatusEx with invalid artwork ('unknow')")
    raw_response_invalid_art = {
        "type": "0",
        "status": "play",
        "Title": "Test Song 2",
        "cover": "unknow",  # Invalid value
        "albumart": "unknown",  # Invalid value
    }
    
    parsed, _ = parse_player_status(raw_response_invalid_art)
    entity_picture = parsed.get("entity_picture")
    
    print(f"  Result: entity_picture = {entity_picture[:50]}..." if entity_picture and len(entity_picture) > 50 else f"  Result: entity_picture = {entity_picture}")
    
    if entity_picture == DEFAULT_WIIM_LOGO_URL:
        print("  ✅ PASS: Parser correctly set fallback logo for invalid artwork\n")
    else:
        print(f"  ❌ FAIL: Expected fallback logo\n")
    
    # Test 3: Valid artwork URL should NOT use fallback
    print("Test 3: getPlayerStatusEx with valid artwork URL")
    raw_response_valid_art = {
        "type": "0",
        "status": "play",
        "Title": "Test Song 3",
        "cover": "https://example.com/artwork.jpg",
    }
    
    parsed, _ = parse_player_status(raw_response_valid_art)
    entity_picture = parsed.get("entity_picture")
    
    print(f"  Result: entity_picture = {entity_picture}")
    
    if entity_picture != DEFAULT_WIIM_LOGO_URL and "example.com" in entity_picture:
        print("  ✅ PASS: Parser kept valid artwork URL\n")
    else:
        print(f"  ❌ FAIL: Should have kept valid artwork URL\n")


def create_html_preview():
    """Create an HTML file to preview the logo in a browser."""
    print("=" * 80)
    print("Creating HTML Preview")
    print("=" * 80 + "\n")
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>PyWiim Fallback Logo Preview</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .preview {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        img {{
            max-width: 300px;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin: 20px;
        }}
        .info {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
            text-align: left;
        }}
        code {{
            background: #e8e8e8;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="preview">
        <h1>PyWiim Fallback Logo</h1>
        <p>This logo is displayed when no cover art is available</p>
        
        <img src="{DEFAULT_WIIM_LOGO_URL}" alt="PyWiim Logo">
        
        <div class="info">
            <h3>Technical Details</h3>
            <ul>
                <li><strong>Format:</strong> SVG (Scalable Vector Graphics)</li>
                <li><strong>Encoding:</strong> Base64 data URI</li>
                <li><strong>Size:</strong> {len(DEFAULT_WIIM_LOGO_URL):,} bytes</li>
                <li><strong>Type:</strong> Embedded (no external dependencies)</li>
                <li><strong>Benefits:</strong>
                    <ul>
                        <li>✅ Always available (no network required)</li>
                        <li>✅ No CORS issues</li>
                        <li>✅ No HTTP 403 errors</li>
                        <li>✅ Instant display</li>
                    </ul>
                </li>
            </ul>
        </div>
    </div>
</body>
</html>"""
    
    html_file = Path("pywiim-logo-preview.html")
    html_file.write_text(html_content)
    
    print(f"✅ HTML preview saved to: {html_file}")
    print(f"   Open this file in a browser to see the logo:\n")
    print(f"   file://{html_file.absolute()}\n")


async def test_with_device(ip: str):
    """Test fallback logo with a real device (when nothing is playing)."""
    print("=" * 80)
    print(f"Testing with Real Device: {ip}")
    print("=" * 80 + "\n")
    
    client = WiiMClient(ip, timeout=5.0)
    player = Player(client)
    
    try:
        await player.refresh()
        
        print("Current Player State:")
        print(f"  Play State: {player.play_state}")
        print(f"  Title: {player.media_title or 'N/A'}")
        print(f"  Artist: {player.media_artist or 'N/A'}")
        print(f"  Cover Art URL: {player.media_image_url[:80] if player.media_image_url else 'None'}...")
        print()
        
        if player.media_image_url == DEFAULT_WIIM_LOGO_URL:
            print("✅ Device is using fallback logo (no cover art available)")
        elif player.media_image_url:
            if player.media_image_url.startswith("data:"):
                print("✅ Device is using embedded image (data URI)")
            else:
                print("ℹ️  Device has real cover art from external URL")
        else:
            print("⚠️  Device has no cover art URL at all")
        
    except Exception as e:
        print(f"❌ Error testing with device: {e}")
    finally:
        await client.close()


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("PyWiim Embedded Logo Test Suite")
    print("=" * 80)
    
    # Test 1: Data URI validation
    test_data_uri()
    
    # Test 2: Parser fallback logic
    test_parser_fallback()
    
    # Test 3: Create HTML preview
    create_html_preview()
    
    # Test 4: Real device (optional)
    if len(sys.argv) > 1:
        ip = sys.argv[1]
        asyncio.run(test_with_device(ip))
    else:
        print("=" * 80)
        print("Optional: Test with Real Device")
        print("=" * 80 + "\n")
        print("To test with a real device, run:")
        print(f"  python3 {sys.argv[0]} <device-ip>\n")
    
    print("=" * 80)
    print("✅ All Tests Complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

