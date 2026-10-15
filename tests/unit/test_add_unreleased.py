"""
scripts/add-unreleased.py のテスト

2026-10-15: base-image-update.yml が版上げの PR を作るときに、CHANGELOG の
[Unreleased] へ区分付きで 1 行足すようにした。足した結果が
check-unreleased.py を通ることまで見る。
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


au = _load("add_unreleased", "add-unreleased.py")
cu = _load("check_unreleased", "check-unreleased.py")

pytestmark = pytest.mark.unit

EMPTY = """# Changelog

## [Unreleased]

<!--
コメント
-->

**次の版: なし**（まだ無い）

### メジャー

### マイナー

### パッチ

### リリースしない（次のリリースに相乗りする）

- 文書を直した

## [3.1.0] "Himawari" (向日葵) - 2026-10-14

### マイナー
- 過去の版の見出しには足さない
"""


@pytest.mark.parametrize("current, latest, level", [
    ("1.38.0", "1.38.1", "パッチ"),
    ("1.2.6", "1.2.7", "パッチ"),
    ("1.38.0", "1.39.0", "マイナー"),
    ("0.63.2", "0.64.0", "マイナー"),
    ("1.2.6", "2.0.0", "マイナー"),     # メジャーは人が決める
    ("1.2", "1.2.1", "マイナー"),       # 形が変わったら大きい方
])
def test_level_for(current, latest, level):
    assert au.level_for(current, latest) == level


def test_add_patch_to_empty():
    out = au.add_entry(EMPTY, "パッチ", "musl を上げた", "v3.1.0")
    assert "**次の版: パッチ（3.1.1）**\n" in out
    assert "### パッチ\n\n- musl を上げた\n\n### リリースしない" in out
    assert "まだ無い" not in out
    assert out.endswith("- 過去の版の見出しには足さない\n")
    assert cu.check(["versions.mk"], "v3.1.0", out) == []


def test_minor_after_patch_raises_next_version():
    out = au.add_entry(EMPTY, "パッチ", "musl", "v3.1.0")
    out = au.add_entry(out, "マイナー", "BusyBox", "v3.1.0")
    assert "**次の版: マイナー（3.2.0）**" in out
    assert out.count("**次の版:") == 1
    assert cu.check(["versions.mk"], "v3.1.0", out) == []


def test_appends_after_existing_items():
    out = au.add_entry(EMPTY, "マイナー", "一つ目", "v3.1.0")
    out = au.add_entry(out, "マイナー", "二つ目", "v3.1.0")
    assert "### マイナー\n\n- 一つ目\n- 二つ目\n\n### パッチ" in out


def test_current_changelog_accepts_entry():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    out = au.add_entry(text, "マイナー", "BusyBox を上げた", "v3.1.0")
    assert cu.check(["versions.mk"], "v3.1.0", out) == []
