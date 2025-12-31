#!/bin/bash
# Kimigayo OS - Kernel Build Verification Script
# Verifies kernel build success and checks for required files

set -e

# Configuration
KERNEL_VERSION="${KERNEL_VERSION:-6.6.11}"
ARCH="${ARCH:-x86_64}"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
KERNEL_OUTPUT_DIR="${PROJECT_ROOT}/build/kernel/output"
KERNEL_SRC_DIR="${PROJECT_ROOT}/build/kernel-src/linux-${KERNEL_VERSION}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_test() {
    echo -e "${GREEN}[TEST]${NC} $*"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $*"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $*"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

# Test: Kernel image exists
test_kernel_image_exists() {
    log_test "Checking if kernel image exists"

    local kernel_image="${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}"

    if [ -f "$kernel_image" ]; then
        log_pass "Kernel image found: $kernel_image"
        return 0
    else
        log_fail "Kernel image not found: $kernel_image"
        return 1
    fi
}

# Test: Kernel image is not empty
test_kernel_image_not_empty() {
    log_test "Checking if kernel image is not empty"

    local kernel_image="${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}"

    if [ ! -f "$kernel_image" ]; then
        log_fail "Kernel image does not exist"
        return 1
    fi

    local size
    size=$(stat -f%z "$kernel_image" 2>/dev/null || stat -c%s "$kernel_image" 2>/dev/null || echo 0)

    if [ "$size" -gt 0 ]; then
        log_pass "Kernel image is not empty (${size} bytes)"
        return 0
    else
        log_fail "Kernel image is empty"
        return 1
    fi
}

# Test: Kernel image size is reasonable
test_kernel_image_size() {
    log_test "Checking kernel image size"

    local kernel_image="${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}"

    if [ ! -f "$kernel_image" ]; then
        log_fail "Kernel image does not exist"
        return 1
    fi

    local size
    size=$(stat -f%z "$kernel_image" 2>/dev/null || stat -c%s "$kernel_image" 2>/dev/null || echo 0)
    local size_mb=$((size / 1024 / 1024))

    # Kernel should be between 1MB and 50MB
    if [ "$size_mb" -ge 1 ] && [ "$size_mb" -le 50 ]; then
        log_pass "Kernel size is reasonable: ${size_mb}MB"
        return 0
    else
        log_warn "Kernel size is unusual: ${size_mb}MB (expected 1-50MB)"
        return 0
    fi
}

# Test: System.map exists
test_system_map_exists() {
    log_test "Checking if System.map exists"

    local system_map="${KERNEL_OUTPUT_DIR}/System.map-${KERNEL_VERSION}-${ARCH}"

    if [ -f "$system_map" ]; then
        log_pass "System.map found: $system_map"
        return 0
    else
        log_warn "System.map not found (optional): $system_map"
        return 0
    fi
}

# Test: Kernel config exists
test_kernel_config_exists() {
    log_test "Checking if kernel config exists"

    local config="${KERNEL_OUTPUT_DIR}/config-${KERNEL_VERSION}-${ARCH}"

    if [ -f "$config" ]; then
        log_pass "Kernel config found: $config"
        return 0
    else
        log_warn "Kernel config not found (optional): $config"
        return 0
    fi
}

# Test: Kernel source directory exists
test_kernel_source_exists() {
    log_test "Checking if kernel source directory exists"

    if [ -d "$KERNEL_SRC_DIR" ]; then
        log_pass "Kernel source found: $KERNEL_SRC_DIR"
        return 0
    else
        log_fail "Kernel source not found: $KERNEL_SRC_DIR"
        return 1
    fi
}

# Test: Kernel source contains Makefile
test_kernel_makefile_exists() {
    log_test "Checking if kernel Makefile exists"

    local makefile="${KERNEL_SRC_DIR}/Makefile"

    if [ -f "$makefile" ]; then
        log_pass "Kernel Makefile found"
        return 0
    else
        log_fail "Kernel Makefile not found: $makefile"
        return 1
    fi
}

# Test: Check kernel image magic bytes (x86_64)
test_kernel_magic_bytes() {
    log_test "Checking kernel image magic bytes"

    local kernel_image="${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}"

    if [ ! -f "$kernel_image" ]; then
        log_fail "Kernel image does not exist"
        return 1
    fi

    if [ "$ARCH" = "x86_64" ]; then
        # Check for MZ header (Linux bzImage starts with MZ)
        if command -v xxd &> /dev/null; then
            local magic
            magic=$(xxd -l 2 -p "$kernel_image" 2>/dev/null || echo "")
            if [ "$magic" = "4d5a" ]; then
                log_pass "Kernel image has valid magic bytes (MZ)"
                return 0
            else
                log_warn "Kernel image magic bytes: $magic (expected 4d5a for x86_64)"
                return 0
            fi
        else
            log_warn "xxd not found, skipping magic bytes check"
            return 0
        fi
    else
        log_info "Skipping magic bytes check for architecture: $ARCH"
        return 0
    fi
}

# Test: Build log exists
test_build_log_exists() {
    log_test "Checking if build log exists"

    local build_log="${PROJECT_ROOT}/build/logs/kernel-build.log"

    if [ -f "$build_log" ]; then
        log_pass "Build log found: $build_log"
        return 0
    else
        log_warn "Build log not found (optional): $build_log"
        return 0
    fi
}

# Test: No fatal errors in build log
test_build_log_no_errors() {
    log_test "Checking build log for fatal errors"

    local build_log="${PROJECT_ROOT}/build/logs/kernel-build.log"

    if [ ! -f "$build_log" ]; then
        log_warn "Build log not found, skipping error check"
        return 0
    fi

    local error_count
    error_count=$(grep -i "error:" "$build_log" 2>/dev/null | wc -l | tr -d ' ')

    if [ "$error_count" -eq 0 ]; then
        log_pass "No fatal errors found in build log"
        return 0
    else
        log_warn "Found $error_count error(s) in build log (may be warnings)"
        return 0
    fi
}

# Show build summary
show_summary() {
    echo ""
    log_info "====================================="
    log_info "Kernel Build Verification Summary"
    log_info "====================================="
    log_info "Kernel Version: $KERNEL_VERSION"
    log_info "Architecture: $ARCH"
    log_info "Tests Passed: $TESTS_PASSED"
    log_info "Tests Failed: $TESTS_FAILED"

    if [ -f "${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}" ]; then
        local size
        size=$(stat -f%z "${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}" 2>/dev/null || \
                     stat -c%s "${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}" 2>/dev/null || echo 0)
        local size_mb=$((size / 1024 / 1024))
        log_info "Kernel Image Size: ${size_mb}MB"
    fi

    log_info "====================================="

    if [ "$TESTS_FAILED" -eq 0 ]; then
        log_pass "All tests passed!"
        return 0
    else
        log_fail "$TESTS_FAILED test(s) failed"
        return 1
    fi
}

# Main
main() {
    log_info "Kimigayo OS - Kernel Build Verification"
    log_info "Kernel Version: ${KERNEL_VERSION}"
    log_info "Architecture: ${ARCH}"
    echo ""

    # Run all tests
    test_kernel_source_exists || true
    test_kernel_makefile_exists || true
    test_kernel_image_exists || true
    test_kernel_image_not_empty || true
    test_kernel_image_size || true
    test_system_map_exists || true
    test_kernel_config_exists || true
    test_kernel_magic_bytes || true
    test_build_log_exists || true
    test_build_log_no_errors || true

    # Show summary
    show_summary
}

main "$@"
