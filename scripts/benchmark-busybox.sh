#!/usr/bin/env bash
#
# BusyBox Command Performance Benchmark Script for Kimigayo OS
# Measures execution speed of commonly used BusyBox commands
#

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/json.sh
source "${PROJECT_ROOT}/scripts/lib/json.sh"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/benchmark-results}"
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

# Function to calculate the ratio Alpine / Kimigayo (> 1.00 = Kimigayo faster)
#
# **比は中央値どうしで取る。** README・CLAUDE.md の「0.97〜1.02x」は
# 中央値の比。2026-10-13 まで平均の比を "Speedup" と表示しており、
# 同じ名前で別の値を指していた（docker run の外れ値に平均が引っ張られる）。
# JSON には平均の比も ratio_avg として残す。"speedup" は
# benchmark-report.sh など既存の読み手のための別名で、ratio_median と同じ値。
calculate_ratio() {
    local kimigayo_ms=$1
    local alpine_ms=$2
    # **Do not use `bc` here.** `echo "scale=2; 742/772" | bc` prints `.96`
    # with no leading zero, and this value goes straight into the JSON as
    # `"speedup": .96`, which is not valid JSON - the whole file becomes
    # unparseable (found 2026-10-11). awk's printf always emits `0.96`.
    awk -v a="$alpine_ms" -v k="$kimigayo_ms" 'BEGIN {
        if (k + 0 == 0) { printf "0.00" } else { printf "%.2f", a / k }
    }'
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
    log_warning "Image $IMAGE_NAME not found locally, pulling..."
    docker pull "$IMAGE_NAME"
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
ls_ratio=$(calculate_ratio "$kimigayo_ls_median" "$alpine_ls_median")
ls_ratio_avg=$(calculate_ratio "$kimigayo_ls_avg" "$alpine_ls_avg")
log_success "ls: Kimigayo median=${kimigayo_ls_median}ms, Alpine median=${alpine_ls_median}ms, ratio (Alpine/Kimigayo, median)=${ls_ratio}x"
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
grep_ratio=$(calculate_ratio "$kimigayo_grep_median" "$alpine_grep_median")
grep_ratio_avg=$(calculate_ratio "$kimigayo_grep_avg" "$alpine_grep_avg")
log_success "grep: Kimigayo median=${kimigayo_grep_median}ms, Alpine median=${alpine_grep_median}ms, ratio (Alpine/Kimigayo, median)=${grep_ratio}x"
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
find_ratio=$(calculate_ratio "$kimigayo_find_median" "$alpine_find_median")
find_ratio_avg=$(calculate_ratio "$kimigayo_find_avg" "$alpine_find_avg")
log_success "find: Kimigayo median=${kimigayo_find_median}ms, Alpine median=${alpine_find_median}ms, ratio (Alpine/Kimigayo, median)=${find_ratio}x"
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
awk_ratio=$(calculate_ratio "$kimigayo_awk_median" "$alpine_awk_median")
awk_ratio_avg=$(calculate_ratio "$kimigayo_awk_avg" "$alpine_awk_avg")
log_success "awk: Kimigayo median=${kimigayo_awk_median}ms, Alpine median=${alpine_awk_median}ms, ratio (Alpine/Kimigayo, median)=${awk_ratio}x"
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
sort_ratio=$(calculate_ratio "$kimigayo_sort_median" "$alpine_sort_median")
sort_ratio_avg=$(calculate_ratio "$kimigayo_sort_avg" "$alpine_sort_avg")
log_success "sort: Kimigayo median=${kimigayo_sort_median}ms, Alpine median=${alpine_sort_median}ms, ratio (Alpine/Kimigayo, median)=${sort_ratio}x"
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
cat_ratio=$(calculate_ratio "$kimigayo_cat_median" "$alpine_cat_median")
cat_ratio_avg=$(calculate_ratio "$kimigayo_cat_avg" "$alpine_cat_avg")
log_success "cat: Kimigayo median=${kimigayo_cat_median}ms, Alpine median=${alpine_cat_median}ms, ratio (Alpine/Kimigayo, median)=${cat_ratio}x"
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
wc_ratio=$(calculate_ratio "$kimigayo_wc_median" "$alpine_wc_median")
wc_ratio_avg=$(calculate_ratio "$kimigayo_wc_avg" "$alpine_wc_avg")
log_success "wc: Kimigayo median=${kimigayo_wc_median}ms, Alpine median=${alpine_wc_median}ms, ratio (Alpine/Kimigayo, median)=${wc_ratio}x"
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
head_ratio=$(calculate_ratio "$kimigayo_head_median" "$alpine_head_median")
head_ratio_avg=$(calculate_ratio "$kimigayo_head_avg" "$alpine_head_avg")
log_success "head: Kimigayo median=${kimigayo_head_median}ms, Alpine median=${alpine_head_median}ms, ratio (Alpine/Kimigayo, median)=${head_ratio}x"
echo ""

# Generate summary
log_info "=== Benchmark Summary ==="
echo ""
printf "%-20s %15s %15s %15s %15s %12s\n" "Command" "Kimigayo Avg" "Alpine Avg" "K Median" "A Median" "Ratio(med)"
printf "%-20s %15s %15s %15s %15s %12s\n" "--------------------" "---------------" "---------------" "---------------" "---------------" "------------"
printf "%-20s %15d %15d %15d %15d %12s\n" "ls" "$kimigayo_ls_avg" "$alpine_ls_avg" "$kimigayo_ls_median" "$alpine_ls_median" "${ls_ratio}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "grep" "$kimigayo_grep_avg" "$alpine_grep_avg" "$kimigayo_grep_median" "$alpine_grep_median" "${grep_ratio}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "find" "$kimigayo_find_avg" "$alpine_find_avg" "$kimigayo_find_median" "$alpine_find_median" "${find_ratio}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "awk" "$kimigayo_awk_avg" "$alpine_awk_avg" "$kimigayo_awk_median" "$alpine_awk_median" "${awk_ratio}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "sort" "$kimigayo_sort_avg" "$alpine_sort_avg" "$kimigayo_sort_median" "$alpine_sort_median" "${sort_ratio}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "cat" "$kimigayo_cat_avg" "$alpine_cat_avg" "$kimigayo_cat_median" "$alpine_cat_median" "${cat_ratio}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "wc" "$kimigayo_wc_avg" "$alpine_wc_avg" "$kimigayo_wc_median" "$alpine_wc_median" "${wc_ratio}x"
printf "%-20s %15d %15d %15d %15d %12s\n" "head" "$kimigayo_head_avg" "$alpine_head_avg" "$kimigayo_head_median" "$alpine_head_median" "${head_ratio}x"
echo ""
echo "Ratio(med) = Alpine median / Kimigayo median (> 1.00 means Kimigayo is faster)"
echo ""

# Save results to JSON (fixed filename, overwrite mode)
json_file="${OUTPUT_DIR}/busybox.json"
cat > "$json_file" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "kimigayo_image": "$IMAGE_NAME",
  "alpine_image": "$ALPINE_IMAGE",
  "iterations": $ITERATIONS,
  "ratio_definition": "ratio_median = alpine_median_ms / kimigayo_median_ms; ratio_avg = alpine_avg_ms / kimigayo_avg_ms; speedup = ratio_median (alias kept for existing readers). > 1.00 means Kimigayo is faster",
  "results": {
    "ls": {
      "kimigayo_avg_ms": $kimigayo_ls_avg,
      "kimigayo_median_ms": $kimigayo_ls_median,
      "alpine_avg_ms": $alpine_ls_avg,
      "alpine_median_ms": $alpine_ls_median,
      "ratio_median": $ls_ratio,
      "ratio_avg": $ls_ratio_avg,
      "speedup": $ls_ratio,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_ls_times[*]}")]
    },
    "grep": {
      "kimigayo_avg_ms": $kimigayo_grep_avg,
      "kimigayo_median_ms": $kimigayo_grep_median,
      "alpine_avg_ms": $alpine_grep_avg,
      "alpine_median_ms": $alpine_grep_median,
      "ratio_median": $grep_ratio,
      "ratio_avg": $grep_ratio_avg,
      "speedup": $grep_ratio,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_grep_times[*]}")]
    },
    "find": {
      "kimigayo_avg_ms": $kimigayo_find_avg,
      "kimigayo_median_ms": $kimigayo_find_median,
      "alpine_avg_ms": $alpine_find_avg,
      "alpine_median_ms": $alpine_find_median,
      "ratio_median": $find_ratio,
      "ratio_avg": $find_ratio_avg,
      "speedup": $find_ratio,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_find_times[*]}")]
    },
    "awk": {
      "kimigayo_avg_ms": $kimigayo_awk_avg,
      "kimigayo_median_ms": $kimigayo_awk_median,
      "alpine_avg_ms": $alpine_awk_avg,
      "alpine_median_ms": $alpine_awk_median,
      "ratio_median": $awk_ratio,
      "ratio_avg": $awk_ratio_avg,
      "speedup": $awk_ratio,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_awk_times[*]}")]
    },
    "sort": {
      "kimigayo_avg_ms": $kimigayo_sort_avg,
      "kimigayo_median_ms": $kimigayo_sort_median,
      "alpine_avg_ms": $alpine_sort_avg,
      "alpine_median_ms": $alpine_sort_median,
      "ratio_median": $sort_ratio,
      "ratio_avg": $sort_ratio_avg,
      "speedup": $sort_ratio,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_sort_times[*]}")]
    },
    "cat": {
      "kimigayo_avg_ms": $kimigayo_cat_avg,
      "kimigayo_median_ms": $kimigayo_cat_median,
      "alpine_avg_ms": $alpine_cat_avg,
      "alpine_median_ms": $alpine_cat_median,
      "ratio_median": $cat_ratio,
      "ratio_avg": $cat_ratio_avg,
      "speedup": $cat_ratio,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_cat_times[*]}")]
    },
    "wc": {
      "kimigayo_avg_ms": $kimigayo_wc_avg,
      "kimigayo_median_ms": $kimigayo_wc_median,
      "alpine_avg_ms": $alpine_wc_avg,
      "alpine_median_ms": $alpine_wc_median,
      "ratio_median": $wc_ratio,
      "ratio_avg": $wc_ratio_avg,
      "speedup": $wc_ratio,
      "kimigayo_samples": [$(IFS=,; echo "${kimigayo_wc_times[*]}")]
    },
    "head": {
      "kimigayo_avg_ms": $kimigayo_head_avg,
      "kimigayo_median_ms": $kimigayo_head_median,
      "alpine_avg_ms": $alpine_head_avg,
      "alpine_median_ms": $alpine_head_median,
      "ratio_median": $head_ratio,
      "ratio_avg": $head_ratio_avg,
      "speedup": $head_ratio,
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
    printf "%-20s %15s %15s %15s %15s %12s\n" "Command" "Kimigayo Avg" "Alpine Avg" "K Median" "A Median" "Ratio(med)"
    printf "%-20s %15s %15s %15s %15s %12s\n" "--------------------" "---------------" "---------------" "---------------" "---------------" "------------"
    printf "%-20s %15d %15d %15d %15d %12s\n" "ls" "$kimigayo_ls_avg" "$alpine_ls_avg" "$kimigayo_ls_median" "$alpine_ls_median" "${ls_ratio}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "grep" "$kimigayo_grep_avg" "$alpine_grep_avg" "$kimigayo_grep_median" "$alpine_grep_median" "${grep_ratio}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "find" "$kimigayo_find_avg" "$alpine_find_avg" "$kimigayo_find_median" "$alpine_find_median" "${find_ratio}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "awk" "$kimigayo_awk_avg" "$alpine_awk_avg" "$kimigayo_awk_median" "$alpine_awk_median" "${awk_ratio}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "sort" "$kimigayo_sort_avg" "$alpine_sort_avg" "$kimigayo_sort_median" "$alpine_sort_median" "${sort_ratio}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "cat" "$kimigayo_cat_avg" "$alpine_cat_avg" "$kimigayo_cat_median" "$alpine_cat_median" "${cat_ratio}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "wc" "$kimigayo_wc_avg" "$alpine_wc_avg" "$kimigayo_wc_median" "$alpine_wc_median" "${wc_ratio}x"
    printf "%-20s %15d %15d %15d %15d %12s\n" "head" "$kimigayo_head_avg" "$alpine_head_avg" "$kimigayo_head_median" "$alpine_head_median" "${head_ratio}x"
    echo ""
    echo "Ratio(med) = Alpine median / Kimigayo median (> 1.00 means Kimigayo is faster)"
} > "$txt_file"

log_success "Summary saved to: $txt_file"
echo ""

kimigayo_validate_json "$json_file" || exit 1
log_success "JSON is valid: $json_file"
echo ""

log_success "=== Benchmark Complete ==="
log_info "Results directory: $OUTPUT_DIR"
