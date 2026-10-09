#!/usr/bin/env python3
"""Bash のコマンド文字列から「実際に実行されるコマンド」だけを取り出す。

guard-bash.sh の誤検知対策。コマンド全体を1つの文字列として正規表現で
見ると、次のどれでも引っかかってしまう（3つとも実際に踏んだ）:

  1. heredoc のコミットメッセージ本文
       git commit -F - <<'EOF'
       .env は履歴に一度も入っていない
       EOF
  2. 読むだけの操作と同じコマンドに並んだリリースタグ名
       git tag backup/x HEAD; for t in v0.1.0 v1.0.0; do git rev-list -n1 $t; done
  3. echo の引数として書いた説明文
       echo "復元: git reset --hard backup/pre-rewrite"

いずれも実行されるのは危険な操作ではない。危険なのは「コマンド位置」に
その語が来たときだけなので、そこだけを抜き出して判定対象にする。

やっていること:
  - heredoc の本文を落とす
  - クォートを尊重して ; && || | 改行 で区切る
  - $(...) と `...` の中身も独立した区切りとして扱う（echo "$(危険)" を
    見逃さないため）
  - 各区切りの先頭トークン（先頭の VAR=val と sudo は読み飛ばす）が
    監視対象のコマンドのものだけを出力する

標準入力からコマンド文字列を読み、1行1コマンドで標準出力に書く。
"""

import re
import sys

# 監視対象。ここに無いコマンドの引数は判定されない。
WATCHED = {"git", "make", "docker", "rm", "tar", "apk", "pip", "pip3"}

HEREDOC_RE = re.compile(r"<<-?\s*[\"']?([A-Za-z_][A-Za-z0-9_]*)[\"']?")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def strip_heredocs(text: str) -> str:
    """heredoc の本文を落とす。コマンド行自体は残す。"""
    out = []
    pending: list[str] = []
    marker = None
    for line in text.split("\n"):
        if marker is not None:
            if line.strip() == marker:
                marker = pending.pop(0) if pending else None
            continue
        out.append(line)
        found = HEREDOC_RE.findall(line)
        if found:
            pending = list(found)
            marker = pending.pop(0)
    return "\n".join(out)


def split_segments(text: str):
    """クォートを尊重して区切り、$(...) / `...` の中身も別区切りにする。"""
    segments = []
    buf = []
    nested = []
    quote = None
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]

        if quote:
            # '...' の中ではエスケープも展開も起きない
            if ch == "\\" and quote == '"' and i + 1 < n:
                buf.append(text[i : i + 2])
                i += 2
                continue
            if ch == quote:
                quote = None
            else:
                # "..." の中の $(...) は展開されるので中身を拾う
                if quote == '"' and ch == "$" and text.startswith("$(", i):
                    depth, j = 1, i + 2
                    while j < n and depth:
                        if text[j] == "(":
                            depth += 1
                        elif text[j] == ")":
                            depth -= 1
                        j += 1
                    nested.append(text[i + 2 : j - 1])
                    i = j
                    continue
            buf.append(ch)
            i += 1
            continue

        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue

        if ch == "\\" and i + 1 < n:
            buf.append(text[i : i + 2])
            i += 2
            continue

        if text.startswith("$(", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                j += 1
            nested.append(text[i + 2 : j - 1])
            i = j
            continue

        if ch == "`":
            j = text.find("`", i + 1)
            if j == -1:
                j = n
            nested.append(text[i + 1 : j])
            i = j + 1
            continue

        if text.startswith("&&", i) or text.startswith("||", i):
            segments.append("".join(buf))
            buf = []
            i += 2
            continue

        if ch in ";\n|&(){}":
            segments.append("".join(buf))
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    segments.append("".join(buf))
    for inner in nested:
        segments.extend(split_segments(inner))
    return segments


def first_command(segment: str):
    """先頭の VAR=val と sudo を読み飛ばして、実行されるコマンド名を返す。"""
    tokens = segment.strip().split()
    while tokens and (ENV_ASSIGN_RE.match(tokens[0]) or tokens[0] == "sudo"):
        tokens.pop(0)
    # シェルのキーワードも読み飛ばす（for ... do git ... のような形）
    while tokens and tokens[0] in {
        "do", "then", "else", "elif", "fi", "done", "if", "while",
        "until", "for", "!", "time", "command", "exec", "xargs",
    }:
        tokens.pop(0)
    return tokens[0] if tokens else None


def main() -> None:
    text = sys.stdin.read()
    kept = []
    for segment in split_segments(strip_heredocs(text)):
        name = first_command(segment)
        if name is None:
            continue
        # パス付きで呼ばれることもある（/usr/bin/git など）
        base = name.rsplit("/", 1)[-1]
        if base in WATCHED:
            kept.append(" ".join(segment.split()))
    print("\n".join(kept))


if __name__ == "__main__":
    main()
