"""
Unit tests for BusyBox configuration and build system
"""

import pytest
from pathlib import Path

from src.utilities.busybox import (
    BusyBoxConfig,
    BusyBoxUtility,
    BusyBoxBuilder,
    ImageProfile,
    UtilityCategory,
    ESSENTIAL_UTILITIES,
    OPTIONAL_UTILITIES,
    build_busybox,
)


def test_utility_category_enum():
    """Test UtilityCategory enum values"""
    assert UtilityCategory.CORE.value == "core"
    assert UtilityCategory.SHELL.value == "shell"
    assert UtilityCategory.FILE.value == "file"
    assert UtilityCategory.TEXT.value == "text"
    assert UtilityCategory.NETWORK.value == "network"
    assert UtilityCategory.SYSTEM.value == "system"
    assert UtilityCategory.PROCESS.value == "process"


def test_image_profile_enum():
    """Test ImageProfile enum values"""
    assert ImageProfile.MINIMAL.value == "minimal"
    assert ImageProfile.STANDARD.value == "standard"
    assert ImageProfile.EXTENDED.value == "extended"


def test_busybox_utility_creation():
    """Test BusyBoxUtility creation"""
    util = BusyBoxUtility(
        name="test",
        category=UtilityCategory.CORE,
        essential=True,
        description="Test utility",
        size_bytes=1000
    )

    assert util.name == "test"
    assert util.category == UtilityCategory.CORE
    assert util.essential is True
    assert util.description == "Test utility"
    assert util.size_bytes == 1000


def test_busybox_utility_equality():
    """Test BusyBoxUtility equality"""
    util1 = BusyBoxUtility("test", UtilityCategory.CORE)
    util2 = BusyBoxUtility("test", UtilityCategory.FILE)
    util3 = BusyBoxUtility("other", UtilityCategory.CORE)

    assert util1 == util2  # Same name
    assert util1 != util3  # Different name


def test_essential_utilities_defined():
    """Test that essential utilities are defined"""
    assert len(ESSENTIAL_UTILITIES) > 0

    # Check some expected essential utilities
    essential_names = {u.name for u in ESSENTIAL_UTILITIES}
    assert "sh" in essential_names
    assert "ls" in essential_names
    assert "cp" in essential_names
    assert "mv" in essential_names
    assert "rm" in essential_names


def test_optional_utilities_defined():
    """Test that optional utilities are defined"""
    assert len(OPTIONAL_UTILITIES) > 0

    # Check some expected optional utilities
    optional_names = {u.name for u in OPTIONAL_UTILITIES}
    assert "wget" in optional_names
    assert "tar" in optional_names
    assert "vi" in optional_names


def test_busybox_config_defaults():
    """Test BusyBoxConfig default values"""
    config = BusyBoxConfig()

    assert config.profile == ImageProfile.MINIMAL
    assert config.enable_static is True
    assert config.enable_size_optimization is True
    assert config.enable_security_hardening is True
    assert len(config.utilities) > 0


def test_busybox_config_minimal_profile():
    """Test minimal profile utilities"""
    config = BusyBoxConfig(profile=ImageProfile.MINIMAL)

    # Should have only essential utilities
    assert config.verify_essential_utilities()

    essential_names = {u.name for u in ESSENTIAL_UTILITIES}
    config_names = set(config.get_utility_names())

    assert essential_names == config_names


def test_busybox_config_standard_profile():
    """Test standard profile utilities"""
    config = BusyBoxConfig(profile=ImageProfile.STANDARD)

    # Should have essential utilities
    assert config.verify_essential_utilities()

    # Should have more than minimal
    minimal_config = BusyBoxConfig(profile=ImageProfile.MINIMAL)
    assert len(config.utilities) > len(minimal_config.utilities)


def test_busybox_config_extended_profile():
    """Test extended profile utilities"""
    config = BusyBoxConfig(profile=ImageProfile.EXTENDED)

    # Should have essential utilities
    assert config.verify_essential_utilities()

    # Should have most utilities
    assert len(config.utilities) > len(ESSENTIAL_UTILITIES)


def test_busybox_config_add_utility():
    """Test adding utility to configuration"""
    config = BusyBoxConfig(profile=ImageProfile.MINIMAL)
    initial_count = len(config.utilities)

    # Add an optional utility
    optional = OPTIONAL_UTILITIES[0]
    result = config.add_utility(optional)

    if result:
        assert len(config.utilities) == initial_count + 1
        assert optional in config.utilities


def test_busybox_config_remove_utility():
    """Test removing utility from configuration"""
    config = BusyBoxConfig(profile=ImageProfile.EXTENDED)

    # Find an optional utility in config
    optional = next(u for u in config.utilities if not u.essential)

    # Remove it
    result = config.remove_utility(optional)
    assert result is True
    assert optional not in config.utilities


def test_busybox_config_cannot_remove_essential():
    """Test that essential utilities cannot be removed"""
    config = BusyBoxConfig()

    essential = ESSENTIAL_UTILITIES[0]

    with pytest.raises(ValueError, match="Cannot remove essential utility"):
        config.remove_utility(essential)


def test_busybox_config_get_cflags():
    """Test getting compilation flags"""
    config = BusyBoxConfig(
        enable_size_optimization=True,
        enable_security_hardening=True,
    )

    cflags = config.get_cflags()

    # Size optimization flags
    assert "-Os" in cflags
    assert "-ffunction-sections" in cflags

    # Security flags
    assert "-fPIE" in cflags
    assert "-fstack-protector-strong" in cflags


def test_busybox_config_get_ldflags():
    """Test getting linker flags"""
    config = BusyBoxConfig(
        enable_static=True,
        enable_size_optimization=True,
        enable_security_hardening=True,
    )

    ldflags = config.get_ldflags()

    # Static linking
    assert "-static" in ldflags

    # Size optimization
    assert "-Wl,--gc-sections" in ldflags
    assert "-Wl,--strip-all" in ldflags

    # Security flags
    assert "-Wl,-z,relro" in ldflags
    assert "-Wl,-z,now" in ldflags


def test_busybox_config_estimated_size():
    """Test size estimation"""
    config = BusyBoxConfig(profile=ImageProfile.MINIMAL)
    size = config.get_estimated_size()

    # Size should be positive
    assert size > 0

    # Minimal should be smaller than extended
    extended_config = BusyBoxConfig(profile=ImageProfile.EXTENDED)
    extended_size = extended_config.get_estimated_size()

    assert size < extended_size


def test_busybox_builder_initialization(tmp_path):
    """Test BusyBoxBuilder initialization"""
    config = BusyBoxConfig()
    builder = BusyBoxBuilder(config, tmp_path)

    assert builder.config == config
    assert builder.output_dir == tmp_path
    assert builder.output_dir.exists()


def test_busybox_builder_generate_config_file(tmp_path):
    """Test configuration file generation"""
    config = BusyBoxConfig(profile=ImageProfile.MINIMAL)
    builder = BusyBoxBuilder(config, tmp_path)

    config_file = builder.generate_config_file()

    assert config_file.exists()
    assert config_file.name == ".config"

    content = config_file.read_text()
    assert "Kimigayo OS BusyBox Configuration" in content


def test_busybox_builder_build(tmp_path):
    """Test BusyBox build"""
    config = BusyBoxConfig(profile=ImageProfile.MINIMAL)
    builder = BusyBoxBuilder(config, tmp_path)

    result = builder.build()

    assert result.binary_path.exists()
    assert result.size_bytes > 0
    assert len(result.checksum) == 64  # SHA-256
    assert len(result.utilities) > 0


def test_busybox_builder_list_utilities(tmp_path):
    """Test listing available utilities"""
    config = BusyBoxConfig()
    builder = BusyBoxBuilder(config, tmp_path)

    by_category = builder.list_available_utilities()

    assert len(by_category) > 0
    assert "core" in by_category or "shell" in by_category


def test_busybox_build_result_verify_checksum(tmp_path):
    """Test build result checksum verification"""
    config = BusyBoxConfig()
    result = build_busybox(config, tmp_path)

    # Should verify with same checksum
    assert result.verify_checksum(result.checksum)

    # Should fail with different checksum
    assert not result.verify_checksum("invalid")


def test_busybox_build_result_verify_utilities(tmp_path):
    """Test build result utilities verification"""
    config = BusyBoxConfig()
    result = build_busybox(config, tmp_path)

    # Should verify successfully
    assert result.verify_utilities()


def test_build_busybox_function(tmp_path):
    """Test build_busybox helper function"""
    config = BusyBoxConfig(profile=ImageProfile.STANDARD)
    result = build_busybox(config, tmp_path)

    assert result.binary_path.exists()
    assert result.config == config


def test_busybox_config_custom_cflags(tmp_path):
    """Test custom CFLAGS"""
    custom_flags = ["-O3", "-march=native"]
    config = BusyBoxConfig(custom_cflags=custom_flags)

    cflags = config.get_cflags()

    assert "-O3" in cflags
    assert "-march=native" in cflags


def test_size_optimization_reduces_size(tmp_path):
    """Test that size optimization reduces estimated size"""
    config_opt = BusyBoxConfig(enable_size_optimization=True)
    config_no_opt = BusyBoxConfig(enable_size_optimization=False)

    size_opt = config_opt.get_estimated_size()
    size_no_opt = config_no_opt.get_estimated_size()

    # Optimized should be smaller
    assert size_opt < size_no_opt
