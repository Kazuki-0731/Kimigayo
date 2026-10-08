#!/usr/bin/env bash
#
# OpenRC Download Script for Kimigayo OS
# Downloads OpenRC init system source code with verification
#

set -euo pipefail

# Save project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# バージョンは versions.mk（単一の真実の源）から読み込む
# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"

# Configuration
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
    # Download OpenRC with mirror fallback
    log_info "Downloading OpenRC ${OPENRC_VERSION}..."

    # OpenRC は GitHub の自動生成アーカイブでしか配布されていない。
    # releases/download/... は全バージョンで 404 を返す（2026-10-09 実測）ため、
    # 自動生成アーカイブを第一候補にする。
    urls=(
        "https://github.com/OpenRC/openrc/archive/refs/tags/${OPENRC_VERSION}.tar.gz"
        "https://codeload.github.com/OpenRC/openrc/tar.gz/refs/tags/${OPENRC_VERSION}"
    )

    download_success=false
    for url in "${urls[@]}"; do
        log_info "Trying: $url"
        if curl -fSL --connect-timeout 30 --max-time 300 -o "$tarball_path" "$url"; then
            download_success=true
            log_success "Downloaded from: $url"
            break
        else
            log_warning "Failed to download from: $url"
        fi
    done

    if [ "$download_success" = false ]; then
        log_error "Failed to download OpenRC from all mirrors"
        log_error "Tried ${#urls[@]} different URLs"
        exit 1
    fi
fi

# Verify SHA-256 checksum
#
# OpenRC は公式の SHA-256 一覧を公開していない。ここに書いてある値は
# Alpine aports の main/openrc/APKBUILD の sha512sums と突合して確認したもの。
# tarball は GitHub の自動生成アーカイブなので、理論上は再生成でバイト列が
# 変わりうる。合わなくなったら改竄を疑う前に aports 側と突合する。
log_info "Verifying SHA-256 checksum..."

expected_sha256=""
case "$OPENRC_VERSION" in
    "0.63.2")
        expected_sha256="a8a890338952202b5893c53b639b098850279a7149e2fc4d42515283facd00e8"
        ;;
    *)
        log_warning "No known checksum for OpenRC ${OPENRC_VERSION}"
        log_warning "Add it to this script after cross-checking against Alpine aports"
        ;;
esac

if [ -n "$expected_sha256" ]; then
    if command -v sha256sum > /dev/null 2>&1; then
        actual_sha256="$(sha256sum "$tarball_path" | awk '{print $1}')"
    else
        actual_sha256="$(shasum -a 256 "$tarball_path" | awk '{print $1}')"
    fi

    if [ "$actual_sha256" != "$expected_sha256" ]; then
        log_error "SHA-256 checksum mismatch!"
        log_error "Expected: $expected_sha256"
        log_error "Got:      $actual_sha256"
        log_error "Refusing to use this tarball. Delete it and retry:"
        log_error "  rm -f ${tarball_path}"
        exit 1
    fi

    log_success "Checksum verification: OK"
fi

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
# 0.63.2 でソース構成が変わり src/rc/rc.c は src/openrc/rc.c に移動している
required_files=("meson.build" "src/openrc/rc.c" "sh/openrc-run.sh.in")
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
