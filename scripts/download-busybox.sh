#!/usr/bin/env bash
#
# BusyBox Download Script for Kimigayo OS
# Downloads BusyBox source code with verification
#

set -euo pipefail

# Save project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# バージョンは versions.mk（単一の真実の源）から読み込む
# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"

# Configuration
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

# GitHub の自動生成アーカイブから取った場合は公式 tarball とバイト列が
# 違うためチェックサムを飛ばす。既存 tarball を再利用する経路でも参照されるので、
# if の外で必ず初期化する（未初期化のままだと set -u で落ちていた）。
skip_checksum=false

# GitHub のタグはドットをアンダースコアにした形式（1.38.0 -> 1_38_0）。
# 展開後のディレクトリ名のリネームでも参照するので、download 分岐の外で定義する
# （以前は分岐の中だけで定義しており、既存 tarball を再利用すると
#  set -u で "github_tag_version: unbound variable" になって落ちていた）。
github_tag_version="${BUSYBOX_VERSION//./_}"

# Check if already downloaded
if [ -f "$tarball_path" ]; then
    log_warning "BusyBox tarball already exists: $tarball_path"
    log_info "Verifying existing tarball..."
else
    # Download BusyBox with mirror fallback
    log_info "Downloading BusyBox ${BUSYBOX_VERSION}..."

    # 公式 tarball を先に試す。
    # GitHub ミラーの自動生成アーカイブは公式と別のバイト列になるため
    # チェックサム検証を飛ばすことになる（skip_checksum=true）。
    # 加えて mirror/busybox には新しいタグが無いことがあり、
    # 実際に 1_38_0 は 404 だった（2026-10-09 実測）。
    # 検証できる経路を第一候補にし、GitHub ミラーは最後の保険に回す。
    urls=(
        "${BUSYBOX_BASE_URL}/${tarball_filename}"
        "https://www.busybox.net/downloads/${tarball_filename}"
        "${BUSYBOX_GITHUB_MIRROR}/archive/refs/tags/${github_tag_version}.tar.gz"
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
    "1.38.0")
        expected_sha256="34f9ea6ff8636f2c9241153b9114eefa9e65674a45318ae1ef95bb5f31c53bb2"
        ;;
    "1.37.0")
        expected_sha256="3311dff32e746499f4df0d5df04d7eb396382d7e108bb9250e7b519b837043a4"
        ;;
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

# GitHub archives extract to busybox-1_36_1 format, need to rename
github_extract_dir="${BUILD_DIR}/busybox-${github_tag_version}"
if [ -d "$github_extract_dir" ] && [ "$github_extract_dir" != "$extract_dir" ]; then
    log_info "Renaming GitHub archive directory: $github_extract_dir -> $extract_dir"
    mv "$github_extract_dir" "$extract_dir"
fi

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
