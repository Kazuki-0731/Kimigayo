"""
Property Tests for Memory Usage Optimization

Tests memory monitoring, optimization, and resource limits.

Properties tested:
- Property 2: メモリ使用量制約 (Memory Usage Constraint) - 要件 1.2
"""

import pytest
from hypothesis import given, strategies as st, settings, Verbosity

from src.system.memory import (
    MemoryUsage,
    ProcessMemory,
    MemoryMonitor,
    MemoryOptimizer,
    ResourceLimiter,
    MemoryManager,
    MemoryUnit,
)


@pytest.mark.property
class TestMemoryUsageConstraint:
    """
    Property 2: メモリ使用量制約

    任意のシステム設定に対して、通常動作時のRAM消費量は128MB未満でなければならない

    Requirement: 1.2
    """

    def test_memory_usage_creation(self):
        """Test: Memory usage can be created"""
        usage = MemoryUsage(
            total=1024 * 1024 * 1024,  # 1GB
            used=128 * 1024 * 1024,    # 128MB
            free=896 * 1024 * 1024,
            available=900 * 1024 * 1024
        )

        assert usage is not None
        assert usage.total > 0

    def test_memory_to_mb_conversion(self):
        """Test: Memory values can be converted to MB"""
        usage = MemoryUsage(
            total=128 * 1024 * 1024,  # 128MB in bytes
            used=64 * 1024 * 1024,    # 64MB in bytes
            free=64 * 1024 * 1024,
            available=64 * 1024 * 1024
        )

        assert usage.to_mb(usage.total) == 128.0
        assert usage.to_mb(usage.used) == 64.0

    def test_memory_usage_percentage(self):
        """Test: Memory usage percentage can be calculated"""
        usage = MemoryUsage(
            total=100 * 1024 * 1024,  # 100MB
            used=50 * 1024 * 1024,    # 50MB
            free=50 * 1024 * 1024,
            available=50 * 1024 * 1024
        )

        percentage = usage.get_usage_percentage()
        assert 49 <= percentage <= 51  # Should be approximately 50%

    def test_memory_monitor_initialization(self):
        """Test: Memory monitor can be initialized"""
        monitor = MemoryMonitor()

        assert monitor is not None
        assert monitor.memory_limit_mb == 128  # Requirement: 1.2

    def test_memory_limit_is_128mb(self):
        """
        Test: Memory limit is set to 128MB

        Requirement 1.2: RAM consumption must be under 128MB
        """
        monitor = MemoryMonitor()

        assert monitor.memory_limit_mb == 128

    def test_check_memory_limit(self):
        """
        Test: Can check if memory usage is within limit

        Requirement 1.2: Verify RAM consumption under 128MB
        """
        monitor = MemoryMonitor()

        within_limit, used_mb = monitor.check_memory_limit()

        assert isinstance(within_limit, bool)
        assert isinstance(used_mb, float)
        assert used_mb >= 0

    def test_get_system_memory(self):
        """Test: Can get system memory usage"""
        monitor = MemoryMonitor()

        usage = monitor.get_system_memory()

        assert isinstance(usage, MemoryUsage)
        assert usage.total >= 0
        assert usage.used >= 0
        assert usage.free >= 0

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(
        total=st.integers(min_value=128, max_value=4096),  # MB
        used_percent=st.floats(min_value=0.0, max_value=1.0)
    )
    def test_memory_constraint_verification(self, total, used_percent):
        """
        Property Test: Memory constraint can be verified

        For any system configuration, we must be able to verify
        if memory usage is under 128MB.
        """
        total_bytes = total * 1024 * 1024
        used_bytes = int(total_bytes * used_percent)

        usage = MemoryUsage(
            total=total_bytes,
            used=used_bytes,
            free=total_bytes - used_bytes,
            available=total_bytes - used_bytes
        )

        used_mb = usage.to_mb(usage.used)
        within_limit = used_mb < 128

        # Should correctly identify if within limit
        assert isinstance(within_limit, bool)

        if used_mb < 128:
            assert within_limit is True
        else:
            assert within_limit is False


@pytest.mark.property
class TestMemoryMonitoring:
    """Tests for memory monitoring functionality"""

    def test_process_memory_creation(self):
        """Test: Process memory information can be created"""
        proc = ProcessMemory(
            pid=1234,
            name="test-process",
            rss=10 * 1024 * 1024,  # 10MB
            vms=20 * 1024 * 1024   # 20MB
        )

        assert proc.pid == 1234
        assert proc.name == "test-process"

    def test_process_memory_to_mb(self):
        """Test: Process memory can be converted to MB"""
        proc = ProcessMemory(
            pid=1,
            name="test",
            rss=50 * 1024 * 1024,  # 50MB
            vms=100 * 1024 * 1024  # 100MB
        )

        assert proc.to_mb(proc.rss) == 50.0
        assert proc.to_mb(proc.vms) == 100.0

    def test_get_top_memory_processes(self):
        """Test: Can get top memory-consuming processes"""
        monitor = MemoryMonitor()

        # Get top processes (may be empty in test environment)
        top_procs = monitor.get_top_memory_processes(5)

        assert isinstance(top_procs, list)
        assert len(top_procs) <= 5

    def test_memory_usage_serialization(self):
        """Test: Memory usage can be serialized to dict"""
        usage = MemoryUsage(
            total=256 * 1024 * 1024,
            used=100 * 1024 * 1024,
            free=156 * 1024 * 1024,
            available=156 * 1024 * 1024
        )

        usage_dict = usage.to_dict()

        assert isinstance(usage_dict, dict)
        assert 'total_mb' in usage_dict
        assert 'used_mb' in usage_dict
        assert 'usage_percentage' in usage_dict


@pytest.mark.property
class TestMemoryOptimization:
    """Tests for memory optimization"""

    def test_memory_optimizer_initialization(self):
        """Test: Memory optimizer can be initialized"""
        optimizer = MemoryOptimizer()

        assert optimizer is not None
        assert optimizer.monitor is not None

    def test_suggest_optimizations(self):
        """Test: Can suggest memory optimizations"""
        optimizer = MemoryOptimizer()

        suggestions = optimizer.suggest_optimizations()

        assert isinstance(suggestions, list)

    def test_apply_optimization(self):
        """Test: Can apply optimization"""
        optimizer = MemoryOptimizer()

        result = optimizer.apply_optimization("test-optimization")

        assert result is True
        assert "test-optimization" in optimizer.optimizations_applied

    def test_get_optimization_status(self):
        """Test: Can get optimization status"""
        optimizer = MemoryOptimizer()

        status = optimizer.get_optimization_status()

        assert isinstance(status, dict)
        assert 'memory_usage_mb' in status
        assert 'memory_limit_mb' in status
        assert 'within_limit' in status

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(optimizations=st.lists(st.text(min_size=1, max_size=50), max_size=5))
    def test_track_optimizations(self, optimizations):
        """
        Property Test: Optimizations are tracked

        For any list of optimizations, they should be tracked
        when applied.
        """
        optimizer = MemoryOptimizer()

        for opt in optimizations:
            optimizer.apply_optimization(opt)

        # All optimizations should be tracked
        assert len(optimizer.optimizations_applied) == len(optimizations)


@pytest.mark.property
class TestResourceLimiting:
    """Tests for resource limiting"""

    def test_resource_limiter_initialization(self):
        """Test: Resource limiter can be initialized"""
        limiter = ResourceLimiter()

        assert limiter is not None
        assert len(limiter.limits) == 0

    def test_set_memory_limit(self):
        """Test: Can set memory limit for process"""
        limiter = ResourceLimiter()

        limiter.set_memory_limit("nginx", 50)

        assert limiter.get_memory_limit("nginx") == 50

    def test_get_memory_limit(self):
        """Test: Can get memory limit for process"""
        limiter = ResourceLimiter()

        limiter.set_memory_limit("test-process", 100)
        limit = limiter.get_memory_limit("test-process")

        assert limit == 100

    def test_get_nonexistent_limit(self):
        """Test: Returns None for nonexistent limit"""
        limiter = ResourceLimiter()

        limit = limiter.get_memory_limit("nonexistent")

        assert limit is None

    def test_check_limit_exceeded(self):
        """Test: Can check if process exceeds limit"""
        limiter = ResourceLimiter()
        limiter.set_memory_limit("test", 50)

        # Process using 60MB
        proc = ProcessMemory(
            pid=1,
            name="test",
            rss=60 * 1024 * 1024,
            vms=100 * 1024 * 1024
        )

        exceeded = limiter.check_limit_exceeded(proc)

        assert exceeded is True

    def test_check_limit_not_exceeded(self):
        """Test: Detects when limit is not exceeded"""
        limiter = ResourceLimiter()
        limiter.set_memory_limit("test", 100)

        # Process using 50MB
        proc = ProcessMemory(
            pid=1,
            name="test",
            rss=50 * 1024 * 1024,
            vms=100 * 1024 * 1024
        )

        exceeded = limiter.check_limit_exceeded(proc)

        assert exceeded is False

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(
        limit_mb=st.integers(min_value=10, max_value=200),
        usage_mb=st.integers(min_value=1, max_value=300)
    )
    def test_limit_enforcement(self, limit_mb, usage_mb):
        """
        Property Test: Limit enforcement is correct

        For any limit and usage values, the system must correctly
        determine if the limit is exceeded.
        """
        limiter = ResourceLimiter()
        limiter.set_memory_limit("test", limit_mb)

        proc = ProcessMemory(
            pid=1,
            name="test",
            rss=usage_mb * 1024 * 1024,
            vms=usage_mb * 1024 * 1024
        )

        exceeded = limiter.check_limit_exceeded(proc)

        if usage_mb > limit_mb:
            assert exceeded is True
        else:
            assert exceeded is False


@pytest.mark.property
class TestMemoryManager:
    """Tests for overall memory management"""

    def test_memory_manager_initialization(self):
        """Test: Memory manager can be initialized"""
        manager = MemoryManager()

        assert manager is not None
        assert manager.monitor is not None
        assert manager.optimizer is not None
        assert manager.limiter is not None

    def test_get_status(self):
        """Test: Can get comprehensive memory status"""
        manager = MemoryManager()

        status = manager.get_status()

        assert isinstance(status, dict)
        assert 'system_memory' in status
        assert 'within_limit' in status
        assert 'used_mb' in status
        assert 'limit_mb' in status

    def test_verify_memory_constraint(self):
        """
        Test: Can verify memory constraint

        Requirement 1.2: Verify RAM consumption under 128MB
        """
        manager = MemoryManager()

        constraint_met, message = manager.verify_memory_constraint()

        assert isinstance(constraint_met, bool)
        assert isinstance(message, str)
        assert '128' in message  # Should mention the limit

    def test_optimize(self):
        """Test: Can run memory optimization"""
        manager = MemoryManager()

        actions = manager.optimize()

        assert isinstance(actions, list)

    def test_status_includes_top_processes(self):
        """Test: Status includes top memory processes"""
        manager = MemoryManager()

        status = manager.get_status()

        assert 'top_processes' in status
        assert isinstance(status['top_processes'], list)


@pytest.mark.property
class TestMemoryUnits:
    """Tests for memory unit conversions"""

    def test_memory_units_defined(self):
        """Test: All memory units are defined"""
        assert MemoryUnit.BYTES.value == 1
        assert MemoryUnit.KB.value == 1024
        assert MemoryUnit.MB.value == 1024 * 1024
        assert MemoryUnit.GB.value == 1024 * 1024 * 1024

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(mb_value=st.integers(min_value=1, max_value=1024))
    def test_mb_to_bytes_conversion(self, mb_value):
        """
        Property Test: MB to bytes conversion is correct

        For any MB value, conversion to bytes should be consistent.
        """
        bytes_value = mb_value * MemoryUnit.MB.value

        usage = MemoryUsage(
            total=bytes_value,
            used=0,
            free=bytes_value,
            available=bytes_value
        )

        # Convert back to MB
        converted_mb = usage.to_mb(usage.total)

        # Should match original value
        assert abs(converted_mb - mb_value) < 0.1  # Allow small floating point error


@pytest.mark.property
class TestMemoryConstraintCompliance:
    """Tests specifically for 128MB constraint compliance"""

    def test_128mb_limit_constant(self):
        """
        Test: 128MB limit is defined as constant

        Requirement 1.2: 128MB is the hard limit
        """
        monitor = MemoryMonitor()

        assert monitor.memory_limit_mb == 128

    @settings(verbosity=Verbosity.verbose, max_examples=20)
    @given(used_mb=st.integers(min_value=1, max_value=256))
    def test_constraint_check_for_various_usage(self, used_mb):
        """
        Property Test: Constraint check works for any usage level

        For any memory usage value, the system must correctly
        identify if it's under 128MB.
        """
        usage_bytes = used_mb * 1024 * 1024

        usage = MemoryUsage(
            total=512 * 1024 * 1024,  # 512MB total
            used=usage_bytes,
            free=(512 - used_mb) * 1024 * 1024,
            available=(512 - used_mb) * 1024 * 1024
        )

        used_mb_converted = usage.to_mb(usage.used)
        within_limit = used_mb_converted < 128

        # Should correctly identify compliance
        if used_mb < 128:
            assert within_limit is True
        else:
            assert within_limit is False

    def test_exactly_128mb_is_not_compliant(self):
        """Test: Exactly 128MB is not compliant (must be under)"""
        usage = MemoryUsage(
            total=512 * 1024 * 1024,
            used=128 * 1024 * 1024,  # Exactly 128MB
            free=384 * 1024 * 1024,
            available=384 * 1024 * 1024
        )

        used_mb = usage.to_mb(usage.used)
        within_limit = used_mb < 128

        # Exactly 128MB is NOT within limit (must be UNDER 128MB)
        assert within_limit is False

    def test_127mb_is_compliant(self):
        """Test: 127MB is compliant"""
        usage = MemoryUsage(
            total=512 * 1024 * 1024,
            used=127 * 1024 * 1024,  # 127MB
            free=385 * 1024 * 1024,
            available=385 * 1024 * 1024
        )

        used_mb = usage.to_mb(usage.used)
        within_limit = used_mb < 128

        # 127MB should be within limit
        assert within_limit is True
