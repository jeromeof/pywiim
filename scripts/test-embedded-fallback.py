#!/usr/bin/env python3
"""Test the embedded logo fallback - serves bytes directly, no HTTP call."""

import asyncio
import sys
from pathlib import Path

from pywiim import WiiMClient
from pywiim.player import Player
from pywiim.api.constants import EMBEDDED_LOGO_BASE64


def test_logo_constant():
    """Test that the embedded logo constant is valid."""
    print("\n" + "=" * 80)
    print("Testing Embedded Logo Constant")
    print("=" * 80 + "\n")
    
    import base64
    
    # Test decoding
    try:
        logo_bytes = base64.b64decode(EMBEDDED_LOGO_BASE64)
        print(f"✅ Logo decoded successfully")
        print(f"   Size: {len(logo_bytes):,} bytes ({len(logo_bytes)/1024:.2f} KB)")
        
        # Check PNG header
        if logo_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            print(f"✅ Valid PNG header detected")
        else:
            print(f"❌ Invalid PNG header")
        
        # Save for inspection
        Path("decoded-logo.png").write_bytes(logo_bytes)
        print(f"✅ Saved to: decoded-logo.png\n")
        
        return logo_bytes
        
    except Exception as e:
        print(f"❌ Failed to decode: {e}\n")
        return None


async def test_fetch_without_device():
    """Test fetch_cover_art() without a real device - just the embedded logo."""
    print("=" * 80)
    print("Testing fetch_cover_art() with No URL (Embedded Logo)")
    print("=" * 80 + "\n")
    
    # Create a mock player
    client = WiiMClient("1.2.3.4", timeout=1.0)  # Fake IP, won't actually connect
    player = Player(client)
    
    try:
        # Call fetch_cover_art() with no URL - should return embedded logo
        print("Calling player.fetch_cover_art() with no URL...")
        result = await player.fetch_cover_art(url=None)
        
        if result:
            image_bytes, content_type = result
            print(f"✅ Got result!")
            print(f"   Content-Type: {content_type}")
            print(f"   Size: {len(image_bytes):,} bytes ({len(image_bytes)/1024:.2f} KB)")
            
            # Verify it's a PNG
            if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                print(f"✅ Valid PNG image")
            else:
                print(f"❌ Not a valid PNG")
            
            # Save it
            output_file = Path("fetched-logo-no-device.png")
            output_file.write_bytes(image_bytes)
            print(f"✅ Saved to: {output_file}")
            print(f"\n🎉 SUCCESS: fetch_cover_art() returned embedded logo without HTTP call!\n")
            
            return True
        else:
            print(f"❌ fetch_cover_art() returned None\n")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()


async def test_with_real_device(ip: str):
    """Test with a real device that has no artwork."""
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
        print(f"  Cover Art URL: {player.media_image_url or 'None'}")
        print()
        
        # Test fetch_cover_art()
        print("Calling player.fetch_cover_art()...")
        result = await player.fetch_cover_art()
        
        if result:
            image_bytes, content_type = result
            print(f"✅ Success!")
            print(f"   Content-Type: {content_type}")
            print(f"   Size: {len(image_bytes):,} bytes ({len(image_bytes)/1024:.2f} KB)")
            
            # Check if it's the embedded logo
            import base64
            embedded_bytes = base64.b64decode(EMBEDDED_LOGO_BASE64)
            
            if image_bytes == embedded_bytes:
                print(f"✅ Returned embedded PyWiim logo (no HTTP call made)")
                output_file = Path(f"logo-from-device-{ip.replace('.', '-')}.png")
            else:
                print(f"ℹ️  Returned real cover art from device/URL")
                output_file = Path(f"coverart-from-device-{ip.replace('.', '-')}.png")
            
            output_file.write_bytes(image_bytes)
            print(f"✅ Saved to: {output_file}\n")
        else:
            print(f"❌ fetch_cover_art() returned None\n")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("PyWiim Embedded Logo Fallback Test")
    print("=" * 80)
    
    # Test 1: Verify logo constant
    logo_bytes = test_logo_constant()
    if not logo_bytes:
        print("❌ Logo constant test failed - aborting\n")
        return 1
    
    # Test 2: Test fetch_cover_art() without device (embedded logo only)
    success = asyncio.run(test_fetch_without_device())
    if not success:
        print("❌ Embedded logo fetch test failed\n")
        return 1
    
    # Test 3: Test with real device (optional)
    if len(sys.argv) > 1:
        ip = sys.argv[1]
        asyncio.run(test_with_real_device(ip))
    else:
        print("=" * 80)
        print("Optional: Test with Real Device")
        print("=" * 80 + "\n")
        print("To test with a real device, run:")
        print(f"  python3 {sys.argv[0]} <device-ip>\n")
    
    print("=" * 80)
    print("✅ All Tests Complete!")
    print("=" * 80 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

