"""
Unit tests for build configuration
"""

import pytest
from src.build.config import (
    BuildConfig,
    Architecture,
    SecurityLevel,
    ImageType,
    SystemRequirements,
)


class TestBuildConfig:
    """Unit tests for BuildConfig class"""

    def test_default_config(self):
        """Test default configuration values"""
        config = BuildConfig()
        assert config.architecture == Architecture.X86_64
        assert config.security_level == SecurityLevel.FULL
        assert config.image_type == ImageType.MINIMAL
        assert config.reproducible is True
        assert config.debug is False
        assert config.kernel_modules == []

    def test_custom_config(self):
        """Test custom configuration values"""
        config = BuildConfig(
            architecture=Architecture.ARM64,
            security_level=SecurityLevel.STANDARD,
            image_type=ImageType.EXTENDED,
            reproducible=False,
            debug=True,
            kernel_modules=["module1", "module2"],
        )
        assert config.architecture == Architecture.ARM64
        assert config.security_level == SecurityLevel.STANDARD
        assert config.image_type == ImageType.EXTENDED
        assert config.reproducible is False
        assert config.debug is True
        assert len(config.kernel_modules) == 2

    def test_max_image_size_minimal(self):
        """Test max image size for minimal image"""
        config = BuildConfig(image_type=ImageType.MINIMAL)
        assert config.max_image_size == 5 * 1024 * 1024

    def test_max_image_size_standard(self):
        """Test max image size for standard image"""
        config = BuildConfig(image_type=ImageType.STANDARD)
        assert config.max_image_size == 15 * 1024 * 1024

    def test_max_image_size_extended(self):
        """Test max image size for extended image"""
        config = BuildConfig(image_type=ImageType.EXTENDED)
        assert config.max_image_size == 50 * 1024 * 1024

    def test_security_cflags_minimal(self):
        """Test security CFLAGS for minimal security level"""
        config = BuildConfig(security_level=SecurityLevel.MINIMAL)
        flags = config.security_cflags
        assert "-fstack-protector" in flags
        assert len(flags) == 1

    def test_security_cflags_standard(self):
        """Test security CFLAGS for standard security level"""
        config = BuildConfig(security_level=SecurityLevel.STANDARD)
        flags = config.security_cflags
        assert "-fstack-protector" in flags
        assert "-D_FORTIFY_SOURCE=2" in flags
        assert len(flags) == 2

    def test_security_cflags_full(self):
        """Test security CFLAGS for full security level"""
        config = BuildConfig(security_level=SecurityLevel.FULL)
        flags = config.security_cflags
        assert "-fPIE" in flags
        assert "-fstack-protector-strong" in flags
        assert "-D_FORTIFY_SOURCE=2" in flags
        assert len(flags) == 4

    def test_security_ldflags_full(self):
        """Test security LDFLAGS for full security level"""
        config = BuildConfig(security_level=SecurityLevel.FULL)
        flags = config.security_ldflags
        assert "-Wl,-z,relro" in flags
        assert "-Wl,-z,now" in flags
        assert "-pie" in flags


class TestSystemRequirements:
    """Unit tests for SystemRequirements class"""

    def test_default_requirements(self):
        """Test default system requirements"""
        req = SystemRequirements()
        assert req.min_ram_mb == 128
        assert req.recommended_ram_mb == 512
        assert req.min_storage_mb == 512
        assert req.recommended_storage_mb == 2048

    def test_custom_requirements(self):
        """Test custom system requirements"""
        req = SystemRequirements(
            min_ram_mb=256,
            recommended_ram_mb=1024,
            min_storage_mb=1024,
            recommended_storage_mb=4096,
        )
        assert req.min_ram_mb == 256
        assert req.recommended_ram_mb == 1024
        assert req.min_storage_mb == 1024
        assert req.recommended_storage_mb == 4096
