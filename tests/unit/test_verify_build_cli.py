"""
Unit tests for src/build/cli/verify_build.py

reproducible サブコマンドは BuildConfig に文字列を渡しており、
'str' object has no attribute 'value' で必ず失敗していた
（例外を握って終了コード 1 を返すだけだったので、どこからも気づけなかった）。
CLI の入口から呼んで、終了コードが 0 になることを確かめる。
"""

import pytest

from src.build.cli import verify_build


class TestReproducibleCommand:
    """reproducible サブコマンド"""

    def test_reproducible_default_succeeds(self, tmp_path, capsys):
        rc = verify_build.main(["reproducible", str(tmp_path), "--builds", "2"])
        out = capsys.readouterr()

        assert "has no attribute 'value'" not in out.err
        assert rc == 0, out.err
        assert "Unique checksums: 1" in out.out

    @pytest.mark.parametrize("arch", ["x86_64", "arm64"])
    @pytest.mark.parametrize("image_type", ["minimal", "standard", "extended"])
    def test_reproducible_each_arch_and_variant(self, tmp_path, capsys, arch, image_type):
        rc = verify_build.main([
            "reproducible", str(tmp_path), "--builds", "2",
            "--arch", arch, "--image-type", image_type,
        ])
        out = capsys.readouterr()

        assert rc == 0, out.err

    def test_reproducible_rejects_unknown_arch(self, tmp_path):
        with pytest.raises(SystemExit):
            verify_build.main(["reproducible", str(tmp_path), "--arch", "riscv64"])
