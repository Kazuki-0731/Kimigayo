#!/usr/bin/env python3
"""メモ・下書きとして扱うべきパスを判定する。

なぜこれが必要か:
  メモファイルは「いま何が書かれているか」では安全性を判断できない。
  次に何が書かれるか分からないからで、判断すべきは**ファイルの性格**。
  TODO.md・NEXT.md・.claude/question.md のような置き場は、あとで
  資格情報・社内情報・第三者の情報が書き込まれ得る。
  このリポジトリは公開されているので、入ってから気づくのでは遅い。

  → だからメモは最初から機密扱いにして、追跡しない。
    .gitignore は「入れ忘れ」を防げないので、機械チェックで止める。

判定の設計:
  部分一致は使えない。このリポジトリには memory_benchmark.py・
  memory.py・benchmark-memory.sh があり、'memo' を部分文字列として
  含む。RELEASE_NOTES.md も 'NOTES' を含むが実ドキュメントである。
  そのため basename に対する厳密な規則だけを使う。

使い方:
  パスを1行1件で標準入力に渡すと、メモ扱いのものだけを出力する。
  テスト: git ls-files | python3 .claude/hooks/memo-paths.py
          → 1件も出なければ既存の追跡ファイルに誤爆しない
"""

import posixpath
import re
import sys

# basename 全体がこれに一致するもの（大文字小文字は区別しない）
EXACT = {
    "todo.md", "todo.txt", "todo",
    "next.md", "next.txt", "next",
    "memo.md", "memo.txt", "memo",
    "note.md", "notes.md", "note.txt", "notes.txt",
    "scratch.md", "scratch.txt",
    "wip.md", "wip.txt",
    "draft.md", "draft.txt",
    "idea.md", "ideas.md",
    "question.md", "questions.md", "answer.md", "answers.md",
}

# basename がこの語で始まり、直後が区切り（- _ . 数字）であるもの。
# 「接頭辞」に限るのは RELEASE_NOTES.md を巻き込まないため。
PREFIX_RE = re.compile(
    r"^(todo|next|memo|notes?|scratch|wip|draft|ideas?|question|answer)"
    r"([-_.]|[0-9])",
    re.IGNORECASE,
)

# basename がこれで終わるもの。
# notes は入れない。RELEASE_NOTES.md は実ドキュメントであり、
# project_notes.md と名前だけでは区別できない。notes 単独の場合は
# EXACT で、notes-2026.md のような形は PREFIX_RE で拾える。
SUFFIX_RE = re.compile(
    r"([-_.](memo|scratch|draft|wip)\.(md|txt)"
    r"|\.local\.(json|ya?ml|toml|ini|env|conf))$",
    re.IGNORECASE,
)

# このディレクトリ直下の .md は無条件にメモ扱い。
# Claude Code の作業ディレクトリで、共有するのは設定だけ
# （settings.json / hooks / agents / skills / commands）。
MEMO_DIRS_MD = (".claude",)


def is_memo_path(path: str) -> bool:
    # lstrip("./") は使えない。先頭の "." まで食うので
    # ".claude/error.md" が "claude/error.md" になり、ディレクトリ規則が
    # 効かなくなる（実際にこれで .claude/*.md を取りこぼした）。
    norm = path.replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    base = posixpath.basename(norm)
    parent = posixpath.dirname(norm)

    if not base:
        return False

    if base.lower() in EXACT:
        return True
    if PREFIX_RE.match(base):
        return True
    if SUFFIX_RE.search(base):
        return True
    if parent in MEMO_DIRS_MD and base.lower().endswith(".md"):
        return True
    return False


def main() -> None:
    hits = []
    for line in sys.stdin:
        path = line.strip()
        if path and is_memo_path(path):
            hits.append(path)
    if hits:
        print("\n".join(hits))
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
