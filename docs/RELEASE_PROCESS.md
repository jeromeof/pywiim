# Release Process

This document describes the proper release workflow for pywiim.

## Overview

The release process is automated via `make release VERSION=X.Y.Z`, which:
1. **Verifies and updates version** in `pyproject.toml` to match the release version
2. Runs all quality checks (formatting, linting, type checking, tests)
3. Commits any uncommitted changes
4. Verifies version still matches before tagging (prevents PyPI publish failures)
5. Pushes commits to GitHub
6. Creates and pushes git tag
7. Triggers PyPI publishing (via GitHub Actions)

**⚠️ CRITICAL:** The version in `pyproject.toml` MUST match the VERSION you specify. The Makefile now automatically updates it, but always verify before tagging.

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

### 3. Run Release Command

```bash
# Use make release with explicit version number
make release VERSION=2.1.53
```

**⚠️ IMPORTANT:** 
- Always specify the exact version number (e.g., `2.1.53`, not `2.1.52+1`)
- The Makefile will automatically update `pyproject.toml` if it doesn't match
- Version will be verified again before tagging to prevent PyPI publish failures

### 4. What the Release Process Does

**Step 0: Version Verification and Update**
- Checks if `pyproject.toml` version matches the release VERSION
- If mismatch detected: automatically updates `pyproject.toml` and commits the change
- If match: proceeds with release
- **This prevents PyPI publish failures** (e.g., "File already exists" errors)

**Step 1: Quality Checks**
- Checks import sorting with `isort`
- Lints with `ruff`
- Type checks with `mypy`
- Runs full unit test suite

**Step 2: Commit Uncommitted Changes**
- Stages all uncommitted changes
- Commits with message: "chore: prepare release vX.Y.Z"
- If working directory is clean, skips this step

**Step 3: Final Version Verification**
- **CRITICAL STEP:** Verifies `pyproject.toml` version still matches VERSION
- If mismatch: aborts with error (prevents PyPI publish failure)
- This ensures the tag points to code with the correct version

**Step 4: Push Commits**
- Pushes all commits to `origin/main`

**Step 5: Create and Push Tag**
- Creates annotated git tag `vX.Y.Z`
- Pushes tag to GitHub
- Triggers GitHub Actions workflow for PyPI publishing

**Note:** CHANGELOG.md should be updated manually before running `make release`. The Makefile does not automatically update CHANGELOG.md.

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

**Problem:** `pyproject.toml` version doesn't match the release VERSION

**Solution:** The Makefile now automatically handles this:
1. **Automatic fix:** If `pyproject.toml` has a different version, it will be updated automatically
2. **Verification:** Version is checked again before tagging to prevent PyPI failures
3. **If still failing:** Manually check `pyproject.toml` and ensure it matches the VERSION you're releasing

**Common Error:** "File already exists" on PyPI
- **Cause:** Tag was created with wrong version in `pyproject.toml`
- **Prevention:** The Makefile now verifies version before tagging
- **Fix if it happens:**
  ```bash
  # Delete the tag
  git tag -d vX.Y.Z
  git push origin :refs/tags/vX.Y.Z
  
  # Update pyproject.toml version
  # Recreate tag pointing to commit with correct version
  git tag -a vX.Y.Z -m "Release vX.Y.Z"
  git push origin vX.Y.Z
  ```

### Issue: GitHub Release Failed

**Problem:** Git push succeeded but GitHub release creation failed

**Solution:** 
1. Check if `gh` CLI is installed: `gh --version`
2. Check if authenticated: `gh auth status`
3. If not authenticated: `gh auth login`
4. Or set `GH_TOKEN` environment variable in `~/.bashrc`

## Manual Release (If Makefile Fails)

If `make release` fails, you can release manually:

```bash
# 1. Update CHANGELOG.md manually (move [Unreleased] to version)

# 2. Update version in pyproject.toml (CRITICAL - must match tag!)
sed -i 's/version = ".*"/version = "2.1.53"/' pyproject.toml

# 3. Verify version matches
grep '^version = ' pyproject.toml  # Should show: version = "2.1.53"

# 4. Run all checks
make check

# 5. Commit version update
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 2.1.53"

# 6. Push commits
git push origin main

# 7. Create and push tag (VERIFY VERSION FIRST!)
git tag -a "v2.1.53" -m "Release v2.1.53"
git push origin v2.1.53

# 8. GitHub Actions will automatically:
#    - Build the package
#    - Publish to PyPI
#    - Create GitHub release
```

**⚠️ CRITICAL REMINDER:** Always verify `pyproject.toml` version matches the tag before pushing! The GitHub Actions workflow reads the version from `pyproject.toml`, not from the tag name.

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

1. **Always use `make release`**: Don't manually bump versions or tag releases
2. **Verify version before release**: Check that `pyproject.toml` has the version you want (or let Makefile update it)
3. **Keep CHANGELOG updated**: Add entries to `[Unreleased]` as you work
4. **Test before releasing**: `make release` runs tests, but test manually first
5. **Verify after releasing**: Check GitHub releases and PyPI
6. **Document everything**: CHANGELOG is the source of truth for release notes
7. **Use semantic versioning**: Choose patch/minor/major appropriately
8. **Version must match**: The version in `pyproject.toml` MUST match the VERSION you specify - the Makefile now handles this automatically

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

