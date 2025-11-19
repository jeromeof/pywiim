# Testing Against Real Devices

Guide for testing `pywiim` against your actual WiiM/LinkPlay devices.

## Quick Test Script

We've included a simple test script to quickly test your devices:

```bash
# Test a single device
python test_my_devices.py 192.168.1.100

# Test multiple devices
python test_my_devices.py 192.168.1.100 192.168.1.101
```

This script will:
- Connect to each device
- Get device information
- Detect capabilities
- Test basic features
- Show a summary

## Full Diagnostic Tool

For comprehensive device analysis:

```bash
# Run full diagnostics (using console script)
wiim-diagnostics 192.168.1.100

# Or using Python module
python -m pywiim.cli.diagnostics 192.168.1.100

# Save report to file
wiim-diagnostics 192.168.1.100 --output device-report.json

# Verbose output
wiim-diagnostics 192.168.1.100 --verbose
```

## Integration Tests

Run the full integration test suite:

```bash
# Set device IP
export WIIM_TEST_DEVICE=192.168.1.100

# Run all integration tests
pytest tests/integration/ -v

# Run specific test
pytest tests/integration/test_real_device.py::TestRealDevice::test_device_connection -v

# Skip slow tests (ones that change device state)
pytest tests/integration/ -v -m "not slow"
```

## Finding Your Device IP

### Method 1: Router Admin Panel
- Log into your router's admin panel
- Look for connected devices
- Find your WiiM device by name

### Method 2: Network Scan
```bash
# Using nmap (if installed)
nmap -sn 192.168.1.0/24 | grep -B 2 "WiiM"

# Or use the discovery example in docs/EXAMPLES.md
```

### Method 3: Device Display
- Some WiiM devices show their IP on the display
- Check the device's network settings menu

## Testing Different Device Types

### WiiM Devices (Pro, Mini, Amp, Ultra)
```bash
# Standard HTTP
python test_my_devices.py 192.168.1.100

# Should work with default settings
```

### Audio Pro Devices
```bash
# May require HTTPS on port 4443
wiim-diagnostics 192.168.1.100 --port 4443

# Or test with HTTPS
python -c "
import asyncio
from pywiim import WiiMClient

async def test():
    client = WiiMClient('192.168.1.100', port=4443)
    info = await client.get_device_info_model()
    print(f'Device: {info.name}')
    await client.close()

asyncio.run(test())
"
```

### Arylic Devices
```bash
# Should work with standard HTTP
python test_my_devices.py 192.168.1.100
```

## Common Issues

### Connection Timeout

If you get timeout errors:
- Verify the IP address is correct
- Check device is on the same network
- Try increasing timeout:
  ```python
  client = WiiMClient("192.168.1.100", timeout=10.0)
  ```

### HTTPS Required

Some devices require HTTPS:
```python
client = WiiMClient("192.168.1.100", port=443)
```

### Port Issues

Try different ports:
- 80 (HTTP)
- 443 (HTTPS)
- 4443 (Audio Pro MkII HTTPS)
- 8443 (Alternative HTTPS)

## Test Checklist

When testing a new device, check:

- [ ] Device info retrieval
- [ ] Capability detection
- [ ] Player status
- [ ] Volume control
- [ ] Playback control (play/pause/stop)
- [ ] Presets (if supported)
- [ ] EQ (if supported)
- [ ] Multiroom (if supported)
- [ ] Bluetooth (if supported)
- [ ] Audio settings (if supported)

## Sharing Test Results

If you find issues or want to share test results:

1. Run diagnostics:
   ```bash
   wiim-diagnostics <device_ip> --output report.json
   ```

2. Share the `report.json` file

3. Include:
   - Device model
   - Firmware version
   - What worked
   - What didn't work
   - Error messages

## Next Steps

After testing:
- Review the diagnostic report
- Check capability detection results
- Test specific features you need
- Report any issues with the diagnostic report

