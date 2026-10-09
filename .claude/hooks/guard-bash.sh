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

# heredoc の中身は判定対象から外す。
# コミットメッセージを heredoc で渡すのが普通なので、本文に
# 「.env は履歴に入っていない」「git tag を打つ前に」のような説明が
# あるだけでブロックしてしまう（実際に誤検知した）。
# 判定したいのは実行されるコマンドの側だけ。
CMD="$(printf '%s' "$CMD" | python3 -I -c '
import re, sys
text = sys.stdin.read()
lines = text.split("\n")
out = []
pending = []          # まだ終端していない heredoc のマーカー
skipping = None
for line in lines:
    if skipping is not None:
        if line.strip() == skipping:
            skipping = pending.pop(0) if pending else None
            if skipping is not None:
                continue
            skipping = None
        continue
    # そのコマンド行自体は残す（git add などの判定に必要）
    out.append(line)
    markers = re.findall(r"<<-?\s*[\x27\"]?([A-Za-z_][A-Za-z0-9_]*)[\x27\"]?", line)
    if markers:
        pending = list(markers)
        skipping = pending.pop(0)
print("\n".join(out))
' 2>/dev/null || printf '%s' "$CMD")"

block() {
    printf 'ブロックしました: %s\n\n%s\n' "$1" "$2" >&2
    exit 2
}

# ---------------------------------------------------------------------------
# 1. 外に出て取り消せないもの
# ---------------------------------------------------------------------------

# 判定は行単位で行う。コマンド全体を見ると、別の行で
# タグを「読んでいる」だけの場合まで巻き込む（実際に誤検知した）。
lines_with() {
    printf '%s\n' "$CMD" | grep -E "$1" || true
}

# v*.*.* のタグ「作成」は release.yml を起動し、Docker Hub の latest を
# 差し替える。削除（-d）・一覧（-l / --list）・検証は読むだけなので通す。
tag_lines="$(lines_with '\bgit[[:space:]]+tag\b')"
if [ -n "$tag_lines" ] &&
   printf '%s' "$tag_lines" | grep -qE 'v[0-9]+\.[0-9]+\.[0-9]+' &&
   ! printf '%s' "$tag_lines" | grep -qE '(^|[[:space:]])(-d|--delete|-l|--list|--verify|-n[0-9]*)([[:space:]]|$)'; then
    block "リリースタグの作成" \
"v*.*.* タグを push すると .github/workflows/release.yml が走り、
Docker Hub の公開イメージ（latest を含む）を差し替えます。

タグ・リリースは毎回ユーザーの明示的な承認が必要です
（CLAUDE.md「指示の範囲を超えない > 実行・運用・リリース」節）。
先に CHANGELOG.md と RELEASE_NOTES.md を更新したかも確認してください。

ユーザーに確認してから、承認を得て実行してください。"
fi

push_lines="$(lines_with '\bgit[[:space:]]+push\b')"
if [ -n "$push_lines" ] &&
   printf '%s' "$push_lines" | grep -qE '(--tags|--follow-tags|[[:space:]]v[0-9]+\.[0-9]+\.[0-9]+)'; then
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

if [ -n "$push_lines" ] &&
   printf '%s' "$push_lines" | grep -qE '(--force([^-]|$)|--force-with-lease|[[:space:]]-f([[:space:]]|$))'; then
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

add_lines="$(lines_with '\bgit[[:space:]]+add\b')"
if [ -n "$add_lines" ] &&
   printf '%s' "$add_lines" | grep -qE '(^|[[:space:]/])\.env([[:space:]]|$)'; then
    block ".env の追加" \
".env には DOCKER_HUB_ACCESS_TOKEN が入るため絶対にコミットしません
（CLAUDE.md「セキュリティ」節）。"
fi

exit 0
