"""Diagnostic tool for WiiM devices.

This module provides a comprehensive diagnostic tool that can be used to gather
device information, test endpoints, and generate reports for troubleshooting.

Usage:
    wiim-diagnostics <device_ip> [--output report.json] [--verbose]
    # or
    python -m pywiim.cli.diagnostics <device_ip> [--output report.json] [--verbose]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any

from ..client import WiiMClient
from ..exceptions import WiiMError

_LOGGER = logging.getLogger(__name__)


class DeviceDiagnostics:
    """Comprehensive diagnostic tool for WiiM devices."""

    def __init__(self, client: WiiMClient) -> None:
        """Initialize diagnostics with a WiiM client.

        Args:
            client: WiiMClient instance connected to device.
        """
        self.client = client
        self.report: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "device": {},
            "capabilities": {},
            "endpoints": {},
            "status": {},
            "errors": [],
            "warnings": [],
        }

    async def run_full_diagnostic(self) -> dict[str, Any]:
        """Run complete diagnostic suite.

        Returns:
            Complete diagnostic report dictionary.
        """
        print("🔍 Starting comprehensive device diagnostic...")
        print(f"   Device: {self.client.host}:{self.client.port}\n")

        # Gather device information
        await self._gather_device_info()
        await self._gather_capabilities()
        await self._gather_status()
        await self._test_endpoints()
        await self._test_features()

        # Summary
        self.report["summary"] = self._generate_summary()

        return self.report

    async def _gather_device_info(self) -> None:
        """Gather basic device information."""
        print("📋 Gathering device information...")
        try:
            device_info = await self.client.get_device_info_model()
            self.report["device"] = {
                "uuid": device_info.uuid,
                "name": device_info.name,
                "model": device_info.model,
                "firmware": device_info.firmware,
                "mac": device_info.mac,
                "ip": device_info.ip,
                "preset_key": device_info.preset_key,
                "input_list": device_info.input_list,
            }
            print(f"   ✓ Device: {device_info.name} ({device_info.model})")
            print(f"   ✓ Firmware: {device_info.firmware}")
            print(f"   ✓ MAC: {device_info.mac}")
        except Exception as err:
            error_msg = f"Failed to get device info: {err}"
            self.report["errors"].append(error_msg)
            print(f"   ✗ {error_msg}")

    async def _gather_capabilities(self) -> None:
        """Gather device capabilities."""
        print("\n🔧 Detecting device capabilities...")
        try:
            if not self.client._capabilities_detected:
                await self.client._detect_capabilities()

            self.report["capabilities"] = self.client.capabilities.copy()

            vendor = self.client.capabilities.get("vendor", "unknown")
            is_wiim = self.client.capabilities.get("is_wiim_device", False)
            is_legacy = self.client.capabilities.get("is_legacy_device", False)
            generation = self.client.capabilities.get("audio_pro_generation", "unknown")

            print(f"   ✓ Vendor: {vendor}")
            print(f"   ✓ Type: {'WiiM' if is_wiim else 'Legacy' if is_legacy else 'Unknown'}")
            if generation != "unknown":
                print(f"   ✓ Generation: {generation}")

            # List supported features
            features = []
            for key, value in self.client.capabilities.items():
                if key.startswith("supports_") and value:
                    feature = key.replace("supports_", "").replace("_", " ")
                    features.append(feature)

            if features:
                print(f"   ✓ Supported features: {', '.join(features)}")

        except Exception as err:
            error_msg = f"Failed to detect capabilities: {err}"
            self.report["errors"].append(error_msg)
            print(f"   ✗ {error_msg}")

    async def _gather_status(self) -> None:
        """Gather current device status."""
        print("\n📊 Gathering device status...")
        try:
            status = await self.client.get_player_status()
            self.report["status"] = {
                "play_state": status.get("play_state") or status.get("state"),
                "volume": status.get("volume"),
                "mute": status.get("mute"),
                "source": status.get("source"),
                "position": status.get("position"),
                "duration": status.get("duration"),
                "title": status.get("title"),
                "artist": status.get("artist"),
                "album": status.get("album"),
            }
            print(f"   ✓ Play state: {self.report['status'].get('play_state')}")
            print(f"   ✓ Volume: {self.report['status'].get('volume')}")
            print(f"   ✓ Source: {self.report['status'].get('source')}")
        except Exception as err:
            error_msg = f"Failed to get status: {err}"
            self.report["errors"].append(error_msg)
            print(f"   ✗ {error_msg}")

    async def _test_endpoints(self) -> None:
        """Test various API endpoints."""
        print("\n🧪 Testing API endpoints...")

        endpoints_to_test = [
            ("getStatusEx", lambda: self.client.get_status()),
            ("getDeviceInfo", lambda: self.client.get_device_info()),
            ("getPlayerStatus", lambda: self.client.get_player_status()),
            ("getPresets", lambda: self.client.get_presets()),
            ("getEQ", lambda: self.client.get_eq()),
            ("getMultiroomStatus", lambda: self.client.get_multiroom_status()),
            ("getAudioOutputStatus", lambda: self.client.get_audio_output_status()),
            ("getFirmwareInfo", lambda: self.client.get_firmware_info()),
        ]

        for name, test_func in endpoints_to_test:
            try:
                result = await test_func()
                self.report["endpoints"][name] = {
                    "status": "success",
                    "result_type": type(result).__name__,
                    "has_data": bool(result),
                }
                print(f"   ✓ {name}: OK")
            except WiiMError as err:
                self.report["endpoints"][name] = {
                    "status": "error",
                    "error": str(err),
                    "error_type": type(err).__name__,
                }
                print(f"   ✗ {name}: {err}")
            except Exception as err:
                self.report["endpoints"][name] = {
                    "status": "error",
                    "error": str(err),
                    "error_type": type(err).__name__,
                }
                self.report["warnings"].append(f"Unexpected error testing {name}: {err}")
                print(f"   ⚠ {name}: {err}")

    async def _test_features(self) -> None:
        """Test specific features and capabilities."""
        print("\n🎯 Testing specific features...")

        features_to_test = [
            ("Presets", self._test_presets),
            ("EQ", self._test_eq),
            ("Multiroom", self._test_multiroom),
            ("Bluetooth", self._test_bluetooth),
            ("Audio Settings", self._test_audio_settings),
            ("LMS Integration", self._test_lms),
            ("Source Selection", self._test_sources),
            ("Audio Output Modes", self._test_audio_output),
        ]

        self.report["features"] = {}

        for name, test_func in features_to_test:
            try:
                result = await test_func()
                self.report["features"][name] = result
                status = "supported" if result.get("supported") else "not supported"
                print(f"   ✓ {name}: {status}")

                # Special handling for source selection to show ALL sources
                if name == "Source Selection" and result.get("supported"):
                    current = result.get("current_source", "None")
                    enumerable_sources = result.get("enumerable_sources", [])
                    all_selectable = result.get("all_selectable_sources", [])
                    print(f"      Current Source: {current}")
                    enumerable_str = (
                        ", ".join(enumerable_sources)
                        if enumerable_sources
                        else "None (device does not return input_list)"
                    )
                    print(f"      Enumerable Sources ({len(enumerable_sources)}): {enumerable_str}")
                    print(f"      All Selectable Sources ({len(all_selectable)}):")
                    if all_selectable:
                        # Print in columns for readability
                        for i, source in enumerate(all_selectable, 1):
                            marker = " ← current" if source == current else ""
                            print(f"         {i:2d}. {source}{marker}")
                    else:
                        print("         (none)")

                # Special handling for audio output modes to show ALL modes
                if name == "Audio Output Modes" and result.get("supported"):
                    current_mode = result.get("current_mode_name", "None")
                    available_modes = result.get("available_modes", [])
                    model = result.get("model", "Unknown")
                    bluetooth_active = result.get("bluetooth_output_active", False)
                    print(f"      Model: {model}")
                    print(f"      Current Mode: {current_mode}")
                    print(f"      Available Output Modes ({len(available_modes)}):")
                    if available_modes:
                        for i, mode in enumerate(available_modes, 1):
                            marker = " ← current" if mode == current_mode else ""
                            print(f"         {i}. {mode}{marker}")
                    else:
                        print("         (none)")
                    if bluetooth_active:
                        print("      ⚠️  Note: Bluetooth output is active (takes precedence over hardware mode)")

                # Special handling for EQ to show ALL presets
                if name == "EQ" and result.get("supported"):
                    current_preset = result.get("current_preset")
                    available_presets = result.get("available_presets", [])
                    print(f"      Current EQ Preset: {current_preset or 'Unknown'}")
                    print(f"      Available EQ Presets ({len(available_presets)}):")
                    if available_presets:
                        for i, preset in enumerate(available_presets, 1):
                            # Check if this is the current preset (handle case variations)
                            is_current = False
                            if current_preset:
                                preset_lower = str(preset).lower()
                                current_lower = str(current_preset).lower()
                                is_current = (
                                    preset_lower == current_lower
                                    or preset_lower in current_lower
                                    or current_lower in preset_lower
                                )
                            marker = " ← current" if is_current else ""
                            print(f"         {i:2d}. {preset}{marker}")
                    else:
                        print("         (none)")

                # Special handling for Presets to show ALL button presets
                if name == "Presets" and result.get("supported"):
                    presets = result.get("presets", [])
                    max_slots = result.get("max_slots", 0)
                    preset_count = result.get("preset_count", 0)
                    print(f"      Button Presets ({preset_count}/{max_slots} slots used):")
                    if presets:
                        for preset in presets:
                            number = preset.get("number", "?")
                            preset_name = preset.get("name", "Unnamed")
                            source = preset.get("source", "Unknown")
                            url = preset.get("url", "")
                            print(f"         Preset {number}: {preset_name} (source: {source})")
                            if url and url not in ["unknow", "unknown", ""]:
                                print(f"                  URL: {url}")
                    else:
                        print("         (no presets configured)")
                    if max_slots > 0 and preset_count < max_slots:
                        print(f"      Available slots: {max_slots - preset_count}")
            except Exception as err:
                self.report["features"][name] = {
                    "supported": False,
                    "error": str(err),
                }
                print(f"   ✗ {name}: {err}")

    async def _test_presets(self) -> dict[str, Any]:
        """Test preset functionality."""
        try:
            presets = await self.client.get_presets()
            max_slots = await self.client.get_max_preset_slots()
            return {
                "supported": True,
                "preset_count": len(presets),
                "max_slots": max_slots,
                "presets": presets,  # Return ALL presets
            }
        except WiiMError:
            return {"supported": False}

    async def _test_eq(self) -> dict[str, Any]:
        """Test EQ functionality."""
        try:
            eq = await self.client.get_eq()
            presets = await self.client.get_eq_presets()
            # Get current preset name from EQ response
            current_preset = None
            if isinstance(eq, dict):
                # Try multiple field names for current preset
                current_preset = eq.get("Name") or eq.get("name") or eq.get("preset") or eq.get("EQPreset")
            return {
                "supported": True,
                "current_preset": current_preset,
                "available_presets": presets,  # Return ALL presets
            }
        except WiiMError:
            return {"supported": False}

    async def _test_multiroom(self) -> dict[str, Any]:
        """Test multiroom functionality."""
        try:
            await self.client.get_multiroom_status()  # Verify multiroom is supported
            slaves = await self.client.get_slaves()
            return {
                "supported": True,
                "is_master": self.client.is_master,
                "is_slave": self.client.is_slave,
                "slave_count": len(slaves) if slaves else 0,
            }
        except WiiMError:
            return {"supported": False}

    async def _test_bluetooth(self) -> dict[str, Any]:
        """Test Bluetooth functionality."""
        try:
            # Just check if we can get Bluetooth status (don't start scan)
            history = await self.client.get_bluetooth_history()
            return {
                "supported": True,
                "history_count": len(history) if history else 0,
            }
        except WiiMError:
            return {"supported": False}

    async def _test_audio_settings(self) -> dict[str, Any]:
        """Test audio settings functionality."""
        try:
            status = await self.client.get_audio_settings_status()
            return {
                "supported": True,
                "has_status": bool(status),
            }
        except WiiMError:
            return {"supported": False}

    async def _test_lms(self) -> dict[str, Any]:
        """Test LMS integration."""
        try:
            state = await self.client.get_squeezelite_state()
            return {
                "supported": True,
                "has_state": bool(state),
            }
        except WiiMError:
            return {"supported": False}

    async def _test_audio_output(self) -> dict[str, Any]:
        """Test audio output mode capabilities."""
        try:
            if not self.client.capabilities.get("supports_audio_output", False):
                return {"supported": False}

            # Get current audio output status
            status = await self.client.get_audio_output_status()
            if not status:
                return {"supported": False}

            # Get device info for model-based mode detection
            device_info = await self.client.get_device_info_model()
            model = device_info.model or "Unknown"

            # Determine available modes (would need Player instance, but we can infer from model)
            # For diagnostics, we'll show what the device reports and model-based inference
            hardware_mode = status.get("hardware")
            bluetooth_source = status.get("source")

            # Model-based available modes (simplified - matches Player logic)
            model_lower = model.lower()
            if "wiim amp" in model_lower:
                available_modes = ["Line Out"]
            elif "wiim mini" in model_lower:
                available_modes = ["Line Out", "Optical Out"]
            elif "wiim ultra" in model_lower:
                available_modes = ["Line Out", "Optical Out", "Coax Out", "Headphone Out", "HDMI Out"]
            elif "wiim pro" in model_lower or "wiim" in model_lower:
                available_modes = ["Line Out", "Optical Out", "Coax Out"]
            else:
                available_modes = ["Line Out", "Optical Out", "Coax Out"]

            # Convert hardware mode to name
            from pywiim.api.constants import AUDIO_OUTPUT_MODE_MAP

            current_mode_name = None
            if hardware_mode is not None:
                try:
                    mode_int = int(hardware_mode)
                    current_mode_name = AUDIO_OUTPUT_MODE_MAP.get(mode_int)
                    # Check if Bluetooth output is active (takes precedence)
                    if bluetooth_source == 1:
                        current_mode_name = "Bluetooth Out"
                except (ValueError, TypeError):
                    pass

            return {
                "supported": True,
                "model": model,
                "current_hardware_mode": hardware_mode,
                "current_mode_name": current_mode_name,
                "bluetooth_output_active": bluetooth_source == 1,
                "available_modes": available_modes,
                "available_mode_count": len(available_modes),
                "raw_status": status,
            }
        except Exception as err:
            return {
                "supported": False,
                "error": str(err),
            }

    async def _test_sources(self) -> dict[str, Any]:
        """Test source enumeration and selection capabilities."""
        from pywiim.api.constants import MODE_MAP

        try:
            # Get enumerable sources (from input_list)
            device_info = await self.client.get_device_info_model()
            enumerable_sources = device_info.input_list or []

            # Get current source
            status = await self.client.get_player_status()
            current_source = status.get("source")

            # Known selectable sources (from MODE_MAP and common services)
            # These are sources that can be selected but may not be in input_list
            known_selectable_sources = [
                "wifi",
                "bluetooth",
                "line_in",
                "optical",
                "coaxial",
                "usb",
                "hdmi",  # Physical inputs
                "spotify",
                "airplay",
                "dlna",
                "amazon",
                "tidal",
                "qobuz",
                "deezer",  # Streaming services
                "iheartradio",
                "pandora",
                "tunein",  # Internet radio
                # Note: Presets are NOT included here - they should be handled via media browser
                #      (use get_presets() to retrieve preset list and play_preset() to play them)
            ]

            # Get all unique values from MODE_MAP (these are selectable)
            mode_map_sources = list(set(MODE_MAP.values()))

            # Combine enumerable + known selectable sources (remove duplicates)
            all_selectable_sources = list(
                dict.fromkeys(enumerable_sources + known_selectable_sources + mode_map_sources)
            )

            # Remove None/empty values
            all_selectable_sources = [s for s in all_selectable_sources if s and s != "idle" and s != "follower"]

            return {
                "supported": True,
                "current_source": current_source,
                "enumerable_sources": enumerable_sources,
                "enumerable_count": len(enumerable_sources),
                "all_selectable_sources": sorted(all_selectable_sources),
                "selectable_count": len(all_selectable_sources),
                "mode_map_sources": sorted([s for s in mode_map_sources if s and s not in ["idle", "follower"]]),
                "distinction": {
                    "enumerable": "Physical inputs reported by device in input_list",
                    "selectable": "All sources that can be switched to (includes services not in input_list)",
                    "note": "Some sources (like streaming services) can be selected but aren't enumerable",
                },
            }
        except Exception as err:
            return {
                "supported": False,
                "error": str(err),
            }

    def _generate_summary(self) -> dict[str, Any]:
        """Generate diagnostic summary."""
        device = self.report.get("device", {})
        capabilities = self.report.get("capabilities", {})
        endpoints = self.report.get("endpoints", {})
        features = self.report.get("features", {})

        successful_endpoints = sum(1 for ep in endpoints.values() if ep.get("status") == "success")
        total_endpoints = len(endpoints)

        supported_features = sum(1 for feat in features.values() if feat.get("supported"))

        return {
            "device_model": device.get("model", "Unknown"),
            "firmware": device.get("firmware", "Unknown"),
            "vendor": capabilities.get("vendor", "unknown"),
            "endpoints_tested": total_endpoints,
            "endpoints_successful": successful_endpoints,
            "features_supported": supported_features,
            "total_features": len(features),
            "errors": len(self.report.get("errors", [])),
            "warnings": len(self.report.get("warnings", [])),
        }

    def print_report(self) -> None:
        """Print human-readable diagnostic report."""
        print("\n" + "=" * 60)
        print("📋 DIAGNOSTIC REPORT SUMMARY")
        print("=" * 60)

        summary = self.report.get("summary", {})
        print(f"\nDevice: {summary.get('device_model')} (Firmware: {summary.get('firmware')})")
        print(f"Vendor: {summary.get('vendor')}")
        print(f"\nEndpoints: {summary.get('endpoints_successful')}/{summary.get('endpoints_tested')} successful")
        print(f"Features: {summary.get('features_supported')}/{summary.get('total_features')} supported")

        if self.report.get("errors"):
            print(f"\n❌ Errors ({len(self.report['errors'])}):")
            for error in self.report["errors"]:
                print(f"   - {error}")

        if self.report.get("warnings"):
            print(f"\n⚠️  Warnings ({len(self.report['warnings'])}):")
            for warning in self.report["warnings"]:
                print(f"   - {warning}")

        print("\n" + "=" * 60)

    async def collect_diagnostic_data(
        self,
        include_endpoint_tests: bool = False,
        include_feature_tests: bool = False,
    ) -> dict[str, Any]:
        """Collect diagnostic data programmatically.

        This method gathers core diagnostic information and optionally includes
        detailed endpoint and feature testing. Useful for programmatic access
        without CLI output.

        Args:
            include_endpoint_tests: If True, test all API endpoints
            include_feature_tests: If True, test specific features

        Returns:
            Complete diagnostic report dictionary.
        """
        # Gather core info
        await self._gather_device_info()
        await self._gather_capabilities()
        await self._gather_status()

        # Optional detailed testing
        if include_endpoint_tests:
            await self._test_endpoints()
        if include_feature_tests:
            await self._test_features()

        # Add API statistics
        try:
            self.report["api_stats"] = self.client.api_stats
        except Exception:
            self.report["api_stats"] = None

        # Add connection statistics
        try:
            self.report["connection_stats"] = self.client.connection_stats
        except Exception:
            self.report["connection_stats"] = None

        # Add multiroom information
        try:
            multiroom = await self.client.get_multiroom_status()
            self.report["multiroom"] = multiroom
        except Exception:
            self.report["multiroom"] = None

        # Add group info
        try:
            group_info = await self.client.get_device_group_info()
            self.report["group_info"] = {
                "role": group_info.role,
                "master_host": group_info.master_host,
                "master_uuid": group_info.master_uuid,
                "slave_hosts": group_info.slave_hosts,
                "slave_count": group_info.slave_count,
            }
        except Exception:
            self.report["group_info"] = None

        # Add EQ settings
        try:
            if self.client.capabilities.get("supports_eq", False):
                eq = await self.client.get_eq()
                self.report["eq"] = eq
            else:
                self.report["eq"] = None
        except Exception:
            self.report["eq"] = None

        # Add audio output status
        try:
            if self.client.capabilities.get("supports_audio_output", False):
                audio_output = await self.client.get_audio_output_status()
                self.report["audio_output"] = audio_output
            else:
                self.report["audio_output"] = None
        except Exception:
            self.report["audio_output"] = None

        # Generate summary
        self.report["summary"] = self._generate_summary()

        return self.report

    def save_report(self, filename: str) -> None:
        """Save diagnostic report to JSON file."""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2, default=str)
        print(f"\n💾 Report saved to: {filename}")


async def main() -> None:
    """Main entry point for diagnostic tool."""
    parser = argparse.ArgumentParser(
        description="WiiM Device Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic diagnostic
  python -m pywiim.diagnostics 192.168.1.100

  # Save report to file
  python -m pywiim.diagnostics 192.168.1.100 --output report.json

  # Verbose output
  python -m pywiim.diagnostics 192.168.1.100 --verbose

  # HTTPS device
  python -m pywiim.diagnostics 192.168.1.100 --port 443
        """,
    )
    parser.add_argument(
        "host",
        help="Device IP address or hostname",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=80,
        help="Device port (default: 80, use 443 for HTTPS)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Save report to JSON file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )

    # Create client and run diagnostics
    client = WiiMClient(host=args.host, port=args.port)
    diagnostics = DeviceDiagnostics(client)

    try:
        await diagnostics.run_full_diagnostic()
        diagnostics.print_report()

        if args.output:
            diagnostics.save_report(args.output)
        else:
            print("\n💡 Tip: Use --output to save full report to JSON file")

    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as err:
        print(f"\n❌ Fatal error: {err}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
    finally:
        await client.close()


def cli_main() -> None:
    """CLI entry point for setuptools script."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
