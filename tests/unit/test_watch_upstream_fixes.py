"""scripts/watch-upstream-fixes.py の判定を固定する。

上流の修正待ちを知らせる仕組みなので、読み違えると「修正が出たのに
黙っている」状態になる。Debian の表の読み方と、取り込み済みの判定を見る。
ネットワークには出ない。
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "watch-upstream-fixes.py"


def _load():
    spec = importlib.util.spec_from_file_location("watch_upstream_fixes", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


watch = _load()
pytestmark = pytest.mark.unit

# security-tracker.debian.org の表の形（2026-10-14 の実物を縮めたもの）
UNFIXED = """<table><tr><td>busybox</td><td>source</td><td>(unstable)</td>
<td>(unfixed)</td><td></td><td>1150771</td></tr></table>
<pre>Notes</pre> [trixie] - busybox &lt;no-dsa&gt;
https://bugzilla.redhat.com/show_bug.cgi?id=2548611"""
FIXED = """<table><tr><td>busybox</td><td>source</td><td>(unstable)</td>
<td>1:1.38.0-3</td><td></td><td>1142472</td></tr></table>
<pre>Notes</pre> https://lists.busybox.net/pipermail/busybox/2026-June/092353.html"""


def test_unfixed_is_read_as_unfixed():
    fixed, _ = watch.debian_status(UNFIXED, "busybox")
    assert fixed == "(unfixed)"


def test_fixed_version_and_patch_url_are_read():
    fixed, notes = watch.debian_status(FIXED, "busybox")
    assert fixed == "1:1.38.0-3"
    assert notes == ["https://lists.busybox.net/pipermail/busybox/2026-June/092353.html"]


def test_unreadable_table_is_not_treated_as_unfixed():
    # 表が読めないときに「未修正」と読むと、修正が出ても黙ってしまう
    assert watch.debian_status("<html>maintenance</html>", "busybox") is None


def test_every_watched_cve_has_an_existing_patch_dir():
    for cve, pkg, patch_dir in watch.WATCH:
        assert cve.startswith("CVE-")
        assert (ROOT / patch_dir).is_dir(), patch_dir
