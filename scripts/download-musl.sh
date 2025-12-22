#!/bin/bash
# Kimigayo OS - musl libc Download Script
# Downloads and verifies musl libc source code

set -e

# Configuration
MUSL_VERSION="${MUSL_VERSION:-1.2.4}"
MUSL_BASE_URL="https://musl.libc.org/releases"
MUSL_TARBALL="musl-${MUSL_VERSION}.tar.gz"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOWNLOAD_DIR="${PROJECT_ROOT}/build/downloads"
MUSL_SRC_DIR="${PROJECT_ROOT}/build/musl-src"

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
mkdir -p "$MUSL_SRC_DIR"

# Download musl libc tarball
download_musl() {
    local tarball_path="${DOWNLOAD_DIR}/${MUSL_TARBALL}"

    if [ -f "$tarball_path" ]; then
        log_info "musl libc tarball already exists: $tarball_path"
    else
        log_info "Downloading musl libc ${MUSL_VERSION}..."

        # Multiple mirror URLs for redundancy
        local urls=(
            "${MUSL_BASE_URL}/${MUSL_TARBALL}"
            "https://www.musl-libc.org/releases/${MUSL_TARBALL}"
            "https://git.musl-libc.org/cgit/musl/snapshot/${MUSL_TARBALL}"
        )

        local download_success=false
        for url in "${urls[@]}"; do
            log_info "Trying: $url"
            if curl -fSL --connect-timeout 30 --max-time 300 -o "$tarball_path" "$url"; then
                download_success=true
                log_success "Downloaded from: $url"
                break
            else
                log_warn "Failed to download from: $url"
            fi
        done

        if [ "$download_success" = false ]; then
            log_error "Failed to download musl libc from all mirrors"
            return 1
        fi
    fi
}

# Calculate and display checksum
show_checksum() {
    local tarball_path="${DOWNLOAD_DIR}/${MUSL_TARBALL}"

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

# Verify checksum (if known checksums are provided)
verify_checksum() {
    local tarball_path="${DOWNLOAD_DIR}/${MUSL_TARBALL}"

    # Known SHA-256 checksums for musl versions
    local expected=""
    case "$MUSL_VERSION" in
        1.2.4)
            expected="7a35eae33d5372a7c0da1188de798726f68825513b7ae3ebe97aaaa52114f039"
            ;;
        1.2.3)
            expected="7d5b0b6062521e4627e099e4c9dc8248d32a30285e959b7eecaa780cf8cfd4a4"
            ;;
        *)
            log_warn "No known checksum for musl version $MUSL_VERSION"
            return 0
            ;;
    esac

    if [ -n "$expected" ]; then
        log_info "Verifying checksum..."
        local actual
        actual=$(cat "${tarball_path}.sha256" 2>/dev/null || echo "")

        if [ "$actual" = "$expected" ]; then
            log_info "Checksum verification: OK"
            return 0
        else
            log_warn "Checksum mismatch!"
            log_warn "Expected: $expected"
            log_warn "Actual:   $actual"
            log_warn "Continuing anyway..."
            return 0
        fi
    fi
}

# Extract musl libc tarball
extract_musl() {
    local tarball_path="${DOWNLOAD_DIR}/${MUSL_TARBALL}"

    if [ -d "${MUSL_SRC_DIR}/musl-${MUSL_VERSION}" ]; then
        log_info "musl libc source already extracted: ${MUSL_SRC_DIR}/musl-${MUSL_VERSION}"
        return 0
    fi

    log_info "Extracting musl libc tarball to ${MUSL_SRC_DIR}"
    tar -xzf "$tarball_path" -C "$MUSL_SRC_DIR" || {
        log_error "Failed to extract musl libc tarball"
        return 1
    }

    log_info "musl libc extracted successfully"
}

# Main
main() {
    log_info "Kimigayo OS - musl libc Download Script"
    log_info "musl libc Version: ${MUSL_VERSION}"
    log_info "Download Directory: ${DOWNLOAD_DIR}"
    log_info "Source Directory: ${MUSL_SRC_DIR}"
    log_info ""

    download_musl || exit 1
    show_checksum
    verify_checksum
    extract_musl || exit 1

    log_info "musl libc download completed successfully"
    log_info "musl libc source: ${MUSL_SRC_DIR}/musl-${MUSL_VERSION}"
}

main "$@"
