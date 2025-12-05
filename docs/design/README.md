# Design Documentation

This directory contains design documentation, architecture decisions, and implementation patterns for the pywiim library.

## Core Architecture

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - High-level system architecture, components, and design patterns
- **[ARCHITECTURE_DATA_FLOW.md](ARCHITECTURE_DATA_FLOW.md)** - State synchronization, data flow, play state identification, and position handling

## Design Principles

- **[DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md)** - Core design principles, goals, trade-offs, and patterns
- **[LESSONS_LEARNED.md](LESSONS_LEARNED.md)** - Critical design requirements and patterns learned from integration

## Device Compatibility

- **[DEVICE_PROFILES.md](DEVICE_PROFILES.md)** - Device profiles system, vendor detection, endpoint abstraction, device catalog, and compatibility matrix
- **[PROTOCOL_DETECTION.md](PROTOCOL_DETECTION.md)** - Protocol/port detection strategy and endpoint caching

## API & Integration

- **[API_DESIGN_PATTERNS.md](API_DESIGN_PATTERNS.md)** - API reliability matrix, defensive programming, and endpoint patterns
- **[UPNP_INTEGRATION.md](UPNP_INTEGRATION.md)** - UPnP integration patterns, architecture, and health tracking
- **[LINKPLAY_ARCHITECTURE.md](LINKPLAY_ARCHITECTURE.md)** - LinkPlay "split brain" system, transport protocols, shuffle/repeat support, and control authority

## Implementation Patterns

- **[OPERATION_PATTERNS.md](OPERATION_PATTERNS.md)** - State-changing operation patterns (trust API, handle preconditions)
- **[SOURCE_ENUMERATION_VS_SELECTION.md](SOURCE_ENUMERATION_VS_SELECTION.md)** - Two-layer source system (enumerable vs selectable)

## Documentation Status

All design documentation has been consolidated and updated as of 2025-01-XX:
- ✅ Merged overlapping documents
- ✅ Removed outdated information
- ✅ Updated cross-references
- ✅ Consolidated from 15 files to 12 files

See [CONSOLIDATION_PLAN.md](CONSOLIDATION_PLAN.md) for details on the consolidation process.
