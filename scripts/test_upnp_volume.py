#!/usr/bin/env python3
"""Test UPnP GetVolume implementation against real devices.

Tests:
- Lazy UPnP client creation
- UPnP GetVolume vs HTTP volume
- Fallback behavior
- Grouped device scenarios
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pywiim import Player, WiiMClient

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_LOGGER = logging.getLogger(__name__)


async def test_device(host: str) -> None:
    """Test UPnP GetVolume on a single device."""
    print(f"\n{'='*60}")
    print(f"Testing device: {host}")
    print(f"{'='*60}")

    try:
        # Create client and player (no UPnP client initially)
        client = WiiMClient(host=host)
        player = Player(client, upnp_client=None)  # Explicitly None to test lazy creation

        print(f"\n1. Initial state:")
        print(f"   UPnP client: {player._upnp_client}")
        print(f"   UPnP client creation attempted: {player._state_mgr._upnp_client_creation_attempted}")

        # First refresh - should trigger lazy UPnP client creation
        print(f"\n2. Calling refresh() (should trigger lazy UPnP client creation)...")
        await player.refresh(full=True)

        print(f"\n3. After refresh:")
        print(f"   UPnP client: {player._upnp_client is not None}")
        if player._upnp_client:
            print(f"   AVTransport: {player._upnp_client.av_transport is not None}")
            print(f"   RenderingControl: {player._upnp_client.rendering_control is not None}")
        print(f"   UPnP client creation attempted: {player._state_mgr._upnp_client_creation_attempted}")

        # Check volume from different sources
        print(f"\n4. Volume comparison:")
        volume_level = player.volume_level
        print(f"   player.volume_level: {volume_level}")

        # Try direct UPnP GetVolume if available
        if player._upnp_client and player._upnp_client.rendering_control:
            try:
                upnp_volume = await player._upnp_client.get_volume()
                print(f"   UPnP GetVolume: {upnp_volume} ({upnp_volume / 100.0 if upnp_volume else None})")
            except Exception as err:
                print(f"   UPnP GetVolume failed: {err}")

        # Check HTTP volume from status
        if player._status_model:
            http_volume = player._status_model.volume
            print(f"   HTTP volume (from status): {http_volume} ({http_volume / 100.0 if http_volume else None})")

        # Check state synchronizer
        merged = player._state_synchronizer.get_merged_state()
        sync_volume = merged.get("volume")
        print(f"   StateSynchronizer volume: {sync_volume} ({sync_volume / 100.0 if sync_volume else None})")

        # Check if grouped
        print(f"\n5. Group status:")
        print(f"   Role: {player.role}")
        print(f"   Group: {player.group is not None}")
        if player.group:
            print(f"   Group volume_level: {player.group.volume_level}")
            print(f"   Slaves: {len(player.group.slaves)}")

        # Test volume change
        print(f"\n6. Testing volume change...")
        current_vol = player.volume_level
        if current_vol is not None:
            # Change volume slightly
            new_vol = min(1.0, current_vol + 0.05) if current_vol < 0.95 else max(0.0, current_vol - 0.05)
            print(f"   Setting volume from {current_vol:.2f} to {new_vol:.2f}")
            await player.set_volume(new_vol)
            await asyncio.sleep(0.5)  # Brief pause

            # Refresh and check
            await player.refresh(full=False)
            updated_vol = player.volume_level
            print(f"   Volume after change: {updated_vol}")

            # Restore original
            print(f"   Restoring volume to {current_vol:.2f}")
            await player.set_volume(current_vol)
            await asyncio.sleep(0.5)

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
    """Test all devices."""
    devices = ["192.168.1.115", "192.168.6.95", "192.168.6.50"]

    print("Testing UPnP GetVolume implementation")
    print("=" * 60)

    for host in devices:
        await test_device(host)
        await asyncio.sleep(1)  # Brief pause between devices

    print(f"\n{'='*60}")
    print("All tests completed")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
