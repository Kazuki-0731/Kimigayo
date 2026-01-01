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
IMAGES=(
    "kimigayo-os:standard"
    "alpine:latest"
    "gcr.io/distroless/base-debian12"
    "ubuntu:minimal"
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

        # Try different shell paths for different images
        if docker run --rm "$image" /bin/sh -c "exit 0" > /dev/null 2>&1; then
            end=$(date +%s%N)
            successful_runs=$((successful_runs + 1))
        elif docker run --rm "$image" /busybox/sh -c "exit 0" > /dev/null 2>&1; then
            end=$(date +%s%N)
            successful_runs=$((successful_runs + 1))
        elif docker run --rm "$image" sh -c "exit 0" > /dev/null 2>&1; then
            end=$(date +%s%N)
            successful_runs=$((successful_runs + 1))
        else
            log_warning "  Iteration $i: failed to execute"
            continue
        fi

        elapsed=$((($end - $start) / 1000000)) # Convert to milliseconds
        total_time=$((total_time + elapsed))
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
    container_id=""
    if docker run -d --name "bench-mem-$$" "$image" sleep 60 > /dev/null 2>&1; then
        container_id="bench-mem-$$"
    elif docker run -d --name "bench-mem-$$" "$image" /bin/sleep 60 > /dev/null 2>&1; then
        container_id="bench-mem-$$"
    elif docker run -d --name "bench-mem-$$" "$image" /busybox/sleep 60 > /dev/null 2>&1; then
        container_id="bench-mem-$$"
    else
        log_warning "$image: failed to start container"
        memory_usage["$image"]=0
        continue
    fi

    sleep 2

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
    else
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

for image in "${IMAGES[@]}"; do
    if ! docker image inspect "$image" > /dev/null 2>&1; then
        has_shell["$image"]="N/A"
        has_pkg_manager["$image"]="N/A"
        continue
    fi

    # Check shell availability
    if docker run --rm "$image" /bin/sh -c "exit 0" > /dev/null 2>&1; then
        has_shell["$image"]="✅"
    else
        has_shell["$image"]="❌"
    fi

    # Check package manager
    pkg_mgr="❌"
    if docker run --rm "$image" /bin/sh -c "which apk" > /dev/null 2>&1; then
        pkg_mgr="✅ (apk)"
    elif docker run --rm "$image" /bin/sh -c "which apt" > /dev/null 2>&1; then
        pkg_mgr="✅ (apt)"
    fi
    has_pkg_manager["$image"]="$pkg_mgr"

    log_result "$image: Shell=${has_shell[$image]}, PkgMgr=${has_pkg_manager[$image]}"
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

| Image | Size (MB) | Startup (ms) | Memory (MB) | Shell | Package Manager |
|-------|-----------|--------------|-------------|-------|-----------------|
EOF

for image in "${IMAGES[@]}"; do
    echo "| $image | ${image_sizes[$image]:-0} | ${startup_times[$image]:-0} | ${memory_usage[$image]:-0} | ${has_shell[$image]:-N/A} | ${has_pkg_manager[$image]:-N/A} |" >> "$MD_FILE"
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
    if [[ "$image" == kimigayo-os:* ]]; then
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
