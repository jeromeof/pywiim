# Quick Start Guide

Get started with `pywiim` in 5 minutes.

## Installation

```bash
pip install pywiim
```

## Your First Script

Create a file `test_device.py`:

```python
import asyncio
from pywiim import WiiMClient

async def main():
    # Replace with your device IP
    client = WiiMClient("192.168.1.100")
    
    try:
        # Get device info
        info = await client.get_device_info_model()
        print(f"Connected to: {info.name}")
        print(f"Model: {info.model}")
        print(f"Firmware: {info.firmware}")
        
        # Get current status
        status = await client.get_player_status()
        print(f"\nCurrent Status:")
        print(f"  State: {status.get('play_state')}")
        print(f"  Volume: {status.get('volume', 0):.0%}")
        print(f"  Source: {status.get('source')}")
        
        # Control playback
        print("\nSetting volume to 50%...")
        await client.set_volume(0.5)
        
        print("Starting playback...")
        await client.play()
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python test_device.py
```

## Common Tasks

### Get Device Information

```python
client = WiiMClient("192.168.1.100")
info = await client.get_device_info_model()
print(f"{info.name} - {info.model} (fw: {info.firmware})")
await client.close()
```

### Control Volume

```python
# Set volume to 50%
await client.set_volume(0.5)

# Mute
await client.set_mute(True)

# Unmute
await client.set_mute(False)
```

### Control Playback

```python
await client.play()
await client.pause()
await client.stop()
await client.next_track()
await client.previous_track()
```

### Play a Preset

```python
# Get available presets
presets = await client.get_presets()
print(f"Available presets: {[p.get('name') for p in presets]}")

# Play preset #1
await client.play_preset(1)
```

### Check Capabilities

```python
# Capabilities are auto-detected
info = await client.get_device_info_model()

# Check what's supported
caps = client.capabilities
if caps.get("supports_presets"):
    presets = await client.get_presets()
if caps.get("supports_eq"):
    eq_presets = await client.get_eq_presets()
```

## Next Steps

- Read [API Reference](../integration/API_REFERENCE.md) for complete API documentation
- Check [Examples](EXAMPLES.md) for more code examples
- See [DIAGNOSTICS.md](DIAGNOSTICS.md) for troubleshooting

