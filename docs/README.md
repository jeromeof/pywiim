# Documentation

This directory contains all project documentation, organized by purpose and audience.

## Structure

### 📖 [User Documentation](user/)
Documentation for end users of the library:
- **QUICK_START.md** - Get started quickly
- **EXAMPLES.md** - Code examples
- **DISCOVERY.md** - Device discovery guide
- **DIAGNOSTICS.md** - Diagnostic tool guide
- **REQUIREMENTS.md** - Requirements specification

### 🏗️ [Design & Architecture](design/)
Design documentation, architecture decisions, and patterns:
- **ARCHITECTURE.md** - System architecture overview
- **DESIGN_PRINCIPLES.md** - Design principles, goals, and patterns
- **DEVICE_VARIATIONS.md** - Vendor detection, endpoint abstraction, and device compatibility
- **STATE_MANAGEMENT.md** - State synchronization, play state identification, position tracking, and caching

- **LESSONS_LEARNED.md** - Key lessons from HA integration
- **API_DESIGN_PATTERNS.md** - API design patterns and defensive programming
- **UPNP_INTEGRATION.md** - UPnP integration patterns and architecture
- **SOURCE_ENUMERATION_VS_SELECTION.md** - Source system documentation
- **OPERATION_PATTERNS.md** - Operation implementation patterns (trust API, handle preconditions)
- **PROTOCOL_DETECTION.md** - Protocol/port detection strategy

### 💻 [Development Guides](development/)
Guides for developers working on the project:
- **DEVELOPMENT.md** - Development setup, standards, and practices
- **PROJECT_STRUCTURE.md** - Project organization and structure reference
- **TESTING_BEST_PRACTICES.md** - Comprehensive testing guide
- **TESTING_DEVICES.md** - Testing with real devices

### 🔌 [Integration Guides](integration/)
Guides for integrating the library with frameworks:
- **HA_INTEGRATION.md** - Home Assistant integration guide (polling, session management, UPnP)
- **API_REFERENCE.md** - Complete API reference

### 🔨 [Working Documents](working/)
Temporary working documents, analysis, and discussions:
- **TODO_STATUS.md** - TODO status tracking

**Note**: Working documents are temporary and may be archived or deleted once their purpose is fulfilled.

## Quick Navigation

- **New to the project?** Start with [QUICK_START.md](user/QUICK_START.md)
- **Want to understand the design?** Read [ARCHITECTURE.md](design/ARCHITECTURE.md)
- **Setting up development?** See [DEVELOPMENT.md](development/DEVELOPMENT.md)
- **Integrating with Home Assistant?** Check [HA_INTEGRATION.md](integration/HA_INTEGRATION.md)
- **Looking for device compatibility?** See [DEVICE_VARIATIONS.md](design/DEVICE_VARIATIONS.md)

## Documentation Standards

- **User docs**: Clear, example-driven, assume minimal prior knowledge
- **Design docs**: Technical depth, explain decisions and trade-offs
- **Development docs**: Practical guides for contributors
- **Working docs**: Temporary analysis and discussions

## Contributing to Documentation

When adding new documentation:
1. Determine the appropriate category (user/design/development/integration/working)
2. Follow existing documentation style
3. Update this README if adding new major sections
4. Move temporary analysis to `working/` directory
5. Follow naming conventions: Use UPPER_SNAKE_CASE for file names

## Documentation Organization

This documentation is organized by purpose and audience:

- **User Documentation** (`user/`): End-user guides, API reference, examples, and tool documentation
- **Design Documentation** (`design/`): Architecture decisions, design patterns, and technical deep-dives
- **Development Guides** (`development/`): Setup guides, standards, and practices for contributors
- **Integration Guides** (`integration/`): Framework-specific integration documentation
- **Working Documents** (`working/`): Temporary analysis, discussions, and status tracking

**Note**: Working documents are temporary and may be archived or deleted once their purpose is fulfilled.

