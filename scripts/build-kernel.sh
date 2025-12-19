#!/bin/bash
# Kimigayo OS - Kernel Build Script
# Builds Linux kernel with security hardening

set -e

# Configuration
KERNEL_VERSION="${KERNEL_VERSION:-6.6.11}"
ARCH="${ARCH:-x86_64}"
BUILD_TYPE="${BUILD_TYPE:-release}"
JOBS="${JOBS:-$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)}"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
KERNEL_SRC_DIR="${PROJECT_ROOT}/build/kernel-src/linux-${KERNEL_VERSION}"
KERNEL_BUILD_DIR="${PROJECT_ROOT}/build/kernel"
KERNEL_CONFIG_DIR="${PROJECT_ROOT}/src/kernel/config"
BUILD_LOG="${PROJECT_ROOT}/build/logs/kernel-build.log"

# Output
KERNEL_OUTPUT_DIR="${PROJECT_ROOT}/build/kernel/output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*" | tee -a "$BUILD_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$BUILD_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$BUILD_LOG"
}

log_build() {
    echo -e "${CYAN}[BUILD]${NC} $*" | tee -a "$BUILD_LOG"
}

# Architecture-specific settings
setup_arch() {
    case "$ARCH" in
        x86_64)
            export ARCH=x86_64
            export CROSS_COMPILE="${CROSS_COMPILE:-}"
            KERNEL_ARCH="x86"
            KERNEL_CONFIG="x86_64_defconfig"
            ;;
        arm64)
            export ARCH=arm64
            export CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-musl-}"
            KERNEL_ARCH="arm64"
            KERNEL_CONFIG="defconfig"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac

    log_info "Architecture: $ARCH"
    log_info "Cross Compiler: ${CROSS_COMPILE:-native}"
    log_info "Kernel Arch: $KERNEL_ARCH"
}

# Create build directories
init_build_dirs() {
    mkdir -p "$KERNEL_BUILD_DIR"
    mkdir -p "$KERNEL_OUTPUT_DIR"
    mkdir -p "$(dirname "$BUILD_LOG")"
    mkdir -p "$KERNEL_CONFIG_DIR"

    log_info "Build directories initialized"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking build prerequisites"

    if [ ! -d "$KERNEL_SRC_DIR" ]; then
        log_error "Kernel source not found: $KERNEL_SRC_DIR"
        log_error "Please run download-kernel.sh first"
        exit 1
    fi

    # Check for required tools
    local required_tools=("make" "gcc" "bc" "flex" "bison")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_warn "$tool not found (may be required for kernel build)"
        fi
    done

    log_info "Prerequisites check completed"
}

# Generate kernel config
generate_kernel_config() {
    log_build "Generating kernel configuration for $ARCH"

    cd "$KERNEL_SRC_DIR" || exit 1

    # Use custom config if available, otherwise use default
    local custom_config="${KERNEL_CONFIG_DIR}/${ARCH}.config"
    if [ -f "$custom_config" ]; then
        log_info "Using custom kernel config: $custom_config"
        cp "$custom_config" .config
    else
        log_info "Using default kernel config: $KERNEL_CONFIG"
        make ARCH="$KERNEL_ARCH" "$KERNEL_CONFIG" O="$KERNEL_BUILD_DIR" || {
            log_error "Failed to generate default config"
            exit 1
        }

        # Copy generated config to build dir
        if [ -f "$KERNEL_BUILD_DIR/.config" ]; then
            cp "$KERNEL_BUILD_DIR/.config" .config
        fi

        # Create default custom config template
        log_info "Creating default config template: $custom_config"
        cat > "$custom_config" << 'EOF'
# Kimigayo OS Kernel Configuration
# This is a placeholder config file
# Actual configuration will be generated from kernel defconfig
# with Kimigayo OS specific security and optimization settings
#
# Security Hardening Features:
# CONFIG_SECURITY=y
# CONFIG_SECURITY_DMESG_RESTRICT=y
# CONFIG_SECURITY_PERF_EVENTS_RESTRICT=y
# CONFIG_SECURITY_NETWORK=y
# CONFIG_HARDENED_USERCOPY=y
# CONFIG_FORTIFY_SOURCE=y
# CONFIG_GCC_PLUGIN_STACKLEAK=y
# CONFIG_GCC_PLUGIN_STRUCTLEAK=y
# CONFIG_GCC_PLUGIN_STRUCTLEAK_BYREF_ALL=y
# CONFIG_GCC_PLUGIN_LATENT_ENTROPY=y
# CONFIG_GCC_PLUGIN_RANDSTRUCT=y
# CONFIG_RANDOMIZE_BASE=y
# CONFIG_RANDOMIZE_MEMORY=y
#
# Note: Run 'make menuconfig' to customize this configuration
EOF
    fi

    log_info "Kernel configuration generated"
}

# Apply security hardening to kernel config
apply_security_hardening() {
    log_build "Applying security hardening to kernel config"

    cd "$KERNEL_SRC_DIR" || exit 1

    # Enable security features via scripts/config
    if [ -f scripts/config ]; then
        # ASLR and security features
        scripts/config --enable RANDOMIZE_BASE
        scripts/config --enable RANDOMIZE_MEMORY
        scripts/config --enable SECURITY
        scripts/config --enable SECURITY_DMESG_RESTRICT
        scripts/config --enable HARDENED_USERCOPY
        scripts/config --enable FORTIFY_SOURCE

        # Stack protection
        scripts/config --enable STACKPROTECTOR
        scripts/config --enable STACKPROTECTOR_STRONG

        # Kernel panic settings
        scripts/config --enable PANIC_ON_OOPS
        scripts/config --set-val PANIC_TIMEOUT 10

        log_info "Security hardening applied to kernel config"
    else
        log_warn "scripts/config not found, skipping config modifications"
    fi
}

# Build kernel
build_kernel() {
    log_build "Building Linux kernel ${KERNEL_VERSION} for ${ARCH}"
    log_info "Using ${JOBS} parallel jobs"

    cd "$KERNEL_SRC_DIR" || exit 1

    # Build kernel
    log_info "Starting kernel compilation..."
    log_info "This may take 5-30 minutes depending on CPU cores and configuration..."
    log_info "Progress will be shown below:"
    log_info "Log file: $BUILD_LOG"
    echo "=========================================="

    # Run make with unbuffered output for real-time display in GitHub Actions
    # stdbuf disables buffering to show output immediately
    stdbuf -oL -eL make -j"$JOBS" ARCH="$KERNEL_ARCH" CROSS_COMPILE="$CROSS_COMPILE" V=1 2>&1 | \
        while IFS= read -r line; do
            echo "$line"
            echo "$line" >> "$BUILD_LOG"
        done || {
        log_error "Kernel build failed"
        log_error "Check log file: $BUILD_LOG"
        exit 1
    }

    echo "=========================================="

    log_info "Kernel build completed successfully"
}

# Install kernel to output directory
install_kernel() {
    log_build "Installing kernel to output directory"

    cd "$KERNEL_SRC_DIR" || exit 1

    # Copy kernel image
    case "$ARCH" in
        x86_64)
            if [ -f "arch/x86/boot/bzImage" ]; then
                cp arch/x86/boot/bzImage "$KERNEL_OUTPUT_DIR/vmlinuz-${KERNEL_VERSION}-${ARCH}"
                log_info "Kernel image: $KERNEL_OUTPUT_DIR/vmlinuz-${KERNEL_VERSION}-${ARCH}"
            else
                log_error "Kernel image not found: arch/x86/boot/bzImage"
                exit 1
            fi
            ;;
        arm64)
            if [ -f "arch/arm64/boot/Image" ]; then
                cp arch/arm64/boot/Image "$KERNEL_OUTPUT_DIR/vmlinuz-${KERNEL_VERSION}-${ARCH}"
                log_info "Kernel image: $KERNEL_OUTPUT_DIR/vmlinuz-${KERNEL_VERSION}-${ARCH}"
            else
                log_error "Kernel image not found: arch/arm64/boot/Image"
                exit 1
            fi
            ;;
    esac

    # Copy System.map and config
    cp System.map "$KERNEL_OUTPUT_DIR/System.map-${KERNEL_VERSION}-${ARCH}" 2>/dev/null || true
    cp .config "$KERNEL_OUTPUT_DIR/config-${KERNEL_VERSION}-${ARCH}" 2>/dev/null || true

    # Install modules (if built)
    if make modules_install INSTALL_MOD_PATH="$KERNEL_OUTPUT_DIR/modules" ARCH="$KERNEL_ARCH" 2>/dev/null; then
        log_info "Kernel modules installed to $KERNEL_OUTPUT_DIR/modules"
    else
        log_warn "No kernel modules to install"
    fi

    log_info "Kernel installation completed"
}

# Show build summary
show_summary() {
    log_info "Build Summary"
    log_info "============================================"
    log_info "Kernel Version: $KERNEL_VERSION"
    log_info "Architecture: $ARCH"
    log_info "Build Type: $BUILD_TYPE"
    log_info "Build Jobs: $JOBS"
    log_info "============================================"

    if [ -f "$KERNEL_OUTPUT_DIR/vmlinuz-${KERNEL_VERSION}-${ARCH}" ]; then
        local kernel_size=$(du -h "$KERNEL_OUTPUT_DIR/vmlinuz-${KERNEL_VERSION}-${ARCH}" | cut -f1)
        log_info "Kernel Image: vmlinuz-${KERNEL_VERSION}-${ARCH} (${kernel_size})"
    fi

    log_info "Build Log: $BUILD_LOG"
    log_info "Output Directory: $KERNEL_OUTPUT_DIR"
    log_info "============================================"
}

# Main
main() {
    log_info "Kimigayo OS - Kernel Build Script"
    log_info "Kernel Version: ${KERNEL_VERSION}"
    log_info "Target Architecture: ${ARCH}"
    log_info "Build Type: ${BUILD_TYPE}"
    echo "" | tee -a "$BUILD_LOG"

    setup_arch
    init_build_dirs
    check_prerequisites
    generate_kernel_config
    apply_security_hardening
    build_kernel
    install_kernel
    show_summary

    log_info "Kernel build completed successfully!"
}

main "$@"
