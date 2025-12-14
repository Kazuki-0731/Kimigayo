"""
Unit Tests for Base Image Size Verification

Tests image size verification and optimization.

Design Goal:
- Minimal: 5MB or less
- Standard: 15MB or less
- Extended: 50MB or less
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.benchmark.image_size import (
    ImageType,
    ComponentSize,
    ImageSizeProfile,
    ImageSizeAnalyzer,
    ImageOptimizer,
    ImageSizeBenchmark,
    ImageSizeReporter,
)


class TestImageType:
    """Tests for image type enum"""

    def test_minimal_image_type(self):
        """Test: Minimal image type has 5MB target"""
        assert ImageType.MINIMAL.image_name == "minimal"
        assert ImageType.MINIMAL.target_mb == 5.0

    def test_standard_image_type(self):
        """Test: Standard image type has 15MB target"""
        assert ImageType.STANDARD.image_name == "standard"
        assert ImageType.STANDARD.target_mb == 15.0

    def test_extended_image_type(self):
        """Test: Extended image type has 50MB target"""
        assert ImageType.EXTENDED.image_name == "extended"
        assert ImageType.EXTENDED.target_mb == 50.0


class TestComponentSize:
    """Tests for component size data structure"""

    def test_component_creation(self):
        """Test: Component size can be created"""
        component = ComponentSize(
            name="kernel",
            path="/boot/vmlinuz",
            size_bytes=2 * 1024 * 1024  # 2MB
        )

        assert component.name == "kernel"
        assert component.size_bytes == 2 * 1024 * 1024

    def test_size_mb_conversion(self):
        """Test: Can convert size to MB"""
        component = ComponentSize(
            name="test",
            path="/test",
            size_bytes=3 * 1024 * 1024  # 3MB
        )

        assert component.size_mb() == 3.0

    def test_size_kb_conversion(self):
        """Test: Can convert size to KB"""
        component = ComponentSize(
            name="test",
            path="/test",
            size_bytes=2048  # 2KB
        )

        assert component.size_kb() == 2.0

    def test_to_dict(self):
        """Test: Can convert to dictionary"""
        component = ComponentSize(
            name="lib",
            path="/lib",
            size_bytes=1024 * 1024
        )

        component_dict = component.to_dict()

        assert isinstance(component_dict, dict)
        assert component_dict['name'] == "lib"
        assert component_dict['size_bytes'] == 1024 * 1024


class TestImageSizeProfile:
    """Tests for image size profile"""

    def test_profile_creation(self):
        """Test: Image size profile can be created"""
        profile = ImageSizeProfile(
            image_type="minimal",
            total_size_bytes=4 * 1024 * 1024,  # 4MB
            target_mb=5.0,
            meets_target=True
        )

        assert profile.image_type == "minimal"
        assert profile.total_size_bytes == 4 * 1024 * 1024
        assert profile.meets_target is True

    def test_total_mb_conversion(self):
        """Test: Can convert total size to MB"""
        profile = ImageSizeProfile(
            image_type="standard",
            total_size_bytes=10 * 1024 * 1024,  # 10MB
            target_mb=15.0
        )

        assert profile.total_mb() == 10.0

    def test_profile_with_components(self):
        """Test: Profile can contain components"""
        components = [
            ComponentSize("kernel", "/boot", 2 * 1024 * 1024),
            ComponentSize("lib", "/lib", 1 * 1024 * 1024)
        ]

        profile = ImageSizeProfile(
            image_type="minimal",
            total_size_bytes=3 * 1024 * 1024,
            components=components,
            target_mb=5.0
        )

        assert len(profile.components) == 2


class TestImageSizeAnalyzer:
    """Tests for image size analyzer"""

    def test_analyzer_initialization(self):
        """Test: Image size analyzer can be initialized"""
        analyzer = ImageSizeAnalyzer()

        assert analyzer is not None
        assert "minimal" in analyzer.image_types
        assert "standard" in analyzer.image_types
        assert "extended" in analyzer.image_types

    def test_get_file_size(self):
        """Test: Can get file size"""
        analyzer = ImageSizeAnalyzer()

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_data = b"x" * 1024  # 1KB
            f.write(test_data)
            temp_path = f.name

        try:
            size = analyzer.get_file_size(temp_path)
            assert size == 1024
        finally:
            os.unlink(temp_path)

    def test_get_file_size_nonexistent(self):
        """Test: Returns 0 for non-existent file"""
        analyzer = ImageSizeAnalyzer()

        size = analyzer.get_file_size("/nonexistent/file")

        assert size == 0

    def test_get_directory_size(self):
        """Test: Can get directory size"""
        analyzer = ImageSizeAnalyzer()

        # Create temporary directory with files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            for i in range(3):
                file_path = os.path.join(temp_dir, f"file{i}.txt")
                with open(file_path, 'wb') as f:
                    f.write(b"x" * 1024)  # 1KB each

            size = analyzer.get_directory_size(temp_dir)
            assert size == 3 * 1024  # 3KB total

    def test_verify_image_size_meets_target(self):
        """Test: Verifies when image meets target"""
        analyzer = ImageSizeAnalyzer()

        # 4MB image, 5MB target - should meet
        profile = analyzer.verify_image_size(
            ImageType.MINIMAL,
            4 * 1024 * 1024
        )

        assert profile.meets_target is True
        assert profile.image_type == "minimal"
        assert profile.target_mb == 5.0

    def test_verify_image_size_exceeds_target(self):
        """Test: Detects when image exceeds target"""
        analyzer = ImageSizeAnalyzer()

        # 6MB image, 5MB target - should not meet
        profile = analyzer.verify_image_size(
            ImageType.MINIMAL,
            6 * 1024 * 1024
        )

        assert profile.meets_target is False

    def test_analyze_components(self):
        """Test: Can analyze component sizes"""
        analyzer = ImageSizeAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            file1 = os.path.join(temp_dir, "file1.txt")
            file2 = os.path.join(temp_dir, "file2.txt")

            with open(file1, 'wb') as f:
                f.write(b"x" * 1024)
            with open(file2, 'wb') as f:
                f.write(b"y" * 2048)

            components = analyzer.analyze_components(
                temp_dir,
                ["file1.txt", "file2.txt"]
            )

            assert len(components) == 2
            assert components[0].size_bytes == 1024
            assert components[1].size_bytes == 2048

    def test_analyze_image_file(self):
        """Test: Can analyze image file"""
        analyzer = ImageSizeAnalyzer()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 3MB test file
            f.write(b"x" * 3 * 1024 * 1024)
            temp_path = f.name

        try:
            profile = analyzer.analyze_image(
                ImageType.MINIMAL,
                temp_path
            )

            assert profile.total_mb() == 3.0
            assert profile.meets_target is True  # 3MB < 5MB
        finally:
            os.unlink(temp_path)

    def test_analyze_image_directory(self):
        """Test: Can analyze image directory"""
        analyzer = ImageSizeAnalyzer()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files totaling 4MB
            for i in range(4):
                file_path = os.path.join(temp_dir, f"file{i}.bin")
                with open(file_path, 'wb') as f:
                    f.write(b"x" * 1024 * 1024)  # 1MB each

            profile = analyzer.analyze_image(
                ImageType.MINIMAL,
                temp_dir
            )

            assert profile.total_mb() == 4.0
            assert profile.meets_target is True


class TestImageOptimizer:
    """Tests for image optimizer"""

    def test_optimizer_initialization(self):
        """Test: Image optimizer can be initialized"""
        optimizer = ImageOptimizer()

        assert optimizer is not None
        assert optimizer.analyzer is not None

    def test_suggest_optimizations_exceeds_target(self):
        """Test: Suggests optimizations when target exceeded"""
        profile = ImageSizeProfile(
            image_type="minimal",
            total_size_bytes=7 * 1024 * 1024,  # 7MB, over 5MB target
            target_mb=5.0,
            meets_target=False
        )

        optimizer = ImageOptimizer()
        suggestions = optimizer.suggest_optimizations(profile)

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # Should mention exceeding target
        assert any("exceeds target" in s for s in suggestions)

    def test_suggest_optimizations_large_components(self):
        """Test: Suggests optimizations for large components"""
        components = [
            ComponentSize("kernel", "/boot", 3 * 1024 * 1024),  # 3MB
            ComponentSize("lib", "/lib", 2 * 1024 * 1024)  # 2MB
        ]

        profile = ImageSizeProfile(
            image_type="minimal",
            total_size_bytes=6 * 1024 * 1024,
            components=components,
            target_mb=5.0,
            meets_target=False
        )

        optimizer = ImageOptimizer()
        suggestions = optimizer.suggest_optimizations(profile)

        # Should mention large components
        assert any("kernel" in s for s in suggestions)

    def test_apply_optimization(self):
        """Test: Can apply optimization"""
        optimizer = ImageOptimizer()

        result = optimizer.apply_optimization("test-optimization")

        assert result is True
        assert "test-optimization" in optimizer.optimizations_applied

    def test_optimize_for_target(self):
        """Test: Can optimize for target"""
        profile = ImageSizeProfile(
            image_type="minimal",
            total_size_bytes=7 * 1024 * 1024,
            target_mb=5.0,
            meets_target=False
        )

        optimizer = ImageOptimizer()
        actions = optimizer.optimize_for_target(profile)

        assert isinstance(actions, list)

    def test_get_optimization_status(self):
        """Test: Can get optimization status"""
        optimizer = ImageOptimizer()

        optimizer.apply_optimization("opt1")
        optimizer.apply_optimization("opt2")

        status = optimizer.get_optimization_status()

        assert status['optimization_count'] == 2


class TestImageSizeBenchmark:
    """Tests for image size benchmark"""

    def test_benchmark_initialization(self):
        """Test: Image size benchmark can be initialized"""
        benchmark = ImageSizeBenchmark()

        assert benchmark is not None
        assert benchmark.analyzer is not None
        assert benchmark.optimizer is not None

    def test_verify_minimal_image_meets_target(self):
        """Test: Verifies minimal image meets 5MB target"""
        benchmark = ImageSizeBenchmark()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 4MB test file
            f.write(b"x" * 4 * 1024 * 1024)
            temp_path = f.name

        try:
            meets_target, message = benchmark.verify_minimal_image(temp_path)

            assert meets_target is True
            assert "4.00" in message
        finally:
            os.unlink(temp_path)

    def test_verify_minimal_image_exceeds_target(self):
        """Test: Detects when minimal image exceeds 5MB"""
        benchmark = ImageSizeBenchmark()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 6MB test file
            f.write(b"x" * 6 * 1024 * 1024)
            temp_path = f.name

        try:
            meets_target, message = benchmark.verify_minimal_image(temp_path)

            assert meets_target is False
            assert "exceeds" in message.lower()
        finally:
            os.unlink(temp_path)

    def test_verify_standard_image_meets_target(self):
        """Test: Verifies standard image meets 15MB target"""
        benchmark = ImageSizeBenchmark()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 12MB test file
            f.write(b"x" * 12 * 1024 * 1024)
            temp_path = f.name

        try:
            meets_target, message = benchmark.verify_standard_image(temp_path)

            assert meets_target is True
            assert "12.00" in message
        finally:
            os.unlink(temp_path)

    def test_verify_standard_image_exceeds_target(self):
        """Test: Detects when standard image exceeds 15MB"""
        benchmark = ImageSizeBenchmark()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 18MB test file
            f.write(b"x" * 18 * 1024 * 1024)
            temp_path = f.name

        try:
            meets_target, message = benchmark.verify_standard_image(temp_path)

            assert meets_target is False
            assert "exceeds" in message.lower()
        finally:
            os.unlink(temp_path)

    def test_verify_extended_image_meets_target(self):
        """Test: Verifies extended image meets 50MB target"""
        benchmark = ImageSizeBenchmark()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 40MB test file
            f.write(b"x" * 40 * 1024 * 1024)
            temp_path = f.name

        try:
            meets_target, message = benchmark.verify_extended_image(temp_path)

            assert meets_target is True
            assert "40.00" in message
        finally:
            os.unlink(temp_path)

    def test_verify_extended_image_exceeds_target(self):
        """Test: Detects when extended image exceeds 50MB"""
        benchmark = ImageSizeBenchmark()

        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Create 60MB test file
            f.write(b"x" * 60 * 1024 * 1024)
            temp_path = f.name

        try:
            meets_target, message = benchmark.verify_extended_image(temp_path)

            assert meets_target is False
            assert "exceeds" in message.lower()
        finally:
            os.unlink(temp_path)

    def test_verify_all_images(self):
        """Test: Can verify all image types"""
        benchmark = ImageSizeBenchmark()

        # Create temporary files for each image type
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(b"x" * 4 * 1024 * 1024)  # 4MB minimal
            minimal_path = f1.name

        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(b"x" * 12 * 1024 * 1024)  # 12MB standard
            standard_path = f2.name

        with tempfile.NamedTemporaryFile(delete=False) as f3:
            f3.write(b"x" * 40 * 1024 * 1024)  # 40MB extended
            extended_path = f3.name

        try:
            results = benchmark.verify_all_images(
                minimal_path=minimal_path,
                standard_path=standard_path,
                extended_path=extended_path
            )

            assert results['all_passed'] is True
            assert 'minimal' in results['images']
            assert 'standard' in results['images']
            assert 'extended' in results['images']
        finally:
            os.unlink(minimal_path)
            os.unlink(standard_path)
            os.unlink(extended_path)

    def test_optimize_and_verify(self):
        """Test: Can optimize and verify"""
        profile = ImageSizeProfile(
            image_type="minimal",
            total_size_bytes=7 * 1024 * 1024,
            target_mb=5.0,
            meets_target=False
        )

        benchmark = ImageSizeBenchmark()
        result = benchmark.optimize_and_verify(profile)

        assert isinstance(result, dict)
        assert 'initial_size_mb' in result
        assert 'meets_target' in result


class TestImageSizeReporter:
    """Tests for image size reporter"""

    def test_reporter_initialization(self):
        """Test: Image size reporter can be initialized"""
        reporter = ImageSizeReporter()

        assert reporter is not None

    def test_generate_report(self):
        """Test: Can generate report"""
        components = [
            ComponentSize("kernel", "/boot", 2 * 1024 * 1024),
            ComponentSize("lib", "/lib", 1 * 1024 * 1024)
        ]

        profile = ImageSizeProfile(
            image_type="minimal",
            total_size_bytes=4 * 1024 * 1024,
            components=components,
            target_mb=5.0,
            meets_target=True
        )

        reporter = ImageSizeReporter()
        report = reporter.generate_report(profile)

        assert isinstance(report, str)
        assert "MINIMAL" in report
        assert "4.00" in report
        assert "PASS" in report

    def test_generate_comparison_report(self):
        """Test: Can generate comparison report"""
        profiles = {
            'minimal': ImageSizeProfile(
                image_type="minimal",
                total_size_bytes=4 * 1024 * 1024,
                target_mb=5.0,
                meets_target=True
            ),
            'standard': ImageSizeProfile(
                image_type="standard",
                total_size_bytes=12 * 1024 * 1024,
                target_mb=15.0,
                meets_target=True
            )
        }

        reporter = ImageSizeReporter()
        report = reporter.generate_comparison_report(profiles)

        assert isinstance(report, str)
        assert "MINIMAL" in report
        assert "STANDARD" in report

    def test_export_metrics(self):
        """Test: Can export metrics"""
        profile = ImageSizeProfile(
            image_type="minimal",
            total_size_bytes=4 * 1024 * 1024,
            target_mb=5.0,
            meets_target=True
        )

        reporter = ImageSizeReporter()
        metrics = reporter.export_metrics(profile)

        assert isinstance(metrics, dict)
        assert 'total_size_mb' in metrics
        assert 'meets_target' in metrics
        assert metrics['meets_target'] is True


class TestImageSizeTargetCompliance:
    """Tests for image size target compliance"""

    def test_minimal_5mb_target(self):
        """
        Test: Minimal image has 5MB target

        Design Goal: Minimal image ≤ 5MB
        """
        assert ImageType.MINIMAL.target_mb == 5.0

    def test_standard_15mb_target(self):
        """
        Test: Standard image has 15MB target

        Design Goal: Standard image ≤ 15MB
        """
        assert ImageType.STANDARD.target_mb == 15.0

    def test_extended_50mb_target(self):
        """
        Test: Extended image has 50MB target

        Design Goal: Extended image ≤ 50MB
        """
        assert ImageType.EXTENDED.target_mb == 50.0

    def test_4mb_meets_minimal_target(self):
        """Test: 4MB meets minimal target"""
        analyzer = ImageSizeAnalyzer()
        profile = analyzer.verify_image_size(
            ImageType.MINIMAL,
            4 * 1024 * 1024
        )

        assert profile.meets_target is True

    def test_6mb_exceeds_minimal_target(self):
        """Test: 6MB exceeds minimal target"""
        analyzer = ImageSizeAnalyzer()
        profile = analyzer.verify_image_size(
            ImageType.MINIMAL,
            6 * 1024 * 1024
        )

        assert profile.meets_target is False

    def test_exactly_5mb_meets_minimal_target(self):
        """Test: Exactly 5MB meets minimal target"""
        analyzer = ImageSizeAnalyzer()
        profile = analyzer.verify_image_size(
            ImageType.MINIMAL,
            5 * 1024 * 1024
        )

        # Exactly 5.0MB should meet target (<=)
        assert profile.meets_target is True
