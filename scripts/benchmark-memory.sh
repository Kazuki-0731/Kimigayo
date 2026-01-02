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

echo -e "${BOLD}Kimigayo OS - メモリ使用量ベンチマーク${NC}"
echo "======================================"
echo -e "${BLUE}イメージ:${NC} $IMAGE"
echo -e "${BLUE}測定時間:${NC} ${DURATION}sec"
echo ""

# コンテナ起動
CONTAINER_NAME="benchmark-memory-$$"

echo -e "${YELLOW}コンテナ起動中...${NC}"
docker run --name "$CONTAINER_NAME" -d "$IMAGE" sleep $((DURATION + 10)) > /dev/null

echo -e "${GREEN}メモリ使用量測定中...${NC}"
echo ""

# メモリ使用量を測定
declare -a memory_usage=()
total_memory=0
count=0

for i in $(seq 1 "$DURATION"); do
    # docker statsからメモリ使用量を取得（MB単位）
    mem=$(docker stats --no-stream --format "{{.MemUsage}}" "$CONTAINER_NAME" | awk '{print $1}' | sed 's/MiB//' | sed 's/KiB/0.001/' | sed 's/GiB/*1024/' | bc 2>/dev/null || echo "0")

    # 小数点を整数に変換（bcがない環境対応）
    mem_int=$(echo "$mem" | awk '{printf "%.0f", $1}')

    memory_usage+=("$mem_int")
    total_memory=$((total_memory + mem_int))
    count=$((count + 1))

    echo "  測定中 $i/${DURATION}sec... ${mem_int}MB"

    sleep 1
done

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
echo -e "${BLUE}平均メモリ使用量:${NC}   ${avg}MB"
echo -e "${BLUE}中央値:${NC}             ${median}MB"
echo -e "${BLUE}最小:${NC}               ${min}MB"
echo -e "${BLUE}最大:${NC}               ${max}MB"
echo ""

# JSON形式で保存
cat > "$OUTPUT_FILE" <<EOF
{
  "benchmark": "memory_usage",
  "image": "$IMAGE",
  "duration_seconds": $DURATION,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "results": {
    "average_mb": $avg,
    "median_mb": $median,
    "min_mb": $min,
    "max_mb": $max,
    "samples": $count
  }
}
EOF

echo -e "${GREEN}✓ 結果を $OUTPUT_FILE に保存しました${NC}"

# CI環境の場合は環境変数にも出力
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "memory_avg_mb=$avg" >> "$GITHUB_OUTPUT"
    echo "memory_median_mb=$median" >> "$GITHUB_OUTPUT"
    echo "memory_min_mb=$min" >> "$GITHUB_OUTPUT"
    echo "memory_max_mb=$max" >> "$GITHUB_OUTPUT"
fi

# 目標値チェック（128MB以下）
if [ $avg -lt 128 ]; then
    echo -e "${GREEN}✓ 目標達成: 平均メモリ使用量が128MB以下です${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ 警告: 平均メモリ使用量が128MBを超えています${NC}"
    exit 1
fi
