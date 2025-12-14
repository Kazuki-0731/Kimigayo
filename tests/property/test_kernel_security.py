"""
Property-based tests for kernel security configuration

Tests validate that kernel builds have proper security hardening enabled.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from pathlib import Path

from src.kernel.build import (
    KernelConfig,
    KernelVersion,
    build_kernel,
    KernelBuilder,
)


# Strategy for kernel architectures
kernel_architectures = st.sampled_from(["x86_64", "arm64"])


# Strategy for kernel configurations
@st.composite
def kernel_configs(draw):
    """Strategy for generating kernel configurations"""
    arch = draw(kernel_architectures)
    version = draw(st.sampled_from(KernelVersion))
    enable_hardening = draw(st.booleans())
    reproducible = draw(st.booleans())

    num_modules = draw(st.integers(min_value=0, max_value=3))
    modules = [f"module_{i}" for i in range(num_modules)]

    return KernelConfig(
        architecture=arch,
        version=version,
        modules=modules,
        enable_hardening=enable_hardening,
        reproducible=reproducible,
    )


# **Feature: kimigayo-os-core, Property 31: カーネルセキュリティ設定**
# **検証対象: 要件 6.3**
@pytest.mark.property
@given(arch=kernel_architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_kernel_security_hardening_enabled(arch, tmp_path):
    """
    任意のアーキテクチャに対して、Kernel_Configは
    セキュリティ強化オプション（ASLR、DEP、PIE）を有効化しなければならない
    """
    config = KernelConfig(
        architecture=arch,
        enable_hardening=True,
        reproducible=True,
    )

    result = build_kernel(config, tmp_path)

    # Verify security configuration was checked
    builder = KernelBuilder(config, tmp_path)
    assert builder.verify_security_config(), (
        f"Security configuration verification failed for {arch}"
    )

    # Verify security features are enabled
    security_features = builder.get_enabled_security_features()

    required_features = [
        "CONFIG_SECURITY",
        "CONFIG_HARDENED_USERCOPY",
        "CONFIG_FORTIFY_SOURCE",
        "CONFIG_STACKPROTECTOR_STRONG",
    ]

    for feature in required_features:
        assert feature in security_features, (
            f"Required security feature {feature} not enabled for {arch}"
        )


@pytest.mark.property
@given(config=kernel_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_kernel_config_file_exists(config, tmp_path):
    """
    Verify that kernel config files exist for all architectures
    """
    # The config file should exist
    assert config.config_file.exists(), (
        f"Kernel config file not found: {config.config_file}"
    )

    # Config file should be non-empty
    assert config.config_file.stat().st_size > 0, (
        f"Kernel config file is empty: {config.config_file}"
    )


@pytest.mark.property
@given(arch=kernel_architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_reproducible_kernel_build(arch, tmp_path):
    """
    Verify that kernel builds are reproducible
    """
    config = KernelConfig(
        architecture=arch,
        reproducible=True,
        enable_hardening=True,
    )

    # Build twice
    result1 = build_kernel(config, tmp_path / "build1")
    result2 = build_kernel(config, tmp_path / "build2")

    # Checksums should be identical for reproducible builds
    assert result1.checksum == result2.checksum, (
        f"Kernel builds are not reproducible for {arch}:\n"
        f"  Build 1: {result1.checksum}\n"
        f"  Build 2: {result2.checksum}"
    )

    # Sizes should be identical
    assert result1.size_bytes == result2.size_bytes, (
        f"Kernel build sizes differ for {arch}:\n"
        f"  Build 1: {result1.size_bytes}\n"
        f"  Build 2: {result2.size_bytes}"
    )


@pytest.mark.property
@given(arch=kernel_architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_kernel_module_sig_enforcement(arch, tmp_path):
    """
    Verify that module signature enforcement is enabled
    """
    config = KernelConfig(
        architecture=arch,
        enable_hardening=True,
    )

    builder = KernelBuilder(config, tmp_path)
    builder.configure_kernel()

    # Check that module signature enforcement is in config
    config_content = (builder.build_dir / ".config").read_text()

    assert "CONFIG_MODULE_SIG=y" in config_content, (
        "Module signing not enabled"
    )
    assert "CONFIG_MODULE_SIG_FORCE=y" in config_content, (
        "Module signature enforcement not enabled"
    )
    assert "CONFIG_MODULE_SIG_ALL=y" in config_content, (
        "All modules signing not enabled"
    )


@pytest.mark.property
@given(
    arch=kernel_architectures,
    reproducible=st.booleans(),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_kernel_build_environment_variables(arch, reproducible, tmp_path, monkeypatch):
    """
    Verify that reproducible builds set proper environment variables
    """
    config = KernelConfig(
        architecture=arch,
        reproducible=reproducible,
    )

    builder = KernelBuilder(config, tmp_path)
    builder.setup_reproducible_environment()

    if reproducible:
        # Check that reproducible build environment variables are set
        assert "SOURCE_DATE_EPOCH" in os.environ
        assert os.environ["SOURCE_DATE_EPOCH"] == "0"
        assert os.environ["LC_ALL"] == "C"
        assert os.environ["TZ"] == "UTC"
        assert os.environ["KBUILD_BUILD_USER"] == "kimigayo"
        assert os.environ["KBUILD_BUILD_HOST"] == "kimigayo"


@pytest.mark.property
@given(arch=kernel_architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_kernel_stack_protection_enabled(arch, tmp_path):
    """
    Verify that stack protection is enabled in kernel config
    """
    config = KernelConfig(
        architecture=arch,
        enable_hardening=True,
    )

    builder = KernelBuilder(config, tmp_path)
    builder.configure_kernel()

    config_content = (builder.build_dir / ".config").read_text()

    # Check stack protection options
    assert "CONFIG_STACKPROTECTOR=y" in config_content
    assert "CONFIG_STACKPROTECTOR_STRONG=y" in config_content
    assert "CONFIG_VMAP_STACK=y" in config_content


@pytest.mark.property
@given(arch=kernel_architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_kernel_memory_protection_enabled(arch, tmp_path):
    """
    Verify that memory protection features are enabled
    """
    config = KernelConfig(
        architecture=arch,
        enable_hardening=True,
    )

    builder = KernelBuilder(config, tmp_path)
    builder.configure_kernel()

    config_content = (builder.build_dir / ".config").read_text()

    # Check memory protection options
    assert "CONFIG_SLAB_FREELIST_RANDOM=y" in config_content
    assert "CONFIG_SLAB_FREELIST_HARDENED=y" in config_content
    assert "CONFIG_SHUFFLE_PAGE_ALLOCATOR=y" in config_content


@pytest.mark.property
@given(arch=kernel_architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_kernel_aslr_enabled(arch, tmp_path):
    """
    Verify that ASLR (Address Space Layout Randomization) is enabled
    """
    config = KernelConfig(
        architecture=arch,
        enable_hardening=True,
    )

    builder = KernelBuilder(config, tmp_path)
    builder.configure_kernel()

    config_content = (builder.build_dir / ".config").read_text()

    # Check ASLR options
    assert "CONFIG_RANDOMIZE_BASE=y" in config_content

    # x86_64 specific ASLR options
    if arch == "x86_64":
        assert "CONFIG_RANDOMIZE_MEMORY=y" in config_content


@pytest.mark.property
@given(config=kernel_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_kernel_build_result_checksum(config, tmp_path):
    """
    Verify that kernel build results include valid checksums
    """
    result = build_kernel(config, tmp_path)

    # Checksum should be non-empty
    assert result.checksum, "Build result checksum is empty"

    # Checksum should be 64 characters (SHA-256)
    assert len(result.checksum) == 64, (
        f"Invalid checksum length: {len(result.checksum)}"
    )

    # Checksum should be hexadecimal
    try:
        int(result.checksum, 16)
    except ValueError:
        pytest.fail(f"Checksum is not valid hexadecimal: {result.checksum}")


@pytest.mark.property
@given(arch=kernel_architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_kernel_strict_rwx_enabled(arch, tmp_path):
    """
    Verify that strict RWX memory protection is enabled
    """
    config = KernelConfig(
        architecture=arch,
        enable_hardening=True,
    )

    builder = KernelBuilder(config, tmp_path)
    builder.configure_kernel()

    config_content = (builder.build_dir / ".config").read_text()

    # Check strict RWX options
    assert "CONFIG_STRICT_KERNEL_RWX=y" in config_content
    assert "CONFIG_STRICT_MODULE_RWX=y" in config_content


import os
