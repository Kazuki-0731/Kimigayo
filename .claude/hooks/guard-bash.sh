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

# 判定対象を「実際に実行されるコマンド」だけに絞る。
# コマンド全体を正規表現で見ると、heredoc のコミットメッセージ本文、
# 読むだけの操作、echo の引数として書いた説明文まで引っかかる
# （3つとも実際に踏んだ）。理由と実装は extract-commands.py のコメント。
EXTRACT="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/extract-commands.py"
if [ -f "$EXTRACT" ]; then
    CMD="$(printf '%s' "$CMD" | python3 -I "$EXTRACT" 2>/dev/null || printf '%s' "$CMD")"
fi
[ -n "$(printf '%s' "$CMD" | tr -d '[:space:]')" ] || exit 0

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

# そのコマンド「自身」が $1 である行だけを返す。
# extract-commands.py の出力は1行1コマンドで、先頭に VAR=val と sudo が
# 残ることがあるのでそこだけ読み飛ばす。
#
# オプションに同じ語が現れるケースを除くために必要。
# 例: docker run --rm -v cache:/build/kimigayo/build/downloads ...
#     ここには rm が含まれるが削除コマンドではない（実際に誤検知した）。
lines_cmd() {
    printf '%s\n' "$CMD" |
        grep -E "^(([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*)(sudo[[:space:]]+)?$1([[:space:]]|$)" ||
        true
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
   printf '%s' "$push_lines" | grep -qE '(--tags|--follow-tags|[[:space:]]v[0-9]+\.[0-9]+\.[0-9]+|refs/tags/)'; then
    # **そのタグのコミット時点のワークフロー**を調べて見せる。
    #
    # タグ push で走るのは、いまの main にあるものではなく、タグが
    # 指すコミットの .github/workflows/ で決まる。
    # 2026-10-09 にこれで事故った: release.yml を gh workflow disable で
    # 止めて v0.1.1 を push したところ、当時のコミットにあった
    # docker-publish.yml（"Docker Build and Push"）が走り、
    # **Docker Hub の latest を含む公開イメージが差し替わった。**
    # いまの main にそのファイルは無いので gh workflow list にも出ず、
    # 現在の一覧を見るだけでは気づけなかった。
    # gh workflow disable はワークフロー ID 単位なので、古いコミットに
    # しか無いものは止められない（ID が存在しない）。
    tag_report=""
    tags_in_cmd="$(printf '%s\n' "$push_lines" | tr ' ' '\n' |
        sed -n 's|^refs/tags/||p; /^v[0-9][0-9.]*$/p' | sort -u | tr '\n' ' ')"
    detector="${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/tag-push-workflows.py"
    if [ -f "$detector" ] && [ -n "$(printf '%s' "$tags_in_cmd" | tr -d ' ')" ]; then
        # shellcheck disable=SC2086
        tag_report="$(python3 -I "$detector" $tags_in_cmd 2>/dev/null || true)"
    fi

    block "タグの push" \
"タグの push は、**そのタグのコミット時点にあるワークフロー**を起動します。
いまの main のワークフローではありません。Docker Hub の公開イメージが
差し替わる可能性があります。毎回ユーザーの明示的な承認が必要です。

このタグで起動するワークフロー:
${tag_report:-  （タグ名を特定できませんでした。手動で確認してください:
    python3 .claude/hooks/tag-push-workflows.py <tag>）}

**gh workflow disable では古いコミットにしか無いワークフローを
止められません**（ワークフロー ID が存在しないため）。
上に ★ が出ているなら、公開を避けるには次のいずれかが必要です:
  - リポジトリ全体の Actions を一時停止する
    gh api -X PUT repos/{owner}/{repo}/actions/permissions -f enabled=false
  - 公開されてしまう前提で進め、あとで正しいイメージを出し直す"
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

rm_lines="$(lines_cmd 'rm')"
if [ -n "$rm_lines" ] && printf '%s' "$rm_lines" | grep -q 'build/downloads'; then
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
tar_lines="$(lines_cmd 'tar')"
if [ "$(uname -s)" = "Darwin" ] && [ -n "$tar_lines" ] &&
   printf '%s' "$tar_lines" | grep -qE '^([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*(sudo[[:space:]]+)?tar[[:space:]]+-?[a-zA-Z]*c' &&
   ! printf '%s' "$tar_lines" | grep -q 'COPYFILE_DISABLE'; then
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
