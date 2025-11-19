#!/usr/bin/env python3
"""Quick test script to verify UPnP events are working.

This script connects to a device and monitors for UPnP events.
It will clearly indicate if events are arriving.

Usage:
    python scripts/test_upnp_events.py <device_ip> [--callback-host <ip>]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime

from pywiim import WiiMClient
from pywiim.upnp.client import UpnpClient
from pywiim.upnp.eventer import UpnpEventer


async def test_upnp_events(device_ip: str, callback_host: str | None = None) -> None:
    """Test UPnP events on a device."""
    print("🧪 UPnP Events Test")
    print("=" * 60)
    print(f"Device: {device_ip}")
    if callback_host:
        print(f"Callback Host: {callback_host}")
    print()

    # Create client
    client = WiiMClient(device_ip)
    
    try:
        # Get device info
        print("📋 Getting device info...")
        device_info = await client.get_device_info_model()
        print(f"   Device: {device_info.name} ({device_info.model})")
        print(f"   UUID: {device_info.uuid}")
        print()

        # Create UPnP client
        print("🔌 Connecting to UPnP services...")
        description_url = f"http://{device_ip}:49152/description.xml"
        upnp_client = await UpnpClient.create(device_ip, description_url, session=None)
        print("   ✅ UPnP client created")
        print()

        # Track events
        event_count = 0
        last_event_time: float | None = None

        def on_event_received():
            nonlocal event_count, last_event_time
            event_count += 1
            last_event_time = time.time()
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] 📡 UPnP Event #{event_count} received!")

        # Create a simple state manager for testing
        class TestStateManager:
            def apply_diff(self, changes: dict) -> bool:
                on_event_received()
                return True

            @property
            def play_state(self):
                return None

        state_manager = TestStateManager()

        # Create eventer
        print("📨 Subscribing to UPnP events...")
        eventer = UpnpEventer(
            upnp_client,
            state_manager,
            device_info.uuid,
            state_updated_callback=on_event_received,
        )

        # Start subscriptions
        await eventer.start(callback_host=callback_host)
        print("   ✅ Subscriptions established")
        print()

        # Check callback URL
        if upnp_client.notify_server:
            callback_url = getattr(upnp_client.notify_server, "callback_url", None)
            server_host = getattr(upnp_client.notify_server, "host", "unknown")
            server_port = getattr(upnp_client.notify_server, "port", "unknown")
            
            print("📡 Callback URL Information:")
            print(f"   Host: {server_host}")
            print(f"   Port: {server_port}")
            if callback_url:
                print(f"   URL: {callback_url}")
            
            # Check if callback URL is reachable
            if server_host == "0.0.0.0":
                print()
                print("   ❌ WARNING: Callback URL uses wildcard binding - may not work!")
            else:
                print()
                print("   ✅ Callback URL appears reachable")
        print()

        print("⏳ Waiting for UPnP events...")
        print("   (Try changing volume, play/pause, or track on the device)")
        print("   Press Ctrl+C to stop")
        print()

        # Monitor for events
        start_time = time.time()
        while True:
            await asyncio.sleep(1)
            
            # Show status every 10 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                if event_count > 0:
                    time_since_last = time.time() - last_event_time if last_event_time else None
                    if time_since_last and time_since_last < 60:
                        print(f"   ✅ {event_count} event(s) received (last {int(time_since_last)}s ago)")
                    else:
                        print(f"   ⚠️  {event_count} event(s) received (last {int(time_since_last)}s ago - may have stopped)")
                else:
                    print(f"   ⏳ No events yet (waiting {elapsed}s)...")

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n📊 Final Results:")
        print(f"   Events received: {event_count}")
        if event_count > 0:
            print("   ✅ UPnP events are working!")
        else:
            print("   ❌ No UPnP events received")
            print("   Possible causes:")
            print("      - Callback URL not reachable from device")
            print("      - Device not sending events")
            print("      - Network/firewall blocking")
            print("      - Try --callback-host to specify a reachable IP address")
        
        await client.close()


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test UPnP events on a WiiM device",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test
  python scripts/test_upnp_events.py 192.168.1.68
  
  # With callback host
  python scripts/test_upnp_events.py 192.168.1.68 --callback-host 192.168.1.254
        """
    )
    parser.add_argument(
        "device_ip",
        help="Device IP address",
    )
    parser.add_argument(
        "--callback-host",
        help="IP address for UPnP callback URL (auto-detected if not specified)",
    )
    
    args = parser.parse_args()
    
    await test_upnp_events(args.device_ip, args.callback_host)


if __name__ == "__main__":
    asyncio.run(main())

