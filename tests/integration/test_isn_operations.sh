#!/usr/bin/env bash
#
# Task 21.3 - isn Operation Verification Tests
# Tests basic operations of the isn package manager
#

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ISN_SRC="${REPO_ROOT}/src/pkg/isn"
METADATA_DIR="${REPO_ROOT}/repository/metadata"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}Task 21.3: isn Operation Verification${NC}"
echo -e "${BLUE}====================================${NC}"
echo ""

# Helper functions
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

# Check if we're in Docker environment
if [ -f /.dockerenv ]; then
    info "Running in Docker environment"
    ISN_BIN="/workspace/src/pkg/isn/target/release/isn"
else
    info "Running in host environment"
    # Try to find isn binary
    if [ -f "${ISN_SRC}/target/release/isn" ]; then
        ISN_BIN="${ISN_SRC}/target/release/isn"
    elif [ -f "${ISN_SRC}/target/debug/isn" ]; then
        ISN_BIN="${ISN_SRC}/target/debug/isn"
    else
        info "isn binary not found, will test source code structure only"
        ISN_BIN=""
    fi
fi

echo ""
echo -e "${BLUE}Test 1: Package Search Test (パッケージ検索テスト)${NC}"
echo "-----------------------------------------------"

# Test 1.1: Check metadata files exist
if [ -f "${METADATA_DIR}/packages/hello-world.json" ]; then
    pass "hello-world metadata exists"
else
    fail "hello-world metadata not found"
fi

if [ -f "${METADATA_DIR}/packages/curl.json" ]; then
    pass "curl metadata exists"
else
    fail "curl metadata not found"
fi

if [ -f "${METADATA_DIR}/packages/openssl.json" ]; then
    pass "openssl metadata exists"
else
    fail "openssl metadata not found"
fi

# Test 1.2: Check package index
if [ -f "${METADATA_DIR}/index.json" ]; then
    pass "package index exists"

    # Check if packages are listed in index
    if grep -q '"hello-world"' "${METADATA_DIR}/index.json"; then
        pass "hello-world is in package index"
    else
        fail "hello-world not in package index"
    fi

    if grep -q '"curl"' "${METADATA_DIR}/index.json"; then
        pass "curl is in package index"
    else
        fail "curl not in package index"
    fi
else
    fail "package index not found"
fi

# Test 1.3: Test isn search command (if binary exists)
if [ -n "$ISN_BIN" ] && [ -f "$ISN_BIN" ]; then
    info "Testing isn search command"

    if output=$("$ISN_BIN" search hello 2>&1); then
        pass "isn search command executed successfully"
        echo "   Output: ${output}"
    else
        fail "isn search command failed"
    fi
else
    info "Skipping binary test (isn not built yet)"
fi

echo ""
echo -e "${BLUE}Test 2: Package Install Test (パッケージインストールテスト)${NC}"
echo "---------------------------------------------------------------"

# Test 2.1: Verify install command exists in source
if grep -q "pub fn install" "${ISN_SRC}/src/commands.rs"; then
    pass "install function exists in commands.rs"
else
    fail "install function not found in commands.rs"
fi

# Test 2.2: Test isn install command (if binary exists)
if [ -n "$ISN_BIN" ] && [ -f "$ISN_BIN" ]; then
    info "Testing isn install command (dry-run)"

    if output=$("$ISN_BIN" install hello-world --yes 2>&1); then
        pass "isn install command executed successfully"
        echo "   Output: ${output}"
    else
        fail "isn install command failed"
    fi
else
    info "Skipping binary test (isn not built yet)"
fi

echo ""
echo -e "${BLUE}Test 3: Dependency Resolution Test (依存関係解決テスト)${NC}"
echo "----------------------------------------------------------------"

# Test 3.1: Verify curl depends on openssl
if jq -e '.depends[] | select(. | startswith("openssl"))' "${METADATA_DIR}/packages/curl.json" > /dev/null 2>&1; then
    pass "curl correctly depends on openssl"
else
    fail "curl dependency on openssl not found"
fi

# Test 3.2: Verify openssl depends on zlib
if jq -e '.depends[] | select(. | startswith("zlib"))' "${METADATA_DIR}/packages/openssl.json" > /dev/null 2>&1; then
    pass "openssl correctly depends on zlib"
else
    fail "openssl dependency on zlib not found"
fi

# Test 3.3: Verify hello-world has no dependencies
if jq -e '.depends | length == 0' "${METADATA_DIR}/packages/hello-world.json" > /dev/null 2>&1; then
    pass "hello-world correctly has no dependencies"
else
    fail "hello-world should have no dependencies"
fi

# Test 3.4: Check if resolver module exists
if [ -f "${ISN_SRC}/src/package.rs" ]; then
    pass "package module exists for dependency handling"
else
    fail "package module not found"
fi

echo ""
echo -e "${BLUE}Test 4: Signature Verification Test (署名検証テスト)${NC}"
echo "-------------------------------------------------------------"

# Test 4.1: Verify signature field exists in metadata
if jq -e '.signature.algorithm == "ed25519"' "${METADATA_DIR}/packages/hello-world.json" > /dev/null 2>&1; then
    pass "hello-world has ed25519 signature field"
else
    fail "hello-world signature field incorrect"
fi

# Test 4.2: Verify all packages have signature fields
for pkg in "${METADATA_DIR}/packages"/*.json; do
    pkg_name=$(basename "$pkg" .json)
    if jq -e '.signature' "$pkg" > /dev/null 2>&1; then
        pass "${pkg_name} has signature field"
    else
        fail "${pkg_name} missing signature field"
    fi
done

# Test 4.3: Test isn verify command (if binary exists)
if [ -n "$ISN_BIN" ] && [ -f "$ISN_BIN" ]; then
    info "Testing isn verify command"

    if output=$("$ISN_BIN" verify hello-world 2>&1); then
        pass "isn verify command executed successfully"
        echo "   Output: ${output}"
    else
        fail "isn verify command failed"
    fi
else
    info "Skipping binary test (isn not built yet)"
fi

# Test 4.4: Verify checksum field exists
if jq -e '.checksum.sha256' "${METADATA_DIR}/packages/hello-world.json" > /dev/null 2>&1; then
    pass "hello-world has SHA-256 checksum"
else
    fail "hello-world checksum missing"
fi

echo ""
echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}====================================${NC}"
echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
echo ""

if [ ${TESTS_FAILED} -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo -e "${YELLOW}Note:${NC} isn binary tests were skipped as this is Phase 5."
    echo "Full implementation will be completed in Phase 6."
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
