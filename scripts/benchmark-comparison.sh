#!/bin/bash
#
# Comparison Benchmark Script for Kimigayo OS
# Compares performance against Alpine, Distroless, and Ubuntu Minimal
#
# Note: Requires bash 4.0+ for associative arrays
# macOS: brew install bash, then use /usr/local/bin/bash or /opt/homebrew/bin/bash

set -euo pipefail

# Check bash version (need 4.0+ for associative arrays)
if [ "${BASH_VERSINFO[0]}" -lt 4 ]; then
    echo "Error: This script requires bash 4.0 or higher (current: ${BASH_VERSION})"
    echo "On macOS: brew install bash"
    echo "Then run with: /usr/local/bin/bash or /opt/homebrew/bin/bash"
    exit 1
fi

# Save project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Configuration
ITERATIONS="${ITERATIONS:-10}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/benchmark-results}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/comparison_${TIMESTAMP}.txt"
JSON_FILE="${OUTPUT_DIR}/comparison_${TIMESTAMP}.json"
MD_FILE="${OUTPUT_DIR}/comparison_${TIMESTAMP}.md"

# Images to compare
# Use explicit version tags for Kimigayo OS
KIMIGAYO_VERSION="${KIMIGAYO_VERSION:-2.0.1}"
IMAGES=(
    "ishinokazuki/kimigayo-os:${KIMIGAYO_VERSION}-standard-arm64"
    "alpine:latest"
    "gcr.io/distroless/base-debian12:latest"
    "gcr.io/distroless/static-debian12:latest"
    "ubuntu:22.04"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions with timestamp (JST)
log_info() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[INFO] ${timestamp}${NC} $*" | tee -a "$OUTPUT_FILE"
}

log_success() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[SUCCESS] ${timestamp}${NC} $*" | tee -a "$OUTPUT_FILE"
}

log_warning() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARNING] ${timestamp}${NC} $*" | tee -a "$OUTPUT_FILE"
}

log_error() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR] ${timestamp}${NC} $*" | tee -a "$OUTPUT_FILE"
}

log_result() {
    echo -e "${BLUE}[RESULT]${NC} $*" | tee -a "$OUTPUT_FILE"
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

log_info "=== Comparison Benchmark Script ==="
log_info "Comparing Kimigayo OS against Alpine, Distroless, and Ubuntu"
log_info "Iterations: ${ITERATIONS}"
log_info "Output directory: ${OUTPUT_DIR}"
echo ""

# Pull all images
log_info "=== Pulling images ==="
for image in "${IMAGES[@]}"; do
    log_info "Pulling $image..."
    if docker pull "$image" > /dev/null 2>&1; then
        log_success "Pulled: $image"
    else
        log_warning "Failed to pull: $image (skipping)"
    fi
done
echo ""

# Measure image sizes
log_info "=== Image Size Comparison ==="
declare -A image_sizes
for image in "${IMAGES[@]}"; do
    if docker image inspect "$image" > /dev/null 2>&1; then
        size=$(docker images "$image" --format "{{.Size}}")
        size_bytes=$(docker inspect "$image" --format "{{.Size}}")
        size_mb=$((size_bytes / 1024 / 1024))
        image_sizes["$image"]=$size_mb
        log_result "$image: $size ($size_mb MB)"
    else
        log_warning "$image: not available"
        image_sizes["$image"]=0
    fi
done
echo ""

# Measure startup time
log_info "=== Startup Time Comparison ==="
declare -A startup_times

for image in "${IMAGES[@]}"; do
    if ! docker image inspect "$image" > /dev/null 2>&1; then
        log_warning "$image: skipping (not available)"
        startup_times["$image"]=0
        continue
    fi

    log_info "Testing $image (${ITERATIONS} iterations)..."

    total_time=0
    successful_runs=0

    for i in $(seq 1 "$ITERATIONS"); do
        start=$(date +%s%N)
        execution_success=false

        # Try different execution methods for different images
        # 1. Standard shell (Alpine, Ubuntu, Kimigayo)
        if docker run --rm "$image" /bin/sh -c "exit 0" > /dev/null 2>&1; then
            execution_success=true
        elif docker run --rm "$image" sh -c "exit 0" > /dev/null 2>&1; then
            execution_success=true
        elif docker run --rm "$image" /busybox/sh -c "exit 0" > /dev/null 2>&1; then
            execution_success=true
        # 2. Distroless images: try sleep directly (no shell)
        elif docker run --rm "$image" sleep 0.001 > /dev/null 2>&1; then
            execution_success=true
        # 3. Try with timeout (for images that need SIGTERM)
        elif timeout 1 docker run --rm "$image" tail -f /dev/null > /dev/null 2>&1; then
            execution_success=true
        fi

        end=$(date +%s%N)

        if [ "$execution_success" = true ]; then
            successful_runs=$((successful_runs + 1))
            elapsed=$((($end - $start) / 1000000)) # Convert to milliseconds
            total_time=$((total_time + elapsed))
        else
            log_warning "  Iteration $i: failed to execute"
        fi
    done

    if [ "$successful_runs" -gt 0 ]; then
        avg_time=$((total_time / successful_runs))
        startup_times["$image"]=$avg_time
        log_result "$image: ${avg_time}ms (avg of $successful_runs runs)"
    else
        startup_times["$image"]=0
        log_warning "$image: no successful runs"
    fi
done
echo ""

# Measure memory usage
log_info "=== Memory Usage Comparison ==="
declare -A memory_usage

for image in "${IMAGES[@]}"; do
    if ! docker image inspect "$image" > /dev/null 2>&1; then
        log_warning "$image: skipping (not available)"
        memory_usage["$image"]=0
        continue
    fi

    log_info "Testing $image..."

    # Run container in background
    # Try different methods depending on image type
    container_id="bench-mem-$$"
    started=false

    # Standard images with shell
    if docker run -d --name "$container_id" "$image" sleep 60 > /dev/null 2>&1; then
        started=true
    # BusyBox path
    elif docker run -d --name "$container_id" "$image" /bin/sleep 60 > /dev/null 2>&1; then
        started=true
    elif docker run -d --name "$container_id" "$image" /busybox/sleep 60 > /dev/null 2>&1; then
        started=true
    # Distroless: use tail -f /dev/null (keeps container running)
    elif docker run -d --name "$container_id" "$image" tail -f /dev/null > /dev/null 2>&1; then
        started=true
    # Distroless static: use /pause if available
    elif docker run -d --name "$container_id" "$image" /pause > /dev/null 2>&1; then
        started=true
    fi

    if [ "$started" = false ]; then
        log_warning "$image: failed to start container"
        memory_usage["$image"]=0
        continue
    fi

    sleep 2

    # Verify container is still running
    if ! docker ps --filter "name=$container_id" --format "{{.Names}}" | grep -q "$container_id"; then
        log_warning "$image: container stopped unexpectedly"
        memory_usage["$image"]=0
        docker rm -f "$container_id" > /dev/null 2>&1 || true
        continue
    fi

    # Get memory usage in MB
    mem_raw=$(docker stats --no-stream --format "{{.MemUsage}}" "$container_id" 2>/dev/null | awk '{print $1}')

    # Extract numeric value and convert to MB
    if [[ "$mem_raw" =~ ^([0-9.]+)([KMG])iB$ ]]; then
        mem_value="${BASH_REMATCH[1]}"
        mem_unit="${BASH_REMATCH[2]}"

        case "$mem_unit" in
            K)
                mem_mb=$(echo "scale=2; $mem_value / 1024" | bc)
                ;;
            M)
                mem_mb="$mem_value"
                ;;
            G)
                mem_mb=$(echo "scale=2; $mem_value * 1024" | bc)
                ;;
        esac
    elif [[ "$mem_raw" =~ ^([0-9.]+)MiB$ ]]; then
        # Alternative format without unit letter
        mem_mb="${BASH_REMATCH[1]}"
    else
        log_warning "$image: unable to parse memory usage: $mem_raw"
        mem_mb="0"
    fi

    memory_usage["$image"]=$(printf "%.0f" "$mem_mb" 2>/dev/null || echo "0")

    docker rm -f "$container_id" > /dev/null 2>&1

    log_result "$image: ${memory_usage[$image]} MB"
done
echo ""

# Check features
log_info "=== Feature Comparison ==="
declare -A has_shell
declare -A has_pkg_manager
declare -A image_type

for image in "${IMAGES[@]}"; do
    if ! docker image inspect "$image" > /dev/null 2>&1; then
        has_shell["$image"]="N/A"
        has_pkg_manager["$image"]="N/A"
        image_type["$image"]="N/A"
        continue
    fi

    # Determine image type
    if [[ "$image" == *"distroless"* ]]; then
        image_type["$image"]="Distroless"
    elif [[ "$image" == *"alpine"* ]]; then
        image_type["$image"]="Alpine"
    elif [[ "$image" == *"ubuntu"* ]]; then
        image_type["$image"]="Ubuntu"
    elif [[ "$image" == *"kimigayo"* ]]; then
        image_type["$image"]="Kimigayo"
    else
        image_type["$image"]="Other"
    fi

    # Check shell availability
    if docker run --rm "$image" /bin/sh -c "exit 0" > /dev/null 2>&1; then
        has_shell["$image"]="✅"
    elif docker run --rm "$image" sh -c "exit 0" > /dev/null 2>&1; then
        has_shell["$image"]="✅"
    else
        has_shell["$image"]="❌"
    fi

    # Check package manager
    pkg_mgr="❌"
    if [ "${has_shell[$image]}" = "✅" ]; then
        if docker run --rm "$image" /bin/sh -c "which apk" > /dev/null 2>&1; then
            pkg_mgr="✅ (apk)"
        elif docker run --rm "$image" sh -c "which apt" > /dev/null 2>&1; then
            pkg_mgr="✅ (apt)"
        fi
    fi
    has_pkg_manager["$image"]="$pkg_mgr"

    log_result "$image (${image_type[$image]}): Shell=${has_shell[$image]}, PkgMgr=${has_pkg_manager[$image]}"
done
echo ""

# Generate JSON report
log_info "=== Generating JSON report ==="
cat > "$JSON_FILE" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "iterations": $ITERATIONS,
  "results": {
EOF

first=true
for image in "${IMAGES[@]}"; do
    if [ "$first" = false ]; then
        echo "," >> "$JSON_FILE"
    fi
    first=false

    cat >> "$JSON_FILE" <<EOF
    "$image": {
      "type": "${image_type[$image]:-N/A}",
      "size_mb": ${image_sizes[$image]:-0},
      "startup_ms": ${startup_times[$image]:-0},
      "memory_mb": ${memory_usage[$image]:-0},
      "has_shell": "${has_shell[$image]:-N/A}",
      "has_pkg_manager": "${has_pkg_manager[$image]:-N/A}"
    }
EOF
done

cat >> "$JSON_FILE" <<EOF

  }
}
EOF

log_success "JSON report: $JSON_FILE"

# Generate Markdown report
log_info "=== Generating Markdown report ==="
cat > "$MD_FILE" <<EOF
# Comparison Benchmark Results

**Timestamp**: $TIMESTAMP
**Iterations**: $ITERATIONS

## Performance Comparison

| Image | Type | Size (MB) | Startup (ms) | Memory (MB) | Shell | Package Manager |
|-------|------|-----------|--------------|-------------|-------|-----------------|
EOF

for image in "${IMAGES[@]}"; do
    echo "| $image | ${image_type[$image]:-N/A} | ${image_sizes[$image]:-0} | ${startup_times[$image]:-0} | ${memory_usage[$image]:-0} | ${has_shell[$image]:-N/A} | ${has_pkg_manager[$image]:-N/A} |" >> "$MD_FILE"
done

cat >> "$MD_FILE" <<EOF

## Summary

- **Smallest image**: $(for img in "${IMAGES[@]}"; do echo "${image_sizes[$img]:-999999} $img"; done | sort -n | head -1 | awk '{print $2}')
- **Fastest startup**: $(for img in "${IMAGES[@]}"; do if [ "${startup_times[$img]:-0}" -gt 0 ]; then echo "${startup_times[$img]} $img"; fi; done | sort -n | head -1 | awk '{print $2}')
- **Lowest memory**: $(for img in "${IMAGES[@]}"; do if [ "${memory_usage[$img]:-0}" -gt 0 ]; then echo "${memory_usage[$img]} $img"; fi; done | sort -n | head -1 | awk '{print $2}')

## Notes

- Startup time measured over $ITERATIONS iterations
- Memory usage measured after 2-second warmup
- Some images may not support all tests
EOF

log_success "Markdown report: $MD_FILE"

# Cleanup: Remove pulled images
log_info "=== Cleaning up pulled images ==="
for image in "${IMAGES[@]}"; do
    # Skip kimigayo-os (our own image)
    if [[ "$image" == *"kimigayo-os"* ]]; then
        log_info "Keeping $image (our image)"
        continue
    fi

    if docker image inspect "$image" > /dev/null 2>&1; then
        log_info "Removing $image..."
        docker rmi "$image" > /dev/null 2>&1 || log_warning "Failed to remove $image"
    fi
done
log_success "Cleanup complete"
echo ""

# Display summary
echo ""
log_success "=== Benchmark Complete ==="
log_info "Results saved to:"
log_info "  Text:     $OUTPUT_FILE"
log_info "  JSON:     $JSON_FILE"
log_info "  Markdown: $MD_FILE"
echo ""
log_info "Summary table:"
echo ""
cat "$MD_FILE"
