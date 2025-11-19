# API Design Patterns and Defensive Programming

## Overview

This document captures API design patterns, defensive programming strategies, and implementation details learned from the WiiM integration to ensure robust device communication.

## API Reliability Matrix

### ✅ Universal Endpoints (Always Available)

These endpoints work on **all LinkPlay devices** and form the foundation:

| Endpoint                  | Purpose             | Critical Notes                                                                                   |
| ------------------------- | ------------------- | ------------------------------------------------------------------------------------------------ |
| **`getPlayerStatus`**     | Core playback state | **Most critical - always poll this** ⚠️ **Exception: Audio Pro MkII uses `getStatusEx` instead** |
| **`wlanGetConnectState`** | WiFi connection     | Network diagnostics                                                                              |

### ⚠️ WiiM-Enhanced Endpoints (Probe Required)

These endpoints are **WiiM-specific enhancements** that may not exist on pure LinkPlay devices:

| Endpoint          | WiiM Enhancement            | LinkPlay Fallback              | Probe Strategy                            |
| ----------------- | --------------------------- | ------------------------------ | ----------------------------------------- |
| **`getStatusEx`** | Rich device/group info      | Use basic `getStatus`          | Try once, remember result                 |
| **`getMetaInfo`** | Track metadata with artwork | Extract from `getPlayerStatus` | **Critical - many devices don't support** |
| **EQ endpoints**  | Equalizer controls          | None - feature missing         | Disable EQ UI if unsupported              |

### ❌ Highly Inconsistent Endpoints (Use Carefully)

| Endpoint          | Issue                                  | Our Strategy                            |
| ----------------- | -------------------------------------- | --------------------------------------- |
| **`getStatus`**   | **DOESN'T WORK on WiiM devices!**      | Pure LinkPlay only - never rely on this |
| **EQ endpoints**  | Some devices have no EQ support at all | Probe on startup, disable if missing    |
| **`getMetaInfo`** | Missing on many older LinkPlay devices | Always have fallback metadata           |

**🚨 CRITICAL**: `getStatus` (basic LinkPlay endpoint) **does not work** on WiiM devices!

## Defensive Programming Patterns

### 1. Capability Probing

Always test endpoint availability on first connection:

```python
class WiiMClient:
    def __init__(self):
        # Capability flags - None means untested
        self._statusex_supported: bool | None = None
        self._metadata_supported: bool | None = None
        self._eq_supported: bool | None = None

    async def probe_capabilities(self):
        """Test endpoint support once on initial connection"""
        # Test WiiM-enhanced device info
        try:
            await self._get_status_ex()
            self._statusex_supported = True
        except WiiMError:
            self._statusex_supported = False

        # Test metadata support (critical!)
        try:
            await self._get_meta_info()
            self._metadata_supported = True
        except WiiMError:
            self._metadata_supported = False
            logger.warning("Device doesn't support getMetaInfo - no track artwork")
```

### 2. Graceful Fallbacks

Always have fallbacks for unreliable endpoints:

```python
async def get_device_info(self) -> dict:
    """Get device info with WiiM enhancement fallback"""
    if self._statusex_supported:
        try:
            return await self._request(API_ENDPOINT_STATUS)
        except WiiMError:
            self._statusex_supported = False  # Remember failure

    # Fallback to basic LinkPlay
    return await self._request(API_ENDPOINT_PLAYER_STATUS)

async def get_track_metadata(self) -> dict:
    """Get track metadata with basic info fallback"""
    if self._metadata_supported:
        try:
            result = await self._request("/httpapi.asp?command=getMetaInfo")
            if result and result.get("metaData"):
                return result["metaData"]
        except WiiMError:
            self._metadata_supported = False  # Disable forever

    # Fallback: Extract from basic player status
    status = await self.get_player_status()
    return {
        "title": status.get("title", "Unknown Track"),
        "artist": status.get("artist", "Unknown Artist"),
        "album": status.get("album", ""),
        # Note: No artwork available in basic status
    }
```

### 3. Never Fail Hard

Missing advanced features shouldn't break core functionality:

```python
async def get_eq_status(self) -> bool:
    """Return True if the device reports that EQ is enabled.

    Not all firmware builds implement EQGetStat – many return the
    generic {"status":"Failed"} payload instead. In that case we
    fall back to calling EQGetBand: if the speaker answers with a
    valid response (status "OK") we assume that EQ support is present
    and therefore enabled.
    """
    try:
        response = await self._request(API_ENDPOINT_EQ_STATUS)

        # Normal, spec-compliant reply → {"EQStat":"On"|"Off"}
        if "EQStat" in response:
            return str(response["EQStat"]).lower() == "on"

        # Some firmwares return {"status":"Failed"} for unsupported
        # commands – treat this as unknown and use a heuristic.
        if str(response.get("status", "")).lower() == "failed":
            # If EQGetBand succeeds we take that as evidence that the EQ
            # subsystem is operational which implies it is enabled.
            try:
                response = await self._request(API_ENDPOINT_EQ_GET)
                # Verify we got a valid response (not "unknown command")
                if isinstance(response, dict) and response.get("status") == "OK":
                    return True
                return False
            except WiiMError:
                return False

        # Fallback – any other structure counts as EQ disabled.
        return False

    except WiiMError:
        # On explicit request error, still proceed without raising.
        return False
```

## Two-Layer Source System

WiiM devices have a hierarchical source system with enumerable physical inputs and selectable services. See [SOURCE_ENUMERATION_VS_SELECTION.md](SOURCE_ENUMERATION_VS_SELECTION.md) for detailed documentation.

## Group Management API Patterns

### Essential Group Commands

#### Create Master Command
```
setMultiroom:Master
```
- **Purpose**: Makes the current device a multiroom master
- **Target**: Send to the device that should become master

#### Leave Group Command
```
multiroom:SlaveKickout:<slave_ip>
```
- **Purpose**: Removes a slave from the group
- **Target**: Send to the master device's IP
- **Parameters**: `<slave_ip>` - IP address of slave to remove

#### Ungroup Command
```
multiroom:Ungroup
```
- **Purpose**: Disbands the entire group or leaves current group
- **Target**: Send to any device in the group

#### Join Group Command
```
ConnectMasterAp:JoinGroupMaster:eth<master_ip>:wifi0.0.0.0
```
- **Purpose**: Join this device as slave to a master's multiroom group
- **Target**: Send to the **slave device's IP** (using slave's protocol!)
- **Parameters**: `<master_ip>` - IP address of the master device

**🚨 CRITICAL**: Command must be sent **TO the slave device** using **the slave's protocol** (HTTP or HTTPS). Using the master's protocol will cause SSL/connection failures with mixed-protocol devices.

### Group Status Detection

#### Device Role from getStatusEx

```json
{
  "group": "0", // Solo or Master
  "group": "1", // Slave
  "master_uuid": "...", // Present when slave
  "uuid": "...", // Device UUID
  "wmrm_version": "4.2" // WiiM MultiRoom protocol version
}
```

**wmrm_version** indicates the multiroom protocol version:
- **2.0**: Legacy LinkPlay protocol (older devices, Audio Pro Gen 1)
- **4.2**: Current router-based multiroom protocol (WiiM, Audio Pro Gen 2+/W-Gen)

**⚠️ Compatibility**: Devices can only group with matching `wmrm_version` - this is a protocol-level requirement. Devices with version 2.0 cannot join groups with version 4.2 devices.

#### Master's Slaves from getSlaveList

**Correct API Format:**
```json
{
  "slaves": 1, // Integer count (always present)
  "wmrm_version": "4.2",
  "slave_list": [
    // Array of slave objects (when slaves > 0)
    {
      "name": "Master Bedroom",
      "uuid": "FF31F09EFFF1D2BB4FDE2B3F",
      "ip": "192.168.1.116",
      "version": "4.2",
      "type": "WiiMu-A31",
      "channel": 0,
      "volume": 63,
      "mute": 0,
      "battery_percent": 0,
      "battery_charging": 0
    }
  ]
}
```

**Response when no slaves (standalone mode):**
```json
{
  "slaves": 0,
  "wmrm_version": "4.2"
}
```

**Critical Parsing Note:**
- `slaves` is always an integer count, `slave_list` contains the actual slave objects
- Prior implementations incorrectly expected `slaves` to sometimes be a list
- This caused multiroom group detection failures

### Group Role Logic

1. **Slave**: `group == "1"` and has `master_uuid`
2. **Master**: `group == "0"` and `getSlaveList` shows slaves
3. **Solo**: `group == "0"` and no slaves

## Audio Pro Device Considerations

Audio Pro devices (especially MkII generation) have significant API endpoint differences and require special handling. See [DEVICE_VARIATIONS.md](DEVICE_VARIATIONS.md) for comprehensive documentation on vendor-specific variations, endpoint abstraction, and Audio Pro generation differences.

## Best Practices

### DO

- ✅ **Probe capabilities once** - remember results permanently
- ✅ **Use getPlayerStatus as foundation** - universally supported (except Audio Pro MkII)
- ✅ **Implement graceful fallbacks** - for all enhanced features
- ✅ **Log missing capabilities** - for user troubleshooting
- ✅ **Test multiple protocols** - HTTP and HTTPS with fallback ports
- ✅ **Normalize field names** - handle Audio Pro field variations automatically
- ✅ **Send commands to target device** - multiroom join goes TO slave, using slave's protocol

### DO NOT

- ❌ **Assume getMetaInfo works** - many devices don't support it
- ❌ **Require EQ endpoints** - often missing entirely
- ❌ **Use only WiiM API docs** - covers enhanced features only
- ❌ **Fail hard on missing features** - always have fallbacks
- ❌ **Assume HTTP protocol** - Audio Pro MkII+ devices use HTTPS
- ❌ **Expect consistent field names** - Audio Pro uses different field variations
- ❌ **Use master's protocol for slave commands** - each device has its own protocol
- ❌ **Group devices with different wmrm_version** - protocol incompatibility will cause failures

## Timer and Alarm API (WiiM Only)

### Device Support

Alarm clock and sleep timer functionality is **WiiM-specific** and not part of the standard LinkPlay API. Capability detection automatically sets:

```python
capabilities["supports_alarms"] = is_wiim_device
capabilities["supports_sleep_timer"] = is_wiim_device
capabilities["max_alarm_slots"] = 3  # WiiM supports 3 independent alarms
```

### API Documentation

These features are documented in the official WiiM HTTP API specification:
- [WiiM HTTP API PDF](https://www.wiimhome.com/pdf/HTTP%20API%20for%20WiiM%20Mini.pdf) - Section 2.5 (Sleep Timer) and Section 2.6 (Alarm Clock)

### Time Handling

**Critical:** All alarm times use **UTC timezone** per the WiiM API specification. Applications must handle timezone conversion:

```python
# Application handles timezone conversion
from datetime import datetime
import pytz

local_tz = pytz.timezone('America/New_York')
local_time = local_tz.localize(datetime(2025, 1, 17, 7, 30))
utc_time = local_time.astimezone(pytz.UTC)
time_str = utc_time.strftime("%H%M%S")  # Format: HHMMSS

await client.set_alarm(alarm_id=0, trigger=2, operation=1, time=time_str)
```

### Alarm Slot Management

WiiM devices provide 3 independent alarm slots (indices 0-2). Applications can:
- Use slot 0 for single alarm scenarios
- Use all 3 slots for multiple independent alarms
- Track slot usage at application level

### Sleep Timer vs Shutdown

The API endpoint is named `setShutdown`, but it functions as a sleep timer:
- Stops playback after specified seconds
- `0` = immediate shutdown
- `-1` = cancel timer
- Positive value = seconds until playback stops

We name the methods `set_sleep_timer()` / `get_sleep_timer()` for clarity.

### Best Practices

- ✅ Check `capabilities["supports_alarms"]` before using alarm API
- ✅ Check `capabilities["supports_sleep_timer"]` before using sleep timer API
- ✅ Document UTC requirement clearly in user-facing applications
- ✅ Validate alarm_id is 0-2 before calling API
- ✅ Use constants (e.g., `ALARM_TRIGGER_DAILY`) for readability
- ✅ Handle offline devices with `sync_time()` if needed
- ❌ Don't assume these features work on non-WiiM devices
- ❌ Don't convert times to local timezone - API requires UTC
- ❌ Don't use alarm_id > 2 (only 3 slots available)

## Capability Detection and Caching Strategy

### Design Philosophy

The `pywiim` library is **stateless and framework-agnostic**. It does not persist capabilities between sessions. **Applications are responsible for managing capability storage and reuse**.

### Current Implementation

**Library Behavior:**
- Each `WiiMClient` instance has its own in-memory capability cache (per-instance)
- Capabilities are detected automatically on first use if not provided
- Cache is lost when the client instance is destroyed
- Library accepts optional `capabilities` parameter in `__init__` to avoid re-probing

**Key Point**: Creating a new `WiiMClient` instance will probe capabilities again unless you provide them.

### Recommended Design Pattern

**Option 1: Application-Managed Caching (Recommended)**

Applications should detect capabilities once and store them persistently:

```python
# Application code (e.g., Home Assistant integration)
class DeviceManager:
    def __init__(self):
        # Application's persistent storage (config entry, database, etc.)
        self._capabilities_cache: dict[str, dict[str, Any]] = {}
    
    async def get_client(self, host: str, uuid: str) -> WiiMClient:
        """Get or create client with cached capabilities."""
        device_id = f"{host}:{uuid}"
        
        # Check if we have cached capabilities
        capabilities = self._capabilities_cache.get(device_id)
        
        if capabilities:
            # Reuse cached capabilities - no probing needed
            return WiiMClient(host, capabilities=capabilities)
        else:
            # First time - create client, it will probe automatically
            client = WiiMClient(host)
            # After first use, capabilities are detected
            # Store them for next time
            device_info = await client.get_device_info_model()
            await client._detect_capabilities()
            self._capabilities_cache[device_id] = client.capabilities.copy()
            return client
```

**Option 2: Probe on Every Startup (Simple but Slower)**

If you don't need persistent caching, let the library probe each time:

```python
# Simple approach - probe every time
client = WiiMClient("192.168.1.100")
# Capabilities detected automatically on first use
# Accept the ~1-2 second delay on startup
```

**Option 3: Static Detection Only (Fastest, Less Accurate)**

Use static detection (model/firmware-based) without endpoint probing:

```python
from pywiim import WiiMClient, detect_device_capabilities

# Get device info first
client = WiiMClient("192.168.1.100")
device_info = await client.get_device_info_model()

# Static detection (no API calls, instant)
capabilities = detect_device_capabilities(device_info)

# Create new client with static capabilities
client = WiiMClient("192.168.1.100", capabilities=capabilities)
# Note: Static detection may be less accurate than runtime probing
```

### When to Re-Probe Capabilities

**Re-probe when:**
- Firmware version changes (capabilities may change with firmware updates)
- Device model changes (unlikely, but possible if device is replaced)
- User reports missing features (capability detection may have failed)
- After significant time period (firmware may have been updated)

**Don't re-probe when:**
- Same device, same session (use cached capabilities)
- Same device, different application restart (reuse stored capabilities)
- Multiple client instances for same device (share capabilities)

### Capability Storage Recommendations

**For Home Assistant:**
- Store in config entry data (persists across restarts)
- Key: `f"{host}:{uuid}"` or use device UUID
- Update when firmware version changes

**For CLI Tools:**
- Store in local JSON file or user config directory
- Key: device IP or UUID
- Optional: TTL (time-to-live) for automatic re-probing

**For Long-Running Applications:**
- In-memory cache with optional persistence
- Periodic refresh (e.g., once per day)
- Manual refresh option for users

### Library Support

The library provides:

1. **Capability Detection**: `WiiMClient._detect_capabilities()` - Full runtime probing
2. **Static Detection**: `detect_device_capabilities(device_info)` - Fast, model-based
3. **Capability Acceptance**: `WiiMClient(host, capabilities=...)` - Skip probing
4. **Capability Access**: `client.capabilities` - Read detected capabilities

**Example:**
```python
# Detect once, reuse many times
client1 = WiiMClient("192.168.1.100")
await client1._detect_capabilities()  # Probes device
cached_caps = client1.capabilities.copy()

# Reuse in new client instance
client2 = WiiMClient("192.168.1.100", capabilities=cached_caps)
# No probing - instant startup
```

### Best Practice

**Recommended Pattern:**
1. **First connection**: Probe capabilities, store in application's persistent storage
2. **Subsequent connections**: Load from storage, pass to `WiiMClient(..., capabilities=...)`
3. **Periodic refresh**: Re-probe when firmware version changes or after extended period
4. **Error recovery**: If device reports unsupported feature, re-probe capabilities

This gives you:
- ✅ Fast startup (no probing delay)
- ✅ Persistent capabilities (survive restarts)
- ✅ Flexibility (application controls when to probe)
- ✅ Framework-agnostic (library doesn't need to know storage mechanism)

## API Documentation Sources

**Official Documentation**:
- [Arylic LinkPlay API](https://developer.arylic.com/httpapi/) - Core LinkPlay protocol
- [WiiM API PDF](https://www.wiimhome.com/pdf/HTTP%20API%20for%20WiiM%20Products.pdf) - WiiM-specific enhancements
- [OpenAPI Specification](https://github.com/cvdlinden/wiim-httpapi/blob/main/openapi.yaml) - Complete API reference (OpenAPI 3.0 spec)

**OpenAPI Reference**: The [WiiM HTTP API OpenAPI Specification](https://github.com/cvdlinden/wiim-httpapi/blob/main/openapi.yaml) provides a comprehensive, machine-readable reference for all available endpoints, request parameters, and response structures. This is the most complete and up-to-date API documentation available.

