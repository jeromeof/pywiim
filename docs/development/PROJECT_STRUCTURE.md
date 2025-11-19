# Project Structure

This document describes the organization and structure of the `pywiim` project.

## Directory Structure

```
pywiim/
├── pywiim/                    # Main package
│   ├── __init__.py            # Public API exports
│   ├── client.py              # Main WiiMClient facade
│   ├── exceptions.py          # Exception classes
│   ├── models.py              # Pydantic models
│   ├── capabilities.py        # Capability detection
│   ├── state.py               # State synchronization
│   ├── discovery.py           # Discovery module
│   ├── cli/                   # Command-line tools
│   │   ├── __init__.py
│   │   ├── diagnostics.py     # Diagnostic CLI tool
│   │   ├── discovery_cli.py   # Discovery CLI tool
│   │   ├── monitor_cli.py    # Real-time monitoring CLI
│   │   ├── verify_cli.py      # Feature verification CLI
│   │   ├── group_test_cli.py # Group testing CLI
│   │   └── join_test_cli.py   # Join/unjoin testing CLI
│   ├── api/                   # API mixin modules
│   │   ├── __init__.py
│   │   ├── base.py            # Base HTTP client
│   │   ├── parser.py          # Response parser
│   │   ├── constants.py       # API constants
│   │   ├── endpoints.py       # Endpoint abstraction
│   │   ├── device.py          # Device operations
│   │   ├── playback.py         # Playback controls
│   │   ├── group.py            # Multiroom groups
│   │   ├── eq.py              # Equalizer
│   │   ├── preset.py          # Presets
│   │   ├── diagnostics.py     # Diagnostics API
│   │   ├── bluetooth.py       # Bluetooth
│   │   ├── audio_settings.py  # Audio settings
│   │   ├── lms.py             # LMS integration
│   │   ├── misc.py            # Miscellaneous
│   │   ├── firmware.py        # Firmware info
│   │   └── timer.py           # Timer/alarm
│   └── upnp/                  # UPnP modules
│       ├── __init__.py
│       ├── client.py          # UPnP client
│       └── eventer.py         # UPnP event handler
│
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures
│   ├── README.md              # Test documentation
│   ├── unit/                  # Unit tests (mocked)
│   │   ├── __init__.py
│   │   ├── test_client.py
│   │   └── test_exceptions.py
│   └── integration/           # Integration tests (real devices)
│       ├── __init__.py
│       └── test_real_device.py
│
├── docs/                      # Documentation
│   ├── user/                  # User documentation
│   │   ├── QUICK_START.md     # Quick start guide
│   │   ├── EXAMPLES.md        # Code examples
│   │   └── DISCOVERY.md       # Discovery tool guide
│   └── integration/           # Integration guides
│       ├── API_REFERENCE.md   # Complete API reference
│       └── HA_INTEGRATION.md  # Home Assistant integration
│
├── scripts/                   # Utility scripts (optional)
│   └── test_my_devices.py     # Quick device test script
│
├── .github/                   # GitHub configuration (if using)
│   └── workflows/             # CI/CD workflows
│
├── pyproject.toml             # Project configuration
├── Makefile                   # Development commands
├── .pre-commit-config.yaml    # Pre-commit hooks
├── .gitignore                 # Git ignore rules
├── .gitattributes             # Git attributes
├── LICENSE                    # License file
├── README.md                  # Main README
│
└── docs/                      # Design & architecture docs (root level)
    ├── ANALYSIS.md            # Source code analysis
    ├── ARCHITECTURE.md        # Architecture documentation
    ├── DESIGN_PRINCIPLES.md   # Design principles and goals
    ├── REQUIREMENTS.md        # Requirements specification
    ├── DEVICE_VARIATIONS.md   # Vendor detection and endpoint abstraction
    ├── STATE_MANAGEMENT.md    # State synchronization and play state handling
    ├── LESSONS_LEARNED.md     # Lessons from HA integration
    └── integration/
        └── HA_INTEGRATION.md # HA integration guide
    ├── MISSING_FEATURES.md    # Missing features analysis
    ├── TESTING_DEVICES.md     # Testing guide
    ├── DIAGNOSTICS.md         # Diagnostic tool guide
    ├── CONTRIBUTING.md        # Contribution guidelines
    ├── DEVELOPMENT.md         # Development standards
    └── PROJECT_STATUS.md      # Project status
```

## File Organization Principles

### 1. Package Structure (`pywiim/`)

**Core Modules** (root of package):
- `client.py` - Main facade (composes all mixins)
- `exceptions.py` - Exception hierarchy
- `models.py` - Pydantic models
- `capabilities.py` - Capability detection
- `state.py` - State synchronization
- `discovery.py` - Discovery module

**CLI Tools** (`pywiim/cli/`):
- `diagnostics.py` - Comprehensive diagnostic tool
- `discovery_cli.py` - Device discovery tool
- `monitor_cli.py` - Real-time player monitoring
- `verify_cli.py` - Feature verification and testing
- `group_test_cli.py` - Group operations testing
- `join_test_cli.py` - Join/unjoin operations testing

**API Modules** (`pywiim/api/`):
- All API mixin modules
- Base client and parser
- Constants and endpoints

**UPnP Modules** (`pywiim/upnp/`):
- UPnP client and event handler

### 2. Documentation Structure

**User Documentation** (`docs/user/`):
- Quick start guides
- API reference
- Code examples
- Tool documentation
- Requirements

**Design Documentation** (`docs/design/`):
- Architecture and design decisions
- Patterns and best practices
- Lessons learned
- Design principles

**Development Guides** (`docs/development/`):
- Setup instructions
- Development standards
- Testing guides
- Project structure

**Integration Guides** (`docs/integration/`):
- Framework integration patterns
- Home Assistant integration
- Polling architecture

**Working Documents** (`docs/working/`):
- Temporary analysis and discussions
- Design reviews
- Status tracking
- May be archived or deleted when no longer needed

### 3. Test Structure

**Unit Tests** (`tests/unit/`):
- Mocked tests
- Fast execution
- High coverage

**Integration Tests** (`tests/integration/`):
- Real device tests
- Marked with `@pytest.mark.slow`
- Optional execution

### 4. Scripts and Tools

**Utility Scripts** (`scripts/` or root):
- Quick test scripts
- Development helpers
- Not part of package distribution

## File Size Guidelines

- **Soft Limit**: 400 lines of code
- **Hard Limit**: 600 lines of code
- **Exceeding Hard Limit**: Requires `# pragma: allow-long-file <issue>` and justification

## Naming Conventions

### Files
- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

### Directories
- **Packages**: `snake_case` (no underscores per project convention)
- **Tests**: `tests/` with subdirectories

## Import Organization

1. Standard library imports
2. Third-party imports
3. Local imports (pywiim)
4. Type-only imports (if using `TYPE_CHECKING`)

## Documentation Organization

All documentation is organized in `docs/` with clear subdirectories:

- **User-Facing** (`docs/user/`): Guides for library users
- **Design** (`docs/design/`): Architecture and design decisions (includes device compatibility in DEVICE_VARIATIONS.md)
- **Development** (`docs/development/`): Guides for contributors
- **Integration** (`docs/integration/`): Framework integration guides
- **Working** (`docs/working/`): Temporary working documents

See `docs/README.md` for detailed navigation.

## Current Organization Status

### Overall Assessment: ✅ **Well Organized**

The project follows good Python packaging practices and maintains clear separation of concerns.

### ✅ Strengths

**Package Structure:**
- Clear module organization: `pywiim/`, `pywiim/api/`, `pywiim/upnp/`
- Logical grouping: Related functionality grouped together
- Public API: Clean exports in `__init__.py`
- Mixin pattern: Well-organized API mixins

**Documentation Structure:**
- User docs: Organized in `docs/` directory
- Design docs: Comprehensive design documentation
- Clear separation: User-facing vs developer-facing docs

**Test Structure:**
- Unit tests: Separate from integration tests
- Fixtures: Centralized in `conftest.py`
- Documentation: Test README explains structure

**Tooling:**
- CLI tools: Organized in `pywiim/cli/`, properly configured in `pyproject.toml`
- Code quality: Pre-commit hooks, Makefile
- Type hints: PEP 561 support (`py.typed`)

### ⚠️ Areas for Improvement

**File Size Compliance:**

Some files exceed recommended limits:

| File | Lines | Limit | Status |
|------|-------|-------|--------|
| `api/base.py` | 988 | 600 (hard) | ❌ **Exceeds hard limit** |
| `upnp/eventer.py` | 618 | 600 (hard) | ❌ **Exceeds hard limit** |
| `upnp/client.py` | 594 | 600 (hard) | ⚠️ **Close to limit** |
| `state.py` | 558 | 400 (soft) | ⚠️ **Exceeds soft limit** |
| `capabilities.py` | 500 | 400 (soft) | ⚠️ **Exceeds soft limit** |

**Recommendations:**
- `api/base.py`: Consider splitting transport layer from client logic
- `upnp/eventer.py`: Could extract event parsing to separate module
- `state.py`: Consider splitting synchronization from state models
- `capabilities.py`: Could split detection from registry

**Note**: Some files may be acceptable if they're cohesive and difficult to split. Document justification if keeping as-is.

**Scripts Organization:**
- Current: `test_my_devices.py` moved to `scripts/` ✅
- Recommendation: Create `scripts/README.md` explaining utility scripts

**Missing Files:**
- ✅ `CHANGELOG.md` - Added
- ✅ `PROJECT_STRUCTURE.md` - Added
- `.github/workflows/` - CI/CD workflows (if using GitHub)
- `py.typed` - PEP 561 marker (added to package-data)

### 📊 Statistics

- **Total Python LOC**: ~8,500 lines
- **Package modules**: 30+ files
- **API mixins**: 12 modules
- **Test files**: 4+ files
- **Documentation**: 20+ markdown files

### ✅ Compliance Checklist

- [x] Clear package structure
- [x] Logical module organization
- [x] Proper public API exports
- [x] Test structure (unit + integration)
- [x] Documentation organization
- [x] Code quality tooling
- [x] Type hints support
- [x] CLI tools configured
- [x] Git configuration
- [x] Pre-commit hooks
- [ ] File size compliance (some files exceed limits)
- [x] CHANGELOG.md
- [x] Project structure documentation

## Maintenance

This structure should be maintained as the project grows:
- New API modules go in `pywiim/api/`
- New UPnP features go in `pywiim/upnp/`
- New models go in `pywiim/models.py` (or new file if large)
- New CLI tools go in `pywiim/cli/`
- Utility scripts go in `scripts/` (not part of package)
- Documentation follows the structure above

