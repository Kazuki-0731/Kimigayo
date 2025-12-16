#!/usr/bin/env bash
#
# BusyBox Integration Test Script for Kimigayo OS
# Tests BusyBox functionality and integration
#

set -euo pipefail

# Configuration
BUILD_DIR="${BUILD_DIR:-./build}"
ARCH="${ARCH:-x86_64}"
IMAGE_TYPE="${IMAGE_TYPE:-standard}"

BUSYBOX_INSTALL_DIR="${BUILD_DIR}/busybox-install-${ARCH}"
BUSYBOX_BIN="${BUSYBOX_INSTALL_DIR}/bin/busybox"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
}

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $*"
}

# Test result tracking
test_pass() {
    ((TESTS_PASSED++)) || true
    ((TESTS_RUN++)) || true
    log_success "$1"
}

test_fail() {
    ((TESTS_FAILED++)) || true
    ((TESTS_RUN++)) || true
    log_error "$1"
}

# Header
echo "========================================"
echo "BusyBox Integration Tests"
echo "========================================"
log_info "Architecture: ${ARCH}"
log_info "Image type: ${IMAGE_TYPE}"
log_info "BusyBox binary: ${BUSYBOX_BIN}"
echo ""

# Test 1: Verify BusyBox binary exists
log_test "Test 1: Verify BusyBox binary exists"
if [ -f "$BUSYBOX_BIN" ]; then
    test_pass "BusyBox binary found: $BUSYBOX_BIN"
else
    test_fail "BusyBox binary not found: $BUSYBOX_BIN"
    echo ""
    echo "Test suite cannot continue without BusyBox binary."
    echo "Please run: make busybox ARCH=${ARCH} IMAGE_TYPE=${IMAGE_TYPE}"
    exit 1
fi

# Test 2: Verify static linking
log_test "Test 2: Verify static linking"
if file "$BUSYBOX_BIN" | grep -q "statically linked"; then
    test_pass "BusyBox is statically linked"
else
    test_fail "BusyBox is not statically linked"
fi

# Test 3: Verify binary size
log_test "Test 3: Verify binary size against target"
binary_size=$(stat -f%z "$BUSYBOX_BIN" 2>/dev/null || stat -c%s "$BUSYBOX_BIN" 2>/dev/null)
binary_size_kb=$((binary_size / 1024))

case "$IMAGE_TYPE" in
    minimal)
        target_size=500
        ;;
    standard)
        target_size=800
        ;;
    extended)
        target_size=1200
        ;;
    *)
        target_size=800
        ;;
esac

log_info "Binary size: ${binary_size_kb} KB"
log_info "Target size: ${target_size} KB"

if [ "$binary_size_kb" -le "$target_size" ]; then
    test_pass "Binary size (${binary_size_kb} KB) within target (${target_size} KB)"
else
    test_fail "Binary size (${binary_size_kb} KB) exceeds target (${target_size} KB)"
fi

# Test 4: List available applets
log_test "Test 4: List available applets"
if applets=$("$BUSYBOX_BIN" --list 2>/dev/null); then
    applet_count=$(echo "$applets" | wc -l)
    log_info "Total applets: ${applet_count}"
    test_pass "Successfully listed ${applet_count} applets"
else
    test_fail "Failed to list applets"
fi

# Test 5: Verify symlinks installation
log_test "Test 5: Verify symlinks installation"
symlink_count=$(find "$BUSYBOX_INSTALL_DIR" -type l 2>/dev/null | wc -l)
log_info "Total symlinks: ${symlink_count}"

if [ "$symlink_count" -gt 0 ]; then
    test_pass "Symlinks installed: ${symlink_count}"
else
    test_fail "No symlinks found"
fi

# Test 6: Verify essential commands (shell)
log_test "Test 6: Verify essential commands - sh"
if [ -L "${BUSYBOX_INSTALL_DIR}/bin/sh" ] || [ -f "${BUSYBOX_INSTALL_DIR}/bin/sh" ]; then
    test_pass "sh command available"
else
    test_fail "sh command not found"
fi

# Test 7: Test basic command execution - echo
log_test "Test 7: Test basic command execution - echo"
test_output=$("$BUSYBOX_BIN" echo "Hello BusyBox" 2>/dev/null || echo "")
if [ "$test_output" = "Hello BusyBox" ]; then
    test_pass "echo command works correctly"
else
    test_fail "echo command failed or returned incorrect output"
fi

# Test 8: Test ls command
log_test "Test 8: Test ls command"
if "$BUSYBOX_BIN" ls "$BUSYBOX_INSTALL_DIR" >/dev/null 2>&1; then
    test_pass "ls command works correctly"
else
    test_fail "ls command failed"
fi

# Test 9: Test cat command
log_test "Test 9: Test cat command"
temp_file=$(mktemp)
echo "test content" > "$temp_file"
cat_output=$("$BUSYBOX_BIN" cat "$temp_file" 2>/dev/null || echo "")
rm -f "$temp_file"

if [ "$cat_output" = "test content" ]; then
    test_pass "cat command works correctly"
else
    test_fail "cat command failed or returned incorrect output"
fi

# Test 10: Test grep command
log_test "Test 10: Test grep command"
if echo "test line" | "$BUSYBOX_BIN" grep "test" >/dev/null 2>&1; then
    test_pass "grep command works correctly"
else
    test_fail "grep command failed"
fi

# Test 11: Test find command
log_test "Test 11: Test find command"
if "$BUSYBOX_BIN" find "$BUSYBOX_INSTALL_DIR" -type f -name "busybox" 2>/dev/null | grep -q "busybox"; then
    test_pass "find command works correctly"
else
    test_fail "find command failed"
fi

# Test 12: Test sort command
log_test "Test 12: Test sort command"
temp_file=$(mktemp)
echo -e "3\n1\n2" > "$temp_file"
sort_output=$("$BUSYBOX_BIN" sort "$temp_file" 2>/dev/null || echo "")
rm -f "$temp_file"

if [ "$sort_output" = "$(echo -e "1\n2\n3")" ]; then
    test_pass "sort command works correctly"
else
    test_fail "sort command failed or returned incorrect output"
fi

# Test 13: Test tar command (if available)
log_test "Test 13: Test tar command (if available)"
if "$BUSYBOX_BIN" --list 2>/dev/null | grep -q "^tar$"; then
    temp_dir=$(mktemp -d)
    temp_tar="${temp_dir}/test.tar"
    echo "test" > "${temp_dir}/testfile"

    if cd "$temp_dir" && "$BUSYBOX_BIN" tar -cf test.tar testfile 2>/dev/null && [ -f test.tar ]; then
        test_pass "tar command works correctly"
    else
        test_fail "tar command failed"
    fi
    cd - >/dev/null
    rm -rf "$temp_dir"
else
    log_info "tar command not available in this build (skipped)"
    ((TESTS_RUN++)) || true
fi

# Test 14: Test gzip command (if available)
log_test "Test 14: Test gzip/gunzip commands (if available)"
if "$BUSYBOX_BIN" --list 2>/dev/null | grep -q "^gzip$"; then
    temp_file=$(mktemp)
    echo "test content" > "$temp_file"

    if "$BUSYBOX_BIN" gzip "$temp_file" 2>/dev/null && [ -f "${temp_file}.gz" ]; then
        if "$BUSYBOX_BIN" gunzip "${temp_file}.gz" 2>/dev/null && [ -f "$temp_file" ]; then
            test_pass "gzip/gunzip commands work correctly"
        else
            test_fail "gunzip command failed"
        fi
    else
        test_fail "gzip command failed"
    fi
    rm -f "$temp_file" "${temp_file}.gz"
else
    log_info "gzip command not available in this build (skipped)"
    ((TESTS_RUN++)) || true
fi

# Test 15: Test networking commands (if available)
log_test "Test 15: Test networking commands (basic availability)"
net_commands=("ip" "ifconfig" "ping" "route" "hostname")
net_found=0

for cmd in "${net_commands[@]}"; do
    if "$BUSYBOX_BIN" --list 2>/dev/null | grep -q "^${cmd}$"; then
        ((net_found++)) || true
    fi
done

if [ "$net_found" -gt 0 ]; then
    test_pass "Networking commands available: ${net_found}/${#net_commands[@]}"
else
    log_info "No networking commands available in this build"
    ((TESTS_RUN++)) || true
fi

# Test 16: Test init-related commands (if available)
log_test "Test 16: Test init-related commands (basic availability)"
init_commands=("init" "halt" "reboot" "poweroff")
init_found=0

for cmd in "${init_commands[@]}"; do
    if "$BUSYBOX_BIN" --list 2>/dev/null | grep -q "^${cmd}$"; then
        ((init_found++)) || true
    fi
done

if [ "$init_found" -gt 0 ]; then
    test_pass "Init commands available: ${init_found}/${#init_commands[@]}"
else
    test_fail "No init commands available"
fi

# Test 17: Test shell (ash)
log_test "Test 17: Test ash shell"
if "$BUSYBOX_BIN" --list 2>/dev/null | grep -q "^ash$"; then
    test_script="echo 'shell test' && exit 0"
    if echo "$test_script" | "$BUSYBOX_BIN" ash 2>/dev/null | grep -q "shell test"; then
        test_pass "ash shell works correctly"
    else
        test_fail "ash shell failed"
    fi
else
    test_fail "ash shell not available"
fi

# Test 18: Verify no dynamic dependencies
log_test "Test 18: Verify no dynamic dependencies"
if ldd "$BUSYBOX_BIN" 2>&1 | grep -q "not a dynamic executable"; then
    test_pass "BusyBox has no dynamic dependencies"
elif ldd "$BUSYBOX_BIN" 2>&1 | grep -q "statically linked"; then
    test_pass "BusyBox is statically linked"
else
    test_fail "BusyBox may have dynamic dependencies"
    ldd "$BUSYBOX_BIN" 2>&1 || true
fi

# Summary
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
log_info "Tests run:    ${TESTS_RUN}"
log_info "Tests passed: ${TESTS_PASSED}"
log_info "Tests failed: ${TESTS_FAILED}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    log_success "All tests passed!"
    exit 0
else
    log_error "Some tests failed"
    exit 1
fi
