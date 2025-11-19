# Release Process

This document describes the proper release workflow for pywiim.

## Overview

The release process is automated via `scripts/release.sh`, which:
1. Runs all quality checks (formatting, linting, type checking, tests)
2. Updates CHANGELOG.md (moves [Unreleased] → [VERSION])
3. Bumps version number
4. Commits, tags, and pushes to GitHub
5. Creates GitHub release with changelog notes
6. Triggers PyPI publishing (via GitHub Actions)

## Step-by-Step Workflow

### 1. Development

As you work on features/fixes, update `CHANGELOG.md`:

```markdown
## [Unreleased]

### Added
- New feature description

### Fixed
- Bug fix description

### Changed
- Changes to existing functionality
```

**Important:** All changes should be documented under `[Unreleased]` during development.

### 2. Pre-Release Checklist

Before running the release script, ensure:

- [ ] All changes are documented in `CHANGELOG.md` under `[Unreleased]`
- [ ] All code is committed (or intentionally excluded)
- [ ] Working directory is clean (or only has files you want to release)
- [ ] You're on the `main` branch
- [ ] You've pulled latest changes from remote

### 3. Run Release Script

```bash
# For patch version bump (1.0.X → 1.0.X+1)
bash scripts/release.sh patch

# For minor version bump (1.X.0 → 1.X+1.0)
bash scripts/release.sh minor

# For major version bump (X.0.0 → X+1.0.0)
bash scripts/release.sh major
```

### 4. What the Script Does

**Step 1-3: Quality Checks**
- Formats code with `black` and `isort`
- Lints with `ruff` (auto-fixes issues)
- Type checks with `mypy`
- Runs full test suite

**Step 4: Update CHANGELOG**
- Finds `[Unreleased]` section
- Renames it to `[CURRENT_VERSION] - YYYY-MM-DD`
- Adds new empty `[Unreleased]` section above it
- Example:
  ```markdown
  ## [Unreleased]
  
  ## [1.0.68] - 2025-11-18
  
  ### Added
  - Feature that was under [Unreleased]
  ```

**Step 5-6: Bump Version**
- Updates `pyproject.toml`
- Updates `pywiim/__init__.py`
- Verifies both files match

**Step 7-12: Git Operations**
- Stages all changes
- Commits with message: "Release vX.Y.Z"
- Creates git tag `vX.Y.Z`
- Pushes commit and tags to GitHub

**Step 13: GitHub Release**
- Creates GitHub release with changelog notes
- Uses CHANGELOG content for release description
- Triggers PyPI publishing workflow

### 5. Post-Release

After release completes:

1. **Verify GitHub release**: Visit https://github.com/mjcumming/pywiim/releases
2. **Verify PyPI publish**: Check https://pypi.org/project/pywiim/ (may take a few minutes)
3. **Start new development**: Add new changes under `[Unreleased]` in CHANGELOG.md

## Version Numbering (Semantic Versioning)

- **Patch** (1.0.X): Bug fixes, minor improvements, documentation updates
- **Minor** (1.X.0): New features, backwards-compatible changes
- **Major** (X.0.0): Breaking changes, major redesigns

## When to Create RELEASE_NOTES Files

Most releases only need CHANGELOG.md entries. Create a separate `RELEASE_NOTES_x.y.z.md` file when:

### ✅ Create RELEASE_NOTES file when:

1. **Major new features** that need detailed examples
   - Example: Output selection with Bluetooth (v1.0.55)
   - Include usage examples and integration guides

2. **Breaking changes** requiring migration
   - Document what changed and how to migrate
   - Include before/after code examples

3. **Significant API additions** (3+ new public methods/properties)
   - Comprehensive documentation needed
   - Multiple integration scenarios

4. **Performance improvements** worth highlighting
   - Benchmark results, optimization details
   - Impact on existing integrations

5. **Addressing major community issues**
   - Document the problem and solution
   - Reference related GitHub issues

### ⏭️ Skip RELEASE_NOTES file when:

1. **Bug fixes only** - CHANGELOG.md entry is sufficient
2. **Documentation updates** - No functional changes
3. **Internal refactoring** - No API changes
4. **Dependency updates** - Routine maintenance

### RELEASE_NOTES Template

If creating a release notes file, name it `RELEASE_NOTES_x.y.z.md`:

```markdown
# Release Notes - pywiim vx.y.z

**Release Date:** YYYY-MM-DD  
**Tag:** vx.y.z

## Overview

Brief description of the main features/changes...

## Features

### Feature Name

Description and usage examples:

\`\`\`python
# Code example
\`\`\`

## Benefits

- Key benefits for users/integrators

## Migration Guide (if breaking changes)

**Before:**
\`\`\`python
# Old way
\`\`\`

**After:**
\`\`\`python
# New way
\`\`\`

## Installation

\`\`\`bash
pip install --upgrade pywiim
\`\`\`
```

## CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format:

```markdown
## [Unreleased]

## [1.0.68] - 2025-11-18

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes

### Documentation
- Documentation-only changes
```

## Common Issues

### Issue: CHANGELOG Not Updated

**Problem:** Released version has no CHANGELOG entry

**Solution:** The release script now automatically moves `[Unreleased]` to the version section. If you see this error, it means:
1. There was no `[Unreleased]` section in CHANGELOG.md
2. You need to manually add changelog notes before releasing

### Issue: Version Mismatch

**Problem:** `pyproject.toml` and `__init__.py` have different versions

**Solution:** The release script verifies both files match. If they don't:
1. Manually check both files
2. Ensure they both have the same version
3. Re-run the release script

### Issue: GitHub Release Failed

**Problem:** Git push succeeded but GitHub release creation failed

**Solution:** 
1. Check if `gh` CLI is installed: `gh --version`
2. Check if authenticated: `gh auth status`
3. If not authenticated: `gh auth login`
4. Or set `GH_TOKEN` environment variable in `~/.bashrc`

## Manual Release (If Script Fails)

If the automated script fails, you can release manually:

```bash
# 1. Update CHANGELOG.md manually (move [Unreleased] to version)

# 2. Update version files
sed -i 's/version = "1.0.X"/version = "1.0.Y"/' pyproject.toml
sed -i 's/__version__ = "1.0.X"/__version__ = "1.0.Y"/' pywiim/__init__.py

# 3. Commit and tag
git add CHANGELOG.md pyproject.toml pywiim/__init__.py
git commit -m "Release v1.0.Y"
git tag -a "v1.0.Y" -m "Release version 1.0.Y"

# 4. Push
git push && git push --tags

# 5. Create GitHub release (optional)
gh release create "v1.0.Y" --title "Release v1.0.Y" --notes "See CHANGELOG.md"
```

## Automation

### PyPI Publishing

Publishing to PyPI is automated via GitHub Actions:
- Triggered when a new version tag (`v*`) is pushed
- Workflow file: `.github/workflows/publish.yml`
- Requires `PYPI_API_TOKEN` secret in GitHub repo settings

### GitHub Release

GitHub release creation is automated via `release.sh`:
- Requires `gh` CLI installed and authenticated
- Or `GH_TOKEN` environment variable set
- Falls back to manual creation if not available

## Best Practices

1. **Always use the script**: Don't manually bump versions or tag releases
2. **Keep CHANGELOG updated**: Add entries to `[Unreleased]` as you work
3. **Test before releasing**: The script runs tests, but test manually first
4. **Verify after releasing**: Check GitHub releases and PyPI
5. **Document everything**: CHANGELOG is the source of truth for release notes
6. **Use semantic versioning**: Choose patch/minor/major appropriately

## Troubleshooting

If something goes wrong during release:

1. **Don't panic** - Git tags can be deleted and recreated
2. **Check what was pushed**: `git log --oneline -5`
3. **Delete tag if needed**: 
   ```bash
   git tag -d vX.Y.Z         # Delete local tag
   git push --delete origin vX.Y.Z  # Delete remote tag
   ```
4. **Fix the issue** and re-run the script
5. **Ask for help**: Open an issue with details about what failed

