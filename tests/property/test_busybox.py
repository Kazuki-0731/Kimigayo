"""
Property-based tests for BusyBox configuration

Tests validate essential utilities completeness and modular configuration.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
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


# Strategy for image profiles
image_profiles = st.sampled_from(ImageProfile)


# Strategy for utility categories
utility_categories = st.sampled_from(UtilityCategory)


# Strategy for BusyBox configurations
@st.composite
def busybox_configs(draw):
    """Strategy for generating BusyBox configurations"""
    profile = draw(image_profiles)
    enable_static = draw(st.booleans())
    enable_size_optimization = draw(st.booleans())
    enable_security_hardening = draw(st.booleans())

    return BusyBoxConfig(
        profile=profile,
        enable_static=enable_static,
        enable_size_optimization=enable_size_optimization,
        enable_security_hardening=enable_security_hardening,
    )


# **Feature: kimigayo-os-core, Property 3: 必須ユーティリティ完全性**
# **検証対象: 要件 1.4**
@pytest.mark.property
@given(config=busybox_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_essential_utilities_completeness(config, tmp_path):
    """
    任意のシステム構成に対して、必須Unixユーティリティが
    すべて含まれていなければならない
    """
    builder = BusyBoxBuilder(config, tmp_path)

    # Verify essential utilities are present
    assert config.verify_essential_utilities(), (
        "Essential utilities are missing from configuration"
    )

    # Build BusyBox
    result = builder.build()

    # Verify all essential utilities are in the built binary
    essential_names = {u.name for u in ESSENTIAL_UTILITIES}
    built_utilities = set(result.utilities)

    missing = essential_names - built_utilities
    assert not missing, f"Missing essential utilities: {missing}"

    # Verify result includes all configured utilities
    assert result.verify_utilities(), (
        "Built utilities don't match configured utilities"
    )


@pytest.mark.property
@given(profile=image_profiles)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_profile_utility_selection(profile, tmp_path):
    """
    Verify that different profiles include appropriate utilities
    """
    config = BusyBoxConfig(profile=profile)
    builder = BusyBoxBuilder(config, tmp_path)

    # All profiles must include essential utilities
    assert config.verify_essential_utilities()

    # Minimal should only have essentials
    if profile == ImageProfile.MINIMAL:
        essential_names = {u.name for u in ESSENTIAL_UTILITIES}
        config_names = set(config.get_utility_names())
        assert config_names == essential_names, (
            f"Minimal profile should only have essential utilities"
        )

    # Standard should have more than minimal
    if profile == ImageProfile.STANDARD:
        minimal_count = len(ESSENTIAL_UTILITIES)
        assert len(config.utilities) > minimal_count, (
            "Standard profile should have more utilities than minimal"
        )

    # Extended should have the most
    if profile == ImageProfile.EXTENDED:
        standard_config = BusyBoxConfig(profile=ImageProfile.STANDARD)
        assert len(config.utilities) >= len(standard_config.utilities), (
            "Extended profile should have at least as many utilities as standard"
        )


@pytest.mark.property
@given(config=busybox_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_size_optimization_effect(config, tmp_path):
    """
    Verify that size optimization reduces binary size
    """
    # Build with optimization
    config_opt = BusyBoxConfig(
        profile=config.profile,
        enable_size_optimization=True,
    )
    result_opt = build_busybox(config_opt, tmp_path / "opt")

    # Build without optimization
    config_no_opt = BusyBoxConfig(
        profile=config.profile,
        enable_size_optimization=False,
    )
    result_no_opt = build_busybox(config_no_opt, tmp_path / "no_opt")

    # Optimized should be smaller or equal
    assert result_opt.size_bytes <= result_no_opt.size_bytes, (
        f"Optimized build should be smaller: "
        f"{result_opt.size_bytes} vs {result_no_opt.size_bytes}"
    )


@pytest.mark.property
@given(config=busybox_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_static_linking_configuration(config, tmp_path):
    """
    Verify that static linking is properly configured
    """
    builder = BusyBoxBuilder(config, tmp_path)
    ldflags = config.get_ldflags()

    if config.enable_static:
        assert "-static" in ldflags, "Static linking flag should be present"


@pytest.mark.property
@given(config=busybox_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_security_hardening_flags(config, tmp_path):
    """
    Verify that security hardening flags are applied
    """
    if config.enable_security_hardening:
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
@given(config=busybox_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_build_reproducibility(config, tmp_path):
    """
    Verify that builds are reproducible
    """
    # Build twice
    result1 = build_busybox(config, tmp_path / "build1")
    result2 = build_busybox(config, tmp_path / "build2")

    # Checksums should be identical
    assert result1.checksum == result2.checksum, (
        f"Builds are not reproducible:\n"
        f"  Build 1: {result1.checksum}\n"
        f"  Build 2: {result2.checksum}"
    )

    # Sizes should be identical
    assert result1.size_bytes == result2.size_bytes, (
        f"Build sizes differ: {result1.size_bytes} vs {result2.size_bytes}"
    )


@pytest.mark.property
@given(
    profile1=image_profiles,
    profile2=image_profiles,
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_profile_size_ordering(profile1, profile2, tmp_path):
    """
    Verify that larger profiles produce larger binaries
    """
    config1 = BusyBoxConfig(profile=profile1)
    config2 = BusyBoxConfig(profile=profile2)

    size1 = config1.get_estimated_size()
    size2 = config2.get_estimated_size()

    profile_order = [ImageProfile.MINIMAL, ImageProfile.STANDARD, ImageProfile.EXTENDED]
    idx1 = profile_order.index(profile1)
    idx2 = profile_order.index(profile2)

    if idx1 < idx2:
        assert size1 <= size2, (
            f"{profile1.value} should not be larger than {profile2.value}"
        )
    elif idx1 > idx2:
        assert size1 >= size2, (
            f"{profile1.value} should not be smaller than {profile2.value}"
        )


@pytest.mark.property
@given(config=busybox_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_utility_add_remove(config, tmp_path):
    """
    Verify that utilities can be added and removed (except essential ones)
    """
    # Find an optional utility that's not in the current config
    optional = None
    for util in OPTIONAL_UTILITIES:
        if util not in config.utilities:
            optional = util
            break

    if optional is not None:
        # Add utility
        initial_count = len(config.utilities)
        result = config.add_utility(optional)

        assert result is True, "add_utility should return True for new utility"
        assert len(config.utilities) == initial_count + 1
        assert optional in config.utilities

    # Try to remove essential utility (should fail)
    essential = ESSENTIAL_UTILITIES[0]
    with pytest.raises(ValueError, match="Cannot remove essential utility"):
        config.remove_utility(essential)


@pytest.mark.property
@given(config=busybox_configs())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_config_file_generation(config, tmp_path):
    """
    Verify that configuration file is properly generated
    """
    builder = BusyBoxBuilder(config, tmp_path)
    config_file = builder.generate_config_file()

    # Config file should exist
    assert config_file.exists()

    # Config file should be non-empty
    assert config_file.stat().st_size > 0

    # Read and verify content
    content = config_file.read_text()

    # Should contain static config if enabled
    if config.enable_static:
        assert "CONFIG_STATIC=y" in content

    # Should list utilities
    for utility in config.utilities:
        # At minimum, the utility name should appear
        assert utility.name in content.lower()


@pytest.mark.property
@given(category=utility_categories)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_utilities_by_category(category, tmp_path):
    """
    Verify that utilities can be listed by category
    """
    config = BusyBoxConfig(profile=ImageProfile.EXTENDED)
    builder = BusyBoxBuilder(config, tmp_path)

    by_category = builder.list_available_utilities()

    # Should have entries for categories
    assert len(by_category) > 0

    # Each category should have at least one utility
    for cat, utilities in by_category.items():
        assert len(utilities) > 0
        # All utilities in category should have matching category
        for util in utilities:
            assert util.category.value == cat


@pytest.mark.property
@given(config=busybox_configs())
@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_estimated_vs_actual_size(config, tmp_path):
    """
    Verify that estimated size is reasonably close to actual size
    """
    estimated = config.get_estimated_size()
    result = build_busybox(config, tmp_path)
    actual = result.size_bytes

    # Estimated should be exactly the same as actual in our mock
    # (since we use estimated size to generate the mock binary)
    assert estimated == actual, (
        f"Estimated size ({estimated}) should match actual ({actual})"
    )
