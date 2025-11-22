# Home Assistant Integration Fix Instructions

## Problem

The Home Assistant integration (version 1.0.19+) defaults to `port=443` when creating `WiiMClient`, which causes connection failures for devices that use HTTP on port 80 (like LinkPlay "smart_audio" devices).

## Root Cause

In `custom_components/wiim/coordinator.py`, the `WiiMCoordinator.__init__()` method has:
```python
port: int = 443,  # ❌ Wrong default
```

And in `custom_components/wiim/__init__.py`:
```python
coordinator = WiiMCoordinator(
    hass,
    host=entry.data["host"],
    port=entry.data.get("port", 443),  # ❌ Wrong default
    ...
)
```

## Solution Options

### Option 1: Simple Fix (Recommended)

**Don't pass a port at all** - let pywiim figure it out automatically:

**File: `custom_components/wiim/coordinator.py`**

```python
def __init__(
    self,
    hass: HomeAssistant,
    host: str,
    entry=None,
    capabilities: dict[str, Any] | None = None,
    port: int | None = None,  # ✅ Change default to None
    timeout: int = 10,
) -> None:
    """Initialize the coordinator."""
    # ... existing code ...
    
    # Create pywiim client with HA's session
    client = WiiMClient(
        host=host,
        port=port,  # ✅ Will be None, pywiim will probe automatically
        timeout=timeout,
        session=session,
        capabilities=capabilities,
    )
```

**File: `custom_components/wiim/__init__.py`**

```python
# Remove port from entry.data.get() - just don't pass it
coordinator = WiiMCoordinator(
    hass,
    host=entry.data["host"],
    entry=entry,
    capabilities=capabilities,
    # ✅ Don't pass port - let pywiim probe automatically
    timeout=entry.data.get("timeout", 10),
)
```

### Option 2: Optimized Fix (Optional, for Faster Startup)

**Persist the discovered endpoint** and use it on subsequent startups:

**File: `custom_components/wiim/__init__.py`**

```python
from urllib.parse import urlparse

# ... existing code ...

# Check if we have a cached endpoint
cached_endpoint = entry.data.get("endpoint")
if cached_endpoint:
    # Parse cached endpoint
    parsed = urlparse(cached_endpoint)
    port = parsed.port
    protocol = parsed.scheme
else:
    # First time - let pywiim probe
    port = None
    protocol = None

# Coordinator creates client
coordinator = WiiMCoordinator(
    hass,
    host=entry.data["host"],
    entry=entry,
    capabilities=capabilities,
    port=port,  # ✅ None first time, then cached port
    protocol=protocol,  # ✅ None first time, then cached protocol
    timeout=entry.data.get("timeout", 10),
)

# After first successful refresh, persist discovered endpoint
if not cached_endpoint:
    try:
        await coordinator.async_config_entry_first_refresh()
        discovered = coordinator.player.client.discovered_endpoint
        if discovered:
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, "endpoint": discovered}
            )
            _LOGGER.info(
                "Discovered endpoint for %s: %s (persisted for faster startup)",
                entry.data["host"],
                discovered
            )
    except Exception as e:
        _LOGGER.warning("Could not persist endpoint for %s: %s", entry.data["host"], e)
```

**File: `custom_components/wiim/coordinator.py`**

```python
def __init__(
    self,
    hass: HomeAssistant,
    host: str,
    entry=None,
    capabilities: dict[str, Any] | None = None,
    port: int | None = None,  # ✅ Change default to None
    protocol: str | None = None,  # ✅ Add protocol parameter
    timeout: int = 10,
) -> None:
    """Initialize the coordinator."""
    # ... existing code ...
    
    # Create pywiim client with HA's session
    client = WiiMClient(
        host=host,
        port=port,  # ✅ None or cached port
        protocol=protocol,  # ✅ None or cached protocol
        timeout=timeout,
        session=session,
        capabilities=capabilities,
    )
```

## Testing

After making changes:

1. **Test with a device that uses HTTP on port 80:**
   - Remove the device from HA
   - Re-add it
   - Verify it connects successfully

2. **Test with a device that uses HTTPS on port 443:**
   - Verify it still connects correctly

3. **Test with Option 2 (persistence):**
   - First startup should probe and discover endpoint
   - Restart HA
   - Second startup should use cached endpoint (faster, no probe)

## Migration Notes

- **Existing installations**: Will automatically work after update (pywiim v2.1.6+ handles wrong ports gracefully)
- **New installations**: Will work correctly with either fix option
- **No breaking changes**: Both options are backward compatible

## Related Issues

- GitHub Issue #114: Device not found with new version
- pywiim v2.1.6: Enhanced port/protocol detection with fallback logic

