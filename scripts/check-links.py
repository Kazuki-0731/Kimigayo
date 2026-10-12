#!/usr/bin/env python3
"""追跡ファイル基準で Markdown の相対リンクとアンカーを監査する。

ローカルのファイルシステムで判定してはいけない。.gitignore されている
ファイル（TODO.md など）が手元にあると「リンクは生きている」と誤判定し、
clone した人だけ壊れている状態を見逃す。公開リポジトリでは
**git が追跡しているか**だけが基準。

アンカー（`#見出し` / `file.md#見出し`）も見る。以前はファイルの存在
しか見ておらず、docs/security/PENETRATION_TEST.md の壊れたアンカーに
気づけなかった（2026-10-13）。見出しからアンカーを作る規則は GitHub
（github-slugger）に合わせる → heading_slug() のコメント。
"""
import os
import posixpath
import re
import subprocess
import sys
import unicodedata
from urllib.parse import unquote

LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
SETEXT_H1 = re.compile(r"^ {0,3}=+[ \t]*$")
SETEXT_H2 = re.compile(r"^ {0,3}-+[ \t]*$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
# <a name="x"> / <span id="x"> などの明示的なアンカー
HTML_ANCHOR = re.compile(r"""<[A-Za-z][^>]*?\b(?:name|id)\s*=\s*["']([^"']+)["']""")


# ---------------------------------------------------------------------------
# 見出し → アンカー（GitHub 互換）
# ---------------------------------------------------------------------------

def _keep_char(ch: str) -> bool:
    """github-slugger が残す文字か。

    残すのは文字（L*）・結合記号（M*）・数字（N*）・連結句読点（Pc。
    `_` を含む）・ハイフン・半角スペースだけ。それ以外の記号・句読点は
    消える。日本語の文字（漢字・かな・長音符「ー」）は L* なので残り、
    「」（）、。・→ や絵文字は消える。
    """
    if ch in ("-", " "):
        return True
    cat = unicodedata.category(ch)
    return cat[0] in ("L", "M", "N") or cat == "Pc"


def heading_slug(text: str) -> str:
    """描画後の見出しテキストから GitHub のアンカーを作る（重複処理は別）。

    github-slugger と同じ: 小文字化 → 許可外の文字を削除 →
    半角スペースを1つずつ `-` に置換（連続スペースは `--` になる）。
    """
    kept = "".join(ch for ch in text.lower() if _keep_char(ch))
    return kept.replace(" ", "-")


def heading_text(raw: str) -> str:
    """Markdown の見出し（# を除いた部分）を描画後のテキストに近づける。

    コードスパンの中身はそのまま残し、それ以外ではリンク・画像を
    ラベルに、HTML タグを除去、強調記号（* と語境界の _）を除く。
    """
    out = []
    pos = 0
    for m in re.finditer(r"(`+)(.+?)\1", raw):
        out.append(_strip_inline(raw[pos:m.start()]))
        out.append(m.group(2).strip())
        pos = m.end()
    out.append(_strip_inline(raw[pos:]))
    return "".join(out).strip()


def _strip_inline(seg: str) -> str:
    seg = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", seg)
    seg = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", seg)
    seg = re.sub(r"\[([^\]]*)\]\[[^\]]*\]", r"\1", seg)
    seg = re.sub(r"<[^>]+>", "", seg)
    seg = seg.replace("*", "")
    seg = re.sub(r"(?<![0-9A-Za-z])_+|_+(?![0-9A-Za-z])", "", seg)
    return seg


class Slugger:
    """github-slugger の重複処理をそのまま移したもの。

    同じ見出しが2つ目以降に現れると -1, -2 ... が付く。
    すでに存在する名前（例: 見出し「a-1」）とも衝突しないよう回す。
    """

    def __init__(self):
        self.occurrences = {}

    def slug(self, text: str) -> str:
        result = heading_slug(text)
        original = result
        while result in self.occurrences:
            self.occurrences[original] += 1
            result = "%s-%d" % (original, self.occurrences[original])
        self.occurrences[result] = 0
        return result


def strip_code(lines):
    """フェンスの中を空行に置き換えた行リストを返す（行番号は保つ）。"""
    out = []
    fence = None
    for line in lines:
        if fence is None:
            m = FENCE.match(line)
            if m:
                fence = m.group(1)
                out.append("")
                continue
            out.append(line)
        else:
            s = line.strip()
            if s and s[0] == fence[0] and set(s) == {fence[0]} and len(s) >= len(fence):
                fence = None
            out.append("")
    return out


def collect_anchors(text: str) -> set:
    """Markdown 本文から、リンクできるアンカーの集合を作る。"""
    lines = strip_code(text.split("\n"))
    slugger = Slugger()
    anchors = set()
    prev = ""
    prev_is_para = False
    for line in lines:
        m = ATX.match(line)
        is_para = False
        if m:
            raw = m.group(2) or ""
            raw = re.sub(r"(^|[ \t]+)#+[ \t]*$", "", raw)  # 閉じの ###
            anchors.add(slugger.slug(heading_text(raw)))
        elif prev_is_para and (SETEXT_H1.match(line) or SETEXT_H2.match(line)):
            anchors.add(slugger.slug(heading_text(prev.strip())))
        elif line.strip() and not re.match(r"^ {0,3}([-*+>|]|\d+[.)]|<)", line):
            is_para = True
        for a in HTML_ANCHOR.findall(line):
            anchors.add(a)
        prev, prev_is_para = line, is_para
    return anchors


def anchor_exists(fragment: str, anchors: set) -> bool:
    frag = unquote(fragment)
    if not frag or frag == "top":
        return True
    # GitHub はページ側の JS で大文字小文字を区別せずに当てる
    return frag in anchors or frag.lower() in anchors


def link_targets(line: str):
    """行から (label, target) を返す。インラインコードの中は除く。"""
    line = re.sub(r"(`+).*?\1", "", line)
    for label, target in LINK.findall(line):
        target = target.strip()
        if target.startswith("<") and ">" in target:
            target = target[1:target.index(">")]
        else:
            # [x](file.md "title") の title を外す
            target = re.split(r"\s+", target, maxsplit=1)[0]
        yield label, target


# ---------------------------------------------------------------------------
# 本体
# ---------------------------------------------------------------------------

def main() -> int:
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

    texts = {}

    def read(f):
        if f not in texts:
            try:
                with open(os.path.join(root, f), encoding="utf-8") as fh:
                    texts[f] = fh.read()
            except Exception:
                texts[f] = None
        return texts[f]

    anchor_cache = {}

    def anchors_of(f):
        if f not in anchor_cache:
            t = read(f)
            anchor_cache[f] = collect_anchors(t) if t is not None else None
        return anchor_cache[f]

    broken = []
    bad_anchors = []
    for f in sorted(x for x in tracked if x.endswith(".md")):
        text = read(f)
        if text is None:
            continue
        base = posixpath.dirname(f)
        raw_lines = text.split("\n")
        code_free = strip_code(raw_lines)
        for lineno, line in enumerate(raw_lines, 1):
            for _label, target in LINK.findall(line):
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

            # アンカーはコードブロック・インラインコードの外だけを見る
            for _label, target in link_targets(code_free[lineno - 1]):
                if target.startswith(("http://", "https://", "mailto:")) or "#" not in target:
                    continue
                path_part, frag = target.split("#", 1)
                if path_part:
                    dest = posixpath.normpath(posixpath.join(base, path_part)) if base \
                        else posixpath.normpath(path_part)
                else:
                    dest = f
                if not dest.endswith(".md") or dest not in tracked:
                    continue  # ファイル側の判定は上で行う。.md 以外は見ない
                anchors = anchors_of(dest)
                if anchors is None or anchor_exists(frag, anchors):
                    continue
                bad_anchors.append((f, lineno, target))

    status = 0
    if broken:
        status = 1
        print("追跡されていないものを指すリンク: %d 件\n" % len(broken))
        print("%-44s %-5s %-34s %s" % ("ファイル", "行", "リンク先", "手元には"))
        print("-" * 104)
        for f, lineno, target, on_disk in broken:
            mark = "★ある（ローカルでは気づけない）" if on_disk else "無い"
            print("%-44s %-5d %-34s %s" % (f, lineno, target, mark))
        print()
    if bad_anchors:
        status = 1
        print("存在しない見出しを指すアンカー: %d 件\n" % len(bad_anchors))
        for f, lineno, target in bad_anchors:
            print("%s:%d -> %s" % (f, lineno, target))
        print()
    if status == 0:
        print("リンク切れなし（ファイル・アンカーとも）")
    return status


if __name__ == "__main__":
    sys.exit(main())
