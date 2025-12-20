#!/bin/bash
# Kimigayo OS - Kernel Patch Application Script
# Applies security and optimization patches to Linux kernel

set -e

# Configuration
KERNEL_VERSION="${KERNEL_VERSION:-6.6.11}"

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
KERNEL_SRC_DIR="${PROJECT_ROOT}/build/kernel-src/linux-${KERNEL_VERSION}"
PATCHES_DIR="${PROJECT_ROOT}/src/kernel/patches"
PATCH_LOG="${PROJECT_ROOT}/build/kernel-patches.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions with timestamp
log_info() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[INFO]${NC} ${timestamp} $*" | tee -a "$PATCH_LOG"
}

log_warn() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARN]${NC} ${timestamp} $*" | tee -a "$PATCH_LOG"
}

log_error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR]${NC} ${timestamp} $*" | tee -a "$PATCH_LOG"
}

log_patch() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[PATCH]${NC} ${timestamp} $*" | tee -a "$PATCH_LOG"
}

# Check if kernel source exists
check_kernel_source() {
    if [ ! -d "$KERNEL_SRC_DIR" ]; then
        log_error "Kernel source not found: $KERNEL_SRC_DIR"
        log_error "Please run download-kernel.sh first"
        return 1
    fi
}

# Create patches directory if not exists
init_patches_dir() {
    mkdir -p "$PATCHES_DIR"
    mkdir -p "$(dirname "$PATCH_LOG")"

    # Create marker file to track applied patches
    touch "${KERNEL_SRC_DIR}/.kimigayo-patches-applied" 2>/dev/null || true
}

# Check if patches already applied
is_patches_applied() {
    if [ -f "${KERNEL_SRC_DIR}/.kimigayo-patches-applied" ]; then
        local applied_count=$(wc -l < "${KERNEL_SRC_DIR}/.kimigayo-patches-applied" 2>/dev/null || echo 0)
        if [ "$applied_count" -gt 0 ]; then
            log_info "Patches already applied ($applied_count patches)"
            return 0
        fi
    fi
    return 1
}

# Apply a single patch
apply_patch() {
    local patch_file="$1"
    local patch_name=$(basename "$patch_file")

    log_patch "Applying patch: $patch_name"

    cd "$KERNEL_SRC_DIR" || return 1

    if patch -p1 --dry-run --silent < "$patch_file" 2>/dev/null; then
        patch -p1 < "$patch_file" || {
            log_error "Failed to apply patch: $patch_name"
            return 1
        }
        log_info "Successfully applied: $patch_name"
        echo "$patch_name" >> "${KERNEL_SRC_DIR}/.kimigayo-patches-applied"
        return 0
    else
        log_warn "Patch already applied or not applicable: $patch_name"
        return 0
    fi
}

# Apply all patches
apply_all_patches() {
    local patch_count=0

    # Find all patch files in patches directory
    if [ -d "$PATCHES_DIR" ]; then
        while IFS= read -r -d '' patch_file; do
            apply_patch "$patch_file" || {
                log_error "Failed to apply patch: $(basename "$patch_file")"
                return 1
            }
            patch_count=$((patch_count + 1))
        done < <(find "$PATCHES_DIR" -name "*.patch" -print0 | sort -z)
    fi

    if [ "$patch_count" -eq 0 ]; then
        log_info "No patches found in $PATCHES_DIR"
        log_info "Creating example security hardening patch..."
        create_example_patches
    else
        log_info "Applied $patch_count patches successfully"
    fi
}

# Create example security hardening patches
create_example_patches() {
    local example_patch="${PATCHES_DIR}/0001-security-hardening.patch"

    if [ -f "$example_patch" ]; then
        log_info "Example patch already exists"
        return 0
    fi

    cat > "$example_patch" << 'EOF'
# Kimigayo OS Security Hardening Patch
# This is a placeholder for future security patches
#
# Example patches that may be added:
# - Grsecurity/PaX security enhancements
# - Kernel self-protection features
# - Additional ASLR improvements
# - Stack canary enhancements
#
# Note: Actual patches will be added based on security requirements
EOF

    log_info "Created example patch template: $example_patch"
    log_info "Add actual .patch files to $PATCHES_DIR as needed"
}

# Verify kernel source integrity after patching
verify_patched_kernel() {
    log_info "Verifying patched kernel source"

    # Check if kernel source directory exists
    if [ ! -d "$KERNEL_SRC_DIR" ]; then
        log_error "Kernel source directory not found: $KERNEL_SRC_DIR"
        return 1
    fi

    # Check critical files exist (using absolute paths)
    local critical_files=(
        "${KERNEL_SRC_DIR}/Makefile"
        "${KERNEL_SRC_DIR}/arch/x86/Makefile"
        "${KERNEL_SRC_DIR}/kernel/Makefile"
    )

    for file in "${critical_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Critical file missing after patching: $file"
            log_info "Directory listing:"
            ls -la "$KERNEL_SRC_DIR" | head -20 || true
            return 1
        fi
    done

    log_info "Kernel source integrity verified"
}

# Main
main() {
    log_info "Kimigayo OS - Kernel Patch Application Script"
    log_info "Kernel Version: ${KERNEL_VERSION}"
    log_info "Kernel Source: ${KERNEL_SRC_DIR}"
    log_info "Patches Directory: ${PATCHES_DIR}"
    log_info "Patch Log: ${PATCH_LOG}"
    echo "" | tee -a "$PATCH_LOG"

    check_kernel_source || exit 1
    init_patches_dir

    if is_patches_applied; then
        log_info "Skipping patch application (already applied)"
        exit 0
    fi

    apply_all_patches || exit 1
    verify_patched_kernel || exit 1

    log_info "Kernel patching completed successfully"
}

main "$@"
