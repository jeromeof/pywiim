#!/usr/bin/env python3
"""Test queue functionality against real WiiM device.

Usage:
    python scripts/debug/test_queue.py <device_ip>
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from pywiim import Player, WiiMClient
from pywiim.discovery import discover_via_ssdp
from pywiim.upnp.client import UpnpClient


async def test_queue_functionality(host: str) -> None:
    """Test queue functionality on real device."""
    print(f"🔍 Testing queue functionality on {host}...")
    print()

    # Create HTTP client
    client = WiiMClient(host=host)
    upnp_client = None

    try:
        # Get device info first
        print("📱 Getting device info...")
        device_info = await client.get_device_info_model()
        print(f"   Device: {device_info.name}")
        print(f"   Model: {device_info.model}")
        print(f"   Firmware: {device_info.firmware}")

        # Try to discover UPnP description URL
        print()
        print("📡 Discovering UPnP services...")
        devices = await discover_via_ssdp(timeout=3, target=host)

        if not devices:
            print(f"⚠️  No UPnP device found for {host}")
            print("   Trying default description URL...")
            description_url = f"http://{host}:49152/description.xml"
        else:
            device = devices[0]
            description_url = device.location
            print(f"✅ Found UPnP device: {device.name}")
            print(f"   Description URL: {description_url}")

        # Create UPnP client
        print()
        print("🔌 Creating UPnP client...")
        upnp_client = await UpnpClient.create(host, description_url)
        print(f"✅ UPnP client created")
        print(f"   AVTransport: {upnp_client.av_transport is not None}")
        print(f"   RenderingControl: {upnp_client.rendering_control is not None}")
        print(f"   ContentDirectory: {upnp_client.content_directory is not None}")

        # Create Player with UPnP client
        print()
        print("🎵 Creating Player...")
        player = Player(client, upnp_client=upnp_client)
        await player.refresh()
        print(f"✅ Player created: {player.device_name} ({player.play_state})")

        # Test capability properties
        print()
        print("🔧 Capability Properties:")
        print(f"   supports_upnp: {player.supports_upnp}")
        print(f"   supports_queue_add: {player.supports_queue_add}")
        print(f"   supports_queue_browse: {player.supports_queue_browse}")
        print(f"   supports_queue_count: {player.supports_queue_count}")

        # Test HTTP API queue info (always available)
        print()
        print("📊 Queue Info (HTTP API - always available):")
        print(f"   queue_count: {player.queue_count}")
        print(f"   queue_position: {player.queue_position}")

        # Test queue operations if AVTransport is available
        if player.supports_queue_add:
            print()
            print("🎯 Testing Queue Operations (AVTransport)...")

            # Test play_queue (won't actually change anything if queue is empty)
            print()
            print("   Testing play_queue(0)...")
            try:
                await player.play_queue(0)
                print("   ✅ play_queue(0) succeeded")
            except Exception as err:
                print(f"   ⚠️  play_queue(0) failed: {err}")

        # Test queue retrieval if ContentDirectory is available
        if player.supports_queue_browse:
            print()
            print("📋 Testing Queue Retrieval (ContentDirectory)...")
            try:
                queue = await player.get_queue()
                print(f"✅ Queue retrieved: {len(queue)} items")
                print()

                if len(queue) == 0:
                    print("   Queue is empty")
                else:
                    print("   Queue contents (new format):")
                    for item in queue[:5]:  # Show first 5 items
                        pos = item.get("position", "?")
                        title = item.get("title", "Unknown Title")
                        artist = item.get("artist", "Unknown Artist")
                        duration = item.get("duration")
                        duration_str = f" ({duration}s)" if duration else ""
                        print(f"   [{pos}] {title} - {artist}{duration_str}")
                        if item.get("media_content_id"):
                            url = item["media_content_id"]
                            print(f"       URL: {url[:60]}...")
                    if len(queue) > 5:
                        print(f"   ... and {len(queue) - 5} more items")

            except Exception as err:
                print(f"❌ Failed to retrieve queue: {err}")
                import traceback

                traceback.print_exc()
        else:
            print()
            print("ℹ️  ContentDirectory service not available on this device")
            print("   Full queue retrieval requires UPnP ContentDirectory service.")
            print()
            print("   ContentDirectory is only available on:")
            print("   - WiiM Amp (when USB drive is connected)")
            print("   - WiiM Ultra (when USB drive is connected)")
            print()
            print("   Other WiiM devices (Mini, Pro, Pro Plus) function only as UPnP")
            print("   renderers and do not expose ContentDirectory service.")

        # Test other capability properties
        print()
        print("🔧 Other Capabilities:")
        print(f"   supports_eq: {player.supports_eq}")
        print(f"   supports_presets: {player.supports_presets}")
        print(f"   supports_audio_output: {player.supports_audio_output}")
        print(f"   supports_alarms: {player.supports_alarms}")
        print(f"   supports_sleep_timer: {player.supports_sleep_timer}")

    except Exception as err:
        print(f"❌ Error: {err}")
        import traceback

        traceback.print_exc()
    finally:
        # Cleanup
        if upnp_client:
            await upnp_client.close()
        await client.close()


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/debug/test_queue.py <device_ip>")
        print("Example: python scripts/debug/test_queue.py 192.168.1.115")
        sys.exit(1)

    host = sys.argv[1]
    await test_queue_functionality(host)


if __name__ == "__main__":
    asyncio.run(main())
