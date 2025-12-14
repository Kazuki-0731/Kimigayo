"""
Integration Tests for Virtualization Environment

Tests QEMU/KVM and VirtualBox deployment functionality.

Target Environments:
- QEMU/KVM
- VirtualBox
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
from pathlib import Path

from src.integration.virtualization_test import (
    VirtualizationType,
    VMStatus,
    VMInfo,
    VirtualizationTestResult,
    QEMUTester,
    VirtualBoxTester,
    VirtualizationEnvironmentBenchmark,
    VirtualizationTestReporter,
)


class TestVirtualizationType:
    """Tests for virtualization type enum"""

    def test_qemu_type(self):
        """Test: QEMU type is defined"""
        assert VirtualizationType.QEMU.value == "qemu"

    def test_kvm_type(self):
        """Test: KVM type is defined"""
        assert VirtualizationType.KVM.value == "kvm"

    def test_virtualbox_type(self):
        """Test: VirtualBox type is defined"""
        assert VirtualizationType.VIRTUALBOX.value == "virtualbox"

    def test_vmware_type(self):
        """Test: VMware type is defined"""
        assert VirtualizationType.VMWARE.value == "vmware"


class TestVMStatus:
    """Tests for VM status enum"""

    def test_running_status(self):
        """Test: Running status is defined"""
        assert VMStatus.RUNNING.value == "running"

    def test_stopped_status(self):
        """Test: Stopped status is defined"""
        assert VMStatus.STOPPED.value == "stopped"


class TestVMInfo:
    """Tests for VM info data structure"""

    def test_vm_info_creation(self):
        """Test: VM info can be created"""
        info = VMInfo(
            vm_name="test-vm",
            vm_id="vm-123",
            status="running",
            platform="qemu"
        )

        assert info.vm_name == "test-vm"
        assert info.vm_id == "vm-123"
        assert info.status == "running"

    def test_to_dict(self):
        """Test: Can convert to dictionary"""
        info = VMInfo(
            vm_name="test",
            vm_id="123",
            status="running",
            platform="kvm"
        )

        info_dict = info.to_dict()

        assert isinstance(info_dict, dict)
        assert info_dict['vm_name'] == "test"


class TestVirtualizationTestResult:
    """Tests for virtualization test result"""

    def test_result_creation(self):
        """Test: Test result can be created"""
        result = VirtualizationTestResult(
            test_name="QEMU Boot Test",
            passed=True,
            message="Boot successful",
            duration=2.5
        )

        assert result.test_name == "QEMU Boot Test"
        assert result.passed is True
        assert result.duration == 2.5

    def test_result_with_details(self):
        """Test: Result can contain details"""
        result = VirtualizationTestResult(
            test_name="Test",
            passed=True,
            message="OK",
            details={'vm_name': 'test-vm'}
        )

        assert 'vm_name' in result.details


class TestQEMUTester:
    """Tests for QEMU tester"""

    def test_qemu_tester_initialization(self):
        """Test: QEMU tester can be initialized"""
        tester = QEMUTester()

        assert tester is not None
        assert tester.platform == VirtualizationType.QEMU

    @patch('subprocess.run')
    def test_check_qemu_available_true(self, mock_run):
        """Test: Detects when QEMU is available"""
        mock_run.return_value = Mock(returncode=0)

        tester = QEMUTester()
        available = tester.check_qemu_available()

        assert available is True

    @patch('subprocess.run')
    def test_check_qemu_available_false(self, mock_run):
        """Test: Detects when QEMU is not available"""
        mock_run.side_effect = FileNotFoundError()

        tester = QEMUTester()
        available = tester.check_qemu_available()

        assert available is False

    @patch('subprocess.run')
    def test_get_qemu_version(self, mock_run):
        """Test: Can get QEMU version"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="QEMU emulator version 8.0.0\n"
        )

        tester = QEMUTester()
        version = tester.get_qemu_version()

        assert version == "QEMU emulator version 8.0.0"

    @patch('pathlib.Path.exists')
    def test_check_kvm_available_device_exists(self, mock_exists):
        """Test: Detects KVM when /dev/kvm exists"""
        mock_exists.return_value = True

        tester = QEMUTester()
        available = tester.check_kvm_available()

        assert available is True

    @patch('pathlib.Path.exists')
    @patch('subprocess.run')
    def test_check_kvm_available_via_qemu(self, mock_run, mock_exists):
        """Test: Detects KVM via QEMU accel help"""
        mock_exists.return_value = False
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Accelerators supported:\nkvm\ntcg\n"
        )

        tester = QEMUTester()
        available = tester.check_kvm_available()

        assert available is True

    @patch('subprocess.run')
    def test_create_test_image_success(self, mock_run):
        """Test: Can create QEMU disk image"""
        mock_run.return_value = Mock(returncode=0)

        tester = QEMUTester()
        success, msg = tester.create_test_image("/tmp/test.qcow2", 100)

        assert success is True
        assert "Created disk image" in msg

    @patch('subprocess.run')
    def test_create_test_image_failure(self, mock_run):
        """Test: Handles image creation failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Creation failed"
        )

        tester = QEMUTester()
        success, msg = tester.create_test_image("/tmp/test.qcow2", 100)

        assert success is False
        assert "Failed to create image" in msg

    @patch.object(QEMUTester, 'check_qemu_available')
    def test_test_qemu_boot_not_available(self, mock_available):
        """Test: Handles QEMU not available"""
        mock_available.return_value = False

        tester = QEMUTester()
        result = tester.test_qemu_boot()

        assert result.passed is False
        assert "not available" in result.message

    @patch.object(QEMUTester, 'check_qemu_available')
    @patch('subprocess.run')
    def test_test_qemu_boot_success(self, mock_run, mock_available):
        """Test: QEMU boot test passes"""
        mock_available.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired('qemu', 2)

        tester = QEMUTester()
        result = tester.test_qemu_boot()

        # Timeout is expected and considered success for this test
        assert result.passed is True


class TestVirtualBoxTester:
    """Tests for VirtualBox tester"""

    def test_vbox_tester_initialization(self):
        """Test: VirtualBox tester can be initialized"""
        tester = VirtualBoxTester()

        assert tester is not None
        assert tester.platform == VirtualizationType.VIRTUALBOX

    @patch('subprocess.run')
    def test_check_vboxmanage_available_true(self, mock_run):
        """Test: Detects when VBoxManage is available"""
        mock_run.return_value = Mock(returncode=0)

        tester = VirtualBoxTester()
        available = tester.check_vboxmanage_available()

        assert available is True

    @patch('subprocess.run')
    def test_check_vboxmanage_available_false(self, mock_run):
        """Test: Detects when VBoxManage is not available"""
        mock_run.side_effect = FileNotFoundError()

        tester = VirtualBoxTester()
        available = tester.check_vboxmanage_available()

        assert available is False

    @patch('subprocess.run')
    def test_get_virtualbox_version(self, mock_run):
        """Test: Can get VirtualBox version"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="7.0.10r158379"
        )

        tester = VirtualBoxTester()
        version = tester.get_virtualbox_version()

        assert version == "7.0.10r158379"

    @patch('subprocess.run')
    def test_list_vms(self, mock_run):
        """Test: Can list VirtualBox VMs"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='"VM1" {uuid-1}\n"VM2" {uuid-2}\n'
        )

        tester = VirtualBoxTester()
        vms = tester.list_vms()

        assert len(vms) == 2
        assert "VM1" in vms
        assert "VM2" in vms

    @patch('subprocess.run')
    def test_list_vms_empty(self, mock_run):
        """Test: Returns empty list when no VMs"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=""
        )

        tester = VirtualBoxTester()
        vms = tester.list_vms()

        assert vms == []

    @patch('subprocess.run')
    def test_create_vm_success(self, mock_run):
        """Test: Can create VirtualBox VM"""
        mock_run.return_value = Mock(returncode=0)

        tester = VirtualBoxTester()
        success, msg = tester.create_vm("test-vm")

        assert success is True
        assert "Created VM" in msg

    @patch('subprocess.run')
    def test_create_vm_failure(self, mock_run):
        """Test: Handles VM creation failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Creation failed"
        )

        tester = VirtualBoxTester()
        success, msg = tester.create_vm("test-vm")

        assert success is False
        assert "Failed to create VM" in msg

    @patch('subprocess.run')
    def test_delete_vm_success(self, mock_run):
        """Test: Can delete VirtualBox VM"""
        mock_run.return_value = Mock(returncode=0)

        tester = VirtualBoxTester()
        success, msg = tester.delete_vm("test-vm")

        assert success is True
        assert "Deleted VM" in msg

    @patch('subprocess.run')
    def test_delete_vm_failure(self, mock_run):
        """Test: Handles VM deletion failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Deletion failed"
        )

        tester = VirtualBoxTester()
        success, msg = tester.delete_vm("test-vm")

        assert success is False
        assert "Failed to delete VM" in msg

    @patch.object(VirtualBoxTester, 'check_vboxmanage_available')
    def test_test_vm_lifecycle_not_available(self, mock_available):
        """Test: Handles VBoxManage not available"""
        mock_available.return_value = False

        tester = VirtualBoxTester()
        result = tester.test_vm_lifecycle()

        assert result.passed is False
        assert "not available" in result.message

    @patch.object(VirtualBoxTester, 'check_vboxmanage_available')
    @patch.object(VirtualBoxTester, 'create_vm')
    @patch.object(VirtualBoxTester, 'delete_vm')
    def test_test_vm_lifecycle_success(self, mock_delete, mock_create, mock_available):
        """Test: VM lifecycle test passes"""
        mock_available.return_value = True
        mock_create.return_value = (True, "Created")
        mock_delete.return_value = (True, "Deleted")

        tester = VirtualBoxTester()
        result = tester.test_vm_lifecycle()

        assert result.passed is True
        assert "lifecycle test passed" in result.message


class TestVirtualizationEnvironmentBenchmark:
    """Tests for virtualization environment benchmark"""

    def test_benchmark_initialization(self):
        """Test: Virtualization environment benchmark can be initialized"""
        benchmark = VirtualizationEnvironmentBenchmark()

        assert benchmark is not None
        assert benchmark.qemu_tester is not None
        assert benchmark.vbox_tester is not None

    @patch.object(QEMUTester, 'check_qemu_available')
    @patch.object(QEMUTester, 'get_qemu_version')
    @patch.object(QEMUTester, 'check_kvm_available')
    def test_run_qemu_tests_available(self, mock_kvm, mock_version, mock_available):
        """Test: Runs QEMU tests when available"""
        mock_available.return_value = True
        mock_version.return_value = "QEMU emulator version 8.0.0"
        mock_kvm.return_value = True

        benchmark = VirtualizationEnvironmentBenchmark()
        results = benchmark.run_qemu_tests()

        assert results['qemu_available'] is True
        assert results['kvm_available'] is True

    @patch.object(QEMUTester, 'check_qemu_available')
    def test_run_qemu_tests_not_available(self, mock_available):
        """Test: Handles QEMU not available"""
        mock_available.return_value = False

        benchmark = VirtualizationEnvironmentBenchmark()
        results = benchmark.run_qemu_tests()

        assert results['qemu_available'] is False

    @patch.object(VirtualBoxTester, 'check_vboxmanage_available')
    @patch.object(VirtualBoxTester, 'get_virtualbox_version')
    def test_run_virtualbox_tests_available(self, mock_version, mock_available):
        """Test: Runs VirtualBox tests when available"""
        mock_available.return_value = True
        mock_version.return_value = "7.0.10"

        benchmark = VirtualizationEnvironmentBenchmark()
        results = benchmark.run_virtualbox_tests()

        assert results['vbox_available'] is True
        assert results['vbox_version'] == "7.0.10"

    @patch.object(VirtualBoxTester, 'check_vboxmanage_available')
    def test_run_virtualbox_tests_not_available(self, mock_available):
        """Test: Handles VirtualBox not available"""
        mock_available.return_value = False

        benchmark = VirtualizationEnvironmentBenchmark()
        results = benchmark.run_virtualbox_tests()

        assert results['vbox_available'] is False

    @patch.object(VirtualizationEnvironmentBenchmark, 'run_qemu_tests')
    @patch.object(VirtualizationEnvironmentBenchmark, 'run_virtualbox_tests')
    def test_run_all_tests(self, mock_vbox, mock_qemu):
        """Test: Runs all virtualization tests"""
        mock_qemu.return_value = {'qemu_available': True}
        mock_vbox.return_value = {'vbox_available': True}

        benchmark = VirtualizationEnvironmentBenchmark()
        results = benchmark.run_all_tests()

        assert 'qemu' in results
        assert 'virtualbox' in results

    def test_measure_performance(self):
        """Test: Can measure performance metrics"""
        benchmark = VirtualizationEnvironmentBenchmark()
        metrics = benchmark.measure_performance(VirtualizationType.QEMU)

        assert isinstance(metrics, dict)
        assert metrics['platform'] == "qemu"


class TestVirtualizationTestReporter:
    """Tests for virtualization test reporter"""

    def test_reporter_initialization(self):
        """Test: Virtualization test reporter can be initialized"""
        reporter = VirtualizationTestReporter()

        assert reporter is not None

    def test_generate_report(self):
        """Test: Can generate test report"""
        results = {
            'qemu': {
                'qemu_available': True,
                'qemu_version': "QEMU emulator version 8.0.0",
                'kvm_available': True,
                'tests': [
                    {
                        'test_name': 'QEMU Boot Test',
                        'passed': True,
                        'duration': 1.2,
                        'message': 'OK'
                    }
                ]
            },
            'virtualbox': {
                'vbox_available': True,
                'vbox_version': "7.0.10",
                'tests': []
            }
        }

        reporter = VirtualizationTestReporter()
        report = reporter.generate_report(results)

        assert isinstance(report, str)
        assert "Virtualization Environment Test Report" in report
        assert "QEMU/KVM Environment" in report
        assert "VirtualBox Environment" in report
        assert "PASS" in report

    def test_export_metrics(self):
        """Test: Can export metrics"""
        results = {
            'qemu': {
                'qemu_available': True,
                'kvm_available': True,
                'tests': [
                    {'passed': True},
                    {'passed': True}
                ]
            },
            'virtualbox': {
                'vbox_available': True,
                'tests': [
                    {'passed': True}
                ]
            }
        }

        reporter = VirtualizationTestReporter()
        metrics = reporter.export_metrics(results)

        assert isinstance(metrics, dict)
        assert metrics['qemu_available'] is True
        assert metrics['kvm_available'] is True
        assert metrics['qemu_tests_passed'] == 2
        assert metrics['vbox_available'] is True


class TestVirtualizationEnvironmentCompliance:
    """Tests for virtualization environment target compliance"""

    def test_qemu_target_environment(self):
        """
        Test: QEMU is a target environment

        Target Environment: QEMU/KVM
        """
        assert VirtualizationType.QEMU.value == "qemu"
        assert VirtualizationType.KVM.value == "kvm"

    def test_virtualbox_target_environment(self):
        """
        Test: VirtualBox is a target environment

        Target Environment: VirtualBox
        """
        assert VirtualizationType.VIRTUALBOX.value == "virtualbox"

    def test_vmware_defined(self):
        """
        Test: VMware is defined

        Target Environment: VMware
        """
        assert VirtualizationType.VMWARE.value == "vmware"
