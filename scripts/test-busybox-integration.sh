#!/usr/bin/env bash
#
# BusyBox Integration Test Script for Kimigayo OS
# Tests BusyBox functionality and integration
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# リンク方法の既定値（BUSYBOX_LINK）は build-stamp.sh にだけ書いてある
# shellcheck source=scripts/lib/build-stamp.sh
source "${PROJECT_ROOT}/scripts/lib/build-stamp.sh"

# Configuration
# `make test-busybox` はコンテナ内の build-system/ から呼ばれるので、
# ./build（カレント基準）ではなくプロジェクトルート基準で解決する。
# アーキテクチャは build-system/Makefile と同じく TARGET_ARCH で受ける
# （ARCH は互換のため残す）。
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
ARCH="${ARCH:-${TARGET_ARCH:-x86_64}}"
IMAGE_TYPE="${IMAGE_TYPE:-standard}"
BUSYBOX_LINK="$(kimigayo_busybox_link)"

BUSYBOX_INSTALL_DIR="${BUILD_DIR}/busybox-install-${ARCH}"
BUSYBOX_BIN="${BUSYBOX_INSTALL_DIR}/bin/busybox"

case "$ARCH" in
    arm64|aarch64) MUSL_ARCH="aarch64" ;;
    *)             MUSL_ARCH="$ARCH" ;;
esac

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

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

# 実行していないものは PASS にも FAIL にも数えない
test_skip() {
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    echo -e "${YELLOW}[SKIP]${NC} $1"
}

# Header
echo "========================================"
echo "BusyBox Integration Tests"
echo "========================================"
log_info "Architecture: ${ARCH}"
log_info "Image type: ${IMAGE_TYPE}"
log_info "Link mode: ${BUSYBOX_LINK}"
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
    echo "Please run (inside the build container):"
    echo "  make busybox TARGET_ARCH=${ARCH} IMAGE_TYPE=${IMAGE_TYPE}"
    exit 1
fi

# ビルドしたときのバリアントとリンク方法が、いま検査しようとしているものと
# 合っているか。スタンプは 1.38.0+standard+dynamic+<hash> の形
# （scripts/lib/build-stamp.sh の kimigayo_busybox_build_id）
built_id="$(kimigayo_built_version "$BUSYBOX_INSTALL_DIR")"
log_info "Build stamp: ${built_id:-<none>}"
case "$built_id" in
    *"+${IMAGE_TYPE}+${BUSYBOX_LINK}+"*|*"+${IMAGE_TYPE}+${BUSYBOX_LINK}")
        test_pass "Build stamp matches ${IMAGE_TYPE}/${BUSYBOX_LINK}" ;;
    *)
        test_fail "Build stamp '${built_id:-<none>}' is not ${IMAGE_TYPE}/${BUSYBOX_LINK} (rebuild: make busybox TARGET_ARCH=${ARCH} IMAGE_TYPE=${IMAGE_TYPE})" ;;
esac

# Test 2: Verify link mode (BUSYBOX_LINK, default: dynamic)
#
# 2026-10-12 に既定が dynamic になった（scripts/build-busybox.sh の冒頭）。
# 判定は build-busybox.sh のビルド直後の検査と同じ文字列で行う。
log_test "Test 2: Verify ${BUSYBOX_LINK} linking"
file_out="$(file "$BUSYBOX_BIN")"
if [ "$BUSYBOX_LINK" = "static" ]; then
    if echo "$file_out" | grep -qE "(statically linked|static-pie linked)"; then
        test_pass "BusyBox is statically linked"
    else
        test_fail "BusyBox is not statically linked: ${file_out}"
    fi
else
    if echo "$file_out" | grep -q "interpreter /lib/ld-musl-${MUSL_ARCH}.so.1"; then
        test_pass "BusyBox is dynamically linked against musl (/lib/ld-musl-${MUSL_ARCH}.so.1)"
    else
        test_fail "BusyBox is not dynamically linked against /lib/ld-musl-${MUSL_ARCH}.so.1: ${file_out}"
    fi
fi

# Test 3: Verify binary size
#
# 上限は実測（2026-10-12、BUSYBOX_LINK=dynamic、strip 済み）に約 15% の
# 余裕を足したもの。肥大化（config の取り違え・strip 漏れ）を拾うためで、
# 目標値ではない。
#   実測 KB    minimal  standard  extended
#   x86_64       870     1002      1026
#   arm64        941     1085      1120
# static は libc を取り込む分だけ 165〜169KB 大きい（build-busybox.sh）
log_test "Test 3: Verify binary size against upper bound"
binary_size=$(stat -c%s "$BUSYBOX_BIN" 2>/dev/null || stat -f%z "$BUSYBOX_BIN")
binary_size_kb=$((binary_size / 1024))

case "$IMAGE_TYPE" in
    minimal)  target_size=1100 ;;
    standard) target_size=1250 ;;
    extended) target_size=1300 ;;
    *)
        log_error "Unknown IMAGE_TYPE: ${IMAGE_TYPE} (minimal|standard|extended)"
        exit 1
        ;;
esac
if [ "$BUSYBOX_LINK" = "static" ]; then
    target_size=$((target_size + 200))
fi

log_info "Binary size: ${binary_size_kb} KB"
log_info "Upper bound: ${target_size} KB"

if [ "$binary_size_kb" -le "$target_size" ]; then
    test_pass "Binary size (${binary_size_kb} KB) within upper bound (${target_size} KB)"
else
    test_fail "Binary size (${binary_size_kb} KB) exceeds upper bound (${target_size} KB)"
fi

# ここから先はバイナリを実際に実行する。
# クロスビルドしたもの（例: amd64 のコンテナで arm64）は実行できないので
# まとめて SKIP にする。動的リンクなら /lib/ld-musl-<arch>.so.1 が
# 実行環境に必要（ビルドコンテナの Alpine は持っている）。
host_arch="$(uname -m)"
case "$host_arch" in
    arm64) host_arch="aarch64" ;;
esac
if [ "$host_arch" != "$MUSL_ARCH" ]; then
    test_skip "Runtime tests 4-18: cannot execute ${MUSL_ARCH} binary on ${host_arch} host"
    RUNTIME=false
elif [ "$BUSYBOX_LINK" = "dynamic" ] && [ ! -e "/lib/ld-musl-${MUSL_ARCH}.so.1" ]; then
    test_skip "Runtime tests 4-18: /lib/ld-musl-${MUSL_ARCH}.so.1 not present on this host (run inside the build container)"
    RUNTIME=false
else
    RUNTIME=true
fi

if [ "$RUNTIME" = true ]; then

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
    echo "test" > "${temp_dir}/testfile"

    if cd "$temp_dir" && "$BUSYBOX_BIN" tar -cf test.tar testfile 2>/dev/null && [ -f test.tar ]; then
        test_pass "tar command works correctly"
    else
        test_fail "tar command failed"
    fi
    cd - >/dev/null
    rm -rf "$temp_dir"
else
    test_skip "tar command not available in this build"
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
    test_skip "gzip command not available in this build"
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
    test_skip "No networking commands available in this build"
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

# Test 18: Verify shared library dependencies
#
# dynamic: 依存は libc（musl）だけであること。OpenRC と同じ
#          /lib/libc.so 以外を rootfs に入れていないので、ほかの
#          共有ライブラリを要求したらイメージで起動しない。
# static:  依存が無いこと。
log_test "Test 18: Verify shared library dependencies (${BUSYBOX_LINK})"
ldd_out="$(ldd "$BUSYBOX_BIN" 2>&1)" || ldd_rc=$?
if [ "$BUSYBOX_LINK" = "static" ]; then
    if echo "$ldd_out" | grep -qE "not a dynamic executable|statically linked" \
        || ! echo "$ldd_out" | grep -q "=>"; then
        test_pass "BusyBox has no shared library dependencies"
    else
        test_fail "BusyBox (static) has shared library dependencies:"
        echo "$ldd_out"
    fi
else
    # musl の ldd は「libc.musl-<arch>.so.1 => /lib/ld-musl-<arch>.so.1」と
    # ローダー自身の行を出す。libc 以外の NEEDED があれば失敗にする
    # static-pie を ldd に掛けてもローダーの行しか出ないので、
    # 「libc 以外が無い」だけでなく「libc がある」ことも確かめる
    libc_deps="$(echo "$ldd_out" | awk '/=>/ && /^[[:space:]]*libc(\.musl-[a-z0-9_]+)?\.so/')"
    other_deps="$(echo "$ldd_out" | awk '/=>/ && !/^[[:space:]]*libc(\.musl-[a-z0-9_]+)?\.so/')"
    if [ "${ldd_rc:-0}" -ne 0 ]; then
        test_fail "ldd failed on BusyBox (exit ${ldd_rc}):"
        echo "$ldd_out"
    elif [ -z "$libc_deps" ]; then
        test_fail "BusyBox does not depend on musl libc (not dynamically linked?):"
        echo "$ldd_out"
    elif [ -z "$other_deps" ]; then
        test_pass "BusyBox depends only on musl libc"
    else
        test_fail "BusyBox depends on libraries other than musl libc:"
        echo "$other_deps"
    fi
fi

fi  # RUNTIME

# Summary
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
log_info "Tests run:    ${TESTS_RUN}"
log_info "Tests passed: ${TESTS_PASSED}"
log_info "Tests failed: ${TESTS_FAILED}"
log_info "Skipped:      ${TESTS_SKIPPED}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    log_success "All tests passed!"
    exit 0
else
    log_error "Some tests failed"
    exit 1
fi
