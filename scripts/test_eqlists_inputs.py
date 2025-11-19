#!/usr/bin/env python3
"""Test script to verify EQ lists and input sources are returned correctly.

This script tests:
1. EQ presets list from EQGetList endpoint
2. Input sources list from getStatusEx endpoint
"""

import asyncio
import logging
import sys
from typing import Any

from pywiim import Player, WiiMClient

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

_LOGGER = logging.getLogger(__name__)


async def test_eq_presets(client: WiiMClient) -> None:
    """Test EQ presets retrieval."""
    print("\n" + "=" * 60)
    print("Testing EQ Presets (EQGetList)")
    print("=" * 60)

    try:
        # Test direct API call
        print("\n1. Direct API call to EQGetList:")
        raw_response = await client._request("/httpapi.asp?command=EQGetList")
        print(f"   Raw response type: {type(raw_response)}")
        print(f"   Raw response: {raw_response}")
        print(f"   Is list? {isinstance(raw_response, list)}")
        print(f"   Is dict? {isinstance(raw_response, dict)}")

        if isinstance(raw_response, dict):
            print(f"   Dict keys: {list(raw_response.keys())}")
            # Check if list is nested in dict
            for key, value in raw_response.items():
                if isinstance(value, list):
                    print(f"   Found list in key '{key}': {value}")

        # Test via get_eq_presets method
        print("\n2. Via get_eq_presets() method:")
        presets = await client.get_eq_presets()
        print(f"   Presets type: {type(presets)}")
        print(f"   Presets: {presets}")
        print(f"   Presets count: {len(presets)}")

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback

        traceback.print_exc()


async def test_input_sources(client: WiiMClient) -> None:
    """Test input sources retrieval."""
    print("\n" + "=" * 60)
    print("Testing Input Sources")
    print("=" * 60)

    try:
        # Test getDeviceInfo endpoint (different from getStatusEx)
        print("\n1. Direct API call to getDeviceInfo:")
        try:
            device_info_response = await client._request("/httpapi.asp?command=getDeviceInfo")
            print(f"   Raw response type: {type(device_info_response)}")
            if isinstance(device_info_response, dict):
                print(f"   Has InputList key? {'InputList' in device_info_response}")
                print(f"   Has inputList key? {'inputList' in device_info_response}")
                print(f"   Has input_list key? {'input_list' in device_info_response}")

                # Check all variations
                input_list = None
                for key in ["InputList", "inputList", "input_list", "inputlist"]:
                    if key in device_info_response:
                        input_list = device_info_response[key]
                        print(f"   Found '{key}': {input_list} (type: {type(input_list)})")
                        break

                if input_list is None:
                    print("   No InputList found in getDeviceInfo")
                    print(f"   Available keys: {list(device_info_response.keys())[:20]}...")
        except Exception as e:
            print(f"   ERROR calling getDeviceInfo: {e}")

        # Test getStatusEx endpoint
        print("\n2. Direct API call to getStatusEx:")
        raw_response = await client._request("/httpapi.asp?command=getStatusEx")
        print(f"   Raw response type: {type(raw_response)}")
        if isinstance(raw_response, dict):
            print(f"   Has InputList key? {'InputList' in raw_response}")
            print(f"   Has inputList key? {'inputList' in raw_response}")
            print(f"   Has input_list key? {'input_list' in raw_response}")

            # Check all variations
            input_list = None
            for key in ["InputList", "inputList", "input_list", "inputlist"]:
                if key in raw_response:
                    input_list = raw_response[key]
                    print(f"   Found '{key}': {input_list} (type: {type(input_list)})")
                    break

            if input_list is None:
                print("   WARNING: No InputList found in response")
                print(f"   Available keys: {list(raw_response.keys())[:20]}...")  # Show first 20 keys

        # Test via get_device_info_model
        print("\n3. Via get_device_info_model() method:")
        device_info = await client.get_device_info_model()
        print(f"   DeviceInfo.input_list type: {type(device_info.input_list)}")
        print(f"   DeviceInfo.input_list: {device_info.input_list}")
        if device_info.input_list:
            print(f"   Input sources count: {len(device_info.input_list)}")

        # Check plm_support (smart detection bitmask)
        print(f"\n   DeviceInfo.plm_support: {device_info.plm_support}")
        if device_info.plm_support is not None:
            print(f"   plm_support type: {type(device_info.plm_support)}")
            # Parse and show what inputs it indicates
            try:
                if isinstance(device_info.plm_support, str):
                    plm_value = (
                        int(device_info.plm_support.replace("0x", "").replace("0X", ""), 16)
                        if "x" in device_info.plm_support.lower()
                        else int(device_info.plm_support)
                    )
                else:
                    plm_value = int(device_info.plm_support)
                print(f"   plm_support value (int): {plm_value}")
                print(f"   plm_support value (hex): 0x{plm_value:x}")
                detected_inputs = []
                if plm_value & (1 << 0):  # bit1: LineIn
                    detected_inputs.append("line_in")
                if plm_value & (1 << 1):  # bit2: Bluetooth
                    detected_inputs.append("bluetooth")
                if plm_value & (1 << 2):  # bit3: USB
                    detected_inputs.append("usb")
                if plm_value & (1 << 3):  # bit4: Optical
                    detected_inputs.append("optical")
                if plm_value & (1 << 5):  # bit6: Coaxial
                    detected_inputs.append("coaxial")
                if plm_value & (1 << 7):  # bit8: LineIn 2
                    detected_inputs.append("line_in_2")
                print(f"   Detected inputs from plm_support: {detected_inputs}")
            except (ValueError, TypeError) as e:
                print(f"   Error parsing plm_support: {e}")

        # Test via Player
        print("\n4. Via Player.available_sources property:")
        player = Player(client)
        await player.refresh()
        available_sources = player.available_sources
        print(f"   Player.available_sources type: {type(available_sources)}")
        print(f"   Player.available_sources: {available_sources}")
        if available_sources:
            print(f"   Available sources count: {len(available_sources)}")

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback

        traceback.print_exc()


async def main() -> None:
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage: python test_eqlists_inputs.py <device_ip>")
        sys.exit(1)

    host = sys.argv[1]
    print(f"Testing device at {host}")

    client = WiiMClient(host=host)

    try:
        # Test EQ presets
        await test_eq_presets(client)

        # Test input sources
        await test_input_sources(client)

        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
