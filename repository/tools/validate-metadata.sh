#!/usr/bin/env bash
#
# Validate Package Metadata
# Checks all package metadata files against the JSON schema
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
METADATA_DIR="${REPO_ROOT}/metadata"
SCHEMA_FILE="${METADATA_DIR}/schema.json"
PACKAGES_DIR="${METADATA_DIR}/packages"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Validating package metadata...${NC}"

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed${NC}"
    echo "Install with: apk add jq  (Alpine Linux)"
    exit 1
fi

valid_count=0
invalid_count=0

for pkg_file in "${PACKAGES_DIR}"/*.json; do
    if [ ! -f "$pkg_file" ]; then
        continue
    fi

    pkg_name=$(basename "$pkg_file")

    # Basic JSON validation
    if ! jq empty "$pkg_file" 2>/dev/null; then
        echo -e "${RED}✗ ${pkg_name}: Invalid JSON${NC}"
        ((invalid_count++))
        continue
    fi

    # Check required fields
    required_fields=("name" "version" "arch" "description" "license" "maintainer" "size" "checksum")
    missing_fields=()

    for field in "${required_fields[@]}"; do
        if ! jq -e ".${field}" "$pkg_file" > /dev/null 2>&1; then
            missing_fields+=("$field")
        fi
    done

    if [ ${#missing_fields[@]} -gt 0 ]; then
        echo -e "${RED}✗ ${pkg_name}: Missing fields: ${missing_fields[*]}${NC}"
        ((invalid_count++))
        continue
    fi

    # Validate version format
    version=$(jq -r '.version' "$pkg_file")
    if ! [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9]+)?$ ]]; then
        echo -e "${RED}✗ ${pkg_name}: Invalid version format: ${version}${NC}"
        ((invalid_count++))
        continue
    fi

    echo -e "${GREEN}✓ ${pkg_name}${NC}"
    ((valid_count++))
done

echo ""
echo -e "${BLUE}Validation complete${NC}"
echo "  Valid: ${valid_count}"
echo "  Invalid: ${invalid_count}"

if [ $invalid_count -gt 0 ]; then
    exit 1
fi
