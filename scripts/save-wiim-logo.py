#!/usr/bin/env python3
"""Fetch and save the default WiiM logo directly."""

import asyncio
import sys
from pathlib import Path
import aiohttp

from pywiim.api.constants import DEFAULT_WIIM_LOGO_URL


async def save_wiim_logo(output_file: str = "wiim-logo-fallback.jpg"):
    """Fetch and save the WiiM logo."""
    print(f"\n📥 Fetching WiiM logo from: {DEFAULT_WIIM_LOGO_URL}\n")

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(DEFAULT_WIIM_LOGO_URL) as response:
                if response.status == 200:
                    image_bytes = await response.read()
                    content_type = response.headers.get("Content-Type", "image/png")
                    
                    print(f"✅ Success!")
                    print(f"   Content Type: {content_type}")
                    print(f"   Size: {len(image_bytes):,} bytes ({len(image_bytes) / 1024:.1f} KB)")
                    
                    # Save to file
                    output_path = Path(output_file)
                    output_path.write_bytes(image_bytes)
                    print(f"\n💾 Saved to: {output_path.absolute()}")
                    print(f"   File size: {output_path.stat().st_size:,} bytes")
                    print(f"   ✅ WiiM logo saved successfully!")
                    return 0
                else:
                    print(f"❌ Failed to fetch logo: HTTP {response.status}")
                    return 1
    except Exception as e:
        print(f"❌ Error fetching logo: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    output_file = "wiim-logo-fallback.jpg"
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    
    sys.exit(asyncio.run(save_wiim_logo(output_file)))

