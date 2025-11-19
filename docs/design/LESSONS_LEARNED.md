# Lessons Learned

## Overview

Critical design requirements and patterns learned from the WiiM integration to ensure the `pywiim` library avoids known pitfalls.

## Key Takeaways

1. **State Synchronization is Critical**: Most issues relate to HTTP/UPnP state merging. See `STATE_MANAGEMENT.md` for details.
2. **Audio Pro Devices Need Special Handling**: Client certs, protocol detection, endpoint variations. See `DEVICE_VARIATIONS.md`.
3. **Metadata Preservation is Essential**: Don't clear metadata during transitions - check play_state before clearing.
4. **UPnP Health Checking is Unreliable**: Events only on changes, no heartbeat - use long timeouts (300s).
5. **Endpoint Variations are Common**: Need abstraction and fallback chains. See `DEVICE_VARIATIONS.md`.
6. **Discovery Must be Robust**: Multi-protocol fallback, graceful validation failures.
7. **Trust the API**: If HTTP call succeeds, operation worked - update state immediately. See `OPERATION_PATTERNS.md`.

## Critical Requirements

### State Synchronization
- ✅ Timestamped state merging with source tracking
- ✅ Freshness windows (field-specific time windows)
- ✅ Source priority (UPnP for real-time, HTTP for metadata)
- ✅ Metadata preservation (don't clear during play/transition)
- ✅ Conflict resolution (freshness > priority > recency)

**Implementation**: `STATE_MANAGEMENT.md`, `StateSynchronizer` class

### Audio Pro Device Handling
- ✅ Client certificate authentication for MkII devices
- ✅ Multi-protocol fallback: HTTPS:4443 → HTTPS:8443 → HTTPS:443 → HTTP:80 → HTTP:8080
- ✅ Generation detection (MkII, W-Generation, Original)
- ✅ Capability detection (probe endpoints before using)

**Implementation**: `DEVICE_VARIATIONS.md`, endpoint abstraction

### UPnP Subscription Management
- ✅ No health checking (UPnP has no heartbeat)
- ✅ Long timeout (300s) since events only on changes
- ✅ HTTP polling becomes authoritative when UPnP fails
- ✅ Cooperative sources (UPnP supplements HTTP, doesn't replace)

**Implementation**: `UPNP_INTEGRATION.md`, `StateSynchronizer`

### Endpoint Variations
- ✅ Endpoint abstraction with fallback chains
- ✅ Capability detection (probe before using)
- ✅ Field mapping (handle missing fields gracefully)

**Implementation**: `DEVICE_VARIATIONS.md`, `EndpointResolver` class

## Design Patterns

### Smart Logging Escalation
- First 2 attempts: WARNING (normal)
- Next 2 attempts: DEBUG (reduce noise)
- After 4+ attempts: ERROR (device likely offline)

### Protocol/Port Fallback
```python
PROTOCOL_FALLBACK_CHAIN = [
    ("https", 4443),  # Audio Pro MkII with client cert
    ("https", 8443),  # Audio Pro W-Generation
    ("https", 443),   # Standard HTTPS
    ("http", 80),     # Standard HTTP
    ("http", 8080),   # Alternative HTTP port
]
```

### Empty Response Handling
Some commands (e.g., `reboot`) don't return responses - handle gracefully.

## Related Documentation

- **[STATE_MANAGEMENT.md](STATE_MANAGEMENT.md)** - State synchronization details
- **[DEVICE_VARIATIONS.md](DEVICE_VARIATIONS.md)** - Device compatibility and endpoint abstraction
- **[OPERATION_PATTERNS.md](OPERATION_PATTERNS.md)** - Operation implementation patterns
- **[UPNP_INTEGRATION.md](UPNP_INTEGRATION.md)** - UPnP integration details
