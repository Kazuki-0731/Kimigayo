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
#
# **版を直書きしないこと。** 2026-10-10 まで既定値が `2.0.1` に
# 固定されており、環境変数を渡さずに実行すると v3.0.0 を測っている
# つもりで **v2.0.1 のイメージを引いて比較していた**。
# 版の正本は git describe（→ scripts/get-version.sh）。
KIMIGAYO_VERSION="${KIMIGAYO_VERSION:-$(bash "${PROJECT_ROOT}/scripts/get-version.sh" 2>/dev/null || echo latest)}"

# **公開前の版は Docker Hub に無い。** KIMIGAYO_IMAGE で手元のイメージを
# 指せるようにしておく（タグを打つ前に比較値が要るときのため）。
#   KIMIGAYO_IMAGE=kimigayo-os:standard-arm64 bash scripts/benchmark-comparison.sh
KIMIGAYO_IMAGE="${KIMIGAYO_IMAGE:-ishinokazuki/kimigayo-os:${KIMIGAYO_VERSION}-standard-arm64}"

# Ubuntu は 24.04。README と CLAUDE.md が載せている比較値がこの版なので
# 揃える（2026-10-11 まで 22.04 を測っていて食い違っていた）。
IMAGES=(
    "$KIMIGAYO_IMAGE"
    "alpine:latest"
    "gcr.io/distroless/base-debian12:latest"
    "gcr.io/distroless/static-debian12:latest"
    "ubuntu:24.04"
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
        # **整数 MB にしない。** 2.76MB も 2.11MB も「2」になり、
        # distroless との比較ができなくなる（2026-10-11 に修正）。
        # 単位は docker images と揃えて 10 進 MB。
        size_mb=$(awk -v b="$size_bytes" 'BEGIN { printf "%.2f", b / 1000 / 1000 }')
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

    # Check if this is a Distroless image (no executables)
    if [[ "$image" == *"distroless"* ]]; then
        log_warning "$image: Skipped (Distroless images have no executables for testing)"
        startup_times["$image"]=-1  # -1 indicates N/A
        continue
    fi

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

    # Check if this is a Distroless image (no executables)
    if [[ "$image" == *"distroless"* ]]; then
        log_warning "$image: Skipped (Distroless images have no executables for testing)"
        memory_usage["$image"]=-1  # -1 indicates N/A
        continue
    fi

    log_info "Testing $image..."

    # Run container in background
    # Try different methods depending on image type
    container_id="bench-mem-$$"
    started=false

    # Standard images with shell - try different sleep paths
    if docker run -d --name "$container_id" "$image" sleep 60 > /dev/null 2>&1; then
        started=true
    elif docker run -d --name "$container_id" "$image" /bin/sleep 60 > /dev/null 2>&1; then
        started=true
    elif docker run -d --name "$container_id" "$image" /busybox/sleep 60 > /dev/null 2>&1; then
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

    # **KB で持つ。** 2026-10-11 まで MB 小数1桁に丸めていたため、
    # Kimigayo 232KB・Alpine 280KB・Ubuntu 316KB がすべて「0.2 / 0.3」に
    # なって区別が付かなかった（benchmark-memory.sh と同じ誤り）。
    #
    # `docker stats` はコンテナ起動直後に `0B` を返すことがある。
    # その標本を 0 として記録すると「最小メモリ」の判定が壊れるので、
    # 読めるまで数回試す。
    mem_kb=0
    for _attempt in 1 2 3 4 5; do
        mem_raw=$(docker stats --no-stream --format "{{.MemUsage}}" "$container_id" 2>/dev/null | awk '{print $1}')
        mem_kb=$(awk -v v="$mem_raw" 'BEGIN {
            if (v ~ /GiB$/)      { sub(/GiB$/, "", v); printf "%.0f", v * 1024 * 1024 }
            else if (v ~ /MiB$/) { sub(/MiB$/, "", v); printf "%.0f", v * 1024 }
            else if (v ~ /KiB$/) { sub(/KiB$/, "", v); printf "%.0f", v }
            else if (v ~ /B$/)   { sub(/B$/, "", v);   printf "%.0f", v / 1024 }
            else                 { printf "0" }
        }')
        [ "${mem_kb:-0}" -gt 0 ] 2>/dev/null && break
        sleep 1
    done

    if [ "${mem_kb:-0}" -le 0 ] 2>/dev/null; then
        log_warning "$image: unable to read memory usage (last value: ${mem_raw:-none})"
        mem_kb=0
    fi

    memory_usage["$image"]=$mem_kb

    docker rm -f "$container_id" > /dev/null 2>&1

    log_result "$image: ${memory_usage[$image]} KB"
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

    # Convert -1 to "N/A" for JSON output
    startup_val="${startup_times[$image]:-0}"
    memory_val="${memory_usage[$image]:-0}"
    if [ "$startup_val" = "-1" ]; then
        startup_val="\"N/A\""
    fi
    if [ "$memory_val" = "-1" ]; then
        memory_val="\"N/A\""
    fi

    cat >> "$JSON_FILE" <<EOF
    "$image": {
      "type": "${image_type[$image]:-N/A}",
      "size_mb": ${image_sizes[$image]:-0},
      "startup_ms": $startup_val,
      "memory_kb": $memory_val,
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

| Image | Type | Size (MB) | Startup (ms) | Memory (KB) | Shell | Package Manager |
|-------|------|-----------|--------------|-------------|-------|-----------------|
EOF

for image in "${IMAGES[@]}"; do
    # Convert -1 to N/A for display
    startup_display="${startup_times[$image]:-0}"
    memory_display="${memory_usage[$image]:-0}"
    if [ "$startup_display" = "-1" ]; then
        startup_display="N/A"
    fi
    if [ "$memory_display" = "-1" ]; then
        memory_display="N/A"
    fi
    echo "| $image | ${image_type[$image]:-N/A} | ${image_sizes[$image]:-0} | $startup_display | $memory_display | ${has_shell[$image]:-N/A} | ${has_pkg_manager[$image]:-N/A} |" >> "$MD_FILE"
done

cat >> "$MD_FILE" <<EOF

## Summary

- **Smallest image**: $(for img in "${IMAGES[@]}"; do echo "${image_sizes[$img]:-999999} $img"; done | sort -g | head -1 | awk '{print $2}')
- **Fastest startup**: $(for img in "${IMAGES[@]}"; do val="${startup_times[$img]:-0}"; if [ "$val" != "-1" ] && [ "$val" != "0" ]; then echo "$val $img"; fi; done | sort -n | head -1 | awk '{print $2}')
- **Lowest memory**: $(for img in "${IMAGES[@]}"; do val="${memory_usage[$img]:-0}"; if [ "$val" != "-1" ] && awk "BEGIN {exit !($val > 0)}"; then echo "$val $img"; fi; done | sort -n | head -1 | awk '{print $2}')

**Startup time does not differ between images.** Most of the measured time is
Docker's own container creation, so Ubuntu lands within noise of Kimigayo
despite being ~30x larger. Memory is where the difference shows.

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
