#!/usr/bin/env python3
"""構成要素の版上げを CHANGELOG.md の [Unreleased] に区分付きで 1 行足す。

component-update-pr.yml が更新 PR を作るときに呼ぶ。手で書き足さないと
check-unreleased.py が CI を落とすので、PR を作る側で書いておく
（SPECIFICATION.md「10.2 バージョニングとリリースの方針」）。

使い方: python3 scripts/add-unreleased.py <名前> <現在の版> <新しい版>
  例:   python3 scripts/add-unreleased.py BusyBox 1.38.0 1.39.0

区分は版の差から決める。最後の数字だけが変わればパッチ、それより上が
変われば上流のマイナー以上の版上げなのでマイナー。メジャーにはしない
（世代の変わり目は人が決める）。項目を足したあと「次の版」を、項目のある
区分のうちいちばん大きいものと前回のタグから計算した版に書き換える。

前回のタグは git describe で探すので、CI では fetch-depth: 0 が要る。
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"


def _load_check():
    spec = importlib.util.spec_from_file_location("check_unreleased", ROOT / "scripts" / "check-unreleased.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cu = _load_check()


def level_for(current: str, latest: str) -> str:
    a, b = current.split("."), latest.split(".")
    if len(a) != len(b) or len(a) < 2:
        return "マイナー"   # 版の形が変わったら大きい方に倒す
    return "パッチ" if a[:-1] == b[:-1] else "マイナー"


def add_entry(text: str, level: str, entry: str, tag: str) -> str:
    """[Unreleased] の level の節の末尾に entry を足し、「次の版」を書き直す。"""
    m = re.search(r"^## \[Unreleased\][^\n]*\n", text, re.M)
    if not m:
        raise ValueError("CHANGELOG.md に ## [Unreleased] がありません")
    start = m.end()
    end_m = re.search(r"^## \[", text[start:], re.M)
    end = start + end_m.start() if end_m else len(text)
    lines = text[start:end].split("\n")

    head = next((i for i, l in enumerate(lines) if re.match(rf"^### {level}\s*$", l)), None)
    if head is None:
        raise ValueError(f"[Unreleased] に ### {level} がありません")
    nxt = next((i for i in range(head + 1, len(lines)) if lines[i].startswith("### ")), len(lines))
    body = lines[head + 1:nxt]
    while body and body[-1] == "":
        body.pop()
    if not body:
        body = [""]
    body += [f"- {entry}", ""]
    lines[head + 1:nxt] = body
    section = "\n".join(lines)

    _, _, sections = cu.parse_unreleased(text[:start] + section + text[end:])
    top = next(lv for lv in cu.LEVELS if sections.get(lv))
    new_next = f"**次の版: {top}（{cu.bump(tag, top)}）**"
    section, n = re.subn(r"^\*\*次の版:.*$", new_next, section, count=1, flags=re.M)
    if n != 1:
        raise ValueError("[Unreleased] に **次の版: ...** の行がありません")
    return text[:start] + section + text[end:]


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__.split("\n\n")[2])
        return 2
    name, current, latest = sys.argv[1:]
    try:
        tag = subprocess.run(["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*.[0-9]*.[0-9]*"],
                             capture_output=True, text=True, check=True, cwd=ROOT).stdout.strip()
    except subprocess.CalledProcessError:
        print("前回のタグが見つかりません（CI なら actions/checkout に fetch-depth: 0 が要る）")
        return 1
    level = level_for(current, latest)
    entry = (f"**{name} を {current} → {latest} に上げた**（`component-update-pr.yml` が自動検知。"
             "チェックサム・パッチ・ビルドオプションは PR で確かめる）")
    text = CHANGELOG.read_text(encoding="utf-8")
    try:
        CHANGELOG.write_text(add_entry(text, level, entry, tag), encoding="utf-8")
    except ValueError as e:
        print(e)
        return 1
    print(f"[Unreleased] の {level} に足した: {name} {current} -> {latest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
