#!/bin/bash
# Kimigayo OS - メモリ使用量ベンチマーク

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# デフォルト設定
IMAGE="${IMAGE:-ishinokazuki/kimigayo-os:latest-standard}"
DURATION="${DURATION:-30}"
OUTPUT_FILE="${OUTPUT_FILE:-benchmark-memory.json}"
PLATFORM="${PLATFORM:-}"
# 常駐させるコマンド。Alpine / Ubuntu との比較で揃える必要がある。
IDLE_CMD="${IDLE_CMD:-sleep}"

echo -e "${BOLD}Kimigayo OS - メモリ使用量ベンチマーク${NC}"
echo "======================================"
echo -e "${BLUE}イメージ:${NC} $IMAGE"
echo -e "${BLUE}測定時間:${NC} ${DURATION}sec"
echo ""

# コンテナ起動
CONTAINER_NAME="benchmark-memory-$$"

echo -e "${YELLOW}コンテナ起動中...${NC}"
platform_args=()
[ -n "$PLATFORM" ] && platform_args=(--platform "$PLATFORM")
docker run --name "$CONTAINER_NAME" -d "${platform_args[@]}" "$IMAGE" \
    "$IDLE_CMD" $((DURATION + 10)) > /dev/null

echo -e "${GREEN}メモリ使用量測定中...${NC}"
echo ""

# メモリ使用量を測定
declare -a memory_usage=()
total_memory=0
count=0

# docker stats の "412KiB / 7.653GiB" のような値を KB（1000 B）に直す。
#
# **単位を取り違えると桁が飛ぶ。** 2026-10-10 まで
# `sed 's/KiB/0.001/'` で KiB を置換しており、`512KiB` が `5120.001`
# という無関係な数になっていた。さらに結果を整数 MB に丸めていたため、
# **1MB 未満は 0 になって区別がつかなかった**。
# Kimigayo の常駐は実測 232KB（2026-10-10、arm64）で 1MB を大きく
# 下回るので、MB 単位の整数ではそもそも表現できない。KB で持つ。
to_kb() {
    awk '{
        v = $0
        sub(/[KMGi]*B$/, "", v)
        if ($0 ~ /GiB$/)      printf "%.0f", v * 1024 * 1024
        else if ($0 ~ /MiB$/) printf "%.0f", v * 1024
        else if ($0 ~ /KiB$/) printf "%.0f", v
        else if ($0 ~ /B$/)   printf "%.0f", v / 1024
        else                  printf "0"
    }'
}

# **0 は捨てる。** コンテナ起動直後は docker stats がまだ cgroup の値を
# 拾えず 0B を返すことがある。これを平均に混ぜると実測値が半分近くまで
# 下がる（2026-10-10 に実測: 中央値 232KB に対し平均が 162KB になった）。
skipped=0

for i in $(seq 1 "$DURATION"); do
    raw=$(docker stats --no-stream --format "{{.MemUsage}}" "$CONTAINER_NAME" 2>/dev/null | awk '{print $1}')
    mem_kb=$(printf '%s' "$raw" | to_kb)
    [ -z "$mem_kb" ] && mem_kb=0

    if [ "$mem_kb" -le 0 ]; then
        skipped=$((skipped + 1))
        echo "  測定中 ${i}sec... ${raw:-（取得できず）} → 捨てる"
        sleep 1
        continue
    fi

    memory_usage+=("$mem_kb")
    total_memory=$((total_memory + mem_kb))
    count=$((count + 1))

    echo "  測定中 ${i}sec... ${raw} (${mem_kb}KB)"

    sleep 1
done

if [ "$count" -eq 0 ]; then
    echo "メモリを一度も取得できませんでした（${skipped} 回とも 0）。" >&2
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1
    docker rm "$CONTAINER_NAME" > /dev/null 2>&1
    exit 1
fi

[ "$skipped" -gt 0 ] && echo "  （${skipped} 回ぶんは 0 だったので捨てました）"

echo ""

# コンテナ停止・削除
docker stop "$CONTAINER_NAME" > /dev/null 2>&1
docker rm "$CONTAINER_NAME" > /dev/null 2>&1

# 統計計算
avg=$((total_memory / count))

# ソートして中央値、最小、最大を計算
mapfile -t sorted < <(printf '%s\n' "${memory_usage[@]}" | sort -n)

if [ $((count % 2)) -eq 0 ]; then
    idx1=$((count / 2 - 1))
    idx2=$((count / 2))
    median=$(( (sorted[idx1] + sorted[idx2]) / 2 ))
else
    idx=$((count / 2))
    median=${sorted[$idx]}
fi

min=${sorted[0]}
max=${sorted[$((count - 1))]}

# 結果表示
echo -e "${BOLD}ベンチマーク結果${NC}"
echo "======================================"
echo -e "${BLUE}平均メモリ使用量:${NC}   ${avg}KB"
echo -e "${BLUE}中央値:${NC}             ${median}KB"
echo -e "${BLUE}最小:${NC}               ${min}KB"
echo -e "${BLUE}最大:${NC}               ${max}KB"
echo ""

# JSON形式で保存
cat > "$OUTPUT_FILE" <<EOF
{
  "benchmark": "memory_usage",
  "image": "$IMAGE",
  "platform": "${PLATFORM:-default}",
  "duration_seconds": $DURATION,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "results": {
    "average_kb": $avg,
    "median_kb": $median,
    "min_kb": $min,
    "max_kb": $max,
    "samples": $count,
    "discarded_zero_samples": $skipped
  }
}
EOF

echo -e "${GREEN}✓ 結果を $OUTPUT_FILE に保存しました${NC}"

# CI環境の場合は環境変数にも出力
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "memory_avg_kb=$avg" >> "$GITHUB_OUTPUT"
    echo "memory_median_kb=$median" >> "$GITHUB_OUTPUT"
    echo "memory_min_kb=$min" >> "$GITHUB_OUTPUT"
    echo "memory_max_kb=$max" >> "$GITHUB_OUTPUT"
fi

# 目標値チェック（128MB以下）
if [ $avg -lt 131072 ]; then
    echo -e "${GREEN}✓ 目標達成: 平均メモリ使用量が128MB以下です${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ 警告: 平均メモリ使用量が128MBを超えています${NC}"
    exit 1
fi
