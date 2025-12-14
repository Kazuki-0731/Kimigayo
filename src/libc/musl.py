"""
musl libc integration and optimization for Kimigayo OS

Provides lightweight, secure C library with static and dynamic linking support.
"""

import hashlib
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum


class LinkMode(Enum):
    """Linking mode for musl libc"""
    STATIC = "static"
    DYNAMIC = "dynamic"
    BOTH = "both"


class OptimizationLevel(Enum):
    """Optimization level for musl libc"""
    SIZE = "size"  # -Os
    SPEED = "speed"  # -O2
    BALANCED = "balanced"  # -O2 with some size optimizations


@dataclass
class MuslConfig:
    """musl libc build configuration"""
    architecture: str = "x86_64"
    link_mode: LinkMode = LinkMode.STATIC
    optimization: OptimizationLevel = OptimizationLevel.SIZE
    enable_security_hardening: bool = True
    enable_wrapper_functions: bool = True
    enable_debug_symbols: bool = False
    custom_cflags: List[str] = field(default_factory=list)
    custom_ldflags: List[str] = field(default_factory=list)

    def get_cflags(self) -> List[str]:
        """Get compilation flags for musl"""
        flags = list(self.custom_cflags)

        # Optimization flags
        if self.optimization == OptimizationLevel.SIZE:
            flags.extend(["-Os", "-ffunction-sections", "-fdata-sections"])
        elif self.optimization == OptimizationLevel.SPEED:
            flags.append("-O2")
        else:  # BALANCED
            flags.extend(["-O2", "-ffunction-sections"])

        # Security hardening flags
        if self.enable_security_hardening:
            flags.extend([
                "-fPIE",
                "-fstack-protector-strong",
                "-D_FORTIFY_SOURCE=2",
                "-fno-strict-overflow",
                "-fno-delete-null-pointer-checks",
            ])

        # Architecture-specific flags
        if self.architecture == "x86_64":
            flags.extend(["-m64", "-march=x86-64"])
        elif self.architecture in ["arm64", "aarch64"]:
            flags.append("-march=armv8-a")

        return flags

    def get_ldflags(self) -> List[str]:
        """Get linker flags for musl"""
        flags = list(self.custom_ldflags)

        # Size optimization
        if self.optimization == OptimizationLevel.SIZE:
            flags.extend(["-Wl,--gc-sections", "-Wl,--strip-all"])

        # Security hardening
        if self.enable_security_hardening:
            flags.extend([
                "-Wl,-z,relro",
                "-Wl,-z,now",
                "-Wl,-z,noexecstack",
            ])

        return flags

    def get_configure_flags(self) -> List[str]:
        """Get configuration flags for musl build"""
        flags = []

        # Disable features not needed for minimal systems
        flags.append("--disable-shared" if self.link_mode == LinkMode.STATIC else "--enable-shared")

        # Enable wrapper functions if requested
        if self.enable_wrapper_functions:
            flags.append("--enable-wrapper")

        # Debug symbols
        if self.enable_debug_symbols:
            flags.append("--enable-debug")
        else:
            flags.append("--disable-debug")

        return flags

    def supports_static_linking(self) -> bool:
        """Check if static linking is supported"""
        return self.link_mode in [LinkMode.STATIC, LinkMode.BOTH]

    def supports_dynamic_linking(self) -> bool:
        """Check if dynamic linking is supported"""
        return self.link_mode in [LinkMode.DYNAMIC, LinkMode.BOTH]


@dataclass
class MuslBuildResult:
    """Result of musl libc build"""
    lib_dir: Path
    include_dir: Path
    config: MuslConfig
    static_lib: Optional[Path] = None
    dynamic_lib: Optional[Path] = None
    size_bytes: int = 0
    checksum: str = ""

    def verify_static_lib(self) -> bool:
        """Verify static library exists"""
        if self.config.supports_static_linking():
            return self.static_lib is not None and self.static_lib.exists()
        return True

    def verify_dynamic_lib(self) -> bool:
        """Verify dynamic library exists"""
        if self.config.supports_dynamic_linking():
            return self.dynamic_lib is not None and self.dynamic_lib.exists()
        return True

    def get_total_size(self) -> int:
        """Get total size of built libraries"""
        total = 0
        if self.static_lib and self.static_lib.exists():
            total += self.static_lib.stat().st_size
        if self.dynamic_lib and self.dynamic_lib.exists():
            total += self.dynamic_lib.stat().st_size
        return total


class MuslBuilder:
    """musl libc build system"""

    def __init__(self, config: MuslConfig, output_dir: Path):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.lib_dir = self.output_dir / "lib"
        self.include_dir = self.output_dir / "include"

    def setup_directories(self):
        """Setup build directories"""
        self.lib_dir.mkdir(parents=True, exist_ok=True)
        self.include_dir.mkdir(parents=True, exist_ok=True)

    def build(self) -> MuslBuildResult:
        """Build musl libc with current configuration"""
        self.setup_directories()

        # Build static library if needed
        static_lib = None
        if self.config.supports_static_linking():
            static_lib = self._build_static_library()

        # Build dynamic library if needed
        dynamic_lib = None
        if self.config.supports_dynamic_linking():
            dynamic_lib = self._build_dynamic_library()

        # Create header files (mock)
        self._create_headers()

        # Calculate checksum
        checksum = self._calculate_checksum(static_lib or dynamic_lib)

        result = MuslBuildResult(
            lib_dir=self.lib_dir,
            include_dir=self.include_dir,
            config=self.config,
            static_lib=static_lib,
            dynamic_lib=dynamic_lib,
            checksum=checksum,
        )

        result.size_bytes = result.get_total_size()

        return result

    def _build_static_library(self) -> Path:
        """Build static musl library (mock)"""
        lib_path = self.lib_dir / "libc.a"

        # Estimate size based on configuration
        base_size = 600000  # ~600KB base size for musl

        # Apply optimization factor
        if self.config.optimization == OptimizationLevel.SIZE:
            size = int(base_size * 0.8)  # 20% reduction
        elif self.config.optimization == OptimizationLevel.SPEED:
            size = int(base_size * 1.1)  # 10% increase
        else:
            size = base_size

        # Create mock library
        mock_data = b"MUSL_STATIC" * ((size // 11) + 1)
        lib_path.write_bytes(mock_data[:size])

        return lib_path

    def _build_dynamic_library(self) -> Path:
        """Build dynamic musl library (mock)"""
        lib_path = self.lib_dir / "libc.so"

        # Dynamic library is typically smaller
        base_size = 400000  # ~400KB

        if self.config.optimization == OptimizationLevel.SIZE:
            size = int(base_size * 0.85)
        elif self.config.optimization == OptimizationLevel.SPEED:
            size = int(base_size * 1.05)
        else:
            size = base_size

        # Create mock library
        mock_data = b"MUSL_SHARED" * ((size // 11) + 1)
        lib_path.write_bytes(mock_data[:size])

        return lib_path

    def _create_headers(self):
        """Create header files (mock)"""
        # Create some essential headers
        headers = [
            "stdio.h",
            "stdlib.h",
            "string.h",
            "unistd.h",
            "stdint.h",
            "sys/types.h",
        ]

        for header in headers:
            header_path = self.include_dir / header
            header_path.parent.mkdir(parents=True, exist_ok=True)

            # Create mock header content
            content = f"/* {header} - musl libc header */\n"
            header_path.write_text(content)

    def _calculate_checksum(self, lib_path: Optional[Path]) -> str:
        """Calculate SHA-256 checksum of library"""
        if not lib_path or not lib_path.exists():
            return ""

        sha256 = hashlib.sha256()
        with open(lib_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_compiler_flags(self) -> Dict[str, str]:
        """Get compiler flags for using musl"""
        flags = {
            "CC": f"{self.config.architecture}-linux-musl-gcc",
            "CFLAGS": " ".join(self.config.get_cflags()),
            "LDFLAGS": " ".join(self.config.get_ldflags()),
        }

        if self.config.supports_static_linking():
            flags["LDFLAGS"] += " -static"

        return flags

    def verify_security_features(self) -> bool:
        """Verify that security features are enabled"""
        if not self.config.enable_security_hardening:
            return True

        cflags = self.config.get_cflags()
        ldflags = self.config.get_ldflags()

        # Check required security flags
        required_cflags = ["-fPIE", "-fstack-protector-strong"]
        required_ldflags = ["-Wl,-z,relro", "-Wl,-z,now"]

        for flag in required_cflags:
            if flag not in cflags:
                return False

        for flag in required_ldflags:
            if flag not in ldflags:
                return False

        return True

    def get_library_info(self, result: MuslBuildResult) -> Dict[str, any]:
        """Get information about built libraries"""
        info = {
            "architecture": self.config.architecture,
            "link_mode": self.config.link_mode.value,
            "optimization": self.config.optimization.value,
            "security_hardening": self.config.enable_security_hardening,
            "total_size": result.size_bytes,
        }

        if result.static_lib:
            info["static_lib_size"] = result.static_lib.stat().st_size

        if result.dynamic_lib:
            info["dynamic_lib_size"] = result.dynamic_lib.stat().st_size

        return info


def build_musl(config: MuslConfig, output_dir: Path) -> MuslBuildResult:
    """Build musl libc with specified configuration"""
    builder = MuslBuilder(config, output_dir)
    return builder.build()
