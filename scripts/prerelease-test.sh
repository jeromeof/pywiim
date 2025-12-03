#!/bin/bash
# Pre-release testing script for pywiim
#
# This script runs a comprehensive test suite before releases:
# 1. Unit tests
# 2. Real device connectivity tests
# 3. State property validation
# 4. Integration tests (if devices available)
#
# Usage:
#   ./scripts/prerelease-test.sh              # Run all tests
#   ./scripts/prerelease-test.sh --quick      # Skip long integration tests
#   ./scripts/prerelease-test.sh --devices-only  # Only test devices
#
# Configure devices in: scripts/test_devices.conf
# Or set WIIM_TEST_DEVICES="ip1,ip2,ip3"

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$SCRIPT_DIR/test_devices.conf"

# Default test devices (can be overridden by config file or env var)
# These are the known WiiM devices for testing
DEFAULT_DEVICES="192.168.1.115,192.168.1.116,192.168.1.68"

# Unbuffered output for real-time feedback
export PYTHONUNBUFFERED=1

# Parse arguments
QUICK_MODE=false
DEVICES_ONLY=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick|-q)
            QUICK_MODE=true
            shift
            ;;
        --devices-only|-d)
            DEVICES_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick, -q        Skip long integration tests"
            echo "  --devices-only, -d Only run device tests"
            echo "  --help, -h         Show this help"
            echo ""
            echo "Configure devices in: $CONFIG_FILE"
            echo "Or set WIIM_TEST_DEVICES=\"ip1,ip2,ip3\""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Load device configuration
load_devices() {
    # Priority: env var > config file > defaults
    if [[ -n "$WIIM_TEST_DEVICES" ]]; then
        echo "$WIIM_TEST_DEVICES"
    elif [[ -f "$CONFIG_FILE" ]]; then
        # Remove comments (both full-line and inline), trim whitespace, join with commas
        grep -v '^#' "$CONFIG_FILE" | grep -v '^$' | sed 's/#.*//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//' | grep -v '^$' | tr '\n' ',' | sed 's/,$//'
    else
        echo "$DEFAULT_DEVICES"
    fi
}

# Print header
print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

# Print status
print_status() {
    local status=$1
    local message=$2
    if [[ "$status" == "pass" ]]; then
        echo -e "${GREEN}✓${NC} $message"
    elif [[ "$status" == "fail" ]]; then
        echo -e "${RED}✗${NC} $message"
    elif [[ "$status" == "skip" ]]; then
        echo -e "${YELLOW}○${NC} $message (skipped)"
    else
        echo -e "${BLUE}→${NC} $message"
    fi
}

# Track results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

record_result() {
    local result=$1
    ((TOTAL_TESTS++))
    case $result in
        pass) ((PASSED_TESTS++)) ;;
        fail) ((FAILED_TESTS++)) ;;
        skip) ((SKIPPED_TESTS++)) ;;
    esac
}

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment
if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
else
    echo -e "${RED}Error: Virtual environment not found at .venv${NC}"
    exit 1
fi

print_header "pywiim Pre-Release Testing Suite"
echo "Mode: $([ "$QUICK_MODE" = true ] && echo "Quick" || echo "Full")"
echo "Date: $(date)"
echo ""

# Get devices
DEVICES=$(load_devices)
IFS=',' read -ra DEVICE_ARRAY <<< "$DEVICES"
echo "Test devices: ${DEVICE_ARRAY[*]}"
echo ""

# =============================================================================
# 1. Unit Tests
# =============================================================================
if [[ "$DEVICES_ONLY" != true ]]; then
    print_header "1. Unit Tests"
    
    if python -m pytest tests/unit/ -q --tb=no 2>&1 | tee /tmp/unit_test_output.txt; then
        UNIT_RESULT=$(tail -1 /tmp/unit_test_output.txt)
        print_status "pass" "Unit tests: $UNIT_RESULT"
        record_result pass
    else
        print_status "fail" "Unit tests failed"
        record_result fail
    fi
fi

# =============================================================================
# 2. Device Connectivity Tests
# =============================================================================
print_header "2. Device Connectivity Tests"

REACHABLE_DEVICES=()
for ip in "${DEVICE_ARRAY[@]}"; do
    ip=$(echo "$ip" | tr -d ' ')  # Trim whitespace
    print_status "info" "Testing $ip..."
    
    if timeout 10 python scripts/test_state_properties.py "$ip" > /tmp/device_test_$ip.txt 2>&1; then
        # Extract device name from output
        DEVICE_NAME=$(grep "Device:" /tmp/device_test_$ip.txt | head -1 | sed 's/.*Device: //' | cut -d'(' -f1 | tr -d ' ')
        print_status "pass" "$ip ($DEVICE_NAME) - all state properties work"
        record_result pass
        REACHABLE_DEVICES+=("$ip")
    else
        print_status "fail" "$ip - unreachable or test failed"
        record_result fail
    fi
done

echo ""
echo "Reachable devices: ${#REACHABLE_DEVICES[@]}/${#DEVICE_ARRAY[@]}"

# =============================================================================
# 3. State Property Validation (detailed)
# =============================================================================
print_header "3. State Property Validation"

for ip in "${REACHABLE_DEVICES[@]}"; do
    echo -e "\n${YELLOW}--- $ip ---${NC}"
    
    # Extract and display key info
    if [[ -f "/tmp/device_test_$ip.txt" ]]; then
        grep -E "is_playing|is_paused|is_idle|is_buffering|player\.state|shuffle.*type:|repeat.*type:" /tmp/device_test_$ip.txt
        
        # Check consistency
        if grep -q "ALL STATE PROPERTY TESTS PASSED" /tmp/device_test_$ip.txt; then
            print_status "pass" "State consistency verified"
            record_result pass
        else
            print_status "fail" "State consistency check failed"
            record_result fail
        fi
    fi
done

# =============================================================================
# 4. Integration Tests (if not quick mode)
# =============================================================================
if [[ "$QUICK_MODE" != true && "$DEVICES_ONLY" != true && ${#REACHABLE_DEVICES[@]} -gt 0 ]]; then
    print_header "4. Integration Tests"
    
    # Use first reachable device for integration tests
    TEST_DEVICE="${REACHABLE_DEVICES[0]}"
    print_status "info" "Running integration tests against $TEST_DEVICE..."
    
    export WIIM_TEST_DEVICE="$TEST_DEVICE"
    
    if python -m pytest tests/integration/test_real_device.py -v --tb=short 2>&1 | tee /tmp/integration_test_output.txt; then
        INTEGRATION_RESULT=$(tail -1 /tmp/integration_test_output.txt)
        print_status "pass" "Integration tests: $INTEGRATION_RESULT"
        record_result pass
    else
        print_status "fail" "Some integration tests failed (see output above)"
        record_result fail
    fi
else
    if [[ "$QUICK_MODE" == true ]]; then
        print_status "skip" "Integration tests (quick mode)"
        record_result skip
    elif [[ ${#REACHABLE_DEVICES[@]} -eq 0 ]]; then
        print_status "skip" "Integration tests (no reachable devices)"
        record_result skip
    fi
fi

# =============================================================================
# Summary
# =============================================================================
print_header "Test Summary"

echo "Total tests:   $TOTAL_TESTS"
echo -e "Passed:        ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed:        ${RED}$FAILED_TESTS${NC}"
echo -e "Skipped:       ${YELLOW}$SKIPPED_TESTS${NC}"
echo ""

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "${GREEN}🎉 All tests passed! Ready for release.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Review output above.${NC}"
    exit 1
fi

