#!/bin/bash
# Kimigayo OS - Kernel Download Script
# Downloads and verifies Linux kernel source code

set -e

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# バージョンは versions.mk（単一の真実の源）から読み込む
# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"

# Configuration（KERNEL_VERSION / KERNEL_SERIES は versions.sh が定義する）
KERNEL_BASE_URL="https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_SERIES}"
KERNEL_TARBALL="linux-${KERNEL_VERSION}.tar.xz"
KERNEL_TARBALL_SIGN="linux-${KERNEL_VERSION}.tar.sign"
DOWNLOAD_DIR="${PROJECT_ROOT}/build/downloads"
KERNEL_SRC_DIR="${PROJECT_ROOT}/build/kernel-src"

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

log_warn() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARN] ${timestamp}${NC} $*"
}

log_error() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR] ${timestamp}${NC} $*"
}

# Create directories
mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$KERNEL_SRC_DIR"

# Download kernel tarball if not exists
download_kernel() {
    local tarball_path="${DOWNLOAD_DIR}/${KERNEL_TARBALL}"
    local sign_path="${DOWNLOAD_DIR}/${KERNEL_TARBALL_SIGN}"

    if [ -f "$tarball_path" ]; then
        log_info "Kernel tarball already exists: $tarball_path"
    else
        log_info "Downloading kernel tarball (Linux ${KERNEL_VERSION})..."

        # Multiple mirror URLs for redundancy
        local urls=(
            "${KERNEL_BASE_URL}/${KERNEL_TARBALL}"
            "https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_VERSION%%.*}.x/${KERNEL_TARBALL}"
            "https://mirrors.edge.kernel.org/pub/linux/kernel/v${KERNEL_VERSION%%.*}.x/${KERNEL_TARBALL}"
        )

        local download_success=false
        for url in "${urls[@]}"; do
            log_info "Trying: $url"
            if curl -fSL --connect-timeout 30 --max-time 600 -o "$tarball_path" "$url"; then
                download_success=true
                log_success "Downloaded from: $url"
                break
            else
                log_warn "Failed to download from: $url"
            fi
        done

        if [ "$download_success" = false ]; then
            log_error "Failed to download kernel from all mirrors"
            return 1
        fi
    fi

    # Download signature file for verification
    if [ -f "$sign_path" ]; then
        log_info "Kernel signature already exists: $sign_path"
    else
        log_info "Downloading kernel signature..."
        local sign_url="${KERNEL_BASE_URL}/${KERNEL_TARBALL_SIGN}"
        curl -fSL --connect-timeout 30 --max-time 120 -o "$sign_path" "$sign_url" || {
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
    local kernel_dir="${KERNEL_SRC_DIR}/linux-${KERNEL_VERSION}"

    # Check if kernel source is properly extracted (Makefile must exist)
    if [ -f "${kernel_dir}/Makefile" ]; then
        log_info "Kernel source already extracted: ${kernel_dir}"
        return 0
    fi

    # Remove incomplete extraction if exists
    if [ -d "${kernel_dir}" ]; then
        log_warn "Removing incomplete kernel source directory"
        rm -rf "${kernel_dir}"
    fi

    log_info "Extracting kernel tarball to ${KERNEL_SRC_DIR}"
    tar -xf "$tarball_path" -C "$KERNEL_SRC_DIR" || {
        log_error "Failed to extract kernel tarball"
        return 1
    }

    # Verify extraction
    if [ ! -f "${kernel_dir}/Makefile" ]; then
        log_error "Kernel extraction incomplete: Makefile not found"
        return 1
    fi

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

# Verify SHA-256 against the value published by kernel.org
# 取得元: https://cdn.kernel.org/pub/linux/kernel/v<series>/sha256sums.asc
# 既知の値が無いバージョンでは上流から sha256sums.asc を引いて照合する。
verify_checksum() {
    local tarball_path="${DOWNLOAD_DIR}/${KERNEL_TARBALL}"
    local expected=""

    case "$KERNEL_VERSION" in
        6.18.55)
            expected="f410638061a165c12f42ab871d2f3fcd525515359b5faeee80969cff84524df9"
            ;;
        *)
            log_info "No pinned checksum for ${KERNEL_VERSION}, fetching sha256sums.asc..."
            expected="$(curl -fsSL --connect-timeout 30 --max-time 120 \
                "${KERNEL_BASE_URL}/sha256sums.asc" 2>/dev/null \
                | awk -v f="$KERNEL_TARBALL" '$2 == f { print $1 }' || true)"
            if [ -z "$expected" ]; then
                log_error "Could not determine expected checksum for ${KERNEL_TARBALL}"
                log_error "Pin it in this script or check network access to kernel.org"
                return 1
            fi
            ;;
    esac

    local actual
    actual="$(cat "${tarball_path}.sha256" 2>/dev/null || echo "")"
    if [ -z "$actual" ]; then
        log_error "Checksum file not found: ${tarball_path}.sha256"
        return 1
    fi

    if [ "$actual" = "$expected" ]; then
        log_info "Checksum verification: OK"
        return 0
    fi

    log_error "SHA-256 checksum mismatch!"
    log_error "Expected: $expected"
    log_error "Actual:   $actual"
    log_error "Refusing to use this tarball. Delete it and retry:"
    log_error "  rm -f ${tarball_path} ${tarball_path}.sha256"
    return 1
}

# Main
main() {
    log_info "Kimigayo OS - Kernel Download Script"
    log_info "Kernel Version: ${KERNEL_VERSION}"
    log_info "Download Directory: ${DOWNLOAD_DIR}"
    log_info "Source Directory: ${KERNEL_SRC_DIR}"
    log_info ""

    download_kernel || exit 1
    show_checksum
    verify_checksum || exit 1
    verify_kernel
    extract_kernel || exit 1

    log_info "Kernel download completed successfully"
    log_info "Kernel source: ${KERNEL_SRC_DIR}/linux-${KERNEL_VERSION}"
}

main "$@"
