"""
Property-based tests for build constraints

Tests validate the correctness properties defined in the design specification.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from pathlib import Path

from src.build.config import (
    BuildConfig,
    Architecture,
    SecurityLevel,
    ImageType,
)
from src.build.image import build_base_image


# Custom strategies for Kimigayo OS build configurations
@st.composite
def build_configurations(draw):
    """Strategy for generating valid BuildConfig instances"""
    arch = draw(st.sampled_from(Architecture))
    security = draw(st.sampled_from(SecurityLevel))
    image_type = draw(st.sampled_from(ImageType))
    reproducible = draw(st.booleans())
    debug = draw(st.booleans())

    # Generate a reasonable list of kernel modules
    num_modules = draw(st.integers(min_value=0, max_value=10))
    modules = [f"module_{i}" for i in range(num_modules)]

    return BuildConfig(
        architecture=arch,
        security_level=security,
        image_type=image_type,
        reproducible=reproducible,
        debug=debug,
        kernel_modules=modules,
    )


# **Feature: kimigayo-os-core, Property 1: ビルドサイズ制約**
# **検証対象: 要件 1.1**
@pytest.mark.property
@given(build_config=build_configurations())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_build_size_constraint(build_config, tmp_path):
    """
    任意のビルド設定に対して、生成されるBase_Imageのサイズは
    指定されたイメージタイプの制約以下でなければならない

    - MINIMAL: 5MB未満
    - STANDARD: 15MB未満
    - EXTENDED: 50MB未満
    """
    # Build the image
    image = build_base_image(build_config, output_dir=tmp_path)

    # Verify size constraint
    max_size = build_config.max_image_size
    assert image.size_bytes < max_size, (
        f"Image size {image.size_bytes} exceeds maximum {max_size} "
        f"for {build_config.image_type.value} image"
    )

    # Additional verification
    assert image.verify_size_constraint(), (
        f"Image size constraint verification failed for {build_config.image_type.value}"
    )


# Additional property tests for build configuration
@pytest.mark.property
@given(build_config=build_configurations())
def test_security_flags_presence(build_config):
    """
    Verify that security flags are present based on security level
    """
    cflags = build_config.security_cflags
    ldflags = build_config.security_ldflags

    # All security levels should have at least one flag
    assert len(cflags) > 0, "Security CFLAGS should not be empty"

    # Full security should have PIE
    if build_config.security_level == SecurityLevel.FULL:
        assert "-fPIE" in cflags
        assert "-pie" in ldflags

    # Standard and Full should have FORTIFY_SOURCE
    if build_config.security_level in [SecurityLevel.STANDARD, SecurityLevel.FULL]:
        assert any("FORTIFY_SOURCE" in flag for flag in cflags)


@pytest.mark.property
@given(image_type=st.sampled_from(ImageType))
def test_max_image_size_values(image_type):
    """
    Verify that max_image_size returns correct values for each image type
    """
    config = BuildConfig(image_type=image_type)
    max_size = config.max_image_size

    expected_sizes = {
        ImageType.MINIMAL: 5 * 1024 * 1024,
        ImageType.STANDARD: 15 * 1024 * 1024,
        ImageType.EXTENDED: 50 * 1024 * 1024,
    }

    assert max_size == expected_sizes[image_type], (
        f"Max image size mismatch for {image_type.value}"
    )


@pytest.mark.property
@given(
    arch=st.sampled_from(Architecture),
    security=st.sampled_from(SecurityLevel),
)
def test_build_config_immutability(arch, security):
    """
    Verify that BuildConfig properties are consistent
    """
    config = BuildConfig(architecture=arch, security_level=security)

    # Security flags should be deterministic
    flags1 = config.security_cflags
    flags2 = config.security_cflags
    assert flags1 == flags2, "Security flags should be deterministic"

    # Max image size should be deterministic
    size1 = config.max_image_size
    size2 = config.max_image_size
    assert size1 == size2, "Max image size should be deterministic"
