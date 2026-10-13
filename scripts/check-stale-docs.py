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
    # 2026-10-13: build-openrc.sh が build/logs/openrc-build.log を書くようになった。
    # 以前ここにあった「make log-openrc と書くな」の規則は逆になったので外し、
    # 「何も出ない」と書く古い記述の方を止める。
    (r"log-openrc[^\n]*(何も出ない|読む(もの|対象|先)が無い)|(ログ(ファイル)?を書かない)[^\n]*(OpenRC|openrc)|(OpenRC|openrc)[^\n]*ログ(ファイル)?を書かない",
     r"以前|当時|まで|was|used to",
     "build-openrc.sh は build/logs/openrc-build.log を書く。make log-openrc は動く"),
    (r"手動実行でも[^\n]*push|manual(ly)?[^\n]*(run|running)[^\n]*(also )?push|[Rr]unning `?release\.yml`? manually also pushes",
     r"以前|当時|まで|was|used to|no longer|しない|not push|does not",
     "release.yml の手動実行は Docker Hub に push しない（公開は v*.*.* タグの push だけ）"),
    (r"arm64 の OpenRC[^\n]*(付いていない|付いていません|渡していない|無い|を除く)|arm64 OpenRC[^\n]*no stack protector|Stack Protector は arm64 の OpenRC$",
     r"v3\.0\.2|以前|当時|まで|was|used to|until",
     "arm64 の OpenRC は main でスタック保護つき。付いていないのは v3.0.2 の公開イメージ（「v3.0.2 の」と明記する）"),
    (r"IMAGE_TYPE[^\n]*(省くと|省略すると|既定が無)|既定がずれ[^\n]*minimal",
     r"以前|当時|まで|was|used to",
     "build-system/Makefile の IMAGE_TYPE の既定は standard（export して BusyBox と rootfs に同じ値が届く）"),
    (r"compose[^\n]*ARCH=x86_64[^\n]*(固定|渡す|入れ)",
     r"以前|当時|まで|was|used to",
     "docker-compose.yml はもう ARCH を渡さない。ARCH=arm64 もコマンドラインで渡せば効く"),
    (r"ludeeus/action-shellcheck|additional_files: '\.claude/hooks'",
     r"以前|当時|まで|was|used to|していなかった",
     "CI の ShellCheck は koalaman/shellcheck を直接 docker run する（ludeeus の Action は外した）"),
    (r"UPDATES\.md",
     r"以前|当時|まで|was|used to|no |しない|not ",
     "base-image-update.yml は UPDATES.md をコミットしない（PR 本文だけ）"),
    (r"`?main`? ?/ ?`?develop`? への push|main/develop", None,
     "ci.yml のトリガーに develop は無い（main への push・PR と手動）"),
    (r"REPRODUCIBLE_BUILD.*(どこも|誰も)設定", r"誤り",
     "build-system/Makefile が REPRODUCIBLE_BUILD ?= yes を設定している"),
    (r"isn \(Package Manager\)|isn info|isn install", None,
     "パッケージマネージャー isn は存在しない（設計上持たない）"),
    (r"軽量・高速|[Ll]ightweight, [Ff]ast", r"musl",
     "起動時間は Alpine・Ubuntu と差が出ていない。「高速」を名乗らない"),
    (r"glibcの1/10", None, "根拠を示せない比較"),
    (r"FORTIFY[^\n]*(効果は確認|確認できていない|x86_64 だけ|x86_64 のみ)|効いているのは x86_64 だけ|x86_64 だけ効いて|effect of$|-D_FORTIFY_SOURCE=2 is not confirmed|only works on x86_64", None,
     "FORTIFY は main で両アーキに効く（2026-10-14 に arm64 を修正）。効いていないのは v3.0.2 の arm64 だけ"),
    (r"1\.38\.0[^\n]*(影響は未確認|対象かは)|影響は未確認[^\n]*108119|108119[^\n]*未確認", None,
     "CVE-2026-108119 は 1.38.0 も影響を受ける（2026-10-13 に公開イメージで実測）"),
    (r"`\.config` でこれらが効いているかは未確認|squashfs[^\n]*ビルドで有効になるかは", None,
     "カーネルの .config は 2026-10-13 に両アーキで確認済み（ARCHITECTURE.md のカーネル設定）"),
    (r"tests/property|test-property|configs/(openrc|sysctl)|(minimal|standard|extended)-x86_64\.config|kimigayo_(x86_64|arm64)_defconfig|/sbin/create-devices",
     r"削除|消した|以前|当時|まで|deleted|removed|実施した最適化|inittab\.optimized|^`configs/sysctl/99-kimigayo-performance\.conf`。$",
     "2026-10-14 に削除したもの（プロパティテスト・configs/・未使用のカーネル config・create-devices・Python モック）"),
    (r"image\.licenses=\"GPL-2\.0\"|LICENSES/BSD-2-Clause\.txt|musl libc \| MIT \| LICENSES/MIT\.txt", None,
     "イメージのライセンスは GPL-2.0-only AND MIT AND BSD-2-Clause AND BSD-3-Clause。musl・OpenRC・libcap の条文は LICENSES/ の上流の原文"),
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
