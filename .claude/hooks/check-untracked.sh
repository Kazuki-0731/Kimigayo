#!/usr/bin/env bash
#
# Stop フック — 新規ファイルを残したままターンを終えない
#
# CLAUDE.md「Git の運用ルール」:
#   「新規ファイルを残したままターンを終えない。コミットするか
#     .gitignore に入れるかをその場で決める。『後で』にすると誰も
#     気づかない（実際に .hypothesis/ の59ファイルと
#     benchmark-optimized.log が追跡されたまま9か月放置されていた）」
#
# これは文章のルールでは守れない種類のミス。30ターン目に報告を書いて
# いるとき、セッション冒頭に読んだ文章は背景に沈む。
# → CLAUDE.md「判断が絡まないミスは文章にしない」節
#
# 1度だけブロックする（stop_hook_active で再入を検知して通す）。

set -uo pipefail

ACTIVE="$(python3 -I -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("true")
    sys.exit(0)
print("true" if d.get("stop_hook_active") else "false")
' 2>/dev/null || echo true)"

# 2回目は通す（無限ループ防止）
[ "$ACTIVE" = "false" ] || exit 0

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" 2>/dev/null || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

UNTRACKED="$(git ls-files --others --exclude-standard | head -40)"
[ -n "$UNTRACKED" ] || exit 0

COUNT="$(git ls-files --others --exclude-standard | grep -c '' || echo 0)"

{
    printf '追跡されていない新規ファイルが %s 件あります:\n\n' "$COUNT"
    printf '%s\n' "$UNTRACKED" | sed 's/^/  /'
    [ "$COUNT" -gt 40 ] && printf '  ...(先頭40件)\n'
    cat <<'EOF'

ターンを終える前に、1件ずつ「コミットする」か「.gitignore に入れる」かを
決めてください（CLAUDE.md「Git の運用ルール」節）。
「後で」にすると誰も気づきません。実際に .hypothesis/ の59ファイルと
benchmark-optimized.log が追跡されたまま9か月放置されていました。

判断に迷うもの（計測結果・パッチ・config）はユーザーに確認してください。
EOF
} >&2

exit 2
