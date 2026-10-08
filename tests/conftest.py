"""
Pytest configuration for Kimigayo OS tests
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
# バージョンは git のリリースタグが真実の源（0.1.0 のハードコードをやめた）
def _project_version() -> str:
    try:
        import subprocess
        return subprocess.run(
            ["bash", str(project_root / "scripts" / "get-version.sh")],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip() or "0.0.0-unknown"
    except Exception:
        return "0.0.0-unknown"


KIMIGAYO_VERSION = _project_version()
BUILD_DIR = project_root / "build"
OUTPUT_DIR = project_root / "output"

# Hypothesis configuration
from hypothesis import settings, Verbosity

# deadline=None にしている理由:
# ここのプロパティテストは tmp_path への実ファイル書き込みや
# サブプロセス起動を含み、1例あたり 300-400ms かかることがある。
# hypothesis の既定デッドライン 200ms は「純粋な関数の性能劣化を拾う」ための
# もので、I/O を伴うこれらのテストには合わない。
# 実際に arm64 ホストでの linux/amd64 エミュレーションビルドでは
# DeadlineExceeded で3件落ちた（ロジックの失敗ではなく実行速度の問題）。
# CI がテストをゲートにしている以上、速度依存の不安定さは持ち込まない。
settings.register_profile(
    "kimigayo", max_examples=100, verbosity=Verbosity.verbose, deadline=None
)
settings.register_profile(
    "ci", max_examples=200, verbosity=Verbosity.normal, deadline=None
)
settings.register_profile(
    "dev", max_examples=50, verbosity=Verbosity.verbose, deadline=None
)

# Load profile from environment or use default
profile = os.getenv("HYPOTHESIS_PROFILE", "kimigayo")
settings.load_profile(profile)


@pytest.fixture(scope="session")
def project_root_path():
    """Return the project root directory path"""
    return project_root


@pytest.fixture(scope="session")
def build_dir():
    """Return the build directory path"""
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    return BUILD_DIR


@pytest.fixture(scope="session")
def output_dir():
    """Return the output directory path"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


@pytest.fixture
def temp_build_dir(tmp_path):
    """Return a temporary build directory for tests"""
    return tmp_path / "build"


@pytest.fixture
def kimigayo_version():
    """Return the Kimigayo OS version"""
    return KIMIGAYO_VERSION


# Architecture fixtures
@pytest.fixture(params=["x86_64", "arm64"])
def architecture(request):
    """Parametrize tests for all supported architectures"""
    return request.param


@pytest.fixture
def x86_64_arch():
    """x86_64 architecture"""
    return "x86_64"


@pytest.fixture
def arm64_arch():
    """ARM64 architecture"""
    return "arm64"


# Security fixtures
@pytest.fixture
def security_flags():
    """Return security hardening flags"""
    return {
        "cflags": [
            "-fPIE",
            "-fstack-protector-strong",
            "-D_FORTIFY_SOURCE=2",
        ],
        "ldflags": [
            "-Wl,-z,relro",
            "-Wl,-z,now",
        ],
    }


# Size constraints
@pytest.fixture
def size_constraints():
    """Return size constraints for Kimigayo OS"""
    return {
        "minimal": 5 * 1024 * 1024,      # 5 MB
        "standard": 15 * 1024 * 1024,    # 15 MB
        "extended": 50 * 1024 * 1024,    # 50 MB
        "ram_minimum": 128 * 1024 * 1024,  # 128 MB
    }


# Property test markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "property: mark test as a property-based test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
