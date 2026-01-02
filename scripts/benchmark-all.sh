#!/bin/bash
# Kimigayo OS - 統合ベンチマーク実行スクリプト

set -e

# Colors
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 出力ディレクトリ
OUTPUT_DIR="${OUTPUT_DIR:-benchmark-results}"
mkdir -p "$OUTPUT_DIR"

echo -e "${BOLD}Kimigayo OS - 統合ベンチマーク${NC}"
echo "======================================"
echo -e "${BLUE}出力ディレクトリ:${NC} $OUTPUT_DIR"
echo ""

# 1. ディスクサイズベンチマーク
echo -e "${YELLOW}[1/6] ディスクサイズベンチマーク実行中...${NC}"
echo ""
OUTPUT_FILE="$OUTPUT_DIR/benchmark-size.json" bash "$SCRIPT_DIR/benchmark-size.sh" || true
echo ""

# 2. 起動時間ベンチマーク
echo -e "${YELLOW}[2/6] 起動時間ベンチマーク実行中...${NC}"
echo ""
OUTPUT_FILE="$OUTPUT_DIR/benchmark-startup.json" ITERATIONS=5 bash "$SCRIPT_DIR/benchmark-startup.sh" || true
echo ""

# 3. メモリ使用量ベンチマーク
echo -e "${YELLOW}[3/6] メモリ使用量ベンチマーク実行中...${NC}"
echo ""
OUTPUT_FILE="$OUTPUT_DIR/benchmark-memory.json" DURATION=10 bash "$SCRIPT_DIR/benchmark-memory.sh" || true
echo ""

# 4. コンテナライフサイクルベンチマーク
echo -e "${YELLOW}[4/6] コンテナライフサイクルベンチマーク実行中...${NC}"
echo ""
BENCHMARK_ITERATIONS=5 bash "$SCRIPT_DIR/benchmark-lifecycle.sh" || true
echo ""

# 5. BusyBoxコマンドベンチマーク
echo -e "${YELLOW}[5/6] BusyBoxコマンドベンチマーク実行中...${NC}"
echo ""
BENCHMARK_ITERATIONS=5 bash "$SCRIPT_DIR/benchmark-busybox.sh" || true
echo ""

# 6. OS間比較ベンチマーク
echo -e "${YELLOW}[6/6] OS間比較ベンチマーク実行中...${NC}"
echo ""
ITERATIONS=5 OUTPUT_DIR="$OUTPUT_DIR" bash "$SCRIPT_DIR/benchmark-comparison.sh" || true
echo ""

# レポート生成
echo -e "${YELLOW}ベンチマークレポート生成中...${NC}"
bash "$SCRIPT_DIR/benchmark-report.sh" "$OUTPUT_DIR"

echo ""
echo -e "${GREEN}✓ 全ベンチマーク完了${NC}"
echo -e "${BLUE}結果:${NC} $OUTPUT_DIR/"
echo ""

ls -lh "$OUTPUT_DIR/"
