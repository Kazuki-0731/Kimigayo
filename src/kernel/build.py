"""
Kernel build system for Kimigayo OS

Handles kernel configuration, compilation, and module management
with security hardening and reproducible builds.
"""

import os
import subprocess
import hashlib
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum


class KernelVersion(Enum):
    """Supported kernel versions"""
    KERNEL_6_6 = "6.6"  # LTS


@dataclass
class KernelConfig:
    """Kernel build configuration"""
    architecture: str  # x86_64 or arm64
    version: KernelVersion = KernelVersion.KERNEL_6_6
    config_file: Optional[Path] = None
    modules: List[str] = None
    enable_hardening: bool = True
    reproducible: bool = True

    def __post_init__(self):
        if self.modules is None:
            self.modules = []

        # Set default config file based on architecture
        if self.config_file is None:
            project_root = Path(__file__).parent.parent.parent
            self.config_file = (
                project_root / "src" / "kernel" / "config" /
                f"kimigayo_{self.architecture}_defconfig"
            )


@dataclass
class KernelBuildResult:
    """Result of kernel build operation"""
    kernel_image: Path
    modules_dir: Optional[Path]
    config_file: Path
    checksum: str
    size_bytes: int
    build_log: str

    def verify_checksum(self, expected: str) -> bool:
        """Verify kernel image checksum"""
        return self.checksum == expected


class KernelBuilder:
    """Kernel build system with security hardening"""

    def __init__(self, config: KernelConfig, output_dir: Path):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.kernel_dir = self.output_dir / "linux"
        self.build_dir = self.output_dir / "build"
        self.modules_dir = self.output_dir / "modules"

    def setup_reproducible_environment(self):
        """Setup environment for reproducible builds"""
        if not self.config.reproducible:
            return

        # Set SOURCE_DATE_EPOCH for reproducible timestamps
        os.environ["SOURCE_DATE_EPOCH"] = "0"

        # Set locale for reproducible sorting
        os.environ["LC_ALL"] = "C"
        os.environ["TZ"] = "UTC"

        # Disable build timestamp
        os.environ["KBUILD_BUILD_TIMESTAMP"] = ""
        os.environ["KBUILD_BUILD_USER"] = "kimigayo"
        os.environ["KBUILD_BUILD_HOST"] = "kimigayo"

    def get_hardening_flags(self) -> Dict[str, str]:
        """Get kernel hardening compilation flags"""
        if not self.config.enable_hardening:
            return {}

        return {
            "KCFLAGS": "-fPIE -fstack-protector-strong -D_FORTIFY_SOURCE=2",
            "KAFLAGS": "-Wa,--noexecstack",
        }

    def download_kernel_source(self) -> bool:
        """Download Linux kernel source (stub for now)"""
        # In real implementation, this would download and verify kernel sources
        # For now, we simulate this
        self.kernel_dir.mkdir(parents=True, exist_ok=True)
        return True

    def configure_kernel(self) -> bool:
        """Configure kernel with defconfig"""
        if not self.config.config_file.exists():
            raise FileNotFoundError(
                f"Kernel config file not found: {self.config.config_file}"
            )

        # Copy config to build directory
        self.build_dir.mkdir(parents=True, exist_ok=True)
        config_dest = self.build_dir / ".config"

        # In real implementation, this would run make defconfig
        # For now, we copy the config file
        import shutil
        shutil.copy(self.config.config_file, config_dest)

        return True

    def verify_security_config(self) -> bool:
        """Verify that security hardening options are enabled"""
        config_file = self.build_dir / ".config"
        if not config_file.exists():
            return False

        required_options = [
            "CONFIG_SECURITY=y",
            "CONFIG_HARDENED_USERCOPY=y",
            "CONFIG_FORTIFY_SOURCE=y",
            "CONFIG_STACKPROTECTOR=y",
            "CONFIG_STACKPROTECTOR_STRONG=y",
            "CONFIG_STRICT_KERNEL_RWX=y",
            "CONFIG_STRICT_MODULE_RWX=y",
        ]

        config_content = config_file.read_text()

        for option in required_options:
            if option not in config_content:
                raise ValueError(f"Required security option not found: {option}")

        return True

    def build_kernel(self) -> KernelBuildResult:
        """Build kernel with current configuration"""
        self.setup_reproducible_environment()

        # Download sources
        if not self.download_kernel_source():
            raise RuntimeError("Failed to download kernel sources")

        # Configure kernel
        if not self.configure_kernel():
            raise RuntimeError("Failed to configure kernel")

        # Verify security configuration
        if self.config.enable_hardening:
            if not self.verify_security_config():
                raise RuntimeError("Security configuration verification failed")

        # Get hardening flags
        build_env = os.environ.copy()
        build_env.update(self.get_hardening_flags())

        # Build kernel image (stub - in real implementation would run make)
        kernel_image = self.build_dir / "vmlinuz"

        # Create a mock kernel image for testing
        kernel_image.write_bytes(b"KERNEL_IMAGE_MOCK_DATA")

        # Calculate checksum
        checksum = self._calculate_checksum(kernel_image)

        # Get size
        size_bytes = kernel_image.stat().st_size

        # Build log
        build_log = "Kernel build completed successfully\n"

        return KernelBuildResult(
            kernel_image=kernel_image,
            modules_dir=self.modules_dir if self.config.modules else None,
            config_file=self.build_dir / ".config",
            checksum=checksum,
            size_bytes=size_bytes,
            build_log=build_log,
        )

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def enable_kernel_module(self, module_name: str) -> bool:
        """Enable a kernel module in configuration"""
        config_file = self.build_dir / ".config"
        if not config_file.exists():
            raise FileNotFoundError("Kernel not configured yet")

        # Add module to configuration (simplified)
        self.config.modules.append(module_name)
        return True

    def get_enabled_security_features(self) -> List[str]:
        """Get list of enabled security features"""
        config_file = self.build_dir / ".config"
        if not config_file.exists():
            return []

        security_features = []
        security_options = [
            "CONFIG_SECURITY",
            "CONFIG_HARDENED_USERCOPY",
            "CONFIG_FORTIFY_SOURCE",
            "CONFIG_PAGE_TABLE_ISOLATION",
            "CONFIG_RANDOMIZE_BASE",
            "CONFIG_RANDOMIZE_MEMORY",
            "CONFIG_STACKPROTECTOR_STRONG",
            "CONFIG_SLAB_FREELIST_RANDOM",
            "CONFIG_MODULE_SIG_FORCE",
        ]

        config_content = config_file.read_text()

        for option in security_options:
            if f"{option}=y" in config_content:
                security_features.append(option)

        return security_features


def build_kernel(config: KernelConfig, output_dir: Path) -> KernelBuildResult:
    """Build kernel with specified configuration"""
    builder = KernelBuilder(config, output_dir)
    return builder.build_kernel()
