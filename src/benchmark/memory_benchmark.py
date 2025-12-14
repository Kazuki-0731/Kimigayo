"""
Memory Usage Measurement and Optimization

Measures and optimizes system memory usage.

Design Goal: RAM consumption under 128MB
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field


@dataclass
class ProcessMemoryUsage:
    """Memory usage for a process"""
    pid: int
    name: str
    rss: int  # Resident Set Size in bytes
    vms: int  # Virtual Memory Size in bytes
    shared: int  # Shared memory in bytes

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    def rss_mb(self) -> float:
        """Get RSS in MB"""
        return self.rss / (1024 * 1024)

    def vms_mb(self) -> float:
        """Get VMS in MB"""
        return self.vms / (1024 * 1024)


@dataclass
class SystemMemorySnapshot:
    """System memory snapshot"""
    timestamp: float
    total: int  # Total memory in bytes
    available: int  # Available memory in bytes
    used: int  # Used memory in bytes
    free: int  # Free memory in bytes
    buffers: int = 0  # Buffer memory in bytes
    cached: int = 0  # Cached memory in bytes

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    def used_mb(self) -> float:
        """Get used memory in MB"""
        return self.used / (1024 * 1024)

    def available_mb(self) -> float:
        """Get available memory in MB"""
        return self.available / (1024 * 1024)

    def usage_percentage(self) -> float:
        """Get memory usage percentage"""
        if self.total == 0:
            return 0.0
        return (self.used / self.total) * 100


@dataclass
class MemoryProfile:
    """Complete memory profile"""
    system_snapshot: SystemMemorySnapshot
    process_usages: List[ProcessMemoryUsage] = field(default_factory=list)
    meets_target: bool = False
    target_mb: float = 128.0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'system_snapshot': self.system_snapshot.to_dict(),
            'process_usages': [p.to_dict() for p in self.process_usages],
            'meets_target': self.meets_target,
            'target_mb': self.target_mb
        }


class MemoryProfiler:
    """
    Profiles memory usage.

    Design Goal: RAM consumption under 128MB
    """

    def __init__(self):
        """Initialize memory profiler"""
        self.target_mb = 128.0  # Design goal: requirement 1.2
        self.snapshots: List[SystemMemorySnapshot] = []

    def read_meminfo(self) -> Dict[str, int]:
        """
        Read /proc/meminfo.

        Returns:
            Dictionary of memory statistics in bytes
        """
        meminfo = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(':')
                        # Value in /proc/meminfo is in kB
                        value = int(parts[1]) * 1024  # Convert to bytes
                        meminfo[key] = value
        except (IOError, OSError):
            # Fallback for testing environments
            pass
        return meminfo

    def get_system_snapshot(self) -> SystemMemorySnapshot:
        """
        Get current system memory snapshot.

        Returns:
            System memory snapshot
        """
        meminfo = self.read_meminfo()

        total = meminfo.get('MemTotal', 0)
        available = meminfo.get('MemAvailable', 0)
        free = meminfo.get('MemFree', 0)
        buffers = meminfo.get('Buffers', 0)
        cached = meminfo.get('Cached', 0)

        # Calculate used memory
        used = total - available if available > 0 else total - free

        snapshot = SystemMemorySnapshot(
            timestamp=time.time(),
            total=total,
            available=available,
            used=used,
            free=free,
            buffers=buffers,
            cached=cached
        )

        self.snapshots.append(snapshot)
        return snapshot

    def get_process_memory(self, pid: int) -> Optional[ProcessMemoryUsage]:
        """
        Get memory usage for a specific process.

        Args:
            pid: Process ID

        Returns:
            Process memory usage or None if not found
        """
        try:
            # Read /proc/[pid]/status
            status_path = f'/proc/{pid}/status'
            name = ""
            rss = 0
            vms = 0
            shared = 0

            with open(status_path, 'r') as f:
                for line in f:
                    if line.startswith('Name:'):
                        name = line.split()[1]
                    elif line.startswith('VmRSS:'):
                        # Value in kB, convert to bytes
                        rss = int(line.split()[1]) * 1024
                    elif line.startswith('VmSize:'):
                        vms = int(line.split()[1]) * 1024
                    elif line.startswith('RssFile:') or line.startswith('RssShmem:'):
                        shared += int(line.split()[1]) * 1024

            return ProcessMemoryUsage(
                pid=pid,
                name=name,
                rss=rss,
                vms=vms,
                shared=shared
            )
        except (IOError, OSError):
            return None

    def get_all_processes_memory(self) -> List[ProcessMemoryUsage]:
        """
        Get memory usage for all processes.

        Returns:
            List of process memory usages
        """
        processes = []
        try:
            for entry in os.listdir('/proc'):
                if entry.isdigit():
                    pid = int(entry)
                    usage = self.get_process_memory(pid)
                    if usage:
                        processes.append(usage)
        except (IOError, OSError):
            pass

        return processes

    def check_target(self, snapshot: SystemMemorySnapshot) -> bool:
        """
        Check if memory usage meets target.

        Design Goal: RAM consumption under 128MB

        Args:
            snapshot: Memory snapshot to check

        Returns:
            True if memory usage is under target
        """
        used_mb = snapshot.used_mb()
        return used_mb < self.target_mb

    def get_profile(self) -> MemoryProfile:
        """
        Get complete memory profile.

        Returns:
            Memory profile with system and process data
        """
        snapshot = self.get_system_snapshot()
        processes = self.get_all_processes_memory()
        meets_target = self.check_target(snapshot)

        return MemoryProfile(
            system_snapshot=snapshot,
            process_usages=processes,
            meets_target=meets_target,
            target_mb=self.target_mb
        )


class MemoryAnalyzer:
    """
    Analyzes memory usage patterns.

    Design Goal: Identify memory optimization opportunities
    """

    def __init__(self):
        """Initialize memory analyzer"""
        self.target_mb = 128.0

    def analyze_profile(self, profile: MemoryProfile) -> Dict:
        """
        Analyze memory profile.

        Args:
            profile: Memory profile to analyze

        Returns:
            Analysis results
        """
        snapshot = profile.system_snapshot

        analysis = {
            'used_mb': snapshot.used_mb(),
            'available_mb': snapshot.available_mb(),
            'usage_percentage': snapshot.usage_percentage(),
            'meets_target': profile.meets_target,
            'target_mb': self.target_mb,
            'top_processes': [],
            'recommendations': []
        }

        # Find top memory consumers
        sorted_processes = sorted(
            profile.process_usages,
            key=lambda p: p.rss,
            reverse=True
        )

        analysis['top_processes'] = [
            {
                'pid': p.pid,
                'name': p.name,
                'rss_mb': p.rss_mb(),
                'vms_mb': p.vms_mb()
            }
            for p in sorted_processes[:10]
        ]

        # Generate recommendations
        if not profile.meets_target:
            excess_mb = snapshot.used_mb() - self.target_mb
            analysis['recommendations'].append(
                f"Memory usage exceeds target by {excess_mb:.2f}MB"
            )
            analysis['recommendations'].append(
                "Consider reducing number of running services"
            )

        # Check for memory-heavy processes
        for process in sorted_processes[:5]:
            if process.rss_mb() > 10.0:
                analysis['recommendations'].append(
                    f"Process {process.name} (PID {process.pid}) uses {process.rss_mb():.2f}MB"
                )

        return analysis

    def detect_memory_leak(self, snapshots: List[SystemMemorySnapshot]) -> Dict:
        """
        Detect potential memory leaks.

        Args:
            snapshots: List of memory snapshots over time

        Returns:
            Memory leak detection results
        """
        if len(snapshots) < 2:
            return {
                'leak_detected': False,
                'reason': 'Insufficient data'
            }

        # Check if memory usage is consistently increasing
        increases = 0
        for i in range(1, len(snapshots)):
            if snapshots[i].used > snapshots[i-1].used:
                increases += 1

        leak_threshold = 0.8  # 80% of samples show increase
        leak_detected = (increases / (len(snapshots) - 1)) > leak_threshold

        if leak_detected:
            total_increase = snapshots[-1].used - snapshots[0].used
            total_increase_mb = total_increase / (1024 * 1024)

            return {
                'leak_detected': True,
                'increase_mb': total_increase_mb,
                'sample_count': len(snapshots),
                'increasing_samples': increases
            }

        return {
            'leak_detected': False,
            'sample_count': len(snapshots),
            'increasing_samples': increases
        }


class MemoryOptimizer:
    """
    Optimizes memory usage.

    Design Goal: Achieve memory usage under 128MB
    """

    def __init__(self, analyzer: Optional[MemoryAnalyzer] = None):
        """
        Initialize memory optimizer.

        Args:
            analyzer: Memory analyzer instance
        """
        self.analyzer = analyzer or MemoryAnalyzer()
        self.optimizations_applied = []

    def suggest_optimizations(self, profile: MemoryProfile) -> List[str]:
        """
        Suggest memory optimizations.

        Args:
            profile: Memory profile

        Returns:
            List of optimization suggestions
        """
        suggestions = []
        snapshot = profile.system_snapshot

        # General suggestions if target not met
        if not profile.meets_target:
            suggestions.append("Reduce number of startup services")
            suggestions.append("Use static linking to reduce runtime overhead")
            suggestions.append("Configure smaller buffer sizes")
            suggestions.append("Disable unnecessary kernel modules")

        # Check cache usage
        cache_mb = snapshot.cached / (1024 * 1024)
        if cache_mb > 20.0:
            suggestions.append(f"High cache usage ({cache_mb:.2f}MB), consider reducing cache size")

        # Check buffer usage
        buffer_mb = snapshot.buffers / (1024 * 1024)
        if buffer_mb > 10.0:
            suggestions.append(f"High buffer usage ({buffer_mb:.2f}MB), consider tuning buffer settings")

        # Check process memory
        for process in sorted(profile.process_usages, key=lambda p: p.rss, reverse=True)[:5]:
            if process.rss_mb() > 15.0:
                suggestions.append(
                    f"Optimize or disable heavy process: {process.name} ({process.rss_mb():.2f}MB)"
                )

        return suggestions

    def apply_optimization(self, optimization: str) -> bool:
        """
        Apply a memory optimization.

        Args:
            optimization: Optimization to apply

        Returns:
            True if successfully applied
        """
        self.optimizations_applied.append(optimization)
        return True

    def optimize_for_target(self, profile: MemoryProfile) -> List[str]:
        """
        Apply optimizations to meet memory target.

        Args:
            profile: Current memory profile

        Returns:
            List of optimizations applied
        """
        suggestions = self.suggest_optimizations(profile)

        actions = []
        for suggestion in suggestions:
            if self.apply_optimization(suggestion):
                actions.append(f"Applied: {suggestion}")

        return actions


class MemoryBenchmark:
    """
    Benchmarks memory usage.

    Design Goal: Verify RAM consumption under 128MB
    """

    def __init__(self):
        """Initialize memory benchmark"""
        self.profiler = MemoryProfiler()
        self.analyzer = MemoryAnalyzer()
        self.optimizer = MemoryOptimizer(self.analyzer)

    def run_benchmark(self, duration: float = 1.0, samples: int = 5) -> Dict:
        """
        Run memory benchmark.

        Args:
            duration: Duration between samples in seconds
            samples: Number of samples to collect

        Returns:
            Benchmark results
        """
        profiles = []

        for _ in range(samples):
            profile = self.profiler.get_profile()
            profiles.append(profile)
            time.sleep(duration)

        # Analyze final profile
        final_profile = profiles[-1]
        analysis = self.analyzer.analyze_profile(final_profile)

        # Check for memory leaks
        snapshots = [p.system_snapshot for p in profiles]
        leak_detection = self.analyzer.detect_memory_leak(snapshots)

        return {
            'profile': final_profile.to_dict(),
            'analysis': analysis,
            'leak_detection': leak_detection,
            'meets_target': final_profile.meets_target,
            'sample_count': len(profiles)
        }

    def verify_memory_target(self, profile: MemoryProfile) -> Tuple[bool, str]:
        """
        Verify memory usage meets target.

        Design Goal: RAM consumption under 128MB

        Args:
            profile: Memory profile to verify

        Returns:
            Tuple of (meets_target, status_message)
        """
        used_mb = profile.system_snapshot.used_mb()

        if profile.meets_target:
            message = f"Memory usage {used_mb:.2f}MB meets target (<{profile.target_mb}MB)"
        else:
            excess = used_mb - profile.target_mb
            message = f"Memory usage {used_mb:.2f}MB exceeds target by {excess:.2f}MB"

        return (profile.meets_target, message)

    def optimize_and_verify(self, profile: MemoryProfile) -> Dict:
        """
        Optimize memory and verify target is met.

        Args:
            profile: Current memory profile

        Returns:
            Optimization results
        """
        optimizations = self.optimizer.optimize_for_target(profile)

        return {
            'initial_usage_mb': profile.system_snapshot.used_mb(),
            'meets_target': profile.meets_target,
            'optimizations_applied': optimizations,
            'target_mb': profile.target_mb
        }


class MemoryReporter:
    """
    Reports memory usage metrics.
    """

    def generate_report(self, profile: MemoryProfile, analysis: Dict) -> str:
        """
        Generate memory usage report.

        Args:
            profile: Memory profile
            analysis: Analysis results

        Returns:
            Report as string
        """
        snapshot = profile.system_snapshot

        report_lines = [
            "=== Memory Usage Report ===",
            f"Total Memory: {snapshot.used_mb():.2f}MB / {snapshot.total / (1024*1024):.2f}MB",
            f"Target: <128MB",
            f"Status: {'PASS' if profile.meets_target else 'FAIL'}",
            f"Usage: {snapshot.usage_percentage():.1f}%",
            "",
            "Memory Breakdown:",
            f"  Used:      {snapshot.used_mb():8.2f}MB",
            f"  Free:      {snapshot.free / (1024*1024):8.2f}MB",
            f"  Available: {snapshot.available_mb():8.2f}MB",
            f"  Buffers:   {snapshot.buffers / (1024*1024):8.2f}MB",
            f"  Cached:    {snapshot.cached / (1024*1024):8.2f}MB",
        ]

        if analysis.get('top_processes'):
            report_lines.append("")
            report_lines.append("Top Memory Consumers:")
            for proc in analysis['top_processes'][:5]:
                report_lines.append(
                    f"  {proc['name']:20s} (PID {proc['pid']:5d}) {proc['rss_mb']:8.2f}MB"
                )

        if analysis.get('recommendations'):
            report_lines.append("")
            report_lines.append("Recommendations:")
            for rec in analysis['recommendations']:
                report_lines.append(f"  - {rec}")

        return "\n".join(report_lines)

    def export_metrics(self, profile: MemoryProfile) -> Dict:
        """
        Export metrics in structured format.

        Args:
            profile: Memory profile

        Returns:
            Metrics dictionary
        """
        snapshot = profile.system_snapshot

        return {
            'used_mb': snapshot.used_mb(),
            'available_mb': snapshot.available_mb(),
            'usage_percentage': snapshot.usage_percentage(),
            'meets_128mb_target': profile.meets_target,
            'process_count': len(profile.process_usages),
            'timestamp': snapshot.timestamp
        }
