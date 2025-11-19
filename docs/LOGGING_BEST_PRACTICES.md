# Logging Best Practices

This document outlines logging best practices for the pywiim library to ensure useful debugging information without excessive noise.

## Philosophy

**Log when it matters, not on every poll.**

The purpose of logging is to help developers and users understand what's happening in the system, especially when things go wrong or change. Logging the same unchanged information every few seconds creates noise that obscures real issues.

## Logging Levels

### ERROR
Use for unrecoverable errors that prevent functionality:
- Failed connections after all retries
- Invalid configuration
- Critical parsing errors

```python
_LOGGER.error("Failed to connect to device at %s after %d retries: %s", host, retries, error)
```

### WARNING
Use for recoverable errors or degraded functionality:
- Transient connection issues
- Unexpected but handled response formats  
- Deprecated feature usage

```python
_LOGGER.warning("Device returned unexpected format, using fallback parser: %s", error)
```

### INFO
Use for significant events and state changes:
- Track changes (music playing)
- Device discovery results
- Group formation/disbanding
- Major state transitions

```python
_LOGGER.info("🎵 Track changed: %s", track_name)
_LOGGER.info("Group disbanded (master: %s)", master_host)
```

### DEBUG
Use sparingly for diagnostic information **only when values change**:
- State changes (not every poll result)
- Protocol fallbacks
- Capability detection
- Group synchronization changes

```python
# ✅ GOOD: Log when value changes
if new_source != old_source:
    _LOGGER.debug("Source changed from %s to %s", old_source, new_source)

# ❌ BAD: Log on every poll
_LOGGER.debug("Current source: %s", current_source)
```

## Anti-Patterns to Avoid

### ❌ Logging on Every Poll

**Don't do this:**
```python
async def get_status():
    status = await device.get_status()
    _LOGGER.debug("Status: %s", status)  # Spams logs every 5 seconds!
    return status
```

**Do this instead:**
```python
async def get_status():
    status = await device.get_status()
    # Status available for debugging if needed, but not logged
    # to avoid spam on every poll cycle
    return status
```

### ❌ Logging Unchanged Metadata

**Don't do this:**
```python
_LOGGER.debug("Parsing: Title=%s, Artist=%s", title, artist)  # Every poll!
```

**Do this instead:**
```python
# Only log when track actually changes
if current_track != last_track:
    _LOGGER.info("🎵 Track changed: %s", current_track)
```

### ❌ Logging Raw API Responses

**Don't do this:**
```python
response = await api_call()
_LOGGER.debug("API response: %s", response)  # Huge JSON blob every poll!
```

**Do this instead:**
```python
response = await api_call()
# Response available for debugging if needed, but not logged
# to avoid spam on every poll cycle
```

## Best Practices

### 1. Log State Changes, Not State

```python
# ✅ GOOD
if play_state != previous_play_state:
    _LOGGER.debug("Play state changed: %s -> %s", previous_play_state, play_state)

# ❌ BAD  
_LOGGER.debug("Play state: %s", play_state)
```

### 2. Use Conditional Logging for Expensive Operations

```python
# ✅ GOOD: Check if DEBUG is enabled before expensive operations
if _LOGGER.isEnabledFor(logging.DEBUG):
    formatted_data = format_complex_data(large_object)
    _LOGGER.debug("Complex data: %s", formatted_data)
```

### 3. Provide Context in Error Messages

```python
# ✅ GOOD: Include relevant context
_LOGGER.warning(
    "Failed to refresh state for %s (model=%s, firmware=%s): %s",
    host, model, firmware, error
)

# ❌ BAD: Minimal context
_LOGGER.warning("Refresh failed: %s", error)
```

### 4. Use Emojis Sparingly for Important Events

```python
# ✅ GOOD: Makes track changes easy to spot
_LOGGER.info("🎵 Track changed: %s", track)

# ✅ GOOD: Highlights AirPlay issues
_LOGGER.debug("🔍 AirPlay position parsing issue: %s", details)

# ❌ BAD: Overuse makes them meaningless
_LOGGER.debug("🔧 Getting status...")  # Every poll!
```

### 5. Track Changes with State Variables

```python
class Parser:
    def __init__(self):
        self._last_track = None
    
    def parse(self, data):
        current_track = data.get('title')
        
        # Only log when track changes
        if current_track != self._last_track:
            _LOGGER.info("🎵 Track changed: %s", current_track)
            self._last_track = current_track
```

### 6. Log Startup/Initialization Events at INFO

```python
# ✅ GOOD: Startup events at INFO level
_LOGGER.info("Discovering devices via SSDP...")
_LOGGER.info("Discovery complete: found %d device(s)", count)

# ✅ GOOD: Capability detection at DEBUG
_LOGGER.debug("Device %s supports EQ (detected via %s)", host, endpoint)
```

### 7. Aggregate Repeated Events

```python
# ✅ GOOD: Log summary instead of every item
_LOGGER.info("Discovery found %d device(s)", len(devices))

# ❌ BAD: Log each item
for device in devices:
    _LOGGER.info("Found device: %s", device)  # Spams logs
```

## Integration-Specific Guidelines

For Home Assistant and other integrations that poll frequently:

1. **First Load**: Log at DEBUG or INFO to capture initial state
2. **Subsequent Polls with No Changes**: Don't log anything
3. **When Values Change**: Log at DEBUG with the change
4. **Errors**: Always log at WARNING/ERROR

Example for HA coordinator:
```python
async def _async_update_data(self):
    """Fetch data from device."""
    new_data = await self.device.get_status()
    
    # Only log if something changed or it's first load
    if self._first_load:
        _LOGGER.debug("Initial data for %s: sources=%s", self.name, new_data.sources)
        self._first_load = False
    elif new_data != self._last_data:
        _LOGGER.debug("Data changed for %s: %s", self.name, changes)
    
    self._last_data = new_data
    return new_data
```

## When to Use Each Level - Quick Reference

| Level | When to Use | Examples |
|-------|-------------|----------|
| **ERROR** | Unrecoverable failures | Connection failed after retries, critical parse error |
| **WARNING** | Recoverable issues, degraded state | Unexpected response format, fallback used |
| **INFO** | Significant events, user-visible changes | Track changed, device discovered, group formed |
| **DEBUG** | Diagnostic details **only when changed** | Source changed, capability detected, state transition |

## Testing Your Logging

Before committing, check that your logging:

1. ✅ Doesn't log on every poll when nothing changes
2. ✅ Does log when meaningful state changes occur  
3. ✅ Provides enough context to understand the issue
4. ✅ Isn't using expensive string operations without checking log level
5. ✅ Uses appropriate log levels for the severity

## Summary

**Good logging is:**
- Event-driven (logs changes, not states)
- Contextual (includes relevant information)
- Appropriately leveled (ERROR for failures, DEBUG for diagnostics)
- Efficient (checks log level before expensive operations)

**Bad logging is:**
- Polling-driven (logs every status check)
- Noisy (logs unchanged values repeatedly)
- Overly verbose (huge data dumps at DEBUG)
- Missing context (just "Error: failed")

Remember: **The best debug log is one that helps you find bugs without drowning in noise.**

