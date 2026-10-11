#!/usr/bin/env bash
#
# musl Patch Application Script for Kimigayo OS
# Applies src/libc/patches/*.patch to the musl source tree.
#
# Unlike apply-kernel-patches.sh / apply-busybox-patches.sh, this script
# FAILS when a patch does not apply. Those two log a warning and return 0,
# so a patch that stopped applying after a version bump is skipped silently
# and the build still reports success (CLAUDE.md "パッチはなぜ存在するか").
# The musl patches are security fixes; silently shipping without them is
# worse than a failed build.
#
# The musl source directory (build/musl-src/musl-<ver>) is extracted once and
# reused across builds and architectures, so patches are applied in place.
# To keep that safe:
#
#   - a patch that is already applied is skipped (reverse dry-run succeeds)
#   - the set of applied patches is recorded in .kimigayo-patches; if the
#     current patch set differs (a patch was added, changed or removed),
#     the source tree is discarded and re-extracted before patching, so a
#     removed patch cannot linger in the tree
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# バージョンは versions.mk（単一の真実の源）から読み込む
# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"
# shellcheck source=scripts/lib/build-stamp.sh
source "${PROJECT_ROOT}/scripts/lib/build-stamp.sh"

MUSL_SRC_DIR="${MUSL_SRC_DIR:-${PROJECT_ROOT}/build/musl-src/musl-${MUSL_VERSION}}"
PATCHES_DIR="${PROJECT_ROOT}/src/libc/patches"
PATCH_LOG="${PROJECT_ROOT}/build/musl-patches.log"
MARKER="${MUSL_SRC_DIR}/.kimigayo-patches"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$PATCH_LOG"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$PATCH_LOG"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$PATCH_LOG"; }

mkdir -p "$(dirname "$PATCH_LOG")"
: > "$PATCH_LOG"

log_info "Kimigayo OS - musl Patch Application Script"
log_info "musl Source: $MUSL_SRC_DIR"
log_info "Patches Directory: $PATCHES_DIR"

wanted="$(kimigayo_inputs_id "$PATCHES_DIR"/*.patch)"
log_info "Patch set id: ${wanted:-none}"

# A tree patched with a different set (including "some patch that has since
# been removed") must not be reused. Re-extract it from the verified tarball.
if [ -d "$MUSL_SRC_DIR" ]; then
    have="$(cat "$MARKER" 2>/dev/null || true)"
    if [ "$have" != "$wanted" ]; then
        log_info "Source tree patch set differs (have='${have:-none}', want='${wanted:-none}')"
        log_info "Discarding and re-extracting musl source"
        rm -rf "$MUSL_SRC_DIR"
        bash "${SCRIPT_DIR}/download-musl.sh"
    fi
fi

if [ ! -d "$MUSL_SRC_DIR" ]; then
    log_error "musl source directory not found: $MUSL_SRC_DIR"
    log_error "Run scripts/download-musl.sh first"
    exit 1
fi

shopt -s nullglob
patches=("$PATCHES_DIR"/*.patch)
shopt -u nullglob

applied=0
already=0
for p in "${patches[@]}"; do
    name="$(basename "$p")"
    if (cd "$MUSL_SRC_DIR" && patch -p1 -R --dry-run -s -f < "$p" >/dev/null 2>&1); then
        log_info "  already applied: $name"
        already=$((already + 1))
        continue
    fi
    if (cd "$MUSL_SRC_DIR" && patch -p1 --dry-run -s -f < "$p" >/dev/null 2>&1); then
        (cd "$MUSL_SRC_DIR" && patch -p1 -s -f < "$p") 2>&1 | tee -a "$PATCH_LOG"
        log_success "  applied: $name"
        applied=$((applied + 1))
    else
        log_error "  DOES NOT APPLY: $name"
        log_error "  musl ${MUSL_VERSION} no longer matches this patch."
        log_error "  Rework it against the new source, or remove it deliberately."
        log_error "  Not continuing: shipping without a security patch is worse"
        log_error "  than a failed build."
        (cd "$MUSL_SRC_DIR" && patch -p1 --dry-run -f < "$p") 2>&1 | tee -a "$PATCH_LOG" || true
        exit 1
    fi
done

printf '%s\n' "$wanted" > "$MARKER"
log_success "musl patches: applied=${applied} already=${already} total=${#patches[@]}"
