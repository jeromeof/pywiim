#!/usr/bin/env python3
"""Quick test script for testing pywiim against real devices.

Usage:
    python test_my_devices.py <device_ip> [<device_ip2> ...]
    python test_my_devices.py --debug-capabilities <device_ip>

Example:
    python test_my_devices.py 192.168.1.100
    python test_my_devices.py 192.168.1.100 192.168.1.101
    python test_my_devices.py --debug-capabilities 192.168.1.100
"""

import argparse
import asyncio
import sys
from typing import Any

from pywiim import WiiMClient


async def test_device_capabilities_debug(ip: str) -> None:
    """Debug capability detection for a device."""
    print(f"\n{'='*60}")
    print(f"Testing capabilities for: {ip}")
    print(f"{'='*60}")

    client = WiiMClient(ip, timeout=5.0)

    try:
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

        print(f"\n✅ Test completed for {ip}")

    except Exception as err:
        print(f"\n❌ Error testing {ip}: {err}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


async def test_device(ip: str) -> dict[str, Any]:
    """Test a single device and return results."""
    print(f"\n{'='*60}")
    print(f"Testing device: {ip}")
    print(f"{'='*60}\n")

    results = {
        "ip": ip,
        "connected": False,
        "device_info": None,
        "capabilities": None,
        "status": None,
        "errors": [],
    }

    client = WiiMClient(ip, timeout=5.0)

    try:
        # Test connection and device info
        print("📋 Getting device information...")
        try:
            device_info = await client.get_device_info_model()
            results["device_info"] = {
                "name": device_info.name,
                "model": device_info.model,
                "firmware": device_info.firmware,
                "mac": device_info.mac,
                "uuid": device_info.uuid,
            }
            results["connected"] = True
            print(f"   ✓ Connected: {device_info.name}")
            print(f"   ✓ Model: {device_info.model}")
            print(f"   ✓ Firmware: {device_info.firmware}")
            print(f"   ✓ MAC: {device_info.mac}")
        except Exception as e:
            results["errors"].append(f"Device info failed: {e}")
            print(f"   ✗ Failed: {e}")
            return results

        # Test capabilities
        print("\n🔧 Detecting capabilities...")
        try:
            caps = client.capabilities
            results["capabilities"] = {
                "vendor": caps.get("vendor"),
                "is_wiim": caps.get("is_wiim_device"),
                "is_legacy": caps.get("is_legacy_device"),
                "generation": caps.get("audio_pro_generation"),
                "supports_presets": caps.get("supports_presets"),
                "supports_eq": caps.get("supports_eq"),
                "supports_multiroom": caps.get("supports_enhanced_grouping"),
            }
            print(f"   ✓ Vendor: {caps.get('vendor')}")
            print(f"   ✓ Type: {'WiiM' if caps.get('is_wiim_device') else 'Legacy'}")
            if caps.get("audio_pro_generation") != "unknown":
                print(f"   ✓ Generation: {caps.get('audio_pro_generation')}")
        except Exception as e:
            results["errors"].append(f"Capability detection failed: {e}")
            print(f"   ✗ Failed: {e}")

        # Test player status
        print("\n📊 Getting player status...")
        try:
            status = await client.get_player_status()
            results["status"] = {
                "play_state": status.get("play_state") or status.get("state"),
                "volume": status.get("volume"),
                "mute": status.get("mute"),
                "source": status.get("source"),
            }
            print(f"   ✓ State: {results['status']['play_state']}")
            print(f"   ✓ Volume: {results['status']['volume']}")
            print(f"   ✓ Source: {results['status']['source']}")
        except Exception as e:
            results["errors"].append(f"Status failed: {e}")
            print(f"   ✗ Failed: {e}")

        # Test features
        print("\n🎯 Testing features...")

        # Test presets
        if client.capabilities.get("supports_presets"):
            try:
                presets = await client.get_presets()
                print(f"   ✓ Presets: {len(presets)} available")
            except Exception as e:
                print(f"   ⚠ Presets: Error - {e}")
        else:
            print("   - Presets: Not supported")

        # Test EQ
        if client.capabilities.get("supports_eq"):
            try:
                eq_presets = await client.get_eq_presets()
                print(f"   ✓ EQ: {len(eq_presets)} presets available")
            except Exception as e:
                print(f"   ⚠ EQ: Error - {e}")
        else:
            print("   - EQ: Not supported")

        # Test multiroom
        try:
            await client.get_multiroom_status()
            print("   ✓ Multiroom: Supported")
        except Exception:
            print("   - Multiroom: Not supported or error")

        print(f"\n✅ Device {ip} test completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        results["errors"].append("Test interrupted")
    except Exception as e:
        results["errors"].append(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
    finally:
        await client.close()

    return results


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test pywiim against real devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--debug-capabilities",
        action="store_true",
        help="Debug capability detection (detailed endpoint testing)",
    )
    parser.add_argument(
        "device_ips",
        nargs="+",
        help="Device IP address(es) to test",
    )

    args = parser.parse_args()

    # Debug capabilities mode
    if args.debug_capabilities:
        if len(args.device_ips) > 1:
            print("⚠️  Debug mode only supports one device at a time")
            sys.exit(1)
        await test_device_capabilities_debug(args.device_ips[0])
        return

    # Normal test mode
    device_ips = args.device_ips

    print(f"\n🧪 Testing {len(device_ips)} device(s)...")
    print(f"   Devices: {', '.join(device_ips)}\n")

    # Test each device
    results = []
    for ip in device_ips:
        result = await test_device(ip)
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}\n")

    successful = sum(1 for r in results if r["connected"])
    print(f"Devices tested: {len(results)}")
    print(f"Successful connections: {successful}/{len(results)}")

    for result in results:
        print(f"\n{result['ip']}:")
        if result["connected"]:
            info = result["device_info"]
            print(f"  ✓ {info['name']} ({info['model']}) - fw: {info['firmware']}")
            if result["capabilities"]:
                caps = result["capabilities"]
                print(f"    Vendor: {caps['vendor']}, Type: {'WiiM' if caps['is_wiim'] else 'Legacy'}")
        else:
            print("  ✗ Connection failed")
            if result["errors"]:
                for error in result["errors"]:
                    print(f"    Error: {error}")

    print(f"\n{'='*60}")
    print("💡 Tip: Run full diagnostics with:")
    print(f"   python -m pywiim.diagnostics {device_ips[0]} --output report.json")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
