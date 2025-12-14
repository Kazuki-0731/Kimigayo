"""
Unit tests for musl libc integration
"""

import pytest
from pathlib import Path

from src.libc.musl import (
    MuslConfig,
    LinkMode,
    OptimizationLevel,
    MuslBuilder,
    MuslBuildResult,
    build_musl,
)


def test_link_mode_enum():
    """Test LinkMode enum values"""
    assert LinkMode.STATIC.value == "static"
    assert LinkMode.DYNAMIC.value == "dynamic"
    assert LinkMode.BOTH.value == "both"


def test_optimization_level_enum():
    """Test OptimizationLevel enum values"""
    assert OptimizationLevel.SIZE.value == "size"
    assert OptimizationLevel.SPEED.value == "speed"
    assert OptimizationLevel.BALANCED.value == "balanced"


def test_musl_config_defaults():
    """Test MuslConfig default values"""
    config = MuslConfig()

    assert config.architecture == "x86_64"
    assert config.link_mode == LinkMode.STATIC
    assert config.optimization == OptimizationLevel.SIZE
    assert config.enable_security_hardening is True
    assert config.enable_wrapper_functions is True
    assert config.enable_debug_symbols is False


def test_musl_config_get_cflags_size_optimization():
    """Test CFLAGS for size optimization"""
    config = MuslConfig(optimization=OptimizationLevel.SIZE)
    cflags = config.get_cflags()

    assert "-Os" in cflags
    assert "-ffunction-sections" in cflags
    assert "-fdata-sections" in cflags


def test_musl_config_get_cflags_speed_optimization():
    """Test CFLAGS for speed optimization"""
    config = MuslConfig(optimization=OptimizationLevel.SPEED)
    cflags = config.get_cflags()

    assert "-O2" in cflags


def test_musl_config_get_cflags_security():
    """Test security CFLAGS"""
    config = MuslConfig(enable_security_hardening=True)
    cflags = config.get_cflags()

    assert "-fPIE" in cflags
    assert "-fstack-protector-strong" in cflags
    assert "-D_FORTIFY_SOURCE=2" in cflags


def test_musl_config_get_ldflags_security():
    """Test security LDFLAGS"""
    config = MuslConfig(enable_security_hardening=True)
    ldflags = config.get_ldflags()

    assert "-Wl,-z,relro" in ldflags
    assert "-Wl,-z,now" in ldflags
    assert "-Wl,-z,noexecstack" in ldflags


def test_musl_config_get_ldflags_size_optimization():
    """Test LDFLAGS for size optimization"""
    config = MuslConfig(optimization=OptimizationLevel.SIZE)
    ldflags = config.get_ldflags()

    assert "-Wl,--gc-sections" in ldflags
    assert "-Wl,--strip-all" in ldflags


def test_musl_config_supports_static_linking():
    """Test static linking support"""
    config_static = MuslConfig(link_mode=LinkMode.STATIC)
    config_dynamic = MuslConfig(link_mode=LinkMode.DYNAMIC)
    config_both = MuslConfig(link_mode=LinkMode.BOTH)

    assert config_static.supports_static_linking()
    assert not config_dynamic.supports_static_linking()
    assert config_both.supports_static_linking()


def test_musl_config_supports_dynamic_linking():
    """Test dynamic linking support"""
    config_static = MuslConfig(link_mode=LinkMode.STATIC)
    config_dynamic = MuslConfig(link_mode=LinkMode.DYNAMIC)
    config_both = MuslConfig(link_mode=LinkMode.BOTH)

    assert not config_static.supports_dynamic_linking()
    assert config_dynamic.supports_dynamic_linking()
    assert config_both.supports_dynamic_linking()


def test_musl_config_custom_flags():
    """Test custom compilation flags"""
    custom_cflags = ["-DCUSTOM_FLAG"]
    custom_ldflags = ["-lcustom"]

    config = MuslConfig(
        custom_cflags=custom_cflags,
        custom_ldflags=custom_ldflags,
    )

    cflags = config.get_cflags()
    ldflags = config.get_ldflags()

    assert "-DCUSTOM_FLAG" in cflags
    assert "-lcustom" in ldflags


def test_musl_config_architecture_x86_64():
    """Test x86_64 architecture flags"""
    config = MuslConfig(architecture="x86_64")
    cflags = config.get_cflags()

    assert "-m64" in cflags
    assert "-march=x86-64" in cflags


def test_musl_config_architecture_arm64():
    """Test ARM64 architecture flags"""
    config = MuslConfig(architecture="arm64")
    cflags = config.get_cflags()

    assert "-march=armv8-a" in cflags


def test_musl_builder_initialization(tmp_path):
    """Test MuslBuilder initialization"""
    config = MuslConfig()
    builder = MuslBuilder(config, tmp_path)

    assert builder.config == config
    assert builder.output_dir == tmp_path
    assert builder.lib_dir == tmp_path / "lib"
    assert builder.include_dir == tmp_path / "include"


def test_musl_builder_setup_directories(tmp_path):
    """Test directory setup"""
    config = MuslConfig()
    builder = MuslBuilder(config, tmp_path)
    builder.setup_directories()

    assert builder.lib_dir.exists()
    assert builder.include_dir.exists()


def test_musl_builder_build_static(tmp_path):
    """Test building static library"""
    config = MuslConfig(link_mode=LinkMode.STATIC)
    builder = MuslBuilder(config, tmp_path)
    result = builder.build()

    assert result.static_lib is not None
    assert result.static_lib.exists()
    assert result.static_lib.name == "libc.a"
    assert result.dynamic_lib is None


def test_musl_builder_build_dynamic(tmp_path):
    """Test building dynamic library"""
    config = MuslConfig(link_mode=LinkMode.DYNAMIC)
    builder = MuslBuilder(config, tmp_path)
    result = builder.build()

    assert result.dynamic_lib is not None
    assert result.dynamic_lib.exists()
    assert result.dynamic_lib.name == "libc.so"
    assert result.static_lib is None


def test_musl_builder_build_both(tmp_path):
    """Test building both static and dynamic libraries"""
    config = MuslConfig(link_mode=LinkMode.BOTH)
    builder = MuslBuilder(config, tmp_path)
    result = builder.build()

    assert result.static_lib is not None
    assert result.static_lib.exists()
    assert result.dynamic_lib is not None
    assert result.dynamic_lib.exists()


def test_musl_builder_get_compiler_flags(tmp_path):
    """Test getting compiler flags"""
    config = MuslConfig(architecture="x86_64")
    builder = MuslBuilder(config, tmp_path)
    flags = builder.get_compiler_flags()

    assert "CC" in flags
    assert "musl" in flags["CC"]
    assert "CFLAGS" in flags
    assert "LDFLAGS" in flags


def test_musl_builder_verify_security_features(tmp_path):
    """Test security features verification"""
    config = MuslConfig(enable_security_hardening=True)
    builder = MuslBuilder(config, tmp_path)

    assert builder.verify_security_features()


def test_musl_build_result_verify_static_lib(tmp_path):
    """Test static library verification"""
    config = MuslConfig(link_mode=LinkMode.STATIC)
    result = build_musl(config, tmp_path)

    assert result.verify_static_lib()


def test_musl_build_result_verify_dynamic_lib(tmp_path):
    """Test dynamic library verification"""
    config = MuslConfig(link_mode=LinkMode.DYNAMIC)
    result = build_musl(config, tmp_path)

    assert result.verify_dynamic_lib()


def test_musl_build_result_get_total_size(tmp_path):
    """Test total size calculation"""
    config = MuslConfig(link_mode=LinkMode.BOTH)
    result = build_musl(config, tmp_path)

    expected_size = (
        result.static_lib.stat().st_size +
        result.dynamic_lib.stat().st_size
    )

    assert result.get_total_size() == expected_size
    assert result.size_bytes == expected_size


def test_musl_builder_get_library_info(tmp_path):
    """Test getting library information"""
    config = MuslConfig(link_mode=LinkMode.BOTH, architecture="x86_64")
    builder = MuslBuilder(config, tmp_path)
    result = builder.build()

    info = builder.get_library_info(result)

    assert info["architecture"] == "x86_64"
    assert info["link_mode"] == "both"
    assert "total_size" in info
    assert "static_lib_size" in info
    assert "dynamic_lib_size" in info


def test_build_musl_function(tmp_path):
    """Test build_musl helper function"""
    config = MuslConfig(link_mode=LinkMode.STATIC)
    result = build_musl(config, tmp_path)

    assert isinstance(result, MuslBuildResult)
    assert result.static_lib.exists()


def test_musl_size_optimization_effect(tmp_path):
    """Test that size optimization produces smaller libraries"""
    config_size = MuslConfig(
        optimization=OptimizationLevel.SIZE,
        link_mode=LinkMode.STATIC
    )
    config_speed = MuslConfig(
        optimization=OptimizationLevel.SPEED,
        link_mode=LinkMode.STATIC
    )

    result_size = build_musl(config_size, tmp_path / "size")
    result_speed = build_musl(config_speed, tmp_path / "speed")

    assert result_size.static_lib.stat().st_size < result_speed.static_lib.stat().st_size


def test_musl_headers_created(tmp_path):
    """Test that header files are created"""
    config = MuslConfig()
    result = build_musl(config, tmp_path)

    # Check essential headers
    assert (result.include_dir / "stdio.h").exists()
    assert (result.include_dir / "stdlib.h").exists()
    assert (result.include_dir / "string.h").exists()


def test_musl_config_get_configure_flags():
    """Test configure flags generation"""
    config = MuslConfig(
        link_mode=LinkMode.STATIC,
        enable_debug_symbols=True,
        enable_wrapper_functions=True,
    )

    flags = config.get_configure_flags()

    assert "--disable-shared" in flags
    assert "--enable-debug" in flags
    assert "--enable-wrapper" in flags
