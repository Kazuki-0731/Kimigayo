#!/usr/bin/env bash
#
# PreToolUse(Bash) ガード — Kimigayo OS
#
# 「人の判断が絡まないミス」だけを機械的に止める。
# 判断や例外が多いものは入れない（毎回の警告はノイズになり、
# ノイズになった警告は読まれなくなる）。
# → CLAUDE.md「手段の選び方 — 判断が絡まないミスは文章にしない」節
#
# 止めるのは次の4種類だけ:
#   1. 外に出てしまって取り消せないもの（リリースタグ・Docker Hub）
#   2. 履歴を壊すもの（force push・rebase）
#   3. 取り戻すのに時間と帯域がかかるもの（ダウンロードキャッシュの削除）
#   4. 黙って成果物を汚すもの（macOS の AppleDouble 混入）
#
# 通常の `git push origin main` は止めない。会話での承認ルール
# （CLAUDE.md「Git の運用ルール」節）に任せる。ここで止めると
# 承認後も進めなくなる。
#
# 終了コード 2 = ブロックして stderr を Claude に返す。
# 終了コード 0 = 通す（何も出力しない）。

set -uo pipefail

# PreToolUse の入力は stdin の JSON。jq は環境にあるとは限らないので python3 で読む。
CMD="$(python3 -I -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get("tool_input", {}).get("command", ""))
' 2>/dev/null || true)"

[ -n "$CMD" ] || exit 0

block() {
    printf 'ブロックしました: %s\n\n%s\n' "$1" "$2" >&2
    exit 2
}

# ---------------------------------------------------------------------------
# 1. 外に出て取り消せないもの
# ---------------------------------------------------------------------------

# v*.*.* のタグ付けは release.yml を起動し、Docker Hub の latest を差し替える。
if printf '%s' "$CMD" | grep -qE '\bgit[[:space:]]+tag\b' &&
   printf '%s' "$CMD" | grep -qE 'v[0-9]+\.[0-9]+\.[0-9]+'; then
    block "リリースタグの作成" \
"v*.*.* タグを push すると .github/workflows/release.yml が走り、
Docker Hub の公開イメージ（latest を含む）を差し替えます。

タグ・リリースは毎回ユーザーの明示的な承認が必要です
（CLAUDE.md「指示の範囲を超えない > 実行・運用・リリース」節）。
先に CHANGELOG.md と RELEASE_NOTES.md を更新したかも確認してください。

ユーザーに確認してから、承認を得て実行してください。"
fi

if printf '%s' "$CMD" | grep -qE '\bgit[[:space:]]+push\b' &&
   printf '%s' "$CMD" | grep -qE '(--tags|--follow-tags|[[:space:]]v[0-9]+\.[0-9]+\.[0-9]+)'; then
    block "タグの push" \
"タグの push は release.yml を起動し、Docker Hub の公開イメージを
差し替えます。毎回ユーザーの明示的な承認が必要です。"
fi

if printf '%s' "$CMD" | grep -qE '\bdocker[[:space:]]+push\b'; then
    block "Docker Hub への push" \
"公開イメージを直接差し替える操作です。毎回ユーザーの明示的な
承認が必要です（CLAUDE.md「Git の運用ルール」節）。"
fi

# ---------------------------------------------------------------------------
# 2. 履歴を壊すもの
# ---------------------------------------------------------------------------

if printf '%s' "$CMD" | grep -qE '\bgit[[:space:]]+push\b' &&
   printf '%s' "$CMD" | grep -qE '(--force([^-]|$)|--force-with-lease|[[:space:]]-f([[:space:]]|$))'; then
    block "force push" \
"履歴の書き換えはユーザーに確認してから行う操作です
（CLAUDE.md「Git の運用ルール」節）。"
fi

if printf '%s' "$CMD" | grep -qE '\bgit[[:space:]]+rebase\b'; then
    block "git rebase" \
"このリポジトリでは rebase を使いません。自分のコミットのハッシュを
書き換えてしまうためです。

non-fast-forward で弾かれたときは merge で取り込みます:
  git pull origin main   または   git merge origin/main

（CLAUDE.md「Git の運用ルール」節）"
fi

if printf '%s' "$CMD" | grep -qE '\bgit[[:space:]]+filter-branch\b|\bgit[[:space:]]+reset[[:space:]]+--hard\b'; then
    block "履歴・作業ツリーの破壊的操作" \
"ユーザーに確認してから行う操作です。何を失うのかを先に提示してください
（CLAUDE.md「Git の運用ルール」節）。"
fi

# ---------------------------------------------------------------------------
# 3. 取り戻すのに時間と帯域がかかるもの
# ---------------------------------------------------------------------------

if printf '%s' "$CMD" | grep -qE '\bmake[[:space:]]+([A-Za-z0-9_=./-]+[[:space:]]+)*clean-all\b'; then
    block "make clean-all" \
"build/downloads/ のキャッシュまで消すため、カーネル・musl・BusyBox・
OpenRC の再ダウンロード（約150MB）とフルビルドを招きます。

どれを意図しているかユーザーに確認してください:
  make clean         成果物のみ
  make clean-cache   ダウンロードのみ
  make clean-all     全部

（CLAUDE.md「削除指示を受けたら」節）"
fi

if printf '%s' "$CMD" | grep -qE 'rm[[:space:]]+(-[a-zA-Z]+[[:space:]]+)*[^|;&]*build/downloads'; then
    block "ダウンロードキャッシュの削除" \
"build/downloads/ は約150MB の再取得を招きます。
意図した削除ならユーザーに確認してください
（CLAUDE.md「削除指示を受けたら」節）。"
fi

# ---------------------------------------------------------------------------
# 4. 黙って成果物を汚すもの
# ---------------------------------------------------------------------------

# macOS の bsdtar は AppleDouble（._*）を除外処理のあとに自分で生成し、
# しかも自分が作った ._* を一覧表示時に隠すため tar tzf では気づけない。
# 実測で 458 個がイメージに混入していた（2026-10-09）。
if [ "$(uname -s)" = "Darwin" ] &&
   printf '%s' "$CMD" | grep -qE '\btar[[:space:]]+-?[a-zA-Z]*c[a-zA-Z]*f?\b' &&
   ! printf '%s' "$CMD" | grep -q 'COPYFILE_DISABLE'; then
    block "COPYFILE_DISABLE なしの tar（macOS）" \
"macOS の bsdtar は AppleDouble メンバー（._*）を --exclude の処理の
あとに自分で生成するため --exclude='._*' では止まりません。さらに
自分が作った ._* を一覧表示時に隠すので tar tzf でも気づけません。
実測で 458 個がイメージに混入していました。

先頭に COPYFILE_DISABLE=1 を付けてください:
  COPYFILE_DISABLE=1 tar czf ... --exclude='._*' --exclude='.DS_Store' .

（CLAUDE.md「ビルドの全体像」節）"
fi

# ---------------------------------------------------------------------------
# 5. 機密
# ---------------------------------------------------------------------------

if printf '%s' "$CMD" | grep -qE '\bgit[[:space:]]+add\b' &&
   printf '%s' "$CMD" | grep -qE '(^|[[:space:]/])\.env([[:space:]]|$)'; then
    block ".env の追加" \
".env には DOCKER_HUB_ACCESS_TOKEN が入るため絶対にコミットしません
（CLAUDE.md「セキュリティ」節）。"
fi

exit 0
