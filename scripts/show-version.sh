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
VERSION=$("$SCRIPT_DIR/get-version.sh")

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
