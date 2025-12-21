#!/bin/bash
# Kimigayo OS - Image Builder
# Creates tar.gz images with checksums and signatures

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Build configuration
BUILD_DIR="${PROJECT_ROOT}/build"
ROOTFS_DIR="${BUILD_DIR}/rootfs"
OUTPUT_DIR="${PROJECT_ROOT}/output"
ARCH="${ARCH:-x86_64}"
IMAGE_TYPE="${IMAGE_TYPE:-minimal}"
VERSION="${VERSION:-0.1.0}"

# Output file names
IMAGE_NAME="kimigayo-${IMAGE_TYPE}-${VERSION}-${ARCH}"
IMAGE_FILE="${OUTPUT_DIR}/${IMAGE_NAME}.tar.gz"
CHECKSUM_FILE="${OUTPUT_DIR}/${IMAGE_NAME}.sha256"
SIGNATURE_FILE="${OUTPUT_DIR}/${IMAGE_NAME}.sig"

# Log file
LOG_DIR="${BUILD_DIR}/logs"
LOG_FILE="${LOG_DIR}/image-build.log"
mkdir -p "$LOG_DIR"
mkdir -p "$OUTPUT_DIR"

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $*" | tee -a "$LOG_FILE"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════╗
║   Kimigayo OS - Image Builder        ║
║   Task 22.1: tar.gz Image Generation  ║
╚═══════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if rootfs exists
if [ ! -d "$ROOTFS_DIR" ]; then
    log_error "rootfs directory not found: $ROOTFS_DIR"
    log_error "Please run scripts/build-rootfs.sh first"
    exit 1
fi

# Display build information
log_info "Build Configuration:"
log_info "  Architecture: $ARCH"
log_info "  Image Type:   $IMAGE_TYPE"
log_info "  Version:      $VERSION"
log_info "  Output:       $IMAGE_FILE"
echo ""

# Step 1: Create tar.gz archive
log "Step 1/3: Creating tar.gz archive..."
cd "$ROOTFS_DIR"

# Create compressed tarball
# Note: BSD tar (macOS) doesn't support --sort, --numeric-owner, --owner, --group
# Using portable options
if tar --version 2>&1 | grep -q "GNU tar"; then
    # GNU tar
    tar czf "$IMAGE_FILE" \
        --numeric-owner \
        --owner=0 \
        --group=0 \
        --sort=name \
        . 2>&1 | tee -a "$LOG_FILE"
else
    # BSD tar (macOS)
    tar czf "$IMAGE_FILE" . 2>&1 | tee -a "$LOG_FILE"
fi

if [ ! -f "$IMAGE_FILE" ]; then
    log_error "Failed to create image file"
    exit 1
fi

# Get image size
IMAGE_SIZE=$(du -h "$IMAGE_FILE" | cut -f1)
IMAGE_SIZE_BYTES=$(stat -f%z "$IMAGE_FILE" 2>/dev/null || stat -c%s "$IMAGE_FILE" 2>/dev/null)

log "✓ Image created: $IMAGE_FILE"
log "  Size: $IMAGE_SIZE ($IMAGE_SIZE_BYTES bytes)"
echo ""

# Check size requirements
SIZE_LIMIT_MB=0
case "$IMAGE_TYPE" in
    minimal)
        SIZE_LIMIT_MB=5
        ;;
    standard)
        SIZE_LIMIT_MB=15
        ;;
    extended)
        SIZE_LIMIT_MB=50
        ;;
esac

SIZE_LIMIT_BYTES=$((SIZE_LIMIT_MB * 1024 * 1024))
if [ "$IMAGE_SIZE_BYTES" -gt "$SIZE_LIMIT_BYTES" ]; then
    log_warn "Image size ($IMAGE_SIZE) exceeds target ($SIZE_LIMIT_MB MB)"
else
    log "✓ Image size is within target ($SIZE_LIMIT_MB MB)"
fi
echo ""

# Step 2: Generate SHA-256 checksum
log "Step 2/3: Generating SHA-256 checksum..."
cd "$OUTPUT_DIR"

# Generate checksum (platform-independent)
if command -v sha256sum &> /dev/null; then
    sha256sum "$(basename "$IMAGE_FILE")" > "$CHECKSUM_FILE"
elif command -v shasum &> /dev/null; then
    shasum -a 256 "$(basename "$IMAGE_FILE")" > "$CHECKSUM_FILE"
else
    log_error "No SHA-256 tool found (sha256sum or shasum)"
    exit 1
fi

CHECKSUM=$(cut -d' ' -f1 "$CHECKSUM_FILE")
log "✓ Checksum generated: $CHECKSUM_FILE"
log "  SHA-256: $CHECKSUM"
echo ""

# Step 3: Generate Ed25519 signature (placeholder)
log "Step 3/3: Generating Ed25519 signature..."

# For Phase 5, we'll create a placeholder signature
# Full implementation will use actual Ed25519 signing in Phase 6
cat > "$SIGNATURE_FILE" << EOF
{
  "version": "1",
  "algorithm": "ed25519",
  "file": "$(basename "$IMAGE_FILE")",
  "checksum": "$CHECKSUM",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "signer": "Kimigayo OS Build System",
  "public_key": "placeholder_public_key_phase5",
  "signature": "placeholder_signature_phase5_$(echo -n "$CHECKSUM" | head -c 32)",
  "note": "This is a placeholder signature for Phase 5. Full Ed25519 implementation in Phase 6."
}
EOF

log "✓ Signature generated: $SIGNATURE_FILE"
log "  Note: Placeholder signature (Phase 5)"
echo ""

# Verify archive integrity
log "Verifying archive integrity..."
if tar tzf "$IMAGE_FILE" > /dev/null 2>&1; then
    log "✓ Archive integrity verified"
else
    log_error "Archive integrity check failed"
    exit 1
fi
echo ""

# Summary
echo -e "${BLUE}═══════════════════════════════════════${NC}"
log "Build Summary:"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
log "  Image:     $IMAGE_FILE"
log "  Size:      $IMAGE_SIZE ($IMAGE_SIZE_BYTES bytes)"
log "  Checksum:  $CHECKSUM_FILE"
log "  Signature: $SIGNATURE_FILE"
echo ""

# List all output files
log "Output files:"
ls -lh "$OUTPUT_DIR"/"${IMAGE_NAME}"* | while read -r line; do
    log "  $line"
done
echo ""

log "✓ Image build completed successfully!"
log "Next step: Run verification tests (Task 23)"
