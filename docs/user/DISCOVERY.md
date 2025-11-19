# Device Discovery

The `pywiim` library includes comprehensive device discovery tools to find WiiM and LinkPlay devices on your network.

## Quick Start

### Command Line Tool

```bash
# Discover all devices (SSDP + network scan)
wiim-discover

# Discover via SSDP only
wiim-discover --methods ssdp

# Discover via network scan only
wiim-discover --methods network_scan

# Scan specific network
wiim-discover --network 192.168.0.0/24

# Output as JSON
wiim-discover --output json

# Save report to file
wiim-discover --output json > devices.json
```

### Python API

```python
import asyncio
from pywiim import discover_devices

async def main():
    # Discover all devices
    devices = await discover_devices()
    
    for device in devices:
        print(f"Found: {device.name} @ {device.ip}")
        print(f"  Model: {device.model}")
        print(f"  Firmware: {device.firmware}")
        print(f"  Vendor: {device.vendor}")

asyncio.run(main())
```

## Discovery Methods

### SSDP/UPnP Discovery

Discovers devices via SSDP (Simple Service Discovery Protocol) and UPnP.

**Advantages**:
- Fast (typically 1-5 seconds)
- Finds devices that advertise via UPnP
- Gets device information from UPnP description
- Optimized filtering: Automatically skips known non-LinkPlay devices (Chromecast, Denon Heos, Sony, Kodi, etc.) before validation for faster discovery

**Limitations**:
- Requires `async-upnp-client` library
- May not find all devices (some don't advertise)
- Network firewall may block SSDP

**Usage**:
```python
from pywiim import discover_via_ssdp

devices = await discover_via_ssdp(timeout=5)
```

### Network Scanning

Scans network IP ranges to find devices by attempting connections.

**Advantages**:
- Finds all devices (even if they don't advertise)
- Works when SSDP is blocked
- Can scan specific network ranges

**Limitations**:
- Slower (must probe each IP)
- More network traffic
- May trigger firewall alerts

**Usage**:
```python
from pywiim import scan_network

devices = await scan_network(
    network="192.168.1.0/24",
    timeout=1.0,
    ports=[80, 443, 4443]
)
```

## Discovery API

### `discover_devices()`

Main discovery function that uses multiple methods.

```python
from pywiim import discover_devices

devices = await discover_devices(
    methods=["ssdp", "network_scan"],  # Methods to use
    validate=True,                      # Validate via API
    network="192.168.1.0/24",          # Network for scanning
    ssdp_timeout=5                      # SSDP timeout
)
```

**Parameters**:
- `methods`: List of methods to use (`["ssdp"]`, `["network_scan"]`, or both)
- `validate`: Whether to validate devices via API (default: `True`)
- `network`: Network CIDR for network scanning (default: `"192.168.1.0/24"`)
- `ssdp_timeout`: SSDP discovery timeout in seconds (default: `5`)

**Returns**: List of `DiscoveredDevice` objects

### `DiscoveredDevice`

Represents a discovered device.

```python
@dataclass
class DiscoveredDevice:
    ip: str                    # IP address
    name: str | None           # Device name
    model: str | None          # Device model
    firmware: str | None       # Firmware version
    mac: str | None           # MAC address
    uuid: str | None          # Device UUID
    port: int                 # Port (80, 443, 4443)
    protocol: str             # "http" or "https"
    vendor: str | None        # "wiim", "arylic", "audio_pro", etc.
    discovery_method: str     # "ssdp", "network_scan", "manual"
    validated: bool           # Whether validated via API
    ssdp_response: dict[str, Any] | None = None  # Internal: SSDP response for filtering
```

**Methods**:
- `to_dict()`: Convert to dictionary
- `__str__()`: String representation

### `validate_device()`

Validate a discovered device by querying its API.

```python
from pywiim import validate_device, DiscoveredDevice

device = DiscoveredDevice(ip="192.168.1.100")
validated_device = await validate_device(device)

# Device now has full information:
# - name, model, firmware, mac, uuid
# - vendor (detected from capabilities)
# - validated = True
```

## Examples

### Discover and List All Devices

```python
import asyncio
from pywiim import discover_devices

async def main():
    print("Discovering devices...")
    devices = await discover_devices()
    
    print(f"\nFound {len(devices)} device(s):\n")
    for i, device in enumerate(devices, 1):
        print(f"{i}. {device.name or 'Unknown'} ({device.model})")
        print(f"   IP: {device.ip}:{device.port}")
        print(f"   Firmware: {device.firmware}")
        print(f"   Vendor: {device.vendor}")
        print()

asyncio.run(main())
```

### Discover and Create Clients

```python
import asyncio
from pywiim import discover_devices, WiiMClient

async def main():
    # Discover devices
    devices = await discover_devices()
    
    # Create clients for all devices
    clients = []
    for device in devices:
        client = WiiMClient(device.ip, port=device.port)
        clients.append(client)
    
    # Use clients
    for client in clients:
        status = await client.get_player_status()
        print(f"{client.host}: {status.get('play_state')}")
        await client.close()

asyncio.run(main())
```

### Discover Specific Network

```python
import asyncio
from pywiim import discover_devices

async def main():
    # Scan office network
    office_devices = await discover_devices(
        methods=["network_scan"],
        network="10.0.0.0/24"
    )
    
    # Scan home network
    home_devices = await discover_devices(
        methods=["ssdp"],
        network="192.168.1.0/24"
    )
    
    print(f"Office: {len(office_devices)} devices")
    print(f"Home: {len(home_devices)} devices")

asyncio.run(main())
```

### Export to JSON

```python
import asyncio
import json
from pywiim import discover_devices

async def main():
    devices = await discover_devices()
    
    # Convert to JSON
    devices_dict = [device.to_dict() for device in devices]
    
    # Save to file
    with open("devices.json", "w") as f:
        json.dump(devices_dict, f, indent=2)
    
    print(f"Exported {len(devices)} devices to devices.json")

asyncio.run(main())
```

## Command Line Tool

### Installation

The `wiim-discover` command is installed automatically with `pywiim`:

```bash
pip install pywiim
```

### Usage

```bash
# Basic discovery
wiim-discover

# SSDP only
wiim-discover --methods ssdp

# Network scan only
wiim-discover --methods network_scan

# Custom network
wiim-discover --network 192.168.0.0/24

# JSON output
wiim-discover --output json

# Skip validation (faster)
wiim-discover --no-validate

# Verbose logging
wiim-discover --verbose
```

### Options

- `--methods`: Discovery methods (`ssdp`, `network_scan`, or both)
- `--network`: Network CIDR for scanning (default: `192.168.1.0/24`)
- `--ssdp-timeout`: SSDP timeout in seconds (default: `5`)
- `--no-validate`: Skip API validation (faster but less info)
- `--output`: Output format (`text` or `json`)
- `--verbose`: Enable verbose logging

## Troubleshooting

### No Devices Found

1. **Check network**: Ensure devices are on the same network
2. **Try network scan**: SSDP may be blocked
   ```bash
   wiim-discover --methods network_scan
   ```
3. **Check firewall**: SSDP uses UDP port 1900
4. **Try manual IP**: If you know the IP, use it directly
   ```python
   from pywiim import validate_device, DiscoveredDevice
   
   device = DiscoveredDevice(ip="192.168.1.100")
   validated = await validate_device(device)
   ```

### SSDP Not Working

If SSDP discovery fails:

1. **Install dependency**: Ensure `async-upnp-client` is installed
   ```bash
   pip install async-upnp-client
   ```
2. **Use network scan**: Fall back to network scanning
3. **Check network**: Ensure devices support UPnP/SSDP

### WSL2 Multicast Issues

If you're running in WSL2 and SSDP discovery doesn't work:

**Problem**: WSL2's default NAT networking mode doesn't support multicast properly, which SSDP requires.

**Solution**: Enable mirrored networking mode:

1. **Create/Edit `.wslconfig`** in your Windows user directory (`C:\Users\<YourUsername>\.wslconfig`):
   ```ini
   [wsl2]
   networkingMode=mirrored
   firewall=false
   ```

2. **Restart WSL** (run in PowerShell or Command Prompt):
   ```powershell
   wsl --shutdown
   ```

3. **Verify Windows Firewall** (run in PowerShell as Administrator):
   ```powershell
   Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
   ```

4. **Test multicast**:
   ```bash
   # In WSL, test if multicast socket works
   python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('', 1900)); s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton('239.255.255.250') + socket.inet_aton('0.0.0.0')); print('Multicast OK')"
   ```

**Note**: Even with mirrored mode, SSDP may still not work perfectly in WSL. Use network scanning as a fallback:
   ```bash
   wiim-discover --methods network_scan
   ```

### Slow Discovery

Network scanning can be slow on large networks:

1. **Use SSDP**: Faster but may miss devices
2. **Limit network range**: Scan smaller subnet
3. **Skip validation**: Use `--no-validate` for faster discovery
4. **Reduce timeout**: Lower `--ssdp-timeout` (may miss devices)

## Integration with Home Assistant

The discovery module can be used in HA integration:

```python
# In config_flow.py
from pywiim import discover_devices

async def async_step_discovery(self):
    devices = await discover_devices(methods=["ssdp"])
    
    # Show discovered devices to user
    options = [f"{d.name} ({d.ip})" for d in devices]
    # ... show form with options
```

## Best Practices

1. **Use SSDP first**: Faster and less network traffic
2. **Fall back to network scan**: If SSDP doesn't find devices
3. **Validate devices**: Always validate to get full information
4. **Cache results**: Discovery can be slow, cache results when possible
5. **Handle errors**: Discovery may fail, handle gracefully

## Performance

- **SSDP**: Typically 1-5 seconds
- **Network scan**: Depends on network size (192.168.1.0/24 ≈ 30-60 seconds)
- **Validation**: ~1 second per device

### Performance Optimization

The discovery system includes automatic optimization to skip validation of known non-LinkPlay devices:

- **Quick filtering**: Uses SSDP `SERVER` headers to identify non-LinkPlay devices (Chromecast, Denon Heos, Sony, Kodi, etc.) before validation
- **Conservative approach**: Only filters devices we're 100% certain are not LinkPlay-compatible
- **Safe fallback**: Generic "Linux" headers (used by Audio Pro, Arylic, WiiM) pass through to validation
- **Performance improvement**: Reduces discovery time by 50-70% when non-LinkPlay devices are present on the network

**Example**: If SSDP discovers 5 devices (4 non-LinkPlay + 1 WiiM):
- **Before optimization**: ~45 seconds (validates all 5 devices)
- **After optimization**: ~13-21 seconds (validates only 1-2 devices)

For best performance:
- Use SSDP when possible (includes automatic filtering)
- Limit network scan range
- Validate devices in parallel
- Cache discovery results

