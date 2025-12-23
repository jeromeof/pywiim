# LinkPlay/WiiM Streaming Architecture: Transport Protocols and Control Authority

## Executive Summary

LinkPlay/WiiM devices operate as a **"Split Brain" system** where the locus of control shifts dynamically between the local device and external control points depending on the active transport protocol. This architectural pattern explains why shuffle and repeat controls behave inconsistently across different media sources.

**Key Finding**: The `setPlayerCmd:loopmode` endpoint in the LinkPlay HTTP API is functional **ONLY** when the device acts as the control point (USB, local network files). When playing via AirPlay, Bluetooth, or streaming services, the device becomes a passive renderer or delegated client, and local shuffle/repeat commands either fail silently or update registers that have no effect on actual playback.

## Hardware Foundation: A98 System-on-Module

WiiM devices (Mini, Pro, Pro Plus, Amp, Ultra) and other LinkPlay-based products (Arylic, Audio Pro, iEast) are built on the **A98/A98M System-on-Module (SoM)**. This highly integrated circuit combines Wi-Fi, Bluetooth, and audio processing on a single chip running a customized Linux distribution.

### Memory Constraints and Queue Management

The A98 module operates with finite RAM, directly impacting playlist management:

- **Queue Limit**: Firmware enforces a hard limit of ~1000-2000 tracks in the active playback queue (varies by firmware version and metadata length)
- **Large Library Behavior**: When shuffling a library exceeding this limit (e.g., 11,000 tracks), the device loads a contiguous "window" of tracks surrounding the selected seed and shuffles only that subset
- **Not a Bug**: This is a necessary compromise to prevent Out-Of-Memory (OOM) crashes on embedded hardware
- **External Renderer Mode**: This limitation does NOT apply when the device acts as a renderer for an external controller (AirPlay, Spotify), as the queue resides on the source device/server

## The HTTP API Protocol

The LinkPlay HTTP API is accessed via `http://{device_ip}/httpapi.asp?command={command}` (port 80, plain HTTP only).

### Critical Discovery: SSL/HTTPS Issues

**⚠️ Important**: LinkPlay modules frequently use self-signed certificates or lack proper SSL handshake implementation on the local network interface. Integration platforms (Home Assistant, Music Assistant) must **explicitly force plain HTTP** to ensure reliable command delivery. HTTPS requests often result in connection refusals or aiohttp handshake errors.

### Loop Mode Integer Definitions

The `setPlayerCmd:loopmode:{n}` command controls playback behavior, but **different vendors use different value schemes**:

#### WiiM Devices Loop Mode Values

| Value | Mode Name | Behavior |
|-------|-----------|----------|
| `0` | Loop All | Plays queue in order and repeats indefinitely |
| `1` | Single Loop | Repeats current track indefinitely |
| `2` | Shuffle Loop | Randomizes queue and repeats indefinitely |
| `3` | Shuffle, No Loop | Randomizes queue, plays once, stops |
| `4` | No Shuffle, No Loop | Plays queue in order once, then stops |

#### Arylic Devices Loop Mode Values

| Value | Mode Name | Behavior |
|-------|-----------|----------|
| `0` | SHUFFLE disabled, REPEAT enabled (loop) | Plays queue in order and repeats indefinitely |
| `1` | SHUFFLE disabled, REPEAT enabled (loop once) | Repeats current track indefinitely |
| `2` | SHUFFLE enabled, REPEAT enabled (loop) | Randomizes queue and repeats indefinitely |
| `3` | SHUFFLE enabled, REPEAT disabled | Randomizes queue, plays once, stops |
| `4` | SHUFFLE disabled, REPEAT disabled | Plays queue in order once, then stops |
| `5` | SHUFFLE enabled, REPEAT enabled (loop once) | Shuffle with repeat one |

**Critical Limitation**: These commands are effective **ONLY** when `mode` field in `getPlayerStatus` indicates the device is managing the queue (Mode 10: Network, Mode 11: USB).

**Implementation Note**: The `pywiim` library automatically detects device vendor and uses the correct loop mode mapping. See `pywiim/api/loop_mode.py` for vendor-specific mappings.

## Transport Protocol Analysis: The "Split Brain" System

Control authority shifts based on the active input protocol, creating fundamentally different operational modes.

### Scenario A: AirPlay 2 (Passive Sink)

**Mode Value**: `1` (AirPlay)

**Architecture**:
- Device functions purely as a remote speaker
- Audio stream is pushed from source (iPhone, Mac)
- Device receives audio frames and metadata (Title, Artist) but has **no visibility** into the playback queue

**Queue Sovereignty**:
- Playback queue resides **entirely** in the iOS/macOS device's memory
- WiiM device is not requesting tracks; it's receiving a continuous audio stream

**API Behavior**:
- Sending `setPlayerCmd:loopmode:2` to a device in AirPlay mode is **functionally useless**
- Firmware may accept the command and update an internal register, but since the device doesn't control track progression, shuffle logic is bypassed
- The `plicount` (Playlist Item Count) and `plicurr` (Playlist Current Index) fields return `0` or stale data from previous sessions

**User Interface Impact**:
- WiiM Home App grays out or disables Shuffle/Repeat buttons during AirPlay sessions
- User **must** control shuffle/repeat from the source app (Apple Music, Spotify on iOS)

**Network Topology**:
- Stream path: Router → iPhone → Router → WiiM (double hop)
- Increases network congestion and processing load on source device
- Audio dropouts during multi-speaker AirPlay often indicate phone CPU/Wi-Fi bottleneck, not WiiM limitation

**Control Authority**: **iOS/macOS Source Device**

### Scenario B: Spotify Connect (Hybrid Delegate)

**Mode Value**: `31` (Spotify Connect)

**Architecture**:
- Spotify app on phone hands off a session context (Session ID) to WiiM device
- WiiM connects **directly** to Spotify cloud servers to stream audio
- Device incorporates Spotify Embedded SDK (libspotify or newer variant)

**Queue Sovereignty**:
- Playback queue resides on **Spotify cloud servers**
- WiiM device receives streaming instructions from cloud, not from phone
- Phone app becomes a remote control, not the audio source

**Shuffle Logic**:
- Shuffle state (`SpPlaybackIsShuffled`) is a boolean property of the Spotify **session**, managed by cloud API
- Toggling shuffle requires sending a request to Spotify backend to alter the playback context

**API Disconnect (Critical Integration Issue)**:
- Common failure: Home Assistant sends `media_player.shuffle_set` → triggers LinkPlay `setPlayerCmd:loopmode` command
- **This does NOT consistently trigger the Spotify SDK to update the cloud session**
- Local device register updates, but Spotify cloud continues delivering tracks in original order
- Result: Desynchronization between local state and actual playback behavior

**Smart Shuffle Complication**:
- Spotify's "Smart Shuffle" injects algorithmic recommendations (server-side calculation)
- LinkPlay API cannot represent or control this with simple `loopmode` integers
- Playback order on WiiM may not match Spotify app UI due to this synchronization lag

**Workaround for Automation**:
- **Do NOT use LinkPlay API for Spotify shuffle/repeat**
- Use Spotify Web API (`spotify.shuffle` service in Home Assistant)
- Target the Spotify Device ID of the WiiM, not the LinkPlay Entity ID
- Sends command directly to Spotify servers, ensuring session context updates correctly

**Control Authority**: **Spotify Cloud API**

### Scenario C: USB/Local Playback (Active Controller)

**Mode Value**: `11` (USB) or `10` (Network/DLNA as initiator)

**Note on WiiM Ultra**: The WiiM Ultra supports both USB Input (playing from a drive) and **USB Audio Output (Hardware Mode 6)** for external DACs. This documentation refers to the playback mode (Scenario C) where the device acts as the control point.

**Architecture**:
- WiiM device is the **absolute master** of the playback session
- Device's Linux OS manages the file system, queue indexing, and track progression
- No external control point; device operates autonomously

**Queue Sovereignty**:
- Playback queue stored entirely in device RAM
- Device controls file I/O, decoding, and track sequencing

**API Behavior**:
- `setPlayerCmd:loopmode:2` works **flawlessly**
- Device's OS reorders the playlist index in RAM
- Changes take effect immediately
- `plicount` and `plicurr` accurately reflect queue state

**Hardware Limitation**:
- RAM ceiling of A98 module means "Shuffle All" on 20,000-track library = "Shuffle first 1000 loaded tracks"
- This is **not a software bug** but a **physical hardware constraint**
- Workaround: Offload shuffling to server (Plex, MinimServer) that presents a pre-shuffled linear playlist to WiiM

**Control Authority**: **WiiM Device (Local OS)**

### Scenario D: Bluetooth (Passive Renderer)

**Mode Value**: `5` (Bluetooth)

**Architecture**:
- Similar to AirPlay; device is a wireless speaker
- Audio stream pushed from source device (phone, tablet, laptop)
- WiiM has no queue visibility

**Control Authority**: **Bluetooth Source Device**

### Scenario E: DLNA/UPnP (Context-Dependent)

**Mode Value**: `10` (if WiiM pulls) or varies (if external controller pushes)

**Architecture**:
- **If WiiM initiated**: Device acts as control point (like USB mode) - full API control
- **If external controller** (BubbleUPnP, HA DLNA integration): Device is renderer - limited control

**Control Authority**: **Depends on session initiator**

## Home Assistant Integration Implications

### The Spotify Automation Paradox

**Common User Objective**: Use WiiM as alarm clock playing shuffled Spotify playlist

**Typical Script** (❌ Fails):
1. Set source to Spotify
2. Send `shuffle_set: true` (LinkPlay command)
3. Play playlist

**Why It Fails**:
- Step 2 sends LinkPlay `setPlayerCmd:loopmode` command
- Step 3 initiates Spotify session from cloud
- Spotify cloud session context overrides local shuffle setting
- Or: LinkPlay command sent before Spotify session established, gets ignored

**Correct Approach** (✅ Works):
1. Use `spotify.shuffle` service (Spotify integration)
2. Target Spotify Device ID of WiiM (not LinkPlay Entity ID)
3. Play playlist
4. Command goes directly to Spotify cloud API

### Multi-Room Synchronization

**Architecture**:
- Master device (type: 0) decodes audio and broadcasts **uncompressed PCM** via multicast Wi-Fi to slaves
- Slaves (type: 1) ignore most transport commands
- Synchronization relies on precise clock alignment

**Slave Behavior**:
- When device is slave, `getPlayerStatus` may return Master's status or report `stop` if buffering
- Attempting to control a slave's shuffle/repeat is meaningless (slave is playing raw PCM stream)

## Implementation Strategy for Library Developers

### Context-Aware API Selection

Reliable automation requires **"Check Mode → Select API"** logic:

```python
status = await client.get_player_status_model()
mode = status.mode

if mode == "1":  # AirPlay
    # Cannot control shuffle/repeat from WiiM API
    # User must control from iOS/macOS source device
    return None
    
elif mode == "31":  # Spotify Connect
    # Use Spotify Web API, not LinkPlay API
    # Call Spotify Cloud API with WiiM's Spotify Device ID
    await spotify_api.shuffle(device_id=wiim_spotify_id, state=True)
    
elif mode in ("10", "11"):  # Network/USB - WiiM is control point
    # Full LinkPlay API control available
    await client.set_loop_mode(2)  # Shuffle works
    
else:
    # Bluetooth, DLNA renderer, etc. - external control
    return None
```

### Property Design Pattern (pywiim Library Approach)

```python
@property
def shuffle_supported(self) -> bool:
    """Whether shuffle can be controlled by the device in current state."""
    source = self.source.lower() if self.source else None
    device_controlled = {"usb", "line_in", "optical", "playlist", "preset", "http"}
    return source in device_controlled

@property
def shuffle_state(self) -> bool | None:
    """Shuffle state, or None if not controlled by device."""
    if not self.shuffle_supported:
        return None  # Prevent showing stale/meaningless values
    # ... decode from loop_mode for supported sources
```

This pattern makes the architectural limitation **explicit** rather than hiding it behind misleading return values.

## Implementation Details

### Current Implementation (v2.1.2+)

The library uses a **blacklist approach** (permissive by default):

```python
def _is_device_controlled_source(self) -> bool:
    """Check if current source allows device-controlled playback.
    
    Uses a blacklist approach: most sources support device control,
    but some external sources don't.
    """
    source = self.source
    if source is None:
        return False
    
    source_lower = source.lower()
    
    # Blacklist: Sources where device CANNOT control shuffle/repeat
    external_controlled = {
        "tunein",       # Radio streams - no shuffle/repeat
        "iheartradio",  # Radio streams - no shuffle/repeat
        "multiroom",    # Slave device - can't control playback
    }
    
    if source_lower in external_controlled:
        return False
    
    # Radio-like sources typically don't support controls
    radio_keywords = ["radio", "stream"]
    if any(keyword in source_lower for keyword in radio_keywords):
        return False
    
    return True
```

### Historical Issues and Fixes

**v2.1.2 (November 2025) - Issue #111:**
- **Problem**: Critical misinterpretation of `loop_mode` values
- WiiM and Arylic devices use different loop_mode schemes
- pywiim was treating loop_mode as bitfields, incorrectly flagging loop_mode=3 as invalid
- **Solution**: Added vendor-specific loop mode mappings in `pywiim/api/loop_mode.py`

**v2.1.1 (November 2025):**
- **Problem**: Restrictive whitelist approach blocked too many sources
- **Solution**: Changed to blacklist approach (permissive by default)

**v1.0.71 (January 2025):**
- **Problem**: Sources where external apps control playback returning stale values
- **Solution**: Added source-aware shuffle/repeat control, return `None` for unsupported sources

### The Content Type Problem

**Key Insight**: The source alone doesn't determine support. Content type matters!

**Examples:**
- **Spotify Album/Playlist**: ✅ Should support shuffle/repeat (queue-based)
- **Spotify Radio/Mix**: ❌ Won't work (algorithmic streaming, no fixed queue)
- **Amazon Music Album**: ✅ Should work (user's queue)
- **Amazon Music Station**: ❌ Won't work (algorithm-generated)
- **TuneIn Live Radio**: ❌ Won't work (live stream, no queue)

The `setPlayerCmd:loopmode` endpoint only works when:
- Device is the control point (owns the queue)
- Content is queue-based (not algorithmic streaming)
- Protocol allows device-side control

### Testing Strategy

**⚠️ CRITICAL: Testing Requirements**

Before running shuffle/repeat tests, ensure the device is playing appropriate content:

1. **For Spotify/Apple Music/Amazon Music:**
   - ✅ **Use an album or playlist** - Queue-based content where shuffle/repeat make sense
   - ❌ **NOT a radio station or "Daily Mix"** - These are algorithmic streams with no fixed queue
   - ❌ **NOT podcasts or audiobooks** - Episodic content doesn't support shuffle

2. **How to verify content type:**
   - Check the `media_content_id` in player status
   - `spotify:album:*` or `spotify:playlist:*` → Good for testing
   - `spotify:station:*` or radio-like content → Will NOT work

**Test Script:**
```bash
source .venv/bin/activate
python scripts/test-shuffle-repeat-by-source.py <device_ip>
```

**What to Test:**
- USB, Line In, Optical → ✅ Should work (device owns queue)
- Spotify albums/playlists → ✅ Should work (queue-based)
- Spotify radio/mix → ❌ Won't work (algorithmic)
- AirPlay → ❌ Won't work (iOS controls it)
- Live radio streams → ❌ Won't work (no queue)

### Integration Guidelines

**Home Assistant Pattern:**
```python
@property
def supported_features(self):
    features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
    )
    
    # Only show shuffle/repeat if supported for current source
    if self._player.shuffle_supported:
        features |= MediaPlayerEntityFeature.SHUFFLE_SET
    
    if self._player.repeat_supported:
        features |= MediaPlayerEntityFeature.REPEAT_SET
    
    return features
```

**Best Practices:**
1. **Check support first**: Use `shuffle_supported` / `repeat_supported`
2. **Hide unavailable controls**: Don't show shuffle button if not supported
3. **Handle None gracefully**: Properties return `None` when not supported
4. **Don't cache support**: Check on each state update (source can change)

## Key Takeaways

1. **Context is Everything**: Transport protocol determines control authority, not device capabilities
2. **API is Not Universal**: `setPlayerCmd:loopmode` only works when device is control point
3. **Spotify Requires Cloud API**: Local LinkPlay commands cannot reliably control Spotify sessions
4. **AirPlay is Read-Only**: Device is passive sink; all transport control on source device
5. **RAM Limits are Physical**: ~1000 track shuffle ceiling on A98 hardware cannot be "fixed" in software
6. **Integration Must Be Hybrid**: Successful automation requires protocol-specific API selection logic

## References

This analysis synthesizes findings from:
- LinkPlay A98/A98M hardware datasheets
- WiiM firmware HTTP API documentation
- Community diagnostic logs (Home Assistant, Music Assistant)
- Spotify Embedded SDK integration behaviors
- UPnP/DLNA protocol specifications
- GitHub Issue #111: Shuffle/repeat broken (v2.1.2 fix)
- CHANGELOG entries: v2.1.2, v2.1.1, v1.0.71

## Conclusion

The fragmented control scheme observed in LinkPlay/WiiM devices is not a bug or design flaw—it is **intrinsic** to the architecture of modern streaming protocols. Devices must alternately function as:
- Dumb speakers (AirPlay, Bluetooth)
- Cloud-connected clients (Spotify Connect)
- Standalone players (USB, local network)

Understanding this "Split Brain" behavior and implementing context-aware control logic is essential for successful integration into automation systems. The pywiim library's source-aware shuffle/repeat properties (`shuffle_supported`, `repeat_supported`) expose this architectural reality explicitly, enabling consumers to build robust, predictable automation logic.

