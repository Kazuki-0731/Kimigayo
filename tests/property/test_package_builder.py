"""
Property Tests for Package Builder

Tests package generation and architecture-specific binary processing.

Properties tested:
- Property 30: パッケージ互換性ラウンドトリップ (Package Compatibility Roundtrip) - 要件 8.4
- Property 18: アーキテクチャ固有バイナリ処理 (Architecture-Specific Binary Processing) - 要件 5.4
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, Verbosity

from src.pkg.package_builder import (
    PackageMetadata,
    PackageFormat,
    PackageBuilder,
)


@pytest.mark.property
class TestPackageCompatibilityRoundtrip:
    """
    Property 30: パッケージ互換性ラウンドトリップ

    任意のソフトウェアに対して、Build_Systemで生成されたパッケージは
    Package_Managerで正常に処理可能でなければならない

    Requirement: 8.4
    """

    def test_package_format_has_correct_extension(self):
        """
        Test: Package files have correct extension (.kpkg)
        """
        assert PackageFormat.EXTENSION == ".kpkg"

    def test_package_metadata_serialization(self):
        """
        Test: PackageMetadata can be serialized and deserialized
        """
        metadata = PackageMetadata(
            name="test-package",
            version="1.0.0",
            architecture="x86_64",
            dependencies=["dep1>=1.0", "dep2"],
            conflicts=["conflict1"],
            size=1024,
            checksum={"sha256": "abc123"},
            build_info={
                "timestamp": "2025-01-01T00:00:00",
                "build_hash": "def456"
            }
        )

        # Serialize to JSON
        json_str = metadata.to_json()

        # Deserialize
        restored = PackageMetadata.from_json(json_str)

        # Verify roundtrip
        assert restored.name == "test-package"
        assert restored.version == "1.0.0"
        assert restored.architecture == "x86_64"
        assert len(restored.dependencies) == 2
        assert len(restored.conflicts) == 1

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(
        name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
        version=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Nd', 'Pc'))),
        arch=st.sampled_from(["x86_64", "aarch64", "armv7", "any"])
    )
    def test_package_creation_and_extraction(self, name, version, arch):
        """
        Property Test: Packages can be created and extracted

        For any software, packages created by Build_System must be
        processable by Package_Manager.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create data directory
            data_dir = tmp_path / "data"
            data_dir.mkdir()
            (data_dir / "file1.txt").write_text("content1")
            (data_dir / "file2.txt").write_text("content2")

            # Create metadata
            metadata = PackageMetadata(
                name=name,
                version=version,
                architecture=arch,
                dependencies=[],
                conflicts=[],
                size=100,
                checksum={"sha256": ""},
                build_info={"timestamp": "2025-01-01T00:00:00"}
            )

            # Create package
            package_path = tmp_path / f"{name}.kpkg"
            PackageFormat.create_package(package_path, metadata, data_dir)

            # Verify package was created
            assert package_path.exists()

            # Extract package
            extract_dir = tmp_path / "extracted"
            extract_dir.mkdir()
            extracted_metadata = PackageFormat.extract_package(package_path, extract_dir)

            # Verify extraction
            assert extracted_metadata.name == name
            assert extracted_metadata.version == version
            assert extracted_metadata.architecture == arch

            # Verify data was extracted
            assert (extract_dir / PackageFormat.DATA_DIR / "file1.txt").exists()
            assert (extract_dir / PackageFormat.DATA_DIR / "file2.txt").exists()

    def test_package_builder_creates_valid_packages(self):
        """
        Test: PackageBuilder creates valid packages
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create data directory
            data_dir = tmp_path / "data"
            data_dir.mkdir()
            (data_dir / "bin").mkdir(parents=True)
            (data_dir / "bin" / "app").write_text("#!/bin/sh\necho hello")

            # Build package
            builder = PackageBuilder(architecture="x86_64")
            package_path = builder.build_package(
                name="test-app",
                version="1.0.0",
                data_dir=data_dir,
                output_dir=tmp_path,
                dependencies=["libc"],
                description="Test application"
            )

            # Verify package
            assert package_path.exists()
            assert PackageFormat.verify_package(package_path)

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(
        arch=st.sampled_from(["x86_64", "aarch64", "armv7", "any"]),
        num_files=st.integers(min_value=1, max_value=5)
    )
    def test_package_roundtrip_preserves_data(self, arch, num_files):
        """
        Property Test: Package roundtrip preserves all data

        For any package, creating and extracting must preserve all files.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create data directory with multiple files
            data_dir = tmp_path / "data"
            data_dir.mkdir()

            file_contents = {}
            for i in range(num_files):
                file_path = data_dir / f"file{i}.txt"
                content = f"content{i}" * 10
                file_path.write_text(content)
                file_contents[file_path.name] = content

            # Build package
            builder = PackageBuilder(architecture=arch)
            package_path = builder.build_package(
                name="roundtrip-test",
                version="1.0.0",
                data_dir=data_dir,
                output_dir=tmp_path
            )

            # Extract package
            extract_dir = tmp_path / "extracted"
            extract_dir.mkdir()
            PackageFormat.extract_package(package_path, extract_dir)

            # Verify all files were preserved
            extracted_data_dir = extract_dir / PackageFormat.DATA_DIR
            for filename, expected_content in file_contents.items():
                file_path = extracted_data_dir / filename
                assert file_path.exists(), f"File {filename} not found after roundtrip"
                actual_content = file_path.read_text()
                assert actual_content == expected_content, f"Content mismatch for {filename}"


@pytest.mark.property
class TestArchitectureSpecificBinaryProcessing:
    """
    Property 18: アーキテクチャ固有バイナリ処理

    任意のアーキテクチャのバイナリに対して、Package_Managerは
    正しい処理を実行しなければならない

    Requirement: 5.4
    """

    def test_architecture_validation(self):
        """
        Test: Architecture validation accepts valid architectures
        """
        assert PackageFormat.validate_architecture("x86_64") is True
        assert PackageFormat.validate_architecture("aarch64") is True
        assert PackageFormat.validate_architecture("armv7") is True
        assert PackageFormat.validate_architecture("any") is True
        assert PackageFormat.validate_architecture("invalid") is False

    def test_package_builder_validates_architecture(self):
        """
        Test: PackageBuilder validates architecture on initialization
        """
        # Valid architectures
        PackageBuilder("x86_64")
        PackageBuilder("aarch64")
        PackageBuilder("armv7")
        PackageBuilder("any")

        # Invalid architecture
        with pytest.raises(ValueError, match="Invalid architecture"):
            PackageBuilder("invalid_arch")

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(arch=st.sampled_from(["x86_64", "aarch64", "armv7", "any"]))
    def test_package_includes_architecture_in_metadata(self, arch):
        """
        Property Test: Packages include architecture in metadata

        For any architecture, packages must include architecture information
        in metadata for correct processing.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            data_dir = tmp_path / "data"
            data_dir.mkdir()
            (data_dir / "file.txt").write_text("content")

            builder = PackageBuilder(architecture=arch)
            package_path = builder.build_package(
                name="arch-test",
                version="1.0.0",
                data_dir=data_dir,
                output_dir=tmp_path
            )

            # Extract and verify architecture
            extract_dir = tmp_path / "extracted"
            extract_dir.mkdir()
            metadata = PackageFormat.extract_package(package_path, extract_dir)

            assert metadata.architecture == arch

    def test_architecture_binary_processing_elf_header(self):
        """
        Test: Architecture binary processing reads ELF headers

        PackageBuilder should be able to process ELF binaries and
        detect architecture.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create a fake ELF binary (x86_64)
            fake_elf = tmp_path / "binary"
            with open(fake_elf, 'wb') as f:
                # ELF header for x86_64
                f.write(b'\x7fELF')     # Magic number
                f.write(b'\x02')        # 64-bit
                f.write(b'\x01')        # Little endian
                f.write(b'\x01')        # ELF version
                f.write(b'\x00' * 9)    # Padding
                f.write(b'\x02\x00')    # Executable type
                f.write(b'\x3e\x00')    # x86-64 machine type

            builder = PackageBuilder(architecture="x86_64")

            # Should recognize as x86_64 binary
            is_compatible = builder.process_architecture_binary(fake_elf, "x86_64")
            assert is_compatible is True

    def test_non_elf_files_are_architecture_independent(self):
        """
        Test: Non-ELF files are treated as architecture-independent

        Text files, scripts, and other non-binary files should be
        compatible with any architecture.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create text file
            text_file = tmp_path / "script.sh"
            text_file.write_text("#!/bin/sh\necho hello")

            builder = PackageBuilder(architecture="x86_64")

            # Text files should be compatible with any architecture
            assert builder.process_architecture_binary(text_file, "x86_64") is True
            assert builder.process_architecture_binary(text_file, "aarch64") is True

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(
        build_arch=st.sampled_from(["x86_64", "aarch64", "armv7"]),
        target_arch=st.sampled_from(["x86_64", "aarch64", "armv7"])
    )
    def test_package_architecture_mismatch_detection(self, build_arch, target_arch):
        """
        Property Test: Architecture mismatch is detectable

        For any combination of build and target architectures,
        Package_Manager should be able to detect mismatches.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            data_dir = tmp_path / "data"
            data_dir.mkdir()
            (data_dir / "file.txt").write_text("content")

            # Build package for specific architecture
            builder = PackageBuilder(architecture=build_arch)
            package_path = builder.build_package(
                name="arch-mismatch-test",
                version="1.0.0",
                data_dir=data_dir,
                output_dir=tmp_path
            )

            # Extract metadata
            extract_dir = tmp_path / "extracted"
            extract_dir.mkdir()
            metadata = PackageFormat.extract_package(package_path, extract_dir)

            # Verify architecture is recorded correctly
            assert metadata.architecture == build_arch

            # Architecture mismatch should be detectable
            if build_arch != target_arch:
                # Metadata shows different architecture
                assert metadata.architecture != target_arch


@pytest.mark.property
class TestPackageChecksum:
    """Test package checksum calculation and verification"""

    def test_checksum_calculation(self):
        """
        Test: Package checksum is calculated correctly
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create test file
            test_file = tmp_path / "test.txt"
            test_file.write_text("test content")

            # Calculate checksum
            checksum = PackageFormat.calculate_checksum(test_file)

            # Verify checksum format (SHA-256 is 64 hex characters)
            assert len(checksum) == 64
            assert all(c in '0123456789abcdef' for c in checksum)

    def test_package_verification_with_checksum(self):
        """
        Test: Package verification with checksum
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            data_dir = tmp_path / "data"
            data_dir.mkdir()
            (data_dir / "file.txt").write_text("content")

            builder = PackageBuilder(architecture="x86_64")
            package_path = builder.build_package(
                name="checksum-test",
                version="1.0.0",
                data_dir=data_dir,
                output_dir=tmp_path
            )

            # Calculate checksum
            checksum = PackageFormat.calculate_checksum(package_path)

            # Verify with correct checksum
            assert PackageFormat.verify_package(package_path, checksum) is True

            # Verify with incorrect checksum
            wrong_checksum = "0" * 64
            assert PackageFormat.verify_package(package_path, wrong_checksum) is False

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(content=st.text(min_size=1, max_size=100))
    def test_identical_content_produces_identical_checksum(self, content):
        """
        Property Test: Identical content produces identical checksum

        For any content, creating the same file twice should produce
        the same checksum.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create first file
            file1 = tmp_path / "file1.txt"
            file1.write_text(content)
            checksum1 = PackageFormat.calculate_checksum(file1)

            # Create second file with same content
            file2 = tmp_path / "file2.txt"
            file2.write_text(content)
            checksum2 = PackageFormat.calculate_checksum(file2)

            # Checksums should be identical
            assert checksum1 == checksum2
