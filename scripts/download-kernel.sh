#!/bin/bash
# Kimigayo OS - Kernel Download Script
# Downloads and verifies Linux kernel source code

set -e

# Configuration
KERNEL_VERSION="${KERNEL_VERSION:-6.6.11}"
KERNEL_MAJOR_VERSION="$(echo "$KERNEL_VERSION" | cut -d. -f1)"
KERNEL_BASE_URL="https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_MAJOR_VERSION}.x"
KERNEL_TARBALL="linux-${KERNEL_VERSION}.tar.xz"
KERNEL_TARBALL_SIGN="linux-${KERNEL_VERSION}.tar.sign"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOWNLOAD_DIR="${PROJECT_ROOT}/build/downloads"
KERNEL_SRC_DIR="${PROJECT_ROOT}/build/kernel-src"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Create directories
mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$KERNEL_SRC_DIR"

# Download kernel tarball if not exists
download_kernel() {
    local url="${KERNEL_BASE_URL}/${KERNEL_TARBALL}"
    local sign_url="${KERNEL_BASE_URL}/${KERNEL_TARBALL_SIGN}"
    local tarball_path="${DOWNLOAD_DIR}/${KERNEL_TARBALL}"
    local sign_path="${DOWNLOAD_DIR}/${KERNEL_TARBALL_SIGN}"

    if [ -f "$tarball_path" ]; then
        log_info "Kernel tarball already exists: $tarball_path"
    else
        log_info "Downloading kernel tarball from $url"
        curl -fSL -o "$tarball_path" "$url" || {
            log_error "Failed to download kernel tarball"
            return 1
        }
    fi

    # Download signature file for verification
    if [ -f "$sign_path" ]; then
        log_info "Kernel signature already exists: $sign_path"
    else
        log_info "Downloading kernel signature from $sign_url"
        curl -fSL -o "$sign_path" "$sign_url" || {
            log_warn "Failed to download kernel signature (optional)"
        }
    fi
}

# Verify kernel tarball (GPG signature)
verify_kernel() {
    local tarball_path="${DOWNLOAD_DIR}/${KERNEL_TARBALL}"
    local sign_path="${DOWNLOAD_DIR}/${KERNEL_TARBALL_SIGN}"

    if [ ! -f "$sign_path" ]; then
        log_warn "Signature file not found, skipping GPG verification"
        return 0
    fi

    log_info "Verifying kernel signature (GPG)"

    # Decompress tarball temporarily for signature verification
    local uncompressed="${tarball_path%.xz}"
    if [ ! -f "$uncompressed" ]; then
        log_info "Decompressing tarball for signature verification"
        xz -dk "$tarball_path" || {
            log_error "Failed to decompress tarball"
            return 1
        }
    fi

    # Verify signature
    if command -v gpg2 &> /dev/null; then
        gpg2 --verify "$sign_path" "$uncompressed" 2>&1 | grep -q "Good signature" && {
            log_info "GPG signature verification: OK"
            rm -f "$uncompressed"
            return 0
        } || {
            log_warn "GPG signature verification failed (continuing anyway)"
            rm -f "$uncompressed"
            return 0
        }
    else
        log_warn "gpg2 not found, skipping signature verification"
    fi
}

# Extract kernel tarball
extract_kernel() {
    local tarball_path="${DOWNLOAD_DIR}/${KERNEL_TARBALL}"

    if [ -d "${KERNEL_SRC_DIR}/linux-${KERNEL_VERSION}" ]; then
        log_info "Kernel source already extracted: ${KERNEL_SRC_DIR}/linux-${KERNEL_VERSION}"
        return 0
    fi

    log_info "Extracting kernel tarball to ${KERNEL_SRC_DIR}"
    tar -xf "$tarball_path" -C "$KERNEL_SRC_DIR" || {
        log_error "Failed to extract kernel tarball"
        return 1
    }

    log_info "Kernel extracted successfully"
}

# Calculate and display checksum
show_checksum() {
    local tarball_path="${DOWNLOAD_DIR}/${KERNEL_TARBALL}"

    log_info "Calculating SHA-256 checksum"
    if command -v sha256sum &> /dev/null; then
        sha256sum "$tarball_path" | awk '{print $1}' > "${tarball_path}.sha256"
        log_info "SHA-256: $(cat "${tarball_path}.sha256")"
    elif command -v shasum &> /dev/null; then
        shasum -a 256 "$tarball_path" | awk '{print $1}' > "${tarball_path}.sha256"
        log_info "SHA-256: $(cat "${tarball_path}.sha256")"
    else
        log_warn "sha256sum/shasum not found, skipping checksum"
    fi
}

# Main
main() {
    log_info "Kimigayo OS - Kernel Download Script"
    log_info "Kernel Version: ${KERNEL_VERSION}"
    log_info "Download Directory: ${DOWNLOAD_DIR}"
    log_info "Source Directory: ${KERNEL_SRC_DIR}"
    echo ""

    download_kernel || exit 1
    show_checksum
    verify_kernel
    extract_kernel || exit 1

    log_info "Kernel download completed successfully"
    log_info "Kernel source: ${KERNEL_SRC_DIR}/linux-${KERNEL_VERSION}"
}

main "$@"
