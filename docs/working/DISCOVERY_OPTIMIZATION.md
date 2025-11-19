# Discovery Performance Optimization

## Problem Statement

Discovery is slow because it validates every SSDP-discovered device, even non-WiiM devices. From the logs:

1. **SSDP discovery is fast** (~5 seconds) - finds 5 devices quickly
2. **Validation is slow** (~40+ seconds) - tries to connect to each device and test many protocol/port combinations
3. **Non-WiiM devices waste time** - Chromecast, Denon Heos, Sony devices, etc. are validated every time
4. **Same devices discovered repeatedly** - On each discovery run, the same non-WiiM devices are validated again

## Current Flow

```
SSDP Discovery (5s) → Find 5 devices → Validate all 5 (40s) → Filter to 0 WiiM devices
```

**Time breakdown:**
- SSDP: ~5 seconds ✅ Fast
- Validation per device: ~8-15 seconds ❌ Slow
- Total: ~45 seconds for 5 devices

## Design Principle: Library vs Application Responsibility

**Key Insight:** The library should be **stateless and framework-agnostic**. Caching/persistence is an **application concern**, not a library concern.

- **Library responsibility:** Make discovery fast and efficient (quick filtering, smart validation)
- **Application responsibility:** Cache/persist discovery results if needed (config entries, database, etc.)

This matches how other libraries work (e.g., vellemon linkplay, HA integration patterns).

## Proposed Solution: Quick Filtering (No Caching)

Instead of caching, the library should **quickly filter out known non-WiiM devices** before validation using SSDP response headers.

**Idea:** Use SSDP response headers to identify non-WiiM devices before validation. This is pure library logic - no persistence needed.

**SSDP Headers to Check:**
- `SERVER` field - Contains device/server info
  - Chromecast: `Linux/4.19.260-ab681001, UPnP/1.0, Chromecast/1.6.18`
  - Denon Heos: `LINUX UPnP/1.0 Denon-Heos/...`
  - Sony: `FedoraCore/2 UPnP/1.0 MINT-X/1.8.1`
  - Kodi: `KnOS/3.2 UPnP/1.0 DMP/3.5`
  - **WiiM/Audio Pro/Arylic**: `Linux` (generic - these will pass through filter)

**⚠️ CRITICAL: Conservative Filtering**

We must be **very conservative** - only filter devices we're **100% certain** are not LinkPlay-compatible. Audio Pro, Arylic, and other LinkPlay devices likely use generic "Linux" SERVER headers and must NOT be filtered.

**Implementation:**
```python
# Known non-LinkPlay server patterns (ONLY devices we're CERTAIN are not LinkPlay)
# These patterns are specific to non-LinkPlay devices that clearly identify themselves
NON_LINKPLAY_SERVER_PATTERNS = [
    "Chromecast",      # Google Chromecast - definitely not LinkPlay
    "Denon-Heos",      # Denon Heos - definitely not LinkPlay
    "MINT-X",          # Sony devices - definitely not LinkPlay
    "KnOS",            # Kodi/OSMC - definitely not LinkPlay
    # Add more ONLY if we're 100% certain they're not LinkPlay-compatible
    # DO NOT add generic patterns like "Linux" - Audio Pro uses this!
]

def is_likely_non_linkplay(ssdp_response: dict) -> bool:
    """Quick check if device is likely not a LinkPlay device based on SSDP headers.
    
    ⚠️ CONSERVATIVE: Only filters devices we're 100% certain are not LinkPlay.
    Audio Pro, Arylic, and other LinkPlay devices use generic "Linux" headers
    and will pass through this filter (which is correct - they need validation).
    
    Returns True if device is CERTAINLY not a LinkPlay device.
    """
    server = ssdp_response.get("SERVER", "").upper()
    return any(pattern.upper() in server for pattern in NON_LINKPLAY_SERVER_PATTERNS)
```

**Flow:**
```
SSDP Discovery → Quick Filter (SSDP headers) → Skip known non-WiiM
                ↓
            Validate remaining devices → Return only validated WiiM devices
```

**Benefits:**
- Very fast (no network requests for filtering)
- Reduces validation load significantly
- No persistence needed (stateless library)
- Framework-agnostic (applications handle their own caching if needed)

## Implementation Plan

### 1. Store SSDP Response in DiscoveredDevice

**Modify `DiscoveredDevice` to store SSDP response data:**

```python
@dataclass
class DiscoveredDevice:
    """Represents a discovered WiiM/LinkPlay device."""
    
    ip: str
    name: str | None = None
    model: str | None = None
    firmware: str | None = None
    mac: str | None = None
    uuid: str | None = None
    port: int = 80
    protocol: str = "http"  # "http" or "https"
    vendor: str | None = None
    discovery_method: str = "unknown"
    validated: bool = False
    ssdp_response: dict[str, Any] | None = None  # Store SSDP response for filtering
```

### 2. Quick Filter Function

```python
# Known non-WiiM server patterns (from SSDP SERVER header)
NON_WIIM_SERVER_PATTERNS = [
    "Chromecast",
    "Denon-Heos",
    "MINT-X",  # Sony
    "KnOS",    # Kodi
    # Add more as discovered
]

def is_likely_non_wiim(ssdp_response: dict[str, Any]) -> bool:
    """Quick check if device is likely not a WiiM based on SSDP headers.
    
    This is a fast, stateless check that doesn't require network requests.
    Returns True if device is likely NOT a WiiM device.
    """
    server = ssdp_response.get("SERVER", "").upper()
    return any(pattern.upper() in server for pattern in NON_WIIM_SERVER_PATTERNS)
```

### 3. Integration with Discovery

**Modify `discover_via_ssdp()` to store SSDP response:**

```python
async def discover_via_ssdp(...) -> list[DiscoveredDevice]:
    # ... existing code ...
    
    async def process_response(response: dict[str, Any]) -> None:
        # ... existing extraction code ...
        
        device = DiscoveredDevice(
            ip=ip,
            name=name,
            model=None,
            uuid=uuid,
            port=port,
            protocol=protocol,
            discovery_method="ssdp",
            ssdp_response=response,  # Store full SSDP response
        )
        
        devices.append(device)
```

**Modify `discover_devices()` to apply quick filter:**

```python
async def discover_devices(
    methods: list[str] | None = None,
    validate: bool = True,
    ssdp_timeout: int = 5,
) -> list[DiscoveredDevice]:
    """Discover WiiM/LinkPlay devices via SSDP/UPnP."""
    
    # SSDP discovery
    ssdp_devices = await discover_via_ssdp(timeout=ssdp_timeout)
    
    # Quick filter: Skip known non-LinkPlay devices before validation
    # ⚠️ CONSERVATIVE: Only filters devices we're 100% certain are not LinkPlay
    devices_to_validate = []
    for device in ssdp_devices:
        if device.ssdp_response and is_likely_non_linkplay(device.ssdp_response):
            _LOGGER.debug("Skipping known non-LinkPlay device: %s (SERVER: %s)", 
                         device.ip, device.ssdp_response.get("SERVER", "unknown"))
            continue
        
        # Device passes filter - will be validated (Audio Pro, Arylic, WiiM, etc.)
        devices_to_validate.append(device)
    
    # Validate remaining devices
    if validate:
        validation_tasks = [validate_device(device) for device in devices_to_validate]
        validated_devices = await asyncio.gather(*validation_tasks)
        return [device for device in validated_devices if device.validated]
    
    return devices_to_validate
```

## Benefits

1. **Faster discovery** - Skip validation for known non-WiiM devices (no network requests needed)
2. **Reduced network traffic** - Fewer HTTP requests during discovery
3. **Better user experience** - Discovery completes in seconds instead of minutes
4. **Stateless library** - No persistence complexity, framework-agnostic
5. **Application flexibility** - Applications can implement their own caching if needed

## Expected Performance Improvement

**Before:**
- SSDP: ~5 seconds
- Validation: ~40 seconds (5 devices × 8 seconds each)
- **Total: ~45 seconds**

**After (with quick filtering):**
- SSDP: ~5 seconds
- Quick filter: <1 second (in-memory pattern matching)
- Validation: ~8-16 seconds (1-2 devices × 8 seconds each, instead of 5)
- **Total: ~13-21 seconds** (50-70% faster)

## Edge Cases & Safety Considerations

### ⚠️ CRITICAL: Audio Pro Device Safety

**Audio Pro devices are LinkPlay-compatible and MUST NOT be filtered.**

- **Audio Pro SSDP headers:** Likely use generic `Linux` SERVER header (same as WiiM)
- **Risk:** If we filter too aggressively, Audio Pro devices could be incorrectly excluded
- **Solution:** Only filter devices with **specific, non-LinkPlay identifiers** (Chromecast, Denon-Heos, etc.)
- **Safety:** Generic "Linux" headers pass through filter → validation happens → Audio Pro devices are correctly identified

### Edge Cases

1. **False positives (CRITICAL)** - Incorrectly filtering LinkPlay devices
   - **Risk:** Audio Pro, Arylic, or other LinkPlay devices filtered out
   - **Solution:** Be VERY conservative - only filter devices with specific non-LinkPlay identifiers
   - **Fallback:** Validation still happens for devices that pass the filter
   - **Principle:** Better to validate too many devices than to miss a LinkPlay device

2. **False negatives (Acceptable)** - Some non-LinkPlay devices pass the filter
   - **Impact:** These devices will be validated (slower, but safe)
   - **Solution:** This is acceptable - they'll be caught during validation and filtered out
   - **Trade-off:** Better to be conservative than to incorrectly filter LinkPlay devices

3. **Pattern maintenance** - Need to update patterns as new devices are discovered
   - **Solution:** Patterns are in code, easy to update
   - **Rule:** Only add patterns for devices we're 100% certain are not LinkPlay
   - **Future:** Could make patterns configurable if needed

### Testing Requirements

**Before implementing, verify:**
1. ✅ Audio Pro devices (all generations) pass through filter
2. ✅ Arylic devices pass through filter  
3. ✅ WiiM devices pass through filter
4. ✅ Generic "Linux" headers pass through filter
5. ✅ Only specific non-LinkPlay devices are filtered

## Application-Level Caching (Optional)

**For applications that want to cache discovery results:**

Applications can implement their own caching using the discovery results:

```python
# Example: CLI tool caching
import json
from pathlib import Path

def load_discovery_cache() -> dict:
    cache_file = Path.home() / ".config" / "wiim-discover" / "cache.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    return {}

def save_discovery_cache(devices: list[DiscoveredDevice]):
    cache_file = Path.home() / ".config" / "wiim-discover" / "cache.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache = {d.ip: d.to_dict() for d in devices}
    cache_file.write_text(json.dumps(cache, indent=2))

# Usage
cache = load_discovery_cache()
# Filter devices based on cache before calling discover_devices()
# ... application-specific caching logic ...
devices = await discover_devices()
save_discovery_cache(devices)
```

**For Home Assistant integration:**
- Uses config entries (built-in HA caching mechanism)
- No library-level caching needed

## Future Enhancements

1. **More patterns** - Add more non-WiiM device patterns as discovered
2. **Pattern configuration** - Make patterns configurable (optional)
3. **Validation optimization** - Make validation faster/smarter (parallel requests, timeout tuning)
4. **SSDP filtering** - More sophisticated SSDP header analysis

## Questions for Discussion

1. **Pattern list** - Maintain in code or make configurable?
   - **Recommendation:** Keep in code for now, make configurable later if needed

2. **Filter aggressiveness** - How conservative should we be?
   - **Answer:** VERY conservative - only filter devices we're 100% certain are not LinkPlay
   - **Principle:** Better to validate too many devices than to miss a LinkPlay device
   - **Audio Pro safety:** Generic "Linux" headers must pass through

3. **Validation timeout** - Can we reduce validation timeout for faster discovery?
   - **Current:** 5 seconds per device
   - **Consideration:** Reducing timeout might cause false negatives for slow devices

4. **Parallel validation** - Are we already validating in parallel?
   - **Answer:** Yes, via `asyncio.gather()` - all devices validated concurrently

5. **Audio Pro verification** - Do we have test devices to verify Audio Pro passes filter?
   - **Action needed:** Test with actual Audio Pro devices before implementing
   - **Fallback:** If uncertain, skip quick filtering entirely and rely on validation only

