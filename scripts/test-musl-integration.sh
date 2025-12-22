#!/bin/bash
# Kimigayo OS - musl libc Integration Test Script
# Tests musl libc library linking, compilation, and system call compatibility

set -e

# Configuration
ARCH="${ARCH:-x86_64}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MUSL_INSTALL_DIR="${PROJECT_ROOT}/build/musl-install-${ARCH}"
TEST_DIR="${PROJECT_ROOT}/build/musl-test-${ARCH}"
TEST_LOG="${PROJECT_ROOT}/build/logs/musl-test.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

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
    log_info "Initializing test environment"
    mkdir -p "$TEST_DIR"
    mkdir -p "$(dirname "$TEST_LOG")"

    # Clear previous test log
    > "$TEST_LOG"

    log_info "Test directory: $TEST_DIR"
    log_info "musl installation: $MUSL_INSTALL_DIR"
}

# Record test result
record_test() {
    local test_name="$1"
    local result="$2"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [ "$result" = "PASS" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_test "✓ $test_name: PASS"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        log_test "✗ $test_name: FAIL"
    fi
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
        return 0
    else
        record_test "musl installation" "FAIL"
        return 1
    fi
}

# Test 2: Compile and link simple C program
test_simple_compilation() {
    log_test "Test 2: Compile simple C program with musl"

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
test_dynamic_linking() {
    log_test "Test 5: Test dynamic linking"

    local test_file="${TEST_DIR}/dynamic_test.c"
    local test_bin="${TEST_DIR}/dynamic_test"

    cat > "$test_file" << 'EOF'
#include <stdio.h>
#include <dlfcn.h>

int main() {
    printf("Dynamic linking test\n");
    return 0;
}
EOF

    # Find libc.so
    local libc_so=""
    for path in "${MUSL_INSTALL_DIR}/lib/libc.so" "${MUSL_INSTALL_DIR}/usr/lib/libc.so"; do
        if [ -f "$path" ]; then
            libc_so="$path"
            break
        fi
    done

    if [ -z "$libc_so" ]; then
        log_warn "libc.so not found, skipping dynamic linking test"
        record_test "dynamic linking" "SKIP"
        return 0
    fi

    # Compile dynamically
    if gcc -I"${MUSL_INSTALL_DIR}/usr/include" \
        -L"${MUSL_INSTALL_DIR}/usr/lib" \
        -Wl,--dynamic-linker="$libc_so" \
        "$test_file" -o "$test_bin" 2>>"$TEST_LOG"; then

        record_test "dynamic linking compilation" "PASS"
        return 0
    else
        log_error "Failed to compile with dynamic linking"
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
    log_info "Success rate:       $(( TESTS_PASSED * 100 / TESTS_RUN ))%"
    log_info "=========================================="
    log_info "Test log: $TEST_LOG"

    if [ $TESTS_FAILED -eq 0 ]; then
        log_info "✓ All tests passed!"
        return 0
    else
        log_error "✗ Some tests failed"
        return 1
    fi
}

# Main
main() {
    log_info "Kimigayo OS - musl libc Integration Test"
    log_info "Architecture: $ARCH"
    echo "" | tee -a "$TEST_LOG"

    init_test_env

    test_musl_installation
    test_simple_compilation
    test_system_calls
    test_threading
    test_dynamic_linking

    show_summary
}

main "$@"
