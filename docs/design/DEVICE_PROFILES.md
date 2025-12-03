# Device Profiles

## Overview

Device profiles provide a centralized way to define device-specific behaviors, eliminating scattered conditionals throughout the codebase. Each device type (WiiM, Arylic, Audio Pro MkII, etc.) has a profile that defines:

- **State source preferences** - Which source (HTTP or UPnP) is authoritative for each state field
- **Connection requirements** - Ports, protocols, timeouts, client certificates
- **Endpoint availability** - Which API endpoints are supported
- **Grouping behavior** - WiFi Direct vs router-based multiroom
- **Loop mode scheme** - How shuffle/repeat values are interpreted

### Why Profiles Were Created

The library experienced a pattern of "fix one thing, break another" during releases. Analysis revealed:

1. **State management complexity** - The `StateSynchronizer` was guessing which source (HTTP vs UPnP) to trust using freshness windows and priority rules. This was error-prone.

2. **Scattered device conditionals** - Code like `if vendor == "audio_pro_mkii"` was spread across multiple files, making it hard to understand what a device needed.

3. **Implicit knowledge** - Device quirks (e.g., "Audio Pro MkII doesn't provide play_state via HTTP") were encoded in logic, not documented in one place.

Profiles solve this by making device behavior **explicit and centralized**.

---

## Architecture

### Profile Components

```python
# pywiim/profiles.py

@dataclass(frozen=True)
class StateSourceConfig:
    """Which source is authoritative for each state field."""
    play_state: str = "http"  # "http" | "upnp" | "latest"
    volume: str = "http"
    mute: str = "http"
    # ... other fields

@dataclass(frozen=True)
class ConnectionConfig:
    """Connection and protocol settings."""
    requires_client_cert: bool = False
    preferred_ports: tuple[int, ...] = (80, 443)
    protocol_priority: tuple[str, ...] = ("http", "https")
    response_timeout: float = 5.0

@dataclass(frozen=True)
class EndpointConfig:
    """Which API endpoints are available."""
    supports_getPlayerStatusEx: bool = True
    supports_getMetaInfo: bool = True
    supports_eq: bool = True
    # ... other endpoints

@dataclass(frozen=True)
class GroupingConfig:
    """Multiroom grouping settings."""
    uses_wifi_direct: bool = False
    supports_enhanced_grouping: bool = True

@dataclass(frozen=True)
class DeviceProfile:
    """Complete profile for a device type."""
    vendor: str
    generation: str | None = None
    loop_mode_scheme: str = "wiim"  # "wiim" | "arylic" | "legacy"
    state_sources: StateSourceConfig
    connection: ConnectionConfig
    endpoints: EndpointConfig
    grouping: GroupingConfig
```

### Pre-defined Profiles

| Profile | Key Characteristics |
|---------|---------------------|
| `PROFILE_WIIM` | HTTP for all state, standard ports, alarms/sleep timer supported |
| `PROFILE_ARYLIC` | HTTP for all state, Arylic loop mode scheme, EQ read-only |
| `PROFILE_AUDIO_PRO_MKII` | **UPnP for play_state/volume/mute**, mTLS required, port 4443 |
| `PROFILE_AUDIO_PRO_W_GENERATION` | HTTP for all state, HTTPS preferred |
| `PROFILE_AUDIO_PRO_ORIGINAL` | HTTP for all state, WiFi Direct for grouping |
| `PROFILE_LINKPLAY_GENERIC` | Conservative defaults |

### Profile Detection

Profiles are detected automatically from `DeviceInfo`:

```python
from pywiim.profiles import get_device_profile

profile = get_device_profile(device_info)
# Returns the appropriate profile based on model, vendor, firmware, wmrm_version
```

Detection uses:
1. Model name patterns (WiiM, Arylic, Audio Pro, etc.)
2. Generation detection for Audio Pro (MkII, W-Generation, Original)
3. Gen1 detection via `wmrm_version == "2.0"` or old firmware

---

## Current Integration Status

The profile system is partially integrated. Core functionality is complete; other areas use legacy conditionals.

### Completed

| Area | File | Description |
|------|------|-------------|
| State source selection | `pywiim/state.py` | `StateSynchronizer` uses profile to determine HTTP vs UPnP per field |
| Player profile detection | `pywiim/player/base.py` | Profile auto-detected on first refresh when `device_info` available |
| Profile setting on sync | `pywiim/player/statemgr.py` | Calls `_update_profile_from_device_info()` after device_info fetch |

**How it works:**
1. Player refreshes and fetches `device_info`
2. `_update_profile_from_device_info()` calls `get_device_profile(device_info)`
3. Profile is set on `StateSynchronizer` via `set_profile()`
4. All subsequent state merging uses the profile's source preferences

### Pending (Wait and See)

These areas still use scattered conditionals. They work correctly but are harder to maintain.

| Area | File | Current Approach | Notes |
|------|------|------------------|-------|
| Connection config | `pywiim/capabilities.py` | `detect_device_capabilities()` returns dict | Could use `profile.connection` |
| Loop mode interpretation | `pywiim/api/loop_mode.py` | `get_loop_mode_mapping(vendor)` | Could use `profile.loop_mode_scheme` |
| WiFi Direct detection | `pywiim/api/group.py` | `_needs_wifi_direct_mode()` function | Could use `profile.grouping.uses_wifi_direct` |
| Endpoint probing | `pywiim/capabilities.py` | Runtime probing | Could use `profile.endpoints` as hints |

**Migration approach:** Wait and see. Migrate an area when:
- A bug report reveals the scattered conditionals are causing problems
- Adding a new device type becomes painful without profiles
- Maintenance burden becomes too high

The profile infrastructure is in place; future migrations are incremental.

---

## Usage

### Getting a Profile

```python
from pywiim.profiles import get_device_profile, get_profile_for_vendor

# From device_info (preferred - auto-detects everything)
profile = get_device_profile(device_info)

# From vendor/generation strings (when device_info not available)
profile = get_profile_for_vendor("audio_pro", "mkii")
```

### Checking Profile Settings

```python
# State sources
if profile.state_sources.play_state == "upnp":
    # Use UPnP for play_state on this device
    ...

# Connection requirements
if profile.connection.requires_client_cert:
    # Set up mTLS
    ...

# Grouping behavior
if profile.grouping.uses_wifi_direct:
    # Use WiFi Direct mode for multiroom
    ...

# Loop mode
from pywiim.api.loop_mode import get_loop_mode_mapping
mapping = get_loop_mode_mapping(profile.loop_mode_scheme)
```

### In StateSynchronizer

The synchronizer automatically uses the profile when set:

```python
# Profile-driven resolution (when profile is set)
sync = StateSynchronizer(profile=profile)
# OR
sync.set_profile(profile)

# For Audio Pro MkII: UPnP is used for play_state
# For WiiM: HTTP is used for play_state
# No manual conflict resolution needed
```

---

## Adding a New Device Type

### Step 1: Understand the Device

Determine:
- What vendor/model/generation?
- Does HTTP provide all state fields, or does UPnP required for some?
- What ports/protocols does it use?
- What endpoints are supported?
- Does it need WiFi Direct for multiroom?

### Step 2: Create the Profile

Add to `pywiim/profiles.py`:

```python
PROFILE_NEW_DEVICE = DeviceProfile(
    vendor="new_vendor",
    generation="gen2",  # if applicable
    display_name="New Device Gen2",
    loop_mode_scheme="wiim",  # or "arylic"
    state_sources=StateSourceConfig(
        play_state="http",  # or "upnp" if HTTP doesn't provide it
        volume="http",
        # ...
    ),
    connection=ConnectionConfig(
        preferred_ports=(80, 443),
        protocol_priority=("http", "https"),
    ),
    endpoints=EndpointConfig(
        supports_eq=True,
        # ...
    ),
    grouping=GroupingConfig(
        uses_wifi_direct=False,
    ),
)

# Add to registry
PROFILES["new_vendor_gen2"] = PROFILE_NEW_DEVICE
```

### Step 3: Update Detection

Update `get_device_profile()` to detect your new device:

```python
def _detect_vendor(device_info: DeviceInfo) -> str:
    # Add detection for new vendor
    if "new_vendor" in model_lower:
        return "new_vendor"
    # ...
```

### Step 4: Add Tests

Add tests to `tests/unit/test_profiles.py`:

```python
def test_new_device_detection(self):
    device_info = DeviceInfo(uuid="test", name="Test", model="New Vendor Speaker")
    profile = get_device_profile(device_info)
    assert profile.vendor == "new_vendor"

def test_new_device_profile_settings(self):
    profile = PROFILES["new_vendor_gen2"]
    assert profile.state_sources.play_state == "http"
    # ...
```

---

## Migration Guide

When migrating an area from scattered conditionals to profiles:

### Example: Migrating Loop Mode

**Before (in `api/loop_mode.py`):**
```python
def get_loop_mode_mapping(vendor: str | None) -> LoopModeMapping:
    if vendor == "wiim":
        return WIIM_LOOP_MODE
    elif vendor in ("arylic", "audio_pro"):
        return ARYLIC_LOOP_MODE
    return WIIM_LOOP_MODE
```

**After (using profile):**
```python
def get_loop_mode_mapping(profile: DeviceProfile) -> LoopModeMapping:
    scheme = profile.loop_mode_scheme
    if scheme == "wiim":
        return WIIM_LOOP_MODE
    elif scheme == "arylic":
        return ARYLIC_LOOP_MODE
    return WIIM_LOOP_MODE
```

**Caller change:**
```python
# Before
mapping = get_loop_mode_mapping(vendor)

# After
mapping = get_loop_mode_mapping(player.profile)
```

---

## Related Documentation

- **[DEVICE_VARIATIONS.md](DEVICE_VARIATIONS.md)** - Vendor detection and endpoint variations
- **[STATE_MANAGEMENT.md](STATE_MANAGEMENT.md)** - State synchronization design
- **[LESSONS_LEARNED.md](LESSONS_LEARNED.md)** - Key design requirements

