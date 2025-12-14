"""
Package Builder Module

Builds packages compatible with Package_Manager (isn).
Handles architecture-specific binaries and package format.

Requirements:
- 8.4: Package_Manager compatible package generation
- 5.4: Architecture-specific binary processing
"""

import tarfile
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PackageMetadata:
    """
    Package metadata structure.

    Compatible with Package_Manager format.
    """
    name: str
    version: str
    architecture: str
    dependencies: List[str]
    conflicts: List[str]
    size: int
    checksum: Dict[str, str]
    build_info: Dict[str, any]
    description: Optional[str] = None
    maintainer: Optional[str] = None
    license: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict) -> "PackageMetadata":
        """Create from dictionary"""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "PackageMetadata":
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))


class PackageFormat:
    """
    Package format handler.

    Kimigayo OS package format (.kpkg):
    - Compressed tarball (tar.gz)
    - Contains metadata.json
    - Contains data/ directory with files
    - Compatible with Package_Manager
    """

    METADATA_FILE = "metadata.json"
    DATA_DIR = "data"
    EXTENSION = ".kpkg"

    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def calculate_directory_size(directory: Path) -> int:
        """Calculate total size of a directory"""
        total_size = 0
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    @staticmethod
    def validate_architecture(architecture: str) -> bool:
        """
        Validate architecture string.

        Supported architectures:
        - x86_64 (AMD64)
        - aarch64 (ARM64)
        - armv7
        - any (architecture-independent)
        """
        valid_archs = ["x86_64", "aarch64", "armv7", "any"]
        return architecture in valid_archs

    @classmethod
    def create_package(
        cls,
        output_path: Path,
        metadata: PackageMetadata,
        data_dir: Path
    ) -> Path:
        """
        Create a package file.

        Args:
            output_path: Output package file path
            metadata: Package metadata
            data_dir: Directory containing package files

        Returns:
            Path to created package file

        Raises:
            ValueError: If architecture is invalid
        """
        if not cls.validate_architecture(metadata.architecture):
            raise ValueError(f"Invalid architecture: {metadata.architecture}")

        if not data_dir.exists():
            raise ValueError(f"Data directory not found: {data_dir}")

        # Ensure output has correct extension
        if not output_path.name.endswith(cls.EXTENSION):
            output_path = output_path.with_suffix(cls.EXTENSION)

        # Create temporary directory for package contents
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Write metadata
            metadata_path = tmp_path / cls.METADATA_FILE
            metadata_path.write_text(metadata.to_json())

            # Copy data directory
            import shutil
            data_dest = tmp_path / cls.DATA_DIR
            shutil.copytree(data_dir, data_dest)

            # Create tarball
            with tarfile.open(output_path, 'w:gz') as tar:
                tar.add(metadata_path, arcname=cls.METADATA_FILE)
                tar.add(data_dest, arcname=cls.DATA_DIR)

        return output_path

    @classmethod
    def extract_package(
        cls,
        package_path: Path,
        extract_dir: Path
    ) -> PackageMetadata:
        """
        Extract a package file.

        Args:
            package_path: Package file path
            extract_dir: Directory to extract to

        Returns:
            Package metadata

        Raises:
            ValueError: If package is invalid
        """
        if not package_path.exists():
            raise ValueError(f"Package not found: {package_path}")

        # Extract tarball
        with tarfile.open(package_path, 'r:gz') as tar:
            tar.extractall(extract_dir)

        # Read metadata
        metadata_path = extract_dir / cls.METADATA_FILE
        if not metadata_path.exists():
            raise ValueError(f"Invalid package: missing {cls.METADATA_FILE}")

        metadata_json = metadata_path.read_text()
        metadata = PackageMetadata.from_json(metadata_json)

        return metadata

    @classmethod
    def verify_package(
        cls,
        package_path: Path,
        expected_checksum: Optional[str] = None
    ) -> bool:
        """
        Verify package integrity.

        Args:
            package_path: Package file path
            expected_checksum: Expected SHA-256 checksum (optional)

        Returns:
            True if package is valid
        """
        if not package_path.exists():
            return False

        # Verify checksum if provided
        if expected_checksum:
            actual_checksum = cls.calculate_checksum(package_path)
            if actual_checksum != expected_checksum:
                return False

        # Verify tarball can be opened
        try:
            with tarfile.open(package_path, 'r:gz') as tar:
                # Check for required files
                members = tar.getnames()
                if cls.METADATA_FILE not in members:
                    return False
                if cls.DATA_DIR not in members:
                    return False
            return True
        except Exception:
            return False


class PackageBuilder:
    """
    Package builder for Kimigayo OS.

    Builds packages compatible with Package_Manager (isn).
    Handles architecture-specific binaries.

    Requirements:
    - 8.4: Package_Manager compatible package generation
    - 5.4: Architecture-specific binary processing
    """

    def __init__(self, architecture: str = "x86_64"):
        """
        Initialize package builder.

        Args:
            architecture: Target architecture (x86_64, aarch64, armv7, any)
        """
        if not PackageFormat.validate_architecture(architecture):
            raise ValueError(f"Invalid architecture: {architecture}")

        self.architecture = architecture

    def build_package(
        self,
        name: str,
        version: str,
        data_dir: Path,
        output_dir: Path,
        dependencies: Optional[List[str]] = None,
        conflicts: Optional[List[str]] = None,
        description: Optional[str] = None,
        maintainer: Optional[str] = None,
        license: Optional[str] = None,
        build_hash: Optional[str] = None
    ) -> Path:
        """
        Build a package.

        Args:
            name: Package name
            version: Package version
            data_dir: Directory containing package files
            output_dir: Output directory
            dependencies: List of dependencies
            conflicts: List of conflicting packages
            description: Package description
            maintainer: Package maintainer
            license: Package license
            build_hash: Build hash for reproducibility

        Returns:
            Path to created package file
        """
        if not data_dir.exists():
            raise ValueError(f"Data directory not found: {data_dir}")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Calculate size
        size = PackageFormat.calculate_directory_size(data_dir)

        # Build metadata
        metadata = PackageMetadata(
            name=name,
            version=version,
            architecture=self.architecture,
            dependencies=dependencies or [],
            conflicts=conflicts or [],
            size=size,
            checksum={
                "sha256": "",  # Will be calculated after package creation
            },
            build_info={
                "timestamp": datetime.utcnow().isoformat(),
                "build_hash": build_hash or "",
                "architecture": self.architecture,
            },
            description=description,
            maintainer=maintainer,
            license=license
        )

        # Create package
        package_name = f"{name}-{version}-{self.architecture}{PackageFormat.EXTENSION}"
        package_path = output_dir / package_name

        PackageFormat.create_package(
            output_path=package_path,
            metadata=metadata,
            data_dir=data_dir
        )

        # Calculate and update checksum
        checksum = PackageFormat.calculate_checksum(package_path)
        metadata.checksum["sha256"] = checksum

        # Recreate package with updated metadata
        PackageFormat.create_package(
            output_path=package_path,
            metadata=metadata,
            data_dir=data_dir
        )

        return package_path

    def process_architecture_binary(
        self,
        binary_path: Path,
        target_arch: Optional[str] = None
    ) -> bool:
        """
        Process architecture-specific binary.

        Validates that binary is compatible with target architecture.

        Args:
            binary_path: Path to binary file
            target_arch: Target architecture (default: self.architecture)

        Returns:
            True if binary is compatible

        Requirement: 5.4 (Architecture-specific binary processing)
        """
        if target_arch is None:
            target_arch = self.architecture

        if not binary_path.exists():
            return False

        # Read ELF header to determine architecture
        try:
            with open(binary_path, 'rb') as f:
                # ELF magic number
                magic = f.read(4)
                if magic != b'\x7fELF':
                    # Not an ELF binary - assume compatible
                    return True

                # ELF class (32/64 bit)
                f.seek(4)
                elf_class = f.read(1)[0]

                # Machine type
                f.seek(18)
                machine = int.from_bytes(f.read(2), byteorder='little')

                # Validate architecture compatibility
                arch_mappings = {
                    "x86_64": (2, 0x3E),    # 64-bit, x86-64
                    "aarch64": (2, 0xB7),   # 64-bit, AArch64
                    "armv7": (1, 0x28),     # 32-bit, ARM
                }

                if target_arch in arch_mappings:
                    expected_class, expected_machine = arch_mappings[target_arch]
                    return elf_class == expected_class and machine == expected_machine
                elif target_arch == "any":
                    return True
                else:
                    return False

        except Exception:
            # If we can't read the binary, assume incompatible
            return False
