#!/usr/bin/env bash
#
# BusyBox Build Script for Kimigayo OS
# Builds BusyBox statically linked with musl libc
#

set -euo pipefail

# Save script and project root directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Configuration
BUSYBOX_VERSION="${BUSYBOX_VERSION:-1.36.1}"
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
IMAGE_TYPE="${IMAGE_TYPE:-standard}"
ARCH="${ARCH:-x86_64}"

BUSYBOX_SRC_DIR="${BUILD_DIR}/busybox-${BUSYBOX_VERSION}"
BUSYBOX_BUILD_DIR="${BUILD_DIR}/busybox-build-${ARCH}"
BUSYBOX_INSTALL_DIR="${BUILD_DIR}/busybox-install-${ARCH}"

# MUSL_INSTALL_DIR can be overridden by environment variable
# This allows Makefile to pass the correct path based on MUSL_ARCH
if [ -z "$MUSL_INSTALL_DIR" ]; then
    MUSL_INSTALL_DIR="${BUILD_DIR}/musl-install-${ARCH}"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions with timestamp (JST)
log_info() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[INFO] ${timestamp}${NC} $*"
}

log_success() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[SUCCESS] ${timestamp}${NC} $*"
}

log_warning() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARNING] ${timestamp}${NC} $*"
}

log_error() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR] ${timestamp}${NC} $*"
}

# Check if BusyBox is already built
if [ -f "${BUSYBOX_INSTALL_DIR}/bin/busybox" ]; then
    log_info "BusyBox already built and installed: ${BUSYBOX_INSTALL_DIR}"
    log_info "Skipping build (use 'make clean' to rebuild)"
    log_info "BusyBox build check completed!"
    exit 0
fi

# Check if source directory exists
if [ ! -d "$BUSYBOX_SRC_DIR" ]; then
    log_error "BusyBox source directory not found: $BUSYBOX_SRC_DIR"
    log_error "Please run download-busybox.sh first"
    exit 1
fi

# Check if musl is built, auto-build if necessary
# Determine musl arch (aarch64 vs arm64)
MUSL_ARCH="$ARCH"
if [ "$ARCH" = "arm64" ]; then
    MUSL_ARCH="aarch64"
fi

# Try both naming conventions
MUSL_CHECK_PATHS=(
    "${MUSL_INSTALL_DIR}/lib/libc.a"
    "${BUILD_DIR}/musl-install-${MUSL_ARCH}/lib/libc.a"
    "${BUILD_DIR}/musl-install-${ARCH}/lib/libc.a"
)

MUSL_FOUND=false
for musl_path in "${MUSL_CHECK_PATHS[@]}"; do
    if [ -f "$musl_path" ]; then
        MUSL_INSTALL_DIR="$(dirname "$(dirname "$musl_path")")"
        export MUSL_INSTALL_DIR
        log_info "Found musl libc at: $musl_path"
        MUSL_FOUND=true
        break
    fi
done

if [ "$MUSL_FOUND" = false ]; then
    log_warning "musl libc not found, building automatically..."
    log_info "Downloading musl libc..."
    bash "${SCRIPT_DIR}/download-musl.sh" || {
        log_error "Failed to download musl libc"
        exit 1
    }
    log_info "Building musl libc for ${MUSL_ARCH}..."
    ARCH=$MUSL_ARCH bash "${SCRIPT_DIR}/build-musl.sh" || {
        log_error "Failed to build musl libc"
        exit 1
    }
    # Set the install directory
    MUSL_INSTALL_DIR="${BUILD_DIR}/musl-install-${MUSL_ARCH}"
    export MUSL_INSTALL_DIR
    log_success "musl libc built successfully at: ${MUSL_INSTALL_DIR}"
fi

# Apply patches for musl libc compatibility (if any)
if [ -f "${SCRIPT_DIR}/apply-busybox-patches.sh" ]; then
    log_info "Applying BusyBox patches..."
    bash "${SCRIPT_DIR}/apply-busybox-patches.sh"
    patch_exit_code=$?
    log_info "Patch script exited with code: $patch_exit_code"
    if [ "$patch_exit_code" -ne 0 ]; then
        log_error "Patch application failed with exit code $patch_exit_code"
        exit 1
    fi
fi

log_info "BusyBox Build Script"
log_info "Version: ${BUSYBOX_VERSION}"
log_info "Image type: ${IMAGE_TYPE}"
log_info "Architecture: ${ARCH}"
log_info "Source directory: ${BUSYBOX_SRC_DIR}"
log_info "Build directory: ${BUSYBOX_BUILD_DIR}"
log_info "Install directory: ${BUSYBOX_INSTALL_DIR}"

# Create build directories
mkdir -p "$BUSYBOX_BUILD_DIR"
mkdir -p "$BUSYBOX_INSTALL_DIR"

# Architecture-specific settings
case "$ARCH" in
    x86_64)
        TARGET="x86_64-linux-musl"
        CROSS_COMPILE=""
        export CC="${CC:-gcc}"
        export AR="${AR:-ar}"
        export RANLIB="${RANLIB:-ranlib}"
        export STRIP="${STRIP:-strip}"
        ;;
    arm64|aarch64)
        TARGET="aarch64-linux-musl"
        CROSS_COMPILE="aarch64-linux-musl-"
        export CC="${CROSS_COMPILE}gcc"
        export AR="${CROSS_COMPILE}ar"
        export RANLIB="${CROSS_COMPILE}ranlib"
        export STRIP="${CROSS_COMPILE}strip"
        export HOSTCC="gcc"
        # Tell BusyBox to use LLD linker and avoid GCC-specific libraries
        export LD="${CROSS_COMPILE}ld.lld"
        ;;
    *)
        log_error "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

log_info "Build configuration:"
log_info "  Target: ${TARGET}"
log_info "  CC: ${CC}"
log_info "  AR: ${AR}"
log_info "  Cross-compile prefix: ${CROSS_COMPILE:-none}"

# Select configuration file (absolute path)
config_file=""
case "$IMAGE_TYPE" in
    minimal)
        config_file="${PROJECT_ROOT}/src/busybox/config/minimal.config"
        ;;
    standard)
        config_file="${PROJECT_ROOT}/src/busybox/config/standard.config"
        ;;
    extended)
        config_file="${PROJECT_ROOT}/src/busybox/config/extended.config"
        ;;
    *)
        log_error "Unknown image type: $IMAGE_TYPE"
        log_error "Supported types: minimal, standard, extended"
        exit 1
        ;;
esac

if [ ! -f "$config_file" ]; then
    log_error "Configuration file not found: $config_file"
    exit 1
fi

log_info "Using configuration: $config_file"

# Copy source to build directory
log_info "Preparing build directory..."
rsync -a --delete "$BUSYBOX_SRC_DIR/" "$BUSYBOX_BUILD_DIR/"

# Change to build directory
cd "$BUSYBOX_BUILD_DIR"

# Apply configuration
log_info "Applying BusyBox configuration..."
cp "$config_file" .config

# Update configuration with musl paths
log_info "Updating configuration for musl libc..."

# Set cross-compiler prefix (only for ARM64)
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    if [ -n "$CROSS_COMPILE" ]; then
        sed -i "s|CONFIG_CROSS_COMPILER_PREFIX=.*|CONFIG_CROSS_COMPILER_PREFIX=\"${CROSS_COMPILE}\"|" .config
    fi
    # Set sysroot for musl (for cross-compilation)
    sed -i "s|CONFIG_SYSROOT=.*|CONFIG_SYSROOT=\"${MUSL_INSTALL_DIR}\"|" .config
    # Disable stack protector for ARM64 LLVM/Clang to avoid libssp_nonshared dependency
    sed -i "s|CONFIG_EXTRA_CFLAGS=.*|CONFIG_EXTRA_CFLAGS=\"-Os\"|" .config
    # Disable PIE for static builds (PIE + static is not compatible)
    sed -i "s|CONFIG_PIE=.*|CONFIG_PIE=n|" .config
    log_info "Disabled stack protector and PIE for ARM64 (LLVM/Clang compatibility)"
else
    # For x86_64, clear cross-compiler settings and use system musl
    sed -i "s|CONFIG_CROSS_COMPILER_PREFIX=.*|CONFIG_CROSS_COMPILER_PREFIX=\"\"|" .config
    sed -i "s|CONFIG_SYSROOT=.*|CONFIG_SYSROOT=\"\"|" .config
fi

# Set install prefix
install_prefix="${BUSYBOX_INSTALL_DIR}"
sed -i "s|CONFIG_PREFIX=.*|CONFIG_PREFIX=\"${install_prefix}\"|" .config

# Ensure static linking is enabled
log_info "Ensuring static linking configuration..."
sed -i "s|# CONFIG_STATIC is not set|CONFIG_STATIC=y|" .config
sed -i "s|CONFIG_STATIC=.*|CONFIG_STATIC=y|" .config

# Apply oldconfig with automatic default answers (non-interactive)
log_info "Resolving configuration dependencies..."
# Use 'yes ""' to automatically answer with default for all prompts
# This handles BusyBox versions that don't have olddefconfig
yes "" | make oldconfig > /dev/null 2>&1 || true

# Re-apply critical settings after oldconfig (oldconfig may reset some values)
sed -i "s|CONFIG_STATIC=.*|CONFIG_STATIC=y|" .config
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    sed -i "s|CONFIG_PIE=.*|CONFIG_PIE=n|" .config
    # Disable STATIC_LIBGCC for clang compatibility (avoid -lgcc, -lgcc_eh, crtbeginT.o)
    sed -i "s|CONFIG_STATIC_LIBGCC=.*|# CONFIG_STATIC_LIBGCC is not set|" .config
    log_info "Re-applied settings after oldconfig (STATIC=y, PIE=n, STATIC_LIBGCC=n for ARM64)"
else
    log_info "Re-applied settings after oldconfig (STATIC=y)"
fi

# Verify CONFIG_STATIC is set
if ! grep -q "^CONFIG_STATIC=y" .config; then
    log_error "Failed to enable CONFIG_STATIC in BusyBox configuration"
    exit 1
fi
log_success "CONFIG_STATIC=y verified"

# Build BusyBox
log_info "Building BusyBox..."
log_info "This may take several minutes..."

# Set compiler flags for static musl build
# Alpine Linux's gcc is already configured to use musl
# Note: Don't use -static in CFLAGS as it affects compilation, only in LDFLAGS
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    # For ARM64: Use standard static linking
    # Disable stack protector to avoid libssp_nonshared dependency with clang
    export CFLAGS="-Os -D_FORTIFY_SOURCE=2"
    export LDFLAGS="-static -Wl,-z,relro -Wl,-z,now"

    # Log musl location (already verified above)
    log_info "Using musl libc from: ${MUSL_INSTALL_DIR}"
    log_info "Stack protector disabled for ARM64 clang compatibility"
else
    # For x86_64: use stack protector (GCC has proper support)
    export CFLAGS="-Os -fstack-protector-strong -D_FORTIFY_SOURCE=2"
    export LDFLAGS="-static -Wl,-z,relro -Wl,-z,now"
fi

# Ensure we're using the correct compiler
log_info "Compiler: ${CC}"
log_info "CFLAGS: ${CFLAGS}"
log_info "LDFLAGS: ${LDFLAGS}"

# Build with verbose output

if ! make -j"$(nproc)" SKIP_STRIP=y 2>&1 | tee /tmp/busybox-build.log; then
    log_error "BusyBox build failed"
    log_error "Last 50 lines of build output:"
    tail -50 /tmp/busybox-build.log >&2
    exit 1
fi

log_success "BusyBox build completed"

# Check binary size
binary_size=$(stat -f%z busybox 2>/dev/null || stat -c%s busybox 2>/dev/null)
binary_size_kb=$((binary_size / 1024))
log_info "BusyBox binary size: ${binary_size_kb} KB"

# Size targets per image type
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
esac

if [ "$binary_size_kb" -gt "$target_size" ]; then
    log_warning "Binary size (${binary_size_kb} KB) exceeds target (${target_size} KB)"
else
    log_success "Binary size within target (${target_size} KB)"
fi

# Verify static linking
log_info "Verifying static linking..."
if file busybox | grep -qE "(statically linked|static-pie linked)"; then
    log_success "BusyBox is statically linked"
else
    log_error "BusyBox is not statically linked!"
    file busybox
    exit 1
fi

# Verify musl libc
if file busybox | grep -q "musl"; then
    log_success "BusyBox is linked with musl libc"
elif ldd busybox 2>&1 | grep -q "not a dynamic executable"; then
    log_success "BusyBox is statically linked (musl libc)"
else
    log_warning "Cannot verify musl libc linkage"
fi

# Install BusyBox
log_info "Installing BusyBox to ${install_prefix}..."
make install

# Strip binary manually with security-aware stripping
log_info "Stripping binary..."
"${STRIP}" --strip-all "${install_prefix}/bin/busybox"

# Verify installation
if [ ! -f "${install_prefix}/bin/busybox" ]; then
    log_error "BusyBox installation failed: binary not found"
    exit 1
fi

log_success "BusyBox installed successfully"

# List installed applets
log_info "Counting installed applets..."
applet_count=$(find "${install_prefix}" -type l 2>/dev/null | wc -l)
log_info "Total applets installed: ${applet_count}"

# Show sample of installed applets
log_info "Sample of installed applets:"
set +o pipefail
find "${install_prefix}" -type l 2>/dev/null | head -20 | while read -r link; do
    log_info "  - ${link#${install_prefix}/}"
done
set -o pipefail

# Display final summary
stripped_size=$(stat -f%z "${install_prefix}/bin/busybox" 2>/dev/null || stat -c%s "${install_prefix}/bin/busybox" 2>/dev/null)
stripped_size_kb=$((stripped_size / 1024))

log_success "BusyBox build completed successfully"
log_info "Build summary:"
log_info "  Image type: ${IMAGE_TYPE}"
log_info "  Architecture: ${ARCH}"
log_info "  Binary size (stripped): ${stripped_size_kb} KB"
log_info "  Target size: ${target_size} KB"
log_info "  Applets installed: ${applet_count}"
log_info "  Installation directory: ${install_prefix}"

# Record build success
"${PROJECT_ROOT}/scripts/build-status.sh" record busybox 2>/dev/null || true
