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
#   1. kimigayo のビルドコンテナ（kimigayo-os-build / kimigayo-build-env）が走っている
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
# ビルドコンテナだけを見る。`grep -i kimigayo` では、計測やスモークテストで
# 走らせた成果物のコンテナ（kimigayo-os:* / ishinokazuki/kimigayo-os:*）まで
# 一致してしまい、ビルドしていないのに編集を止めていた（2026-10-13）。
# 名前は docker-compose.yml の kimigayo-build サービスから取る:
#   - image: kimigayo-os-build:latest（`docker run` で直接叩いた場合も含む）
#   - container_name: kimigayo-build-env
#   - `docker compose run` は container_name を使わず
#     <project>-kimigayo-build-run-<id> になるので、compose のラベルでも見る
running="$(docker ps --format '{{.Image}}|{{.Names}}|{{.Label "com.docker.compose.service"}}' 2>/dev/null |
    awk -F'|' '
        $1 ~ /^kimigayo-os-build(:|$)/ || $2 == "kimigayo-build-env" || $3 == "kimigayo-build" {
            print $1 " " $2
        }' || true)"
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
