#!/usr/bin/env bash
#
# BusyBox Download Script for Kimigayo OS
# Downloads BusyBox source code with verification
#

set -euo pipefail

# Save project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Configuration
BUSYBOX_VERSION="${BUSYBOX_VERSION:-1.36.1}"
BUSYBOX_BASE_URL="https://busybox.net/downloads"
BUSYBOX_GITHUB_MIRROR="https://github.com/mirror/busybox"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-${PROJECT_ROOT}/build/downloads}"
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"

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

# Create directories
mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$BUILD_DIR"

# File paths
tarball_filename="busybox-${BUSYBOX_VERSION}.tar.bz2"
tarball_path="${DOWNLOAD_DIR}/${tarball_filename}"
extract_dir="${BUILD_DIR}/busybox-${BUSYBOX_VERSION}"

log_info "BusyBox Download Script"
log_info "Version: ${BUSYBOX_VERSION}"
log_info "Download directory: ${DOWNLOAD_DIR}"
log_info "Extract directory: ${extract_dir}"

# Check if already downloaded
if [ -f "$tarball_path" ]; then
    log_warning "BusyBox tarball already exists: $tarball_path"
    log_info "Verifying existing tarball..."
else
    # Download BusyBox with mirror fallback
    log_info "Downloading BusyBox ${BUSYBOX_VERSION}..."

    # Convert version format (1.36.1 -> 1_36_1) for GitHub tags
    github_tag_version="${BUSYBOX_VERSION//./_}"

    # Multiple mirror URLs for redundancy (GitHub mirror first as it's faster and more reliable)
    urls=(
        "${BUSYBOX_GITHUB_MIRROR}/archive/refs/tags/${github_tag_version}.tar.gz"
        "${BUSYBOX_BASE_URL}/${tarball_filename}"
        "https://www.busybox.net/downloads/${tarball_filename}"
    )

    download_success=false
    skip_checksum=false

    for url in "${urls[@]}"; do
        log_info "Trying: $url"

        # Determine temporary download path based on URL
        if [[ "$url" == *"github.com"* ]]; then
            temp_download_path="${DOWNLOAD_DIR}/busybox-${github_tag_version}.tar.gz"
            is_github=true
        else
            temp_download_path="$tarball_path"
            is_github=false
        fi

        if curl -fSL --connect-timeout 30 --max-time 300 -o "$temp_download_path" "$url"; then
            # If downloaded from GitHub, need to convert tar.gz to tar.bz2
            if [ "$is_github" = true ]; then
                log_info "Converting GitHub archive to standard format..."
                # Extract from tar.gz and recompress to tar.bz2
                gunzip -c "$temp_download_path" | bzip2 -c > "$tarball_path"
                rm -f "$temp_download_path"
                # GitHub archives have different checksums due to metadata differences
                # Skip checksum verification for GitHub downloads
                skip_checksum=true
                log_info "Note: Checksum verification will be skipped for GitHub mirror"
            fi

            download_success=true
            log_success "Downloaded from: $url"
            break
        else
            log_warning "Failed to download from: $url"
            rm -f "$temp_download_path"
        fi
    done

    if [ "$download_success" = false ]; then
        log_error "Failed to download BusyBox from all mirrors"
        log_error "Tried ${#urls[@]} different URLs"
        exit 1
    fi
fi

# Verify checksum
log_info "Verifying SHA-256 checksum..."

# Known SHA-256 checksums for BusyBox versions
# Source: https://busybox.net/downloads/
case "$BUSYBOX_VERSION" in
    "1.36.1")
        expected_sha256="b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314"
        ;;
    "1.36.0")
        expected_sha256="542750c8af7cb2630e201780b4f99f3dcce0c9e53672c37bf5f88e02c47c126c"
        ;;
    *)
        log_warning "No known checksum for BusyBox ${BUSYBOX_VERSION}"
        log_warning "Skipping checksum verification"
        expected_sha256=""
        ;;
esac

if [ "$skip_checksum" = true ]; then
    log_warning "Skipping checksum verification (downloaded from GitHub mirror)"
    log_info "GitHub archives have different metadata than official tarballs"
elif [ -n "$expected_sha256" ]; then
    actual_sha256=$(sha256sum "$tarball_path" | awk '{print $1}')

    if [ "$actual_sha256" != "$expected_sha256" ]; then
        log_error "SHA-256 checksum mismatch!"
        log_error "Expected: $expected_sha256"
        log_error "Got:      $actual_sha256"
        exit 1
    fi

    log_success "SHA-256 checksum verified"
else
    log_warning "Proceeding without checksum verification"
fi

# Extract if needed
if [ -d "$extract_dir" ]; then
    log_warning "Extract directory already exists: $extract_dir"
    log_info "Removing existing directory..."
    rm -rf "$extract_dir"
fi

log_info "Extracting BusyBox..."
tar -xjf "$tarball_path" -C "$BUILD_DIR"

if [ ! -d "$extract_dir" ]; then
    log_error "Extraction failed: directory not found: $extract_dir"
    exit 1
fi

log_success "BusyBox extracted to $extract_dir"

# Display source info
log_info "BusyBox source information:"
log_info "  Version: ${BUSYBOX_VERSION}"
log_info "  Source directory: ${extract_dir}"
log_info "  Files count: $(find "$extract_dir" -type f | wc -l)"

log_success "BusyBox download completed successfully"
