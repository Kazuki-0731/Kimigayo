"""
Property-based tests for musl libc integration

Tests validate musl libc usage and linking options support.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from pathlib import Path

from src.libc.musl import (
    MuslConfig,
    LinkMode,
    OptimizationLevel,
    MuslBuilder,
    build_musl,
)


# Strategy for link modes
link_modes = st.sampled_from(LinkMode)


# Strategy for optimization levels
optimization_levels = st.sampled_from(OptimizationLevel)


# Strategy for architectures
architectures = st.sampled_from(["x86_64", "arm64", "aarch64"])


# Strategy for musl configurations
@st.composite
def musl_configs(draw):
    """Strategy for generating musl configurations"""
    arch = draw(architectures)
    link_mode = draw(link_modes)
    optimization = draw(optimization_levels)
    enable_security = draw(st.booleans())
    enable_wrapper = draw(st.booleans())
    enable_debug = draw(st.booleans())

    return MuslConfig(
        architecture=arch,
        link_mode=link_mode,
        optimization=optimization,
        enable_security_hardening=enable_security,
        enable_wrapper_functions=enable_wrapper,
        enable_debug_symbols=enable_debug,
    )


# **Feature: kimigayo-os-core, Property 28: musl libc使用**
# **検証対象: 要件 8.2**
@pytest.mark.property
@given(config=musl_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_musl_libc_usage(config, tmp_path):
    """
    任意のビルド構成に対して、システムはmusl libcを使用しなければならない
    """
    builder = MuslBuilder(config, tmp_path)
    result = builder.build()

    # Verify musl was built
    assert result.lib_dir.exists(), "Library directory should exist"
    assert result.include_dir.exists(), "Include directory should exist"

    # Verify appropriate libraries were built based on link mode
    if config.supports_static_linking():
        assert result.verify_static_lib(), "Static library should be built"
        assert result.static_lib.exists(), "Static library file should exist"

    if config.supports_dynamic_linking():
        assert result.verify_dynamic_lib(), "Dynamic library should be built"
        assert result.dynamic_lib.exists(), "Dynamic library file should exist"

    # Verify compiler flags use musl
    compiler_flags = builder.get_compiler_flags()
    assert "musl" in compiler_flags["CC"], "Compiler should be musl-gcc"


# **Feature: kimigayo-os-core, Property 29: リンクオプションサポート**
# **検証対象: 要件 8.3**
@pytest.mark.property
@given(
    link_mode=link_modes,
    arch=architectures,
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_link_option_support(link_mode, arch, tmp_path):
    """
    任意のリンクオプション（静的・動的）に対して、
    Build_Systemは対応するライブラリを生成しなければならない
    """
    config = MuslConfig(
        architecture=arch,
        link_mode=link_mode,
    )

    result = build_musl(config, tmp_path)

    # Verify static linking support
    if link_mode in [LinkMode.STATIC, LinkMode.BOTH]:
        assert config.supports_static_linking()
        assert result.static_lib is not None
        assert result.static_lib.exists()
        assert result.static_lib.name == "libc.a"

    # Verify dynamic linking support
    if link_mode in [LinkMode.DYNAMIC, LinkMode.BOTH]:
        assert config.supports_dynamic_linking()
        assert result.dynamic_lib is not None
        assert result.dynamic_lib.exists()
        assert result.dynamic_lib.name == "libc.so"

    # Verify only requested libraries were built
    if link_mode == LinkMode.STATIC:
        assert result.static_lib is not None
        assert result.dynamic_lib is None

    if link_mode == LinkMode.DYNAMIC:
        assert result.dynamic_lib is not None
        assert result.static_lib is None


@pytest.mark.property
@given(config=musl_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_security_hardening_flags(config, tmp_path):
    """
    Verify that security hardening flags are properly applied
    """
    if config.enable_security_hardening:
        builder = MuslBuilder(config, tmp_path)

        # Verify security features
        assert builder.verify_security_features()

        cflags = config.get_cflags()
        ldflags = config.get_ldflags()

        # Check CFLAGS
        assert "-fPIE" in cflags
        assert "-fstack-protector-strong" in cflags
        assert "-D_FORTIFY_SOURCE=2" in cflags

        # Check LDFLAGS
        assert "-Wl,-z,relro" in ldflags
        assert "-Wl,-z,now" in ldflags
        assert "-Wl,-z,noexecstack" in ldflags


@pytest.mark.property
@given(
    opt1=optimization_levels,
    opt2=optimization_levels,
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_optimization_size_effect(opt1, opt2, tmp_path):
    """
    Verify that size optimization produces smaller libraries
    """
    config1 = MuslConfig(optimization=opt1, link_mode=LinkMode.STATIC)
    config2 = MuslConfig(optimization=opt2, link_mode=LinkMode.STATIC)

    result1 = build_musl(config1, tmp_path / "opt1")
    result2 = build_musl(config2, tmp_path / "opt2")

    size1 = result1.static_lib.stat().st_size
    size2 = result2.static_lib.stat().st_size

    # SIZE should produce smallest, SPEED should produce largest
    opt_order = [OptimizationLevel.SIZE, OptimizationLevel.BALANCED, OptimizationLevel.SPEED]

    if opt_order.index(opt1) < opt_order.index(opt2):
        assert size1 <= size2, f"{opt1.value} should not be larger than {opt2.value}"
    elif opt_order.index(opt1) > opt_order.index(opt2):
        assert size1 >= size2, f"{opt1.value} should not be smaller than {opt2.value}"


@pytest.mark.property
@given(config=musl_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_architecture_specific_flags(config, tmp_path):
    """
    Verify that architecture-specific flags are applied
    """
    cflags = config.get_cflags()

    if config.architecture == "x86_64":
        assert "-m64" in cflags or "-march=x86-64" in cflags
    elif config.architecture in ["arm64", "aarch64"]:
        assert "-march=armv8-a" in cflags


@pytest.mark.property
@given(config=musl_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_header_files_created(config, tmp_path):
    """
    Verify that header files are created
    """
    result = build_musl(config, tmp_path)

    # Check essential headers exist
    essential_headers = ["stdio.h", "stdlib.h", "string.h", "unistd.h", "stdint.h"]

    for header in essential_headers:
        header_path = result.include_dir / header
        assert header_path.exists(), f"Header {header} should exist"


@pytest.mark.property
@given(config=musl_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_build_result_checksum(config, tmp_path):
    """
    Verify that build results include valid checksums
    """
    result = build_musl(config, tmp_path)

    # Checksum should be non-empty
    assert result.checksum, "Checksum should not be empty"

    # Checksum should be 64 characters (SHA-256)
    assert len(result.checksum) == 64, f"Invalid checksum length: {len(result.checksum)}"

    # Checksum should be hexadecimal
    try:
        int(result.checksum, 16)
    except ValueError:
        pytest.fail(f"Checksum is not valid hexadecimal: {result.checksum}")


@pytest.mark.property
@given(config=musl_configs())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_reproducible_builds(config, tmp_path):
    """
    Verify that builds are reproducible
    """
    result1 = build_musl(config, tmp_path / "build1")
    result2 = build_musl(config, tmp_path / "build2")

    # Sizes should be identical
    assert result1.size_bytes == result2.size_bytes, (
        f"Build sizes differ: {result1.size_bytes} vs {result2.size_bytes}"
    )

    # Checksums should be identical
    assert result1.checksum == result2.checksum, (
        f"Checksums differ:\n"
        f"  Build 1: {result1.checksum}\n"
        f"  Build 2: {result2.checksum}"
    )


@pytest.mark.property
@given(
    link_mode=link_modes,
    arch=architectures,
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_library_info_accuracy(link_mode, arch, tmp_path):
    """
    Verify that library info is accurate
    """
    config = MuslConfig(architecture=arch, link_mode=link_mode)
    builder = MuslBuilder(config, tmp_path)
    result = builder.build()

    info = builder.get_library_info(result)

    # Check basic info
    assert info["architecture"] == arch
    assert info["link_mode"] == link_mode.value
    assert info["total_size"] == result.size_bytes

    # Check library-specific info
    if result.static_lib:
        assert "static_lib_size" in info
        assert info["static_lib_size"] == result.static_lib.stat().st_size

    if result.dynamic_lib:
        assert "dynamic_lib_size" in info
        assert info["dynamic_lib_size"] == result.dynamic_lib.stat().st_size


@pytest.mark.property
@given(config=musl_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_configure_flags_generation(config, tmp_path):
    """
    Verify that configure flags are properly generated
    """
    configure_flags = config.get_configure_flags()

    # Check link mode flags
    if config.link_mode == LinkMode.STATIC:
        assert "--disable-shared" in configure_flags
    elif config.link_mode == LinkMode.DYNAMIC:
        assert "--enable-shared" in configure_flags

    # Check debug flags
    if config.enable_debug_symbols:
        assert "--enable-debug" in configure_flags
    else:
        assert "--disable-debug" in configure_flags


@pytest.mark.property
@given(config=musl_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_compiler_flags_consistency(config, tmp_path):
    """
    Verify that compiler flags are consistent
    """
    builder = MuslBuilder(config, tmp_path)
    flags1 = builder.get_compiler_flags()
    flags2 = builder.get_compiler_flags()

    # Flags should be the same across multiple calls
    assert flags1 == flags2


@pytest.mark.property
@given(link_mode=link_modes)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_both_link_modes(link_mode, tmp_path):
    """
    Verify that BOTH link mode builds both static and dynamic libraries
    """
    if link_mode == LinkMode.BOTH:
        config = MuslConfig(link_mode=link_mode)
        result = build_musl(config, tmp_path)

        # Both libraries should exist
        assert result.static_lib is not None
        assert result.static_lib.exists()
        assert result.dynamic_lib is not None
        assert result.dynamic_lib.exists()

        # Total size should be sum of both
        expected_size = (
            result.static_lib.stat().st_size +
            result.dynamic_lib.stat().st_size
        )
        assert result.get_total_size() == expected_size
