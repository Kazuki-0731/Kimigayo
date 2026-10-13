#!/usr/bin/env python3
"""上流の修正待ちの CVE に、修正が出たかを確かめる。

使い方:
    python3 -I scripts/watch-upstream-fixes.py           # 報告を標準出力に
    GITHUB_OUTPUT=... python3 -I scripts/watch-upstream-fixes.py
        # fix_available=true|false も書く（security.yml が Issue を立てる）

なぜ必要か:
    CVE-2026-108119（BusyBox の tar）は 2026-10-14 時点で上流にも
    Alpine にも修正が無く、「上流の修正を待つ」と決めた。待つと決めたものは
    誰かが見に行かない限り忘れられる。Hook は会話中のローカル操作でしか
    動かず上流を見られないので、毎日の security.yml でここを回す。

見るもの（どちらかで修正が見つかれば「出た」とする）:
    Debian   security-tracker の CVE ページ。unstable の Fixed Version が
             (unfixed) 以外になったら修正あり。Notes に修正パッチの URL が
             載ることが多い
    Alpine   aports の main/<pkg>/APKBUILD（master と <ALPINE_VERSION>-stable）。
             CVE ID が現れたら（secfixes かパッチ名）修正あり。
             これまでの CVE パッチは aports と sha512 で突合して取り込んでいる

取り込んだら:
    src/<component>/patches/ に CVE ID 入りのファイル名で置けば、
    ここでは「取り込み済み。WATCH から消す」と出る。WATCH から消す。
"""
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (CVE ID, Debian / Alpine のソースパッケージ名, パッチの置き場)
WATCH = [
    ("CVE-2026-108119", "busybox", "src/busybox/patches"),
]

DEBIAN_URL = "https://security-tracker.debian.org/tracker/{cve}"
# aports は GitHub の公式ミラーから取る。gitlab.alpinelinux.org は GitHub
# Actions からのアクセスをボット扱いして 418 を返す（2026-10-14 に実測。
# 手元からは通るので気づきにくい）。ミラーの中身は GitLab と同じ
ALPINE_URL = ("https://raw.githubusercontent.com/alpinelinux/aports/"
              "{branch}/main/{pkg}/APKBUILD")


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def debian_status(html, pkg):
    """unstable の Fixed Version と Notes の URL を返す。表が読めなければ None。"""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    m = re.search(re.escape(pkg) + r" source \(unstable\) (\S+)", text)
    if not m:
        return None
    notes = re.findall(r"https?://\S+", text.split(" Notes ", 1)[1]) if " Notes " in text else []
    return m.group(1), notes


def alpine_version():
    for line in (ROOT / "versions.mk").read_text().splitlines():
        m = re.match(r"ALPINE_VERSION\s*\?=\s*(\S+)", line)
        if m:
            return m.group(1)
    return None


def main():
    found = False
    lines = []
    for cve, pkg, patch_dir in WATCH:
        if any(cve in p.name for p in (ROOT / patch_dir).glob("*.patch")):
            lines.append(f"- {cve}: 取り込み済み（{patch_dir}）。WATCH から消す")
            continue

        status = debian_status(fetch(DEBIAN_URL.format(cve=cve)), pkg)
        if status is None:
            # 表の形が変わったら黙って「未修正」と読まない
            print(f"[ERROR] {cve}: Debian の表を読めない（ページの形が変わった？）",
                  file=sys.stderr)
            return 1
        fixed, notes = status
        debian_fixed = fixed != "(unfixed)"

        alpine_hits = []
        for branch in ("master", f"{alpine_version()}-stable"):
            if cve in fetch(ALPINE_URL.format(branch=branch, pkg=pkg)):
                alpine_hits.append(branch)

        if debian_fixed or alpine_hits:
            found = True
            lines.append(f"- **{cve}（{pkg}）: 上流に修正が出た**")
            if debian_fixed:
                lines.append(f"  - Debian unstable: {fixed} で修正（{DEBIAN_URL.format(cve=cve)}）")
            for b in alpine_hits:
                lines.append(f"  - Alpine aports {b}: APKBUILD に {cve} がある"
                             f"（{ALPINE_URL.format(branch=b, pkg=pkg)}）")
            for n in notes:
                lines.append(f"  - 参考: {n}")
            lines.append(f"  - 取り込み: {patch_dir}/ に CVE ID 入りの名前でパッチを置き、"
                         "この WATCH から消す（CLAUDE.md「パッチはなぜ存在するか」）")
        else:
            lines.append(f"- {cve}（{pkg}）: まだ修正なし（Debian unstable: {fixed}・Alpine: なし）")

    print("\n".join(lines))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"fix_available={'true' if found else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
