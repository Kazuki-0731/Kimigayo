"""
Image building utilities for Kimigayo OS
"""

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .config import BuildConfig


@dataclass
class BuildMetadata:
    """Metadata for a build"""
    timestamp: str
    build_hash: str
    compiler: str
    flags: Dict[str, list]
    architecture: str
    reproducible: bool


@dataclass
class BaseImage:
    """Represents a built Kimigayo OS base image"""
    path: Path
    size_bytes: int
    checksum: str
    config: BuildConfig
    metadata: Optional[BuildMetadata] = None

    @classmethod
    def from_path(cls, path: Path, config: BuildConfig) -> "BaseImage":
        """Create a BaseImage from a file path"""
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")

        size_bytes = path.stat().st_size
        checksum = cls._calculate_checksum(path)

        return cls(
            path=path,
            size_bytes=size_bytes,
            checksum=checksum,
            config=config,
        )

    @staticmethod
    def _calculate_checksum(path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def verify_size_constraint(self) -> bool:
        """Verify that image size meets the constraint"""
        return self.size_bytes < self.config.max_image_size

    def verify_checksum(self, expected_checksum: str) -> bool:
        """Verify image checksum"""
        return self.checksum == expected_checksum


def create_build_metadata(config: BuildConfig) -> BuildMetadata:
    """Create build metadata for reproducible builds"""
    timestamp = datetime.utcnow().isoformat() + "Z"

    # In reproducible builds, use SOURCE_DATE_EPOCH
    if config.reproducible and "SOURCE_DATE_EPOCH" in os.environ:
        timestamp = datetime.utcfromtimestamp(0).isoformat() + "Z"

    # Calculate build hash (simplified for now)
    build_input = f"{config.architecture.value}{config.security_level.value}{config.reproducible}"
    build_hash = hashlib.sha256(build_input.encode()).hexdigest()[:16]

    return BuildMetadata(
        timestamp=timestamp,
        build_hash=build_hash,
        compiler="gcc",  # Will be detected from environment
        flags={
            "CFLAGS": config.security_cflags,
            "LDFLAGS": config.security_ldflags,
        },
        architecture=config.architecture.value,
        reproducible=config.reproducible,
    )


def build_base_image(config: BuildConfig, output_dir: Optional[Path] = None) -> BaseImage:
    """
    Build a base image with the given configuration.

    This is a placeholder implementation for testing purposes.
    The actual build process will be implemented in later phases.
    """
    if output_dir is None:
        output_dir = Path("output")

    output_dir.mkdir(parents=True, exist_ok=True)

    # For now, create a mock image file
    image_name = f"kimigayo-{config.image_type.value}-{config.architecture.value}.img"
    image_path = output_dir / image_name

    # Create a mock image (will be replaced with actual build in Phase 2+)
    # For testing, create an image that respects size constraints
    mock_size = config.max_image_size - 1024 * 1024  # 1MB smaller than max

    with open(image_path, 'wb') as f:
        # Write a small amount of data
        f.write(b'\x00' * min(mock_size, 1024 * 1024))  # Cap at 1MB for mock

    metadata = create_build_metadata(config)
    image = BaseImage.from_path(image_path, config)
    image.metadata = metadata

    return image
