#!/bin/bash
# Kimigayo OS - ディスクサイズ比較ベンチマーク

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# デフォルト設定
OUTPUT_FILE="${OUTPUT_FILE:-benchmark-size.json}"

# 比較対象イメージ（カンマ区切りで名前:イメージ形式）
IMAGES=(
    "Kimigayo Minimal:ishinokazuki/kimigayo-os:latest-minimal"
    "Kimigayo Standard:ishinokazuki/kimigayo-os:latest"
    "Kimigayo Extended:ishinokazuki/kimigayo-os:latest-extended"
    "Alpine Latest:alpine:latest"
    "Alpine 3.19:alpine:3.19"
    "Debian Slim:debian:stable-slim"
    "Ubuntu:ubuntu:22.04"
    "BusyBox:busybox:latest"
)

echo -e "${BOLD}Kimigayo OS - ディスクサイズ比較ベンチマーク${NC}"
echo "======================================"
echo ""

# イメージをプル（ローカルにあればスキップ）
echo -e "${YELLOW}イメージをプル中...${NC}"

declare -a VALID_IMAGES=()
for entry in "${IMAGES[@]}"; do
    name="${entry%%:*}"
    image="${entry#*:}"
    echo -ne "  ${name}... "

    # ローカルにイメージがあるか確認
    if docker image inspect "$image" > /dev/null 2>&1; then
        echo "✓ (ローカル)"
        VALID_IMAGES+=("$entry")
    elif docker pull "$image" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        VALID_IMAGES+=("$entry")
    else
        echo -e "${RED}✗ (スキップ)${NC}"
    fi
done

echo ""

# サイズ測定
echo -e "${GREEN}イメージサイズ測定中...${NC}"
echo ""

# サイズデータを一時ファイルに保存
tmpfile=$(mktemp)
trap "rm -f $tmpfile" EXIT

max_name_len=0

for entry in "${VALID_IMAGES[@]}"; do
    name="${entry%%:*}"
    image="${entry#*:}"

    # サイズを取得（MB単位）
    size_bytes=$(docker image inspect "$image" --format='{{.Size}}' 2>/dev/null || echo "0")
    size_mb=$((size_bytes / 1024 / 1024))

    echo "$size_mb:$name:$image" >> "$tmpfile"

    # 最大名前長を記録（表示整形用）
    name_len=${#name}
    if [ $name_len -gt $max_name_len ]; then
        max_name_len=$name_len
    fi
done

# サイズでソート
sort -t: -k1 -n "$tmpfile" > "${tmpfile}.sorted"

# 結果表示
echo -e "${BOLD}ベンチマーク結果（サイズ順）${NC}"
echo "======================================"

# ヘッダー
printf "%-${max_name_len}s  %10s  %10s\n" "イメージ" "サイズ(MB)" "比較"
printf "%s\n" "$(printf '=%.0s' {1..50})"

# Kimigayo Minimalのサイズを基準として取得
kimigayo_minimal_size=$(grep "Kimigayo Minimal" "${tmpfile}.sorted" | cut -d: -f1 || echo "")

while IFS=: read -r size name image _unused; do
    # 比較率を計算
    if [ "$name" = "Kimigayo Minimal" ]; then
        comparison="(基準)"
    elif [ -n "$kimigayo_minimal_size" ] && [ "$kimigayo_minimal_size" -gt 0 ]; then
        ratio=$((size * 100 / kimigayo_minimal_size))
        comparison="${ratio}%"
    else
        comparison="-"
    fi

    # Display without color variable
    printf "%-${max_name_len}s  %10d  %10s\n" "$name" "$size" "$comparison"
done < "${tmpfile}.sorted"

echo ""

# JSON形式で保存
echo "{" > "$OUTPUT_FILE"
echo '  "benchmark": "image_size",' >> "$OUTPUT_FILE"
echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"," >> "$OUTPUT_FILE"
echo '  "results": {' >> "$OUTPUT_FILE"

first=true
while IFS=: read -r size name image; do
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$OUTPUT_FILE"
    fi

    # JSON用にエスケープ
    json_name=$(echo "$name" | sed 's/"/\\"/g')
    echo -n "    \"$json_name\": {\"size_mb\": $size, \"image\": \"$image\"}" >> "$OUTPUT_FILE"
done < "${tmpfile}.sorted"

echo "" >> "$OUTPUT_FILE"
echo "  }" >> "$OUTPUT_FILE"
echo "}" >> "$OUTPUT_FILE"

echo -e "${GREEN}✓ 結果を $OUTPUT_FILE に保存しました${NC}"

# CI環境の場合は環境変数にも出力
if [ -n "$GITHUB_OUTPUT" ]; then
    while IFS=: read -r size name image; do
        case "$name" in
            "Kimigayo Minimal")
                echo "kimigayo_minimal_size_mb=$size" >> "$GITHUB_OUTPUT"
                ;;
            "Kimigayo Standard")
                echo "kimigayo_standard_size_mb=$size" >> "$GITHUB_OUTPUT"
                ;;
            "Kimigayo Extended")
                echo "kimigayo_extended_size_mb=$size" >> "$GITHUB_OUTPUT"
                ;;
            "Alpine Latest")
                echo "alpine_size_mb=$size" >> "$GITHUB_OUTPUT"
                ;;
        esac
    done < "${tmpfile}.sorted"
fi

# 目標値チェック（Minimal < 5MB）
kimigayo_minimal_size=$(grep "Kimigayo Minimal" "${tmpfile}.sorted" | cut -d: -f1 || echo "")
if [ -n "$kimigayo_minimal_size" ]; then
    if [ "$kimigayo_minimal_size" -lt 5 ]; then
        echo -e "${GREEN}✓ 目標達成: Kimigayo Minimalが5MB以下です (${kimigayo_minimal_size}MB)${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ 警告: Kimigayo Minimalが5MBを超えています (${kimigayo_minimal_size}MB)${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ 警告: Kimigayo Minimalイメージが見つかりません${NC}"
    exit 0
fi
