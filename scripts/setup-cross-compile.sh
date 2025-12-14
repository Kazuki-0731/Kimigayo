#!/bin/sh
# Setup cross-compilation environment for Kimigayo OS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if running in Alpine
if [ -f /etc/alpine-release ]; then
    info "Running on Alpine Linux"
else
    warn "Not running on Alpine Linux - cross-compilation tools may differ"
fi

# Architecture
ARCH=${ARCH:-x86_64}
info "Setting up cross-compilation for: $ARCH"

# Install cross-compilation toolchain
case "$ARCH" in
    x86_64)
        info "Installing x86_64 toolchain"
        apk add --no-cache \
            gcc \
            g++ \
            musl-dev \
            linux-headers \
            binutils
        ;;
    arm64)
        info "Installing ARM64 toolchain"
        apk add --no-cache \
            gcc \
            g++ \
            musl-dev \
            linux-headers \
            binutils
        # Note: Alpine uses native musl, cross-compilation for ARM64
        # may require additional setup
        warn "ARM64 cross-compilation requires musl-cross-make or similar"
        ;;
    *)
        error "Unsupported architecture: $ARCH"
        ;;
esac

# Verify toolchain
info "Verifying toolchain installation"
command -v gcc >/dev/null 2>&1 || error "gcc not found"
command -v ld >/dev/null 2>&1 || error "ld not found"
command -v ar >/dev/null 2>&1 || error "ar not found"

# Display toolchain information
info "Toolchain information:"
gcc --version | head -n 1
ld --version | head -n 1

# Setup build environment variables
export CC="${CROSS_COMPILE}gcc"
export CXX="${CROSS_COMPILE}g++"
export LD="${CROSS_COMPILE}ld"
export AR="${CROSS_COMPILE}ar"
export STRIP="${CROSS_COMPILE}strip"

info "Cross-compilation environment setup completed"
info "Environment variables:"
echo "  CC=$CC"
echo "  CXX=$CXX"
echo "  LD=$LD"
echo "  AR=$AR"
echo "  STRIP=$STRIP"
