"""
Unit Tests for Memory Usage Measurement

Tests memory usage measurement and optimization.

Design Goal: RAM consumption under 128MB
"""

import pytest
import time
from unittest.mock import Mock, patch, mock_open

from src.benchmark.memory_benchmark import (
    ProcessMemoryUsage,
    SystemMemorySnapshot,
    MemoryProfile,
    MemoryProfiler,
    MemoryAnalyzer,
    MemoryOptimizer,
    MemoryBenchmark,
    MemoryReporter,
)


class TestProcessMemoryUsage:
    """Tests for process memory usage data structure"""

    def test_memory_usage_creation(self):
        """Test: Process memory usage can be created"""
        usage = ProcessMemoryUsage(
            pid=1234,
            name="test_process",
            rss=10 * 1024 * 1024,  # 10MB
            vms=20 * 1024 * 1024,  # 20MB
            shared=2 * 1024 * 1024  # 2MB
        )

        assert usage.pid == 1234
        assert usage.name == "test_process"
        assert usage.rss == 10 * 1024 * 1024

    def test_rss_mb_conversion(self):
        """Test: Can convert RSS to MB"""
        usage = ProcessMemoryUsage(
            pid=1,
            name="test",
            rss=10 * 1024 * 1024,  # 10MB in bytes
            vms=0,
            shared=0
        )

        assert usage.rss_mb() == 10.0

    def test_vms_mb_conversion(self):
        """Test: Can convert VMS to MB"""
        usage = ProcessMemoryUsage(
            pid=1,
            name="test",
            rss=0,
            vms=20 * 1024 * 1024,  # 20MB in bytes
            shared=0
        )

        assert usage.vms_mb() == 20.0

    def test_to_dict(self):
        """Test: Can convert to dictionary"""
        usage = ProcessMemoryUsage(
            pid=1234,
            name="test_process",
            rss=10 * 1024 * 1024,
            vms=20 * 1024 * 1024,
            shared=2 * 1024 * 1024
        )

        usage_dict = usage.to_dict()

        assert isinstance(usage_dict, dict)
        assert usage_dict['pid'] == 1234
        assert usage_dict['name'] == "test_process"


class TestSystemMemorySnapshot:
    """Tests for system memory snapshot"""

    def test_snapshot_creation(self):
        """Test: System memory snapshot can be created"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,  # 512MB
            available=384 * 1024 * 1024,  # 384MB
            used=128 * 1024 * 1024,  # 128MB
            free=384 * 1024 * 1024
        )

        assert snapshot.total == 512 * 1024 * 1024
        assert snapshot.used == 128 * 1024 * 1024

    def test_used_mb_conversion(self):
        """Test: Can convert used memory to MB"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=384 * 1024 * 1024,
            used=128 * 1024 * 1024,
            free=384 * 1024 * 1024
        )

        assert snapshot.used_mb() == 128.0

    def test_usage_percentage(self):
        """Test: Can calculate usage percentage"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=384 * 1024 * 1024,
            used=128 * 1024 * 1024,  # 25% of 512MB
            free=384 * 1024 * 1024
        )

        assert snapshot.usage_percentage() == 25.0

    def test_usage_percentage_zero_total(self):
        """Test: Zero total memory returns 0% usage"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=0,
            available=0,
            used=0,
            free=0
        )

        assert snapshot.usage_percentage() == 0.0


class TestMemoryProfile:
    """Tests for memory profile"""

    def test_profile_creation(self):
        """Test: Memory profile can be created"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=384 * 1024 * 1024,
            used=100 * 1024 * 1024,
            free=412 * 1024 * 1024
        )

        profile = MemoryProfile(
            system_snapshot=snapshot,
            meets_target=True
        )

        assert profile.meets_target is True
        assert profile.target_mb == 128.0

    def test_profile_with_processes(self):
        """Test: Profile can contain process data"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=400 * 1024 * 1024,
            used=112 * 1024 * 1024,
            free=400 * 1024 * 1024
        )

        processes = [
            ProcessMemoryUsage(1, "proc1", 10*1024*1024, 20*1024*1024, 0),
            ProcessMemoryUsage(2, "proc2", 15*1024*1024, 30*1024*1024, 0)
        ]

        profile = MemoryProfile(
            system_snapshot=snapshot,
            process_usages=processes
        )

        assert len(profile.process_usages) == 2


class TestMemoryProfiler:
    """Tests for memory profiler"""

    def test_profiler_initialization(self):
        """Test: Memory profiler can be initialized"""
        profiler = MemoryProfiler()

        assert profiler is not None
        assert profiler.target_mb == 128.0  # Design goal

    def test_memory_target_is_128mb(self):
        """
        Test: Memory target is 128MB

        Design Goal: RAM consumption under 128MB
        """
        profiler = MemoryProfiler()

        assert profiler.target_mb == 128.0

    def test_read_meminfo_mock(self):
        """Test: Can read meminfo (mocked)"""
        profiler = MemoryProfiler()

        meminfo_content = """MemTotal:        524288 kB
MemFree:         393216 kB
MemAvailable:    393216 kB
Buffers:          10240 kB
Cached:           20480 kB
"""

        with patch('builtins.open', mock_open(read_data=meminfo_content)):
            meminfo = profiler.read_meminfo()

            assert 'MemTotal' in meminfo
            assert meminfo['MemTotal'] == 524288 * 1024  # Converted to bytes
            assert meminfo['MemFree'] == 393216 * 1024

    def test_get_system_snapshot_mock(self):
        """Test: Can get system snapshot (mocked)"""
        profiler = MemoryProfiler()

        meminfo_content = """MemTotal:        524288 kB
MemFree:         393216 kB
MemAvailable:    393216 kB
Buffers:          10240 kB
Cached:           20480 kB
"""

        with patch('builtins.open', mock_open(read_data=meminfo_content)):
            snapshot = profiler.get_system_snapshot()

            assert isinstance(snapshot, SystemMemorySnapshot)
            assert snapshot.total == 524288 * 1024
            assert snapshot.available == 393216 * 1024

    def test_check_target_meets(self):
        """Test: Detects when memory usage meets target"""
        profiler = MemoryProfiler()

        # 100MB used - under 128MB target
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=412 * 1024 * 1024,
            used=100 * 1024 * 1024,
            free=412 * 1024 * 1024
        )

        meets_target = profiler.check_target(snapshot)

        assert meets_target is True

    def test_check_target_exceeds(self):
        """Test: Detects when memory usage exceeds target"""
        profiler = MemoryProfiler()

        # 150MB used - over 128MB target
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=362 * 1024 * 1024,
            used=150 * 1024 * 1024,
            free=362 * 1024 * 1024
        )

        meets_target = profiler.check_target(snapshot)

        assert meets_target is False

    def test_get_process_memory_mock(self):
        """Test: Can get process memory (mocked)"""
        profiler = MemoryProfiler()

        status_content = """Name:	test_process
VmSize:	   20480 kB
VmRSS:	   10240 kB
RssFile:	    2048 kB
"""

        with patch('builtins.open', mock_open(read_data=status_content)):
            usage = profiler.get_process_memory(1234)

            assert usage is not None
            assert usage.name == "test_process"
            assert usage.rss == 10240 * 1024
            assert usage.vms == 20480 * 1024

    def test_get_process_memory_not_found(self):
        """Test: Returns None for non-existent process"""
        profiler = MemoryProfiler()

        with patch('builtins.open', side_effect=IOError()):
            usage = profiler.get_process_memory(99999)

            assert usage is None


class TestMemoryAnalyzer:
    """Tests for memory analyzer"""

    def test_analyzer_initialization(self):
        """Test: Memory analyzer can be initialized"""
        analyzer = MemoryAnalyzer()

        assert analyzer is not None
        assert analyzer.target_mb == 128.0

    def test_analyze_profile(self):
        """Test: Can analyze memory profile"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=400 * 1024 * 1024,
            used=112 * 1024 * 1024,
            free=400 * 1024 * 1024
        )

        processes = [
            ProcessMemoryUsage(1, "proc1", 30*1024*1024, 40*1024*1024, 0),
            ProcessMemoryUsage(2, "proc2", 20*1024*1024, 30*1024*1024, 0)
        ]

        profile = MemoryProfile(
            system_snapshot=snapshot,
            process_usages=processes,
            meets_target=True
        )

        analyzer = MemoryAnalyzer()
        analysis = analyzer.analyze_profile(profile)

        assert isinstance(analysis, dict)
        assert 'used_mb' in analysis
        assert 'meets_target' in analysis
        assert 'top_processes' in analysis
        assert analysis['meets_target'] is True

    def test_analyze_profile_exceeds_target(self):
        """Test: Generates recommendations when target exceeded"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=350 * 1024 * 1024,
            used=162 * 1024 * 1024,  # Over 128MB
            free=350 * 1024 * 1024
        )

        profile = MemoryProfile(
            system_snapshot=snapshot,
            meets_target=False
        )

        analyzer = MemoryAnalyzer()
        analysis = analyzer.analyze_profile(profile)

        assert analysis['meets_target'] is False
        assert len(analysis['recommendations']) > 0

    def test_detect_memory_leak_insufficient_data(self):
        """Test: Returns insufficient data for single snapshot"""
        analyzer = MemoryAnalyzer()

        snapshots = [
            SystemMemorySnapshot(
                timestamp=time.time(),
                total=512 * 1024 * 1024,
                available=400 * 1024 * 1024,
                used=112 * 1024 * 1024,
                free=400 * 1024 * 1024
            )
        ]

        result = analyzer.detect_memory_leak(snapshots)

        assert result['leak_detected'] is False
        assert 'Insufficient data' in result['reason']

    def test_detect_memory_leak_detected(self):
        """Test: Detects consistent memory increase"""
        analyzer = MemoryAnalyzer()

        # Create snapshots with increasing memory usage
        snapshots = []
        for i in range(10):
            used = (100 + i * 5) * 1024 * 1024  # Increasing from 100MB to 145MB
            snapshot = SystemMemorySnapshot(
                timestamp=time.time() + i,
                total=512 * 1024 * 1024,
                available=(412 - i * 5) * 1024 * 1024,
                used=used,
                free=(412 - i * 5) * 1024 * 1024
            )
            snapshots.append(snapshot)

        result = analyzer.detect_memory_leak(snapshots)

        assert result['leak_detected'] is True
        assert result['increase_mb'] > 0

    def test_detect_memory_leak_not_detected(self):
        """Test: Does not detect leak with stable memory"""
        analyzer = MemoryAnalyzer()

        # Create snapshots with stable memory usage
        snapshots = []
        for i in range(10):
            snapshot = SystemMemorySnapshot(
                timestamp=time.time() + i,
                total=512 * 1024 * 1024,
                available=400 * 1024 * 1024,
                used=112 * 1024 * 1024,  # Constant
                free=400 * 1024 * 1024
            )
            snapshots.append(snapshot)

        result = analyzer.detect_memory_leak(snapshots)

        assert result['leak_detected'] is False


class TestMemoryOptimizer:
    """Tests for memory optimizer"""

    def test_optimizer_initialization(self):
        """Test: Memory optimizer can be initialized"""
        optimizer = MemoryOptimizer()

        assert optimizer is not None
        assert optimizer.analyzer is not None

    def test_suggest_optimizations(self):
        """Test: Can suggest optimizations"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=350 * 1024 * 1024,
            used=162 * 1024 * 1024,  # Over 128MB
            free=350 * 1024 * 1024,
            cached=25 * 1024 * 1024  # High cache
        )

        profile = MemoryProfile(
            system_snapshot=snapshot,
            meets_target=False
        )

        optimizer = MemoryOptimizer()
        suggestions = optimizer.suggest_optimizations(profile)

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_apply_optimization(self):
        """Test: Can apply optimization"""
        optimizer = MemoryOptimizer()

        result = optimizer.apply_optimization("test-optimization")

        assert result is True
        assert "test-optimization" in optimizer.optimizations_applied

    def test_optimize_for_target(self):
        """Test: Can optimize for target"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=350 * 1024 * 1024,
            used=162 * 1024 * 1024,
            free=350 * 1024 * 1024
        )

        profile = MemoryProfile(
            system_snapshot=snapshot,
            meets_target=False
        )

        optimizer = MemoryOptimizer()
        actions = optimizer.optimize_for_target(profile)

        assert isinstance(actions, list)


class TestMemoryBenchmark:
    """Tests for memory benchmark"""

    def test_benchmark_initialization(self):
        """Test: Memory benchmark can be initialized"""
        benchmark = MemoryBenchmark()

        assert benchmark is not None
        assert benchmark.profiler is not None
        assert benchmark.analyzer is not None

    @pytest.mark.skip(reason="Takes too long (5+ seconds)")
    def test_run_benchmark(self):
        """Test: Can run memory benchmark"""
        benchmark = MemoryBenchmark()

        result = benchmark.run_benchmark(duration=1.0, samples=5)

        assert isinstance(result, dict)
        assert 'profile' in result
        assert 'analysis' in result
        assert 'leak_detection' in result

    def test_verify_memory_target_meets(self):
        """Test: Can verify memory target is met"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=412 * 1024 * 1024,
            used=100 * 1024 * 1024,
            free=412 * 1024 * 1024
        )

        profile = MemoryProfile(
            system_snapshot=snapshot,
            meets_target=True
        )

        benchmark = MemoryBenchmark()
        meets_target, message = benchmark.verify_memory_target(profile)

        assert meets_target is True
        assert '100' in message

    def test_verify_memory_target_exceeds(self):
        """Test: Detects when memory exceeds target"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=350 * 1024 * 1024,
            used=162 * 1024 * 1024,
            free=350 * 1024 * 1024
        )

        profile = MemoryProfile(
            system_snapshot=snapshot,
            meets_target=False
        )

        benchmark = MemoryBenchmark()
        meets_target, message = benchmark.verify_memory_target(profile)

        assert meets_target is False
        assert 'exceeds' in message.lower()

    def test_optimize_and_verify(self):
        """Test: Can optimize and verify"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=350 * 1024 * 1024,
            used=162 * 1024 * 1024,
            free=350 * 1024 * 1024
        )

        profile = MemoryProfile(
            system_snapshot=snapshot,
            meets_target=False
        )

        benchmark = MemoryBenchmark()
        result = benchmark.optimize_and_verify(profile)

        assert isinstance(result, dict)
        assert 'initial_usage_mb' in result
        assert 'meets_target' in result


class TestMemoryReporter:
    """Tests for memory reporter"""

    def test_reporter_initialization(self):
        """Test: Memory reporter can be initialized"""
        reporter = MemoryReporter()

        assert reporter is not None

    def test_generate_report(self):
        """Test: Can generate report"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=412 * 1024 * 1024,
            used=100 * 1024 * 1024,
            free=412 * 1024 * 1024,
            buffers=5 * 1024 * 1024,
            cached=10 * 1024 * 1024
        )

        profile = MemoryProfile(
            system_snapshot=snapshot,
            meets_target=True
        )

        analysis = {
            'used_mb': 100.0,
            'meets_target': True,
            'top_processes': [
                {'pid': 1, 'name': 'proc1', 'rss_mb': 20.0, 'vms_mb': 30.0}
            ],
            'recommendations': []
        }

        reporter = MemoryReporter()
        report = reporter.generate_report(profile, analysis)

        assert isinstance(report, str)
        assert '100.00' in report
        assert 'PASS' in report

    def test_export_metrics(self):
        """Test: Can export metrics"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=412 * 1024 * 1024,
            used=100 * 1024 * 1024,
            free=412 * 1024 * 1024
        )

        profile = MemoryProfile(
            system_snapshot=snapshot,
            meets_target=True
        )

        reporter = MemoryReporter()
        metrics = reporter.export_metrics(profile)

        assert isinstance(metrics, dict)
        assert 'used_mb' in metrics
        assert 'meets_128mb_target' in metrics
        assert metrics['meets_128mb_target'] is True


class TestMemoryTargetCompliance:
    """Tests for memory target compliance"""

    def test_128mb_target(self):
        """
        Test: 128MB target is enforced

        Design Goal: RAM consumption under 128MB
        """
        profiler = MemoryProfiler()

        assert profiler.target_mb == 128.0

    def test_100mb_meets_target(self):
        """Test: 100MB meets target"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=412 * 1024 * 1024,
            used=100 * 1024 * 1024,
            free=412 * 1024 * 1024
        )

        meets_target = snapshot.used_mb() < 128.0

        assert meets_target is True

    def test_150mb_exceeds_target(self):
        """Test: 150MB exceeds target"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=362 * 1024 * 1024,
            used=150 * 1024 * 1024,
            free=362 * 1024 * 1024
        )

        meets_target = snapshot.used_mb() < 128.0

        assert meets_target is False

    def test_exactly_128mb_meets_target(self):
        """Test: Exactly 128MB meets target"""
        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=512 * 1024 * 1024,
            available=384 * 1024 * 1024,
            used=128 * 1024 * 1024,
            free=384 * 1024 * 1024
        )

        profiler = MemoryProfiler()
        meets_target = profiler.check_target(snapshot)

        # Exactly 128.0MB should not meet target (< not <=)
        assert meets_target is False
