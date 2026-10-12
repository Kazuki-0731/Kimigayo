#!/usr/bin/env bash
#
# Functionality Test Script
# Tests BusyBox commands, network functionality, and that no package manager is shipped
#

set -uo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Configuration
# 既定は Makefile の build-image / package-rootfs と同じ名前。
#   イメージ: kimigayo-os:<variant>-<arch>
#   tarball:  output/kimigayo-<variant>-<version>-<arch>.tar.gz
# IMAGE_NAME にタグが無ければ（Makefile / .env の IMAGE_NAME=kimigayo-os は
# リポジトリ名）、<variant>-<arch> を補う。
VARIANT="${VARIANT:-standard}"
ARCH="${ARCH:-x86_64}"
VERSION="${VERSION:-latest}"
IMAGE_NAME="${IMAGE_NAME:-kimigayo-os}"
case "${IMAGE_NAME##*/}" in
    *:*) ;;
    *)   IMAGE_NAME="${IMAGE_NAME}:${VARIANT}-${ARCH}" ;;
esac
TAR_FILE="${TAR_FILE:-${PROJECT_ROOT}/output/kimigayo-${VARIANT}-${VERSION}-${ARCH}.tar.gz}"
case "$ARCH" in
    arm64|aarch64) MUSL_ARCH="aarch64" ;;
    *)             MUSL_ARCH="$ARCH" ;;
esac
CONTAINER_NAME="kimigayo-func-test-$$"

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

section() {
    echo ""
    echo -e "${BLUE}$1${NC}"
    echo "-----------------------------------------------"
}

# Cleanup function
cleanup() {
    if [ -n "${CONTAINER_NAME:-}" ]; then
        docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# tarball の一覧は一度だけ取る。
# `tar tzf | grep -q` は pipefail の下で、grep が先に抜けると tar が
# SIGPIPE で落ちてパイプライン全体が偽になる（見つかったのに FAIL）。
# 判定もパイプを通さず here-string で渡す（同じ理由）。
TAR_LIST=""
tar_has() {
    grep -qE "$1" <<< "$TAR_LIST"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════╗
║   Kimigayo OS - Functionality Test   ║
║   Feature Testing                    ║
╚═══════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if image exists
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo -e "${RED}Error: Docker image not found: $IMAGE_NAME${NC}"
    echo "Please run: make package-rootfs && make build-image"
    exit 1
fi

info "Using Docker image: $IMAGE_NAME"
info "Using rootfs tarball: $TAR_FILE"

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    info "Running on macOS - tests will verify tar.gz contents only"
    info "Full runtime tests are designed for Linux (GitHub Actions CI)"
    SKIP_RUNTIME_TESTS=true
else
    info "Running on Linux - full runtime tests enabled"
    SKIP_RUNTIME_TESTS=false
fi

echo ""

# ===================================================================
# Test 1: BusyBox Binary Verification (tar.gz inspection)
# ===================================================================
section "Test 1: BusyBox Binary Verification"

if [ ! -f "$TAR_FILE" ]; then
    fail "tar.gz file not found: $TAR_FILE"
    echo "Please run: make package-rootfs VARIANT=${VARIANT} ARCH=${ARCH} VERSION=${VERSION}"
elif ! TAR_LIST="$(tar tzf "$TAR_FILE")"; then
    fail "Failed to list tar.gz: $TAR_FILE"
else
    pass "tar.gz file exists"

    # Check if BusyBox binary exists
    if tar_has "^\./bin/busybox$"; then
        pass "BusyBox binary found in tar.gz"
    else
        fail "BusyBox binary not found in tar.gz"
    fi

    # Check essential libraries
    if tar_has "lib/ld-musl-${MUSL_ARCH}\.so\.1$"; then
        pass "musl libc loader found (ld-musl-${MUSL_ARCH}.so.1)"
    else
        fail "musl libc loader not found (ld-musl-${MUSL_ARCH}.so.1)"
    fi
fi

# ===================================================================
# Test 2: BusyBox Commands Test (Runtime - Linux only)
# ===================================================================
section "Test 2: BusyBox Commands Test"

if [ "$SKIP_RUNTIME_TESTS" = "true" ]; then
    info "Skipping runtime tests on macOS"
    info "Verifying BusyBox applets in tar.gz instead..."

    # BusyBox はアプレットを /bin・/sbin・/usr/bin・/usr/sbin への
    # シンボリックリンクとして入れる。その存在を tarball で確かめる
    EXPECTED_COMMANDS="sh ls cat echo pwd mkdir rm cp mv grep sed awk"
    for cmd in $EXPECTED_COMMANDS; do
        if tar_has "^\./(usr/)?s?bin/${cmd}$"; then
            pass "BusyBox applet in tar.gz: $cmd"
        else
            fail "BusyBox applet not found in tar.gz: $cmd"
        fi
    done
else
    # Linux - run full container tests
    info "Starting test container..."
    if ! docker run -d --name "$CONTAINER_NAME" "$IMAGE_NAME" /bin/sh -c "while true; do sleep 1; done" >/dev/null 2>&1; then
        fail "Failed to start test container"
        exit 1
    fi

    sleep 2

    # Test BusyBox commands
    BUSYBOX_COMMANDS="ls cat echo pwd mkdir rm cp mv"
    for cmd in $BUSYBOX_COMMANDS; do
        if docker exec "$CONTAINER_NAME" /bin/sh -c "command -v $cmd >/dev/null 2>&1"; then
            pass "BusyBox command available: $cmd"
        else
            fail "BusyBox command not found: $cmd"
        fi
    done

    # Test actual command execution
    if docker exec "$CONTAINER_NAME" /bin/sh -c "echo 'test' | cat" >/dev/null 2>&1; then
        pass "BusyBox pipe functionality works"
    else
        fail "BusyBox pipe functionality failed"
    fi

    # Test file operations
    if docker exec "$CONTAINER_NAME" /bin/sh -c "mkdir -p /tmp/test && echo 'data' > /tmp/test/file && cat /tmp/test/file" | grep -q "data"; then
        pass "BusyBox file operations work"
    else
        fail "BusyBox file operations failed"
    fi
fi

# ===================================================================
# Test 3: Network Functionality Test (Runtime - Linux only)
# ===================================================================
section "Test 3: Network Functionality Test"

if [ "$SKIP_RUNTIME_TESTS" = "true" ]; then
    info "Skipping runtime tests on macOS"

    # Check if network-related files exist in tar.gz
    if tar_has "^\./etc/"; then
        pass "etc/ directory exists (for network config)"
    else
        fail "etc/ directory not found"
    fi
else
    # Linux - test network stack
    if docker exec "$CONTAINER_NAME" /bin/sh -c "command -v ping >/dev/null 2>&1"; then
        info "Testing ping command..."
        if timeout 5 docker exec "$CONTAINER_NAME" /bin/sh -c "ping -c 1 127.0.0.1" >/dev/null 2>&1; then
            pass "Loopback ping works"
        else
            info "Loopback ping failed (ping needs the NET_RAW capability)"
        fi
    else
        info "ping command not available"
    fi

    # Check if network interfaces can be listed
    if docker exec "$CONTAINER_NAME" /bin/sh -c "command -v ip >/dev/null 2>&1 || command -v ifconfig >/dev/null 2>&1"; then
        pass "Network interface tools available"
    else
        info "Network interface tools not available"
    fi
fi

# ===================================================================
# Test 4: Package Manager Test (removed - distroless approach)
# ===================================================================
section "Test 4: Package Manager Test"
info "Package manager intentionally excluded (distroless approach)"

# 出荷物にパッケージマネージャーが入っていないこと
PKG_MANAGERS="apk apt apt-get dpkg rpm yum dnf opkg pip pip3"
found_pm=""
for pm in $PKG_MANAGERS; do
    if tar_has "^\./(usr/)?(local/)?s?bin/${pm}$"; then
        found_pm="${found_pm} ${pm}"
    fi
done
if [ -n "$TAR_LIST" ] && [ -z "$found_pm" ]; then
    pass "No package manager in tar.gz"
elif [ -z "$TAR_LIST" ]; then
    fail "Cannot check for package managers (tar.gz not available)"
else
    fail "Package manager found in tar.gz:${found_pm}"
fi

# Package repository removed (distroless approach)
REPO_DIR="${PROJECT_ROOT}/repository"
if [ -d "$REPO_DIR" ]; then
    fail "Package repository directory should not exist (distroless approach)"
else
    pass "Package repository correctly removed"
fi

# ===================================================================
# Test 5: File System Structure Verification
# ===================================================================
section "Test 5: File System Structure Verification"

# FHS (Filesystem Hierarchy Standard) directories
FHS_DIRS="bin sbin lib etc usr var dev"
for dir in $FHS_DIRS; do
    if tar_has "^\./$dir/"; then
        pass "FHS directory exists: /$dir"
    else
        fail "FHS directory missing: /$dir"
    fi
done

# ===================================================================
# Test 6: OpenRC Init System Verification
# ===================================================================
section "Test 6: OpenRC Init System Verification"

if tar_has "lib/librc\.so"; then
    pass "OpenRC library found"
else
    fail "OpenRC library not found"
fi

if tar_has "^\./lib/rc/"; then
    pass "OpenRC scripts directory found"
else
    fail "OpenRC scripts directory not found"
fi

# ===================================================================
# Summary
# ===================================================================
echo ""
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
echo ""

if [ "$SKIP_RUNTIME_TESTS" = "true" ]; then
    echo -e "${YELLOW}Note:${NC} Runtime tests were skipped on macOS."
    echo "Full container runtime tests will run on Linux (GitHub Actions CI)."
    echo ""
fi

if [ ${TESTS_FAILED} -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
