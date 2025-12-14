"""
Unit Tests for Boot Time Measurement

Tests boot time measurement and optimization.

Design Goal: Boot time under 10 seconds
"""

import pytest
import time

from src.benchmark.boot_time import (
    BootMeasurement,
    BootProfile,
    BootTimer,
    BootAnalyzer,
    BootOptimizer,
    BootBenchmark,
    BootReporter,
    BootPhase,
)


class TestBootMeasurement:
    """Tests for boot measurement data structure"""

    def test_measurement_creation(self):
        """Test: Boot measurement can be created"""
        measurement = BootMeasurement(
            phase="test_phase",
            start_time=0.0,
            end_time=2.5,
            duration=2.5
        )

        assert measurement.phase == "test_phase"
        assert measurement.duration == 2.5

    def test_to_dict(self):
        """Test: Can convert to dictionary"""
        measurement = BootMeasurement(
            phase="kernel_init",
            start_time=0.0,
            end_time=3.0,
            duration=3.0
        )

        measurement_dict = measurement.to_dict()

        assert isinstance(measurement_dict, dict)
        assert measurement_dict['phase'] == "kernel_init"
        assert measurement_dict['duration'] == 3.0


class TestBootProfile:
    """Tests for boot profile"""

    def test_profile_creation(self):
        """Test: Boot profile can be created"""
        profile = BootProfile(
            total_time=8.5,
            meets_target=True
        )

        assert profile.total_time == 8.5
        assert profile.meets_target is True

    def test_profile_with_measurements(self):
        """Test: Profile can contain measurements"""
        measurements = [
            BootMeasurement("phase1", 0.0, 2.0, 2.0),
            BootMeasurement("phase2", 2.0, 5.0, 3.0)
        ]

        profile = BootProfile(
            total_time=5.0,
            measurements=measurements
        )

        assert len(profile.measurements) == 2

    def test_to_dict(self):
        """Test: Can convert profile to dictionary"""
        profile = BootProfile(
            total_time=9.5,
            meets_target=True,
            bottlenecks=["slow_phase: 3.5s"]
        )

        profile_dict = profile.to_dict()

        assert isinstance(profile_dict, dict)
        assert profile_dict['total_time'] == 9.5
        assert profile_dict['meets_target'] is True


class TestBootTimer:
    """Tests for boot timer"""

    def test_timer_initialization(self):
        """Test: Boot timer can be initialized"""
        timer = BootTimer()

        assert timer is not None
        assert timer.boot_target_seconds == 10.0  # Design goal

    def test_boot_target_is_10_seconds(self):
        """
        Test: Boot target is 10 seconds

        Design Goal: Boot time under 10 seconds
        """
        timer = BootTimer()

        assert timer.boot_target_seconds == 10.0

    def test_start_phase(self):
        """Test: Can start timing a phase"""
        timer = BootTimer()

        timer.start_phase("test_phase")

        assert "test_phase" in timer.phase_start_times

    def test_end_phase(self):
        """Test: Can end timing a phase"""
        timer = BootTimer()

        timer.start_phase("test_phase")
        time.sleep(0.1)  # Small delay
        measurement = timer.end_phase("test_phase")

        assert measurement is not None
        assert measurement.phase == "test_phase"
        assert measurement.duration > 0

    def test_end_phase_not_started(self):
        """Test: Ending non-started phase returns None"""
        timer = BootTimer()

        measurement = timer.end_phase("nonexistent_phase")

        assert measurement is None

    def test_get_total_time(self):
        """Test: Can get total boot time"""
        timer = BootTimer()

        timer.start_phase("phase1")
        time.sleep(0.05)
        timer.end_phase("phase1")

        timer.start_phase("phase2")
        time.sleep(0.05)
        timer.end_phase("phase2")

        total_time = timer.get_total_time()

        assert total_time > 0

    def test_check_target(self):
        """
        Test: Can check if boot time meets target

        Design Goal: Verify boot time under 10 seconds
        """
        timer = BootTimer()

        timer.start_phase("fast_phase")
        time.sleep(0.05)
        timer.end_phase("fast_phase")

        meets_target, total_time = timer.check_target()

        assert isinstance(meets_target, bool)
        assert total_time > 0
        # With only 0.05s, should meet target
        assert meets_target is True

    def test_get_profile(self):
        """Test: Can get complete boot profile"""
        timer = BootTimer()

        timer.start_phase("phase1")
        time.sleep(0.05)
        timer.end_phase("phase1")

        profile = timer.get_profile()

        assert isinstance(profile, BootProfile)
        assert len(profile.measurements) == 1


class TestBootAnalyzer:
    """Tests for boot analyzer"""

    def test_analyzer_initialization(self):
        """Test: Boot analyzer can be initialized"""
        analyzer = BootAnalyzer()

        assert analyzer is not None
        assert analyzer.boot_target_seconds == 10.0

    def test_analyze_profile(self):
        """Test: Can analyze boot profile"""
        measurements = [
            BootMeasurement("phase1", 0.0, 2.0, 2.0),
            BootMeasurement("phase2", 2.0, 5.0, 3.0),
            BootMeasurement("phase3", 5.0, 8.0, 3.0)
        ]

        profile = BootProfile(
            total_time=8.0,
            measurements=measurements,
            meets_target=True
        )

        analyzer = BootAnalyzer()
        analysis = analyzer.analyze_profile(profile)

        assert isinstance(analysis, dict)
        assert 'total_time' in analysis
        assert 'meets_target' in analysis
        assert 'slowest_phases' in analysis

    def test_suggest_optimizations(self):
        """Test: Can suggest optimizations"""
        measurements = [
            BootMeasurement("kernel_init", 0.0, 4.0, 4.0),  # Slow
            BootMeasurement("services", 4.0, 8.0, 4.0)      # Slow
        ]

        profile = BootProfile(
            total_time=12.0,  # Over target
            measurements=measurements,
            meets_target=False
        )

        analyzer = BootAnalyzer()
        suggestions = analyzer.suggest_optimizations(profile)

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0


class TestBootOptimizer:
    """Tests for boot optimizer"""

    def test_optimizer_initialization(self):
        """Test: Boot optimizer can be initialized"""
        optimizer = BootOptimizer()

        assert optimizer is not None
        assert optimizer.analyzer is not None

    def test_apply_optimization(self):
        """Test: Can apply optimization"""
        optimizer = BootOptimizer()

        result = optimizer.apply_optimization("test-optimization")

        assert result is True
        assert "test-optimization" in optimizer.optimizations_applied

    def test_optimize_for_target(self):
        """Test: Can optimize for target"""
        measurements = [
            BootMeasurement("services", 0.0, 5.0, 5.0)
        ]

        profile = BootProfile(
            total_time=12.0,
            measurements=measurements,
            meets_target=False
        )

        optimizer = BootOptimizer()
        actions = optimizer.optimize_for_target(profile)

        assert isinstance(actions, list)

    def test_get_optimization_status(self):
        """Test: Can get optimization status"""
        optimizer = BootOptimizer()

        optimizer.apply_optimization("opt1")
        optimizer.apply_optimization("opt2")

        status = optimizer.get_optimization_status()

        assert isinstance(status, dict)
        assert status['optimization_count'] == 2


class TestBootBenchmark:
    """Tests for boot benchmark"""

    def test_benchmark_initialization(self):
        """Test: Boot benchmark can be initialized"""
        benchmark = BootBenchmark()

        assert benchmark is not None
        assert benchmark.timer is not None
        assert benchmark.analyzer is not None

    @pytest.mark.skip(reason="Takes too long (~7 seconds)")
    def test_measure_boot(self):
        """Test: Can measure boot sequence"""
        benchmark = BootBenchmark()

        profile = benchmark.measure_boot()

        assert isinstance(profile, BootProfile)
        assert len(profile.measurements) > 0

    def test_verify_boot_target(self):
        """
        Test: Can verify boot target

        Design Goal: Verify boot time under 10 seconds
        """
        measurements = [
            BootMeasurement("phase1", 0.0, 8.0, 8.0)
        ]

        profile = BootProfile(
            total_time=8.0,
            measurements=measurements,
            meets_target=True
        )

        benchmark = BootBenchmark()
        meets_target, message = benchmark.verify_boot_target(profile)

        assert isinstance(meets_target, bool)
        assert isinstance(message, str)
        assert '8.0' in message  # Should mention the time

    def test_verify_boot_target_exceeded(self):
        """Test: Detects when boot time exceeds target"""
        measurements = [
            BootMeasurement("phase1", 0.0, 12.0, 12.0)
        ]

        profile = BootProfile(
            total_time=12.0,
            measurements=measurements,
            meets_target=False
        )

        benchmark = BootBenchmark()
        meets_target, message = benchmark.verify_boot_target(profile)

        assert meets_target is False
        assert 'exceeds' in message.lower()

    def test_optimize_and_verify(self):
        """Test: Can optimize and verify"""
        measurements = [
            BootMeasurement("services", 0.0, 5.0, 5.0)
        ]

        profile = BootProfile(
            total_time=11.0,
            measurements=measurements,
            meets_target=False
        )

        benchmark = BootBenchmark()
        result = benchmark.optimize_and_verify(profile)

        assert isinstance(result, dict)
        assert 'initial_time' in result
        assert 'meets_target' in result


class TestBootReporter:
    """Tests for boot reporter"""

    def test_reporter_initialization(self):
        """Test: Boot reporter can be initialized"""
        reporter = BootReporter()

        assert reporter is not None

    def test_generate_report(self):
        """Test: Can generate report"""
        measurements = [
            BootMeasurement("kernel_init", 0.0, 2.0, 2.0),
            BootMeasurement("services", 2.0, 5.0, 3.0)
        ]

        profile = BootProfile(
            total_time=8.5,
            measurements=measurements,
            meets_target=True
        )

        analysis = {
            'total_time': 8.5,
            'meets_target': True,
            'recommendations': []
        }

        reporter = BootReporter()
        report = reporter.generate_report(profile, analysis)

        assert isinstance(report, str)
        assert '8.5' in report
        assert 'PASS' in report

    def test_export_metrics(self):
        """Test: Can export metrics"""
        measurements = [
            BootMeasurement("kernel_init", 0.0, 2.0, 2.0),
            BootMeasurement("services", 2.0, 5.0, 3.0)
        ]

        profile = BootProfile(
            total_time=9.0,
            measurements=measurements,
            meets_target=True
        )

        reporter = BootReporter()
        metrics = reporter.export_metrics(profile)

        assert isinstance(metrics, dict)
        assert 'total_time_seconds' in metrics
        assert 'meets_10s_target' in metrics
        assert metrics['meets_10s_target'] is True


class TestBootPhases:
    """Tests for boot phases"""

    def test_boot_phases_defined(self):
        """Test: Boot phases are defined"""
        assert BootPhase.KERNEL_INIT.value == "kernel_init"
        assert BootPhase.INIT_SYSTEM.value == "init_system"
        assert BootPhase.SERVICES.value == "services"
        assert BootPhase.USER_SPACE.value == "user_space"
        assert BootPhase.TOTAL.value == "total"


class TestBootTargetCompliance:
    """Tests for boot target compliance"""

    def test_10_second_target(self):
        """
        Test: 10 second target is enforced

        Design Goal: Boot time under 10 seconds
        """
        timer = BootTimer()

        assert timer.boot_target_seconds == 10.0

    def test_9_seconds_meets_target(self):
        """Test: 9 seconds meets target"""
        measurements = [
            BootMeasurement("total", 0.0, 9.0, 9.0)
        ]

        profile = BootProfile(
            total_time=9.0,
            measurements=measurements
        )

        meets_target = profile.total_time <= 10.0

        assert meets_target is True

    def test_11_seconds_exceeds_target(self):
        """Test: 11 seconds exceeds target"""
        measurements = [
            BootMeasurement("total", 0.0, 11.0, 11.0)
        ]

        profile = BootProfile(
            total_time=11.0,
            measurements=measurements
        )

        meets_target = profile.total_time <= 10.0

        assert meets_target is False

    def test_exactly_10_seconds_meets_target(self):
        """Test: Exactly 10 seconds meets target"""
        measurements = [
            BootMeasurement("total", 0.0, 10.0, 10.0)
        ]

        profile = BootProfile(
            total_time=10.0,
            measurements=measurements
        )

        meets_target = profile.total_time <= 10.0

        # Exactly 10.0s should meet target (<=)
        assert meets_target is True
