#!/bin/bash
# Kimigayo OS - Kernel Security Verification Script
# Verifies security hardening features in kernel configuration

set -e

# Configuration
KERNEL_VERSION="${KERNEL_VERSION:-6.6.11}"
ARCH="${ARCH:-x86_64}"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
KERNEL_OUTPUT_DIR="${PROJECT_ROOT}/build/kernel/output"
KERNEL_CONFIG="${KERNEL_OUTPUT_DIR}/config-${KERNEL_VERSION}-${ARCH}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
SECURITY_ENABLED=0
SECURITY_DISABLED=0
SECURITY_WARNINGS=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_check() {
    echo -e "${GREEN}[CHECK]${NC} $*"
}

log_enabled() {
    echo -e "${GREEN}[✓]${NC} $*"
    SECURITY_ENABLED=$((SECURITY_ENABLED + 1))
}

log_disabled() {
    echo -e "${RED}[✗]${NC} $*"
    SECURITY_DISABLED=$((SECURITY_DISABLED + 1))
}

log_optional() {
    echo -e "${YELLOW}[○]${NC} $*"
    SECURITY_WARNINGS=$((SECURITY_WARNINGS + 1))
}

# Check if config exists
check_config_exists() {
    if [ ! -f "$KERNEL_CONFIG" ]; then
        log_error "Kernel config not found: $KERNEL_CONFIG"
        log_error "Please build the kernel first with: make kernel"
        return 1
    fi

    log_info "Using kernel config: $KERNEL_CONFIG"
    return 0
}

# Check if a config option is enabled
is_enabled() {
    local option="$1"
    grep -q "^${option}=y" "$KERNEL_CONFIG" 2>/dev/null
}

# Check if a config option is set (to any value)
is_set() {
    local option="$1"
    grep -q "^${option}=" "$KERNEL_CONFIG" 2>/dev/null
}

# Get config option value
get_value() {
    local option="$1"
    grep "^${option}=" "$KERNEL_CONFIG" 2>/dev/null | cut -d= -f2
}

# ASLR and Memory Randomization
check_aslr() {
    log_check "ASLR (Address Space Layout Randomization)"

    if is_enabled "CONFIG_RANDOMIZE_BASE"; then
        log_enabled "CONFIG_RANDOMIZE_BASE enabled"
    else
        log_disabled "CONFIG_RANDOMIZE_BASE disabled (CRITICAL)"
    fi

    if is_enabled "CONFIG_RANDOMIZE_MEMORY"; then
        log_enabled "CONFIG_RANDOMIZE_MEMORY enabled"
    else
        log_optional "CONFIG_RANDOMIZE_MEMORY disabled (x86_64 specific)"
    fi
}

# Stack Protection
check_stack_protection() {
    log_check "Stack Protection"

    if is_enabled "CONFIG_STACKPROTECTOR"; then
        log_enabled "CONFIG_STACKPROTECTOR enabled"
    else
        log_disabled "CONFIG_STACKPROTECTOR disabled (CRITICAL)"
    fi

    if is_enabled "CONFIG_STACKPROTECTOR_STRONG"; then
        log_enabled "CONFIG_STACKPROTECTOR_STRONG enabled"
    else
        log_optional "CONFIG_STACKPROTECTOR_STRONG disabled (recommended)"
    fi

    if is_enabled "CONFIG_VMAP_STACK"; then
        log_enabled "CONFIG_VMAP_STACK enabled"
    else
        log_optional "CONFIG_VMAP_STACK disabled (recommended)"
    fi
}

# Memory Protection
check_memory_protection() {
    log_check "Memory Protection"

    if is_enabled "CONFIG_HARDENED_USERCOPY"; then
        log_enabled "CONFIG_HARDENED_USERCOPY enabled"
    else
        log_disabled "CONFIG_HARDENED_USERCOPY disabled (IMPORTANT)"
    fi

    if is_enabled "CONFIG_FORTIFY_SOURCE"; then
        log_enabled "CONFIG_FORTIFY_SOURCE enabled"
    else
        log_disabled "CONFIG_FORTIFY_SOURCE disabled (IMPORTANT)"
    fi

    if is_enabled "CONFIG_SLAB_FREELIST_RANDOM"; then
        log_enabled "CONFIG_SLAB_FREELIST_RANDOM enabled"
    else
        log_optional "CONFIG_SLAB_FREELIST_RANDOM disabled"
    fi

    if is_enabled "CONFIG_SLAB_FREELIST_HARDENED"; then
        log_enabled "CONFIG_SLAB_FREELIST_HARDENED enabled"
    else
        log_optional "CONFIG_SLAB_FREELIST_HARDENED disabled"
    fi

    if is_enabled "CONFIG_SHUFFLE_PAGE_ALLOCATOR"; then
        log_enabled "CONFIG_SHUFFLE_PAGE_ALLOCATOR enabled"
    else
        log_optional "CONFIG_SHUFFLE_PAGE_ALLOCATOR disabled"
    fi
}

# Page Table Isolation
check_pti() {
    log_check "Page Table Isolation (PTI)"

    if is_enabled "CONFIG_PAGE_TABLE_ISOLATION"; then
        log_enabled "CONFIG_PAGE_TABLE_ISOLATION enabled"
    else
        log_optional "CONFIG_PAGE_TABLE_ISOLATION disabled (x86_64 specific)"
    fi
}

# Security Modules
check_security_modules() {
    log_check "Security Modules"

    if is_enabled "CONFIG_SECURITY"; then
        log_enabled "CONFIG_SECURITY enabled"
    else
        log_disabled "CONFIG_SECURITY disabled (CRITICAL)"
    fi

    if is_enabled "CONFIG_SECURITY_SELINUX"; then
        log_enabled "CONFIG_SECURITY_SELINUX enabled"
    else
        log_optional "CONFIG_SECURITY_SELINUX disabled (optional)"
    fi

    if is_enabled "CONFIG_SECURITY_APPARMOR"; then
        log_enabled "CONFIG_SECURITY_APPARMOR enabled"
    else
        log_optional "CONFIG_SECURITY_APPARMOR disabled (optional)"
    fi

    if is_enabled "CONFIG_SECURITY_YAMA"; then
        log_enabled "CONFIG_SECURITY_YAMA enabled"
    else
        log_optional "CONFIG_SECURITY_YAMA disabled"
    fi
}

# Module Signing
check_module_signing() {
    log_check "Module Signing"

    if is_enabled "CONFIG_MODULES"; then
        log_info "Kernel modules enabled"

        if is_enabled "CONFIG_MODULE_SIG"; then
            log_enabled "CONFIG_MODULE_SIG enabled"

            if is_enabled "CONFIG_MODULE_SIG_FORCE"; then
                log_enabled "CONFIG_MODULE_SIG_FORCE enabled (enforced)"
            else
                log_optional "CONFIG_MODULE_SIG_FORCE disabled (not enforced)"
            fi

            if is_enabled "CONFIG_MODULE_SIG_SHA256"; then
                log_enabled "CONFIG_MODULE_SIG_SHA256 enabled"
            else
                log_optional "CONFIG_MODULE_SIG_SHA256 disabled"
            fi
        else
            log_optional "CONFIG_MODULE_SIG disabled (modules not signed)"
        fi
    else
        log_info "Kernel modules disabled (static kernel)"
    fi
}

# Kernel Hardening Options
check_kernel_hardening() {
    log_check "Kernel Hardening Options"

    if is_enabled "CONFIG_STRICT_KERNEL_RWX"; then
        log_enabled "CONFIG_STRICT_KERNEL_RWX enabled"
    else
        log_optional "CONFIG_STRICT_KERNEL_RWX disabled"
    fi

    if is_enabled "CONFIG_STRICT_MODULE_RWX"; then
        log_enabled "CONFIG_STRICT_MODULE_RWX enabled"
    else
        log_optional "CONFIG_STRICT_MODULE_RWX disabled"
    fi

    if is_enabled "CONFIG_REFCOUNT_FULL"; then
        log_enabled "CONFIG_REFCOUNT_FULL enabled"
    else
        log_optional "CONFIG_REFCOUNT_FULL disabled"
    fi

    if is_enabled "CONFIG_INIT_STACK_ALL_ZERO"; then
        log_enabled "CONFIG_INIT_STACK_ALL_ZERO enabled"
    else
        log_optional "CONFIG_INIT_STACK_ALL_ZERO disabled"
    fi

    if is_enabled "CONFIG_INIT_ON_ALLOC_DEFAULT_ON"; then
        log_enabled "CONFIG_INIT_ON_ALLOC_DEFAULT_ON enabled"
    else
        log_optional "CONFIG_INIT_ON_ALLOC_DEFAULT_ON disabled"
    fi

    if is_enabled "CONFIG_INIT_ON_FREE_DEFAULT_ON"; then
        log_enabled "CONFIG_INIT_ON_FREE_DEFAULT_ON enabled"
    else
        log_optional "CONFIG_INIT_ON_FREE_DEFAULT_ON disabled"
    fi
}

# x86_64 Specific Security Features
check_x86_64_security() {
    if [ "$ARCH" != "x86_64" ]; then
        log_info "Skipping x86_64 specific checks (architecture: $ARCH)"
        return 0
    fi

    log_check "x86_64 Specific Security Features"

    if is_enabled "CONFIG_X86_SMAP"; then
        log_enabled "CONFIG_X86_SMAP enabled (Supervisor Mode Access Prevention)"
    else
        log_optional "CONFIG_X86_SMAP disabled"
    fi

    if is_enabled "CONFIG_X86_UMIP"; then
        log_enabled "CONFIG_X86_UMIP enabled (User Mode Instruction Prevention)"
    else
        log_optional "CONFIG_X86_UMIP disabled"
    fi

    if is_enabled "CONFIG_RETPOLINE"; then
        log_enabled "CONFIG_RETPOLINE enabled (Spectre mitigation)"
    else
        log_optional "CONFIG_RETPOLINE disabled"
    fi

    if is_enabled "CONFIG_X86_MCE"; then
        log_enabled "CONFIG_X86_MCE enabled (Machine Check Exception)"
    else
        log_optional "CONFIG_X86_MCE disabled"
    fi

    if is_set "CONFIG_LEGACY_VSYSCALL_NONE"; then
        log_enabled "CONFIG_LEGACY_VSYSCALL_NONE (legacy vsyscall disabled)"
    elif is_set "CONFIG_LEGACY_VSYSCALL_EMULATE"; then
        log_optional "CONFIG_LEGACY_VSYSCALL_EMULATE (vsyscall emulated)"
    else
        log_optional "Legacy vsyscall configuration not found"
    fi
}

# Panic on Oops
check_panic_on_oops() {
    log_check "Panic on Oops"

    if is_enabled "CONFIG_PANIC_ON_OOPS"; then
        log_enabled "CONFIG_PANIC_ON_OOPS enabled"

        local timeout=$(get_value "CONFIG_PANIC_TIMEOUT")
        if [ -n "$timeout" ]; then
            log_info "PANIC_TIMEOUT set to: $timeout seconds"
        fi
    else
        log_optional "CONFIG_PANIC_ON_OOPS disabled"
    fi
}

# Network Security
check_network_security() {
    log_check "Network Security"

    if is_enabled "CONFIG_SYN_COOKIES"; then
        log_enabled "CONFIG_SYN_COOKIES enabled (SYN flood protection)"
    else
        log_optional "CONFIG_SYN_COOKIES disabled"
    fi

    if is_enabled "CONFIG_SECURITY_NETWORK"; then
        log_enabled "CONFIG_SECURITY_NETWORK enabled"
    else
        log_optional "CONFIG_SECURITY_NETWORK disabled"
    fi
}

# Show security summary
show_summary() {
    echo ""
    log_info "====================================="
    log_info "Kernel Security Verification Summary"
    log_info "====================================="
    log_info "Kernel Version: $KERNEL_VERSION"
    log_info "Architecture: $ARCH"
    log_info ""
    log_info "Security Features Enabled: $SECURITY_ENABLED"
    log_info "Security Features Disabled: $SECURITY_DISABLED"
    log_info "Optional/Warnings: $SECURITY_WARNINGS"
    log_info "====================================="

    # Security score
    local total=$((SECURITY_ENABLED + SECURITY_DISABLED))
    if [ $total -gt 0 ]; then
        local percentage=$((SECURITY_ENABLED * 100 / total))
        log_info "Security Score: ${percentage}%"
    fi

    log_info "====================================="

    if [ $SECURITY_DISABLED -eq 0 ]; then
        log_info "✓ All critical security features enabled"
        return 0
    else
        log_warn "⚠ Some critical security features are disabled"
        return 1
    fi
}

# Main
main() {
    log_info "Kimigayo OS - Kernel Security Verification"
    log_info "Kernel Version: ${KERNEL_VERSION}"
    log_info "Architecture: ${ARCH}"
    echo ""

    # Check if config exists
    check_config_exists || exit 1

    echo ""

    # Run all security checks
    check_aslr
    echo ""
    check_stack_protection
    echo ""
    check_memory_protection
    echo ""
    check_pti
    echo ""
    check_security_modules
    echo ""
    check_module_signing
    echo ""
    check_kernel_hardening
    echo ""
    check_x86_64_security
    echo ""
    check_panic_on_oops
    echo ""
    check_network_security

    # Show summary
    show_summary
}

main "$@"
