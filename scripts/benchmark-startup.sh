#!/bin/bash
# Kimigayo OS - 起動時間ベンチマーク

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# デフォルト設定
ITERATIONS="${ITERATIONS:-10}"
IMAGE="${IMAGE:-ishinokazuki/kimigayo-os:latest-standard}"
OUTPUT_FILE="${OUTPUT_FILE:-benchmark-startup.json}"
PLATFORM="${PLATFORM:-}"

# 何を「起動」と呼ぶか。
#   exec … docker run からコンテナの最初のコマンドが走り終わるまで（既定）。
#          イメージの層の準備・コンテナ作成・起動・exec を含む、
#          利用者から見た「使えるようになるまで」の時間。
#   init … OpenRC が default ランレベルを完走するまで。Init を同梱する
#          のが Kimigayo の売りなので、こちらが本来の起動時間。
#
# **コンテナの中で sleep して、その sleep が終わるのを待ってはいけない。**
# 2026-10-10 まで `docker run -d "$IMAGE" sleep 5` + `docker wait` を
# 測っており、正常なイメージほど必ず約 5,600ms になっていた。
# README が長く載せていた 439ms は、この sleep が成立しなかった
# （＝コンテナが即死した）ときの値で、起動時間ではない。
MODE="${MODE:-exec}"

case "$MODE" in
    exec) RUN_CMD=(/bin/true) ;;
    init) RUN_CMD=(/sbin/openrc default) ;;
    *)    echo "MODE は exec か init を指定してください（いまは '$MODE'）" >&2; exit 1 ;;
esac

echo "Kimigayo OS - 起動時間ベンチマーク"
echo "======================================"
echo "イメージ: $IMAGE"
echo "測定回数: $ITERATIONS"
echo "測る対象: $MODE（${RUN_CMD[*]} が終わるまで）"
[ -n "$PLATFORM" ] && echo "platform: $PLATFORM"
echo ""

# 起動時間を測定する関数
measure_startup_time() {
    local start_time end_time duration
    local platform_args=()
    [ -n "$PLATFORM" ] && platform_args=(--platform "$PLATFORM")

    start_time=$(date +%s%N)
    docker run --rm "${platform_args[@]}" "$IMAGE" "${RUN_CMD[@]}" > /dev/null 2>&1
    end_time=$(date +%s%N)

    # ナノ秒からミリ秒に変換
    duration=$(( (end_time - start_time) / 1000000 ))

    echo "$duration"
}

# ウォームアップ（キャッシュを準備）
echo -e "${YELLOW}ウォームアップ中...${NC}"
docker image inspect "$IMAGE" > /dev/null 2>&1 || docker pull "$IMAGE" > /dev/null 2>&1 || true
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
  "mode": "$MODE",
  "measured": "${RUN_CMD[*]}",
  "platform": "${PLATFORM:-default}",
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
