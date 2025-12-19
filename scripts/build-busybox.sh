#!/usr/bin/env bash
#
# BusyBox Build Script for Kimigayo OS
# Builds BusyBox statically linked with musl libc
#

set -euo pipefail

# Save project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Configuration
BUSYBOX_VERSION="${BUSYBOX_VERSION:-1.36.1}"
BUILD_DIR="${BUILD_DIR:-./build}"
IMAGE_TYPE="${IMAGE_TYPE:-standard}"
ARCH="${ARCH:-x86_64}"

BUSYBOX_SRC_DIR="${BUILD_DIR}/busybox-${BUSYBOX_VERSION}"
BUSYBOX_BUILD_DIR="${BUILD_DIR}/busybox-build-${ARCH}"
BUSYBOX_INSTALL_DIR="${BUILD_DIR}/busybox-install-${ARCH}"
MUSL_INSTALL_DIR="${BUILD_DIR}/musl-install-${ARCH}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if source directory exists
if [ ! -d "$BUSYBOX_SRC_DIR" ]; then
    log_error "BusyBox source directory not found: $BUSYBOX_SRC_DIR"
    log_error "Please run download-busybox.sh first"
    exit 1
fi

# Check if musl is built
if [ ! -d "$MUSL_INSTALL_DIR" ]; then
    log_error "musl libc installation not found: $MUSL_INSTALL_DIR"
    log_error "Please run build-musl.sh first"
    exit 1
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
else
    # For x86_64, clear cross-compiler settings and use system musl
    sed -i "s|CONFIG_CROSS_COMPILER_PREFIX=.*|CONFIG_CROSS_COMPILER_PREFIX=\"\"|" .config
    sed -i "s|CONFIG_SYSROOT=.*|CONFIG_SYSROOT=\"\"|" .config
fi

# Set install prefix
install_prefix="${BUSYBOX_INSTALL_DIR}"
sed -i "s|CONFIG_PREFIX=.*|CONFIG_PREFIX=\"${install_prefix}\"|" .config

# Apply oldconfig with automatic default answers (non-interactive)
log_info "Resolving configuration dependencies..."
# Use 'yes ""' to automatically answer with default for all prompts
# This handles BusyBox versions that don't have olddefconfig
yes "" | make oldconfig > /dev/null 2>&1 || true

# Build BusyBox
log_info "Building BusyBox..."
log_info "This may take several minutes..."

# Set compiler flags for static musl build
# Alpine Linux's gcc is already configured to use musl
# Note: Don't use -static in CFLAGS as it affects compilation, only in LDFLAGS
export CFLAGS="-Os -fstack-protector-strong -D_FORTIFY_SOURCE=2"
export LDFLAGS="-static -Wl,-z,relro -Wl,-z,now"

# Ensure we're using the correct compiler
log_info "Compiler: ${CC}"
log_info "CFLAGS: ${CFLAGS}"
log_info "LDFLAGS: ${LDFLAGS}"

# Build with verbose output
if ! make -j"$(nproc)" SKIP_STRIP=y; then
    log_error "BusyBox build failed"
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
if file busybox | grep -q "statically linked"; then
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
