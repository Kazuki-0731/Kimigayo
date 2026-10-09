#!/bin/bash
# Kimigayo OS - リリースのコードネームを返す
#
# 命名体系は SPECIFICATION.md「10.3 リリース名」が正本。
# 日本の通年の花を 12 本で循環させ、**メジャーバージョンに割り当てる**。
#
# **表に版を書き足す運用にしない。** メジャー番号から導出する。
# 版ごとの表にすると 3.0.1 を切ったときに更新を忘れる
# （CLAUDE.md「判断が絡まないミスは文章にしない」節）。
#
# v1.0 / v2.0 は命名を始める前に公開済みなので名前を持たない。
# この2つには後付けしない方針（2026-10-10 に決定）。名前が無いときは
# 何も出力せず 0 で終わる（呼び出し側は空文字列として扱う）。
#
# 使い方:
#   scripts/get-codename.sh          # get-version.sh の版から決める
#   scripts/get-codename.sh 3.0.0    # 版を指定する  -> Himawari
#   scripts/get-codename.sh 15.2.0   # 循環する      -> Himawari
set -eu

# メジャー 1 から順に。12 本使い切ったら先頭に戻る。
# 菊は "Kiku"（きく）。.claude のメモにあった "Kikku" は綴り間違い。
CODENAMES=(Sakura Ajisai Himawari Kiku Momiji Ume Fuji Asagao Tsubaki Satsuki Higanbana Sazanka)

# コードネームの運用を始めたメジャーバージョン
FIRST_NAMED_MAJOR=3

version="${1:-}"
if [ -z "$version" ]; then
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    version="$(bash "${script_dir}/get-version.sh" 2>/dev/null || echo "")"
fi

major="${version%%.*}"
case "$major" in
    ''|*[!0-9]*)
        # dev / 0.0.0-<sha> / unknown など。名前は付けない
        exit 0
        ;;
esac

if [ "$major" -lt "$FIRST_NAMED_MAJOR" ]; then
    exit 0
fi

echo "${CODENAMES[$(( (major - 1) % ${#CODENAMES[@]} ))]}"
