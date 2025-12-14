"""
Cross-compilation environment for Kimigayo OS

Supports x86_64 and ARM64 targets with musl libc integration.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class Architecture(Enum):
    """Supported target architectures"""
    X86_64 = "x86_64"
    ARM64 = "arm64"
    AARCH64 = "aarch64"  # Alias for ARM64


class LibcType(Enum):
    """C library type"""
    MUSL = "musl"
    GLIBC = "glibc"


@dataclass
class ToolchainConfig:
    """Toolchain configuration for cross-compilation"""
    architecture: Architecture
    libc: LibcType = LibcType.MUSL
    toolchain_prefix: Optional[str] = None
    sysroot: Optional[Path] = None

    def __post_init__(self):
        # Set default toolchain prefix if not specified
        if self.toolchain_prefix is None:
            self.toolchain_prefix = self._get_default_prefix()

    def _get_default_prefix(self) -> str:
        """Get default toolchain prefix based on architecture and libc"""
        arch_map = {
            Architecture.X86_64: "x86_64-linux-musl",
            Architecture.ARM64: "aarch64-linux-musl",
            Architecture.AARCH64: "aarch64-linux-musl",
        }

        if self.libc == LibcType.GLIBC:
            arch_map = {
                Architecture.X86_64: "x86_64-linux-gnu",
                Architecture.ARM64: "aarch64-linux-gnu",
                Architecture.AARCH64: "aarch64-linux-gnu",
            }

        return arch_map.get(self.architecture, "")


@dataclass
class CrossCompileConfig:
    """Configuration for cross-compilation build"""
    target_arch: Architecture
    host_arch: Architecture = Architecture.X86_64
    toolchain: Optional[ToolchainConfig] = None
    cflags: List[str] = field(default_factory=list)
    ldflags: List[str] = field(default_factory=list)
    enable_static: bool = True
    enable_shared: bool = False

    def __post_init__(self):
        if self.toolchain is None:
            self.toolchain = ToolchainConfig(
                architecture=self.target_arch,
                libc=LibcType.MUSL
            )

        # Add default security flags if not present
        self._add_security_flags()

    def _add_security_flags(self):
        """Add default security hardening flags"""
        security_cflags = [
            "-fPIE",
            "-fstack-protector-strong",
            "-D_FORTIFY_SOURCE=2",
            "-fno-strict-overflow",
            "-fno-delete-null-pointer-checks",
        ]

        security_ldflags = [
            "-Wl,-z,relro",
            "-Wl,-z,now",
            "-Wl,-z,noexecstack",
        ]

        for flag in security_cflags:
            if flag not in self.cflags:
                self.cflags.append(flag)

        for flag in security_ldflags:
            if flag not in self.ldflags:
                self.ldflags.append(flag)

    def get_environment(self) -> Dict[str, str]:
        """Get environment variables for cross-compilation"""
        env = os.environ.copy()

        prefix = self.toolchain.toolchain_prefix

        # Set cross-compilation tools
        env["CC"] = f"{prefix}-gcc"
        env["CXX"] = f"{prefix}-g++"
        env["AR"] = f"{prefix}-ar"
        env["LD"] = f"{prefix}-ld"
        env["RANLIB"] = f"{prefix}-ranlib"
        env["STRIP"] = f"{prefix}-strip"
        env["OBJCOPY"] = f"{prefix}-objcopy"
        env["OBJDUMP"] = f"{prefix}-objdump"

        # Set compilation flags
        env["CFLAGS"] = " ".join(self.cflags)
        env["LDFLAGS"] = " ".join(self.ldflags)

        # Set target architecture
        if self.target_arch == Architecture.ARM64 or self.target_arch == Architecture.AARCH64:
            env["ARCH"] = "arm64"
            env["CROSS_COMPILE"] = "aarch64-linux-musl-"
        else:
            env["ARCH"] = "x86_64"
            env["CROSS_COMPILE"] = "x86_64-linux-musl-"

        # Set sysroot if available
        if self.toolchain.sysroot:
            env["SYSROOT"] = str(self.toolchain.sysroot)

        return env


class CrossCompiler:
    """Cross-compilation build system"""

    def __init__(self, config: CrossCompileConfig, output_dir: Path):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def verify_toolchain(self) -> bool:
        """Verify that the cross-compilation toolchain is available"""
        env = self.config.get_environment()
        cc = env.get("CC", "gcc")

        try:
            # Try to run the compiler with --version
            result = subprocess.run(
                [cc, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_toolchain_info(self) -> Dict[str, str]:
        """Get information about the toolchain"""
        env = self.config.get_environment()
        cc = env.get("CC", "gcc")

        info = {
            "compiler": cc,
            "target_arch": self.config.target_arch.value,
            "libc": self.config.toolchain.libc.value,
        }

        try:
            result = subprocess.run(
                [cc, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                info["version"] = result.stdout.split('\n')[0]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            info["version"] = "unknown"

        return info

    def compile_test_program(self, source_code: str) -> bool:
        """Compile a test program to verify toolchain"""
        test_file = self.output_dir / "test.c"
        output_file = self.output_dir / "test"

        # Write test source
        test_file.write_text(source_code)

        env = self.config.get_environment()
        cc = env.get("CC", "gcc")
        cflags = env.get("CFLAGS", "").split()
        ldflags = env.get("LDFLAGS", "").split()

        try:
            # Compile the test program
            cmd = [cc] + cflags + ["-o", str(output_file), str(test_file)] + ldflags

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )

            success = result.returncode == 0 and output_file.exists()

            # Clean up
            if test_file.exists():
                test_file.unlink()
            if output_file.exists():
                output_file.unlink()

            return success
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_libc_version(self) -> Optional[str]:
        """Get the version of the C library"""
        if self.config.toolchain.libc == LibcType.MUSL:
            # For musl, we can check the version by compiling a test program
            test_code = """
#include <stdio.h>
#ifdef __GLIBC__
#error "Not musl"
#endif
int main() {
    return 0;
}
"""
            if self.compile_test_program(test_code):
                return "musl"

        return None

    def setup_sysroot(self, sysroot_path: Path) -> bool:
        """Setup sysroot directory for cross-compilation"""
        sysroot_path = Path(sysroot_path)
        sysroot_path.mkdir(parents=True, exist_ok=True)

        # Create standard directories
        dirs = ["usr/include", "usr/lib", "lib", "bin", "sbin"]
        for dir_name in dirs:
            (sysroot_path / dir_name).mkdir(parents=True, exist_ok=True)

        self.config.toolchain.sysroot = sysroot_path
        return True


def setup_toolchain(
    target_arch: Architecture,
    output_dir: Path,
    libc: LibcType = LibcType.MUSL
) -> CrossCompiler:
    """Setup cross-compilation toolchain"""
    toolchain = ToolchainConfig(
        architecture=target_arch,
        libc=libc
    )

    config = CrossCompileConfig(
        target_arch=target_arch,
        toolchain=toolchain
    )

    return CrossCompiler(config, output_dir)
