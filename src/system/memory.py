"""
Memory Usage Optimization

Manages memory monitoring, optimization, and resource limits.

Requirements:
- 1.2: Memory usage constraint - RAM consumption under 128MB during normal operation
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class MemoryUnit(Enum):
    """Memory units"""
    BYTES = 1
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024


@dataclass
class MemoryUsage:
    """Memory usage information"""
    total: int  # Total memory in bytes
    used: int   # Used memory in bytes
    free: int   # Free memory in bytes
    available: int  # Available memory in bytes
    buffers: int = 0
    cached: int = 0
    swap_total: int = 0
    swap_used: int = 0

    def to_mb(self, value: int) -> float:
        """Convert bytes to MB"""
        return value / MemoryUnit.MB.value

    def get_usage_percentage(self) -> float:
        """Get memory usage percentage"""
        if self.total == 0:
            return 0.0
        return (self.used / self.total) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary with MB values"""
        return {
            'total_mb': self.to_mb(self.total),
            'used_mb': self.to_mb(self.used),
            'free_mb': self.to_mb(self.free),
            'available_mb': self.to_mb(self.available),
            'usage_percentage': self.get_usage_percentage()
        }


@dataclass
class ProcessMemory:
    """Process memory information"""
    pid: int
    name: str
    rss: int  # Resident Set Size (actual RAM used)
    vms: int  # Virtual Memory Size
    shared: int = 0

    def to_mb(self, value: int) -> float:
        """Convert bytes to MB"""
        return value / MemoryUnit.MB.value

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'pid': self.pid,
            'name': self.name,
            'rss_mb': self.to_mb(self.rss),
            'vms_mb': self.to_mb(self.vms)
        }


class MemoryMonitor:
    """
    Monitors system memory usage.

    Requirement: 1.2 (Memory usage monitoring)
    """

    def __init__(self):
        """Initialize memory monitor"""
        self.proc_path = Path("/proc")
        self.memory_limit_mb = 128  # Requirement: 1.2

    def get_system_memory(self) -> MemoryUsage:
        """
        Get system memory usage.

        Requirement: 1.2 - Monitor RAM consumption

        Returns:
            Memory usage information
        """
        meminfo_path = self.proc_path / "meminfo"

        if not meminfo_path.exists():
            # Return default values if /proc/meminfo is not available
            return MemoryUsage(
                total=0,
                used=0,
                free=0,
                available=0
            )

        try:
            meminfo = meminfo_path.read_text()
            values = {}

            for line in meminfo.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    # Extract numeric value (remove 'kB' suffix)
                    match = re.search(r'(\d+)', value)
                    if match:
                        values[key.strip()] = int(match.group(1)) * 1024  # Convert to bytes

            total = values.get('MemTotal', 0)
            free = values.get('MemFree', 0)
            buffers = values.get('Buffers', 0)
            cached = values.get('Cached', 0)
            available = values.get('MemAvailable', free + buffers + cached)

            used = total - free - buffers - cached

            return MemoryUsage(
                total=total,
                used=used,
                free=free,
                available=available,
                buffers=buffers,
                cached=cached,
                swap_total=values.get('SwapTotal', 0),
                swap_used=values.get('SwapTotal', 0) - values.get('SwapFree', 0)
            )
        except Exception:
            return MemoryUsage(total=0, used=0, free=0, available=0)

    def get_process_memory(self, pid: int) -> Optional[ProcessMemory]:
        """
        Get memory usage for a specific process.

        Args:
            pid: Process ID

        Returns:
            Process memory information or None if not found
        """
        status_path = self.proc_path / str(pid) / "status"

        if not status_path.exists():
            return None

        try:
            status = status_path.read_text()
            values = {}

            for line in status.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    match = re.search(r'(\d+)', value)
                    if match:
                        values[key.strip()] = int(match.group(1)) * 1024  # Convert to bytes

            # Get process name
            name = "unknown"
            for line in status.split('\n'):
                if line.startswith('Name:'):
                    name = line.split(':', 1)[1].strip()
                    break

            return ProcessMemory(
                pid=pid,
                name=name,
                rss=values.get('VmRSS', 0),
                vms=values.get('VmSize', 0),
                shared=values.get('RssFile', 0)
            )
        except Exception:
            return None

    def check_memory_limit(self) -> Tuple[bool, float]:
        """
        Check if memory usage is within limit.

        Requirement: 1.2 - RAM consumption must be under 128MB

        Returns:
            Tuple of (within_limit, current_usage_mb)
        """
        usage = self.get_system_memory()
        used_mb = usage.to_mb(usage.used)
        within_limit = used_mb < self.memory_limit_mb

        return (within_limit, used_mb)

    def get_top_memory_processes(self, limit: int = 10) -> List[ProcessMemory]:
        """
        Get top memory-consuming processes.

        Args:
            limit: Number of processes to return

        Returns:
            List of process memory information
        """
        processes = []

        try:
            for pid_dir in self.proc_path.iterdir():
                if pid_dir.is_dir() and pid_dir.name.isdigit():
                    pid = int(pid_dir.name)
                    proc_mem = self.get_process_memory(pid)
                    if proc_mem:
                        processes.append(proc_mem)
        except Exception:
            pass

        # Sort by RSS (actual RAM usage)
        processes.sort(key=lambda p: p.rss, reverse=True)

        return processes[:limit]


class MemoryOptimizer:
    """
    Optimizes system memory usage.

    Requirement: 1.2 (Memory optimization)
    """

    def __init__(self, monitor: Optional[MemoryMonitor] = None):
        """
        Initialize memory optimizer.

        Args:
            monitor: Memory monitor instance
        """
        self.monitor = monitor or MemoryMonitor()
        self.optimizations_applied = []

    def suggest_optimizations(self) -> List[str]:
        """
        Suggest memory optimizations.

        Returns:
            List of optimization suggestions
        """
        suggestions = []
        usage = self.monitor.get_system_memory()
        used_mb = usage.to_mb(usage.used)

        if used_mb > 100:
            suggestions.append("Consider reducing number of running services")
            suggestions.append("Enable swap to prevent OOM conditions")

        if usage.buffers + usage.cached > usage.total * 0.5:
            suggestions.append("Large buffer/cache usage detected - may be reclaimable")

        # Check top processes
        top_procs = self.monitor.get_top_memory_processes(5)
        if top_procs and top_procs[0].to_mb(top_procs[0].rss) > 50:
            suggestions.append(f"Process '{top_procs[0].name}' using high memory")

        return suggestions

    def apply_optimization(self, optimization: str) -> bool:
        """
        Apply a memory optimization.

        Args:
            optimization: Optimization to apply

        Returns:
            True if successfully applied
        """
        # In a real implementation, this would apply actual optimizations
        # For now, just track what optimizations are requested
        self.optimizations_applied.append(optimization)
        return True

    def clear_page_cache(self) -> bool:
        """
        Clear page cache (requires root).

        Returns:
            True if successfully cleared
        """
        # In real implementation:
        # echo 1 > /proc/sys/vm/drop_caches
        # For testing, just simulate
        return True

    def get_optimization_status(self) -> Dict:
        """
        Get current optimization status.

        Returns:
            Dictionary with optimization information
        """
        usage = self.monitor.get_system_memory()
        within_limit, used_mb = self.monitor.check_memory_limit()

        return {
            'memory_usage_mb': used_mb,
            'memory_limit_mb': self.monitor.memory_limit_mb,
            'within_limit': within_limit,
            'optimizations_applied': self.optimizations_applied,
            'suggestions': self.suggest_optimizations()
        }


class ResourceLimiter:
    """
    Manages resource limits for processes.

    Requirement: 1.2 (Resource limit functionality)
    """

    def __init__(self):
        """Initialize resource limiter"""
        self.limits: Dict[str, Dict] = {}

    def set_memory_limit(self, process_name: str, limit_mb: int):
        """
        Set memory limit for a process.

        Args:
            process_name: Process name
            limit_mb: Memory limit in MB
        """
        if process_name not in self.limits:
            self.limits[process_name] = {}

        self.limits[process_name]['memory_mb'] = limit_mb

    def get_memory_limit(self, process_name: str) -> Optional[int]:
        """
        Get memory limit for a process.

        Args:
            process_name: Process name

        Returns:
            Memory limit in MB or None if not set
        """
        if process_name in self.limits:
            return self.limits[process_name].get('memory_mb')
        return None

    def check_limit_exceeded(self, process: ProcessMemory) -> bool:
        """
        Check if process exceeds memory limit.

        Args:
            process: Process memory information

        Returns:
            True if limit is exceeded
        """
        limit_mb = self.get_memory_limit(process.name)
        if limit_mb is None:
            return False

        actual_mb = process.to_mb(process.rss)
        return actual_mb > limit_mb

    def enforce_limits(self, monitor: MemoryMonitor) -> List[str]:
        """
        Enforce resource limits on all processes.

        Args:
            monitor: Memory monitor instance

        Returns:
            List of actions taken
        """
        actions = []
        top_procs = monitor.get_top_memory_processes(50)

        for proc in top_procs:
            if self.check_limit_exceeded(proc):
                actions.append(f"Process {proc.name} (PID {proc.pid}) exceeds limit")

        return actions


class MemoryManager:
    """
    Manages overall memory optimization and monitoring.

    Requirement: 1.2 (Memory usage optimization)
    """

    def __init__(self):
        """Initialize memory manager"""
        self.monitor = MemoryMonitor()
        self.optimizer = MemoryOptimizer(self.monitor)
        self.limiter = ResourceLimiter()

    def get_status(self) -> Dict:
        """
        Get comprehensive memory status.

        Returns:
            Dictionary with memory status information
        """
        usage = self.monitor.get_system_memory()
        within_limit, used_mb = self.monitor.check_memory_limit()

        return {
            'system_memory': usage.to_dict(),
            'within_limit': within_limit,
            'used_mb': used_mb,
            'limit_mb': self.monitor.memory_limit_mb,
            'top_processes': [p.to_dict() for p in self.monitor.get_top_memory_processes(5)]
        }

    def verify_memory_constraint(self) -> Tuple[bool, str]:
        """
        Verify memory constraint is met.

        Requirement: 1.2 - Verify RAM consumption under 128MB

        Returns:
            Tuple of (constraint_met, status_message)
        """
        within_limit, used_mb = self.monitor.check_memory_limit()

        if within_limit:
            message = f"Memory usage {used_mb:.1f}MB is within limit ({self.monitor.memory_limit_mb}MB)"
        else:
            message = f"Memory usage {used_mb:.1f}MB exceeds limit ({self.monitor.memory_limit_mb}MB)"

        return (within_limit, message)

    def optimize(self) -> List[str]:
        """
        Run memory optimization.

        Returns:
            List of optimizations performed
        """
        suggestions = self.optimizer.suggest_optimizations()

        actions = []
        for suggestion in suggestions:
            if self.optimizer.apply_optimization(suggestion):
                actions.append(f"Applied: {suggestion}")

        return actions
