#!/usr/bin/env python3
"""Test UPnP support across all configured test devices.

Tests whether each device responds to UPnP description.xml requests
and what services they advertise.

Usage:
    python scripts/debug/test_upnp_support.py

This script is useful for:
- Verifying UPnP is working on all devices
- Debugging UPnP connectivity issues
- Confirming device capabilities before release

All LinkPlay devices should support UPnP (AVTransport, RenderingControl).
If a device times out, it's likely a transient issue (device booting, network).
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import aiohttp
import yaml


async def test_upnp_device(ip: str, name: str, model: str, timeout: float = 5.0) -> dict:
    """Test UPnP support for a single device."""
    result = {
        "ip": ip,
        "name": name,
        "model": model,
        "upnp_reachable": False,
        "description_fetched": False,
        "services": [],
        "error": None,
    }

    url = f"http://{ip}:49152/description.xml"

    try:
        async with aiohttp.ClientSession() as session:
            async with asyncio.timeout(timeout):
                async with session.get(url) as response:
                    if response.status == 200:
                        result["upnp_reachable"] = True
                        text = await response.text()
                        result["description_fetched"] = True

                        # Parse for services
                        if "AVTransport" in text:
                            result["services"].append("AVTransport")
                        if "RenderingControl" in text:
                            result["services"].append("RenderingControl")
                        if "ContentDirectory" in text:
                            result["services"].append("ContentDirectory")
                        if "ConnectionManager" in text:
                            result["services"].append("ConnectionManager")
                    else:
                        result["error"] = f"HTTP {response.status}"
    except asyncio.TimeoutError:
        result["error"] = f"Timeout after {timeout}s"
    except aiohttp.ClientError as e:
        result["error"] = f"Connection error: {type(e).__name__}"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    return result


async def main():
    """Test all devices from devices.yaml."""
    # Load devices config
    config_path = Path(__file__).parent.parent.parent / "tests" / "devices.yaml"

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return

    with open(config_path) as f:
        config = yaml.safe_load(f)

    devices = config.get("devices", [])

    if not devices:
        print("❌ No devices configured in devices.yaml")
        return

    print("=" * 70)
    print("UPnP Support Test - All Configured Devices")
    print("=" * 70)
    print()

    # Test all devices concurrently
    tasks = []
    for device in devices:
        ip = device.get("ip")
        name = device.get("name", "Unknown")
        model = device.get("model", "unknown")
        tasks.append(test_upnp_device(ip, name, model))

    results = await asyncio.gather(*tasks)

    # Print results
    for result in results:
        status = "✅" if result["upnp_reachable"] else "❌"
        print(f"{status} {result['name']} ({result['ip']}) - {result['model']}")

        if result["upnp_reachable"]:
            print(f"   Services: {', '.join(result['services']) or 'None found'}")
        else:
            print(f"   Error: {result['error']}")
        print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    success = sum(1 for r in results if r["upnp_reachable"])
    failed = len(results) - success

    print(f"✅ Reachable: {success}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")

    if failed > 0:
        print("\nFailed devices:")
        for result in results:
            if not result["upnp_reachable"]:
                print(f"  - {result['name']} ({result['ip']}): {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
