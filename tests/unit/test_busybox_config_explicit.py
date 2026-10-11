"""
BusyBox の config で「既定値に任せると危ない項目」が明示されているかを見る。

BusyBox の config は**書かないと Kconfig の既定値が入る**（`make oldconfig`）。
これで実際に 3 回事故を起こした:

- DPKG / DPKG_DEB / RPM（既定 y）— v3.0.0 までパッケージマネージャーが入っていた
- FEATURE_PATH_TRAVERSAL_PROTECTION（既定 n）— v3.0.1 まで cpio が展開先を脱出できた
- FEATURE_WGET_OPENSSL（既定 y）— v3.0.1 まで wget の HTTPS が取得後に SIGSEGV で落ちた
  （→ docs/troubleshooting/busybox-wget-https-segfault.md）

成果物の挙動は scripts/verify-image.sh が見るが、それはイメージを作ってから
しか分からない。ここでは config の行が消えた時点で落とす。
"""

import re
from pathlib import Path

import pytest

CONFIG_DIR = Path(__file__).resolve().parents[2] / "src" / "busybox" / "config"
VARIANTS = ["minimal", "standard", "extended"]

# 項目 -> 期待値（"y" か "n"）。全バリアントで明示されていること
ALWAYS = {
    "DPKG": "n",
    "DPKG_DEB": "n",
    "RPM": "n",
    "FEATURE_PATH_TRAVERSAL_PROTECTION": "y",
}

# wget を持つバリアントだけで明示されていること
WITH_WGET = {
    "FEATURE_WGET_HTTPS": "y",
    "FEATURE_WGET_OPENSSL": "n",
}


def explicit_values(text):
    """config に明示された項目 -> "y" / "n"。書かれていない項目は含まない。"""
    values = {}
    for line in text.splitlines():
        m = re.match(r"^CONFIG_([A-Z0-9_]+)=(.*)$", line)
        if m:
            values[m.group(1)] = "n" if m.group(2) == "n" else "y"
            continue
        m = re.match(r"^# CONFIG_([A-Z0-9_]+) is not set$", line)
        if m:
            values[m.group(1)] = "n"
    return values


@pytest.mark.parametrize("variant", VARIANTS)
def test_risky_defaults_are_explicit(variant):
    values = explicit_values((CONFIG_DIR / f"{variant}.config").read_text())
    expected = dict(ALWAYS)
    if values.get("WGET") == "y":
        expected.update(WITH_WGET)
    for name, want in expected.items():
        assert name in values, (
            f"{variant}.config に CONFIG_{name} が書かれていない"
            f"（書かないと BusyBox の既定値が入る）"
        )
        assert values[name] == want, (
            f"{variant}.config の CONFIG_{name} が {values[name]}（期待は {want}）"
        )


def test_explicit_values_parser():
    text = "CONFIG_A=y\nCONFIG_B=n\n# CONFIG_C is not set\nCONFIG_D=\"x\"\n"
    assert explicit_values(text) == {"A": "y", "B": "n", "C": "n", "D": "y"}
