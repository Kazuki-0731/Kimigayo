#!/usr/bin/env bash
#
# OpenRC Build Script for Kimigayo OS
# Builds OpenRC init system with musl libc
#

set -euo pipefail

# Configuration
OPENRC_VERSION="${OPENRC_VERSION:-0.52.1}"
BUILD_DIR="${BUILD_DIR:-./build}"
ARCH="${ARCH:-x86_64}"

OPENRC_SRC_DIR="${BUILD_DIR}/openrc-${OPENRC_VERSION}"
OPENRC_BUILD_DIR="${BUILD_DIR}/openrc-build-${ARCH}"
OPENRC_INSTALL_DIR="${BUILD_DIR}/openrc-install-${ARCH}"
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
if [ ! -d "$OPENRC_SRC_DIR" ]; then
    log_error "OpenRC source directory not found: $OPENRC_SRC_DIR"
    log_error "Please run download-openrc.sh first"
    exit 1
fi

# Check if musl is built
if [ ! -d "$MUSL_INSTALL_DIR" ]; then
    log_error "musl libc installation not found: $MUSL_INSTALL_DIR"
    log_error "Please run build-musl.sh first"
    exit 1
fi

log_info "OpenRC Build Script"
log_info "Version: ${OPENRC_VERSION}"
log_info "Architecture: ${ARCH}"
log_info "Source directory: ${OPENRC_SRC_DIR}"
log_info "Build directory: ${OPENRC_BUILD_DIR}"
log_info "Install directory: ${OPENRC_INSTALL_DIR}"

# Create build directories
mkdir -p "$OPENRC_BUILD_DIR"
mkdir -p "$OPENRC_INSTALL_DIR"

# Architecture-specific settings
case "$ARCH" in
    x86_64)
        TARGET="x86_64-linux-musl"
        export CC="${CC:-gcc}"
        export AR="${AR:-ar}"
        export RANLIB="${RANLIB:-ranlib}"
        ;;
    arm64|aarch64)
        TARGET="aarch64-linux-musl"
        export CC="aarch64-linux-musl-gcc"
        export AR="aarch64-linux-musl-ar"
        export RANLIB="aarch64-linux-musl-ranlib"
        ;;
    *)
        log_error "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

log_info "Build configuration:"
log_info "  Target: ${TARGET}"
log_info "  CC: ${CC}"

# Check for meson and ninja
if ! command -v meson &> /dev/null; then
    log_error "meson not found. Please install meson build system."
    log_info "On Alpine: apk add meson"
    exit 1
fi

if ! command -v ninja &> /dev/null; then
    log_error "ninja not found. Please install ninja build tool."
    log_info "On Alpine: apk add ninja"
    exit 1
fi

# Set compiler flags for musl
# Alpine Linux's gcc is already configured to use musl
export CFLAGS="-Os -fstack-protector-strong -D_FORTIFY_SOURCE=2 -DBRANDING='\"Kimigayo\"'"
export LDFLAGS="-Wl,-z,relro -Wl,-z,now"

# Configure with meson
log_info "Configuring OpenRC with meson..."

# OpenRC-specific configuration options
meson_options=(
    "--prefix=/usr"
    "--sysconfdir=/etc"
    "--libdir=/usr/lib"
    "--sbindir=/usr/sbin"
    "--libexecdir=/lib/rc"
    "--buildtype=release"
    "-Db_pie=true"
    "-Db_staticpic=true"
    "-Dos=Linux"
    "-Dpam=false"
    "-Dselinux=disabled"
    "-Daudit=disabled"
    "-Dnewnet=false"
)

log_info "Meson options:"
for opt in "${meson_options[@]}"; do
    log_info "  $opt"
done

# Setup meson build
if ! meson setup "${meson_options[@]}" "$OPENRC_BUILD_DIR" "$OPENRC_SRC_DIR"; then
    log_error "Meson configuration failed"
    exit 1
fi

log_success "OpenRC configured successfully"

# Build OpenRC
log_info "Building OpenRC..."
log_info "This may take a few minutes..."

if ! ninja -C "$OPENRC_BUILD_DIR"; then
    log_error "OpenRC build failed"
    exit 1
fi

log_success "OpenRC build completed"

# Install to staging directory
log_info "Installing OpenRC to ${OPENRC_INSTALL_DIR}..."

# Use meson install with DESTDIR (absolute path required)
OPENRC_INSTALL_DIR_ABS="$(cd "$(dirname "$OPENRC_INSTALL_DIR")" && pwd)/$(basename "$OPENRC_INSTALL_DIR")"
log_info "Absolute install path: ${OPENRC_INSTALL_DIR_ABS}"

if ! DESTDIR="$OPENRC_INSTALL_DIR_ABS" meson install -C "$OPENRC_BUILD_DIR"; then
    log_error "OpenRC installation failed"
    log_info "Trying to check meson install output..."
    meson install -C "$OPENRC_BUILD_DIR" --dry-run || true
    exit 1
fi

log_success "OpenRC installed successfully"

# Verify installation
log_info "Verifying OpenRC installation..."

# Check possible locations (bin, sbin, usr/bin, usr/sbin)
essential_binaries=(
    "rc"
    "rc-status"
    "rc-service"
    "rc-update"
    "openrc"
    "openrc-init"
    "openrc-run"
    "openrc-shutdown"
)

all_found=true
for binary in "${essential_binaries[@]}"; do
    found=false
    location=""

    # Check multiple possible locations
    for dir in "bin" "sbin" "usr/bin" "usr/sbin"; do
        if [ -f "${OPENRC_INSTALL_DIR}/${dir}/${binary}" ]; then
            location="${dir}/${binary}"
            log_success "  ✓ ${location}"
            found=true
            break
        fi
    done

    if [ "$found" = false ]; then
        log_error "  ✗ ${binary} not found"
        all_found=false
    fi
done

if [ "$all_found" = false ]; then
    log_error "Some essential files are missing"
    log_info "Checking actual installation contents:"
    log_info "Searching for OpenRC binaries in ${OPENRC_INSTALL_DIR}..."
    find "${OPENRC_INSTALL_DIR}" -type f -name "openrc*" -o -name "rc-*" -o -name "rc" 2>/dev/null | while read -r file; do
        log_info "  Found: ${file#${OPENRC_INSTALL_DIR}/}"
    done
    log_info "Directory structure:"
    ls -la "${OPENRC_INSTALL_DIR}/" 2>/dev/null || true

    # Check all possible binary directories
    for dir in "bin" "sbin" "usr/bin" "usr/sbin"; do
        if [ -d "${OPENRC_INSTALL_DIR}/${dir}" ]; then
            log_info "Contents of ${dir}/:"
            ls -la "${OPENRC_INSTALL_DIR}/${dir}/" 2>/dev/null || true
        else
            log_info "${dir}/ does not exist"
        fi
    done

    exit 1
fi

log_success "All essential binaries verified"

# Check for init scripts directory
if [ -d "${OPENRC_INSTALL_DIR}/etc/init.d" ]; then
    init_count=$(find "${OPENRC_INSTALL_DIR}/etc/init.d" -type f 2>/dev/null | wc -l)
    log_info "Init scripts directory created with ${init_count} scripts"
else
    log_warning "Init scripts directory not created"
fi

# Check for runlevel directories
runlevels=("boot" "default" "shutdown" "sysinit")
for level in "${runlevels[@]}"; do
    if [ -d "${OPENRC_INSTALL_DIR}/etc/runlevels/${level}" ]; then
        log_success "  ✓ Runlevel: ${level}"
    else
        log_warning "  ✗ Runlevel directory missing: ${level}"
    fi
done

# Display final summary
log_success "OpenRC build completed successfully"
log_info "Build summary:"
log_info "  Version: ${OPENRC_VERSION}"
log_info "  Architecture: ${ARCH}"
log_info "  Installation directory: ${OPENRC_INSTALL_DIR}"

# List installed binaries
log_info "Installed OpenRC binaries:"
set +o pipefail
for dir in "${OPENRC_INSTALL_DIR}/sbin" "${OPENRC_INSTALL_DIR}/usr/sbin"; do
    if [ -d "$dir" ]; then
        find "$dir" -type f -o -type l 2>/dev/null | while read -r binary; do
            log_info "  - ${binary#${OPENRC_INSTALL_DIR}/}"
        done
    fi
done
set -o pipefail

log_success "OpenRC is ready for integration"
