#!/usr/bin/env python3
"""Comprehensive test script for testing pywiim against multiple real devices.

This script runs both core and pre-release integration tests against multiple devices.

Usage:
    # Test specific devices by IP
    python scripts/test_all_devices.py 192.168.1.100 192.168.1.101 192.168.1.102 192.168.1.103 192.168.1.104 192.168.1.105

    # Try to discover devices first, then test them
    python scripts/test_all_devices.py --discover

    # Test with HTTPS
    python scripts/test_all_devices.py --https 192.168.1.100 192.168.1.101 ...

    # Run only core tests (fast, safe)
    python scripts/test_all_devices.py --core-only 192.168.1.100 ...

    # Run only pre-release tests (comprehensive)
    python scripts/test_all_devices.py --prerelease-only 192.168.1.100 ...
"""

import argparse
import asyncio
import os
import subprocess
import sys
from typing import Any

# Ensure output is flushed immediately
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, "reconfigure") else None

from pywiim import discover_devices
from pywiim.client import WiiMClient
from pywiim.exceptions import WiiMConnectionError, WiiMRequestError
from pywiim.player import Player


async def test_device_basic(
    ip: str, port: int = 80, use_https: bool = False, device_num: int = 0, total_devices: int = 0
) -> dict[str, Any]:
    """Test basic connectivity and device info for a device."""
    if device_num > 0:
        print(f"\n{'='*70}")
        print(f"[{device_num}/{total_devices}] Testing Device: {ip}:{port} ({'HTTPS' if use_https else 'HTTP'})")
    else:
        print(f"\n{'='*70}")
        print(f"Testing Device: {ip}:{port} ({'HTTPS' if use_https else 'HTTP'})")
    print(f"{'='*70}")
    sys.stdout.flush()

    result = {
        "ip": ip,
        "port": port,
        "https": use_https,
        "connected": False,
        "device_info": None,
        "capabilities": None,
        "errors": [],
    }

    client = WiiMClient(host=ip, port=port)

    try:
        # Test connection
        print("📋 Connecting and getting device info...")
        sys.stdout.flush()
        try:
            device_info = await client.get_device_info_model()
            result["device_info"] = {
                "name": device_info.name,
                "model": device_info.model,
                "firmware": device_info.firmware,
                "mac": device_info.mac,
                "uuid": device_info.uuid,
            }
            result["connected"] = True
            print(f"   ✓ Connected: {device_info.name}")
            print(f"   ✓ Model: {device_info.model}")
            print(f"   ✓ Firmware: {device_info.firmware}")
            print(f"   ✓ MAC: {device_info.mac}")
            sys.stdout.flush()
        except Exception as e:
            result["errors"].append(f"Connection failed: {e}")
            print(f"   ✗ Failed: {e}")
            sys.stdout.flush()
            return result

        # Get capabilities
        print("\n🔧 Detecting capabilities...")
        sys.stdout.flush()
        try:
            caps = client.capabilities
            result["capabilities"] = {
                "vendor": caps.get("vendor"),
                "is_wiim": caps.get("is_wiim_device"),
                "is_legacy": caps.get("is_legacy_device"),
                "supports_presets": caps.get("supports_presets"),
                "supports_eq": caps.get("supports_eq"),
                "supports_audio_output": caps.get("supports_audio_output"),
                "supports_multiroom": caps.get("supports_enhanced_grouping"),
            }
            print(f"   ✓ Vendor: {caps.get('vendor')}")
            print(f"   ✓ Type: {'WiiM' if caps.get('is_wiim_device') else 'Legacy'}")
            sys.stdout.flush()
        except Exception as e:
            result["errors"].append(f"Capability detection failed: {e}")
            print(f"   ✗ Failed: {e}")
            sys.stdout.flush()

        # Get current state
        print("\n📊 Getting current state...")
        sys.stdout.flush()
        try:
            player = Player(client)
            await player.refresh()

            print(f"   ✓ Play State: {player.play_state}")
            print(f"   ✓ Volume: {player.volume_level}")
            print(f"   ✓ Muted: {player.is_muted}")
            print(f"   ✓ Source: {player.source}")
            if player.media_title:
                print(f"   ✓ Media: {player.media_title}")
            sys.stdout.flush()
        except Exception as e:
            result["errors"].append(f"State retrieval failed: {e}")
            print(f"   ⚠ State retrieval: {e}")
            sys.stdout.flush()

        print(f"\n✅ Basic test completed for {ip}")
        sys.stdout.flush()

    except Exception as e:
        result["errors"].append(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        sys.stdout.flush()
    finally:
        await client.close()

    return result


async def run_pytest_tests(
    device_ips: list[str], use_https: bool = False, core_only: bool = False, prerelease_only: bool = False
) -> dict[str, Any]:
    """Run pytest integration tests against devices."""
    print(f"\n{'='*70}")
    print("Running pytest integration tests...")
    print(f"{'='*70}\n")
    sys.stdout.flush()

    results = {}
    total_devices = len(device_ips)

    for idx, ip in enumerate(device_ips, 1):
        print(f"\n🧪 [{idx}/{total_devices}] Testing {ip} with pytest...")
        sys.stdout.flush()

        # Set environment variables for pytest
        env = os.environ.copy()
        env["WIIM_TEST_DEVICE"] = ip
        if use_https:
            env["WIIM_TEST_HTTPS"] = "true"
        else:
            env["WIIM_TEST_HTTPS"] = "false"

        # Build pytest command
        cmd = ["python", "-m", "pytest", "tests/integration/", "-v", "-m", "integration", "--tb=short"]

        if core_only:
            cmd.extend(["-m", "core and integration"])
        elif prerelease_only:
            cmd.extend(["-m", "prerelease and integration"])

        # Run pytest with real-time output
        try:
            print(f"   Starting pytest (this may take a few minutes)...")
            sys.stdout.flush()

            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Stream output in real-time
            output_lines = []
            passed_count = 0
            failed_count = 0
            current_test = ""

            for line in process.stdout:
                line = line.rstrip()
                output_lines.append(line)

                # Show progress indicators
                if "PASSED" in line or "passed" in line:
                    passed_count += 1
                    if passed_count % 3 == 0:  # Show every 3rd pass
                        print(f"   ✓ {passed_count} tests passed...", end="\r")
                        sys.stdout.flush()
                elif "FAILED" in line or "failed" in line:
                    failed_count += 1
                    print(f"\n   ✗ Test failed: {line[:80]}")
                    sys.stdout.flush()
                elif "test_" in line and "::" in line and "PASSED" not in line and "FAILED" not in line:
                    # Extract test name
                    parts = line.split("::")
                    if len(parts) >= 2:
                        test_name = parts[-1].strip()
                        if len(test_name) > 50:
                            test_name = test_name[:47] + "..."
                        if test_name != current_test:
                            current_test = test_name
                            print(f"   Running: {test_name}...", end="\r")
                            sys.stdout.flush()
                elif "=" * 10 in line and "test session" in line.lower():
                    print(f"\n   Test session starting...")
                    sys.stdout.flush()

            # Wait for process to complete
            returncode = process.wait(timeout=600)  # 10 minute timeout

            # Clear progress line
            print(" " * 80, end="\r")

            results[ip] = {
                "returncode": returncode,
                "stdout": "\n".join(output_lines),
                "stderr": "",
                "success": returncode == 0,
            }

            # Extract summary from output
            output_text = "\n".join(output_lines)
            if "passed" in output_text.lower():
                import re

                passed_match = re.search(r"(\d+)\s+passed", output_text)
                failed_match = re.search(r"(\d+)\s+failed", output_text)
                passed = int(passed_match.group(1)) if passed_match else passed_count
                failed = int(failed_match.group(1)) if failed_match else failed_count
                if failed > 0:
                    print(f"   Results: {passed} passed, {failed} failed")
                else:
                    print(f"   Results: {passed} passed")

            if returncode == 0:
                print(f"   ✅ All tests passed for {ip}")
            else:
                print(f"   ❌ Some tests failed for {ip} (exit code: {returncode})")
                # Print last 15 lines of output for debugging
                lines = output_lines
                if len(lines) > 15:
                    print("\n   Last 15 lines of output:")
                    for line in lines[-15:]:
                        if line.strip():
                            print(f"      {line[:100]}")

        except subprocess.TimeoutExpired:
            if "process" in locals():
                process.kill()
            results[ip] = {
                "returncode": -1,
                "stdout": "",
                "stderr": "Test timeout (10 minutes)",
                "success": False,
            }
            print(f"   ⏱️  Tests timed out for {ip}")
        except Exception as e:
            results[ip] = {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
            }
            print(f"   ❌ Error running tests for {ip}: {e}")

        sys.stdout.flush()

    return results


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test pywiim against multiple real devices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "device_ips",
        nargs="*",
        help="Device IP addresses to test (or use --discover to find devices)",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Try to discover devices on the network first",
    )
    parser.add_argument(
        "--https",
        action="store_true",
        help="Use HTTPS instead of HTTP",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Run only core integration tests (fast, safe)",
    )
    parser.add_argument(
        "--prerelease-only",
        action="store_true",
        help="Run only pre-release integration tests (comprehensive)",
    )
    parser.add_argument(
        "--skip-basic",
        action="store_true",
        help="Skip basic connectivity tests, only run pytest",
    )
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Skip pytest tests, only run basic connectivity tests",
    )

    args = parser.parse_args()

    # Get device IPs
    device_ips = list(args.device_ips)

    # Try discovery if requested or no IPs provided
    if args.discover or len(device_ips) == 0:
        print("🔍 Discovering devices on network...")
        try:
            discovered = await discover_devices()
            if discovered:
                print(f"\nFound {len(discovered)} device(s):")
                for i, device in enumerate(discovered, 1):
                    print(f"  {i}. {device.name or 'Unknown'} ({device.model}) @ {device.ip}:{device.port}")

                if len(device_ips) == 0:
                    # Use discovered devices
                    device_ips = [device.ip for device in discovered]
                    print(f"\n✅ Using {len(device_ips)} discovered device(s) for testing")
                else:
                    # Merge with provided IPs (avoid duplicates)
                    discovered_ips = {device.ip for device in discovered}
                    for ip in args.device_ips:
                        if ip not in discovered_ips:
                            device_ips.append(ip)
                    print(
                        f"\n✅ Using {len(device_ips)} device(s) ({len(discovered)} discovered + {len(args.device_ips)} provided)"
                    )
            else:
                print("⚠️  No devices discovered via SSDP")
                if len(device_ips) == 0:
                    print("❌ No devices to test. Please provide IP addresses or ensure devices are discoverable.")
                    return 1
        except Exception as e:
            print(f"⚠️  Discovery failed: {e}")
            if len(device_ips) == 0:
                print("❌ No devices to test. Please provide IP addresses.")
                return 1

    if len(device_ips) == 0:
        print("❌ No devices to test. Please provide IP addresses or use --discover.")
        return 1

    print(f"\n🎯 Testing {len(device_ips)} device(s): {', '.join(device_ips)}")

    port = 443 if args.https else 80

    # Run basic connectivity tests
    basic_results = []
    if not args.skip_basic:
        print(f"\n{'='*70}")
        print("PHASE 1: Basic Connectivity Tests")
        print(f"{'='*70}")
        sys.stdout.flush()

        total = len(device_ips)
        for idx, ip in enumerate(device_ips, 1):
            result = await test_device_basic(ip, port=port, use_https=args.https, device_num=idx, total_devices=total)
            basic_results.append(result)

        # Summary
        print(f"\n{'='*70}")
        print("Basic Connectivity Summary")
        print(f"{'='*70}")
        successful = sum(1 for r in basic_results if r["connected"])
        print(f"Devices tested: {len(basic_results)}")
        print(f"Successful connections: {successful}/{len(basic_results)}")

        for result in basic_results:
            print(f"\n{result['ip']}:")
            if result["connected"]:
                info = result["device_info"]
                print(f"  ✅ {info['name']} ({info['model']}) - FW: {info['firmware']}")
            else:
                print("  ❌ Connection failed")
                for error in result["errors"]:
                    print(f"    Error: {error}")

    # Run pytest integration tests
    pytest_results = {}
    if not args.skip_pytest:
        print(f"\n{'='*70}")
        print("PHASE 2: Pytest Integration Tests")
        print(f"{'='*70}")

        pytest_results = await run_pytest_tests(
            device_ips,
            use_https=args.https,
            core_only=args.core_only,
            prerelease_only=args.prerelease_only,
        )

        # Summary
        print(f"\n{'='*70}")
        print("Pytest Integration Tests Summary")
        print(f"{'='*70}")
        successful = sum(1 for r in pytest_results.values() if r["success"])
        print(f"Devices tested: {len(pytest_results)}")
        print(f"Successful test runs: {successful}/{len(pytest_results)}")

        for ip, result in pytest_results.items():
            print(f"\n{ip}:")
            if result["success"]:
                print("  ✅ All tests passed")
            else:
                print(f"  ❌ Tests failed (return code: {result['returncode']})")

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")

    if not args.skip_basic:
        basic_success = sum(1 for r in basic_results if r["connected"])
        print(f"Basic connectivity: {basic_success}/{len(basic_results)} devices")

    if not args.skip_pytest:
        pytest_success = sum(1 for r in pytest_results.values() if r["success"])
        print(f"Pytest integration: {pytest_success}/{len(pytest_results)} devices")

    # Return exit code
    all_success = True
    if not args.skip_basic:
        all_success = all_success and all(r["connected"] for r in basic_results)
    if not args.skip_pytest:
        all_success = all_success and all(r["success"] for r in pytest_results.values())

    return 0 if all_success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
