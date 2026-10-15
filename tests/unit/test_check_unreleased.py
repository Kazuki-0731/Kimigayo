"""
scripts/check-unreleased.py のテスト

2026-10-15: CHANGELOG の [Unreleased] に区分ごとに書く運用にした
（SPECIFICATION.md 10.2）。書き忘れと「次の版」の食い違いを CI で止める。
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check-unreleased.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_unreleased", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cu = _load()

pytestmark = pytest.mark.unit


def changelog(next_line, major="", minor="", patch="", none=""):
    return f"""# Changelog

## [Unreleased]

<!--
**次の版: メジャー** コメントの中は読まない
-->

{next_line}

### メジャー
{major}
### マイナー
{minor}
### パッチ
{patch}
### リリースしない（次のリリースに相乗りする）
{none}
## [3.1.0] "Himawari" (向日葵) - 2026-10-14

### Security
- 過去の版の項目は見ない
"""


def test_nothing_changed_passes():
    assert cu.check([], "v3.1.0", changelog("**次の版: なし**（まだ無い）")) == []


def test_docs_only_change_needs_no_level():
    text = changelog("**次の版: なし**", none="- 文書を直した\n")
    assert cu.check(["README.md", ".github/workflows/on-push-and-pr-build-and-verify-all-images.yml"], "v3.1.0", text) == []


def test_image_input_without_entry_fails():
    errors = cu.check(["src/busybox/patches/0024-x.patch"], "v3.1.0",
                      changelog("**次の版: なし**"))
    assert len(errors) == 1 and "src/busybox/patches/0024-x.patch" in errors[0]


def test_image_input_declared_as_not_released_passes():
    text = changelog("**次の版: なし**",
                     none="- コメントだけ直した\n  （`scripts/build-rootfs.sh`）\n")
    assert cu.check(["scripts/build-rootfs.sh"], "v3.1.0", text) == []


def test_patch_entry_with_version_passes():
    text = changelog("**次の版: パッチ（3.1.1）**", patch="- CVE を直した\n")
    assert cu.check(["src/busybox/patches/0024-x.patch"], "v3.1.0", text) == []


def test_largest_level_wins():
    text = changelog("**次の版: パッチ（3.1.1）**", minor="- 版上げ\n", patch="- CVE\n")
    errors = cu.check(["versions.mk"], "v3.1.0", text)
    assert len(errors) == 1 and "マイナー" in errors[0]


@pytest.mark.parametrize("level, want", [
    ("メジャー", "4.0.0"), ("マイナー", "3.2.0"), ("パッチ", "3.1.1"),
])
def test_version_must_match_bump_from_tag(level, want):
    kw = {"メジャー": "major", "マイナー": "minor", "パッチ": "patch"}[level]
    ok = changelog(f"**次の版: {level}（{want}）**", **{kw: "- x\n"})
    assert cu.check([], "v3.1.0", ok) == []
    bad = changelog(f"**次の版: {level}（9.9.9）**", **{kw: "- x\n"})
    assert any(want in e for e in cu.check([], "v3.1.0", bad))


def test_level_without_entries_fails():
    errors = cu.check([], "v3.1.0", changelog("**次の版: マイナー（3.2.0）**"))
    assert len(errors) == 1 and "なし" in errors[0]


@pytest.mark.parametrize("path, hit", [
    ("versions.mk", True),
    ("Dockerfile", True),
    ("src/libc/patches/0001-x.patch", True),
    ("LICENSES/MIT.txt", True),
    ("src/kernel/config/README.md", False),   # カーネルはイメージに入らない
    ("scripts/build-kernel.sh", False),
    ("examples/nginx/Dockerfile", False),
    ("Dockerfile.runtime.bak", False),
])
def test_image_inputs(path, hit):
    assert cu.is_image_input(path) is hit


def test_current_changelog_parses():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    level, _, sections = cu.parse_unreleased(text)
    assert level in ("なし", *cu.LEVELS)
    assert set(sections) >= set(cu.LEVELS)
