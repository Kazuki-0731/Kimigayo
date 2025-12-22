#!/bin/bash
# Kimigayo OS - 起動時間ベンチマーク

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# デフォルト設定
ITERATIONS="${ITERATIONS:-10}"
IMAGE="${IMAGE:-ishinokazuki/kimigayo-os:latest}"
OUTPUT_FILE="${OUTPUT_FILE:-benchmark-startup.json}"

echo "Kimigayo OS - 起動時間ベンチマーク"
echo "======================================"
echo "イメージ: $IMAGE"
echo "測定回数: $ITERATIONS"
echo ""

# 起動時間を測定する関数
measure_startup_time() {
    local container_name="benchmark-startup-$$"

    # コンテナ起動時間を測定
    local start_time
    start_time=$(date +%s%N)

    docker run --name "$container_name" --rm -d "$IMAGE" sleep 5 > /dev/null 2>&1

    # コンテナが起動するまで待機
    docker wait "$container_name" > /dev/null 2>&1 || true

    local end_time
    end_time=$(date +%s%N)

    # ナノ秒からミリ秒に変換
    local duration=$(( (end_time - start_time) / 1000000 ))

    echo "$duration"
}

# ウォームアップ（キャッシュを準備）
echo -e "${YELLOW}ウォームアップ中...${NC}"
docker pull "$IMAGE" > /dev/null 2>&1 || true
measure_startup_time > /dev/null 2>&1 || true
echo ""

# ベンチマーク実行
echo -e "${GREEN}ベンチマーク実行中...${NC}"
echo ""

declare -a times=()
total=0

for i in $(seq 1 "$ITERATIONS"); do
    echo -ne "  測定 $i/$ITERATIONS... "

    time=$(measure_startup_time)
    times+=("$time")
    total=$((total + time))

    echo -e "${GREEN}${time}ms${NC}"

    # 少し待機
    sleep 0.5
done

echo ""

# 統計計算
avg=$((total / ITERATIONS))

# 中央値計算（ソート）
mapfile -t sorted < <(printf '%s\n' "${times[@]}" | sort -n)

if [ $((ITERATIONS % 2)) -eq 0 ]; then
    idx1=$((ITERATIONS / 2 - 1))
    idx2=$((ITERATIONS / 2))
    median=$(( (sorted[idx1] + sorted[idx2]) / 2 ))
else
    idx=$((ITERATIONS / 2))
    median=${sorted[$idx]}
fi

min=${sorted[0]}
max=${sorted[$((ITERATIONS - 1))]}

# 結果表示
echo "ベンチマーク結果"
echo "======================================"
echo "平均:   ${avg}ms"
echo "中央値: ${median}ms"
echo "最小:   ${min}ms"
echo "最大:   ${max}ms"
echo ""

# JSON形式で保存
cat > "$OUTPUT_FILE" <<EOF
{
  "benchmark": "startup_time",
  "image": "$IMAGE",
  "iterations": $ITERATIONS,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "results": {
    "average_ms": $avg,
    "median_ms": $median,
    "min_ms": $min,
    "max_ms": $max,
    "all_times_ms": [$(IFS=,; echo "${times[*]}")]
  }
}
EOF

echo -e "${GREEN}✓ 結果を $OUTPUT_FILE に保存しました${NC}"

# CI環境の場合は環境変数にも出力
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "startup_avg_ms=$avg" >> "$GITHUB_OUTPUT"
    echo "startup_median_ms=$median" >> "$GITHUB_OUTPUT"
    echo "startup_min_ms=$min" >> "$GITHUB_OUTPUT"
    echo "startup_max_ms=$max" >> "$GITHUB_OUTPUT"
fi

# 目標値チェック（10秒 = 10000ms以下）
if [ $avg -lt 10000 ]; then
    echo -e "${GREEN}✓ 目標達成: 平均起動時間が10秒以下です${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ 警告: 平均起動時間が10秒を超えています${NC}"
    exit 1
fi
