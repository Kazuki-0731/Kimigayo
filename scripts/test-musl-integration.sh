#!/bin/bash
# Kimigayo OS - musl libc Integration Test Script
# Tests musl libc library linking, compilation, and system call compatibility

# set -e は使わない。最初の失敗で抜けると後続のテストとサマリが出ず、
# 「どれが落ちたのか」が分からない。各テストの成否は record_test で数え、
# 最後に終了コードへ反映する。
set -uo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"
# shellcheck source=scripts/lib/build-stamp.sh
source "${PROJECT_ROOT}/scripts/lib/build-stamp.sh"

# build-system/Makefile と同じく TARGET_ARCH で受ける（ARCH は互換）。
# musl のディレクトリ名は aarch64（MUSL_ARCH のマッピング）
ARCH="${ARCH:-${TARGET_ARCH:-x86_64}}"
case "$ARCH" in
    arm64|aarch64) MUSL_ARCH="aarch64" ;;
    *)             MUSL_ARCH="$ARCH" ;;
esac
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
MUSL_INSTALL_DIR="${MUSL_INSTALL_DIR:-${BUILD_DIR}/musl-install-${MUSL_ARCH}}"
TEST_DIR="${BUILD_DIR}/musl-test-${MUSL_ARCH}"
TEST_LOG="${BUILD_DIR}/logs/musl-test.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# コンパイルして実行するテストを回せるか（init_test_env で決める）
CAN_RUN=true
SKIP_REASON=""

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*" | tee -a "$TEST_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$TEST_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$TEST_LOG"
}

log_test() {
    echo -e "${GREEN}[TEST]${NC} $*" | tee -a "$TEST_LOG"
}

# Initialize test environment
init_test_env() {
    mkdir -p "$TEST_DIR"
    mkdir -p "$(dirname "$TEST_LOG")"

    # Clear previous test log
    : > "$TEST_LOG"

    log_info "Initializing test environment"
    log_info "Test directory: $TEST_DIR"
    log_info "musl installation: $MUSL_INSTALL_DIR"

    # テスト 2〜5 は手元の gcc でコンパイルしてその場で実行する。
    # ビルドコンテナ（Alpine, linux/amd64）の中で、そのアーキテクチャの
    # musl に対してだけ意味がある。クロス（amd64 のコンテナで aarch64）は
    # 実行できないので SKIP にする。
    local host_arch
    host_arch="$(uname -m)"
    [ "$host_arch" = "arm64" ] && host_arch="aarch64"
    if [ "$(uname -s)" != "Linux" ]; then
        CAN_RUN=false
        SKIP_REASON="not a Linux host (run inside the build container)"
    elif [ "$host_arch" != "$MUSL_ARCH" ]; then
        CAN_RUN=false
        SKIP_REASON="cannot run ${MUSL_ARCH} binaries on ${host_arch} host"
    elif ! command -v gcc >/dev/null 2>&1; then
        CAN_RUN=false
        SKIP_REASON="gcc not found"
    fi
}

# Record test result: PASS / FAIL / SKIP
# SKIP は実行していないので、PASS にも FAIL にも数えない
record_test() {
    local test_name="$1"
    local result="$2"

    case "$result" in
        PASS)
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_PASSED=$((TESTS_PASSED + 1))
            log_test "✓ $test_name: PASS"
            ;;
        SKIP)
            TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
            log_warn "- $test_name: SKIP"
            ;;
        *)
            TESTS_RUN=$((TESTS_RUN + 1))
            TESTS_FAILED=$((TESTS_FAILED + 1))
            log_test "✗ $test_name: FAIL"
            ;;
    esac
}

# 実行できない環境なら SKIP を記録して真を返す
skip_if_cannot_run() {
    if [ "$CAN_RUN" != true ]; then
        log_warn "Skipping: ${SKIP_REASON}"
        record_test "$1" "SKIP"
        return 0
    fi
    return 1
}

# Test 1: Verify musl installation
test_musl_installation() {
    log_test "Test 1: Verify musl installation"

    local libc_so=""
    for path in "${MUSL_INSTALL_DIR}/lib/libc.so" "${MUSL_INSTALL_DIR}/usr/lib/libc.so"; do
        if [ -f "$path" ]; then
            libc_so="$path"
            break
        fi
    done

    if [ -n "$libc_so" ] && [ -d "${MUSL_INSTALL_DIR}/usr/include" ]; then
        record_test "musl installation" "PASS"
    else
        log_error "libc.so or usr/include not found under ${MUSL_INSTALL_DIR}"
        log_error "Please run (inside the build container): make musl TARGET_ARCH=${ARCH}"
        record_test "musl installation" "FAIL"
    fi

    # ビルドした版が versions.mk と合っているか
    # スタンプは "<版>+<入力ハッシュ>"（scripts/lib/build-stamp.sh）
    local built_id
    built_id="$(kimigayo_built_version "$MUSL_INSTALL_DIR")"
    case "$built_id" in
        "${MUSL_VERSION}"|"${MUSL_VERSION}+"*)
            log_info "Build stamp: ${built_id}"
            record_test "musl version (${MUSL_VERSION})" "PASS"
            ;;
        *)
            log_error "Build stamp '${built_id:-<none>}' does not match versions.mk (${MUSL_VERSION})"
            record_test "musl version (${MUSL_VERSION})" "FAIL"
            ;;
    esac
}

# Test 2: Compile and link simple C program
test_simple_compilation() {
    log_test "Test 2: Compile simple C program with musl"
    skip_if_cannot_run "simple compilation" && return 0

    local test_file="${TEST_DIR}/hello.c"
    local test_bin="${TEST_DIR}/hello"

    cat > "$test_file" << 'EOF'
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("Hello from musl libc!\n");
    return 0;
}
EOF

    # Compile with musl
    if gcc -static \
        -I"${MUSL_INSTALL_DIR}/usr/include" \
        -L"${MUSL_INSTALL_DIR}/usr/lib" \
        "$test_file" -o "$test_bin" 2>>"$TEST_LOG"; then

        # Run the compiled binary
        if "$test_bin" >> "$TEST_LOG" 2>&1; then
            record_test "simple compilation" "PASS"
            return 0
        else
            log_error "Failed to run compiled binary"
            record_test "simple compilation" "FAIL"
            return 1
        fi
    else
        log_error "Failed to compile test program"
        record_test "simple compilation" "FAIL"
        return 1
    fi
}

# Test 3: Test system calls
test_system_calls() {
    log_test "Test 3: Test system call compatibility"
    skip_if_cannot_run "system calls" && return 0

    local test_file="${TEST_DIR}/syscall_test.c"
    local test_bin="${TEST_DIR}/syscall_test"

    cat > "$test_file" << 'EOF'
#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>

int main() {
    // Test getpid
    pid_t pid = getpid();
    if (pid <= 0) {
        fprintf(stderr, "getpid() failed\n");
        return 1;
    }

    // Test file operations
    const char* test_file = "/tmp/musl_test_file";
    int fd = open(test_file, O_CREAT | O_WRONLY | O_TRUNC, 0644);
    if (fd < 0) {
        fprintf(stderr, "open() failed\n");
        return 1;
    }

    const char* test_data = "musl test\n";
    ssize_t written = write(fd, test_data, strlen(test_data));
    if (written != (ssize_t)strlen(test_data)) {
        fprintf(stderr, "write() failed\n");
        close(fd);
        return 1;
    }

    close(fd);
    unlink(test_file);

    printf("System call tests passed\n");
    return 0;
}
EOF

    # Compile with musl
    if gcc -static \
        -I"${MUSL_INSTALL_DIR}/usr/include" \
        -L"${MUSL_INSTALL_DIR}/usr/lib" \
        "$test_file" -o "$test_bin" 2>>"$TEST_LOG"; then

        # Run the test
        if "$test_bin" >> "$TEST_LOG" 2>&1; then
            record_test "system calls" "PASS"
            return 0
        else
            log_error "System call test failed"
            record_test "system calls" "FAIL"
            return 1
        fi
    else
        log_error "Failed to compile system call test"
        record_test "system calls" "FAIL"
        return 1
    fi
}

# Test 4: Test threading support
test_threading() {
    log_test "Test 4: Test pthread support"
    skip_if_cannot_run "threading" && return 0

    local test_file="${TEST_DIR}/thread_test.c"
    local test_bin="${TEST_DIR}/thread_test"

    cat > "$test_file" << 'EOF'
#include <stdio.h>
#include <pthread.h>
#include <unistd.h>

void* thread_func(void* arg) {
    printf("Thread running\n");
    return NULL;
}

int main() {
    pthread_t thread;

    if (pthread_create(&thread, NULL, thread_func, NULL) != 0) {
        fprintf(stderr, "pthread_create() failed\n");
        return 1;
    }

    pthread_join(thread, NULL);
    printf("Threading test passed\n");
    return 0;
}
EOF

    # Compile with musl and pthread
    if gcc -static -pthread \
        -I"${MUSL_INSTALL_DIR}/usr/include" \
        -L"${MUSL_INSTALL_DIR}/usr/lib" \
        "$test_file" -o "$test_bin" 2>>"$TEST_LOG"; then

        # Run the test
        if "$test_bin" >> "$TEST_LOG" 2>&1; then
            record_test "threading" "PASS"
            return 0
        else
            log_error "Threading test failed"
            record_test "threading" "FAIL"
            return 1
        fi
    else
        log_error "Failed to compile threading test"
        record_test "threading" "FAIL"
        return 1
    fi
}

# Test 5: Test dynamic linking
#
# 以前はコンパイルが通ったら PASS にしており、実行していなかった
# （しかもインタプリタに存在しないパスを指定していても通る）。
# いまはビルドした musl の libc.so をインタプリタにしたバイナリを
# 実際に起動し、/proc/self/maps で読み込まれたローダーがそれであることを
# 確かめる。システムの /lib/ld-musl-*.so.1 で動いても PASS にしない。
test_dynamic_linking() {
    log_test "Test 5: Test dynamic linking (run with the built musl loader)"
    skip_if_cannot_run "dynamic linking" && return 0

    local test_file="${TEST_DIR}/dynamic_test.c"
    local test_bin="${TEST_DIR}/dynamic_test"

    # musl では libc.so 自体が動的ローダー（lib/ld-musl-<arch>.so.1 は
    # /usr/lib/libc.so への絶対パスのシンボリックリンクで、インストール先
    # の中では解決できない）
    local libc_so="${MUSL_INSTALL_DIR}/usr/lib/libc.so"
    if [ ! -f "$libc_so" ]; then
        log_error "libc.so not found: $libc_so"
        record_test "dynamic linking" "FAIL"
        return 1
    fi
    libc_so="$(cd "$(dirname "$libc_so")" && pwd -P)/libc.so"

    cat > "$test_file" << 'EOF'
#include <stdio.h>
#include <string.h>

/* 読み込まれている libc（= ローダー）のパスを出す */
int main(void) {
    char line[4096];
    FILE *f = fopen("/proc/self/maps", "r");
    if (!f) {
        perror("fopen /proc/self/maps");
        return 1;
    }
    while (fgets(line, sizeof line, f)) {
        char *path = strchr(line, '/');
        if (path && (strstr(path, "libc") || strstr(path, "ld-musl"))) {
            fputs(path, stdout);
            break;
        }
    }
    fclose(f);
    return 0;
}
EOF

    rm -f "$test_bin"
    if ! gcc -I"${MUSL_INSTALL_DIR}/usr/include" \
        -L"${MUSL_INSTALL_DIR}/usr/lib" \
        -Wl,--dynamic-linker="$libc_so" \
        "$test_file" -o "$test_bin" 2>>"$TEST_LOG"; then
        log_error "Failed to compile with dynamic linking"
        record_test "dynamic linking" "FAIL"
        return 1
    fi

    local output
    if ! output="$("$test_bin" 2>>"$TEST_LOG")"; then
        log_error "Dynamically linked binary failed to run"
        record_test "dynamic linking" "FAIL"
        return 1
    fi
    echo "$output" >> "$TEST_LOG"
    log_info "Loaded libc: ${output}"

    if [ "$output" = "$libc_so" ]; then
        record_test "dynamic linking" "PASS"
    else
        log_error "Expected the built libc.so (${libc_so}) to be loaded"
        record_test "dynamic linking" "FAIL"
        return 1
    fi
}

# Show test summary
show_summary() {
    echo ""
    log_info "=========================================="
    log_info "musl libc Integration Test Summary"
    log_info "=========================================="
    log_info "Total tests run:    $TESTS_RUN"
    log_info "Tests passed:       $TESTS_PASSED"
    log_info "Tests failed:       $TESTS_FAILED"
    log_info "Tests skipped:      $TESTS_SKIPPED"
    log_info "=========================================="
    log_info "Test log: $TEST_LOG"

    if [ "$TESTS_RUN" -eq 0 ]; then
        log_error "✗ No tests were run"
        return 1
    elif [ "$TESTS_FAILED" -eq 0 ]; then
        log_info "✓ All tests passed!"
        return 0
    else
        log_error "✗ Some tests failed"
        return 1
    fi
}

# Main
main() {
    init_test_env

    log_info "Kimigayo OS - musl libc Integration Test"
    log_info "Architecture: $ARCH (musl: $MUSL_ARCH)"
    echo "" | tee -a "$TEST_LOG"

    # 個々の戻り値では止めない。成否は record_test が数え、show_summary が返す
    test_musl_installation
    test_simple_compilation
    test_system_calls
    test_threading
    test_dynamic_linking

    show_summary
}

main "$@"
