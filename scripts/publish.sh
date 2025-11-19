#!/bin/bash
# Helper script for publishing pywiim to PyPI

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if repository is specified
if [ -z "$1" ]; then
    error "Usage: $0 [test|prod]"
    echo "  test - Upload to TestPyPI"
    echo "  prod - Upload to production PyPI"
    exit 1
fi

REPO=$1

if [ "$REPO" != "test" ] && [ "$REPO" != "prod" ]; then
    error "Invalid repository: $REPO"
    echo "Must be 'test' or 'prod'"
    exit 1
fi

# Get version from pyproject.toml
VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
info "Building version: $VERSION"

# Clean old builds
info "Cleaning old build artifacts..."
rm -rf build/ dist/ *.egg-info/

# Check if build tools are installed
if ! python -m build --version &> /dev/null; then
    error "build module not found. Install with: pip install build"
    exit 1
fi

if ! python -m twine --version &> /dev/null; then
    error "twine not found. Install with: pip install twine"
    exit 1
fi

# Build the package
info "Building package..."
python -m build

# Check if build was successful
if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
    error "Build failed - no files in dist/"
    exit 1
fi

info "Build successful! Files created:"
ls -lh dist/

# Upload
if [ "$REPO" == "test" ]; then
    info "Uploading to TestPyPI..."
    python -m twine upload --repository testpypi dist/*
    info "Upload complete! Test with:"
    echo "  pip install --index-url https://test.pypi.org/simple/ pywiim"
else
    warn "Uploading to PRODUCTION PyPI..."
    warn "This will make the package publicly available!"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Upload cancelled"
        exit 0
    fi
    python -m twine upload dist/*
    info "Upload complete! Package available at:"
    echo "  https://pypi.org/project/pywiim/"
fi

info "Done!"

