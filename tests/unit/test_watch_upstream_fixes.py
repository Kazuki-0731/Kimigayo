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


def test_package_page_lists_all_sections():
    html = """<h2>Open issues</h2><table><tr><td><a href="/tracker/CVE-2026-1">x</a>
    </table><h2>Resolved issues</h2><table><tr><td><a href="/tracker/CVE-2020-2">y</a>"""
    assert watch.debian_package_cves(html) == {"CVE-2026-1", "CVE-2020-2"}


def test_package_page_with_unknown_shape_fails():
    with pytest.raises(watch.WatchError):
        watch.debian_package_cves("<html>maintenance</html>")


def test_apkbuild_patches_and_cves():
    text = """pkgver=1.38.0
pkgrel=7
source="https://busybox.net/downloads/busybox-$pkgver.tar.bz2
	0007-tar-fix-TOCTOU-symlink-race-condition.patch
	0033-awk.c-fix-CVE-2023-42366-bug-15874.patch
	bbsuid.c
	"
# secfixes:
#   1.37.0-r27:
#     - CVE-2025-46394
"""
    ver, patches, cves = watch.apkbuild_info(text)
    assert ver == "1.38.0"
    assert patches == ["0007-tar-fix-TOCTOU-symlink-race-condition.patch",
                       "0033-awk.c-fix-CVE-2023-42366-bug-15874.patch"]
    assert cves == {"CVE-2023-42366", "CVE-2025-46394"}


def test_triage_rejects_unknown_status(tmp_path):
    f = tmp_path / "t.tsv"
    f.write_text("CVE-2026-1\tbusybox\tmaybe\tnote\n")
    with pytest.raises(watch.WatchError):
        watch.load_triage(f)


def test_tracked_triage_file_is_valid():
    # 形の崩れた行があると毎日の監視が失敗するので、ここで止める
    triage = watch.load_triage()
    names = {c["name"] for c in watch.COMPONENTS}
    for key, (component, status, _) in triage.items():
        assert component in names, key
        assert key.startswith(("CVE-", "alpine:", "upstream:")), key


def test_security_commit_filter():
    commits = [
        ("382008b3f07d", "tar: protect against Symlink+Hardlink attack", ""),
        ("15666f3e9a0b", "awk: fix 1-byte heap-buffer-overflow in next_token()", ""),
        ("9d961aff6f7b", "Install lsblk to /bin instead of /usr/bin", ""),
        ("aaaaaaaaaaaa", "ash: small cleanup", "Fixes CVE-2026-1"),
    ]
    assert [sha for sha, _ in watch.security_commits(commits)] == [
        "382008b3f07d", "15666f3e9a0b", "aaaaaaaaaaaa"]
