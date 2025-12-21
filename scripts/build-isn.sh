#!/usr/bin/env bash
#
# isn Package Manager Build Script for Kimigayo OS
# Builds isn static binary with musl libc
#

set -euo pipefail

# Save project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Configuration
ISN_VERSION="${ISN_VERSION:-0.1.0}"
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
ARCH="${ARCH:-x86_64}"

ISN_SRC_DIR="${PROJECT_ROOT}/src/pkg/isn"
ISN_BUILD_DIR="${BUILD_DIR}/pkg"
ISN_INSTALL_DIR="${BUILD_DIR}/pkg-install-${ARCH}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions with timestamp (JST)
log_info() {
    local timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[INFO] ${timestamp}${NC} $*"
}

log_success() {
    local timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[SUCCESS] ${timestamp}${NC} $*"
}

log_warning() {
    local timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARNING] ${timestamp}${NC} $*"
}

log_error() {
    local timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR] ${timestamp}${NC} $*"
}

# Check if isn is already built
if [ -f "${ISN_INSTALL_DIR}/bin/isn" ]; then
    log_info "isn already built and installed: ${ISN_INSTALL_DIR}"
    log_info "Skipping build (use 'make clean-pkg' to rebuild)"
    log_success "isn binary verified"
    log_info "isn build check completed!"
    exit 0
fi

# Check if source directory exists
if [ ! -d "$ISN_SRC_DIR" ]; then
    log_error "isn source directory not found: $ISN_SRC_DIR"
    exit 1
fi

log_info "isn Build Script"
log_info "Version: ${ISN_VERSION}"
log_info "Architecture: ${ARCH}"
log_info "Source directory: ${ISN_SRC_DIR}"
log_info "Install directory: ${ISN_INSTALL_DIR}"

# Create build directories
mkdir -p "$ISN_BUILD_DIR"
mkdir -p "$ISN_INSTALL_DIR/bin"

# Check for Rust toolchain
if ! command -v cargo &> /dev/null; then
    log_error "Rust toolchain not found. Please install Rust."
    log_info "Visit: https://rustup.rs/"
    exit 1
fi

# Check for musl target
case "$ARCH" in
    x86_64)
        TARGET="x86_64-unknown-linux-musl"
        ;;
    arm64|aarch64)
        TARGET="aarch64-unknown-linux-musl"
        ;;
    *)
        log_error "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

log_info "Build configuration:"
log_info "  Target: ${TARGET}"

# Check if rustup is available (for rustup-based installations)
if command -v rustup &> /dev/null; then
    # Check if musl target is installed
    if ! rustup target list --installed | grep -q "$TARGET"; then
        log_info "Installing Rust target: $TARGET"
        rustup target add "$TARGET"
    fi
else
    log_info "rustup not available (using system Rust from Alpine apk)"
    log_info "Skipping target installation - using default target"
fi

# Build isn
log_info "Building isn..."
log_info "This may take a few minutes..."

cd "$ISN_SRC_DIR"

# Build with cargo
if ! cargo build --release --target "$TARGET"; then
    log_error "isn build failed"
    exit 1
fi

log_success "isn build completed"

# Install to staging directory
log_info "Installing isn to ${ISN_INSTALL_DIR}..."

# Copy binary
cp "target/${TARGET}/release/isn" "${ISN_INSTALL_DIR}/bin/isn"
chmod +x "${ISN_INSTALL_DIR}/bin/isn"

log_success "isn installed successfully"

# Verify installation
log_info "Verifying isn installation..."

if [ ! -f "${ISN_INSTALL_DIR}/bin/isn" ]; then
    log_error "isn binary not found after installation"
    exit 1
fi

log_success "  ✓ ${ISN_INSTALL_DIR}/bin/isn"

# Check binary size
BINARY_SIZE=$(du -h "${ISN_INSTALL_DIR}/bin/isn" | awk '{print $1}')
log_info "Binary size: ${BINARY_SIZE}"

# Test binary
log_info "Testing isn binary..."
if "${ISN_INSTALL_DIR}/bin/isn" --version > /dev/null 2>&1; then
    log_success "  ✓ isn --version works"
else
    log_error "  ✗ isn --version failed"
    exit 1
fi

# Display final summary
log_success "isn build completed successfully"
log_info "Build summary:"
log_info "  Version: ${ISN_VERSION}"
log_info "  Architecture: ${ARCH}"
log_info "  Target: ${TARGET}"
log_info "  Installation directory: ${ISN_INSTALL_DIR}"
log_info "  Binary size: ${BINARY_SIZE}"

log_success "isn is ready for integration"

# Record build success
"${PROJECT_ROOT}/scripts/build-status.sh" record pkg 2>/dev/null || true
