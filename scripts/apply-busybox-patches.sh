#!/usr/bin/env bash
#
# BusyBox Patch Application Script for Kimigayo OS
# Applies musl libc compatibility patches to BusyBox source
#

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Directories
BUSYBOX_SRC="${BUSYBOX_SRC:-${PROJECT_ROOT}/build/busybox-1.36.1}"
PATCHES_DIR="${PROJECT_ROOT}/src/busybox/patches"
PATCH_LOG="${PROJECT_ROOT}/build/busybox-patches.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$PATCH_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$PATCH_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$PATCH_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$PATCH_LOG"
}

# Initialize log
mkdir -p "$(dirname "$PATCH_LOG")"
: > "$PATCH_LOG"

log_info "Kimigayo OS - BusyBox Patch Application Script"
log_info "BusyBox Source: $BUSYBOX_SRC"
log_info "Patches Directory: $PATCHES_DIR"
log_info "Patch Log: $PATCH_LOG"
log_info ""

# Validate source directory
if [ ! -d "$BUSYBOX_SRC" ]; then
    log_error "BusyBox source directory not found: $BUSYBOX_SRC"
    exit 1
fi

# Validate patches directory
if [ ! -d "$PATCHES_DIR" ]; then
    log_warning "Patches directory not found: $PATCHES_DIR"
    log_info "No patches to apply, continuing..."
    exit 0
fi

# Count patches
PATCH_COUNT=$(find "$PATCHES_DIR" -name "*.patch" -type f | wc -l | tr -d ' ')
if [ "$PATCH_COUNT" -eq 0 ]; then
    log_info "No patches found in $PATCHES_DIR"
    log_success "Patch application completed (no patches to apply)"
    exit 0
fi

log_info "Found $PATCH_COUNT patch(es) to apply"
echo ""

# Apply patches in order
cd "$BUSYBOX_SRC"
APPLIED_COUNT=0
FAILED_COUNT=0

for patch_file in "$PATCHES_DIR"/*.patch; do
    if [ ! -f "$patch_file" ]; then
        continue
    fi

    patch_name=$(basename "$patch_file")
    log_info "Applying patch: $patch_name"

    # Check if patch was already applied
    if patch -p1 --dry-run --silent < "$patch_file" > /dev/null 2>&1; then
        # Patch can be applied
        if patch -p1 < "$patch_file" >> "$PATCH_LOG" 2>&1; then
            log_success "  ✓ $patch_name applied successfully"
            ((APPLIED_COUNT++))
        else
            log_error "  ✗ Failed to apply $patch_name"
            ((FAILED_COUNT++))
        fi
    else
        # Check if already applied (reversed patch test)
        if patch -p1 -R --dry-run --silent < "$patch_file" > /dev/null 2>&1; then
            log_warning "  ⊘ $patch_name already applied (skipping)"
            ((APPLIED_COUNT++))
        else
            log_error "  ✗ Cannot apply $patch_name (conflicts or errors)"
            log_error "    Run: patch -p1 --dry-run < $patch_file"
            log_error "    in directory: $BUSYBOX_SRC"
            ((FAILED_COUNT++))
        fi
    fi
done

echo ""
log_info "=== Patch Application Summary ==="
log_info "Total patches: $PATCH_COUNT"
log_info "Successfully applied: $APPLIED_COUNT"
log_info "Failed: $FAILED_COUNT"
echo ""

if [ "$FAILED_COUNT" -gt 0 ]; then
    log_error "Some patches failed to apply"
    log_info "Check log for details: $PATCH_LOG"
    exit 1
fi

log_success "All patches applied successfully"
log_info "Patch log saved to: $PATCH_LOG"

exit 0
