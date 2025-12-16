#!/usr/bin/env bash
#
# OpenRC Download Script for Kimigayo OS
# Downloads OpenRC init system source code with verification
#

set -euo pipefail

# Configuration
OPENRC_VERSION="${OPENRC_VERSION:-0.52.1}"
OPENRC_BASE_URL="https://github.com/OpenRC/openrc/releases/download"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-./downloads}"
BUILD_DIR="${BUILD_DIR:-./build}"

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

# Create directories
mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$BUILD_DIR"

# File paths
tarball_filename="openrc-${OPENRC_VERSION}.tar.gz"
tarball_path="${DOWNLOAD_DIR}/${tarball_filename}"
extract_dir="${BUILD_DIR}/openrc-${OPENRC_VERSION}"

log_info "OpenRC Download Script"
log_info "Version: ${OPENRC_VERSION}"
log_info "Download directory: ${DOWNLOAD_DIR}"
log_info "Extract directory: ${extract_dir}"

# Check if already downloaded
if [ -f "$tarball_path" ]; then
    log_warning "OpenRC tarball already exists: $tarball_path"
    log_info "Verifying existing tarball..."
else
    # Download OpenRC
    log_info "Downloading OpenRC ${OPENRC_VERSION}..."
    url="${OPENRC_BASE_URL}/${OPENRC_VERSION}/${tarball_filename}"

    if ! curl -fSL -o "$tarball_path" "$url"; then
        log_error "Failed to download OpenRC from $url"
        exit 1
    fi

    log_success "Downloaded OpenRC tarball"
fi

# Note: OpenRC releases don't have published SHA-256 checksums on their GitHub releases
# We'll verify the download by checking if extraction succeeds
log_warning "OpenRC releases don't provide SHA-256 checksums"
log_info "Verification will be done via successful extraction"

# Extract if needed
if [ -d "$extract_dir" ]; then
    log_warning "Extract directory already exists: $extract_dir"
    log_info "Removing existing directory..."
    rm -rf "$extract_dir"
fi

log_info "Extracting OpenRC..."
if ! tar -xzf "$tarball_path" -C "$BUILD_DIR"; then
    log_error "Extraction failed"
    exit 1
fi

if [ ! -d "$extract_dir" ]; then
    log_error "Extraction failed: directory not found: $extract_dir"
    exit 1
fi

log_success "OpenRC extracted to $extract_dir"

# Display source info
log_info "OpenRC source information:"
log_info "  Version: ${OPENRC_VERSION}"
log_info "  Source directory: ${extract_dir}"
log_info "  Files count: $(find "$extract_dir" -type f | wc -l)"

# Check for required files
required_files=("meson.build" "src/rc/rc.c" "sh/openrc-run.sh.in")
all_found=true

for file in "${required_files[@]}"; do
    if [ ! -f "${extract_dir}/${file}" ]; then
        log_warning "Expected file not found: $file"
        all_found=false
    fi
done

if [ "$all_found" = true ]; then
    log_success "All expected source files found"
else
    log_warning "Some expected files are missing, but continuing..."
fi

log_success "OpenRC download completed successfully"
