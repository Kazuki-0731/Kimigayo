#!/bin/bash
# Kimigayo OS - ベンチマークレポート生成

set -e

# Colors
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 入力ディレクトリ
INPUT_DIR="${1:-benchmark-results}"

if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Directory $INPUT_DIR not found"
    exit 1
fi

OUTPUT_FILE="$INPUT_DIR/BENCHMARK_REPORT.md"

echo -e "${BLUE}ベンチマークレポート生成中...${NC}"

# レポートヘッダー
cat > "$OUTPUT_FILE" <<'EOF'
# Kimigayo OS - ベンチマークレポート

このレポートは自動生成されたベンチマーク結果です。

## 📊 サマリー

EOF

# タイムスタンプ
echo "**生成日時:** $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# ディスクサイズ結果
if [ -f "$INPUT_DIR/benchmark-size.json" ]; then
    echo "### 💾 ディスクサイズ" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "| イメージ | サイズ(MB) |" >> "$OUTPUT_FILE"
    echo "|----------|------------|" >> "$OUTPUT_FILE"

    # JSONから結果を抽出（jqがあれば使用、なければgrepとsed）
    if command -v jq > /dev/null 2>&1; then
        jq -r '.results | to_entries | .[] | "| \(.key) | \(.value.size_mb)MB |"' "$INPUT_DIR/benchmark-size.json" >> "$OUTPUT_FILE"
    else
        # jqがない場合の簡易パース
        grep -o '"[^"]*": {"size_mb": [0-9]*' "$INPUT_DIR/benchmark-size.json" | \
            sed 's/"//g' | sed 's/: {size_mb: /|/g' | \
            awk -F'|' '{printf "| %s | %sMB |\n", $1, $2}' >> "$OUTPUT_FILE"
    fi

    echo "" >> "$OUTPUT_FILE"
fi

# 起動時間結果
if [ -f "$INPUT_DIR/benchmark-startup.json" ]; then
    echo "### ⚡ 起動時間" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    if command -v jq > /dev/null 2>&1; then
        avg=$(jq -r '.results.average_ms' "$INPUT_DIR/benchmark-startup.json")
        median=$(jq -r '.results.median_ms' "$INPUT_DIR/benchmark-startup.json")
        min=$(jq -r '.results.min_ms' "$INPUT_DIR/benchmark-startup.json")
        max=$(jq -r '.results.max_ms' "$INPUT_DIR/benchmark-startup.json")
    else
        avg=$(grep -o '"average_ms": [0-9]*' "$INPUT_DIR/benchmark-startup.json" | cut -d: -f2 | tr -d ' ')
        median=$(grep -o '"median_ms": [0-9]*' "$INPUT_DIR/benchmark-startup.json" | cut -d: -f2 | tr -d ' ')
        min=$(grep -o '"min_ms": [0-9]*' "$INPUT_DIR/benchmark-startup.json" | cut -d: -f2 | tr -d ' ')
        max=$(grep -o '"max_ms": [0-9]*' "$INPUT_DIR/benchmark-startup.json" | cut -d: -f2 | tr -d ' ')
    fi

    echo "| 指標 | 値 |" >> "$OUTPUT_FILE"
    echo "|------|-----|" >> "$OUTPUT_FILE"
    echo "| 平均 | ${avg}ms |" >> "$OUTPUT_FILE"
    echo "| 中央値 | ${median}ms |" >> "$OUTPUT_FILE"
    echo "| 最小 | ${min}ms |" >> "$OUTPUT_FILE"
    echo "| 最大 | ${max}ms |" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    # 目標値評価
    avg_sec=$((avg / 1000))
    if [ $avg_sec -lt 10 ]; then
        echo "✅ **目標達成:** 平均起動時間が10秒以下です" >> "$OUTPUT_FILE"
    else
        echo "⚠️ **警告:** 平均起動時間が10秒を超えています (${avg_sec}秒)" >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
fi

# メモリ使用量結果
if [ -f "$INPUT_DIR/benchmark-memory.json" ]; then
    echo "### 💾 メモリ使用量" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    if command -v jq > /dev/null 2>&1; then
        avg=$(jq -r '.results.average_mb' "$INPUT_DIR/benchmark-memory.json")
        median=$(jq -r '.results.median_mb' "$INPUT_DIR/benchmark-memory.json")
        min=$(jq -r '.results.min_mb' "$INPUT_DIR/benchmark-memory.json")
        max=$(jq -r '.results.max_mb' "$INPUT_DIR/benchmark-memory.json")
    else
        avg=$(grep -o '"average_mb": [0-9]*' "$INPUT_DIR/benchmark-memory.json" | cut -d: -f2 | tr -d ' ')
        median=$(grep -o '"median_mb": [0-9]*' "$INPUT_DIR/benchmark-memory.json" | cut -d: -f2 | tr -d ' ')
        min=$(grep -o '"min_mb": [0-9]*' "$INPUT_DIR/benchmark-memory.json" | cut -d: -f2 | tr -d ' ')
        max=$(grep -o '"max_mb": [0-9]*' "$INPUT_DIR/benchmark-memory.json" | cut -d: -f2 | tr -d ' ')
    fi

    echo "| 指標 | 値 |" >> "$OUTPUT_FILE"
    echo "|------|-----|" >> "$OUTPUT_FILE"
    echo "| 平均 | ${avg}MB |" >> "$OUTPUT_FILE"
    echo "| 中央値 | ${median}MB |" >> "$OUTPUT_FILE"
    echo "| 最小 | ${min}MB |" >> "$OUTPUT_FILE"
    echo "| 最大 | ${max}MB |" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    # 目標値評価
    if [ $avg -lt 128 ]; then
        echo "✅ **目標達成:** 平均メモリ使用量が128MB以下です" >> "$OUTPUT_FILE"
    else
        echo "⚠️ **警告:** 平均メモリ使用量が128MBを超えています (${avg}MB)" >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
fi

# フッター
cat >> "$OUTPUT_FILE" <<'EOF'

## 📋 詳細データ

詳細なベンチマークデータは以下のJSONファイルに保存されています:

- `benchmark-size.json` - ディスクサイズ比較
- `benchmark-startup.json` - 起動時間測定
- `benchmark-memory.json` - メモリ使用量測定

## 🎯 パフォーマンス目標

| 指標 | 目標値 | 現在の状態 |
|------|--------|-----------|
| イメージサイズ (Minimal) | < 5MB | 確認中 |
| 起動時間 | < 10秒 | 確認中 |
| メモリ使用量 | < 128MB | 確認中 |

---

*このレポートは自動生成されました*
EOF

echo -e "${GREEN}✓ レポートを $OUTPUT_FILE に保存しました${NC}"

# レポートを表示
echo ""
echo -e "${BOLD}=== ベンチマークレポート ===${NC}"
echo ""
cat "$OUTPUT_FILE"
