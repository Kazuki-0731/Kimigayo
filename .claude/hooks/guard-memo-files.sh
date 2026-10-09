#!/usr/bin/env bash
#
# PreToolUse(Bash) — メモファイルをコミットさせない
#
# なぜ機械チェックにするか:
#   メモファイルは「いま何が書かれているか」では安全性を判断できない。
#   **次に何が書かれるか分からない**からで、判断すべきはファイルの性格。
#   TODO.md・NEXT.md・.claude/question.md のような置き場には、あとで
#   資格情報・第三者の情報・社内情報が書き込まれ得る。
#   このリポジトリは公開されているので、入ってから気づくのでは遅い。
#
#   .gitignore だけでは足りない。`git add -f` で越えられるし、新しい名前の
#   メモを作ったときにルールを足し忘れる。文章のルールも守れない
#   （30ターン目に報告を書いているとき、冒頭に読んだ文章は背景に沈む）。
#   → CLAUDE.md「判断が絡まないミスは文章にしない」節
#
# 止めるもの:
#   1. git add がメモのパスを名指ししている（-f つきを含む）
#   2. git commit の時点でメモがステージされている
#      （git add . や git add -f を経由した場合も捕まえる）
#
# 判定は .claude/hooks/memo-paths.py。部分一致を使わない理由は
# そのファイルのコメントに書いてある（memory.py が 'memo' を含むため）。

set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$HOOK_DIR/../.." && pwd)}"
MEMO_MATCHER="${HOOK_DIR}/memo-paths.py"
EXTRACT="${HOOK_DIR}/extract-commands.py"

[ -f "$MEMO_MATCHER" ] || exit 0

CMD="$(python3 -I -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get("tool_input", {}).get("command", ""))
' 2>/dev/null || true)"

[ -n "$CMD" ] || exit 0

# 実際に実行されるコマンドだけに絞る（echo の引数や heredoc 本文を除く）
if [ -f "$EXTRACT" ]; then
    CMD="$(printf '%s' "$CMD" | python3 -I "$EXTRACT" 2>/dev/null || printf '%s' "$CMD")"
fi
[ -n "$(printf '%s' "$CMD" | tr -d '[:space:]')" ] || exit 0

explain() {
    cat >&2 <<EOF

メモファイルはリポジトリに入れません。**いま何が書かれているかではなく、
次に何が書かれるか分からない**ことが理由です。公開リポジトリなので、
資格情報や第三者の情報が書き込まれてから気づくのでは遅い。
（→ CLAUDE.md「メモは機密扱いにする」節）

どうするか:
  - 手元のメモとして使う          → .gitignore に入れる（追跡しない）
  - 他の人に残す必要がある内容    → 置き場を変える:
      踏んだ罠            docs/troubleshooting/
      手順                docs/developer/
      変更の経緯          コミットメッセージ
      リリースの記録      CHANGELOG.md / RELEASE_NOTES.md
      仕様・設計          SPECIFICATION.md / docs/developer/ARCHITECTURE.md
EOF
}

# ---------------------------------------------------------------------------
# 1. git add がメモを名指ししている
# ---------------------------------------------------------------------------
add_args="$(printf '%s\n' "$CMD" |
    grep -E '\bgit[[:space:]]+add\b' |
    sed -E 's/.*\bgit[[:space:]]+add\b//' |
    tr ' ' '\n' |
    grep -vE '^-' |
    grep -v '^$' || true)"

if [ -n "$add_args" ]; then
    if hits="$(printf '%s\n' "$add_args" | python3 -I "$MEMO_MATCHER")"; then
        : # メモ無し
    else
        printf 'ブロックしました: メモファイルを git add しようとしています\n\n' >&2
        printf '%s\n' "$hits" | sed 's/^/  /' >&2
        explain
        exit 2
    fi
fi

# ---------------------------------------------------------------------------
# 2. git commit の時点でステージに入っている
# ---------------------------------------------------------------------------
if printf '%s\n' "$CMD" | grep -qE '\bgit[[:space:]]+commit\b'; then
    staged="$(git -C "$PROJECT_DIR" diff --cached --name-only --diff-filter=d 2>/dev/null || true)"
    if [ -n "$staged" ]; then
        if hits="$(printf '%s\n' "$staged" | python3 -I "$MEMO_MATCHER")"; then
            : # メモ無し
        else
            printf 'ブロックしました: メモファイルがステージされています\n\n' >&2
            printf '%s\n' "$hits" | sed 's/^/  /' >&2
            printf '\n外すには: git restore --staged <path>\n' >&2
            explain
            exit 2
        fi
    fi
fi

exit 0
