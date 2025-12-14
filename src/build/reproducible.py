"""
Reproducible build utilities for Kimigayo OS
"""

import os
import hashlib
import json
import platform
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .config import BuildConfig
from .image import BaseImage, build_base_image


@dataclass
class BuildEnvironment:
    """Records the build environment for reproducibility"""
    hostname: str
    platform_system: str
    platform_release: str
    platform_machine: str
    python_version: str
    source_date_epoch: str
    locale: str
    timezone: str

    @classmethod
    def capture(cls) -> "BuildEnvironment":
        """Capture current build environment"""
        return cls(
            hostname=platform.node(),
            platform_system=platform.system(),
            platform_release=platform.release(),
            platform_machine=platform.machine(),
            python_version=platform.python_version(),
            source_date_epoch=os.environ.get('SOURCE_DATE_EPOCH', '0'),
            locale=os.environ.get('LC_ALL', 'C'),
            timezone=os.environ.get('TZ', 'UTC'),
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class BuildDependency:
    """Records a build dependency"""
    name: str
    version: str
    source: str  # e.g., "system", "pip", "apk"

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class BuildMetadata:
    """Complete build metadata for reproducibility verification"""
    build_id: str
    timestamp: str
    source_hash: str
    output_hash: str
    config: Dict
    environment: BuildEnvironment
    dependencies: List[BuildDependency]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "build_id": self.build_id,
            "timestamp": self.timestamp,
            "source_hash": self.source_hash,
            "output_hash": self.output_hash,
            "config": self.config,
            "environment": self.environment.to_dict(),
            "dependencies": [dep.to_dict() for dep in self.dependencies],
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict) -> "BuildMetadata":
        """Create from dictionary"""
        return cls(
            build_id=data["build_id"],
            timestamp=data["timestamp"],
            source_hash=data["source_hash"],
            output_hash=data["output_hash"],
            config=data["config"],
            environment=BuildEnvironment(**data["environment"]),
            dependencies=[BuildDependency(**dep) for dep in data["dependencies"]],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "BuildMetadata":
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class BuildArtifact:
    """Represents a build artifact with verification info"""
    image: BaseImage
    build_number: int
    environment_id: str
    metadata: Optional[BuildMetadata] = None


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
) -> Tuple[bool, List[str]]:
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


class ReproducibleBuilder:
    """
    Manages reproducible builds with full metadata tracking.

    Requirements:
    - 6.1: Bit-identical output guarantee
    - 6.2: Environment-independent builds
    - 6.3: Build dependency recording
    """

    def __init__(self, config: BuildConfig):
        """
        Initialize reproducible builder.

        Args:
            config: Build configuration (must have reproducible=True)
        """
        if not config.reproducible:
            raise ValueError("Config must have reproducible=True")
        self.config = config
        self.dependencies: List[BuildDependency] = []

    def add_dependency(self, name: str, version: str, source: str = "system"):
        """
        Record a build dependency.

        Args:
            name: Dependency name
            version: Dependency version
            source: Dependency source (system, pip, apk, etc.)
        """
        dep = BuildDependency(name=name, version=version, source=source)
        self.dependencies.append(dep)

    def record_dependencies(self):
        """
        Automatically record common build dependencies.
        """
        # Record Python version
        self.add_dependency("python", platform.python_version(), "system")

        # Record compiler if available
        import subprocess
        try:
            gcc_version = subprocess.check_output(
                ["gcc", "--version"],
                stderr=subprocess.DEVNULL,
                text=True
            ).split('\n')[0]
            self.add_dependency("gcc", gcc_version.split()[-1], "system")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        try:
            clang_version = subprocess.check_output(
                ["clang", "--version"],
                stderr=subprocess.DEVNULL,
                text=True
            ).split('\n')[0]
            self.add_dependency("clang", clang_version.split()[-1], "system")
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    def build(
        self,
        source_dir: Path,
        output_dir: Path,
        build_id: Optional[str] = None
    ) -> BuildArtifact:
        """
        Perform reproducible build with full metadata.

        Args:
            source_dir: Source code directory
            output_dir: Output directory for artifacts
            build_id: Optional build identifier

        Returns:
            BuildArtifact with metadata
        """
        # Generate build ID if not provided
        if build_id is None:
            build_id = hashlib.sha256(
                f"{source_dir}{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16]

        # Calculate source hash
        source_hash = self._calculate_directory_hash(source_dir)

        # Capture build environment
        environment = BuildEnvironment.capture()

        # Record dependencies
        self.record_dependencies()

        # Perform build
        artifact = perform_reproducible_build(
            config=self.config,
            output_dir=output_dir,
            build_number=1,
            environment_id=build_id
        )

        # Create metadata
        # Convert config to dict, handling enums
        config_dict = {}
        for key, value in asdict(self.config).items():
            if hasattr(value, 'value'):  # Enum
                config_dict[key] = value.value
            else:
                config_dict[key] = value

        metadata = BuildMetadata(
            build_id=build_id,
            timestamp=datetime.utcnow().isoformat(),
            source_hash=source_hash,
            output_hash=artifact.image.checksum,
            config=config_dict,
            environment=environment,
            dependencies=self.dependencies,
        )

        artifact.metadata = metadata

        # Save metadata
        metadata_path = output_dir / "build-metadata.json"
        metadata_path.write_text(metadata.to_json())

        return artifact

    def _calculate_directory_hash(self, directory: Path) -> str:
        """
        Calculate deterministic hash of a directory.

        Args:
            directory: Directory to hash

        Returns:
            SHA-256 hash of directory contents
        """
        sha256 = hashlib.sha256()

        # Sort files for deterministic ordering
        files = sorted(directory.rglob('*'))

        for file_path in files:
            if file_path.is_file():
                # Add relative path
                rel_path = file_path.relative_to(directory)
                sha256.update(str(rel_path).encode())

                # Add file content
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256.update(chunk)

        return sha256.hexdigest()


class BuildVerifier:
    """
    Verifies build reproducibility and metadata.

    Requirements:
    - 6.4: Cryptographic verification of build reproducibility
    - 6.5: Build metadata inclusion
    """

    @staticmethod
    def verify_build(
        artifact1: BuildArtifact,
        artifact2: BuildArtifact
    ) -> bool:
        """
        Verify two builds are bit-identical.

        Args:
            artifact1: First build artifact
            artifact2: Second build artifact

        Returns:
            True if builds are identical
        """
        return artifact1.image.checksum == artifact2.image.checksum

    @staticmethod
    def verify_metadata(metadata_path: Path) -> BuildMetadata:
        """
        Load and verify build metadata.

        Args:
            metadata_path: Path to metadata JSON file

        Returns:
            Validated BuildMetadata

        Raises:
            ValueError: If metadata is invalid
        """
        if not metadata_path.exists():
            raise ValueError(f"Metadata file not found: {metadata_path}")

        metadata_json = metadata_path.read_text()
        metadata = BuildMetadata.from_json(metadata_json)

        return metadata

    @staticmethod
    def verify_output_hash(
        output_path: Path,
        expected_hash: str
    ) -> bool:
        """
        Verify build output hash matches expected value.

        Args:
            output_path: Path to build output
            expected_hash: Expected SHA-256 hash

        Returns:
            True if hashes match
        """
        actual_hash = calculate_build_checksum(output_path)
        return actual_hash == expected_hash

    @staticmethod
    def compare_builds(
        build_dir1: Path,
        build_dir2: Path
    ) -> Dict[str, bool]:
        """
        Compare two build directories for reproducibility.

        Args:
            build_dir1: First build directory
            build_dir2: Second build directory

        Returns:
            Dict with comparison results
        """
        results = {
            "metadata_exists": False,
            "metadata_identical": False,
            "output_hash_match": False,
            "environment_identical": False,
        }

        # Check metadata exists
        metadata1_path = build_dir1 / "build-metadata.json"
        metadata2_path = build_dir2 / "build-metadata.json"

        if metadata1_path.exists() and metadata2_path.exists():
            results["metadata_exists"] = True

            metadata1 = BuildVerifier.verify_metadata(metadata1_path)
            metadata2 = BuildVerifier.verify_metadata(metadata2_path)

            # Compare output hashes
            if metadata1.output_hash == metadata2.output_hash:
                results["output_hash_match"] = True

            # Compare environments
            if metadata1.environment == metadata2.environment:
                results["environment_identical"] = True

            # Compare full metadata (excluding timestamp and build_id)
            meta1_dict = metadata1.to_dict()
            meta2_dict = metadata2.to_dict()
            meta1_dict.pop("timestamp", None)
            meta1_dict.pop("build_id", None)
            meta2_dict.pop("timestamp", None)
            meta2_dict.pop("build_id", None)

            if meta1_dict == meta2_dict:
                results["metadata_identical"] = True

        return results
