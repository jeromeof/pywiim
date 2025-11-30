#!/bin/bash
# Pre-release integration test runner
# Usage: ./scripts/prerelease-check.sh [device_ip]
#
# This script runs comprehensive integration tests against a real device
# before releasing. It's optional but recommended for major/minor releases.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    warn "Virtual environment not activated!"
    if [ -d ".venv" ]; then
        info "Activating virtual environment..."
        source .venv/bin/activate
    else
        error "Virtual environment not found. Please create one first."
        exit 1
    fi
fi

# Get device IP from argument or environment variable
DEVICE_IP=${1:-$WIIM_TEST_DEVICE}

if [ -z "$DEVICE_IP" ]; then
    error "No device IP provided!"
    echo "Usage: $0 [device_ip]"
    echo "   Or: WIIM_TEST_DEVICE=192.168.1.100 $0"
    exit 1
fi

info "Running pre-release integration tests against device: $DEVICE_IP"
echo ""

# Check if device is reachable
step "Checking device connectivity..."
if ! ping -c 1 -W 2 "$DEVICE_IP" > /dev/null 2>&1; then
    error "Device $DEVICE_IP is not reachable!"
    error "Please ensure the device is on the network and accessible."
    exit 1
fi
info "Device is reachable ✓"
echo ""

# Set environment variable for tests
export WIIM_TEST_DEVICE=$DEVICE_IP

# Run core integration tests first (fast, safe)
step "Running core integration tests..."
if pytest tests/integration/test_real_device.py -v -m "core"; then
    info "Core integration tests passed ✓"
else
    error "Core integration tests failed!"
    exit 1
fi
echo ""

# Run pre-release comprehensive tests
step "Running comprehensive pre-release tests..."
warn "These tests will change device state and restore it afterward."
warn "Make sure no one is using the device during testing."
warn ""
warn "NOTE: Some tests require an active source with media (e.g., Spotify, Bluetooth, USB)."
warn "If tests are skipped, you may need to start a source on the device first."
echo ""

read -p "Continue with comprehensive tests? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    warn "Skipping comprehensive tests."
    info "Pre-release check complete (core tests only)"
    exit 0
fi

if pytest tests/integration/test_prerelease.py -v -m "prerelease"; then
    info "Pre-release comprehensive tests passed ✓"
else
    error "Pre-release comprehensive tests failed!"
    exit 1
fi
echo ""

info "=========================================="
info "Pre-release check complete!"
info "All integration tests passed ✓"
info "=========================================="

