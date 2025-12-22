#!/bin/bash
# Kimigayo OS - Docker Image Builder
# Creates optimized Docker container image from tar.gz

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Build configuration
OUTPUT_DIR="${PROJECT_ROOT}/output"
IMAGE_TYPE="${IMAGE_TYPE:-minimal}"
VERSION="${VERSION:-0.1.0}"
ARCH="${ARCH:-x86_64}"

# Docker image configuration
IMAGE_NAME="kimigayo-os"
IMAGE_TAG="${IMAGE_TYPE}-${VERSION}-${ARCH}"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
LATEST_TAG="${IMAGE_NAME}:${IMAGE_TYPE}-latest"

# Log file
LOG_DIR="${PROJECT_ROOT}/build/logs"
LOG_FILE="${LOG_DIR}/docker-image-build.log"
mkdir -p "$LOG_DIR"

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
cat << "EOF"
╔═══════════════════════════════════════╗
║   Kimigayo OS - Docker Image Build   ║
║   Task 22.2: Docker Image Generation  ║
╚═══════════════════════════════════════╝
EOF

# Check if tar.gz exists
TAR_FILE="${OUTPUT_DIR}/kimigayo-${IMAGE_TYPE}-${VERSION}-${ARCH}.tar.gz"
if [ ! -f "$TAR_FILE" ]; then
    log_error "tar.gz file not found: $TAR_FILE"
    log_error "Please run scripts/build-image.sh first"
    exit 1
fi

# Display build information
log_info "Docker Image Configuration:"
log_info "  Image Name:   $FULL_IMAGE_NAME"
log_info "  Latest Tag:   $LATEST_TAG"
log_info "  Image Type:   $IMAGE_TYPE"
log_info "  Version:      $VERSION"
log_info "  Architecture: $ARCH"
log_info "  Source:       $TAR_FILE"
echo ""

# Step 1: Build Docker image using multi-stage Dockerfile
log "Step 1/3: Building Docker image with multi-stage build..."
cd "$PROJECT_ROOT"

# Build the image
docker build \
    -f Dockerfile.runtime \
    -t "$FULL_IMAGE_NAME" \
    -t "$LATEST_TAG" \
    --build-arg VERSION="$VERSION" \
    --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    . 2>&1 | tee -a "$LOG_FILE"

if [ $? -ne 0 ]; then
    log_error "Docker build failed"
    exit 1
fi

log "✓ Docker image built successfully"
echo ""

# Step 2: Verify image
log "Step 2/3: Verifying Docker image..."

# Check if image exists
if ! docker image inspect "$FULL_IMAGE_NAME" > /dev/null 2>&1; then
    log_error "Failed to create Docker image"
    exit 1
fi

# Get image size
IMAGE_SIZE=$(docker image inspect "$FULL_IMAGE_NAME" --format='{{.Size}}' | awk '{print $1}')
IMAGE_SIZE_MB=$(echo "scale=2; $IMAGE_SIZE / 1024 / 1024" | bc)

log "✓ Image verified"
log "  Image ID:   $(docker image inspect "$FULL_IMAGE_NAME" --format='{{.Id}}' | cut -d: -f2 | head -c 12)"
log "  Size:       ${IMAGE_SIZE_MB} MB (${IMAGE_SIZE} bytes)"
log "  Created:    $(docker image inspect "$FULL_IMAGE_NAME" --format='{{.Created}}')"
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

# Compare with float
if [ $(echo "$IMAGE_SIZE_MB > $SIZE_LIMIT_MB" | bc -l) -eq 1 ]; then
    log_warn "Image size (${IMAGE_SIZE_MB} MB) exceeds target ($SIZE_LIMIT_MB MB)"
else
    log "✓ Image size is within target ($SIZE_LIMIT_MB MB)"
fi
echo ""

# Step 3: Test image
log "Step 3/3: Testing Docker image..."

# Test 1: Check if image runs
log_info "Running basic container test..."
if docker run --rm "$FULL_IMAGE_NAME" /bin/sh -c 'echo "Kimigayo OS - Test successful"' 2>&1 | tee -a "$LOG_FILE"; then
    log "✓ Container execution test passed"
else
    log_error "Container execution test failed"
    exit 1
fi
echo ""

# Test 2: Check BusyBox commands
log_info "Testing BusyBox commands..."
TEST_COMMANDS="ls pwd echo cat"
for cmd in $TEST_COMMANDS; do
    if docker run --rm "$FULL_IMAGE_NAME" /bin/sh -c "command -v $cmd > /dev/null 2>&1"; then
        log "✓ Command available: $cmd"
    else
        log_warn "Command not found: $cmd"
    fi
done
echo ""

# Summary
echo -e "${BLUE}═══════════════════════════════════════${NC}"
log "Docker Image Build Summary:"
echo -e "${BLUE}═══════════════════════════════════════${NC}"
log "  Image:        $FULL_IMAGE_NAME"
log "  Latest Tag:   $LATEST_TAG"
log "  Size:         ${IMAGE_SIZE_MB} MB"
log "  Architecture: $ARCH"
echo ""

# List images
log "Available Kimigayo OS images:"
docker images | grep kimigayo-os | while read -r line; do
    log "  $line"
done
echo ""

log "✓ Docker image build completed successfully!"
log ""
log "Usage:"
log "  docker run --rm -it $FULL_IMAGE_NAME"
log "  docker run --rm -it $LATEST_TAG"
echo ""

# Save image to file (optional)
if [ "${SAVE_IMAGE:-false}" = "true" ]; then
    log "Saving image to tar file..."
    IMAGE_TAR="${OUTPUT_DIR}/${IMAGE_NAME}-${IMAGE_TAG}-docker.tar"
    docker save "$FULL_IMAGE_NAME" -o "$IMAGE_TAR"
    log "✓ Image saved to: $IMAGE_TAR"
    log "  Size: $(du -h "$IMAGE_TAR" | cut -f1)"
fi
