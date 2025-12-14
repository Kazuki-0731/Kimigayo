"""
Reproducible build utilities for Kimigayo OS
"""

import os
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .config import BuildConfig
from .image import BaseImage, build_base_image


@dataclass
class BuildArtifact:
    """Represents a build artifact with verification info"""
    image: BaseImage
    build_number: int
    environment_id: str


def calculate_build_checksum(image_path: Path) -> str:
    """
    Calculate deterministic checksum for a build artifact
    """
    sha256 = hashlib.sha256()
    with open(image_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def setup_reproducible_environment() -> dict:
    """
    Set up environment variables for reproducible builds
    """
    env = os.environ.copy()

    # Set SOURCE_DATE_EPOCH for reproducible timestamps
    env['SOURCE_DATE_EPOCH'] = '0'

    # Set LC_ALL for reproducible sorting
    env['LC_ALL'] = 'C'

    # Set TZ for reproducible timezone
    env['TZ'] = 'UTC'

    return env


def verify_reproducible_build(build1: BaseImage, build2: BaseImage) -> bool:
    """
    Verify that two builds are bit-identical
    """
    return build1.checksum == build2.checksum


def perform_reproducible_build(
    config: BuildConfig,
    output_dir: Path,
    build_number: int = 1,
    environment_id: str = "default"
) -> BuildArtifact:
    """
    Perform a reproducible build with proper environment setup

    Args:
        config: Build configuration
        output_dir: Output directory for build artifacts
        build_number: Build iteration number
        environment_id: Identifier for the build environment

    Returns:
        BuildArtifact with the built image and metadata
    """
    # Ensure reproducible build is enabled
    if not config.reproducible:
        raise ValueError("Reproducible build must be enabled in config")

    # Set up reproducible environment
    old_env = os.environ.copy()
    new_env = setup_reproducible_environment()
    os.environ.update(new_env)

    try:
        # Perform the build
        image = build_base_image(config, output_dir=output_dir)

        # Create build artifact
        artifact = BuildArtifact(
            image=image,
            build_number=build_number,
            environment_id=environment_id,
        )

        return artifact
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(old_env)


def verify_cross_environment_reproducibility(
    config: BuildConfig,
    output_dir: Path,
    num_builds: int = 2
) -> tuple[bool, list[str]]:
    """
    Verify that builds are reproducible across multiple builds

    Args:
        config: Build configuration (must have reproducible=True)
        output_dir: Output directory for build artifacts
        num_builds: Number of builds to perform and compare

    Returns:
        Tuple of (is_reproducible, list_of_checksums)
    """
    if not config.reproducible:
        raise ValueError("Config must have reproducible=True")

    checksums = []

    for i in range(num_builds):
        build_dir = output_dir / f"build_{i}"
        build_dir.mkdir(parents=True, exist_ok=True)

        artifact = perform_reproducible_build(
            config=config,
            output_dir=build_dir,
            build_number=i + 1,
            environment_id=f"env_{i}"
        )

        checksums.append(artifact.image.checksum)

    # All checksums should be identical
    is_reproducible = len(set(checksums)) == 1

    return is_reproducible, checksums
