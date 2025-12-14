"""
Unit tests for image building
"""

import pytest
from pathlib import Path
from src.build.config import BuildConfig, Architecture, ImageType
from src.build.image import (
    build_base_image,
    create_build_metadata,
    BaseImage,
)


class TestBuildMetadata:
    """Unit tests for BuildMetadata"""

    def test_create_build_metadata(self):
        """Test build metadata creation"""
        config = BuildConfig()
        metadata = create_build_metadata(config)

        assert metadata.timestamp is not None
        assert metadata.build_hash is not None
        assert metadata.compiler == "gcc"
        assert metadata.architecture == config.architecture.value
        assert metadata.reproducible == config.reproducible

    def test_reproducible_build_metadata(self, monkeypatch):
        """Test reproducible build metadata"""
        monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
        config = BuildConfig(reproducible=True)
        metadata = create_build_metadata(config)

        assert metadata.timestamp == "1970-01-01T00:00:00Z"
        assert metadata.reproducible is True


class TestBaseImage:
    """Unit tests for BaseImage"""

    def test_build_base_image_creates_file(self, tmp_path):
        """Test that build_base_image creates an image file"""
        config = BuildConfig(image_type=ImageType.MINIMAL)
        image = build_base_image(config, output_dir=tmp_path)

        assert image.path.exists()
        assert image.size_bytes > 0
        assert image.checksum is not None

    def test_build_base_image_respects_size_constraint(self, tmp_path):
        """Test that built image respects size constraints"""
        config = BuildConfig(image_type=ImageType.MINIMAL)
        image = build_base_image(config, output_dir=tmp_path)

        assert image.size_bytes < config.max_image_size

    def test_verify_size_constraint(self, tmp_path):
        """Test size constraint verification"""
        config = BuildConfig(image_type=ImageType.MINIMAL)
        image = build_base_image(config, output_dir=tmp_path)

        assert image.verify_size_constraint() is True

    def test_verify_checksum(self, tmp_path):
        """Test checksum verification"""
        config = BuildConfig()
        image = build_base_image(config, output_dir=tmp_path)

        # Verify with correct checksum
        assert image.verify_checksum(image.checksum) is True

        # Verify with incorrect checksum
        assert image.verify_checksum("invalid_checksum") is False

    def test_different_architectures(self, tmp_path):
        """Test building for different architectures"""
        for arch in Architecture:
            config = BuildConfig(architecture=arch)
            image = build_base_image(config, output_dir=tmp_path)

            assert image.config.architecture == arch
            assert image.path.exists()

    def test_different_image_types(self, tmp_path):
        """Test building different image types"""
        for img_type in ImageType:
            config = BuildConfig(image_type=img_type)
            image = build_base_image(config, output_dir=tmp_path)

            assert image.config.image_type == img_type
            assert image.size_bytes < config.max_image_size

    def test_image_metadata_attached(self, tmp_path):
        """Test that metadata is attached to built image"""
        config = BuildConfig()
        image = build_base_image(config, output_dir=tmp_path)

        assert image.metadata is not None
        assert image.metadata.architecture == config.architecture.value
        assert image.metadata.reproducible == config.reproducible
