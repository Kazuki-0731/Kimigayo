#!/usr/bin/env python3
"""CHANGELOG.md の [Unreleased] が、前回のタグからの変更と合っているかを検査する。

SPECIFICATION.md「10.2 バージョニングとリリースの方針」で、溜まった変更は
[Unreleased] に区分（メジャー／マイナー／パッチ／リリースしない）ごとに
push した時点で書くと決めた（2026-10-15）。文章のルールだと書き忘れるので、
ここで止める（CLAUDE.md「判断が絡まないミスは文章にしない」）。

検査すること:
  1. 公開イメージの中身に効くファイル（IMAGE_INPUTS）が前回のタグから
     変わっているのに、メジャー・マイナー・パッチのどれにも項目が無い。
     中身を変えない変更（コメントだけの修正など）なら、
     「リリースしない」の項目にそのパスを `...` で書けば通る
  2. 「次の版」が、項目のある区分のうちいちばん大きいものと合っていない。
     版を上げるなら、前回のタグから計算した版を括弧で添える
     （例: **次の版: マイナー（3.2.0）**）

前回のタグは git describe で探すので、CI では fetch-depth: 0 が要る。
"""
from __future__ import annotations

import re
import subprocess
import sys

CHANGELOG = "CHANGELOG.md"

# 公開イメージの中身に効く入力。前方一致（/ で終わるものはディレクトリ）。
# 迷ったら入れる側に倒す（入れすぎても「リリースしない」に書けば通る）。
IMAGE_INPUTS = (
    "versions.mk",                       # 構成要素の版
    "Dockerfile",                        # ビルド環境（Alpine・ツールチェーン・fortify-headers）
    "Dockerfile.runtime",
    "build-system/Makefile",             # CFLAGS・SOURCE_DATE_EPOCH
    "LICENSES/",                         # /usr/share/licenses/
    "src/busybox/",                      # config・パッチ
    "src/libc/",                         # musl のパッチ
    "scripts/build-rootfs.sh",
    "scripts/build-musl.sh",
    "scripts/build-busybox.sh",
    "scripts/build-openrc.sh",
    "scripts/apply-busybox-patches.sh",
    "scripts/apply-musl-patches.sh",
    "scripts/get-version.sh",            # /etc/os-release
    "scripts/get-codename.sh",
)

# 大きい順
LEVELS = ("メジャー", "マイナー", "パッチ")
NOT_RELEASED = "リリースしない"

NEXT = re.compile(r"\*\*次の版:\s*([^*（(]+?)\s*(?:[（(]([0-9]+\.[0-9]+\.[0-9]+)[）)])?\s*\*\*")
TAG = re.compile(r"^v([0-9]+)\.([0-9]+)\.([0-9]+)$")


def is_image_input(path: str) -> bool:
    for p in IMAGE_INPUTS:
        if p.endswith("/"):
            if path.startswith(p):
                return True
        elif path == p:
            return True
    return False


def parse_unreleased(text: str):
    """[Unreleased] 節を読み、(次の版の区分, 添えた版, {区分: [項目]}) を返す。"""
    m = re.search(r"^## \[Unreleased\][^\n]*\n(.*?)(?=^## \[)", text, re.M | re.S)
    if not m:
        m = re.search(r"^## \[Unreleased\][^\n]*\n(.*)", text, re.M | re.S)
    if not m:
        raise ValueError("CHANGELOG.md に ## [Unreleased] がありません")
    body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)

    nm = NEXT.search(body)
    if not nm:
        raise ValueError("[Unreleased] に **次の版: ...** の行がありません")
    next_level, next_version = nm.group(1).strip(), nm.group(2)

    sections = {}
    current = None
    for line in body.split("\n"):
        h = re.match(r"^### (.+?)\s*$", line)
        if h:
            title = h.group(1)
            current = next((k for k in (*LEVELS, NOT_RELEASED) if title.startswith(k)), None)
            if current:
                sections.setdefault(current, [])
            continue
        if current and line.startswith("- "):
            sections[current].append(line)
        elif current and sections[current] and line.startswith("  "):
            sections[current][-1] += "\n" + line   # 続きの行
    return next_level, next_version, sections


def bump(tag: str, level: str) -> str:
    m = TAG.match(tag)
    if not m:
        raise ValueError(f"タグ {tag} が vX.Y.Z の形ではありません")
    x, y, z = map(int, m.groups())
    if level == "メジャー":
        return f"{x + 1}.0.0"
    if level == "マイナー":
        return f"{x}.{y + 1}.0"
    return f"{x}.{y}.{z + 1}"


VERSION_HEADING = re.compile(r"^## \[(\d+)\.(\d+)\.(\d+)\]", re.M)


def released_newer_than(text: str, tag: str) -> bool:
    """CHANGELOG に、前回のタグより新しい版見出し（## [X.Y.Z]）があるか。"""
    m = TAG.match(tag)
    if not m:
        return False
    last = tuple(int(x) for x in m.groups())
    return any(tuple(int(x) for x in h) > last for h in VERSION_HEADING.findall(text))


def check(changed: list[str], tag: str, text: str) -> list[str]:
    """問題の一覧を返す（空なら通過）。"""
    errors = []
    next_level, next_version, sections = parse_unreleased(text)

    expected = next((lv for lv in LEVELS if sections.get(lv)), "なし")
    if next_level != expected:
        errors.append(f"「次の版」が {next_level} になっていますが、項目のある区分から決まるのは {expected} です")
    elif expected != "なし":
        want = bump(tag, expected)
        if next_version != want:
            errors.append(f"「次の版」に版を添えてください: **次の版: {expected}（{want}）**"
                          f"（前回のタグ {tag} から計算。いまは {next_version or 'なし'}）")

    inputs = [p for p in changed if is_image_input(p)]
    # リリース作業中は、画像の変更が [Unreleased] から版見出し（## [X.Y.Z]）へ
    # 移される。前回のタグより新しい版見出しが既にあれば、その変更はそこに
    # 記載済みなので [Unreleased] が空でよい（タグを打てば次からこの判定は不要）。
    if inputs and expected == "なし" and released_newer_than(text, tag):
        inputs = []
    if inputs and expected == "なし":
        declared = "\n".join(sections.get(NOT_RELEASED, []))
        missing = [p for p in inputs if f"`{p}`" not in declared]
        if missing:
            errors.append(
                f"{tag} から公開イメージの中身に効くファイルが変わっていますが、"
                "[Unreleased] のメジャー・マイナー・パッチに項目がありません:\n"
                + "\n".join(f"    {p}" for p in missing)
                + "\n  区分を付けて項目を足してください（SPECIFICATION.md 10.2）。"
                "\n  中身を変えない変更なら、「リリースしない」の項目にパスを `...` で書いてください。")
    return errors


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main() -> int:
    try:
        tag = git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*.[0-9]*.[0-9]*").strip()
    except subprocess.CalledProcessError:
        print("前回のタグが見つかりません（CI なら actions/checkout に fetch-depth: 0 が要る）")
        return 1
    changed = [p for p in git("diff", "--name-only", f"{tag}..HEAD").split("\n") if p]
    with open(CHANGELOG, encoding="utf-8") as f:
        text = f.read()
    try:
        errors = check(changed, tag, text)
    except ValueError as e:
        print(e)
        return 1
    if errors:
        print("CHANGELOG.md の [Unreleased] が前回のタグからの変更と合っていません:\n")
        print("\n\n".join(f"- {e}" for e in errors))
        return 1
    _, next_version, _ = parse_unreleased(text)
    print(f"[Unreleased] は {tag} からの変更と合っています（次の版: {next_version or 'なし'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
