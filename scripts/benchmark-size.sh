#!/bin/bash
# Kimigayo OS - ディスクサイズ比較ベンチマーク

set -e

# Colors
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# デフォルト設定
OUTPUT_FILE="${OUTPUT_FILE:-benchmark-size.json}"

# 比較対象イメージ
declare -A IMAGES=(
    ["Kimigayo Minimal"]="ishinokazuki/kimigayo-os:latest-minimal"
    ["Kimigayo Standard"]="ishinokazuki/kimigayo-os:latest"
    ["Kimigayo Extended"]="ishinokazuki/kimigayo-os:latest-extended"
    ["Alpine Latest"]="alpine:latest"
    ["Alpine 3.19"]="alpine:3.19"
    ["Debian Slim"]="debian:stable-slim"
    ["Ubuntu"]="ubuntu:22.04"
    ["BusyBox"]="busybox:latest"
)

echo -e "${BOLD}Kimigayo OS - ディスクサイズ比較ベンチマーク${NC}"
echo "======================================"
echo ""

# イメージをプル
echo -e "${YELLOW}イメージをプル中...${NC}"
for name in "${!IMAGES[@]}"; do
    image="${IMAGES[$name]}"
    echo -ne "  ${name}... "
    if docker pull "$image" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ (スキップ)${NC}"
        unset IMAGES["$name"]
    fi
done

echo ""

# サイズ測定
echo -e "${GREEN}イメージサイズ測定中...${NC}"
echo ""

declare -A sizes=()
max_name_len=0

for name in "${!IMAGES[@]}"; do
    image="${IMAGES[$name]}"

    # サイズを取得（MB単位）
    size_bytes=$(docker image inspect "$image" --format='{{.Size}}' 2>/dev/null || echo "0")
    size_mb=$((size_bytes / 1024 / 1024))

    sizes["$name"]=$size_mb

    # 最大名前長を記録（表示整形用）
    name_len=${#name}
    if [ $name_len -gt $max_name_len ]; then
        max_name_len=$name_len
    fi
done

# ソート用配列を作成
declare -a sorted_names=()
for name in "${!sizes[@]}"; do
    sorted_names+=("$name")
done

# サイズでソート
IFS=$'\n' sorted_names=($(sort -t: -k2 -n <(
    for name in "${sorted_names[@]}"; do
        echo "${sizes[$name]}:$name"
    done
) | cut -d: -f2-))
unset IFS

# 結果表示
echo -e "${BOLD}ベンチマーク結果（サイズ順）${NC}"
echo "======================================"

# ヘッダー
printf "%-${max_name_len}s  %10s  %10s\n" "イメージ" "サイズ(MB)" "比較"
printf "%s\n" "$(printf '=%.0s' {1..50})"

# Kimigayo Minimalを基準として比較
kimigayo_minimal_size=${sizes["Kimigayo Minimal"]}

for name in "${sorted_names[@]}"; do
    size=${sizes[$name]}

    # 比較率を計算
    if [ "$name" = "Kimigayo Minimal" ]; then
        comparison="(基準)"
    elif [ $kimigayo_minimal_size -gt 0 ]; then
        ratio=$((size * 100 / kimigayo_minimal_size))
        comparison="${ratio}%"
    else
        comparison="-"
    fi

    # 色分け
    if [[ "$name" == Kimigayo* ]]; then
        color=$BLUE
    else
        color=$NC
    fi

    printf "${color}%-${max_name_len}s${NC}  %10d  %10s\n" "$name" "$size" "$comparison"
done

echo ""

# JSON形式で保存
echo "{" > "$OUTPUT_FILE"
echo '  "benchmark": "image_size",' >> "$OUTPUT_FILE"
echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"," >> "$OUTPUT_FILE"
echo '  "results": {' >> "$OUTPUT_FILE"

first=true
for name in "${sorted_names[@]}"; do
    size=${sizes[$name]}

    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$OUTPUT_FILE"
    fi

    # JSON用にエスケープ
    json_name=$(echo "$name" | sed 's/"/\\"/g')
    echo -n "    \"$json_name\": {\"size_mb\": $size, \"image\": \"${IMAGES[$name]}\"}" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"
echo "  }" >> "$OUTPUT_FILE"
echo "}" >> "$OUTPUT_FILE"

echo -e "${GREEN}✓ 結果を $OUTPUT_FILE に保存しました${NC}"

# CI環境の場合は環境変数にも出力
if [ -n "$GITHUB_OUTPUT" ]; then
    echo "kimigayo_minimal_size_mb=${sizes["Kimigayo Minimal"]}" >> "$GITHUB_OUTPUT"
    echo "kimigayo_standard_size_mb=${sizes["Kimigayo Standard"]}" >> "$GITHUB_OUTPUT"
    echo "kimigayo_extended_size_mb=${sizes["Kimigayo Extended"]}" >> "$GITHUB_OUTPUT"
    echo "alpine_size_mb=${sizes["Alpine Latest"]}" >> "$GITHUB_OUTPUT"
fi

# 目標値チェック（Minimal < 5MB）
kimigayo_minimal_size=${sizes["Kimigayo Minimal"]}
if [ $kimigayo_minimal_size -lt 5 ]; then
    echo -e "${GREEN}✓ 目標達成: Kimigayo Minimalが5MB以下です${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ 警告: Kimigayo Minimalが5MBを超えています (${kimigayo_minimal_size}MB)${NC}"
    exit 1
fi
