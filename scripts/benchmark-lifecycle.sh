#!/usr/bin/env bash
#
# Container Lifecycle Benchmark Script for Kimigayo OS
# Measures container startup, stop, restart performance
#

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${PROJECT_ROOT}/benchmark-results"
ITERATIONS="${BENCHMARK_ITERATIONS:-10}"
IMAGE_NAME="${IMAGE_NAME:-ishinokazuki/kimigayo-os:latest-standard}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Function to measure time in milliseconds
measure_time() {
    local start_time
    local end_time
    start_time=$(date +%s%N)
    "$@" >/dev/null 2>&1
    end_time=$(date +%s%N)
    echo $(( (end_time - start_time) / 1000000 ))
}

# Function to calculate average
calculate_average() {
    local sum=0
    local count=0
    for val in "$@"; do
        sum=$((sum + val))
        count=$((count + 1))
    done
    echo $((sum / count))
}

# Function to calculate median
calculate_median() {
    # Sort values and store in array (Bash 3.2 compatible)
    local sorted_str
    sorted_str=$(printf '%s\n' "$@" | sort -n | tr '\n' ' ')
    # shellcheck disable=SC2206
    local sorted=($sorted_str)
    local count=${#sorted[@]}
    local mid=$((count / 2))
    if [ $((count % 2)) -eq 0 ]; then
        echo $(( (sorted[mid-1] + sorted[mid]) / 2 ))
    else
        echo "${sorted[mid]}"
    fi
}

# Function to calculate standard deviation
calculate_stddev() {
    local avg=$1
    shift
    local sum_sq=0
    local count=0
    for val in "$@"; do
        local diff=$((val - avg))
        sum_sq=$((sum_sq + diff * diff))
        count=$((count + 1))
    done
    echo "scale=2; sqrt($sum_sq / $count)" | bc
}

echo ""
log_info "=== Container Lifecycle Benchmark ==="
log_info "Image: $IMAGE_NAME"
log_info "Iterations: $ITERATIONS"
log_info "Output: $OUTPUT_DIR"
echo ""

# Ensure image is available
log_info "Ensuring test image is available..."
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    log_warning "Image $IMAGE_NAME not found locally, pulling..."
    docker pull "$IMAGE_NAME"
fi
log_success "Image ready"
echo ""

# 1. Run-to-completion benchmark
log_info "1. Run-to-completion time (container start → execute → exit)"
run_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    time_ms=$(measure_time docker run --rm "$IMAGE_NAME" /bin/sh -c "echo 'test' && sleep 0.1")
    run_times+=("$time_ms")
done
run_avg=$(calculate_average "${run_times[@]}")
run_median=$(calculate_median "${run_times[@]}")
log_success "Run-to-completion: avg=${run_avg}ms, median=${run_median}ms"
echo ""

# 2. Container start time (without execution)
log_info "2. Container start time (create → start)"
start_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    container_id=$(docker create "$IMAGE_NAME" /bin/sh -c "exit 0")
    time_ms=$(measure_time docker start -a "$container_id")
    docker rm "$container_id" >/dev/null 2>&1
    start_times+=("$time_ms")
done
start_avg=$(calculate_average "${start_times[@]}")
start_median=$(calculate_median "${start_times[@]}")
log_success "Container start: avg=${start_avg}ms, median=${start_median}ms"
echo ""

# 3. Container stop time
log_info "3. Container stop time"
stop_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    container_id=$(docker run -d "$IMAGE_NAME" sleep 60)
    sleep 0.1  # Let container fully start
    time_ms=$(measure_time docker stop "$container_id")
    docker rm "$container_id" >/dev/null 2>&1
    stop_times+=("$time_ms")
done
stop_avg=$(calculate_average "${stop_times[@]}")
stop_median=$(calculate_median "${stop_times[@]}")
log_success "Container stop: avg=${stop_avg}ms, median=${stop_median}ms"
echo ""

# 4. Container restart time
log_info "4. Container restart time"
restart_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    container_id=$(docker run -d "$IMAGE_NAME" sleep 60)
    sleep 0.1
    time_ms=$(measure_time docker restart "$container_id")
    docker rm -f "$container_id" >/dev/null 2>&1
    restart_times+=("$time_ms")
done
restart_avg=$(calculate_average "${restart_times[@]}")
restart_median=$(calculate_median "${restart_times[@]}")
log_success "Container restart: avg=${restart_avg}ms, median=${restart_median}ms"
echo ""

# 5. Container cleanup time
log_info "5. Container cleanup time (rm -f)"
cleanup_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    container_id=$(docker run -d "$IMAGE_NAME" sleep 60)
    time_ms=$(measure_time docker rm -f "$container_id")
    cleanup_times+=("$time_ms")
done
cleanup_avg=$(calculate_average "${cleanup_times[@]}")
cleanup_median=$(calculate_median "${cleanup_times[@]}")
log_success "Container cleanup: avg=${cleanup_avg}ms, median=${cleanup_median}ms"
echo ""

# 6. Image inspection (layer info)
log_info "6. Image layer information"
image_size=$(docker inspect "$IMAGE_NAME" --format '{{.Size}}')
layer_count=$(docker inspect "$IMAGE_NAME" --format '{{len .RootFS.Layers}}')
image_size_mb=$(echo "scale=2; $image_size / 1048576" | bc)
log_success "Image size: ${image_size_mb}MB, Layers: $layer_count"
echo ""

# 7. Pull time (if cache can be cleared)
log_info "7. Image pull time (warm cache)"
pull_times=()
for i in $(seq 1 3); do  # Only 3 iterations for pull test
    log_info "  Iteration $i/3..."
    time_ms=$(measure_time docker pull "$IMAGE_NAME")
    pull_times+=("$time_ms")
done
pull_avg=$(calculate_average "${pull_times[@]}")
pull_median=$(calculate_median "${pull_times[@]}")
log_success "Image pull (warm): avg=${pull_avg}ms, median=${pull_median}ms"
echo ""

# Generate summary
log_info "=== Benchmark Summary ==="
echo ""
printf "%-35s %15s %15s\n" "Metric" "Average (ms)" "Median (ms)"
printf "%-35s %15s %15s\n" "-----------------------------------" "---------------" "---------------"
printf "%-35s %15d %15d\n" "Run-to-completion" "$run_avg" "$run_median"
printf "%-35s %15d %15d\n" "Container start" "$start_avg" "$start_median"
printf "%-35s %15d %15d\n" "Container stop" "$stop_avg" "$stop_median"
printf "%-35s %15d %15d\n" "Container restart" "$restart_avg" "$restart_median"
printf "%-35s %15d %15d\n" "Container cleanup" "$cleanup_avg" "$cleanup_median"
printf "%-35s %15d %15d\n" "Image pull (warm cache)" "$pull_avg" "$pull_median"
echo ""
printf "%-35s %15s\n" "Image size (MB)" "$image_size_mb"
printf "%-35s %15s\n" "Layer count" "$layer_count"
echo ""

# Save results to JSON (fixed filename, overwrite mode)
json_file="${OUTPUT_DIR}/lifecycle.json"
cat > "$json_file" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "image": "$IMAGE_NAME",
  "iterations": $ITERATIONS,
  "results": {
    "run_to_completion": {
      "average_ms": $run_avg,
      "median_ms": $run_median,
      "samples": [$(IFS=,; echo "${run_times[*]}")]
    },
    "container_start": {
      "average_ms": $start_avg,
      "median_ms": $start_median,
      "samples": [$(IFS=,; echo "${start_times[*]}")]
    },
    "container_stop": {
      "average_ms": $stop_avg,
      "median_ms": $stop_median,
      "samples": [$(IFS=,; echo "${stop_times[*]}")]
    },
    "container_restart": {
      "average_ms": $restart_avg,
      "median_ms": $restart_median,
      "samples": [$(IFS=,; echo "${restart_times[*]}")]
    },
    "container_cleanup": {
      "average_ms": $cleanup_avg,
      "median_ms": $cleanup_median,
      "samples": [$(IFS=,; echo "${cleanup_times[*]}")]
    },
    "image_pull_warm": {
      "average_ms": $pull_avg,
      "median_ms": $pull_median,
      "samples": [$(IFS=,; echo "${pull_times[*]}")]
    },
    "image_info": {
      "size_bytes": $image_size,
      "size_mb": $image_size_mb,
      "layer_count": $layer_count
    }
  }
}
EOF

log_success "Results saved to: $json_file"
echo ""

# Save text summary (fixed filename, overwrite mode)
txt_file="${OUTPUT_DIR}/lifecycle.txt"
{
    echo "Container Lifecycle Benchmark Results"
    echo "======================================"
    echo ""
    echo "Image: $IMAGE_NAME"
    echo "Date: $(date)"
    echo "Iterations: $ITERATIONS"
    echo ""
    echo "Results (all times in milliseconds):"
    echo ""
    printf "%-35s %15s %15s\n" "Metric" "Average" "Median"
    printf "%-35s %15s %15s\n" "-----------------------------------" "---------------" "---------------"
    printf "%-35s %15d %15d\n" "Run-to-completion" "$run_avg" "$run_median"
    printf "%-35s %15d %15d\n" "Container start" "$start_avg" "$start_median"
    printf "%-35s %15d %15d\n" "Container stop" "$stop_avg" "$stop_median"
    printf "%-35s %15d %15d\n" "Container restart" "$restart_avg" "$restart_median"
    printf "%-35s %15d %15d\n" "Container cleanup" "$cleanup_avg" "$cleanup_median"
    printf "%-35s %15d %15d\n" "Image pull (warm cache)" "$pull_avg" "$pull_median"
    echo ""
    echo "Image Information:"
    printf "%-35s %15s MB\n" "Size" "$image_size_mb"
    printf "%-35s %15s\n" "Layer count" "$layer_count"
} > "$txt_file"

log_success "Summary saved to: $txt_file"
echo ""

log_success "=== Benchmark Complete ==="
log_info "Results directory: $OUTPUT_DIR"
