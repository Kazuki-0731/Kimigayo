#!/usr/bin/env python3
"""ドキュメントに古い情報が戻ってきていないかを機械的に検査する。

2026-10-12 にドキュメントを横串で監査したとき（67 ファイル、約 650 件）、
同じ種類の古い記述があちこちに散っていた。直しても、古い文書から
コピーされたり、記憶で書かれたりして戻ってくる。人の判断が要らない
ものはここで止める（CLAUDE.md「判断が絡まないミスは文章にしない」）。

規則の足し方:
  - 一度直した古い記述が別の場所でまた見つかったら、RULES に足す
  - pattern に当たっても unless に当たる行は許す（「〜は使えない」と
    説明している行や、過去の誤りを記録している行）
  - 歴史の記録として古い値を残す文書は HISTORY に入れる（検査しない）

追跡ファイルだけを見る（.gitignore されたメモは対象外）。
"""
import re
import subprocess
import sys

# 当時の記録として古い値を意図的に残している文書
HISTORY = {
    "CHANGELOG.md",
    "RELEASE_NOTES.md",
    "docs/V1_RELEASE_PLAN.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/developer/PERFORMANCE_ANALYSIS.md",
}

# 検査する拡張子・ファイル名
TARGET = re.compile(r"(\.md|\.ya?ml|^Dockerfile[^/]*|/Dockerfile[^/]*|^LICENSE)$")

# (pattern, unless, 理由)
RULES = [
    (r"\b236KB\b", r"誤記",
     "v3.0.1 の常駐メモリは 232KB（236KB は 2026-10-12 の誤記）"),
    (r"\bps aux\b", r"使え|通る|受け付け|動かない|unrecognized|Extended|extended|not work|cannot",
     "BusyBox の ps は Minimal / Standard で aux を受け付けない。ps か top -b -n1 を使う"),
    (r"\bfind\b.*-size \+[0-9]+[MG]\b", r"動かない|と書く|解さない",
     "BusyBox の find は -size +10M を解さない。+10240k のように k で書く"),
    (r"wget[^\n]*--tries", r"accept|受け付け|動かない|失敗していた",
     "BusyBox の wget は --tries を受け付けない"),
    (r"kimigayo-os\.org", None,
     "kimigayo-os.org というドメインは存在しない。報告は GitHub Security Advisories"),
    (r"ishinokazuki/kimigayo-os:(0\.1\.0|stable|edge|standard|minimal|extended)\b", None,
     "Docker Hub に存在しないタグ。latest-<variant> か <版>-<variant>（例 3.0.2-standard）。\n"
     "    手元でビルドしたイメージ名（kimigayo-os:standard-x86_64）は対象外"),
    (r"docker-compose (run|build|up|down|exec|logs)\b", None,
     "docker-compose（v1）は EOL。docker compose を使う"),
    (r"\bmemory: 2G\b", None,
     "docker-compose.yml の memory 上限は 8G"),
    (r"security-updates\.yml|docker-publish\.yml", None,
     "存在しないワークフロー。security.yml / release.yml"),
    (r"needs-triage|feature-request|high-priority|\bP0\b.*label", None,
     "存在しないラベル。実在するのは gh label list の 12 個"),
    (r"make log-openrc", r"何も出ない|読むもの|読む対象|never written|no log",
     "build-openrc.sh はログを書かないので make log-openrc は何も出ない"),
    (r"REPRODUCIBLE_BUILD.*(どこも|誰も)設定", r"誤り",
     "build-system/Makefile が REPRODUCIBLE_BUILD ?= yes を設定している"),
    (r"isn \(Package Manager\)|isn info|isn install", None,
     "パッケージマネージャー isn は存在しない（設計上持たない）"),
    (r"軽量・高速|[Ll]ightweight, [Ff]ast", r"musl",
     "起動時間は Alpine・Ubuntu と差が出ていない。「高速」を名乗らない"),
    (r"glibcの1/10", None, "根拠を示せない比較"),
    (r"Linux ?カーネル 6\.6|linux-6\.6\.|BusyBox 1\.36\.1|musl 1\.2\.4|OpenRC 0\.52", r"当時|かつて|以前|まで|→|のつもり|で既知|の頃|古い版|が 1\.38|libcap は|historical|v[0-2]\.",
     "古い構成要素の版。現在の版は versions.mk"),
]

COMPILED = [(re.compile(p), re.compile(u) if u else None, why) for p, u, why in RULES]


def main() -> int:
    files = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                           check=True).stdout.split("\n")
    hits = []
    for f in files:
        if not f or f in HISTORY or not TARGET.search(f):
            continue
        if f == "scripts/check-stale-docs.py":
            continue
        try:
            lines = open(f, encoding="utf-8").read().split("\n")
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(lines, 1):
            for pat, unless, why in COMPILED:
                if pat.search(line) and not (unless and unless.search(line)):
                    hits.append(f"{f}:{n}: {why}\n    {line.strip()[:160]}")
    if hits:
        print(f"古い記述が {len(hits)} 件見つかりました:\n")
        print("\n".join(hits))
        print("\n直すか、意図して残すなら scripts/check-stale-docs.py の unless / HISTORY を更新してください。")
        return 1
    print("古い記述なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
