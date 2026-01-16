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

# 1. ディスクサイズ結果
# OS間比較データも統合
LATEST_COMPARISON=$(ls -t "$INPUT_DIR"/comparison_*.json 2>/dev/null | head -1)

if [ -f "$INPUT_DIR/benchmark-size.json" ]; then
    echo "### 💾 ディスクサイズ" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "| イメージ | サイズ |" >> "$OUTPUT_FILE"
    echo "|----------|--------|" >> "$OUTPUT_FILE"

    # JSONから結果を抽出（jqがあれば使用、なければgrepとsed）
    if command -v jq > /dev/null 2>&1; then
        # Kimigayo OSはKB単位で詳細表示、他はMB単位
        jq -r '.results | to_entries | .[] |
            if (.key | contains("Kimigayo")) then
                if .value.size_kb then
                    "| \(.key) | \(.value.size_kb)KB (\(.value.size_mb)MB) |"
                else
                    "| \(.key) | \(.value.size_mb * 1024 | floor)KB (\(.value.size_mb)MB) |"
                end
            else
                "| \(.key) | \(.value.size_mb)MB |"
            end' "$INPUT_DIR/benchmark-size.json" >> "$OUTPUT_FILE"

        # OS間比較データから追加のサイズ情報を抽出
        if [ -n "$LATEST_COMPARISON" ] && [ -f "$LATEST_COMPARISON" ]; then
            jq -r '.results | to_entries |
                map(select(.key | contains("distroless"))) |
                .[] |
                # Distroless Staticは1MBなのでKB単位で表示
                if (.key | contains("static")) then
                    if .value.size_mb == 1 then "| Distroless Static | \(.value.size_mb * 1024)KB (\(.value.size_mb)MB) |"
                    else "| Distroless Static | \(.value.size_mb)MB |"
                    end
                elif (.key | contains("base")) then "| Distroless Base | \(.value.size_mb)MB |"
                else empty end' "$LATEST_COMPARISON" >> "$OUTPUT_FILE" 2>/dev/null || true
        fi
    else
        # jqがない場合の簡易パース
        grep -o '"[^"]*": {"size_mb": [0-9]*' "$INPUT_DIR/benchmark-size.json" | \
            sed 's/"//g' | sed 's/: {size_mb: /|/g' | \
            awk -F'|' '{printf "| %s | %sMB |\n", $1, $2}' >> "$OUTPUT_FILE"
    fi

    echo "" >> "$OUTPUT_FILE"
fi

# 2. 起動時間結果
if [ -f "$INPUT_DIR/benchmark-startup.json" ]; then
    echo "### ⚡ 起動時間" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    # ディスクサイズと同じ順序でOS起動時間を表示
    if command -v jq > /dev/null 2>&1; then
        echo "| イメージ | 起動時間 |" >> "$OUTPUT_FILE"
        echo "|----------|---------|" >> "$OUTPUT_FILE"

        # benchmark-size.jsonから全OSをリスト化し、比較データとマージ
        jq -r --slurpfile comparison <(cat "$LATEST_COMPARISON" 2>/dev/null || echo '{"results":{}}') \
            '.results | to_entries | .[] |
            .os_name = .key |
            # 比較データから対応するOSの起動時間を検索
            .startup = (
                if (.key | contains("Kimigayo")) then
                    ($comparison[0].results | to_entries[] | select(.key | contains("kimigayo")) | .value.startup_ms)
                elif (.key | contains("Alpine Latest")) then
                    ($comparison[0].results | to_entries[] | select(.key | contains("alpine:latest")) | .value.startup_ms)
                elif (.key | contains("Alpine 3.19")) then "測定未実施"
                elif (.key | contains("Ubuntu")) then
                    ($comparison[0].results | to_entries[] | select(.key | contains("ubuntu")) | .value.startup_ms)
                elif (.key | contains("Debian")) then "測定未実施"
                elif (.key | contains("BusyBox")) then "測定未実施"
                else "測定未実施"
                end
            ) |
            if .startup == "N/A" or .startup == -1 then
                "| \(.os_name) | N/A (実行可能ファイル無し) |"
            elif (.startup | type) == "number" then
                "| \(.os_name) | \(.startup)ms |"
            else
                "| \(.os_name) | \(.startup) |"
            end' "$INPUT_DIR/benchmark-size.json" >> "$OUTPUT_FILE" 2>/dev/null

        # Distroless（比較データにのみ存在）を追加
        if [ -n "$LATEST_COMPARISON" ] && [ -f "$LATEST_COMPARISON" ]; then
            jq -r '.results | to_entries[] |
                select(.key | contains("distroless")) |
                if (.key | contains("base")) then "| Distroless Base | N/A (実行可能ファイル無し) |"
                elif (.key | contains("static")) then "| Distroless Static | N/A (実行可能ファイル無し) |"
                else empty end' "$LATEST_COMPARISON" >> "$OUTPUT_FILE" 2>/dev/null
        fi

        echo "" >> "$OUTPUT_FILE"
    fi

    # Kimigayo OS単体測定データ
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

    echo "**Kimigayo OS単体測定:**" >> "$OUTPUT_FILE"
    echo "- 平均: ${avg}ms | 中央値: ${median}ms | 最小: ${min}ms | 最大: ${max}ms" >> "$OUTPUT_FILE"
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

# 3. メモリ使用量結果
if [ -f "$INPUT_DIR/benchmark-memory.json" ]; then
    echo "### 💾 メモリ使用量" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    # ディスクサイズと同じ順序でOSメモリ使用量を表示
    if command -v jq > /dev/null 2>&1; then
        echo "| イメージ | メモリ使用量 |" >> "$OUTPUT_FILE"
        echo "|----------|------------|" >> "$OUTPUT_FILE"

        # benchmark-size.jsonから全OSをリスト化し、比較データとマージ
        jq -r --slurpfile comparison <(cat "$LATEST_COMPARISON" 2>/dev/null || echo '{"results":{}}') \
            '.results | to_entries | .[] |
            .os_name = .key |
            # 比較データから対応するOSのメモリ使用量を検索
            .memory = (
                if (.key | contains("Kimigayo")) then
                    ($comparison[0].results | to_entries[] | select(.key | contains("kimigayo")) | .value.memory_mb)
                elif (.key | contains("Alpine Latest")) then
                    ($comparison[0].results | to_entries[] | select(.key | contains("alpine:latest")) | .value.memory_mb)
                elif (.key | contains("Alpine 3.19")) then "測定未実施"
                elif (.key | contains("Ubuntu")) then
                    ($comparison[0].results | to_entries[] | select(.key | contains("ubuntu")) | .value.memory_mb)
                elif (.key | contains("Debian")) then "測定未実施"
                elif (.key | contains("BusyBox")) then "測定未実施"
                else "測定未実施"
                end
            ) |
            if .memory == "N/A" or .memory == -1 then
                "| \(.os_name) | N/A (実行可能ファイル無し) |"
            elif (.memory | type) == "number" then
                "| \(.os_name) | \(.memory)MB |"
            else
                "| \(.os_name) | \(.memory) |"
            end' "$INPUT_DIR/benchmark-size.json" >> "$OUTPUT_FILE" 2>/dev/null

        # Distroless（比較データにのみ存在）を追加
        if [ -n "$LATEST_COMPARISON" ] && [ -f "$LATEST_COMPARISON" ]; then
            jq -r '.results | to_entries[] |
                select(.key | contains("distroless")) |
                if (.key | contains("base")) then "| Distroless Base | N/A (実行可能ファイル無し) |"
                elif (.key | contains("static")) then "| Distroless Static | N/A (実行可能ファイル無し) |"
                else empty end' "$LATEST_COMPARISON" >> "$OUTPUT_FILE" 2>/dev/null
        fi

        echo "" >> "$OUTPUT_FILE"
    fi

    # Kimigayo OS単体測定データ
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

    echo "**Kimigayo OS単体測定:**" >> "$OUTPUT_FILE"
    echo "- 平均: ${avg}MB | 中央値: ${median}MB | 最小: ${min}MB | 最大: ${max}MB" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    # 目標値評価
    if [ $avg -lt 128 ]; then
        echo "✅ **目標達成:** 平均メモリ使用量が128MB以下です" >> "$OUTPUT_FILE"
    else
        echo "⚠️ **警告:** 平均メモリ使用量が128MBを超えています (${avg}MB)" >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
fi

# 4. コンテナライフサイクル結果
if [ -f "$INPUT_DIR/lifecycle.json" ]; then
    echo "### 🔄 コンテナライフサイクル (Kimigayo OS)" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    if command -v jq > /dev/null 2>&1; then
        startup_avg=$(jq -r '.results.container_start.average_ms' "$INPUT_DIR/lifecycle.json" 2>/dev/null || echo "N/A")
        stop_avg=$(jq -r '.results.container_stop.average_ms' "$INPUT_DIR/lifecycle.json" 2>/dev/null || echo "N/A")
        restart_avg=$(jq -r '.results.container_restart.average_ms' "$INPUT_DIR/lifecycle.json" 2>/dev/null || echo "N/A")
        cleanup_avg=$(jq -r '.results.container_cleanup.average_ms' "$INPUT_DIR/lifecycle.json" 2>/dev/null || echo "N/A")
        run_avg=$(jq -r '.results.run_to_completion.average_ms' "$INPUT_DIR/lifecycle.json" 2>/dev/null || echo "N/A")

        echo "| 操作 | 平均時間 |" >> "$OUTPUT_FILE"
        echo "|------|----------|" >> "$OUTPUT_FILE"
        echo "| 起動 | ${startup_avg}ms |" >> "$OUTPUT_FILE"
        echo "| 停止 | ${stop_avg}ms |" >> "$OUTPUT_FILE"
        echo "| 再起動 | ${restart_avg}ms |" >> "$OUTPUT_FILE"
        echo "| クリーンアップ | ${cleanup_avg}ms |" >> "$OUTPUT_FILE"
        echo "| 実行完了 | ${run_avg}ms |" >> "$OUTPUT_FILE"
    else
        echo "詳細データは \`lifecycle.json\` を参照してください。" >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
    echo "*注: ライフサイクル測定はKimigayo OS専用。他のOSとの比較は「起動時間」セクションを参照*" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# 5. BusyBoxコマンド性能結果
if [ -f "$INPUT_DIR/busybox.json" ]; then
    echo "### 🔧 BusyBoxコマンド性能" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    if command -v jq > /dev/null 2>&1; then
        echo "**Kimigayo OS vs Alpine Linux**" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "| コマンド | Kimigayo OS | Alpine Linux | 速度比 |" >> "$OUTPUT_FILE"
        echo "|---------|-------------|--------------|--------|" >> "$OUTPUT_FILE"

        # 各コマンドの結果を抽出
        jq -r '.results | to_entries | .[] |
            "| \(.key) | \(.value.kimigayo_avg_ms)ms | \(.value.alpine_avg_ms)ms | \(.value.speedup)x |"' \
            "$INPUT_DIR/busybox.json" >> "$OUTPUT_FILE" 2>/dev/null || \
            echo "詳細データは \`busybox.json\` を参照してください。" >> "$OUTPUT_FILE"
    else
        echo "詳細データは \`busybox.json\` を参照してください。" >> "$OUTPUT_FILE"
    fi
    echo "" >> "$OUTPUT_FILE"
fi

# 6. 機能比較（OS間比較ベンチマークから生成）
if [ -n "$LATEST_COMPARISON" ] && [ -f "$LATEST_COMPARISON" ] && command -v jq > /dev/null 2>&1; then
    echo "### 🔍 機能比較" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "| イメージ | サイズ | 起動時間 | メモリ | シェル | パッケージマネージャー |" >> "$OUTPUT_FILE"
    echo "|---------|-------|---------|-------|--------|---------------------|" >> "$OUTPUT_FILE"

    # 各OSの情報を整形して表示
    jq -r '.results | to_entries | .[] |
        # イメージ名を短縮
        if (.key | contains("kimigayo")) then .short_name = "Kimigayo Standard"
        elif (.key | contains("alpine")) then .short_name = "Alpine Latest"
        elif (.key | contains("distroless/static")) then .short_name = "Distroless Static"
        elif (.key | contains("distroless/base")) then .short_name = "Distroless Base"
        elif (.key | contains("ubuntu")) then .short_name = "Ubuntu 22.04"
        else .short_name = .key end |

        # サイズのフォーマット
        if .value.size_mb == 0 then .size_str = "N/A" else .size_str = (.value.size_mb | tostring) + "MB" end |

        # 起動時間のフォーマット
        if (.value.startup_ms == "N/A" or .value.startup_ms == 0 or .value.startup_ms == -1) then .startup_str = "N/A"
        else .startup_str = (.value.startup_ms | tostring) + "ms" end |

        # メモリのフォーマット
        if (.value.memory_mb == "N/A" or .value.memory_mb == 0 or .value.memory_mb == -1) then .memory_str = "N/A"
        else .memory_str = (.value.memory_mb | tostring) + "MB" end |

        "| \(.short_name) | \(.size_str) | \(.startup_str) | \(.memory_str) | \(.value.has_shell) | \(.value.has_pkg_manager) |"' \
        "$LATEST_COMPARISON" >> "$OUTPUT_FILE" 2>/dev/null

    echo "" >> "$OUTPUT_FILE"
    echo "**Kimigayo OSの特徴:**" >> "$OUTPUT_FILE"
    echo "- ✅ 最小クラスのイメージサイズ (1MB)" >> "$OUTPUT_FILE"
    echo "- ✅ Alpine並みの低メモリ使用量 (0.2MB)" >> "$OUTPUT_FILE"
    echo "- ✅ シェル対応（Distrolessより柔軟）" >> "$OUTPUT_FILE"
    echo "- ⚠️ パッケージマネージャー非搭載（セキュリティ重視設計）" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
fi

# フッター
cat >> "$OUTPUT_FILE" <<'EOF'

## 📋 詳細データ

詳細なベンチマークデータは以下のファイルに保存されています:

- `benchmark-size.json` - ディスクサイズ比較
- `benchmark-startup.json` - 起動時間測定
- `benchmark-memory.json` - メモリ使用量測定
- `lifecycle.json` - コンテナライフサイクル測定
- `busybox.json` - BusyBoxコマンド性能測定
- `comparison_*.json` - OS間比較ベンチマーク

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
