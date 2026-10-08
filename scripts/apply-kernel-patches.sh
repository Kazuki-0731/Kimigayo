#!/bin/bash
# Kimigayo OS - Kernel Patch Application Script
# Applies security and optimization patches to Linux kernel

set -e

# Configuration

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# バージョンは versions.mk（単一の真実の源）から読み込む
# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"
KERNEL_SRC_DIR="${PROJECT_ROOT}/build/kernel-src/linux-${KERNEL_VERSION}"
PATCHES_DIR="${PROJECT_ROOT}/src/kernel/patches"
PATCH_LOG="${PROJECT_ROOT}/build/kernel-patches.log"

# apply_patch の戻り値:
#   0 = 適用した
#   2 = 差分はあるが当たらなかった（要判断。上流取り込み済み？当て直し必要？）
#   3 = そもそも差分を含まないファイル（プレースホルダ。判断不要）
#   他 = 失敗
readonly PATCH_SKIPPED=2
readonly PATCH_NOT_A_DIFF=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions with timestamp (JST)
log_info() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[INFO] ${timestamp}${NC} $*" | tee -a "$PATCH_LOG"
}

log_warn() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARN] ${timestamp}${NC} $*" | tee -a "$PATCH_LOG"
}

log_error() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR] ${timestamp}${NC} $*" | tee -a "$PATCH_LOG"
}

log_patch() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[PATCH] ${timestamp}${NC} $*" | tee -a "$PATCH_LOG"
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
        local applied_count
        applied_count=$(wc -l < "${KERNEL_SRC_DIR}/.kimigayo-patches-applied" 2>/dev/null || echo 0)
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
    local patch_name
    patch_name=$(basename "$patch_file")

    # 差分を1つも含まないファイル（コメントだけのプレースホルダ）は
    # 「当たらなかったパッチ」と混ぜない。混ぜると毎回 WARN が出続けて、
    # 本当に当て直しが必要なパッチの警告が埋もれる。
    if ! grep -qE '^(---|\+\+\+|diff |Index: ) ' "$patch_file" 2>/dev/null \
       && ! grep -qE '^(--- |\+\+\+ |diff |Index: )' "$patch_file" 2>/dev/null; then
        log_info "Not a diff (placeholder), ignoring: $patch_name"
        return "$PATCH_NOT_A_DIFF"
    fi

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
        return "$PATCH_SKIPPED"
    fi
}

# Apply all patches
apply_all_patches() {
    local found_count=0
    local applied_count=0
    local skipped_count=0
    local ignored_count=0

    # Find all patch files in patches directory
    if [ -d "$PATCHES_DIR" ]; then
        while IFS= read -r -d '' patch_file; do
            found_count=$((found_count + 1))
            if apply_patch "$patch_file"; then
                applied_count=$((applied_count + 1))
            else
                case "$?" in
                    "$PATCH_SKIPPED") skipped_count=$((skipped_count + 1)) ;;
                    "$PATCH_NOT_A_DIFF") ignored_count=$((ignored_count + 1)) ;;
                    *)
                        log_error "Failed to apply patch: $(basename "$patch_file")"
                        return 1
                        ;;
                esac
            fi
        done < <(find "$PATCHES_DIR" -name "*.patch" -print0 | sort -z)
    fi

    if [ "$found_count" -eq 0 ]; then
        log_info "No patches found in $PATCHES_DIR"
        log_info "Creating example security hardening patch..."
        create_example_patches
        return 0
    fi

    log_info "Patches found: ${found_count}, applied: ${applied_count}, skipped: ${skipped_count}, placeholders: ${ignored_count}"

    if [ "$skipped_count" -gt 0 ]; then
        # 当たらなかったパッチは黙って飛ばされる。カーネルを上げた直後は
        # 「上流が取り込んだので不要」なのか「当て直しが必要」なのかを人が判断する。
        log_warn "${skipped_count} patch(es) did not apply to Linux ${KERNEL_VERSION}."
        log_warn "Check whether they are obsolete (upstream took them) or need rebasing:"
        log_warn "  grep -i 'not applicable' ${PATCH_LOG}"
        log_warn "See src/kernel/patches/README.md"
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

    # Check critical files exist
    local critical_files
    critical_files=(
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
    log_info ""

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
