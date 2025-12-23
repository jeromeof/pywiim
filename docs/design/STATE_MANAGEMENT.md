# State Management and Master→Slave Propagation

## Overview

In multi-room groups, the master device controls playback and metadata. Slaves follow the master's state. The `pywiim` library implements automatic metadata propagation from master to slaves to ensure slaves always display the correct playback information.

## Master→Slave State Propagation

### How It Works

When a master device's state changes (via UPnP event or HTTP refresh), the master automatically propagates its metadata to all linked slaves:

1. **Master state update** - Master receives UPnP event or completes HTTP refresh
2. **Propagation trigger** - `GroupOperations.propagate_metadata_to_slaves()` is called
3. **Slave state update** - Each slave's state synchronizer is updated with master's metadata
4. **Callback notification** - Slaves trigger `on_state_changed` callbacks to notify integrations

### Propagated Fields

The following fields are propagated from master to slaves:

- **Metadata**: `title`, `artist`, `album`, `image_url`
- **Audio-quality metadata** (from `getMetaInfo`, cached as `player.metadata`): `sampleRate`, `bitDepth`, `bitRate`
- **Playback state**: `play_state`, `position`, `duration`

### Source Identification: `source="propagated"`

To distinguish master-propagated state from a slave's own device state, propagated updates use `source="propagated"` instead of the default `source="http"`. This is critical for proper conflict resolution when:

- Master propagates metadata to slave
- Slave simultaneously receives its own UPnP event or HTTP refresh
- Both updates arrive at the slave's state synchronizer

#### Race Condition Handling

When a slave receives both:
- Propagated state from master (`source="propagated"`)
- Its own device state (`source="http"` or `source="upnp"`)

The conflict resolution logic prefers `source="propagated"` for metadata fields because:
- **Master is authoritative** - In multi-room groups, the master controls playback
- **Prevents stale data** - Slave's own device state may be outdated or incomplete
- **Ensures consistency** - All slaves display the same metadata as the master

### Conflict Resolution

The `StateSynchronizer` handles conflicts between propagated and local state:

#### For Metadata Fields (`title`, `artist`, `album`, `image_url`)

1. **Propagated state is preferred** - If `http_field.source == "propagated"`, it wins over UPnP
2. **Master is authoritative** - This ensures slaves always match master's metadata
3. **Prevents race conditions** - Even if slave's UPnP event arrives first, propagated state takes precedence

#### For Other Fields

- `play_state`, `position`, `duration` - Propagated from master, but conflict resolution follows normal rules
- `volume`, `muted` - Not propagated (each device maintains its own volume)
- `source` - Not propagated (each device may have different audio sources)

### Implementation Details

#### Propagation Method

```python
def propagate_metadata_to_slaves(self) -> None:
    """Propagate metadata from master to all linked slaves."""
    # ... validation ...
    
    # Update state synchronizer with master's metadata
    # Use source="propagated" to distinguish from slave's own device state
    slave._state_synchronizer.update_from_http(
        {
            "title": master_status.title,
            "artist": master_status.artist,
            # ... other fields ...
        },
        source="propagated",  # Key: identifies this as master-propagated state
    )
    
    # Trigger callback so integrations update
    if slave._on_state_changed:
        slave._on_state_changed()
```

#### State Synchronizer Update

The `StateSynchronizer.update_from_http()` method accepts an optional `source` parameter:

```python
def update_from_http(
    self,
    data: dict[str, Any],
    timestamp: float | None = None,
    source: str = "http",  # Default for normal HTTP polling
) -> None:
    # Creates TimestampedField with specified source
    self._http_state[field_name] = TimestampedField(
        value=value,
        source=source,  # "http" or "propagated"
        timestamp=ts,
    )
```

#### Conflict Resolution Logic

In `StateSynchronizer._resolve_conflict()`:

```python
# For metadata fields, prefer propagated source
if field_name in ["title", "artist", "album", "image_url"]:
    if http_field.source == "propagated" and upnp_field:
        # Master-propagated state wins over slave's own UPnP event
        return http_field
    # ... continue with normal resolution ...
```

### Callback Behavior

When master propagates metadata to slaves:

1. **Slave state synchronizer is updated** - Metadata stored with `source="propagated"`
2. **State merge occurs** - Conflict resolution prefers propagated state
3. **Callback is triggered** - `slave._on_state_changed()` is called
4. **Integration updates** - Home Assistant or other integrations receive notification

**Important**: Callbacks are intentionally triggered. This ensures integrations (like Home Assistant) update their entity state when master metadata changes, even though the slave device itself didn't change.

### Testing Considerations

When testing propagation:

1. **Verify source identification** - Check that propagated updates use `source="propagated"`
2. **Test race conditions** - Simulate simultaneous propagation and slave UPnP events
3. **Verify conflict resolution** - Ensure propagated state wins for metadata
4. **Check callback behavior** - Verify callbacks fire and don't cause cascades

### Benefits

1. **Consistency** - All slaves display the same metadata as master
2. **Real-time updates** - Slaves update immediately when master state changes
3. **Race condition handling** - `source="propagated"` ensures correct conflict resolution
4. **Integration support** - Callbacks notify integrations of state changes

### Limitations

1. **Volume not propagated** - Each device maintains its own volume level
2. **Source not propagated** - Each device may have different audio sources
3. **One-way propagation** - Only master → slave, not slave → master
4. **Requires linked Player objects** - Propagation only works when Player objects are linked via `Group`

## Related Documentation

- [ARCHITECTURE_DATA_FLOW.md](./ARCHITECTURE_DATA_FLOW.md) - Overall state architecture
- [UPNP_INTEGRATION.md](./UPNP_INTEGRATION.md) - UPnP event handling
- [API_DESIGN_PATTERNS.md](./API_DESIGN_PATTERNS.md) - Group role logic

