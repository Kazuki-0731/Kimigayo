#!/usr/bin/env bash
#
# PreToolUse(Edit|Write|MultiEdit) — ビルド実行中にビルドスクリプトを編集させない
#
# bash はスクリプトを一度に全部読まない。実行しながら読み進めるので、
# **走っている最中にファイルを書き換えると読み込み位置がずれ**、
# 途中から別の場所を実行したり構文エラーで落ちたりする。
#
# 2026-10-09 に2回踏んだ:
#   1回目 verify_rootfs に検査を足した -> その run では新しい検査が走らず、
#         古い成果物で検証が通ってしまった（気づくまで1往復無駄にした）
#   2回目 カーネルのパス修正を足した -> 走っていた run が
#         `syntax error near unexpected token 'else'` で exit 2
#         （rootfs は完成していたので成果物自体は無事だったが、
#           実行順序が壊れていたので信頼できない）
#
# どちらも「ビルドが終わってから編集する」だけで防げる。文章のルールでは
# 守れなかったので機械的に止める。
# → CLAUDE.md「判断が絡まないミスは文章にしない」節
#
# 判定は2条件の AND なので、ビルドしていないときは一切発火しない。
#   1. kimigayo のビルドコンテナが走っている
#   2. 編集対象がビルド中に読まれるファイル（scripts/ か build-system/）

set -uo pipefail

FILE="$(python3 -I -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input", {})
print(ti.get("file_path") or "")
' 2>/dev/null || true)"

[ -n "$FILE" ] || exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
REL="${FILE#"$PROJECT_DIR"/}"

# ビルド中に読まれるのはここだけ
case "$REL" in
    scripts/*|build-system/*) ;;
    *) exit 0 ;;
esac

command -v docker >/dev/null 2>&1 || exit 0
running="$(docker ps --format '{{.Image}} {{.Names}}' 2>/dev/null | grep -i kimigayo || true)"
[ -n "$running" ] || exit 0

{
    printf 'ブロックしました: ビルド実行中にビルドスクリプトを編集しようとしています\n\n'
    printf '  編集対象: %s\n' "$REL"
    printf '  走っているコンテナ:\n'
    printf '%s\n' "$running" | sed 's/^/    /'
    cat <<'EOF'

bash はスクリプトを実行しながら読み進めるため、**走っている最中に
書き換えると読み込み位置がずれます。** 途中から別の場所を実行したり、
構文エラーで落ちたりします。しかも成果物が中途半端にできるので、
あとの検証が「通ってしまう」ことがあります。

どうするか:
  - ビルドが終わるまで待つ（進捗はログで確認する）
  - 急ぐなら先にビルドを止める: docker stop <name>
  - 編集だけ先にしたいなら、ビルドを止めてから編集してやり直す

ビルド中でも .claude/ 配下・ドキュメント・テストの編集は止めません
（ビルドが読まないので）。
EOF
} >&2

exit 2
