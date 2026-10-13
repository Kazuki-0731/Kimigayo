#!/usr/bin/env bash
#
# OpenRC Integration Test Script for Kimigayo OS
# Tests the OpenRC installation (build/openrc-install-<arch>)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"
# shellcheck source=scripts/lib/build-stamp.sh
source "${PROJECT_ROOT}/scripts/lib/build-stamp.sh"

# Configuration
# `make test-openrc` はコンテナ内の build-system/ から呼ばれるので、
# ./build（カレント基準）ではなくプロジェクトルート基準で解決する。
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
ARCH="${ARCH:-${TARGET_ARCH:-x86_64}}"

OPENRC_INSTALL_DIR="${BUILD_DIR}/openrc-install-${ARCH}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
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
echo "OpenRC Integration Tests"
echo "========================================"
log_info "Architecture: ${ARCH}"
log_info "OpenRC directory: ${OPENRC_INSTALL_DIR}"
echo ""

# Test 1: Verify OpenRC installation directory exists
log_test "Test 1: Verify OpenRC installation directory"
if [ -d "$OPENRC_INSTALL_DIR" ]; then
    test_pass "OpenRC installation directory found"
else
    test_fail "OpenRC installation directory not found: $OPENRC_INSTALL_DIR"
    echo ""
    echo "Test suite cannot continue without OpenRC."
    echo "Please run (inside the build container): make init TARGET_ARCH=${ARCH}"
    exit 1
fi

# Test 2: ビルドした版が versions.mk と合っているか
# スタンプは "<版>" または "<版>+<入力ハッシュ>"（scripts/lib/build-stamp.sh）
log_test "Test 2: Verify built version matches versions.mk"
built_id="$(kimigayo_built_version "$OPENRC_INSTALL_DIR")"
case "$built_id" in
    "${OPENRC_VERSION}"|"${OPENRC_VERSION}+"*)
        test_pass "OpenRC build stamp ${built_id} matches versions.mk (${OPENRC_VERSION})" ;;
    *)
        test_fail "OpenRC build stamp '${built_id:-<none>}' does not match versions.mk (${OPENRC_VERSION})" ;;
esac

# Test 3: Verify essential OpenRC binaries
#
# scripts/build-openrc.sh は --sbindir=/usr/sbin で入れる（rootfs では
# build-rootfs.sh が /sbin へ移す）。rc-status だけは /bin に入る。
# OpenRC 0.63 には sbin/rc は無い。
log_test "Test 3: Verify essential OpenRC binaries"
essential_binaries=(
    "usr/sbin/openrc"
    "usr/sbin/openrc-init"
    "usr/sbin/openrc-run"
    "usr/sbin/openrc-shutdown"
    "usr/sbin/rc-service"
    "usr/sbin/rc-update"
    "usr/sbin/start-stop-daemon"
    "usr/sbin/supervise-daemon"
    "bin/rc-status"
)

all_found=true
for binary in "${essential_binaries[@]}"; do
    if [ -f "${OPENRC_INSTALL_DIR}/${binary}" ] && [ -x "${OPENRC_INSTALL_DIR}/${binary}" ]; then
        log_info "  ✓ ${binary}"
    else
        log_error "  ✗ ${binary} not found or not executable"
        all_found=false
    fi
done

if [ "$all_found" = true ]; then
    test_pass "All essential OpenRC binaries found"
else
    test_fail "Some essential OpenRC binaries are missing"
fi

# Test 4: Verify OpenRC shared libraries (librc / libeinfo)
log_test "Test 4: Verify OpenRC shared libraries"
all_found=true
for lib in librc.so.1 libeinfo.so.1; do
    if [ -e "${OPENRC_INSTALL_DIR}/usr/lib/${lib}" ]; then
        log_info "  ✓ usr/lib/${lib}"
    else
        log_error "  ✗ usr/lib/${lib} not found"
        all_found=false
    fi
done
if [ "$all_found" = true ]; then
    test_pass "OpenRC shared libraries found"
else
    test_fail "Some OpenRC shared libraries are missing"
fi

# Test 5: Verify OpenRC support files (--libexecdir=/lib/rc)
log_test "Test 5: Verify OpenRC support files"
lib_dir="${OPENRC_INSTALL_DIR}/lib/rc"
if [ -d "$lib_dir" ]; then
    lib_count=$(find "$lib_dir" -type f | wc -l)
    log_info "Found ${lib_count} files in lib/rc"
    if [ "$lib_count" -gt 0 ]; then
        test_pass "OpenRC support files found"
    else
        test_fail "No files found in $lib_dir"
    fi
else
    test_fail "OpenRC support directory not found: $lib_dir"
fi

# Test 6: Verify runlevel directories
log_test "Test 6: Verify runlevel directories"
runlevels=("sysinit" "boot" "default" "shutdown")
runlevel_dir="${OPENRC_INSTALL_DIR}/etc/runlevels"

all_found=true
for level in "${runlevels[@]}"; do
    if [ -d "${runlevel_dir}/${level}" ]; then
        log_info "  ✓ Runlevel: ${level}"
    else
        log_error "  ✗ Runlevel directory missing: ${level}"
        all_found=false
    fi
done

if [ "$all_found" = true ]; then
    test_pass "All runlevel directories found"
else
    test_fail "Some runlevel directories are missing"
fi

# Test 7: Verify OpenRC core configuration
log_test "Test 7: Verify OpenRC core configuration"
if [ -f "${OPENRC_INSTALL_DIR}/etc/rc.conf" ]; then
    test_pass "OpenRC configuration file found: rc.conf"
else
    test_fail "OpenRC configuration file not found: etc/rc.conf"
fi

# Test 8: Verify init.d scripts installed by OpenRC
log_test "Test 8: Verify OpenRC init.d scripts in installation"
init_dir="${OPENRC_INSTALL_DIR}/etc/init.d"
if [ -d "$init_dir" ]; then
    init_count=$(find "$init_dir" \( -type f -o -type l \) | wc -l)
    log_info "Found ${init_count} init scripts in installation"
    if [ "$init_count" -gt 0 ]; then
        test_pass "OpenRC init.d directory populated"
    else
        test_fail "OpenRC init.d directory is empty: $init_dir"
    fi
else
    test_fail "OpenRC init.d directory not found: $init_dir"
fi

# イメージの init.d は scripts/build-rootfs.sh の heredoc と上流 OpenRC が作る。

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
