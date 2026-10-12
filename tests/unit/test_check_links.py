"""
scripts/check-links.py のアンカー判定（GitHub の見出しスラッグ）のテスト

2026-10-13: ファイルの存在しか見ておらず、壊れたアンカーに気づけなかった。
スラッグの規則は GitHub（github-slugger）に合わせている。
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check-links.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_links", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cl = _load()

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("text, slug", [
    ("Table of Contents", "table-of-contents"),
    ("VPS (Docker)", "vps-docker"),
    ("Hello, World!", "hello-world"),
    ("snake_case and kebab-case", "snake_case-and-kebab-case"),
    ("a  b", "a--b"),                     # 連続スペースは潰さない
    ("v3.0.2", "v302"),
    ("テストスコープ", "テストスコープ"),
    ("攻撃面のベースライン（v3.0.2 実測、2026-10-12）",
     "攻撃面のベースラインv302-実測2026-10-12"),
    ("BusyBox の cpio はディレクトリを脱出できた（v3.0.1 まで。修正済み）",
     "busybox-の-cpio-はディレクトリを脱出できたv301-まで修正済み"),
    ("ビルド・計測", "ビルド計測"),
    ("「判断」→ 実装", "判断-実装"),
    ("✨ 機能追加", "-機能追加"),           # 絵文字は消えて先頭の空白が残る
    ("VPS (Docker) {#vps}", "vps-docker-vps"),  # GitHub は {#id} を解さない
])
def test_heading_slug(text, slug):
    assert cl.heading_slug(text) == slug


@pytest.mark.parametrize("raw, text", [
    ("`make build` の使い方", "make build の使い方"),
    ("**重要** な _注意_", "重要 な 注意"),
    ("[README](README.md) を読む", "README を読む"),
    ("`KERNEL_VERSION` と snake_case", "KERNEL_VERSION と snake_case"),
    ("<a name=\"x\"></a>見出し", "見出し"),
])
def test_heading_text_strips_inline_markup(raw, text):
    assert cl.heading_text(raw) == text


def test_duplicate_headings_get_numbered():
    s = cl.Slugger()
    assert [s.slug("Usage"), s.slug("Usage"), s.slug("Usage")] == \
        ["usage", "usage-1", "usage-2"]


def test_duplicate_avoids_existing_numbered_heading():
    # github-slugger と同じ: 「a-1」が先にあれば 2つ目の「a」は a-2
    s = cl.Slugger()
    assert [s.slug("a"), s.slug("a-1"), s.slug("a")] == ["a", "a-1", "a-2"]


def test_collect_anchors_handles_code_setext_and_html():
    md = "\n".join([
        "# Title",
        "",
        "```sh",
        "# not a heading",
        "```",
        "",
        "Setext Heading",
        "--------------",
        "",
        "- list item",
        "---",
        "",
        '<a name="custom-anchor"></a>',
        '<div id="other-id"></div>',
        "## Title",
        "### Closed ###",
    ])
    anchors = cl.collect_anchors(md)
    assert anchors == {"title", "setext-heading", "custom-anchor",
                       "other-id", "title-1", "closed"}


def test_anchor_exists_decodes_and_ignores_case():
    anchors = {"テストスコープ", "usage"}
    assert cl.anchor_exists("%E3%83%86%E3%82%B9%E3%83%88%E3%82%B9%E3%82%B3%E3%83%BC%E3%83%97", anchors)
    assert cl.anchor_exists("Usage", anchors)
    assert cl.anchor_exists("", anchors)
    assert not cl.anchor_exists("missing", anchors)


def test_link_targets_skip_inline_code_and_titles():
    line = 'see [a](x.md#one "Title") and `[b](y.md#two)` and [c](<z w.md#three>)'
    assert [t for _l, t in cl.link_targets(line)] == ["x.md#one", "z w.md#three"]
