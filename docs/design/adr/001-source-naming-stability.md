# ADR 001: Source Naming Stability and Smart Normalization

## Status
Accepted - 2025-12-25

## Context
WiiM and LinkPlay devices have inconsistent internal naming for audio sources (e.g., `line-in` vs `line_in`, `wifi` vs `wi-fi`). Historically, `pywiim` and the Home Assistant integration have changed these names in various releases to improve UI friendliness or API compatibility.

These changes have caused significant "churn" for users, breaking Home Assistant automations that depend on exact source name matching.

Recent attempts to standardize (e.g., adding "In" suffixes to all hardware inputs) caused further frustration as it changed existing working names like "Coaxial" to "Coaxial In".

## Decision
We will enforce **strict display name stability** while providing **high input resilience** through "Smart Normalization".

### 1. Locked Display Names
The following display names are considered "Locked" and must not be changed without a major version bump:
- **Network** (Unified streaming mode)
- **Bluetooth**
- **Line In**
- **Optical In**
- **Aux In** (Model-specific friendly name for `line_in`)
- **Coaxial** (Stable name, NO "In" suffix)
- **HDMI** (Stable name, NO "In" suffix)
- **Phono** (Stable name, NO "In" suffix)
- **USB** (Stable name, NO "In" suffix)

### 2. Smart Normalization in `set_source`
The `set_source()` method will implement a "Smart Normalization" strategy:
- **Direct Mappings**: Hardcoded mappings for known variations (e.g., "Optical In" → `optical`, "Coaxial In" → `coaxial`).
- **Alphanumeric Matching**: When a direct mapping is not found, the library will compare the user input against the device's reported `InputList` using a simplified alphanumeric match (ignoring case, spaces, underscores, and hyphens).
- **Preference for Device-Reported Strings**: If a simplified match is found in the device's own `InputList`, the library will use that exact string for the API call.

## Consequences
- **User Stability**: Home Assistant automations will stop breaking because display names are now stable.
- **UI Consistency**: The source list remains friendly and readable.
- **Improved Compatibility**: Devices that use non-standard naming (like older Audio Pro or Arylic units) will still work because the library matches their specific naming patterns automatically.
- **Reduced Maintenance**: We no longer need to add device-specific special cases for every minor naming variation found in firmware updates.

