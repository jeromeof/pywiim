# Requirements Document

## Functional Requirements

### FR1: Device Communication
- **FR1.1**: Library must support HTTP API communication with WiiM and LinkPlay devices
- **FR1.2**: Library must support UPnP/DLNA event subscriptions for real-time updates
- **FR1.3**: Library must handle both HTTP and HTTPS protocols
- **FR1.4**: Library must support SSL/TLS with self-signed certificates for Audio Pro devices
- **FR1.5**: Library must support client certificate authentication for Audio Pro MkII devices
- **FR1.6**: Library must synchronize state from HTTP polling and UPnP events intelligently
  - Merge overlapping data with conflict resolution
  - Handle stale data (ignore if outside freshness window)
  - Handle missing data (fill from other source)
  - Preserve metadata during transitions
  - Track source availability and health
- **FR1.7**: Library must provide polling strategy recommendations and helpers
  - Recommend optimal polling intervals based on device state and capabilities
  - Provide conditional fetching helpers (device info, multiroom, metadata, EQ)
  - Support parallel execution of independent API calls
  - Framework-agnostic (applications manage their own polling loops)

### FR2: Device Discovery and Identification
- **FR2.1**: Library must identify vendor (WiiM, Arylic, Audio Pro, Generic LinkPlay)
- **FR2.2**: Library must identify device type (WiiM vs Legacy Audio Pro)
- **FR2.3**: Library must detect firmware version
- **FR2.4**: Library must detect Audio Pro generation (mkii, w_generation, original)
  - **Critical**: MkII and W-Generation have significantly different endpoint support
- **FR2.5**: Library must apply vendor-specific capabilities and quirks
- **FR2.6**: Library must use endpoint abstraction to handle vendor/generation variations
- **FR2.7**: Library must support device discovery via UPnP/Zeroconf (optional)

### FR3: Playback Control
- **FR3.1**: Library must support play, pause, stop commands
- **FR3.2**: Library must support next/previous track navigation
- **FR3.3**: Library must support seek/position control
- **FR3.4**: Library must support volume control (0-100)
- **FR3.5**: Library must support mute/unmute
- **FR3.6**: Library must support shuffle and repeat modes

### FR4: Media Information
- **FR4.1**: Library must retrieve current track metadata (title, artist, album)
- **FR4.2**: Library must retrieve playback position and duration
- **FR4.3**: Library must retrieve album artwork URLs
- **FR4.4**: Library must retrieve current source/input
- **FR4.5**: Library must handle metadata from various streaming services

### FR5: Multiroom/Grouping
- **FR5.1**: Library must support creating speaker groups
- **FR5.2**: Library must support joining/leaving groups
- **FR5.3**: Library must support synchronized playback across groups
- **FR5.4**: Library must retrieve group membership information
- **FR5.5**: Library must support master/slave role management

### FR6: Audio Settings
- **FR6.1**: Library must support equalizer control (10-band EQ)
- **FR6.2**: Library must support EQ presets
- **FR6.3**: Library must support audio output mode selection (Line Out, Optical, Coax, Bluetooth)
- **FR6.4**: Library must support channel balance adjustment (unofficial)
- **FR6.5**: Library must support SPDIF delay settings (unofficial)

### FR7: Presets
- **FR7.1**: Library must support hardware preset buttons (device dependent, up to 20)
- **FR7.2**: Library must support preset playback
- **FR7.3**: Library must retrieve preset information

### FR8: Device Management
- **FR8.1**: Library must retrieve device information (model, firmware, MAC, UUID)
- **FR8.2**: Library must support device reboot (unofficial)
- **FR8.3**: Library must support diagnostics information retrieval
- **FR8.4**: Library must support firmware update checking

### FR9: Bluetooth (Unofficial)
- **FR9.1**: Library must support Bluetooth device scanning (unofficial)
- **FR9.2**: Library must support Bluetooth pairing (unofficial)

### FR10: LMS Integration (Unofficial)
- **FR10.1**: Library must support LMS server discovery (unofficial)
- **FR10.2**: Library must support LMS server connection (unofficial)
- **FR10.3**: Library must support LMS auto-connect configuration (unofficial)

## Non-Functional Requirements

### NFR1: Performance
- **NFR1.1**: HTTP requests must complete within 5 seconds (configurable timeout)
- **NFR1.2**: UPnP event subscriptions must be established within 10 seconds
- **NFR1.3**: Library must support connection pooling via custom aiohttp sessions
- **NFR1.4**: Library must minimize network traffic (use UPnP events when available)

### NFR2: Reliability
- **NFR2.1**: Library must implement retry logic with exponential backoff
- **NFR2.2**: Library must gracefully handle network failures
- **NFR2.3**: Library must gracefully handle device unavailability
- **NFR2.4**: Library must support fallback mechanisms (UPnP → HTTP polling)
- **NFR2.5**: Library must handle firmware variations gracefully

### NFR3: Compatibility
- **NFR3.1**: Library must support Python 3.11+
- **NFR3.2**: Library must support all WiiM device models
- **NFR3.3**: Library must support Legacy Audio Pro devices
- **NFR3.4**: Library must handle firmware version differences
- **NFR3.5**: Library must be framework-agnostic (no Home Assistant dependencies)

### NFR4: Dependencies
- **NFR4.1**: Library must have minimal dependencies (aiohttp, pydantic, async-upnp-client)
- **NFR4.2**: Library must not require optional dependencies for core functionality
- **NFR4.3**: Library must use standard Python libraries where possible

### NFR5: Memory
- **NFR5.1**: Library must be memory-efficient
- **NFR5.2**: Library must support connection pooling to reduce resource usage
- **NFR5.3**: Library must clean up resources properly (context managers, async cleanup)

## Quality Requirements

### QR1: Code Quality
- **QR1.1**: All code must follow PEP 8 style guidelines (enforced by Black)
- **QR1.2**: All code must pass Ruff linting (E, W, F, I, B, C4, UP rules)
- **QR1.3**: All public APIs must have type hints
- **QR1.4**: All public APIs must have docstrings (Google style)
- **QR1.5**: Files must not exceed 600 LOC (hard limit, 400 LOC soft limit)
- **QR1.6**: Code must have 90%+ test coverage

### QR2: Type Safety
- **QR2.1**: All function signatures must have type hints
- **QR2.2**: All data models must use Pydantic v2
- **QR2.3**: Type checking must pass with mypy (strict mode where possible)
- **QR2.4**: All API responses must be validated with Pydantic models

### QR3: Error Handling
- **QR3.1**: All errors must use custom exception hierarchy
- **QR3.2**: All exceptions must include device context (host, firmware, model)
- **QR3.3**: All errors must be logged with full context before raising
- **QR3.4**: Library must never crash on device variations (graceful degradation)

### QR4: Logging
- **QR4.1**: All log messages must include device context (host, firmware)
- **QR4.2**: Capability detection decisions must be logged
- **QR4.3**: State transitions must be logged with triggers
- **QR4.4**: Performance metrics (>100ms operations) must be logged
- **QR4.5**: Errors must be logged with full context

### QR5: Documentation
- **QR5.1**: README must include installation and usage examples
- **QR5.2**: All public APIs must have comprehensive docstrings
- **QR5.3**: Architecture must be documented in ARCHITECTURE.md
- **QR5.4**: Device compatibility must be documented in DEVICE_VARIATIONS.md
- **QR5.5**: Development workflow must be documented in CONTRIBUTING.md

### QR6: Testing
- **QR6.1**: Unit tests must mock all external dependencies (HTTP, UPnP)
- **QR6.2**: Test coverage must be 90%+
- **QR6.3**: All API endpoints must have tests
- **QR6.4**: All error paths must have tests
- **QR6.5**: All model validation must have tests
- **QR6.6**: Capability detection must have tests

## Lessons Learned

See `LESSONS_LEARNED.md` for detailed analysis of challenges encountered in the integration and how the library design addresses them proactively.

Key lessons:
- State synchronization between HTTP and UPnP is critical and complex
- Audio Pro devices require special handling (client certs, protocol detection, endpoint variations)
- Metadata preservation during transitions is essential
- UPnP health checking is unreliable (events only on changes)
- Endpoint variations require abstraction and fallback chains
- Discovery must be robust with multi-protocol fallback
- Error handling must be comprehensive with smart logging

## Device Compatibility Matrix

### Supported Devices

#### WiiM Devices
- **WiiM Pro** - Full feature support
- **WiiM Mini** - Full feature support
- **WiiM Amp** - Full feature support

#### Arylic Devices
- **Arylic Up2Stream Amp 2.0/2.1** - Full feature support (vendor-specific LED commands)
- **Arylic S10+** - Full feature support (vendor-specific LED commands)

#### Audio Pro Devices
- **Audio Pro Addon C5/C10 (Original)** - Limited support (Legacy, basic endpoints)
- **Audio Pro Addon C5 MkII (Generation 1)** - Very limited support (requires client cert, different endpoints)
  - Uses getStatusEx only (does NOT support getPlayerStatusEx)
  - Does NOT support: getMetaInfo, EQ, presets
  - May use alternative endpoint paths (/api/status, /cgi-bin/status.cgi)
- **Audio Pro Addon C5A/C10A (Generation 2 - W-Generation)** - Enhanced support
  - Supports getPlayerStatusEx (preferred)
  - May support getMetaInfo (probe to confirm)
  - Better multiroom support

#### Generic LinkPlay Devices
- **Other LinkPlay-based devices** - Capabilities probed at runtime

### Firmware Requirements
- **WiiM devices**: Firmware 4.0+ recommended
- **Legacy devices**: Various firmware versions (capability detection required)

### Known Limitations
- Audio Pro MkII: Requires client certificate for HTTPS
- Audio Pro MkII: getMetaInfo support varies by firmware/model (probe to confirm)
- Audio Pro MkII: Does not support EQ commands
- Audio Pro MkII: Does not support presets
- Some devices: HTTP volume control not available (use UPnP)
- Some devices: Play state not available via HTTP (use UPnP)

See DEVICE_VARIATIONS.md for detailed device-specific quirks and workarounds.

