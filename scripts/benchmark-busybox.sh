#!/usr/bin/env bash
#
# BusyBox Command Performance Benchmark Script for Kimigayo OS
# Measures execution speed of commonly used BusyBox commands
#

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${PROJECT_ROOT}/benchmark-results"
ITERATIONS="${BENCHMARK_ITERATIONS:-10}"
IMAGE_NAME="${IMAGE_NAME:-ishinokazuki/kimigayo-os:latest-standard}"
ALPINE_IMAGE="${ALPINE_IMAGE:-alpine:latest}"

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

# Function to calculate speedup
calculate_speedup() {
    local kimigayo_ms=$1
    local alpine_ms=$2
    # Use bc for floating point division
    echo "scale=2; $alpine_ms / $kimigayo_ms" | bc
}

echo ""
log_info "=== BusyBox Command Performance Benchmark ==="
log_info "Kimigayo OS Image: $IMAGE_NAME"
log_info "Alpine Image: $ALPINE_IMAGE"
log_info "Iterations: $ITERATIONS"
log_info "Output: $OUTPUT_DIR"
echo ""

# Ensure images are available
log_info "Ensuring test images are available..."
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    log_error "Image $IMAGE_NAME not found"
    exit 1
fi
if ! docker image inspect "$ALPINE_IMAGE" >/dev/null 2>&1; then
    log_warning "Image $ALPINE_IMAGE not found locally, pulling..."
    docker pull "$ALPINE_IMAGE"
fi
log_success "Images ready"
echo ""

# Benchmark 1: ls - List directory
log_info "1. ls -la /bin (directory listing)"
kimigayo_ls_times=()
alpine_ls_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    time_ms=$(measure_time docker run --rm "$IMAGE_NAME" ls -la /bin)
    kimigayo_ls_times+=("$time_ms")
    time_ms=$(measure_time docker run --rm "$ALPINE_IMAGE" ls -la /bin)
    alpine_ls_times+=("$time_ms")
done
kimigayo_ls_avg=$(calculate_average "${kimigayo_ls_times[@]}")
kimigayo_ls_median=$(calculate_median "${kimigayo_ls_times[@]}")
alpine_ls_avg=$(calculate_average "${alpine_ls_times[@]}")
alpine_ls_median=$(calculate_median "${alpine_ls_times[@]}")
ls_speedup=$(calculate_speedup "$kimigayo_ls_avg" "$alpine_ls_avg")
log_success "ls: Kimigayo avg=${kimigayo_ls_avg}ms, Alpine avg=${alpine_ls_avg}ms, Speedup=${ls_speedup}x"
echo ""

# Benchmark 2: grep - Text search
log_info "2. grep -r 'bin' /etc (recursive text search)"
kimigayo_grep_times=()
alpine_grep_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    time_ms=$(measure_time docker run --rm "$IMAGE_NAME" grep -r 'bin' /etc)
    kimigayo_grep_times+=("$time_ms")
    time_ms=$(measure_time docker run --rm "$ALPINE_IMAGE" grep -r 'bin' /etc)
    alpine_grep_times+=("$time_ms")
done
kimigayo_grep_avg=$(calculate_average "${kimigayo_grep_times[@]}")
kimigayo_grep_median=$(calculate_median "${kimigayo_grep_times[@]}")
alpine_grep_avg=$(calculate_average "${alpine_grep_times[@]}")
alpine_grep_median=$(calculate_median "${alpine_grep_times[@]}")
grep_speedup=$(calculate_speedup "$kimigayo_grep_avg" "$alpine_grep_avg")
log_success "grep: Kimigayo avg=${kimigayo_grep_avg}ms, Alpine avg=${alpine_grep_avg}ms, Speedup=${grep_speedup}x"
echo ""

# Benchmark 3: find - Directory traversal
log_info "3. find /usr -type f (find files)"
kimigayo_find_times=()
alpine_find_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    time_ms=$(measure_time docker run --rm "$IMAGE_NAME" find /usr -type f)
    kimigayo_find_times+=("$time_ms")
    time_ms=$(measure_time docker run --rm "$ALPINE_IMAGE" find /usr -type f)
    alpine_find_times+=("$time_ms")
done
kimigayo_find_avg=$(calculate_average "${kimigayo_find_times[@]}")
kimigayo_find_median=$(calculate_median "${kimigayo_find_times[@]}")
alpine_find_avg=$(calculate_average "${alpine_find_times[@]}")
alpine_find_median=$(calculate_median "${alpine_find_times[@]}")
find_speedup=$(calculate_speedup "$kimigayo_find_avg" "$alpine_find_avg")
log_success "find: Kimigayo avg=${kimigayo_find_avg}ms, Alpine avg=${alpine_find_avg}ms, Speedup=${find_speedup}x"
echo ""

# Benchmark 4: awk - Text processing
log_info "4. awk '{print \$1}' (text processing)"
kimigayo_awk_times=()
alpine_awk_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    time_ms=$(measure_time docker run --rm "$IMAGE_NAME" sh -c 'ls -la /bin | awk "{print \$1}"')
    kimigayo_awk_times+=("$time_ms")
    time_ms=$(measure_time docker run --rm "$ALPINE_IMAGE" sh -c 'ls -la /bin | awk "{print \$1}"')
    alpine_awk_times+=("$time_ms")
done
kimigayo_awk_avg=$(calculate_average "${kimigayo_awk_times[@]}")
kimigayo_awk_median=$(calculate_median "${kimigayo_awk_times[@]}")
alpine_awk_avg=$(calculate_average "${alpine_awk_times[@]}")
alpine_awk_median=$(calculate_median "${alpine_awk_times[@]}")
awk_speedup=$(calculate_speedup "$kimigayo_awk_avg" "$alpine_awk_avg")
log_success "awk: Kimigayo avg=${kimigayo_awk_avg}ms, Alpine avg=${alpine_awk_avg}ms, Speedup=${awk_speedup}x"
echo ""

# Benchmark 5: sort - Data sorting
log_info "5. sort (data sorting)"
kimigayo_sort_times=()
alpine_sort_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    time_ms=$(measure_time docker run --rm "$IMAGE_NAME" sh -c 'ls -la /bin | sort')
    kimigayo_sort_times+=("$time_ms")
    time_ms=$(measure_time docker run --rm "$ALPINE_IMAGE" sh -c 'ls -la /bin | sort')
    alpine_sort_times+=("$time_ms")
done
kimigayo_sort_avg=$(calculate_average "${kimigayo_sort_times[@]}")
kimigayo_sort_median=$(calculate_median "${kimigayo_sort_times[@]}")
alpine_sort_avg=$(calculate_average "${alpine_sort_times[@]}")
alpine_sort_median=$(calculate_median "${alpine_sort_times[@]}")
sort_speedup=$(calculate_speedup "$kimigayo_sort_avg" "$alpine_sort_avg")
log_success "sort: Kimigayo avg=${kimigayo_sort_avg}ms, Alpine avg=${alpine_sort_avg}ms, Speedup=${sort_speedup}x"
echo ""

# Benchmark 6: cat - File reading
log_info "6. cat /etc/passwd (file reading)"
kimigayo_cat_times=()
alpine_cat_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    time_ms=$(measure_time docker run --rm "$IMAGE_NAME" cat /etc/passwd)
    kimigayo_cat_times+=("$time_ms")
    time_ms=$(measure_time docker run --rm "$ALPINE_IMAGE" cat /etc/passwd)
    alpine_cat_times+=("$time_ms")
done
kimigayo_cat_avg=$(calculate_average "${kimigayo_cat_times[@]}")
kimigayo_cat_median=$(calculate_median "${kimigayo_cat_times[@]}")
alpine_cat_avg=$(calculate_average "${alpine_cat_times[@]}")
alpine_cat_median=$(calculate_median "${alpine_cat_times[@]}")
cat_speedup=$(calculate_speedup "$kimigayo_cat_avg" "$alpine_cat_avg")
log_success "cat: Kimigayo avg=${kimigayo_cat_avg}ms, Alpine avg=${alpine_cat_avg}ms, Speedup=${cat_speedup}x"
echo ""

# Benchmark 7: wc - Word count
log_info "7. wc -l (line counting)"
kimigayo_wc_times=()
alpine_wc_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    time_ms=$(measure_time docker run --rm "$IMAGE_NAME" sh -c 'ls -laR /bin | wc -l')
    kimigayo_wc_times+=("$time_ms")
    time_ms=$(measure_time docker run --rm "$ALPINE_IMAGE" sh -c 'ls -laR /bin | wc -l')
    alpine_wc_times+=("$time_ms")
done
kimigayo_wc_avg=$(calculate_average "${kimigayo_wc_times[@]}")
kimigayo_wc_median=$(calculate_median "${kimigayo_wc_times[@]}")
alpine_wc_avg=$(calculate_average "${alpine_wc_times[@]}")
alpine_wc_median=$(calculate_median "${alpine_wc_times[@]}")
wc_speedup=$(calculate_speedup "$kimigayo_wc_avg" "$alpine_wc_avg")
log_success "wc: Kimigayo avg=${kimigayo_wc_avg}ms, Alpine avg=${alpine_wc_avg}ms, Speedup=${wc_speedup}x"
echo ""

# Benchmark 8: head/tail - Partial file reading
log_info "8. head -n 10 (partial file reading)"
kimigayo_head_times=()
alpine_head_times=()
for i in $(seq 1 "$ITERATIONS"); do
    log_info "  Iteration $i/$ITERATIONS..."
    time_ms=$(measure_time docker run --rm "$IMAGE_NAME" sh -c 'ls -laR /bin | head -n 10')
    kimigayo_head_times+=("$time_ms")
    time_ms=$(measure_time docker run --rm "$ALPINE_IMAGE" sh -c 'ls -laR /bin | head -n 10')
    alpine_head_times+=("$time_ms")
done
kimigayo_head_avg=$(calculate_average "${kimigayo_head_times[@]}")
kimigayo_head_median=$(calculate_median "${kimigayo_head_times[@]}")
alpine_head_avg=$(calculate_average "${alpine_head_times[@]}")
alpine_head_median=$(calculate_median "${alpine_head_times[@]}")
head_speedup=$(calculate_speedup "$kimigayo_head_avg" "$alpine_head_avg")
log_success "head: Kimigayo avg=${kimigayo_head_avg}ms, Alpine avg=${alpine_head_avg}ms, Speedup=${head_speedup}x"
echo ""

# Generate summary
log_info "=== Benchmark Summary ==="
echo ""
printf "%-20s %15s %15s %15s %15s %12s\n" "Command" "Kimigayo (ms)" "Alpine (ms)" "K Median" "A Median" "Speedup"
printf "%-20s %15s %15s %15s %15s %12s\n" "--------------------" "---------------" "---------------" "---------------" "---------------" "------------"
printf "%-20s %15d %15d %15d %15d %12s\n" "ls" "$kimigayo_ls_avg" "$alpine_ls_avg" "$kimigayo_ls_median" "$alpine_ls_median" "${ls_speedup}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "grep" "$kimigayo_grep_avg" "$alpine_grep_avg" "$kimigayo_grep_median" "$alpine_grep_median" "${grep_speedup}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "find" "$kimigayo_find_avg" "$alpine_find_avg" "$kimigayo_find_median" "$alpine_find_median" "${find_speedup}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "awk" "$kimigayo_awk_avg" "$alpine_awk_avg" "$kimigayo_awk_median" "$alpine_awk_median" "${awk_speedup}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "sort" "$kimigayo_sort_avg" "$alpine_sort_avg" "$kimigayo_sort_median" "$alpine_sort_median" "${sort_speedup}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "cat" "$kimigayo_cat_avg" "$alpine_cat_avg" "$kimigayo_cat_median" "$alpine_cat_median" "${cat_speedup}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "wc" "$kimigayo_wc_avg" "$alpine_wc_avg" "$kimigayo_wc_median" "$alpine_wc_median" "${wc_speedup}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "head" "$kimigayo_head_avg" "$alpine_head_avg" "$kimigayo_head_median" "$alpine_head_median" "${head_speedup}x"
echo ""

# Save results to JSON (fixed filename, overwrite mode)
json_file="${OUTPUT_DIR}/busybox.json"
cat > "$json_file" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "kimigayo_image": "$IMAGE_NAME",
  "alpine_image": "$ALPINE_IMAGE",
  "iterations": $ITERATIONS,
  "results": {
    "ls": {
      "kimigayo_avg_ms": $kimigayo_ls_avg,
      "kimigayo_median_ms": $kimigayo_ls_median,
      "alpine_avg_ms": $alpine_ls_avg,
      "alpine_median_ms": $alpine_ls_median,
      "speedup": $ls_speedup,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_ls_times[*]}")]
    },
    "grep": {
      "kimigayo_avg_ms": $kimigayo_grep_avg,
      "kimigayo_median_ms": $kimigayo_grep_median,
      "alpine_avg_ms": $alpine_grep_avg,
      "alpine_median_ms": $alpine_grep_median,
      "speedup": $grep_speedup,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_grep_times[*]}")]
    },
    "find": {
      "kimigayo_avg_ms": $kimigayo_find_avg,
      "kimigayo_median_ms": $kimigayo_find_median,
      "alpine_avg_ms": $alpine_find_avg,
      "alpine_median_ms": $alpine_find_median,
      "speedup": $find_speedup,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_find_times[*]}")]
    },
    "awk": {
      "kimigayo_avg_ms": $kimigayo_awk_avg,
      "kimigayo_median_ms": $kimigayo_awk_median,
      "alpine_avg_ms": $alpine_awk_avg,
      "alpine_median_ms": $alpine_awk_median,
      "speedup": $awk_speedup,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_awk_times[*]}")]
    },
    "sort": {
      "kimigayo_avg_ms": $kimigayo_sort_avg,
      "kimigayo_median_ms": $kimigayo_sort_median,
      "alpine_avg_ms": $alpine_sort_avg,
      "alpine_median_ms": $alpine_sort_median,
      "speedup": $sort_speedup,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_sort_times[*]}")]
    },
    "cat": {
      "kimigayo_avg_ms": $kimigayo_cat_avg,
      "kimigayo_median_ms": $kimigayo_cat_median,
      "alpine_avg_ms": $alpine_cat_avg,
      "alpine_median_ms": $alpine_cat_median,
      "speedup": $cat_speedup,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_cat_times[*]}")]
    },
    "wc": {
      "kimigayo_avg_ms": $kimigayo_wc_avg,
      "kimigayo_median_ms": $kimigayo_wc_median,
      "alpine_avg_ms": $alpine_wc_avg,
      "alpine_median_ms": $alpine_wc_median,
      "speedup": $wc_speedup,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_wc_times[*]}")]
    },
    "head": {
      "kimigayo_avg_ms": $kimigayo_head_avg,
      "kimigayo_median_ms": $kimigayo_head_median,
      "alpine_avg_ms": $alpine_head_avg,
      "alpine_median_ms": $alpine_head_median,
      "speedup": $head_speedup,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_head_times[*]}")]
    }
  }
}
EOF

log_success "Results saved to: $json_file"
echo ""

# Save text summary (fixed filename, overwrite mode)
txt_file="${OUTPUT_DIR}/busybox.txt"
{
    echo "BusyBox Command Performance Benchmark Results"
    echo "=============================================="
    echo ""
    echo "Kimigayo OS Image: $IMAGE_NAME"
    echo "Alpine Image: $ALPINE_IMAGE"
    echo "Date: $(date)"
    echo "Iterations: $ITERATIONS"
    echo ""
    echo "Results (all times in milliseconds):"
    echo ""
    printf "%-20s %15s %15s %15s %15s %12s\n" "Command" "Kimigayo Avg" "Alpine Avg" "K Median" "A Median" "Speedup"
    printf "%-20s %15s %15s %15s %15s %12s\n" "--------------------" "---------------" "---------------" "---------------" "---------------" "------------"
    printf "%-20s %15d %15d %15d %15d %12s\n" "ls" "$kimigayo_ls_avg" "$alpine_ls_avg" "$kimigayo_ls_median" "$alpine_ls_median" "${ls_speedup}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "grep" "$kimigayo_grep_avg" "$alpine_grep_avg" "$kimigayo_grep_median" "$alpine_grep_median" "${grep_speedup}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "find" "$kimigayo_find_avg" "$alpine_find_avg" "$kimigayo_find_median" "$alpine_find_median" "${find_speedup}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "awk" "$kimigayo_awk_avg" "$alpine_awk_avg" "$kimigayo_awk_median" "$alpine_awk_median" "${awk_speedup}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "sort" "$kimigayo_sort_avg" "$alpine_sort_avg" "$kimigayo_sort_median" "$alpine_sort_median" "${sort_speedup}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "cat" "$kimigayo_cat_avg" "$alpine_cat_avg" "$kimigayo_cat_median" "$alpine_cat_median" "${cat_speedup}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "wc" "$kimigayo_wc_avg" "$alpine_wc_avg" "$kimigayo_wc_median" "$alpine_wc_median" "${wc_speedup}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "head" "$kimigayo_head_avg" "$alpine_head_avg" "$kimigayo_head_median" "$alpine_head_median" "${head_speedup}x"
} > "$txt_file"

log_success "Summary saved to: $txt_file"
echo ""

log_success "=== Benchmark Complete ==="
log_info "Results directory: $OUTPUT_DIR"
