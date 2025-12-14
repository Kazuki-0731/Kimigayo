"""
Property-based tests for cross-compilation environment

Tests validate multi-architecture support and cross-architecture consistency.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from pathlib import Path

from src.toolchain.cross_compile import (
    Architecture,
    LibcType,
    ToolchainConfig,
    CrossCompileConfig,
    CrossCompiler,
    setup_toolchain,
)


# Strategy for architectures
architectures = st.sampled_from([Architecture.X86_64, Architecture.ARM64])


# Strategy for libc types
libc_types = st.sampled_from([LibcType.MUSL, LibcType.GLIBC])


# Strategy for toolchain configurations
@st.composite
def toolchain_configs(draw):
    """Strategy for generating toolchain configurations"""
    arch = draw(architectures)
    libc = draw(libc_types)

    return ToolchainConfig(
        architecture=arch,
        libc=libc
    )


# Strategy for cross-compile configurations
@st.composite
def cross_compile_configs(draw):
    """Strategy for generating cross-compile configurations"""
    target_arch = draw(architectures)
    host_arch = draw(architectures)
    enable_static = draw(st.booleans())
    enable_shared = draw(st.booleans())

    # At least one of static or shared should be enabled
    assume(enable_static or enable_shared)

    return CrossCompileConfig(
        target_arch=target_arch,
        host_arch=host_arch,
        enable_static=enable_static,
        enable_shared=enable_shared,
    )


# **Feature: kimigayo-os-core, Property 16: マルチアーキテクチャサポート**
# **検証対象: 要件 5.1**
@pytest.mark.property
@given(arch=architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_multi_architecture_support(arch, tmp_path):
    """
    任意のTarget_Architectureに対して、Build_Systemは
    そのアーキテクチャ用のバイナリを生成できなければならない
    """
    compiler = setup_toolchain(arch, tmp_path)

    # Verify toolchain configuration
    assert compiler.config.target_arch == arch
    assert compiler.config.toolchain.architecture == arch

    # Verify environment is set up correctly
    env = compiler.config.get_environment()

    assert "CC" in env
    assert "ARCH" in env
    assert "CROSS_COMPILE" in env

    # Verify correct architecture is set
    if arch == Architecture.ARM64:
        assert env["ARCH"] == "arm64"
        assert "aarch64" in env["CROSS_COMPILE"]
    else:
        assert env["ARCH"] == "x86_64"
        assert "x86_64" in env["CROSS_COMPILE"]


# **Feature: kimigayo-os-core, Property 17: クロスアーキテクチャ機能一貫性**
# **検証対象: 要件 5.2**
@pytest.mark.property
@given(
    arch1=architectures,
    arch2=architectures,
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_cross_architecture_feature_consistency(arch1, arch2, tmp_path):
    """
    任意の2つのTarget_Architectureに対して、Build_Systemは
    同じFeature_Setを提供しなければならない
    """
    compiler1 = setup_toolchain(arch1, tmp_path / "arch1")
    compiler2 = setup_toolchain(arch2, tmp_path / "arch2")

    # Get toolchain info for both architectures
    info1 = compiler1.get_toolchain_info()
    info2 = compiler2.get_toolchain_info()

    # Both should use the same libc
    assert info1["libc"] == info2["libc"]

    # Both should have the same environment variable structure
    env1 = compiler1.config.get_environment()
    env2 = compiler2.config.get_environment()

    # Check that both have the same set of tools defined
    tools = ["CC", "CXX", "AR", "LD", "RANLIB", "STRIP"]
    for tool in tools:
        assert tool in env1, f"{tool} not in arch1 environment"
        assert tool in env2, f"{tool} not in arch2 environment"

    # Both should have security flags
    assert "CFLAGS" in env1 and "CFLAGS" in env2
    assert "LDFLAGS" in env1 and "LDFLAGS" in env2

    # Security flags should be consistent
    security_flags = ["-fPIE", "-fstack-protector-strong"]
    for flag in security_flags:
        assert flag in env1["CFLAGS"]
        assert flag in env2["CFLAGS"]


@pytest.mark.property
@given(config=toolchain_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_toolchain_prefix_generation(config, tmp_path):
    """
    Verify that toolchain prefixes are correctly generated
    """
    prefix = config.toolchain_prefix

    # Prefix should not be empty
    assert prefix, "Toolchain prefix is empty"

    # Prefix should contain architecture
    if config.architecture == Architecture.X86_64:
        assert "x86_64" in prefix
    elif config.architecture in [Architecture.ARM64, Architecture.AARCH64]:
        assert "aarch64" in prefix

    # Prefix should contain libc type
    if config.libc == LibcType.MUSL:
        assert "musl" in prefix
    else:
        assert "gnu" in prefix


@pytest.mark.property
@given(config=cross_compile_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_security_flags_applied(config, tmp_path):
    """
    Verify that security flags are automatically applied
    """
    compiler = CrossCompiler(config, tmp_path)
    env = compiler.config.get_environment()

    # Check that security CFLAGS are present
    cflags = env.get("CFLAGS", "")
    assert "-fPIE" in cflags
    assert "-fstack-protector-strong" in cflags
    assert "-D_FORTIFY_SOURCE=2" in cflags

    # Check that security LDFLAGS are present
    ldflags = env.get("LDFLAGS", "")
    assert "-Wl,-z,relro" in ldflags
    assert "-Wl,-z,now" in ldflags
    assert "-Wl,-z,noexecstack" in ldflags


@pytest.mark.property
@given(arch=architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_sysroot_setup(arch, tmp_path):
    """
    Verify that sysroot can be set up correctly
    """
    compiler = setup_toolchain(arch, tmp_path)
    sysroot_path = tmp_path / "sysroot"

    # Setup sysroot
    success = compiler.setup_sysroot(sysroot_path)
    assert success, "Failed to setup sysroot"

    # Verify sysroot directories exist
    assert sysroot_path.exists()
    assert (sysroot_path / "usr/include").exists()
    assert (sysroot_path / "usr/lib").exists()
    assert (sysroot_path / "lib").exists()

    # Verify sysroot is set in toolchain
    assert compiler.config.toolchain.sysroot == sysroot_path


@pytest.mark.property
@given(config=cross_compile_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_environment_variables_consistency(config, tmp_path):
    """
    Verify that environment variables are consistently set
    """
    compiler = CrossCompiler(config, tmp_path)
    env1 = compiler.config.get_environment()
    env2 = compiler.config.get_environment()

    # Environment should be the same across multiple calls
    assert env1["CC"] == env2["CC"]
    assert env1["CFLAGS"] == env2["CFLAGS"]
    assert env1["LDFLAGS"] == env2["LDFLAGS"]
    assert env1["ARCH"] == env2["ARCH"]


@pytest.mark.property
@given(
    target_arch=architectures,
    host_arch=architectures,
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_cross_vs_native_compilation(target_arch, host_arch, tmp_path):
    """
    Verify that cross and native compilation are properly distinguished
    """
    config = CrossCompileConfig(
        target_arch=target_arch,
        host_arch=host_arch,
    )

    compiler = CrossCompiler(config, tmp_path)
    env = compiler.config.get_environment()

    # CROSS_COMPILE should always be set (even for native builds)
    assert "CROSS_COMPILE" in env

    # For cross-compilation, CROSS_COMPILE should contain the target arch
    if target_arch != host_arch:
        cross_compile = env["CROSS_COMPILE"]
        if target_arch == Architecture.ARM64:
            assert "aarch64" in cross_compile
        else:
            assert "x86_64" in cross_compile


@pytest.mark.property
@given(arch=architectures)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_toolchain_info_retrieval(arch, tmp_path):
    """
    Verify that toolchain information can be retrieved
    """
    compiler = setup_toolchain(arch, tmp_path)
    info = compiler.get_toolchain_info()

    # Info should contain required fields
    assert "compiler" in info
    assert "target_arch" in info
    assert "libc" in info
    assert "version" in info

    # Target arch should match
    assert info["target_arch"] == arch.value

    # Libc should be musl by default
    assert info["libc"] == "musl"


@pytest.mark.property
@given(config=cross_compile_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_static_shared_linking_options(config, tmp_path):
    """
    Verify that static and shared linking options are properly configured
    """
    compiler = CrossCompiler(config, tmp_path)

    # At least one linking option should be enabled
    assert config.enable_static or config.enable_shared

    # Configuration should be preserved
    assert compiler.config.enable_static == config.enable_static
    assert compiler.config.enable_shared == config.enable_shared
