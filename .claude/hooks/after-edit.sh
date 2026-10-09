#!/usr/bin/env bash
#
# PostToolUse(Edit|Write|MultiEdit) — Kimigayo OS
#
# 編集した内容そのものから機械的に分かることだけを返す。
# 「気をつけよう」系の一般論は返さない（毎回出ると読まれなくなる）。
#
# 返すのは3つ:
#   1. シェルスクリプトの構文エラー（即ブロック。exit 2）
#   2. versions.mk を触ったときの連動先（追加コンテキスト）
#   3. エラーを黙らせる変更を足したときの指摘（追加コンテキスト）
#
# 終了コード 2 = stderr を Claude に返す（ツールは既に実行済み）
# 終了コード 0 + JSON = additionalContext として Claude に渡す

set -uo pipefail

FILE="$(python3 -I -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input", {})
print(ti.get("file_path") or ti.get("notebook_path") or "")
' 2>/dev/null || true)"

[ -n "$FILE" ] || exit 0
[ -f "$FILE" ] || exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

REL="${FILE#"$PROJECT_DIR"/}"
NOTES=""

add_note() {
    NOTES="${NOTES}${NOTES:+$'\n\n'}$1"
}

# ---------------------------------------------------------------------------
# 1. シェルスクリプトの構文チェック（ここだけは即ブロック）
# ---------------------------------------------------------------------------
case "$REL" in
    *.sh)
        if ! err="$(bash -n "$FILE" 2>&1)"; then
            printf '%s に構文エラーがあります:\n\n%s\n\n直してから次に進んでください。\n' \
                "$REL" "$err" >&2
            exit 2
        fi
        ;;
esac

# ---------------------------------------------------------------------------
# 2. versions.mk を触ったら連動先を出す
# ---------------------------------------------------------------------------
if [ "$REL" = "versions.mk" ]; then
    add_note "versions.mk を変更しました。同じターンで次を突合してください
（CLAUDE.md「バージョンの単一の真実の源」節）:

1. チェックサム表（scripts/download-*.sh）。上流の公開値と突合する。
   musl と OpenRC は公式の SHA256 一覧が無いので Alpine aports の
   sha512sums と突合する
2. 捨てた古い値が他のファイルに残っていないか:
   git diff versions.mk | grep '^-[A-Z]' で旧値を拾って grep -rn
3. README.md と docs/ のバージョン表記
4. 版を上げたら build/ の残骸を疑う（make clean-<component>）
5. パッチが黙ってスキップされていないか:
   grep -iE 'skipped: [1-9]|not applicable' build/*-patches.log"
fi

# ---------------------------------------------------------------------------
# 3. エラーを黙らせる変更を「新しく足した」ときだけ指摘する
# ---------------------------------------------------------------------------
# 既にあるものは数えない。git diff の追加行だけを見る。
if git rev-parse --git-dir >/dev/null 2>&1; then
    added="$(git diff -- "$REL" 2>/dev/null | grep '^+' | grep -v '^+++' || true)"
    if [ -n "$added" ]; then
        hits="$(printf '%s' "$added" |
            grep -oE -- '-Wno-error|\|\|[[:space:]]*true|2>/dev/null|--allow-untrusted|-Wno-[a-z-]+' |
            sort -u | tr '\n' ' ' || true)"
        if [ -n "$hits" ]; then
            add_note "この編集で次を新しく足しています: ${hits}

エラーを黙らせる変更は「直した」ではありません。必ず提案に留め、
ユーザーの判断を仰いでください（CLAUDE.md「指示の範囲を超えない >
開発」節）。既に同種のものがリポジトリにあることは、増やしてよい
理由になりません。

やむを得ない場合は、なぜ必要かをコメントで残してください。"
        fi
    fi
fi

[ -n "$NOTES" ] || exit 0

python3 -I -c '
import json, sys
notes = sys.stdin.read()
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": notes,
    }
}, ensure_ascii=False))
' <<<"$NOTES"
exit 0
