#!/bin/bash
# Display version information for Kimigayo OS

set -e

# Colors
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get version
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VERSION=$("$SCRIPT_DIR/get-version.sh")

# 構成要素のバージョンは versions.mk（単一の真実の源）から読み込む
# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"

# Get git information
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    GIT_COMMIT=$(git rev-parse --short HEAD)
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
else
    GIT_COMMIT="unknown"
    GIT_BRANCH="unknown"
fi

# Display version information
echo -e "${BOLD}Kimigayo OS Version Information${NC}"
echo -e "================================"
echo -e "${GREEN}Version:${NC}       $VERSION"
echo -e "${BLUE}Git Commit:${NC}    $GIT_COMMIT"
echo -e "${BLUE}Git Branch:${NC}    $GIT_BRANCH"
echo -e "================================"
echo -e "${BOLD}Components${NC} (versions.mk)"
echo -e "================================"
echo -e "${GREEN}Linux kernel:${NC}  $KERNEL_VERSION"
echo -e "${GREEN}musl libc:${NC}     $MUSL_VERSION"
echo -e "${GREEN}BusyBox:${NC}       $BUSYBOX_VERSION"
echo -e "${GREEN}OpenRC:${NC}        $OPENRC_VERSION"
echo -e "${GREEN}Alpine (build):${NC} $ALPINE_VERSION"
echo -e "================================"
