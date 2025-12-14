"""
Integration Tests for Bare Metal Environment

Tests physical hardware deployment functionality.

Target Environments:
- x86_64 bare metal
- ARM64 devices
"""

import pytest
import platform
from unittest.mock import Mock, patch, mock_open

from src.integration.baremetal_test import (
    Architecture,
    HardwareType,
    HardwareInfo,
    BaremetalTestResult,
    HardwareDetector,
    ArchitectureTester,
    HardwareCompatibilityTester,
    BaremetalEnvironmentBenchmark,
    BaremetalTestReporter,
)


class TestArchitecture:
    """Tests for architecture enum"""

    def test_x86_64_architecture(self):
        """Test: x86_64 architecture is defined"""
        assert Architecture.X86_64.value == "x86_64"

    def test_arm64_architecture(self):
        """Test: ARM64 architecture is defined"""
        assert Architecture.ARM64.value == "aarch64"

    def test_arm32_architecture(self):
        """Test: ARM32 architecture is defined"""
        assert Architecture.ARM32.value == "armv7l"

    def test_riscv_architecture(self):
        """Test: RISC-V architecture is defined"""
        assert Architecture.RISCV.value == "riscv64"


class TestHardwareType:
    """Tests for hardware type enum"""

    def test_server_type(self):
        """Test: Server hardware type is defined"""
        assert HardwareType.SERVER.value == "server"

    def test_embedded_type(self):
        """Test: Embedded hardware type is defined"""
        assert HardwareType.EMBEDDED.value == "embedded"

    def test_iot_type(self):
        """Test: IoT hardware type is defined"""
        assert HardwareType.IOT.value == "iot"


class TestHardwareInfo:
    """Tests for hardware info data structure"""

    def test_hardware_info_creation(self):
        """Test: Hardware info can be created"""
        info = HardwareInfo(
            architecture="x86_64",
            cpu_model="Intel Core i7",
            cpu_count=8,
            total_memory_mb=16384,
            platform_system="Linux"
        )

        assert info.architecture == "x86_64"
        assert info.cpu_count == 8
        assert info.total_memory_mb == 16384

    def test_to_dict(self):
        """Test: Can convert to dictionary"""
        info = HardwareInfo(
            architecture="aarch64",
            cpu_model="ARM Cortex",
            cpu_count=4,
            total_memory_mb=8192,
            platform_system="Linux"
        )

        info_dict = info.to_dict()

        assert isinstance(info_dict, dict)
        assert info_dict['architecture'] == "aarch64"
        assert info_dict['cpu_count'] == 4


class TestBaremetalTestResult:
    """Tests for bare metal test result"""

    def test_result_creation(self):
        """Test: Test result can be created"""
        result = BaremetalTestResult(
            test_name="Hardware Test",
            passed=True,
            message="Test passed",
            duration=1.0
        )

        assert result.test_name == "Hardware Test"
        assert result.passed is True
        assert result.duration == 1.0

    def test_result_with_details(self):
        """Test: Result can contain details"""
        result = BaremetalTestResult(
            test_name="Test",
            passed=True,
            message="OK",
            details={'architecture': 'x86_64'}
        )

        assert 'architecture' in result.details


class TestHardwareDetector:
    """Tests for hardware detector"""

    def test_detector_initialization(self):
        """Test: Hardware detector can be initialized"""
        detector = HardwareDetector()

        assert detector is not None

    @patch('platform.machine')
    def test_get_architecture_x86_64(self, mock_machine):
        """Test: Detects x86_64 architecture"""
        mock_machine.return_value = "x86_64"

        detector = HardwareDetector()
        arch = detector.get_architecture()

        assert arch == Architecture.X86_64

    @patch('platform.machine')
    def test_get_architecture_amd64(self, mock_machine):
        """Test: Detects AMD64 as x86_64"""
        mock_machine.return_value = "amd64"

        detector = HardwareDetector()
        arch = detector.get_architecture()

        assert arch == Architecture.X86_64

    @patch('platform.machine')
    def test_get_architecture_arm64(self, mock_machine):
        """Test: Detects ARM64 architecture"""
        mock_machine.return_value = "aarch64"

        detector = HardwareDetector()
        arch = detector.get_architecture()

        assert arch == Architecture.ARM64

    @patch('platform.machine')
    def test_get_architecture_arm32(self, mock_machine):
        """Test: Detects ARM32 architecture"""
        mock_machine.return_value = "armv7l"

        detector = HardwareDetector()
        arch = detector.get_architecture()

        assert arch == Architecture.ARM32

    @patch('platform.machine')
    def test_get_architecture_unknown(self, mock_machine):
        """Test: Returns UNKNOWN for unrecognized architecture"""
        mock_machine.return_value = "unknown-arch"

        detector = HardwareDetector()
        arch = detector.get_architecture()

        assert arch == Architecture.UNKNOWN

    @patch('os.cpu_count')
    @patch('builtins.open', new_callable=mock_open, read_data="model name\t: Intel Core i7-9700K\n")
    def test_get_cpu_info(self, mock_file, mock_cpu_count):
        """Test: Can get CPU information"""
        mock_cpu_count.return_value = 8

        detector = HardwareDetector()
        cpu_info = detector.get_cpu_info()

        assert cpu_info['count'] == 8
        assert 'Intel Core i7-9700K' in cpu_info['model']

    @patch('builtins.open', new_callable=mock_open, read_data="MemTotal:       16384000 kB\nMemAvailable:   8192000 kB\n")
    def test_get_memory_info(self, mock_file):
        """Test: Can get memory information"""
        detector = HardwareDetector()
        memory_info = detector.get_memory_info()

        assert memory_info['total_mb'] == 16000  # 16384000 / 1024
        assert memory_info['available_mb'] == 8000  # 8192000 / 1024

    @patch.object(HardwareDetector, 'get_architecture')
    @patch.object(HardwareDetector, 'get_cpu_info')
    @patch.object(HardwareDetector, 'get_memory_info')
    @patch('platform.system')
    def test_get_hardware_info(self, mock_system, mock_memory, mock_cpu, mock_arch):
        """Test: Can get complete hardware information"""
        mock_arch.return_value = Architecture.X86_64
        mock_cpu.return_value = {'model': 'Intel i7', 'count': 8}
        mock_memory.return_value = {'total_mb': 16384, 'available_mb': 8192}
        mock_system.return_value = "Linux"

        detector = HardwareDetector()
        hw_info = detector.get_hardware_info()

        assert isinstance(hw_info, HardwareInfo)
        assert hw_info.architecture == "x86_64"
        assert hw_info.cpu_count == 8
        assert hw_info.total_memory_mb == 16384


class TestArchitectureTester:
    """Tests for architecture tester"""

    def test_tester_initialization(self):
        """Test: Architecture tester can be initialized"""
        tester = ArchitectureTester()

        assert tester is not None
        assert tester.detector is not None

    @patch.object(HardwareDetector, 'get_architecture')
    def test_test_x86_64_support_pass(self, mock_arch):
        """Test: x86_64 support test passes on x86_64"""
        mock_arch.return_value = Architecture.X86_64

        tester = ArchitectureTester()
        result = tester.test_x86_64_support()

        assert result.passed is True
        assert "x86_64" in result.message

    @patch.object(HardwareDetector, 'get_architecture')
    def test_test_x86_64_support_fail(self, mock_arch):
        """Test: x86_64 support test fails on non-x86_64"""
        mock_arch.return_value = Architecture.ARM64

        tester = ArchitectureTester()
        result = tester.test_x86_64_support()

        assert result.passed is False

    @patch.object(HardwareDetector, 'get_architecture')
    def test_test_arm64_support_pass(self, mock_arch):
        """Test: ARM64 support test passes on ARM64"""
        mock_arch.return_value = Architecture.ARM64

        tester = ArchitectureTester()
        result = tester.test_arm64_support()

        assert result.passed is True
        assert "ARM64" in result.message

    @patch.object(HardwareDetector, 'get_architecture')
    def test_test_arm64_support_fail(self, mock_arch):
        """Test: ARM64 support test fails on non-ARM64"""
        mock_arch.return_value = Architecture.X86_64

        tester = ArchitectureTester()
        result = tester.test_arm64_support()

        assert result.passed is False

    @patch.object(HardwareDetector, 'get_architecture')
    def test_test_architecture_detection_success(self, mock_arch):
        """Test: Architecture detection succeeds"""
        mock_arch.return_value = Architecture.X86_64

        tester = ArchitectureTester()
        result = tester.test_architecture_detection()

        assert result.passed is True

    @patch.object(HardwareDetector, 'get_architecture')
    def test_test_architecture_detection_failure(self, mock_arch):
        """Test: Architecture detection fails for UNKNOWN"""
        mock_arch.return_value = Architecture.UNKNOWN

        tester = ArchitectureTester()
        result = tester.test_architecture_detection()

        assert result.passed is False


class TestHardwareCompatibilityTester:
    """Tests for hardware compatibility tester"""

    def test_tester_initialization(self):
        """Test: Hardware compatibility tester can be initialized"""
        tester = HardwareCompatibilityTester()

        assert tester is not None
        assert tester.detector is not None

    @patch.object(HardwareDetector, 'get_memory_info')
    def test_test_minimum_memory_pass(self, mock_memory):
        """Test: Minimum memory test passes"""
        mock_memory.return_value = {'total_mb': 512, 'available_mb': 256}

        tester = HardwareCompatibilityTester()
        result = tester.test_minimum_memory(128)

        assert result.passed is True

    @patch.object(HardwareDetector, 'get_memory_info')
    def test_test_minimum_memory_fail(self, mock_memory):
        """Test: Minimum memory test fails"""
        mock_memory.return_value = {'total_mb': 64, 'available_mb': 32}

        tester = HardwareCompatibilityTester()
        result = tester.test_minimum_memory(128)

        assert result.passed is False

    @patch.object(HardwareDetector, 'get_cpu_info')
    def test_test_cpu_count_pass(self, mock_cpu):
        """Test: CPU count test passes"""
        mock_cpu.return_value = {'count': 4, 'model': 'Test CPU'}

        tester = HardwareCompatibilityTester()
        result = tester.test_cpu_count(2)

        assert result.passed is True

    @patch.object(HardwareDetector, 'get_cpu_info')
    def test_test_cpu_count_fail(self, mock_cpu):
        """Test: CPU count test fails"""
        mock_cpu.return_value = {'count': 1, 'model': 'Test CPU'}

        tester = HardwareCompatibilityTester()
        result = tester.test_cpu_count(4)

        assert result.passed is False

    @patch('platform.system')
    def test_test_platform_compatibility_linux(self, mock_system):
        """Test: Platform compatibility passes for Linux"""
        mock_system.return_value = "Linux"

        tester = HardwareCompatibilityTester()
        result = tester.test_platform_compatibility()

        assert result.passed is True

    @patch('platform.system')
    def test_test_platform_compatibility_unsupported(self, mock_system):
        """Test: Platform compatibility fails for unsupported platform"""
        mock_system.return_value = "Windows"

        tester = HardwareCompatibilityTester()
        result = tester.test_platform_compatibility()

        assert result.passed is False


class TestBaremetalEnvironmentBenchmark:
    """Tests for bare metal environment benchmark"""

    def test_benchmark_initialization(self):
        """Test: Bare metal environment benchmark can be initialized"""
        benchmark = BaremetalEnvironmentBenchmark()

        assert benchmark is not None
        assert benchmark.detector is not None
        assert benchmark.arch_tester is not None
        assert benchmark.compat_tester is not None

    @patch.object(HardwareDetector, 'get_architecture')
    def test_run_architecture_tests(self, mock_arch):
        """Test: Runs architecture tests"""
        mock_arch.return_value = Architecture.X86_64

        benchmark = BaremetalEnvironmentBenchmark()
        results = benchmark.run_architecture_tests()

        assert 'current_architecture' in results
        assert 'tests' in results
        assert len(results['tests']) > 0

    @patch.object(HardwareDetector, 'get_hardware_info')
    def test_run_hardware_tests(self, mock_hw_info):
        """Test: Runs hardware tests"""
        mock_hw_info.return_value = HardwareInfo(
            architecture="x86_64",
            cpu_model="Test CPU",
            cpu_count=4,
            total_memory_mb=8192,
            platform_system="Linux"
        )

        benchmark = BaremetalEnvironmentBenchmark()
        results = benchmark.run_hardware_tests()

        assert 'hardware_info' in results
        assert 'tests' in results
        assert len(results['tests']) > 0

    @patch.object(BaremetalEnvironmentBenchmark, 'run_architecture_tests')
    @patch.object(BaremetalEnvironmentBenchmark, 'run_hardware_tests')
    def test_run_all_tests(self, mock_hw, mock_arch):
        """Test: Runs all tests"""
        mock_arch.return_value = {'current_architecture': 'x86_64', 'tests': []}
        mock_hw.return_value = {'hardware_info': {}, 'tests': []}

        benchmark = BaremetalEnvironmentBenchmark()
        results = benchmark.run_all_tests()

        assert 'architecture' in results
        assert 'hardware' in results


class TestBaremetalTestReporter:
    """Tests for bare metal test reporter"""

    def test_reporter_initialization(self):
        """Test: Bare metal test reporter can be initialized"""
        reporter = BaremetalTestReporter()

        assert reporter is not None

    def test_generate_report(self):
        """Test: Can generate test report"""
        results = {
            'architecture': {
                'current_architecture': 'x86_64',
                'tests': [
                    {
                        'test_name': 'Architecture Detection',
                        'passed': True,
                        'duration': 0.01,
                        'message': 'OK'
                    }
                ]
            },
            'hardware': {
                'hardware_info': {
                    'architecture': 'x86_64',
                    'cpu_model': 'Intel i7',
                    'cpu_count': 8,
                    'total_memory_mb': 16384,
                    'platform_system': 'Linux'
                },
                'tests': [
                    {
                        'test_name': 'Memory Test',
                        'passed': True,
                        'duration': 0.01,
                        'message': 'OK'
                    }
                ]
            }
        }

        reporter = BaremetalTestReporter()
        report = reporter.generate_report(results)

        assert isinstance(report, str)
        assert "Bare Metal Environment Test Report" in report
        assert "x86_64" in report
        assert "PASS" in report

    def test_export_metrics(self):
        """Test: Can export metrics"""
        results = {
            'architecture': {
                'current_architecture': 'x86_64',
                'tests': [
                    {'passed': True},
                    {'passed': True}
                ]
            },
            'hardware': {
                'hardware_info': {
                    'cpu_count': 8,
                    'total_memory_mb': 16384
                },
                'tests': [
                    {'passed': True}
                ]
            }
        }

        reporter = BaremetalTestReporter()
        metrics = reporter.export_metrics(results)

        assert isinstance(metrics, dict)
        assert metrics['architecture'] == 'x86_64'
        assert metrics['arch_tests_passed'] == 2
        assert metrics['cpu_count'] == 8
        assert metrics['total_memory_mb'] == 16384


class TestBaremetalEnvironmentCompliance:
    """Tests for bare metal environment target compliance"""

    def test_x86_64_support_requirement(self):
        """
        Test: x86_64 is supported

        Requirement 5.1: x86_64 support
        Target Environment: Bare metal servers
        """
        assert Architecture.X86_64.value == "x86_64"

    def test_arm64_support_requirement(self):
        """
        Test: ARM64 is supported

        Requirement 5.1: ARM64 support
        Target Environment: Embedded devices, IoT
        """
        assert Architecture.ARM64.value == "aarch64"

    def test_server_target_environment(self):
        """
        Test: Server hardware type is defined

        Target Environment: Bare metal servers
        """
        assert HardwareType.SERVER.value == "server"

    def test_embedded_target_environment(self):
        """
        Test: Embedded hardware type is defined

        Target Environment: Embedded devices
        """
        assert HardwareType.EMBEDDED.value == "embedded"

    def test_iot_target_environment(self):
        """
        Test: IoT hardware type is defined

        Target Environment: IoT devices
        """
        assert HardwareType.IOT.value == "iot"
