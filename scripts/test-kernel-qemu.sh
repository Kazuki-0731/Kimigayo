#!/bin/bash
# Kimigayo OS - QEMU Kernel Boot Test Script
# Tests kernel bootability in QEMU

set -e

# Configuration
KERNEL_VERSION="${KERNEL_VERSION:-6.6.11}"
ARCH="${ARCH:-x86_64}"
TIMEOUT="${TIMEOUT:-30}"
RAM="${RAM:-256M}"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
KERNEL_OUTPUT_DIR="${PROJECT_ROOT}/build/kernel/output"
TEST_LOG_DIR="${PROJECT_ROOT}/build/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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

log_qemu() {
    echo -e "${CYAN}[QEMU]${NC} $*"
}

# Check if QEMU is installed
check_qemu() {
    log_info "Checking for QEMU installation"

    case "$ARCH" in
        x86_64)
            if command -v qemu-system-x86_64 &> /dev/null; then
                log_info "QEMU x86_64 found: $(which qemu-system-x86_64)"
                return 0
            else
                log_error "qemu-system-x86_64 not found"
                log_error "Install with: brew install qemu (macOS) or apt-get install qemu-system-x86 (Linux)"
                return 1
            fi
            ;;
        arm64)
            if command -v qemu-system-aarch64 &> /dev/null; then
                log_info "QEMU aarch64 found: $(which qemu-system-aarch64)"
                return 0
            else
                log_error "qemu-system-aarch64 not found"
                log_error "Install with: brew install qemu (macOS) or apt-get install qemu-system-arm (Linux)"
                return 1
            fi
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            return 1
            ;;
    esac
}

# Check if kernel image exists
check_kernel() {
    log_info "Checking for kernel image"

    local kernel_image="${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}"

    if [ -f "$kernel_image" ]; then
        log_info "Kernel image found: $kernel_image"
        local size
        size=$(stat -f%z "$kernel_image" 2>/dev/null || stat -c%s "$kernel_image" 2>/dev/null || echo 0)
        local size_mb=$((size / 1024 / 1024))
        log_info "Kernel size: ${size_mb}MB"
        return 0
    else
        log_error "Kernel image not found: $kernel_image"
        log_error "Please build the kernel first with: make kernel"
        return 1
    fi
}

# Create minimal initramfs for testing
create_minimal_initramfs() {
    log_info "Creating minimal initramfs for testing"

    local initramfs_dir="${PROJECT_ROOT}/build/test-initramfs"
    local initramfs_img="${PROJECT_ROOT}/build/test-initramfs.cpio.gz"

    rm -rf "$initramfs_dir"
    mkdir -p "$initramfs_dir"

    # Create minimal directory structure
    mkdir -p "$initramfs_dir"/{bin,sbin,etc,proc,sys,dev,tmp,root}

    # Create minimal init script
    cat > "$initramfs_dir/init" << 'EOF'
#!/bin/sh
# Minimal init for kernel boot test

mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev

echo "========================================="
echo "Kimigayo OS Kernel Boot Test"
echo "========================================="
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "========================================="

# Show kernel boot messages
dmesg | tail -20

echo ""
echo "Kernel boot test: SUCCESS"
echo "Shutting down in 3 seconds..."

sleep 3

# Shutdown
poweroff -f
EOF

    chmod +x "$initramfs_dir/init"

    # Create initramfs
    cd "$initramfs_dir"
    find . | cpio -o -H newc 2>/dev/null | gzip > "$initramfs_img"

    if [ -f "$initramfs_img" ]; then
        log_info "Initramfs created: $initramfs_img"
        return 0
    else
        log_error "Failed to create initramfs"
        return 1
    fi
}

# Run QEMU boot test (x86_64)
test_qemu_x86_64() {
    log_test "Testing kernel boot in QEMU (x86_64)"

    local kernel_image="${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}"
    local initramfs_img="${PROJECT_ROOT}/build/test-initramfs.cpio.gz"
    local qemu_log="${TEST_LOG_DIR}/qemu-boot-test.log"

    mkdir -p "$TEST_LOG_DIR"

    log_qemu "Starting QEMU..."
    log_qemu "Kernel: $kernel_image"
    log_qemu "RAM: $RAM"
    log_qemu "Timeout: ${TIMEOUT}s"

    # QEMU command
    timeout $TIMEOUT qemu-system-x86_64 \
        -kernel "$kernel_image" \
        -initrd "$initramfs_img" \
        -m "$RAM" \
        -nographic \
        -append "console=ttyS0 quiet" \
        -no-reboot \
        2>&1 | tee "$qemu_log"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_info "QEMU boot test completed successfully"
        return 0
    elif [ $exit_code -eq 124 ]; then
        log_warn "QEMU boot test timed out after ${TIMEOUT}s"
        log_warn "This may indicate kernel panic or hang"
        return 1
    else
        log_error "QEMU boot test failed with exit code: $exit_code"
        return 1
    fi
}

# Run QEMU boot test (ARM64)
test_qemu_arm64() {
    log_test "Testing kernel boot in QEMU (ARM64)"

    local kernel_image="${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}"
    local initramfs_img="${PROJECT_ROOT}/build/test-initramfs.cpio.gz"
    local qemu_log="${TEST_LOG_DIR}/qemu-boot-test.log"

    mkdir -p "$TEST_LOG_DIR"

    log_qemu "Starting QEMU..."
    log_qemu "Kernel: $kernel_image"
    log_qemu "RAM: $RAM"
    log_qemu "Timeout: ${TIMEOUT}s"

    # QEMU command for ARM64
    timeout $TIMEOUT qemu-system-aarch64 \
        -machine virt \
        -cpu cortex-a57 \
        -kernel "$kernel_image" \
        -initrd "$initramfs_img" \
        -m "$RAM" \
        -nographic \
        -append "console=ttyAMA0" \
        -no-reboot \
        2>&1 | tee "$qemu_log"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_info "QEMU boot test completed successfully"
        return 0
    elif [ $exit_code -eq 124 ]; then
        log_warn "QEMU boot test timed out after ${TIMEOUT}s"
        log_warn "This may indicate kernel panic or hang"
        return 1
    else
        log_error "QEMU boot test failed with exit code: $exit_code"
        return 1
    fi
}

# Check boot test results
check_boot_results() {
    log_test "Analyzing boot test results"

    local qemu_log="${TEST_LOG_DIR}/qemu-boot-test.log"

    if [ ! -f "$qemu_log" ]; then
        log_warn "QEMU log not found: $qemu_log"
        return 1
    fi

    # Check for success message
    if grep -q "Kernel boot test: SUCCESS" "$qemu_log"; then
        log_info "✓ Kernel booted successfully"
    else
        log_warn "✗ Success message not found in boot log"
    fi

    # Check for kernel panic
    if grep -qi "kernel panic" "$qemu_log"; then
        log_error "✗ Kernel panic detected"
        grep -i "kernel panic" "$qemu_log"
        return 1
    else
        log_info "✓ No kernel panic detected"
    fi

    # Check for Oops
    if grep -qi "oops:" "$qemu_log"; then
        log_warn "⚠ Kernel Oops detected"
        grep -i "oops:" "$qemu_log"
    else
        log_info "✓ No kernel Oops detected"
    fi

    return 0
}

# Dry run mode (check only, don't boot)
dry_run() {
    log_info "Dry run mode - checking prerequisites only"

    check_qemu || return 1
    check_kernel || return 1

    log_info "All prerequisites satisfied"
    log_info "To run actual boot test: $0 (without DRY_RUN=1)"

    return 0
}

# Main
main() {
    log_info "Kimigayo OS - QEMU Kernel Boot Test"
    log_info "Kernel Version: ${KERNEL_VERSION}"
    log_info "Architecture: ${ARCH}"
    echo ""

    # Dry run mode
    if [ "${DRY_RUN:-0}" = "1" ]; then
        dry_run
        exit $?
    fi

    # Check prerequisites
    check_qemu || exit 1
    check_kernel || exit 1

    # Create initramfs
    create_minimal_initramfs || exit 1

    # Run QEMU test
    case "$ARCH" in
        x86_64)
            test_qemu_x86_64
            ;;
        arm64)
            test_qemu_arm64
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac

    local qemu_result=$?

    # Check results
    check_boot_results

    # Summary
    echo ""
    log_info "====================================="
    log_info "QEMU Boot Test Summary"
    log_info "====================================="
    log_info "Architecture: $ARCH"
    log_info "Kernel: ${KERNEL_VERSION}"

    if [ $qemu_result -eq 0 ]; then
        log_info "Result: SUCCESS ✓"
        log_info "====================================="
        exit 0
    else
        log_error "Result: FAILED ✗"
        log_info "====================================="
        log_info "Check logs: ${TEST_LOG_DIR}/qemu-boot-test.log"
        exit 1
    fi
}

main "$@"
