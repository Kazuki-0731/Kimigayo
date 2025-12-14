"""
Build configuration for Kimigayo OS
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Architecture(Enum):
    """Supported architectures"""
    X86_64 = "x86_64"
    ARM64 = "arm64"


class SecurityLevel(Enum):
    """Security hardening levels"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"


class ImageType(Enum):
    """Image types with size constraints"""
    MINIMAL = "minimal"    # 5MB以下
    STANDARD = "standard"  # 15MB以下
    EXTENDED = "extended"  # 50MB以下


@dataclass
class BuildConfig:
    """Build configuration for Kimigayo OS"""
    architecture: Architecture = Architecture.X86_64
    security_level: SecurityLevel = SecurityLevel.FULL
    image_type: ImageType = ImageType.MINIMAL
    reproducible: bool = True
    debug: bool = False
    kernel_modules: List[str] = None

    def __post_init__(self):
        if self.kernel_modules is None:
            self.kernel_modules = []

    @property
    def max_image_size(self) -> int:
        """Returns the maximum image size in bytes based on image type"""
        size_map = {
            ImageType.MINIMAL: 5 * 1024 * 1024,   # 5 MB
            ImageType.STANDARD: 15 * 1024 * 1024,  # 15 MB
            ImageType.EXTENDED: 50 * 1024 * 1024,  # 50 MB
        }
        return size_map[self.image_type]

    @property
    def security_cflags(self) -> List[str]:
        """Returns security CFLAGS based on security level"""
        minimal_flags = ["-fstack-protector"]
        standard_flags = minimal_flags + ["-D_FORTIFY_SOURCE=2"]
        full_flags = standard_flags + [
            "-fPIE",
            "-fstack-protector-strong",
        ]

        flags_map = {
            SecurityLevel.MINIMAL: minimal_flags,
            SecurityLevel.STANDARD: standard_flags,
            SecurityLevel.FULL: full_flags,
        }
        return flags_map[self.security_level]

    @property
    def security_ldflags(self) -> List[str]:
        """Returns security LDFLAGS based on security level"""
        minimal_flags = []
        standard_flags = minimal_flags + ["-Wl,-z,relro"]
        full_flags = standard_flags + [
            "-Wl,-z,now",
            "-pie",
        ]

        flags_map = {
            SecurityLevel.MINIMAL: minimal_flags,
            SecurityLevel.STANDARD: standard_flags,
            SecurityLevel.FULL: full_flags,
        }
        return flags_map[self.security_level]


@dataclass
class SystemRequirements:
    """System requirements for Kimigayo OS"""
    min_ram_mb: int = 128
    recommended_ram_mb: int = 512
    min_storage_mb: int = 512
    recommended_storage_mb: int = 2048
