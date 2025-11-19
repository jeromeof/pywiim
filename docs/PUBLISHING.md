# Publishing to PyPI

This guide walks you through publishing `pywiim` to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/account/register/
2. **TestPyPI Account**: Create an account at https://test.pypi.org/account/register/
3. **API Tokens**: Generate API tokens for both PyPI and TestPyPI:
   - Go to https://pypi.org/manage/account/token/ (for production)
   - Go to https://test.pypi.org/manage/account/token/ (for test)
   - Create a token with scope "Entire account" or "Project: pywiim"
   - Save the token (format: `pypi-...`) - you'll need it for uploads

4. **Build Tools**: Install build and upload tools:
   ```bash
   pip install build twine
   ```

## Step-by-Step Publishing Process

### 1. Prepare Your Package

Ensure everything is ready:
- [ ] Version number is correct in `pyproject.toml` and `pywiim/__init__.py`
- [ ] CHANGELOG.md is updated
- [ ] README.md is complete and accurate
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Code is formatted: `black .` and `ruff check .`
- [ ] Type checking passes: `mypy pywiim`

### 2. Clean Previous Builds

```bash
# Remove old build artifacts
rm -rf build/ dist/ *.egg-info/
```

### 3. Build the Package

```bash
# Build source distribution and wheel
python -m build
```

This creates:
- `dist/pywiim-<version>.tar.gz` (source distribution)
- `dist/pywiim-<version>-py3-none-any.whl` (wheel)

### 4. Test the Build Locally (Optional)

```bash
# Install from the built wheel to test
pip install dist/pywiim-<version>-py3-none-any.whl

# Test that it works
python -c "import pywiim; print(pywiim.__version__)"
```

### 5. Upload to TestPyPI First

**Always test on TestPyPI before production!**

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# When prompted:
# Username: __token__
# Password: <your-testpypi-token>
```

### 6. Test Installation from TestPyPI

```bash
# Create a clean virtual environment
python3 -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ pywiim

# Test it works
python -c "import pywiim; print(pywiim.__version__)"
wiim-discover --help
```

### 7. Upload to Production PyPI

Once you've verified everything works on TestPyPI:

```bash
# Upload to production PyPI
python -m twine upload dist/*

# When prompted:
# Username: __token__
# Password: <your-pypi-token>
```

### 8. Verify on PyPI

- Check your package: https://pypi.org/project/pywiim/
- Verify installation: `pip install pywiim`

## Using the Helper Script

For convenience, use the provided `scripts/publish.sh` script:

```bash
# Build and upload to TestPyPI
./scripts/publish.sh test

# Build and upload to production PyPI
./scripts/publish.sh prod
```

The script will:
1. Clean old builds
2. Run checks (optional)
3. Build the package
4. Upload to the specified repository

## Version Management

### Automated Release Process (Recommended)

**Before running the release script**, update `CHANGELOG.md`:
- Move items from `[Unreleased]` to a new version section (e.g., `## [1.0.26]`)
- Add the release date
- Ensure all changes are documented

Then use the automated release script which handles version bumping, linting, testing, tagging, and GitHub release creation:

```bash
# For a patch release (1.0.25 -> 1.0.26)
./scripts/release.sh patch

# For a minor release (1.0.25 -> 1.1.0)
./scripts/release.sh minor

# For a major release (1.0.25 -> 2.0.0)
./scripts/release.sh major
```

The script will:
1. Format code with black and isort
2. Run linting (ruff) and type checking (mypy)
3. Run tests (pytest)
4. Bump version in `pyproject.toml` and `pywiim/__init__.py`
5. Commit changes (including CHANGELOG.md updates) and create a version tag
6. Push commits and tags to GitHub
7. Create a GitHub release with changelog notes extracted from `CHANGELOG.md` (if GitHub CLI is installed)

**Prerequisites for GitHub releases:**
- Install GitHub CLI: https://cli.github.com/
- Authenticate: `gh auth login`
- The script will automatically extract release notes from `CHANGELOG.md`

### Manual Release Process

If you prefer to release manually:

1. Update version in `pyproject.toml`:
   ```toml
   version = "1.0.1"
   ```

2. Update version in `pywiim/__init__.py`:
   ```python
   __version__ = "1.0.1"
   ```

3. Update CHANGELOG.md with release notes (move items from `[Unreleased]` to a new version section)

4. Commit and tag:
   ```bash
   git add pyproject.toml pywiim/__init__.py CHANGELOG.md
   git commit -m "Release version 1.0.1"
   git tag v1.0.1
   git push origin main --tags
   ```

5. Create GitHub release (optional but recommended):
   ```bash
   # Extract changelog and create release
   gh release create v1.0.1 --title "Release v1.0.1" --notes-file <(./scripts/extract_changelog.sh 1.0.1)
   # Or create manually at: https://github.com/mjcumming/pywiim/releases/new
   ```

### GitHub Releases

GitHub releases provide:
- Visible release notes on the repository's Releases page
- Downloadable source archives for each version
- Better discoverability of what changed in each version
- Integration with GitHub's release notifications

**Note:** PyPI publishing happens automatically via GitHub Actions when you push a version tag (see `.github/workflows/publish.yml`). GitHub releases are separate and provide additional visibility and documentation.

## Troubleshooting

### "File already exists" error
- The version number is already on PyPI
- Increment the version number and try again

### "Invalid distribution" error
- Check that `pyproject.toml` is valid
- Ensure all required fields are present
- Run `python -m build` to see detailed error messages

### Authentication errors

#### "401 Unauthorized" error
- Check that your token is correct
- Ensure you're using `__token__` as the username
- Verify the token hasn't expired or been revoked

#### "403 Forbidden" error
- Check that your token has the correct scope (project or account)
- Verify the package name matches what the token is scoped to

#### General authentication issues
- For TestPyPI, make sure you're using the TestPyPI token, not the production one
- Verify you're using the correct repository URL for TestPyPI

## Authentication Setup

There are several ways to configure authentication for PyPI uploads. Choose the method that works best for your environment.

### Option 1: Using `.pypirc` File (Recommended)

Create a `.pypirc` file in your home directory (`~/.pypirc`):

```bash
# Create the file
nano ~/.pypirc
# or
vim ~/.pypirc
```

Add the following content (replace the tokens with your actual API tokens):

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YourProductionTokenHere

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YourTestPyPITokenHere
```

**Important Security Notes:**
- The `.pypirc` file should have restricted permissions (600)
- Never commit this file to version control
- Replace the placeholder tokens with your actual tokens

Set proper permissions:
```bash
chmod 600 ~/.pypirc
```

#### Getting Your API Tokens

1. **For TestPyPI:**
   - Go to https://test.pypi.org/manage/account/token/
   - Click "Add API token"
   - Name it (e.g., "pywiim-test")
   - Scope: "Entire account" or "Project: pywiim"
   - Copy the token (starts with `pypi-`)

2. **For Production PyPI:**
   - Go to https://pypi.org/manage/account/token/
   - Click "Add API token"
   - Name it (e.g., "pywiim-prod")
   - Scope: "Entire account" or "Project: pywiim"
   - Copy the token (starts with `pypi-`)

Once configured, you can upload without entering credentials:
```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Upload to production PyPI
python -m twine upload dist/*
```

### Option 2: Environment Variables

You can set environment variables instead:

```bash
# For TestPyPI
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YourTestPyPITokenHere
export TWINE_REPOSITORY_URL=https://test.pypi.org/legacy/
python -m twine upload dist/*

# For Production PyPI
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YourProductionTokenHere
unset TWINE_REPOSITORY_URL  # or don't set it
python -m twine upload dist/*
```

### Option 3: Interactive Prompts

You can simply enter credentials when prompted:

```bash
python -m twine upload dist/*
# Username: __token__
# Password: <paste your token>
```

For TestPyPI:
```bash
python -m twine upload --repository testpypi dist/*
# Username: __token__
# Password: <paste your test token>
```

### Option 4: Using Keyring (Linux/WSL)

Twine can use your system keyring to store credentials securely:

```bash
# Store TestPyPI credentials
keyring set https://test.pypi.org/legacy/ __token__
# Enter password: pypi-YourTestPyPITokenHere

# Store production PyPI credentials
keyring set https://upload.pypi.org/legacy/ __token__
# Enter password: pypi-YourProductionTokenHere
```

Then twine will automatically retrieve them when uploading.

**Note**: If keyring doesn't work on WSL, use `.pypirc` or environment variables instead.

## Security Best Practices

- **Never commit API tokens** to version control
- Use environment variables or `~/.pypirc` for tokens
- Use separate tokens for TestPyPI and production
- Consider using project-scoped tokens instead of account-scoped
- Set proper file permissions (600) on `.pypirc` if using that method

## Additional Resources

- [PyPI Documentation](https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Python Packaging User Guide](https://packaging.python.org/)

