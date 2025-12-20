#!/usr/bin/env bash
#
# Update Package Repository Index
# Scans metadata/ directory and updates index.json
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
METADATA_DIR="${REPO_ROOT}/metadata"
INDEX_FILE="${METADATA_DIR}/index.json"
PACKAGES_DIR="${METADATA_DIR}/packages"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Updating package repository index...${NC}"

# Generate package list
packages=()
for pkg_file in "${PACKAGES_DIR}"/*.json; do
    if [ -f "$pkg_file" ]; then
        pkg_name=$(basename "$pkg_file" .json)
        packages+=("\"$pkg_name\"")
    fi
done

# Build packages array
packages_json=$(printf '%s\n' "${packages[@]}" | paste -sd ',' -)

# Update index.json
cat > "${INDEX_FILE}" << EOF
{
  "version": "1.0",
  "generated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "repository": {
    "name": "Kimigayo OS Official Repository",
    "url": "https://packages.kimigayo.org",
    "description": "Official package repository for Kimigayo OS"
  },
  "architectures": [
    "x86_64",
    "aarch64"
  ],
  "categories": [
    "base",
    "devel",
    "network",
    "security",
    "system",
    "utils"
  ],
  "packages": [
    ${packages_json}
  ]
}
EOF

echo -e "${GREEN}✓ Index updated successfully${NC}"
echo "  Packages: ${#packages[@]}"
echo "  Index file: ${INDEX_FILE}"
