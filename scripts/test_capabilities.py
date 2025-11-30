#!/usr/bin/env python3
"""Test capability detection for device."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pywiim import WiiMClient

logging.basicConfig(
    level=logging.INFO,  # Less verbose
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_LOGGER = logging.getLogger(__name__)


async def test_device(host: str) -> None:
    """Test capability detection."""
    print(f"\n{'='*60}")
    print(f"Testing capabilities for: {host}")
    print(f"{'='*60}")

    try:
        client = WiiMClient(host=host)

        # Detect capabilities
        print(f"\n1. Detecting capabilities...")
        await client._detect_capabilities()

        print(f"\n2. Detected capabilities:")
        caps = client.capabilities
        print(f"   vendor: {caps.get('vendor')}")
        print(f"   audio_pro_generation: {caps.get('audio_pro_generation')}")
        print(f"   supports_player_status_ex: {caps.get('supports_player_status_ex')}")
        print(f"   status_endpoint: {caps.get('status_endpoint')}")
        print(f"   device_type: {caps.get('device_type')}")
        print(f"   firmware: {caps.get('firmware_version')}")

        # Test getPlayerStatusEx directly
        print(f"\n3. Testing getPlayerStatusEx directly...")
        try:
            raw = await client._request("/httpapi.asp?command=getPlayerStatusEx")
            if isinstance(raw, dict):
                volume = raw.get("volume")
                print(f"   ✅ getPlayerStatusEx works! volume: {volume}")
            else:
                print(f"   ⚠️  getPlayerStatusEx returned non-dict: {type(raw)}")
        except Exception as err:
            print(f"   ❌ getPlayerStatusEx failed: {err}")

        # Test getStatusEx
        print(f"\n4. Testing getStatusEx...")
        try:
            raw = await client._request("/httpapi.asp?command=getStatusEx")
            if isinstance(raw, dict):
                volume = raw.get("volume")
                print(f"   getStatusEx volume: {volume}")
            else:
                print(f"   ⚠️  getStatusEx returned non-dict: {type(raw)}")
        except Exception as err:
            print(f"   ❌ getStatusEx failed: {err}")

        # Check what get_player_status actually uses
        print(f"\n5. What get_player_status() uses:")
        status = await client.get_player_status()
        volume = status.get("volume")
        print(f"   volume from get_player_status(): {volume}")

        print(f"\n✅ Test completed for {host}")

    except Exception as err:
        print(f"\n❌ Error testing {host}: {err}")
        import traceback

        traceback.print_exc()
    finally:
        try:
            await client.close()
        except Exception:
            pass


async def main() -> None:
    """Test device."""
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = "192.168.6.50"  # Default
    await test_device(host)


if __name__ == "__main__":
    asyncio.run(main())
