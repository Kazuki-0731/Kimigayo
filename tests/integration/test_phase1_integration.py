"""
Phase 1 Integration Tests for Kimigayo OS

Tests the integration of:
- Linux Kernel (hardened)
- musl libc
- BusyBox utilities
"""

import pytest
from pathlib import Path

from src.kernel.build import KernelConfig, build_kernel
from src.libc.musl import MuslConfig, LinkMode, build_musl
from src.utilities.busybox import BusyBoxConfig, ImageProfile, build_busybox
from src.toolchain.cross_compile import Architecture, setup_toolchain


@pytest.mark.integration
@pytest.mark.slow
def test_kernel_musl_busybox_integration_x86_64(tmp_path):
    """
    Test integration of kernel + musl + BusyBox for x86_64
    """
    # Build kernel
    kernel_config = KernelConfig(
        architecture="x86_64",
        enable_hardening=True,
        reproducible=True,
    )
    kernel_result = build_kernel(kernel_config, tmp_path / "kernel")

    # Build musl libc
    musl_config = MuslConfig(
        architecture="x86_64",
        link_mode=LinkMode.STATIC,
        enable_security_hardening=True,
    )
    musl_result = build_musl(musl_config, tmp_path / "musl")

    # Build BusyBox
    busybox_config = BusyBoxConfig(
        profile=ImageProfile.MINIMAL,
        enable_static=True,
        enable_security_hardening=True,
    )
    busybox_result = build_busybox(busybox_config, tmp_path / "busybox")

    # Verify all components built successfully
    assert kernel_result.kernel_image.exists()
    assert musl_result.static_lib.exists()
    assert busybox_result.binary_path.exists()

    # Verify security features are enabled in all components
    assert kernel_config.enable_hardening
    assert musl_config.enable_security_hardening
    assert busybox_config.enable_security_hardening

    # Calculate total system size
    total_size = (
        kernel_result.size_bytes +
        musl_result.size_bytes +
        busybox_result.size_bytes
    )

    # Minimal system should be under 2MB
    assert total_size < 2 * 1024 * 1024, (
        f"Minimal system too large: {total_size} bytes"
    )


@pytest.mark.integration
@pytest.mark.slow
def test_kernel_musl_busybox_integration_arm64(tmp_path):
    """
    Test integration of kernel + musl + BusyBox for ARM64
    """
    # Build kernel
    kernel_config = KernelConfig(
        architecture="arm64",
        enable_hardening=True,
        reproducible=True,
    )
    kernel_result = build_kernel(kernel_config, tmp_path / "kernel")

    # Build musl libc
    musl_config = MuslConfig(
        architecture="arm64",
        link_mode=LinkMode.STATIC,
        enable_security_hardening=True,
    )
    musl_result = build_musl(musl_config, tmp_path / "musl")

    # Build BusyBox
    busybox_config = BusyBoxConfig(
        profile=ImageProfile.MINIMAL,
        enable_static=True,
        enable_security_hardening=True,
    )
    busybox_result = build_busybox(busybox_config, tmp_path / "busybox")

    # Verify all components built successfully
    assert kernel_result.kernel_image.exists()
    assert musl_result.static_lib.exists()
    assert busybox_result.binary_path.exists()

    # Verify checksums are consistent
    assert len(kernel_result.checksum) == 64
    assert len(musl_result.checksum) == 64
    assert len(busybox_result.checksum) == 64


@pytest.mark.integration
def test_cross_architecture_build_consistency(tmp_path):
    """
    Test that builds are consistent across architectures
    """
    architectures = ["x86_64", "arm64"]
    results = {}

    for arch in architectures:
        # Build kernel
        kernel_config = KernelConfig(
            architecture=arch,
            enable_hardening=True,
            reproducible=True,
        )
        kernel_result = build_kernel(kernel_config, tmp_path / f"kernel_{arch}")

        # Build musl
        musl_config = MuslConfig(
            architecture=arch,
            link_mode=LinkMode.STATIC,
            enable_security_hardening=True,
        )
        musl_result = build_musl(musl_config, tmp_path / f"musl_{arch}")

        # Build BusyBox
        busybox_config = BusyBoxConfig(
            profile=ImageProfile.MINIMAL,
            enable_static=True,
            enable_security_hardening=True,
        )
        busybox_result = build_busybox(busybox_config, tmp_path / f"busybox_{arch}")

        results[arch] = {
            "kernel": kernel_result,
            "musl": musl_result,
            "busybox": busybox_result,
        }

    # Verify both architectures have same components
    for arch in architectures:
        assert results[arch]["kernel"].kernel_image.exists()
        assert results[arch]["musl"].static_lib.exists()
        assert results[arch]["busybox"].binary_path.exists()

    # BusyBox should have same utilities across architectures
    x86_64_utils = set(results["x86_64"]["busybox"].utilities)
    arm64_utils = set(results["arm64"]["busybox"].utilities)
    assert x86_64_utils == arm64_utils


@pytest.mark.integration
def test_minimal_system_components(tmp_path):
    """
    Test that minimal system has all required components
    """
    # Build minimal system
    kernel_config = KernelConfig(architecture="x86_64", reproducible=True)
    kernel_result = build_kernel(kernel_config, tmp_path / "kernel")

    musl_config = MuslConfig(architecture="x86_64", link_mode=LinkMode.STATIC)
    musl_result = build_musl(musl_config, tmp_path / "musl")

    busybox_config = BusyBoxConfig(profile=ImageProfile.MINIMAL)
    busybox_result = build_busybox(busybox_config, tmp_path / "busybox")

    # Verify essential utilities are present
    essential_utils = ["sh", "ls", "cp", "mv", "rm", "mkdir", "cat", "echo"]
    for util in essential_utils:
        assert util in busybox_result.utilities, f"Missing essential utility: {util}"

    # Verify musl headers are present
    assert (musl_result.include_dir / "stdio.h").exists()
    assert (musl_result.include_dir / "stdlib.h").exists()


@pytest.mark.integration
def test_security_hardening_consistency(tmp_path):
    """
    Test that security hardening is consistent across all components
    """
    # Build with security hardening enabled
    kernel_config = KernelConfig(
        architecture="x86_64",
        enable_hardening=True,
    )
    kernel_result = build_kernel(kernel_config, tmp_path / "kernel")

    musl_config = MuslConfig(
        architecture="x86_64",
        enable_security_hardening=True,
    )
    musl_result = build_musl(musl_config, tmp_path / "musl")

    busybox_config = BusyBoxConfig(
        enable_security_hardening=True,
    )
    busybox_result = build_busybox(busybox_config, tmp_path / "busybox")

    # Verify security features are enabled
    from src.kernel.build import KernelBuilder
    from src.libc.musl import MuslBuilder
    from src.utilities.busybox import BusyBoxBuilder

    # Check kernel security
    kernel_builder = KernelBuilder(kernel_config, tmp_path / "kernel")
    kernel_builder.configure_kernel()
    security_features = kernel_builder.get_enabled_security_features()
    assert len(security_features) > 0

    # Check musl security
    musl_builder = MuslBuilder(musl_config, tmp_path / "musl")
    assert musl_builder.verify_security_features()

    # Check BusyBox security
    busybox_cflags = busybox_config.get_cflags()
    assert "-fPIE" in busybox_cflags
    assert "-fstack-protector-strong" in busybox_cflags


@pytest.mark.integration
def test_reproducible_full_system_build(tmp_path):
    """
    Test that full system builds are reproducible
    """
    def build_full_system(output_dir):
        """Build a complete minimal system"""
        kernel_config = KernelConfig(
            architecture="x86_64",
            reproducible=True,
        )
        kernel_result = build_kernel(kernel_config, output_dir / "kernel")

        musl_config = MuslConfig(
            architecture="x86_64",
            link_mode=LinkMode.STATIC,
        )
        musl_result = build_musl(musl_config, output_dir / "musl")

        busybox_config = BusyBoxConfig(
            profile=ImageProfile.MINIMAL,
            enable_static=True,
        )
        busybox_result = build_busybox(busybox_config, output_dir / "busybox")

        return kernel_result, musl_result, busybox_result

    # Build twice
    build1 = build_full_system(tmp_path / "build1")
    build2 = build_full_system(tmp_path / "build2")

    # Verify checksums are identical
    assert build1[0].checksum == build2[0].checksum, "Kernel builds differ"
    assert build1[1].checksum == build2[1].checksum, "musl builds differ"
    assert build1[2].checksum == build2[2].checksum, "BusyBox builds differ"


@pytest.mark.integration
def test_toolchain_integration(tmp_path):
    """
    Test that toolchain integrates with all components
    """
    arch = Architecture.X86_64

    # Setup toolchain
    compiler = setup_toolchain(arch, tmp_path / "toolchain")

    # Get environment
    env = compiler.config.get_environment()

    # Verify toolchain variables are set
    assert "CC" in env
    assert "CFLAGS" in env
    assert "LDFLAGS" in env

    # Verify security flags are in environment
    assert "-fPIE" in env["CFLAGS"]
    assert "-Wl,-z,relro" in env["LDFLAGS"]


@pytest.mark.integration
@pytest.mark.parametrize("profile", [
    ImageProfile.MINIMAL,
    ImageProfile.STANDARD,
    ImageProfile.EXTENDED,
])
def test_different_profiles_integration(profile, tmp_path):
    """
    Test integration with different BusyBox profiles
    """
    # Build with different profile
    kernel_config = KernelConfig(architecture="x86_64", reproducible=True)
    kernel_result = build_kernel(kernel_config, tmp_path / "kernel")

    musl_config = MuslConfig(architecture="x86_64", link_mode=LinkMode.STATIC)
    musl_result = build_musl(musl_config, tmp_path / "musl")

    busybox_config = BusyBoxConfig(profile=profile)
    busybox_result = build_busybox(busybox_config, tmp_path / "busybox")

    # Verify all components work together
    assert kernel_result.kernel_image.exists()
    assert musl_result.static_lib.exists()
    assert busybox_result.binary_path.exists()

    # Verify essential utilities are present in all profiles
    assert busybox_result.config.verify_essential_utilities()


@pytest.mark.integration
def test_static_linking_full_system(tmp_path):
    """
    Test that full system can be built with static linking
    """
    # Build everything with static linking
    kernel_config = KernelConfig(architecture="x86_64")
    kernel_result = build_kernel(kernel_config, tmp_path / "kernel")

    musl_config = MuslConfig(
        architecture="x86_64",
        link_mode=LinkMode.STATIC,
    )
    musl_result = build_musl(musl_config, tmp_path / "musl")

    busybox_config = BusyBoxConfig(
        profile=ImageProfile.MINIMAL,
        enable_static=True,
    )
    busybox_result = build_busybox(busybox_config, tmp_path / "busybox")

    # Verify static library exists
    assert musl_result.static_lib is not None
    assert musl_result.static_lib.exists()
    assert musl_result.dynamic_lib is None

    # Verify BusyBox linker flags include -static
    ldflags = busybox_config.get_ldflags()
    assert "-static" in ldflags
