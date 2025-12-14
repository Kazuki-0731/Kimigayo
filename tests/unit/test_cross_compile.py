"""
Unit tests for cross-compilation environment
"""

import pytest
from pathlib import Path

from src.toolchain.cross_compile import (
    Architecture,
    LibcType,
    ToolchainConfig,
    CrossCompileConfig,
    CrossCompiler,
    setup_toolchain,
)


def test_architecture_enum():
    """Test Architecture enum values"""
    assert Architecture.X86_64.value == "x86_64"
    assert Architecture.ARM64.value == "arm64"
    assert Architecture.AARCH64.value == "aarch64"


def test_libc_type_enum():
    """Test LibcType enum values"""
    assert LibcType.MUSL.value == "musl"
    assert LibcType.GLIBC.value == "glibc"


def test_toolchain_config_defaults():
    """Test ToolchainConfig default values"""
    config = ToolchainConfig(architecture=Architecture.X86_64)

    assert config.architecture == Architecture.X86_64
    assert config.libc == LibcType.MUSL
    assert config.toolchain_prefix == "x86_64-linux-musl"
    assert config.sysroot is None


def test_toolchain_config_arm64():
    """Test ToolchainConfig for ARM64"""
    config = ToolchainConfig(architecture=Architecture.ARM64)

    assert config.architecture == Architecture.ARM64
    assert config.toolchain_prefix == "aarch64-linux-musl"


def test_toolchain_config_with_glibc():
    """Test ToolchainConfig with glibc"""
    config = ToolchainConfig(
        architecture=Architecture.X86_64,
        libc=LibcType.GLIBC
    )

    assert config.libc == LibcType.GLIBC
    assert config.toolchain_prefix == "x86_64-linux-gnu"


def test_toolchain_config_custom_prefix():
    """Test ToolchainConfig with custom prefix"""
    custom_prefix = "custom-toolchain"
    config = ToolchainConfig(
        architecture=Architecture.X86_64,
        toolchain_prefix=custom_prefix
    )

    assert config.toolchain_prefix == custom_prefix


def test_cross_compile_config_defaults():
    """Test CrossCompileConfig default values"""
    config = CrossCompileConfig(target_arch=Architecture.X86_64)

    assert config.target_arch == Architecture.X86_64
    assert config.host_arch == Architecture.X86_64
    assert config.toolchain is not None
    assert config.enable_static is True
    assert config.enable_shared is False


def test_cross_compile_config_security_flags():
    """Test that security flags are automatically added"""
    config = CrossCompileConfig(target_arch=Architecture.X86_64)

    # Check CFLAGS
    assert "-fPIE" in config.cflags
    assert "-fstack-protector-strong" in config.cflags
    assert "-D_FORTIFY_SOURCE=2" in config.cflags

    # Check LDFLAGS
    assert "-Wl,-z,relro" in config.ldflags
    assert "-Wl,-z,now" in config.ldflags
    assert "-Wl,-z,noexecstack" in config.ldflags


def test_cross_compile_config_custom_flags():
    """Test CrossCompileConfig with custom flags"""
    custom_cflags = ["-O3", "-march=native"]
    custom_ldflags = ["-static"]

    config = CrossCompileConfig(
        target_arch=Architecture.X86_64,
        cflags=custom_cflags,
        ldflags=custom_ldflags,
    )

    # Custom flags should be preserved
    assert "-O3" in config.cflags
    assert "-march=native" in config.cflags
    assert "-static" in config.ldflags

    # Security flags should also be present
    assert "-fPIE" in config.cflags
    assert "-Wl,-z,relro" in config.ldflags


def test_cross_compile_config_environment_x86_64():
    """Test environment variables for x86_64"""
    config = CrossCompileConfig(target_arch=Architecture.X86_64)
    env = config.get_environment()

    assert env["CC"] == "x86_64-linux-musl-gcc"
    assert env["CXX"] == "x86_64-linux-musl-g++"
    assert env["ARCH"] == "x86_64"
    assert env["CROSS_COMPILE"] == "x86_64-linux-musl-"


def test_cross_compile_config_environment_arm64():
    """Test environment variables for ARM64"""
    config = CrossCompileConfig(target_arch=Architecture.ARM64)
    env = config.get_environment()

    assert env["CC"] == "aarch64-linux-musl-gcc"
    assert env["CXX"] == "aarch64-linux-musl-g++"
    assert env["ARCH"] == "arm64"
    assert env["CROSS_COMPILE"] == "aarch64-linux-musl-"


def test_cross_compile_config_sysroot():
    """Test sysroot in environment"""
    sysroot = Path("/custom/sysroot")
    toolchain = ToolchainConfig(
        architecture=Architecture.X86_64,
        sysroot=sysroot
    )
    config = CrossCompileConfig(
        target_arch=Architecture.X86_64,
        toolchain=toolchain
    )

    env = config.get_environment()
    assert env["SYSROOT"] == str(sysroot)


def test_cross_compiler_initialization(tmp_path):
    """Test CrossCompiler initialization"""
    config = CrossCompileConfig(target_arch=Architecture.X86_64)
    compiler = CrossCompiler(config, tmp_path)

    assert compiler.config == config
    assert compiler.output_dir == tmp_path
    assert compiler.output_dir.exists()


def test_cross_compiler_get_toolchain_info(tmp_path):
    """Test getting toolchain information"""
    config = CrossCompileConfig(target_arch=Architecture.ARM64)
    compiler = CrossCompiler(config, tmp_path)

    info = compiler.get_toolchain_info()

    assert "compiler" in info
    assert "target_arch" in info
    assert "libc" in info
    assert "version" in info

    assert info["compiler"] == "aarch64-linux-musl-gcc"
    assert info["target_arch"] == "arm64"
    assert info["libc"] == "musl"


def test_cross_compiler_sysroot_setup(tmp_path):
    """Test sysroot setup"""
    config = CrossCompileConfig(target_arch=Architecture.X86_64)
    compiler = CrossCompiler(config, tmp_path)

    sysroot_path = tmp_path / "sysroot"
    success = compiler.setup_sysroot(sysroot_path)

    assert success
    assert sysroot_path.exists()
    assert (sysroot_path / "usr/include").exists()
    assert (sysroot_path / "usr/lib").exists()
    assert (sysroot_path / "lib").exists()
    assert (sysroot_path / "bin").exists()
    assert (sysroot_path / "sbin").exists()


def test_cross_compiler_sysroot_in_config(tmp_path):
    """Test that sysroot is updated in config"""
    config = CrossCompileConfig(target_arch=Architecture.X86_64)
    compiler = CrossCompiler(config, tmp_path)

    sysroot_path = tmp_path / "sysroot"
    compiler.setup_sysroot(sysroot_path)

    # Sysroot should be updated in toolchain config
    assert compiler.config.toolchain.sysroot == sysroot_path

    # Environment should include sysroot
    env = compiler.config.get_environment()
    assert env["SYSROOT"] == str(sysroot_path)


def test_setup_toolchain_function(tmp_path):
    """Test setup_toolchain helper function"""
    compiler = setup_toolchain(Architecture.ARM64, tmp_path)

    assert isinstance(compiler, CrossCompiler)
    assert compiler.config.target_arch == Architecture.ARM64
    assert compiler.config.toolchain.libc == LibcType.MUSL
    assert compiler.output_dir == tmp_path


def test_setup_toolchain_with_glibc(tmp_path):
    """Test setup_toolchain with glibc"""
    compiler = setup_toolchain(
        Architecture.X86_64,
        tmp_path,
        libc=LibcType.GLIBC
    )

    assert compiler.config.toolchain.libc == LibcType.GLIBC
    info = compiler.get_toolchain_info()
    assert info["libc"] == "glibc"


def test_cross_compile_both_static_and_shared(tmp_path):
    """Test configuration with both static and shared linking"""
    config = CrossCompileConfig(
        target_arch=Architecture.X86_64,
        enable_static=True,
        enable_shared=True,
    )

    assert config.enable_static
    assert config.enable_shared


def test_environment_contains_all_tools():
    """Test that environment contains all required tools"""
    config = CrossCompileConfig(target_arch=Architecture.X86_64)
    env = config.get_environment()

    required_tools = ["CC", "CXX", "AR", "LD", "RANLIB", "STRIP", "OBJCOPY", "OBJDUMP"]

    for tool in required_tools:
        assert tool in env, f"{tool} not in environment"
        assert env[tool].startswith("x86_64-linux-musl-")
