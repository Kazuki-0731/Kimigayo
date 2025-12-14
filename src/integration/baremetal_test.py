"""
Bare Metal (Physical Hardware) Testing

Tests for physical hardware deployment verification.

Target Environments:
- x86_64 bare metal servers
- ARM64 devices
- Embedded devices
- IoT devices
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


class Architecture(Enum):
    """Hardware architecture types"""
    X86_64 = "x86_64"
    ARM64 = "aarch64"
    ARM32 = "armv7l"
    RISCV = "riscv64"
    UNKNOWN = "unknown"


class HardwareType(Enum):
    """Hardware type categories"""
    SERVER = "server"
    EMBEDDED = "embedded"
    IOT = "iot"
    DESKTOP = "desktop"
    UNKNOWN = "unknown"


@dataclass
class HardwareInfo:
    """Hardware information"""
    architecture: str
    cpu_model: str
    cpu_count: int
    total_memory_mb: int
    platform_system: str

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class BaremetalTestResult:
    """Bare metal test result"""
    test_name: str
    passed: bool
    message: str
    duration: float = 0.0
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class HardwareDetector:
    """
    Detects hardware information.

    Requirement 5.1: Support x86_64 and ARM64
    """

    def __init__(self):
        """Initialize hardware detector"""
        pass

    def get_architecture(self) -> Architecture:
        """
        Get system architecture.

        Returns:
            Architecture enum
        """
        machine = platform.machine().lower()

        if machine in ['x86_64', 'amd64']:
            return Architecture.X86_64
        elif machine in ['aarch64', 'arm64']:
            return Architecture.ARM64
        elif machine in ['armv7l', 'armv7']:
            return Architecture.ARM32
        elif 'riscv' in machine:
            return Architecture.RISCV
        else:
            return Architecture.UNKNOWN

    def get_cpu_info(self) -> Dict:
        """
        Get CPU information.

        Returns:
            Dictionary with CPU details
        """
        cpu_info = {
            'model': 'Unknown',
            'count': os.cpu_count() or 1,
            'architecture': platform.machine()
        }

        try:
            # Try to get CPU model from /proc/cpuinfo (Linux)
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            cpu_info['model'] = line.split(':')[1].strip()
                            break
                        elif line.startswith('Model'):
                            cpu_info['model'] = line.split(':')[1].strip()
                            break
        except (IOError, OSError):
            pass

        return cpu_info

    def get_memory_info(self) -> Dict:
        """
        Get memory information.

        Returns:
            Dictionary with memory details
        """
        memory_info = {
            'total_mb': 0,
            'available_mb': 0
        }

        try:
            # Try to get memory from /proc/meminfo (Linux)
            if os.path.exists('/proc/meminfo'):
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal'):
                            # Value in kB
                            total_kb = int(line.split()[1])
                            memory_info['total_mb'] = total_kb // 1024
                        elif line.startswith('MemAvailable'):
                            avail_kb = int(line.split()[1])
                            memory_info['available_mb'] = avail_kb // 1024
        except (IOError, OSError, ValueError):
            pass

        return memory_info

    def get_hardware_info(self) -> HardwareInfo:
        """
        Get complete hardware information.

        Returns:
            Hardware information
        """
        arch = self.get_architecture()
        cpu_info = self.get_cpu_info()
        memory_info = self.get_memory_info()

        return HardwareInfo(
            architecture=arch.value,
            cpu_model=cpu_info['model'],
            cpu_count=cpu_info['count'],
            total_memory_mb=memory_info['total_mb'],
            platform_system=platform.system()
        )


class ArchitectureTester:
    """
    Tests architecture-specific functionality.

    Requirement 5.1: Support x86_64 and ARM64
    """

    def __init__(self):
        """Initialize architecture tester"""
        self.detector = HardwareDetector()

    def test_x86_64_support(self) -> BaremetalTestResult:
        """
        Test x86_64 architecture support.

        Requirement 5.1: x86_64 support

        Returns:
            Test result
        """
        import time
        start_time = time.time()
        test_name = "x86_64 Architecture Support"

        arch = self.detector.get_architecture()

        if arch == Architecture.X86_64:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=True,
                message="Running on x86_64 architecture",
                duration=duration,
                details={'architecture': arch.value}
            )
        else:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=False,
                message=f"Not running on x86_64 (detected: {arch.value})",
                duration=duration,
                details={'architecture': arch.value}
            )

    def test_arm64_support(self) -> BaremetalTestResult:
        """
        Test ARM64 architecture support.

        Requirement 5.1: ARM64 support

        Returns:
            Test result
        """
        import time
        start_time = time.time()
        test_name = "ARM64 Architecture Support"

        arch = self.detector.get_architecture()

        if arch == Architecture.ARM64:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=True,
                message="Running on ARM64 architecture",
                duration=duration,
                details={'architecture': arch.value}
            )
        else:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=False,
                message=f"Not running on ARM64 (detected: {arch.value})",
                duration=duration,
                details={'architecture': arch.value}
            )

    def test_architecture_detection(self) -> BaremetalTestResult:
        """
        Test architecture detection.

        Returns:
            Test result
        """
        import time
        start_time = time.time()
        test_name = "Architecture Detection"

        arch = self.detector.get_architecture()

        # Architecture detection succeeds if it's not UNKNOWN
        if arch != Architecture.UNKNOWN:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=True,
                message=f"Detected architecture: {arch.value}",
                duration=duration,
                details={'architecture': arch.value}
            )
        else:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=False,
                message="Failed to detect architecture",
                duration=duration
            )


class HardwareCompatibilityTester:
    """
    Tests hardware compatibility.

    Target Environment: Bare metal servers, embedded devices, IoT devices
    """

    def __init__(self):
        """Initialize hardware compatibility tester"""
        self.detector = HardwareDetector()

    def test_minimum_memory(self, minimum_mb: int = 128) -> BaremetalTestResult:
        """
        Test minimum memory requirement.

        Args:
            minimum_mb: Minimum required memory in MB

        Returns:
            Test result
        """
        import time
        start_time = time.time()
        test_name = "Minimum Memory Requirement"

        memory_info = self.detector.get_memory_info()
        total_mb = memory_info['total_mb']

        if total_mb >= minimum_mb:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=True,
                message=f"System has {total_mb}MB RAM (minimum: {minimum_mb}MB)",
                duration=duration,
                details={'total_mb': total_mb, 'minimum_mb': minimum_mb}
            )
        else:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=False,
                message=f"Insufficient RAM: {total_mb}MB (minimum: {minimum_mb}MB)",
                duration=duration,
                details={'total_mb': total_mb, 'minimum_mb': minimum_mb}
            )

    def test_cpu_count(self, minimum_cpus: int = 1) -> BaremetalTestResult:
        """
        Test CPU count.

        Args:
            minimum_cpus: Minimum required CPUs

        Returns:
            Test result
        """
        import time
        start_time = time.time()
        test_name = "CPU Count Test"

        cpu_info = self.detector.get_cpu_info()
        cpu_count = cpu_info['count']

        if cpu_count >= minimum_cpus:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=True,
                message=f"System has {cpu_count} CPU(s) (minimum: {minimum_cpus})",
                duration=duration,
                details={'cpu_count': cpu_count, 'minimum_cpus': minimum_cpus}
            )
        else:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=False,
                message=f"Insufficient CPUs: {cpu_count} (minimum: {minimum_cpus})",
                duration=duration,
                details={'cpu_count': cpu_count, 'minimum_cpus': minimum_cpus}
            )

    def test_platform_compatibility(self) -> BaremetalTestResult:
        """
        Test platform compatibility.

        Returns:
            Test result
        """
        import time
        start_time = time.time()
        test_name = "Platform Compatibility"

        platform_system = platform.system()
        supported_platforms = ['Linux', 'Darwin']  # Darwin for testing on macOS

        if platform_system in supported_platforms:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=True,
                message=f"Platform {platform_system} is supported",
                duration=duration,
                details={'platform': platform_system}
            )
        else:
            duration = time.time() - start_time
            return BaremetalTestResult(
                test_name=test_name,
                passed=False,
                message=f"Platform {platform_system} is not supported",
                duration=duration,
                details={'platform': platform_system}
            )


class BaremetalEnvironmentBenchmark:
    """
    Benchmarks bare metal environment functionality.

    Target Environment: Bare metal servers, embedded devices, IoT
    Requirement 5.1: x86_64 and ARM64 support
    """

    def __init__(self):
        """Initialize bare metal environment benchmark"""
        self.detector = HardwareDetector()
        self.arch_tester = ArchitectureTester()
        self.compat_tester = HardwareCompatibilityTester()

    def run_architecture_tests(self) -> Dict:
        """
        Run architecture tests.

        Returns:
            Test results
        """
        results = {
            'current_architecture': self.detector.get_architecture().value,
            'tests': []
        }

        # Run architecture detection test
        detection_result = self.arch_tester.test_architecture_detection()
        results['tests'].append(detection_result.to_dict())

        # Run specific architecture tests based on current platform
        arch = self.detector.get_architecture()
        if arch == Architecture.X86_64:
            x86_result = self.arch_tester.test_x86_64_support()
            results['tests'].append(x86_result.to_dict())
        elif arch == Architecture.ARM64:
            arm_result = self.arch_tester.test_arm64_support()
            results['tests'].append(arm_result.to_dict())

        return results

    def run_hardware_tests(self) -> Dict:
        """
        Run hardware compatibility tests.

        Returns:
            Test results
        """
        hw_info = self.detector.get_hardware_info()

        results = {
            'hardware_info': hw_info.to_dict(),
            'tests': []
        }

        # Test minimum memory
        memory_result = self.compat_tester.test_minimum_memory(128)
        results['tests'].append(memory_result.to_dict())

        # Test CPU count
        cpu_result = self.compat_tester.test_cpu_count(1)
        results['tests'].append(cpu_result.to_dict())

        # Test platform compatibility
        platform_result = self.compat_tester.test_platform_compatibility()
        results['tests'].append(platform_result.to_dict())

        return results

    def run_all_tests(self) -> Dict:
        """
        Run all bare metal tests.

        Returns:
            Complete test results
        """
        return {
            'architecture': self.run_architecture_tests(),
            'hardware': self.run_hardware_tests()
        }


class BaremetalTestReporter:
    """
    Reports bare metal test results.
    """

    def generate_report(self, results: Dict) -> str:
        """
        Generate bare metal test report.

        Args:
            results: Test results

        Returns:
            Report as string
        """
        report_lines = [
            "=== Bare Metal Environment Test Report ==="
        ]

        # Architecture results
        if 'architecture' in results:
            arch = results['architecture']
            report_lines.append("")
            report_lines.append("Architecture:")
            report_lines.append(f"  Current: {arch['current_architecture']}")

            if arch['tests']:
                report_lines.append("  Tests:")
                for test in arch['tests']:
                    status = "PASS" if test['passed'] else "FAIL"
                    report_lines.append(f"    [{status}] {test['test_name']} ({test['duration']:.2f}s)")

        # Hardware results
        if 'hardware' in results:
            hw = results['hardware']
            if 'hardware_info' in hw:
                info = hw['hardware_info']
                report_lines.append("")
                report_lines.append("Hardware Information:")
                report_lines.append(f"  Architecture: {info['architecture']}")
                report_lines.append(f"  CPU Model: {info['cpu_model']}")
                report_lines.append(f"  CPU Count: {info['cpu_count']}")
                report_lines.append(f"  Total Memory: {info['total_memory_mb']}MB")
                report_lines.append(f"  Platform: {info['platform_system']}")

            if hw['tests']:
                report_lines.append("")
                report_lines.append("  Hardware Tests:")
                for test in hw['tests']:
                    status = "PASS" if test['passed'] else "FAIL"
                    report_lines.append(f"    [{status}] {test['test_name']} ({test['duration']:.2f}s)")

        return "\n".join(report_lines)

    def export_metrics(self, results: Dict) -> Dict:
        """
        Export metrics in structured format.

        Args:
            results: Test results

        Returns:
            Metrics dictionary
        """
        metrics = {}

        if 'architecture' in results:
            arch = results['architecture']
            metrics['architecture'] = arch['current_architecture']
            metrics['arch_tests_passed'] = sum(
                1 for t in arch.get('tests', []) if t['passed']
            )
            metrics['arch_tests_total'] = len(arch.get('tests', []))

        if 'hardware' in results:
            hw = results['hardware']
            if 'hardware_info' in hw:
                info = hw['hardware_info']
                metrics['cpu_count'] = info['cpu_count']
                metrics['total_memory_mb'] = info['total_memory_mb']

            metrics['hw_tests_passed'] = sum(
                1 for t in hw.get('tests', []) if t['passed']
            )
            metrics['hw_tests_total'] = len(hw.get('tests', []))

        return metrics
