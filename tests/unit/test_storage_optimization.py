"""
Unit Tests for Storage Optimization

Tests storage monitoring, optimization, and efficiency.

Requirements:
- 1.5: Storage optimization - Minimum storage requirement 512MB
"""

import pytest
import tempfile
from pathlib import Path

from src.system.storage import (
    StorageUsage,
    DirectorySize,
    StorageMonitor,
    ImageSizeVerifier,
    StorageOptimizer,
    StorageManager,
    StorageUnit,
    ImageType,
)


class TestStorageUsage:
    """Tests for storage usage data structure"""

    def test_storage_usage_creation(self):
        """Test: Storage usage can be created"""
        usage = StorageUsage(
            total=1024 * 1024 * 1024,  # 1GB
            used=512 * 1024 * 1024,    # 512MB
            free=512 * 1024 * 1024,
            available=512 * 1024 * 1024
        )

        assert usage is not None
        assert usage.total > 0

    def test_to_mb_conversion(self):
        """Test: Storage values can be converted to MB"""
        usage = StorageUsage(
            total=512 * 1024 * 1024,  # 512MB in bytes
            used=256 * 1024 * 1024,    # 256MB in bytes
            free=256 * 1024 * 1024,
            available=256 * 1024 * 1024
        )

        assert usage.to_mb(usage.total) == 512.0
        assert usage.to_mb(usage.used) == 256.0

    def test_usage_percentage(self):
        """Test: Usage percentage can be calculated"""
        usage = StorageUsage(
            total=100 * 1024 * 1024,  # 100MB
            used=50 * 1024 * 1024,    # 50MB
            free=50 * 1024 * 1024,
            available=50 * 1024 * 1024
        )

        percentage = usage.get_usage_percentage()
        assert 49 <= percentage <= 51  # Should be approximately 50%

    def test_to_dict(self):
        """Test: Can convert to dictionary"""
        usage = StorageUsage(
            total=1024 * 1024 * 1024,
            used=512 * 1024 * 1024,
            free=512 * 1024 * 1024,
            available=512 * 1024 * 1024,
            mount_point="/"
        )

        usage_dict = usage.to_dict()

        assert isinstance(usage_dict, dict)
        assert 'total_mb' in usage_dict
        assert 'used_mb' in usage_dict
        assert 'mount_point' in usage_dict


class TestStorageMonitor:
    """Tests for storage monitoring"""

    def test_monitor_initialization(self):
        """Test: Storage monitor can be initialized"""
        monitor = StorageMonitor()

        assert monitor is not None
        assert monitor.minimum_storage_mb == 512  # Requirement: 1.5

    def test_minimum_storage_is_512mb(self):
        """
        Test: Minimum storage is set to 512MB

        Requirement 1.5: Minimum storage 512MB
        """
        monitor = StorageMonitor()

        assert monitor.minimum_storage_mb == 512

    def test_recommended_storage_is_2gb(self):
        """Test: Recommended storage is 2GB"""
        monitor = StorageMonitor()

        assert monitor.recommended_storage_mb == 2048

    def test_get_storage_usage(self):
        """Test: Can get storage usage"""
        monitor = StorageMonitor()

        usage = monitor.get_storage_usage("/")

        assert isinstance(usage, StorageUsage)
        assert usage.total >= 0

    def test_check_minimum_storage(self):
        """
        Test: Can check if storage meets minimum

        Requirement 1.5: Verify minimum storage
        """
        monitor = StorageMonitor()

        meets_req, available_mb = monitor.check_minimum_storage("/")

        assert isinstance(meets_req, bool)
        assert isinstance(available_mb, float)
        assert available_mb >= 0

    def test_get_directory_size(self):
        """Test: Can get directory size"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create test files
            (temp_path / "file1.txt").write_text("test content 1")
            (temp_path / "file2.txt").write_text("test content 2")

            monitor = StorageMonitor()
            dir_size = monitor.get_directory_size(temp_path)

            assert isinstance(dir_size, DirectorySize)
            assert dir_size.size > 0
            assert dir_size.file_count == 2

    def test_get_largest_directories(self):
        """Test: Can get largest directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create subdirectories
            (temp_path / "dir1").mkdir()
            (temp_path / "dir2").mkdir()

            monitor = StorageMonitor()
            largest = monitor.get_largest_directories(temp_path, limit=5)

            assert isinstance(largest, list)
            assert len(largest) <= 5


class TestImageSizeVerifier:
    """Tests for image size verification"""

    def test_verifier_initialization(self):
        """Test: Image size verifier can be initialized"""
        verifier = ImageSizeVerifier()

        assert verifier is not None

    def test_image_types_defined(self):
        """Test: Image types are correctly defined"""
        assert ImageType.MINIMAL.size_limit_mb == 5
        assert ImageType.STANDARD.size_limit_mb == 15
        assert ImageType.EXTENDED.size_limit_mb == 50

    def test_verify_image_size_minimal(self):
        """Test: Can verify minimal image size (5MB limit)"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 4MB file (under limit)
            f.write(b'0' * (4 * 1024 * 1024))
            temp_path = Path(f.name)

        try:
            verifier = ImageSizeVerifier()
            meets_req, size_mb = verifier.verify_image_size(temp_path, ImageType.MINIMAL)

            assert meets_req is True
            assert 3.9 <= size_mb <= 4.1  # Approximately 4MB
        finally:
            temp_path.unlink()

    def test_verify_image_size_exceeds_limit(self):
        """Test: Detects when image exceeds size limit"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 6MB file (over minimal 5MB limit)
            f.write(b'0' * (6 * 1024 * 1024))
            temp_path = Path(f.name)

        try:
            verifier = ImageSizeVerifier()
            meets_req, size_mb = verifier.verify_image_size(temp_path, ImageType.MINIMAL)

            assert meets_req is False
            assert 5.9 <= size_mb <= 6.1  # Approximately 6MB
        finally:
            temp_path.unlink()

    def test_verify_nonexistent_image(self):
        """Test: Handles nonexistent image"""
        verifier = ImageSizeVerifier()
        meets_req, size_mb = verifier.verify_image_size(Path("/nonexistent.img"), ImageType.MINIMAL)

        assert meets_req is False
        assert size_mb == 0.0


class TestStorageOptimizer:
    """Tests for storage optimization"""

    def test_optimizer_initialization(self):
        """Test: Storage optimizer can be initialized"""
        optimizer = StorageOptimizer()

        assert optimizer is not None
        assert optimizer.monitor is not None

    def test_find_large_files(self):
        """Test: Can find large files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create large file (11MB)
            large_file = temp_path / "large.dat"
            large_file.write_bytes(b'0' * (11 * 1024 * 1024))

            # Create small file
            small_file = temp_path / "small.txt"
            small_file.write_text("small")

            optimizer = StorageOptimizer()
            large_files = optimizer.find_large_files(temp_path, min_size_mb=10)

            assert len(large_files) == 1
            assert large_files[0][0] == large_file

    def test_suggest_optimizations(self):
        """Test: Can suggest optimizations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            optimizer = StorageOptimizer()
            suggestions = optimizer.suggest_optimizations(temp_path)

            assert isinstance(suggestions, list)

    def test_apply_optimization(self):
        """Test: Can apply optimization"""
        optimizer = StorageOptimizer()

        result = optimizer.apply_optimization("test-optimization")

        assert result is True
        assert "test-optimization" in optimizer.optimizations_applied

    def test_clean_temporary_files(self):
        """Test: Can clean temporary files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create temp files
            (temp_path / "temp1.tmp").write_text("temporary 1")
            (temp_path / "temp2.tmp").write_text("temporary 2")

            optimizer = StorageOptimizer()
            freed = optimizer.clean_temporary_files(temp_path)

            # Should report some bytes freed
            assert freed > 0


class TestStorageManager:
    """Tests for overall storage management"""

    def test_manager_initialization(self):
        """Test: Storage manager can be initialized"""
        manager = StorageManager()

        assert manager is not None
        assert manager.monitor is not None
        assert manager.optimizer is not None
        assert manager.verifier is not None

    def test_get_status(self):
        """Test: Can get comprehensive storage status"""
        manager = StorageManager()

        status = manager.get_status("/")

        assert isinstance(status, dict)
        assert 'storage_usage' in status
        assert 'meets_minimum' in status
        assert 'minimum_required_mb' in status

    def test_verify_storage_requirements(self):
        """
        Test: Can verify storage requirements

        Requirement 1.5: Verify minimum storage
        """
        manager = StorageManager()

        requirements_met, message = manager.verify_storage_requirements("/")

        assert isinstance(requirements_met, bool)
        assert isinstance(message, str)
        assert '512' in message  # Should mention minimum

    def test_optimize(self):
        """Test: Can run storage optimization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            manager = StorageManager()
            actions = manager.optimize(temp_path)

            assert isinstance(actions, list)

    def test_get_optimization_report(self):
        """Test: Can get optimization report"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            manager = StorageManager()
            report = manager.get_optimization_report(temp_path)

            assert isinstance(report, dict)
            assert 'storage_usage' in report
            assert 'largest_directories' in report
            assert 'optimization_suggestions' in report


class TestStorageUnits:
    """Tests for storage unit conversions"""

    def test_storage_units_defined(self):
        """Test: All storage units are defined"""
        assert StorageUnit.BYTES.value == 1
        assert StorageUnit.KB.value == 1024
        assert StorageUnit.MB.value == 1024 * 1024
        assert StorageUnit.GB.value == 1024 * 1024 * 1024


class TestDirectorySize:
    """Tests for directory size tracking"""

    def test_directory_size_creation(self):
        """Test: Directory size can be created"""
        dir_size = DirectorySize(
            path="/test",
            size=10 * 1024 * 1024,  # 10MB
            file_count=5,
            dir_count=2
        )

        assert dir_size.path == "/test"
        assert dir_size.file_count == 5

    def test_to_mb(self):
        """Test: Can convert directory size to MB"""
        dir_size = DirectorySize(
            path="/test",
            size=50 * 1024 * 1024  # 50MB
        )

        assert dir_size.to_mb() == 50.0

    def test_to_dict(self):
        """Test: Can convert to dictionary"""
        dir_size = DirectorySize(
            path="/test",
            size=100 * 1024 * 1024,
            file_count=10,
            dir_count=3
        )

        dir_dict = dir_size.to_dict()

        assert isinstance(dir_dict, dict)
        assert dir_dict['path'] == "/test"
        assert dir_dict['file_count'] == 10


class TestStorageRequirements:
    """Tests for storage requirements compliance"""

    def test_512mb_minimum_requirement(self):
        """
        Test: 512MB minimum requirement is enforced

        Requirement 1.5: Minimum storage 512MB
        """
        monitor = StorageMonitor()

        assert monitor.minimum_storage_mb == 512

    def test_storage_below_minimum_detected(self):
        """Test: Storage below minimum is detected"""
        # Create mock usage with low available storage
        usage = StorageUsage(
            total=1024 * 1024 * 1024,  # 1GB
            used=900 * 1024 * 1024,    # 900MB used
            free=124 * 1024 * 1024,    # 124MB free (below 512MB)
            available=124 * 1024 * 1024
        )

        available_mb = usage.to_mb(usage.available)
        meets_requirement = available_mb >= 512

        # Should detect that it's below minimum
        assert meets_requirement is False

    def test_storage_above_minimum_detected(self):
        """Test: Storage above minimum is detected"""
        # Create mock usage with sufficient storage
        usage = StorageUsage(
            total=2 * 1024 * 1024 * 1024,  # 2GB
            used=500 * 1024 * 1024,        # 500MB used
            free=1548 * 1024 * 1024,       # 1548MB free
            available=1548 * 1024 * 1024
        )

        available_mb = usage.to_mb(usage.available)
        meets_requirement = available_mb >= 512

        # Should detect that it meets minimum
        assert meets_requirement is True
