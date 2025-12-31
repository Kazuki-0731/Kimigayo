#!/usr/bin/env bash
#
# OpenRC Integration Test Script for Kimigayo OS
# Tests OpenRC installation and service definitions
#

set -euo pipefail

# Configuration
BUILD_DIR="${BUILD_DIR:-./build}"
ARCH="${ARCH:-x86_64}"

OPENRC_INSTALL_DIR="${BUILD_DIR}/openrc-install-${ARCH}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
}

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $*"
}

# Test result tracking
test_pass() {
    ((TESTS_PASSED++)) || true
    ((TESTS_RUN++)) || true
    log_success "$1"
}

test_fail() {
    ((TESTS_FAILED++)) || true
    ((TESTS_RUN++)) || true
    log_error "$1"
}

# Header
echo "========================================"
echo "OpenRC Integration Tests"
echo "========================================"
log_info "Architecture: ${ARCH}"
log_info "OpenRC directory: ${OPENRC_INSTALL_DIR}"
echo ""

# Test 1: Verify OpenRC installation directory exists
log_test "Test 1: Verify OpenRC installation directory"
if [ -d "$OPENRC_INSTALL_DIR" ]; then
    test_pass "OpenRC installation directory found"
else
    test_fail "OpenRC installation directory not found: $OPENRC_INSTALL_DIR"
    echo ""
    echo "Test suite cannot continue without OpenRC."
    echo "Please run: make init ARCH=${ARCH}"
    exit 1
fi

# Test 2: Verify essential OpenRC binaries
log_test "Test 2: Verify essential OpenRC binaries"
essential_binaries=(
    "sbin/openrc"
    "sbin/rc"
    "sbin/rc-status"
    "sbin/rc-service"
    "sbin/rc-update"
    "sbin/openrc-init"
    "sbin/openrc-run"
    "sbin/openrc-shutdown"
)

all_found=true
for binary in "${essential_binaries[@]}"; do
    if [ -f "${OPENRC_INSTALL_DIR}/${binary}" ] || [ -L "${OPENRC_INSTALL_DIR}/${binary}" ]; then
        log_info "  ✓ ${binary}"
    else
        log_error "  ✗ ${binary} not found"
        all_found=false
    fi
done

if [ "$all_found" = true ]; then
    test_pass "All essential OpenRC binaries found"
else
    test_fail "Some essential OpenRC binaries are missing"
fi

# Test 3: Verify OpenRC library files
log_test "Test 3: Verify OpenRC library files"
lib_dir="${OPENRC_INSTALL_DIR}/lib/rc"
if [ -d "$lib_dir" ]; then
    lib_count=$(find "$lib_dir" -type f 2>/dev/null | wc -l)
    log_info "Found ${lib_count} library files"
    if [ "$lib_count" -gt 0 ]; then
        test_pass "OpenRC library files found"
    else
        test_fail "No library files found in $lib_dir"
    fi
else
    test_fail "OpenRC library directory not found: $lib_dir"
fi

# Test 4: Verify runlevel directories
log_test "Test 4: Verify runlevel directories"
runlevels=("sysinit" "boot" "default" "shutdown")
runlevel_dir="${OPENRC_INSTALL_DIR}/etc/runlevels"

all_found=true
for level in "${runlevels[@]}"; do
    if [ -d "${runlevel_dir}/${level}" ]; then
        log_info "  ✓ Runlevel: ${level}"
    else
        log_error "  ✗ Runlevel directory missing: ${level}"
        all_found=false
    fi
done

if [ "$all_found" = true ]; then
    test_pass "All runlevel directories found"
else
    test_fail "Some runlevel directories are missing"
fi

# Test 5: Verify custom init scripts from src/openrc/init.d
log_test "Test 5: Verify custom init scripts availability"
custom_scripts=(
    "bootmisc"
    "hostname"
    "syslog"
    "klogd"
    "networking"
    "crond"
)

script_dir="src/openrc/init.d"
all_found=true

for script in "${custom_scripts[@]}"; do
    if [ -f "${script_dir}/${script}" ]; then
        log_info "  ✓ ${script}"
        # Check if executable
        if [ -x "${script_dir}/${script}" ]; then
            log_info "    (executable)"
        else
            log_error "    (not executable)"
            all_found=false
        fi
    else
        log_error "  ✗ ${script} not found"
        all_found=false
    fi
done

if [ "$all_found" = true ]; then
    test_pass "All custom init scripts found and executable"
else
    test_fail "Some custom init scripts are missing or not executable"
fi

# Test 6: Verify custom configuration files
log_test "Test 6: Verify custom configuration files"
custom_configs=(
    "syslog"
    "klogd"
    "crond"
    "hostname"
)

config_dir="src/openrc/conf.d"
all_found=true

for config in "${custom_configs[@]}"; do
    if [ -f "${config_dir}/${config}" ]; then
        log_info "  ✓ ${config}"
    else
        log_error "  ✗ ${config} not found"
        all_found=false
    fi
done

if [ "$all_found" = true ]; then
    test_pass "All custom configuration files found"
else
    test_fail "Some custom configuration files are missing"
fi

# Test 7: Verify runlevel setup script
log_test "Test 7: Verify runlevel setup script"
setup_script="src/openrc/runlevels/setup-runlevels.sh"

if [ -f "$setup_script" ]; then
    if [ -x "$setup_script" ]; then
        test_pass "Runlevel setup script found and executable"
    else
        test_fail "Runlevel setup script not executable"
    fi
else
    test_fail "Runlevel setup script not found"
fi

# Test 8: Check init script syntax (basic validation)
log_test "Test 8: Validate init script syntax"
validation_passed=true

for script in "${custom_scripts[@]}"; do
    script_path="${script_dir}/${script}"
    if [ -f "$script_path" ]; then
        # Check for shebang
        if head -n 1 "$script_path" | grep -q "^#!/sbin/openrc-run"; then
            log_info "  ✓ ${script}: Valid shebang"
        else
            log_error "  ✗ ${script}: Invalid or missing shebang"
            validation_passed=false
        fi

        # Check for depend() function
        if grep -q "^depend()" "$script_path"; then
            log_info "  ✓ ${script}: Has depend() function"
        else
            log_info "  ⚠ ${script}: No depend() function (optional)"
        fi
    fi
done

if [ "$validation_passed" = true ]; then
    test_pass "Init script syntax validation passed"
else
    test_fail "Some init scripts have syntax issues"
fi

# Test 9: Check service dependencies in init scripts
log_test "Test 9: Check service dependency declarations"
dependency_check_passed=true

# Expected dependencies
declare -A expected_deps=(
    ["syslog"]="localmount"
    ["klogd"]="syslog"
    ["networking"]="localmount"
    ["crond"]="localmount"
)

for script in "${!expected_deps[@]}"; do
    script_path="${script_dir}/${script}"
    expected="${expected_deps[$script]}"

    if [ -f "$script_path" ]; then
        if grep -A 5 "^depend()" "$script_path" | grep -q "$expected"; then
            log_info "  ✓ ${script}: Has expected dependency '${expected}'"
        else
            log_error "  ✗ ${script}: Missing expected dependency '${expected}'"
            dependency_check_passed=false
        fi
    fi
done

if [ "$dependency_check_passed" = true ]; then
    test_pass "Service dependencies correctly declared"
else
    test_fail "Some service dependencies are missing"
fi

# Test 10: Verify OpenRC configuration files
log_test "Test 10: Verify OpenRC core configuration"
openrc_conf="${OPENRC_INSTALL_DIR}/etc/rc.conf"

if [ -f "$openrc_conf" ]; then
    test_pass "OpenRC configuration file found: rc.conf"
else
    log_info "OpenRC configuration file not found (may be optional)"
    ((TESTS_RUN++)) || true
fi

# Test 11: Check init.d directory structure in installation
log_test "Test 11: Check OpenRC init.d directory in installation"
init_dir="${OPENRC_INSTALL_DIR}/etc/init.d"

if [ -d "$init_dir" ]; then
    init_count=$(find "$init_dir" -type f -o -type l 2>/dev/null | wc -l)
    log_info "Found ${init_count} init scripts in installation"
    if [ "$init_count" -gt 0 ]; then
        test_pass "OpenRC init.d directory populated"
    else
        log_info "No init scripts in installation (custom scripts not yet installed)"
        ((TESTS_RUN++)) || true
    fi
else
    log_info "Init.d directory not found (will be created during rootfs build)"
    ((TESTS_RUN++)) || true
fi

# Test 12: Verify OpenRC documentation
log_test "Test 12: Verify OpenRC documentation"
readme="src/openrc/README.md"

if [ -f "$readme" ]; then
    word_count=$(wc -w < "$readme")
    log_info "README contains ${word_count} words"
    if [ "$word_count" -gt 100 ]; then
        test_pass "OpenRC documentation found and substantial"
    else
        test_fail "OpenRC documentation too short"
    fi
else
    test_fail "OpenRC README.md not found"
fi

# Summary
echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
log_info "Tests run:    ${TESTS_RUN}"
log_info "Tests passed: ${TESTS_PASSED}"
log_info "Tests failed: ${TESTS_FAILED}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    log_success "All tests passed!"
    echo ""
    log_info "OpenRC integration ready for deployment"
    log_info "Next steps:"
    log_info "  1. Build rootfs with OpenRC integration"
    log_info "  2. Test boot sequence in QEMU"
    log_info "  3. Verify service startup order"
    exit 0
else
    log_error "Some tests failed"
    exit 1
fi
