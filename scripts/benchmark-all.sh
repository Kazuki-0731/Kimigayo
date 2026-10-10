#!/bin/bash
# Kimigayo OS - 統合ベンチマーク実行スクリプト

set -e

# Colors
BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
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

# 子スクリプトは `${BASH}` で呼ぶ（このスクリプトと同じ interpreter）。
# `bash` と書くと PATH の先頭が拾われ、macOS では 3.2 になる。
#
# 落ちたものを覚えておく。
#
# **`|| true` で握り潰さないこと。** 2026-10-10 まで全6ステップが
# `|| true` で終わっており、**6本とも落ちても「✓ 全ベンチマーク完了」**と
# 表示していた。実際に benchmark-startup.sh と benchmark-memory.sh は
# 別物を測っていたが、このスクリプト経由では気づけなかった。
#
# ただし1本落ちたら即終了にもしない（`set -e` に任せない）。
# 残りの結果は取れた方が役に立つし、レポートも部分的には作れる。
# **最後まで走らせたうえで、落ちたものを名指しして非ゼロで終わる。**
FAILED=""

run_step() {
    local label="$1"
    shift

    echo -e "${YELLOW}${label} 実行中...${NC}"
    echo ""

    # set -e を効かせたままにすると失敗時にここで終わるので、
    # この呼び出しだけ明示的に判定する。
    local rc=0
    "$@" || rc=$?

    echo ""
    if [ "$rc" -ne 0 ]; then
        echo -e "${RED}✗ ${label} が失敗しました（終了コード ${rc}）${NC}"
        echo ""
        FAILED="${FAILED}  - ${label}（終了コード ${rc}）
"
    fi
    return 0
}

run_step "[1/6] ディスクサイズベンチマーク" \
    env OUTPUT_FILE="$OUTPUT_DIR/benchmark-size.json" \
    "${BASH:-bash}" "$SCRIPT_DIR/benchmark-size.sh"

run_step "[2/6] 起動時間ベンチマーク" \
    env OUTPUT_FILE="$OUTPUT_DIR/benchmark-startup.json" ITERATIONS=5 \
    "${BASH:-bash}" "$SCRIPT_DIR/benchmark-startup.sh"

run_step "[3/6] メモリ使用量ベンチマーク" \
    env OUTPUT_FILE="$OUTPUT_DIR/benchmark-memory.json" DURATION=10 \
    "${BASH:-bash}" "$SCRIPT_DIR/benchmark-memory.sh"

run_step "[4/6] コンテナライフサイクルベンチマーク" \
    env BENCHMARK_ITERATIONS=5 OUTPUT_DIR="$OUTPUT_DIR" \
    "${BASH:-bash}" "$SCRIPT_DIR/benchmark-lifecycle.sh"

run_step "[5/6] BusyBoxコマンドベンチマーク" \
    env BENCHMARK_ITERATIONS=5 OUTPUT_DIR="$OUTPUT_DIR" \
    "${BASH:-bash}" "$SCRIPT_DIR/benchmark-busybox.sh"

run_step "[6/6] OS間比較ベンチマーク" \
    env ITERATIONS=5 OUTPUT_DIR="$OUTPUT_DIR" \
    "${BASH:-bash}" "$SCRIPT_DIR/benchmark-comparison.sh"

# レポート生成。入力の JSON が欠けていても、取れたぶんだけは作る。
run_step "ベンチマークレポート生成" \
    "${BASH:-bash}" "$SCRIPT_DIR/benchmark-report.sh" "$OUTPUT_DIR"

echo ""
if [ -n "$FAILED" ]; then
    echo -e "${RED}✗ 失敗したベンチマークがあります:${NC}"
    printf '%s' "$FAILED"
    echo ""
    echo -e "${BLUE}取れた結果:${NC} $OUTPUT_DIR/"
    ls -lh "$OUTPUT_DIR/"
    echo ""
    echo -e "${YELLOW}レポートの数値は欠けています。${NC}"
    echo -e "${YELLOW}落ちたものを直してから測り直してください。${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 全ベンチマーク完了${NC}"
echo -e "${BLUE}結果:${NC} $OUTPUT_DIR/"
echo ""

ls -lh "$OUTPUT_DIR/"
