"""Command-line tool for discovering WiiM/LinkPlay devices."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from ..discovery import DiscoveredDevice


def format_device_report(device: DiscoveredDevice) -> str:
    """Format device information as a readable report."""
    lines = [
        f"Device: {device.name or 'Unknown'}",
        f"  IP Address: {device.ip}:{device.port}",
        f"  Protocol: {device.protocol.upper()}",
    ]

    if device.model:
        lines.append(f"  Model: {device.model}")
    if device.firmware:
        lines.append(f"  Firmware: {device.firmware}")
    if device.mac:
        lines.append(f"  MAC Address: {device.mac}")
    if device.uuid:
        lines.append(f"  UUID: {device.uuid}")
    if device.vendor:
        lines.append(f"  Vendor: {device.vendor}")
    if device.discovery_method:
        lines.append(f"  Discovered via: {device.discovery_method}")
    if device.validated:
        lines.append("  Status: Validated ✓")
    else:
        lines.append("  Status: Not validated")

    return "\n".join(lines)


async def main() -> int:
    """Main entry point for discovery CLI."""
    parser = argparse.ArgumentParser(
        description="Discover WiiM and LinkPlay devices on your network",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover devices via SSDP (default)
  wiim-discover

  # Output as JSON
  wiim-discover --output json

  # Save report to file
  wiim-discover --output report.json
        """,
    )

    parser.add_argument(
        "--ssdp-timeout",
        type=int,
        default=5,
        help="SSDP discovery timeout in seconds (default: 5)",
    )

    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip API validation of discovered devices",
    )

    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    import logging

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        print("🔍 Discovering WiiM/LinkPlay devices via SSDP...")
        print()

        # Discover devices via SSDP (like HA integration)
        devices = []
        try:
            import asyncio

            from pywiim.discovery import discover_via_ssdp, validate_device

            ssdp_devices = await discover_via_ssdp(timeout=args.ssdp_timeout)
            if ssdp_devices:
                print(f"✅ Found {len(ssdp_devices)} device(s):\n")
                for i, device in enumerate(ssdp_devices, 1):
                    print(f"  {i}. {device.name or 'Unknown'} @ {device.ip}:{device.port}")
                print()

                # Validate if requested
                if not args.no_validate:
                    print("Validating devices...")
                    validation_tasks = [validate_device(device) for device in ssdp_devices]
                    ssdp_devices = await asyncio.gather(*validation_tasks)

                devices.extend(ssdp_devices)

        except KeyboardInterrupt:
            print("\n\n⚠️  Discovery interrupted by user")
            if devices:
                print(f"\nShowing {len(devices)} device(s) found before interruption:\n")
            else:
                return 1

        if not devices:
            print("❌ No devices found")
            return 1

        # Output results
        if args.output == "json":
            # JSON output
            devices_dict = [device.to_dict() for device in devices]
            print(json.dumps(devices_dict, indent=2))
        else:
            # Text output
            print(f"✅ Found {len(devices)} device(s):\n")
            for i, device in enumerate(devices, 1):
                print(f"{'=' * 60}")
                print(f"Device {i}/{len(devices)}")
                print(f"{'=' * 60}")
                print(format_device_report(device))
                print()

            # Summary
            print(f"{'=' * 60}")
            print("Summary")
            print(f"{'=' * 60}")
            print(f"Total devices: {len(devices)}")
            validated = sum(1 for d in devices if d.validated)
            print(f"Validated: {validated}/{len(devices)}")

            # Group by vendor
            vendors: dict[str, int] = {}
            for device in devices:
                vendor = device.vendor or "unknown"
                vendors[vendor] = vendors.get(vendor, 0) + 1

            if vendors:
                print("\nBy vendor:")
                for vendor, count in sorted(vendors.items()):
                    print(f"  {vendor}: {count}")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Discovery interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Discovery failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def cli_main() -> None:
    """CLI entry point."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_main()
