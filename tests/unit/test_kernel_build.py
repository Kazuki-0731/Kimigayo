"""
Unit tests for kernel build system
"""

import pytest
from pathlib import Path

from src.kernel.build import (
    KernelConfig,
    KernelVersion,
    KernelBuilder,
    build_kernel,
)


def test_kernel_config_default_values():
    """Test KernelConfig default values"""
    config = KernelConfig(architecture="x86_64")

    assert config.architecture == "x86_64"
    assert config.version == KernelVersion.KERNEL_6_6
    assert config.enable_hardening is True
    assert config.reproducible is True
    assert config.modules == []
    assert config.config_file is not None
    assert "kimigayo_x86_64_defconfig" in str(config.config_file)


def test_kernel_config_arm64():
    """Test ARM64 kernel configuration"""
    config = KernelConfig(architecture="arm64")

    assert config.architecture == "arm64"
    assert "kimigayo_arm64_defconfig" in str(config.config_file)


def test_kernel_config_custom_modules():
    """Test kernel config with custom modules"""
    modules = ["module_a", "module_b", "module_c"]
    config = KernelConfig(
        architecture="x86_64",
        modules=modules
    )

    assert config.modules == modules


def test_kernel_builder_initialization(tmp_path):
    """Test KernelBuilder initialization"""
    config = KernelConfig(architecture="x86_64")
    builder = KernelBuilder(config, tmp_path)

    assert builder.config == config
    assert builder.output_dir == tmp_path
    assert builder.output_dir.exists()


def test_kernel_builder_setup_reproducible_environment(tmp_path):
    """Test reproducible environment setup"""
    import os

    config = KernelConfig(
        architecture="x86_64",
        reproducible=True
    )
    builder = KernelBuilder(config, tmp_path)
    builder.setup_reproducible_environment()

    assert os.environ.get("SOURCE_DATE_EPOCH") == "0"
    assert os.environ.get("LC_ALL") == "C"
    assert os.environ.get("TZ") == "UTC"
    assert os.environ.get("KBUILD_BUILD_USER") == "kimigayo"
    assert os.environ.get("KBUILD_BUILD_HOST") == "kimigayo"


def test_kernel_builder_hardening_flags(tmp_path):
    """Test kernel hardening flags"""
    config = KernelConfig(
        architecture="x86_64",
        enable_hardening=True
    )
    builder = KernelBuilder(config, tmp_path)
    flags = builder.get_hardening_flags()

    assert "KCFLAGS" in flags
    assert "-fPIE" in flags["KCFLAGS"]
    assert "-fstack-protector-strong" in flags["KCFLAGS"]
    assert "-D_FORTIFY_SOURCE=2" in flags["KCFLAGS"]


def test_kernel_builder_no_hardening_flags(tmp_path):
    """Test kernel without hardening flags"""
    config = KernelConfig(
        architecture="x86_64",
        enable_hardening=False
    )
    builder = KernelBuilder(config, tmp_path)
    flags = builder.get_hardening_flags()

    assert flags == {}


def test_kernel_config_file_exists_x86_64(tmp_path):
    """Test that x86_64 kernel config file exists"""
    config = KernelConfig(architecture="x86_64")
    assert config.config_file.exists(), (
        f"x86_64 kernel config not found: {config.config_file}"
    )


def test_kernel_config_file_exists_arm64(tmp_path):
    """Test that ARM64 kernel config file exists"""
    config = KernelConfig(architecture="arm64")
    assert config.config_file.exists(), (
        f"ARM64 kernel config not found: {config.config_file}"
    )


def test_kernel_build_basic(tmp_path):
    """Test basic kernel build"""
    config = KernelConfig(
        architecture="x86_64",
        reproducible=True,
        enable_hardening=True,
    )

    result = build_kernel(config, tmp_path)

    assert result.kernel_image.exists()
    assert result.config_file.exists()
    assert result.checksum
    assert len(result.checksum) == 64  # SHA-256
    assert result.size_bytes > 0


def test_kernel_build_reproducibility(tmp_path):
    """Test that kernel builds are reproducible"""
    config = KernelConfig(
        architecture="x86_64",
        reproducible=True,
    )

    result1 = build_kernel(config, tmp_path / "build1")
    result2 = build_kernel(config, tmp_path / "build2")

    assert result1.checksum == result2.checksum
    assert result1.size_bytes == result2.size_bytes


def test_kernel_verify_security_config(tmp_path):
    """Test security configuration verification"""
    config = KernelConfig(
        architecture="x86_64",
        enable_hardening=True,
    )

    builder = KernelBuilder(config, tmp_path)
    builder.configure_kernel()

    # Should not raise exception
    assert builder.verify_security_config()


def test_kernel_get_enabled_security_features(tmp_path):
    """Test getting enabled security features"""
    config = KernelConfig(
        architecture="x86_64",
        enable_hardening=True,
    )

    builder = KernelBuilder(config, tmp_path)
    builder.configure_kernel()

    features = builder.get_enabled_security_features()

    # Should have some security features enabled
    assert len(features) > 0
    assert "CONFIG_SECURITY" in features


def test_kernel_enable_module(tmp_path):
    """Test enabling a kernel module"""
    config = KernelConfig(architecture="x86_64")

    builder = KernelBuilder(config, tmp_path)
    builder.configure_kernel()

    # Enable a module
    assert builder.enable_kernel_module("test_module")
    assert "test_module" in config.modules


def test_kernel_build_result_verify_checksum(tmp_path):
    """Test KernelBuildResult checksum verification"""
    config = KernelConfig(architecture="x86_64")
    result = build_kernel(config, tmp_path)

    # Should verify with same checksum
    assert result.verify_checksum(result.checksum)

    # Should fail with different checksum
    assert not result.verify_checksum("invalid_checksum")
