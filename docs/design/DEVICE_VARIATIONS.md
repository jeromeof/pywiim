# Device Variations and Compatibility

## Overview

pywiim supports multiple LinkPlay-based device vendors (WiiM, Arylic, Audio Pro, etc.), each with their own API quirks, endpoint variations, and implementation differences. This document describes how the library handles these variations gracefully through vendor detection, endpoint abstraction, and capability-aware design.

## Table of Contents

1. [Vendor Detection](#vendor-detection) - Identifying device vendors
2. [Endpoint Abstraction](#endpoint-abstraction) - Handling endpoint variations
3. [Audio Pro Generations](#audio-pro-generations) - Special handling for Audio Pro devices
4. [Device Catalog](#device-catalog) - Known devices and their quirks
5. [Capability Detection](#capability-detection) - Multi-layered detection strategy

---

## Vendor Detection

### Design Pattern: Strategy Pattern with Vendor Registry

We use a **Strategy Pattern** combined with a **Vendor Registry** to handle vendor-specific differences:

1. **Vendor Detection**: Identify the vendor from device information
2. **Vendor Registry**: Map vendors to their specific capabilities and quirks
3. **Strategy Selection**: Apply vendor-specific strategies for API calls
4. **Graceful Fallback**: Fall back to standard LinkPlay behavior when vendor-specific behavior fails

### Detection Methods

Vendors are identified through multiple signals:

1. **Model Name Patterns**: Check device model for vendor-specific patterns
   - WiiM: "WiiM", "wiim"
   - Arylic: "Arylic", "Up2Stream", "up2stream"
   - Audio Pro: "Addon C5", "Addon C10", "Audio Pro"

2. **Device Name Patterns**: Some vendors include brand in device name
3. **Firmware Signatures**: Vendor-specific firmware version formats
4. **API Response Patterns**: Vendor-specific response formats or fields

### Vendor Types

```python
VENDOR_WIIM = "wiim"
VENDOR_ARYLIC = "arylic"
VENDOR_AUDIO_PRO = "audio_pro"
VENDOR_LINKPLAY_GENERIC = "linkplay_generic"  # Unknown/other LinkPlay devices
```

### Vendor Detection Function

```python
def detect_vendor(device_info: DeviceInfo) -> str:
    """Detect vendor from device information.
    
    Args:
        device_info: Device information from getStatusEx
        
    Returns:
        Vendor identifier string
    """
    model_lower = (device_info.model or "").lower()
    name_lower = (device_info.name or "").lower()
    
    # Check for WiiM devices
    if "wiim" in model_lower or "wiim" in name_lower:
        return VENDOR_WIIM
    
    # Check for Arylic devices
    if any(arylic_type in model_lower for arylic_type in ["arylic", "up2stream"]):
        return VENDOR_ARYLIC
    
    # Check for Audio Pro devices
    if any(pro_type in model_lower for pro_type in ["addon c5", "addon c10", "audio pro"]):
        return VENDOR_AUDIO_PRO
    
    # Default to generic LinkPlay
    return VENDOR_LINKPLAY_GENERIC
```

### Vendor Registry

```python
VENDOR_REGISTRY: dict[str, dict[str, Any]] = {
    VENDOR_WIIM: {
        "led_command_format": "standard",
        "source_name_format": "standard",
        "preferred_protocol": "https",
        "supports_metadata": True,
        "supports_eq": True,
        "supports_presets": True,
        "response_timeout": 2.0,
        "retry_count": 2,
    },
    VENDOR_ARYLIC: {
        "led_command_format": "arylic",
        "source_name_format": "hyphen",  # Prefer "line-in" over "line_in"
        "preferred_protocol": "http",  # May vary by model
        "supports_metadata": True,  # Probe to confirm
        "supports_eq": True,  # Probe to confirm
        "supports_presets": True,  # Probe to confirm
        "response_timeout": 3.0,
        "retry_count": 3,
        "led_fallback": True,  # Try standard commands if Arylic commands fail
    },
    VENDOR_AUDIO_PRO: {
        "led_command_format": "standard",
        "source_name_format": "standard",
        "preferred_protocol": "https",  # Varies by generation
        "supports_metadata": False,  # Varies by generation
        "supports_eq": False,  # Varies by generation
        "supports_presets": False,  # Varies by generation
        "response_timeout": 6.0,  # Varies by generation
        "retry_count": 3,  # Varies by generation
        "requires_client_cert": False,  # True for MkII
    },
    VENDOR_LINKPLAY_GENERIC: {
        "led_command_format": "standard",
        "source_name_format": "standard",
        "preferred_protocol": "https",
        "supports_metadata": None,  # Unknown, probe
        "supports_eq": None,  # Unknown, probe
        "supports_presets": None,  # Unknown, probe
        "response_timeout": 5.0,
        "retry_count": 3,
    },
}
```

### Vendor-Specific Quirks

#### WiiM Devices
- **LED Commands**: Standard `setLED:` and `setLEDBrightness:` commands
- **Source Names**: Standard LinkPlay source names
- **API Endpoints**: Full support for all endpoints
- **Protocol**: HTTPS preferred, HTTP fallback
- **Response Format**: Standard JSON responses

#### Arylic Devices
- **LED Commands**: Use `MCU+PAS+RAKOIT:LED:` and `MCU+PAS+RAKOIT:LEDBRIGHTNESS:` commands
  - Fallback to standard commands if Arylic commands fail
- **Source Names**: Prefer hyphen format (e.g., "line-in" vs "line_in")
- **API Endpoints**: Most standard endpoints supported
- **Protocol**: HTTP/HTTPS (varies by model)
- **Response Format**: Standard JSON, but may have field name variations

#### Audio Pro Devices
- **LED Commands**: Standard commands (varies by generation)
- **Source Names**: Standard LinkPlay names
- **API Endpoints**: **Significantly different between generations** (see [Audio Pro Generations](#audio-pro-generations))
- **Protocol**: HTTPS with client cert (MkII on port 4443), HTTP/HTTPS (others)
- **Response Format**: May return strings instead of JSON (MkII), standard JSON (others)

#### Generic LinkPlay Devices
- **LED Commands**: Standard commands
- **Source Names**: Standard LinkPlay names
- **API Endpoints**: Probe to determine support
- **Protocol**: HTTP/HTTPS (probe to determine)
- **Response Format**: Standard JSON (assumed)

---

## Endpoint Abstraction

### Problem Statement

Different LinkPlay implementations use different endpoint paths and formats:

1. **Vendor Variations**: Arylic, WiiM, Audio Pro may use different endpoint formats
2. **Generation Variations**: Audio Pro MkII vs W-Generation vs Original have different endpoint support
3. **Firmware Variations**: Different firmware versions may add/remove/modify endpoints
4. **Fallback Requirements**: Need to try multiple endpoint variants when primary fails

### Design Pattern: Endpoint Registry with Fallback Chains

We use an **Endpoint Registry** pattern with **Fallback Chains** to handle endpoint variations:

1. **Endpoint Registry**: Maps logical operations to endpoint variants by vendor/generation
2. **Fallback Chains**: Ordered list of endpoints to try when primary fails
3. **Capability-Aware Selection**: Select endpoints based on detected capabilities
4. **Runtime Probing**: Probe endpoints to determine actual availability

### Logical Endpoint Names

Endpoints are identified by logical names, not literal paths:

```python
# Logical endpoint names
ENDPOINT_PLAYER_STATUS = "player_status"  # Get playback status
ENDPOINT_DEVICE_STATUS = "device_status"  # Get device info
ENDPOINT_METADATA = "metadata"  # Get track metadata
ENDPOINT_VOLUME = "volume"  # Set volume
ENDPOINT_PLAY = "play"  # Play command
# ... etc
```

### Endpoint Registry Structure

Each logical endpoint can have multiple variants:

```python
ENDPOINT_REGISTRY: dict[str, dict[str, list[str]]] = {
    "player_status": {
        "default": [
            "/httpapi.asp?command=getPlayerStatusEx",  # Primary (WiiM, most devices)
            "/httpapi.asp?command=getStatusEx",  # Fallback (Audio Pro MkII)
            "/httpapi.asp?command=getPlayerStatus",  # Legacy fallback
            "/httpapi.asp?command=getStatus",  # Legacy fallback
        ],
        "audio_pro_mkii": [
            "/httpapi.asp?command=getStatusEx",  # Primary (MkII doesn't support getPlayerStatusEx)
            "/httpapi.asp?command=getStatus",  # Fallback
            "/api/status",  # REST variant
            "/cgi-bin/status.cgi",  # CGI variant
        ],
        "audio_pro_w_generation": [
            "/httpapi.asp?command=getPlayerStatusEx",  # Primary
            "/httpapi.asp?command=getStatusEx",  # Fallback
        ],
        "audio_pro_original": [
            "/httpapi.asp?command=getStatusEx",  # Primary
            "/httpapi.asp?command=getStatus",  # Fallback
        ],
        "arylic": [
            "/httpapi.asp?command=getPlayerStatusEx",  # Primary
            "/httpapi.asp?command=getStatusEx",  # Fallback
        ],
    },
    "metadata": {
        "default": [
            "/httpapi.asp?command=getMetaInfo",  # Primary
        ],
        "audio_pro_mkii": [],  # Not supported - empty list means unsupported
        "audio_pro_w_generation": [
            "/httpapi.asp?command=getMetaInfo",  # May be supported
        ],
        "audio_pro_original": [],  # Not supported
    },
    # ... more endpoints
}
```

### Endpoint Resolver Class

```python
class EndpointResolver:
    """Resolve logical endpoint names to actual endpoint paths with fallback chains."""
    
    def __init__(self, capabilities: dict[str, Any]):
        """Initialize resolver with device capabilities.
        
        Args:
            capabilities: Device capabilities including vendor, generation, firmware
        """
        self.capabilities = capabilities
        self.vendor = capabilities.get("vendor", VENDOR_LINKPLAY_GENERIC)
        self.generation = capabilities.get("audio_pro_generation")
        self.firmware = capabilities.get("firmware_version")
        
    def get_endpoint_chain(self, logical_name: str) -> list[str]:
        """Get ordered list of endpoint paths to try for a logical operation.
        
        Args:
            logical_name: Logical endpoint name (e.g., "player_status")
            
        Returns:
            List of endpoint paths to try in order
        """
        # Determine variant key based on capabilities
        variant_key = self._get_variant_key()
        
        # Get endpoint chain for this variant
        if logical_name in ENDPOINT_REGISTRY:
            endpoint_variants = ENDPOINT_REGISTRY[logical_name]
            
            # Try variant-specific chain first
            if variant_key in endpoint_variants:
                chain = endpoint_variants[variant_key]
                if chain:  # Not empty (not unsupported)
                    return chain
            
            # Fallback to default chain
            if "default" in endpoint_variants:
                return endpoint_variants["default"]
        
        # No endpoint found - return empty (unsupported)
        return []
    
    def _get_variant_key(self) -> str:
        """Get variant key based on vendor and generation."""
        if self.vendor == VENDOR_AUDIO_PRO:
            if self.generation == "mkii":
                return "audio_pro_mkii"
            elif self.generation == "w_generation":
                return "audio_pro_w_generation"
            elif self.generation == "original":
                return "audio_pro_original"
            return "audio_pro_default"
        elif self.vendor == VENDOR_ARYLIC:
            return "arylic"
        elif self.vendor == VENDOR_WIIM:
            return "default"  # WiiM uses default endpoints
        else:
            return "default"
```

### Capability-Aware Request Method

```python
class BaseWiiMClient:
    """Base client with endpoint abstraction."""
    
    def __init__(self, ...):
        self._endpoint_resolver = EndpointResolver(self._capabilities)
        # ...
    
    async def _request_with_fallback(
        self,
        logical_endpoint: str,
        method: str = "GET",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make request with endpoint fallback chain.
        
        Args:
            logical_endpoint: Logical endpoint name (e.g., "player_status")
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            Response dictionary
            
        Raises:
            WiiMRequestError: If all endpoints in chain fail
        """
        endpoint_chain = self._endpoint_resolver.get_endpoint_chain(logical_endpoint)
        
        if not endpoint_chain:
            raise WiiMRequestError(
                f"Endpoint '{logical_endpoint}' not supported on this device",
                device_info=self._get_device_info(),
            )
        
        last_error: Exception | None = None
        
        for endpoint in endpoint_chain:
            try:
                return await self._request(endpoint, method, **kwargs)
            except (WiiMRequestError, WiiMConnectionError) as err:
                last_error = err
                _LOGGER.debug(
                    "Endpoint %s failed for %s, trying next in chain: %s",
                    endpoint,
                    self.host,
                    err,
                )
                continue
        
        # All endpoints failed
        raise WiiMRequestError(
            f"All endpoints in chain failed for '{logical_endpoint}': {last_error}",
            endpoint=logical_endpoint,
            last_error=last_error,
            device_info=self._get_device_info(),
        ) from last_error
```

### Endpoint Probing and Caching

Endpoints are probed at runtime and results cached:

```python
class EndpointProber:
    """Probe endpoints to determine actual availability."""
    
    def __init__(self):
        self._probed_endpoints: dict[str, dict[str, bool]] = {}  # device_id -> endpoint -> supported
    
    async def probe_endpoint(
        self,
        client: BaseWiiMClient,
        endpoint: str,
    ) -> bool:
        """Probe if endpoint is supported.
        
        Returns:
            True if endpoint works, False otherwise
        """
        device_id = f"{client.host}:{client.capabilities.get('uuid', 'unknown')}"
        
        if device_id not in self._probed_endpoints:
            self._probed_endpoints[device_id] = {}
        
        if endpoint in self._probed_endpoints[device_id]:
            return self._probed_endpoints[device_id][endpoint]
        
        # Probe endpoint
        try:
            await client._request(endpoint)
            supported = True
        except WiiMRequestError:
            supported = False
        
        self._probed_endpoints[device_id][endpoint] = supported
        return supported
```

---

## Audio Pro Generations

### Generation Detection

Audio Pro devices have **three generations** with distinct capabilities:

1. **MkII Generation** (`mkii`):
   - **Models**: "Addon C5 MkII", "A10", "A15", "A28", "C10" (with MkII firmware)
   - **Firmware**: 1.56-1.60 range typically indicates MkII
   - **Key Characteristics**:
     - Requires client certificate (mTLS on port 4443)
     - Does NOT support: getPlayerStatusEx, getMetaInfo, EQ, presets
     - Uses: getStatusEx for status (only supported endpoint)
     - May return string responses instead of JSON
     - Different endpoint paths may be needed (/api/status, /cgi-bin/status.cgi)

2. **W-Generation** (`w_generation`):
   - **Models**: "Addon C5A", "Addon C10A", "A10", "A15" (with W-gen firmware)
   - **Firmware**: 2.0-2.3 range typically indicates W-Generation
   - **Key Characteristics**:
     - Enhanced features compared to original
     - Supports: getPlayerStatusEx, getMetaInfo (may vary by firmware)
     - Better multiroom support
     - Faster response times than original

3. **Original Generation** (`original`):
   - **Models**: "Addon C5", "Addon C10" (older models)
   - **Key Characteristics**:
     - Basic LinkPlay features
     - Limited endpoint support
     - Slower response times
     - May not support newer endpoints

**Critical**: The two main generations (MkII and W-Generation) have **significantly different endpoint support** and must be handled separately.

### Generation-Specific Endpoint Chains

```python
# Example: Player status endpoint chains by generation
"player_status": {
    "audio_pro_mkii": [
        "/httpapi.asp?command=getStatusEx",  # Only supported endpoint
        "/httpapi.asp?command=getStatus",  # Legacy fallback
    ],
    "audio_pro_w_generation": [
        "/httpapi.asp?command=getPlayerStatusEx",  # Preferred
        "/httpapi.asp?command=getStatusEx",  # Fallback
    ],
    "audio_pro_original": [
        "/httpapi.asp?command=getStatusEx",  # Primary
        "/httpapi.asp?command=getStatus",  # Fallback
    ],
}
```

### Audio Pro MkII Critical Differences

**❌ Unsupported Endpoints (Return "unknown command"):**
- **`getPlayerStatus`** - Does NOT work on Audio Pro MkII
- **`getMetaInfo`** - Does NOT work (no track metadata endpoint)
- **`getPresetInfo`** - Does NOT work (no preset information endpoint)
- **EQ Commands** - All EQ endpoints fail

**✅ Working Endpoints:**
- **`getStatusEx`** - Use this instead of `getPlayerStatus` for device status
- **`setPlayerCmd:*`** - All playback commands work
- **`wlanGetConnectState`** - WiFi connection status
- **`getNewAudioOutputHardwareMode`** - Audio output mode status
- **`multiroom:*`** - All multiroom commands work
- **`setPlayerCmd:switchmode:*`** - Source switching

**Critical Implementation Note:**

Our integration automatically uses `getStatusEx` instead of `getPlayerStatus` for Audio Pro MkII devices. The status endpoint is configured as:

```python
capabilities["status_endpoint"] = "/httpapi.asp?command=getStatusEx"
capabilities["supports_player_status_ex"] = False  # getPlayerStatus not supported
capabilities["supports_metadata"] = False  # getMetaInfo not supported
capabilities["supports_eq"] = False  # EQ commands not supported
capabilities["supports_presets"] = False  # getPresetInfo not supported
```

**Protocol Requirements:**
- **HTTPS Required**: Port 4443 with client certificate (mTLS)
- **Fallback Ports**: 8443, 443 (HTTPS), 80 (HTTP as last resort)
- **Client Certificate**: Required for port 4443, embedded in library

---

## Device Catalog

This section catalogs known device models, their quirks, compatibility issues, and workarounds.

### WiiM Devices

WiiM devices are newer LinkPlay-based devices with enhanced features and better API support.

#### WiiM Pro
- **Model**: `WiiM Pro`
- **Firmware**: 4.0+ recommended
- **Features**: Full feature support
- **HTTPS**: Supported (self-signed cert)
- **Client Cert**: Not required
- **Known Issues**: None
- **Workarounds**: None

#### WiiM Mini
- **Model**: `WiiM Mini`
- **Firmware**: 4.0+ recommended
- **Features**: Full feature support
- **HTTPS**: Supported (self-signed cert)
- **Client Cert**: Not required
- **Known Issues**: None
- **Workarounds**: None

#### WiiM Amp
- **Model**: `WiiM Amp`
- **Firmware**: 4.0+ recommended
- **Features**: Full feature support
- **HTTPS**: Supported (self-signed cert)
- **Client Cert**: Not required
- **Known Issues**: None
- **Workarounds**: None

### Arylic Devices

Arylic devices are LinkPlay-based devices with vendor-specific API variations.

#### Arylic Up2Stream Amp 2.0 / 2.1
- **Model**: `Arylic Up2Stream Amp 2.0` or `Arylic Up2Stream Amp 2.1`
- **Vendor**: `arylic`
- **Firmware**: Various versions
- **Features**: Full feature support with vendor-specific quirks
- **HTTPS**: Supported (self-signed cert)
- **Client Cert**: Not required
- **Known Issues**:
  - Uses different LED command format (`MCU+PAS+RAKOIT:LED:` instead of `setLED:`)
  - Prefers hyphen format for source names (e.g., "line-in" vs "line_in")
- **Workarounds**:
  - Try Arylic-specific LED commands first, fallback to standard if they fail
  - Normalize source names to hyphen format for Arylic devices

#### Arylic S10+
- **Model**: `Arylic S10+`
- **Vendor**: `arylic`
- **Firmware**: Various versions
- **Features**: Full feature support with vendor-specific quirks
- **HTTPS**: Supported (self-signed cert)
- **Client Cert**: Not required
- **Known Issues**: Same as other Arylic devices
- **Workarounds**: Same as other Arylic devices

### Audio Pro Devices

Legacy Audio Pro devices are older LinkPlay-based devices with **multiple generations** that have significantly different endpoint support. The endpoint abstraction pattern handles these variations automatically.

#### Audio Pro Addon C5/C10 (Original)
- **Model**: `Addon C5` or `Addon C10`
- **Firmware**: Various versions
- **Generation**: `original`
- **Features**: Limited support
- **HTTPS**: May require self-signed cert handling
- **Client Cert**: Not required
- **Known Issues**:
  - May not support getMetaInfo endpoint
  - Limited EQ support
  - May not support presets
- **Workarounds**:
  - Use getStatusEx instead of getPlayerStatusEx
  - Fallback to UPnP for volume/play state if HTTP unavailable

#### Audio Pro Addon C5A/C10A (W Generation)
- **Model**: `Addon C5A` or `Addon C10A`
- **Firmware**: Various versions
- **Generation**: `w_generation`
- **Features**: Limited support
- **HTTPS**: May require self-signed cert handling
- **Client Cert**: Not required
- **Known Issues**:
  - May not support getMetaInfo endpoint
  - Limited EQ support
  - May not support presets
- **Workarounds**:
  - Use getStatusEx instead of getPlayerStatusEx
  - Fallback to UPnP for volume/play state if HTTP unavailable

#### Audio Pro Addon C5 MkII (Generation 1)
- **Model**: `Addon C5 MkII`, `A10`, `A15`, `A28`, `C10` (with MkII firmware)
- **Firmware**: 1.56-1.60 range typically indicates MkII
- **Generation**: `mkii` (First generation of modern Audio Pro)
- **Features**: Very limited support - **significantly different endpoints**
- **HTTPS**: Required (port 4443)
- **Client Cert**: **REQUIRED** (mTLS)
- **Endpoint Variations**:
  - **Does NOT support**: getPlayerStatusEx, getMetaInfo, EQ commands, presets
  - **Uses**: getStatusEx only (primary status endpoint)
  - **Alternative paths**: May use /api/status, /cgi-bin/status.cgi, /status (REST variants)
  - **Response format**: May return strings instead of JSON
- **Known Issues**:
  - HTTP volume control not available (use UPnP)
  - Play state not available via HTTP (use UPnP)
  - Requires client certificate for HTTPS connections
- **Workarounds**:
  - Endpoint abstraction automatically uses getStatusEx for MkII
  - Use UPnP for volume and play state
  - Skip metadata retrieval (endpoint not available)
  - Use port 4443 for HTTPS with client certificate
  - Prefer HTTPS over HTTP (port 4443, 8443, 443)

#### Audio Pro Addon C5A/C10A (Generation 2 - W-Generation)
- **Model**: `Addon C5A`, `Addon C10A`, `A10`, `A15` (with W-gen firmware)
- **Firmware**: 2.0-2.3 range typically indicates W-Generation
- **Generation**: `w_generation` (Second generation - enhanced features)
- **Features**: Enhanced support compared to MkII
- **HTTPS**: Supported (self-signed cert)
- **Client Cert**: Not required
- **Endpoint Variations**:
  - **Supports**: getPlayerStatusEx (preferred), getStatusEx (fallback)
  - **May support**: getMetaInfo (probe to confirm)
  - **Better**: Multiroom support, faster response times
- **Known Issues**: Fewer issues than MkII, more compatible
- **Workarounds**: Generally uses standard endpoints with fallbacks

---

## API Endpoint Compatibility

### getStatusEx
- **WiiM Devices**: ✅ Supported
- **Legacy Devices**: ✅ Supported
- **Audio Pro MkII**: ✅ Supported (preferred over getPlayerStatusEx)
- **Notes**: Core endpoint, always available

### getPlayerStatusEx
- **WiiM Devices**: ✅ Supported
- **Legacy Devices**: ✅ Supported
- **Audio Pro MkII**: ❌ Not supported (use getStatusEx)
- **Notes**: Enhanced status endpoint, not available on all devices

### getMetaInfo
- **WiiM Devices**: ✅ Supported
- **Legacy Devices**: ⚠️ May not be supported
- **Audio Pro MkII**: ❌ Not supported (returns 404)
- **Notes**: Metadata endpoint, gracefully handle 404

### getSlaveList
- **WiiM Devices**: ✅ Supported
- **Legacy Devices**: ✅ Supported
- **Audio Pro MkII**: ✅ Supported
- **Notes**: Multiroom group information

### EQ Endpoints
- **WiiM Devices**: ✅ Supported
- **Legacy Devices**: ⚠️ Limited support
- **Audio Pro MkII**: ❌ Not supported
- **Notes**: EQ commands may not work on older devices

### Preset Endpoints
- **WiiM Devices**: ✅ Supported (6-20 slots, varies by model/firmware)
  - Preset count determined by `preset_key` field in device info
  - Older firmware may default to 6 slots if `preset_key` not exposed
  - Newer devices may support up to 20 preset slots
- **Legacy Devices**: ⚠️ May not be supported
  - If supported, typically 6 slots (default)
  - May expose `preset_key` in device info for accurate count
- **Audio Pro MkII**: ❌ Not supported (getPresetInfo returns 404)
- **Notes**: 
  - Preset support varies by device and firmware
  - Always check `preset_key` in device info for accurate slot count
  - Default to 6 slots if `preset_key` not available
  - Validate preset numbers against device's max slots before playing

### Audio Output Endpoints
- **WiiM Devices**: ✅ Supported
- **Legacy Devices**: ⚠️ May not be supported
- **Audio Pro MkII**: ⚠️ Limited support
- **Notes**: Audio output control varies by device

---

## Protocol Support

### HTTP
- **WiiM Devices**: ✅ Supported (port 80)
- **Legacy Devices**: ✅ Supported (port 80)
- **Audio Pro MkII**: ✅ Supported (fallback)
- **Notes**: Standard HTTP, no encryption

### HTTPS
- **WiiM Devices**: ✅ Supported (self-signed cert, port 443)
- **Legacy Devices**: ⚠️ May be supported (self-signed cert)
- **Audio Pro MkII**: ✅ Required (port 4443, requires client cert)
- **Notes**: SSL/TLS with self-signed certificates, client cert for MkII

### UPnP/DLNA
- **WiiM Devices**: ✅ Supported
- **Legacy Devices**: ✅ Supported
- **Audio Pro MkII**: ✅ Supported
- **Notes**: Real-time event subscriptions, preferred for volume/play state on MkII

---

## Known Workarounds

### Workaround 1: Audio Pro MkII Volume Control
- **Issue**: HTTP volume control not available
- **Solution**: Use UPnP RenderingControl service for volume
- **Implementation**: Check device type, use UPnP for volume on MkII

### Workaround 2: Audio Pro MkII Play State
- **Issue**: Play state not available via HTTP
- **Solution**: Use UPnP AVTransport service for play state
- **Implementation**: Check device type, use UPnP for play state on MkII

### Workaround 3: Audio Pro MkII Metadata
- **Issue**: getMetaInfo endpoint returns 404
- **Solution**: Skip metadata retrieval, use status endpoint only
- **Implementation**: Capability detection marks metadata as unsupported

### Workaround 4: Time Value Units
- **Issue**: Some devices return time in microseconds, others in milliseconds
- **Solution**: Detect based on value magnitude (> 10 hours if milliseconds)
- **Implementation**: Normalize in parser, convert to seconds

### Workaround 5: Text Encoding
- **Issue**: Some API responses use hex-encoded strings
- **Solution**: Decode hex-encoded strings to UTF-8
- **Implementation**: Parser handles hex encoding automatically

---

## Capability Detection

The capability detection system uses a layered approach:

### Layer 0: Vendor Detection
- Detect vendor from model name and device name patterns
- Identify vendor-specific quirks and capabilities
- Apply vendor-specific defaults from vendor registry
- Vendors: WiiM, Arylic, Audio Pro, Generic LinkPlay

### Layer 1: Device Type Detection
- Check model name for "WiiM" vs "Addon" vs "Arylic"
- Check for known device patterns
- Set base capabilities based on device type and vendor

### Layer 2: Firmware Version Detection
- Parse firmware version string
- Apply firmware-specific capabilities
- Check for known firmware quirks

### Layer 3: Generation Detection (Audio Pro)
- Detect Audio Pro generation (mkii, w_generation, original)
- Apply generation-specific capabilities
- Set generation-specific workarounds

### Layer 4: Endpoint Probing
- Probe endpoints to determine availability
- Cache results to avoid repeated probes
- Mark endpoints as unsupported if they fail

### Layer 5: Protocol Detection
- Detect HTTP vs HTTPS support
- Detect required ports
- Detect client certificate requirements

### Capability Detection Implementation

```python
class DeviceCapabilities:
    """Enhanced capability detection with vendor awareness."""
    
    def __init__(self):
        self._capabilities: dict[str, dict[str, Any]] = {}
        self._vendors: dict[str, str] = {}  # device_id -> vendor
    
    async def detect_capabilities(
        self,
        client: BaseWiiMClient,
        device_info: DeviceInfo,
    ) -> dict[str, Any]:
        """Detect capabilities including vendor identification."""
        device_id = f"{client.host}:{device_info.uuid}"
        
        if device_id in self._capabilities:
            return self._capabilities[device_id]
        
        # Detect vendor first
        vendor = detect_vendor(device_info)
        self._vendors[device_id] = vendor
        
        # Start with vendor defaults
        capabilities = VENDOR_REGISTRY.get(vendor, VENDOR_REGISTRY[VENDOR_LINKPLAY_GENERIC]).copy()
        capabilities["vendor"] = vendor
        
        # Apply device-specific overrides (generation, firmware, etc.)
        # ... existing capability detection logic ...
        
        self._capabilities[device_id] = capabilities
        return capabilities
```

---

## Vendor-Aware API Methods

API methods check vendor capabilities before making calls:

```python
async def set_led(self, enabled: bool) -> None:
    """Set LED state with vendor-aware command selection."""
    vendor = self.capabilities.get("vendor", VENDOR_LINKPLAY_GENERIC)
    led_format = self.capabilities.get("led_command_format", "standard")
    
    if led_format == "arylic":
        # Try Arylic-specific commands first
        try:
            await self._request(f"{API_ENDPOINT_ARYLIC_LED}{1 if enabled else 0}")
            return
        except WiiMRequestError as arylic_err:
            # Fallback to standard if Arylic commands fail
            if self.capabilities.get("led_fallback", False):
                _LOGGER.debug(
                    "Arylic LED command failed for %s, trying standard: %s",
                    self.host,
                    arylic_err,
                )
                try:
                    await self._request(f"{API_ENDPOINT_LED}{1 if enabled else 0}")
                    return
                except WiiMRequestError as std_err:
                    # Re-raise original Arylic error if both fail
                    raise arylic_err from std_err
            raise
    else:
        # Standard LED commands
        await self._request(f"{API_ENDPOINT_LED}{1 if enabled else 0}")
```

### Source Name Normalization

Vendor-aware source name handling:

```python
def normalize_source_name(self, source: str) -> str:
    """Normalize source name based on vendor preferences."""
    vendor = self.capabilities.get("vendor", VENDOR_LINKPLAY_GENERIC)
    source_format = self.capabilities.get("source_name_format", "standard")
    
    if source_format == "hyphen" and "_" in source:
        # Arylic and some devices prefer hyphen format
        return source.replace("_", "-")
    elif source_format == "standard" and "-" in source:
        # Standard format prefers underscores
        return source.replace("-", "_")
    
    return source
```

---

## Logging Vendor Context

All log messages include vendor information for troubleshooting:

```python
_LOGGER.debug(
    "API call: endpoint=%s, device=%s, vendor=%s, firmware=%s, attempt=%d/%d",
    endpoint,
    device.host,
    device.capabilities.get("vendor", "unknown"),
    device.firmware_version,
    attempt,
    max_retries,
)
```

---

## Extending for New Vendors

To add support for a new vendor:

1. **Add vendor constant**: `VENDOR_NEW_VENDOR = "new_vendor"`
2. **Add detection logic**: Update `detect_vendor()` function
3. **Add vendor registry entry**: Add capabilities to `VENDOR_REGISTRY`
4. **Add vendor-specific endpoint chains**: Add to `ENDPOINT_REGISTRY` if needed
5. **Add vendor-specific methods**: If needed, add vendor-specific API methods
6. **Update tests**: Add test cases for new vendor
7. **Update documentation**: Document vendor quirks in Device Catalog section

---

## Benefits of This Pattern

1. **Extensibility**: Easy to add new vendors without modifying existing code
2. **Maintainability**: Vendor-specific code is isolated and well-documented
3. **Testability**: Each vendor can be tested independently
4. **Graceful Degradation**: Falls back to standard behavior when vendor-specific behavior fails
5. **Clear Logging**: Vendor context in all log messages for troubleshooting
6. **Endpoint Abstraction**: Logical endpoint names work across all vendors
7. **Automatic Fallback**: Endpoint chains handle variations automatically

---

## Related Documentation

- **[API_DESIGN_PATTERNS.md](API_DESIGN_PATTERNS.md)** - Core API patterns and defensive programming
- **[STATE_MANAGEMENT.md](STATE_MANAGEMENT.md)** - State synchronization (Audio Pro MkII uses UPnP for volume/play state)
- **[UPNP_INTEGRATION.md](UPNP_INTEGRATION.md)** - UPnP integration patterns

