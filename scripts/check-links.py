#!/usr/bin/env python3
"""追跡ファイル基準で Markdown の相対リンクを監査する。

ローカルのファイルシステムで判定してはいけない。.gitignore されている
ファイル（TODO.md など）が手元にあると「リンクは生きている」と誤判定し、
clone した人だけ壊れている状態を見逃す。公開リポジトリでは
**git が追跡しているか**だけが基準。
"""
import os
import posixpath
import re
import subprocess
import sys

root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, check=True).stdout.strip()
tracked = set(
    subprocess.run(["git", "-C", root, "ls-files"], capture_output=True,
                   text=True, check=True).stdout.split("\n")
) - {""}

# ディレクトリへのリンクも許容するため、追跡ファイルの親ディレクトリ集合を作る
tracked_dirs = set()
for t in tracked:
    d = posixpath.dirname(t)
    while d:
        tracked_dirs.add(d)
        tracked_dirs.add(d + "/")
        d = posixpath.dirname(d)

LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

broken = []
for f in sorted(x for x in tracked if x.endswith(".md")):
    path = os.path.join(root, f)
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        continue
    base = posixpath.dirname(f)
    for lineno, line in enumerate(text.split("\n"), 1):
        for label, target in LINK.findall(line):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            t = target.split("#")[0]
            if not t:
                continue
            resolved = posixpath.normpath(posixpath.join(base, t)) if base else posixpath.normpath(t)
            if resolved in tracked or resolved in tracked_dirs or resolved + "/" in tracked_dirs:
                continue
            on_disk = os.path.exists(os.path.join(root, resolved))
            broken.append((f, lineno, target, on_disk))

if not broken:
    print("リンク切れなし")
    sys.exit(0)

print("追跡されていないものを指すリンク: %d 件\n" % len(broken))
print("%-44s %-5s %-34s %s" % ("ファイル", "行", "リンク先", "手元には"))
print("-" * 104)
for f, lineno, target, on_disk in broken:
    mark = "★ある（ローカルでは気づけない）" if on_disk else "無い"
    print("%-44s %-5d %-34s %s" % (f, lineno, target, mark))
sys.exit(1)
