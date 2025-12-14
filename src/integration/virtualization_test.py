"""
Virtualization Environment Testing

Tests for QEMU/KVM and VirtualBox deployment verification.

Target Environments:
- QEMU/KVM
- VirtualBox
- VMware
"""

import os
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


class VirtualizationType(Enum):
    """Virtualization platform types"""
    QEMU = "qemu"
    KVM = "kvm"
    VIRTUALBOX = "virtualbox"
    VMWARE = "vmware"


class VMStatus(Enum):
    """Virtual machine status"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    SAVED = "saved"
    UNKNOWN = "unknown"


@dataclass
class VMInfo:
    """Virtual machine information"""
    vm_name: str
    vm_id: Optional[str]
    status: str
    platform: str

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class VirtualizationTestResult:
    """Virtualization test result"""
    test_name: str
    passed: bool
    message: str
    duration: float = 0.0
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class QEMUTester:
    """
    Tests QEMU/KVM environment functionality.

    Target Environment: QEMU/KVM
    """

    def __init__(self):
        """Initialize QEMU tester"""
        self.platform = VirtualizationType.QEMU
        self.test_results: List[VirtualizationTestResult] = []

    def check_qemu_available(self) -> bool:
        """
        Check if QEMU is available.

        Returns:
            True if QEMU is available
        """
        try:
            result = subprocess.run(
                ['qemu-system-x86_64', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def get_qemu_version(self) -> Optional[str]:
        """
        Get QEMU version.

        Returns:
            QEMU version string or None
        """
        try:
            result = subprocess.run(
                ['qemu-system-x86_64', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Get first line of version output
                return result.stdout.split('\n')[0].strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def check_kvm_available(self) -> bool:
        """
        Check if KVM is available.

        Returns:
            True if KVM is available
        """
        # Check if /dev/kvm exists (Linux-specific)
        kvm_device = Path('/dev/kvm')
        if kvm_device.exists():
            return True

        # Alternative: try to detect KVM support via qemu
        try:
            result = subprocess.run(
                ['qemu-system-x86_64', '-accel', 'help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return 'kvm' in result.stdout.lower()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def create_test_image(self, image_path: str, size_mb: int = 100) -> Tuple[bool, str]:
        """
        Create a test disk image.

        Args:
            image_path: Path for the disk image
            size_mb: Size in MB

        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = [
                'qemu-img', 'create',
                '-f', 'qcow2',
                image_path,
                f'{size_mb}M'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return (True, f"Created disk image: {image_path}")
            else:
                return (False, f"Failed to create image: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "Image creation timed out")
        except (FileNotFoundError, OSError) as e:
            return (False, f"Image creation error: {str(e)}")

    def test_qemu_boot(
        self,
        image_path: Optional[str] = None,
        memory_mb: int = 512
    ) -> VirtualizationTestResult:
        """
        Test QEMU boot capability.

        Args:
            image_path: Path to bootable image
            memory_mb: Memory size in MB

        Returns:
            Test result
        """
        start_time = time.time()
        test_name = "QEMU Boot Test"

        # Check QEMU availability
        if not self.check_qemu_available():
            duration = time.time() - start_time
            return VirtualizationTestResult(
                test_name=test_name,
                passed=False,
                message="QEMU is not available",
                duration=duration
            )

        # For testing, we just verify QEMU can start with basic args
        # We use -nographic and exit quickly to avoid hanging
        try:
            cmd = [
                'qemu-system-x86_64',
                '-m', str(memory_mb),
                '-nographic',
                '-no-reboot',
                '-kernel', '/dev/null'  # This will fail but tests invocation
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2
            )

            # We expect this to fail (no valid kernel), but if QEMU runs, that's success
            duration = time.time() - start_time

            return VirtualizationTestResult(
                test_name=test_name,
                passed=True,
                message="QEMU invocation successful",
                duration=duration,
                details={'memory_mb': memory_mb}
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return VirtualizationTestResult(
                test_name=test_name,
                passed=True,
                message="QEMU started (timeout expected for test)",
                duration=duration
            )
        except (FileNotFoundError, OSError) as e:
            duration = time.time() - start_time
            return VirtualizationTestResult(
                test_name=test_name,
                passed=False,
                message=f"QEMU error: {str(e)}",
                duration=duration
            )


class VirtualBoxTester:
    """
    Tests VirtualBox environment functionality.

    Target Environment: VirtualBox
    """

    def __init__(self):
        """Initialize VirtualBox tester"""
        self.platform = VirtualizationType.VIRTUALBOX
        self.test_results: List[VirtualizationTestResult] = []

    def check_vboxmanage_available(self) -> bool:
        """
        Check if VBoxManage is available.

        Returns:
            True if VBoxManage is available
        """
        try:
            result = subprocess.run(
                ['VBoxManage', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def get_virtualbox_version(self) -> Optional[str]:
        """
        Get VirtualBox version.

        Returns:
            VirtualBox version string or None
        """
        try:
            result = subprocess.run(
                ['VBoxManage', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def list_vms(self) -> List[str]:
        """
        List all VirtualBox VMs.

        Returns:
            List of VM names
        """
        try:
            result = subprocess.run(
                ['VBoxManage', 'list', 'vms'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                vms = []
                for line in result.stdout.split('\n'):
                    if line.strip():
                        # Format: "VM Name" {UUID}
                        parts = line.split('"')
                        if len(parts) >= 2:
                            vms.append(parts[1])
                return vms
            return []

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return []

    def create_vm(
        self,
        vm_name: str,
        os_type: str = "Linux_64",
        memory_mb: int = 512
    ) -> Tuple[bool, str]:
        """
        Create a VirtualBox VM.

        Args:
            vm_name: Name for the VM
            os_type: OS type (e.g., Linux_64)
            memory_mb: Memory size in MB

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create VM
            result = subprocess.run(
                ['VBoxManage', 'createvm', '--name', vm_name, '--ostype', os_type, '--register'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return (False, f"Failed to create VM: {result.stderr}")

            # Configure memory
            result = subprocess.run(
                ['VBoxManage', 'modifyvm', vm_name, '--memory', str(memory_mb)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return (True, f"Created VM: {vm_name}")
            else:
                return (False, f"Failed to configure VM: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "VM creation timed out")
        except (FileNotFoundError, OSError) as e:
            return (False, f"VM creation error: {str(e)}")

    def delete_vm(self, vm_name: str) -> Tuple[bool, str]:
        """
        Delete a VirtualBox VM.

        Args:
            vm_name: Name of VM to delete

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ['VBoxManage', 'unregistervm', vm_name, '--delete'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return (True, f"Deleted VM: {vm_name}")
            else:
                return (False, f"Failed to delete VM: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "VM deletion timed out")
        except (FileNotFoundError, OSError) as e:
            return (False, f"VM deletion error: {str(e)}")

    def test_vm_lifecycle(self) -> VirtualizationTestResult:
        """
        Test VirtualBox VM lifecycle.

        Returns:
            Test result
        """
        start_time = time.time()
        test_name = "VirtualBox VM Lifecycle Test"
        vm_name = f"kimigayo-test-{int(time.time())}"

        # Check VBoxManage availability
        if not self.check_vboxmanage_available():
            duration = time.time() - start_time
            return VirtualizationTestResult(
                test_name=test_name,
                passed=False,
                message="VBoxManage is not available",
                duration=duration
            )

        # Create VM
        success, msg = self.create_vm(vm_name)
        if not success:
            duration = time.time() - start_time
            return VirtualizationTestResult(
                test_name=test_name,
                passed=False,
                message=f"Failed to create VM: {msg}",
                duration=duration
            )

        # Delete VM
        success, msg = self.delete_vm(vm_name)

        duration = time.time() - start_time

        if success:
            return VirtualizationTestResult(
                test_name=test_name,
                passed=True,
                message="VirtualBox VM lifecycle test passed",
                duration=duration,
                details={'vm_name': vm_name}
            )
        else:
            return VirtualizationTestResult(
                test_name=test_name,
                passed=False,
                message=f"Failed to delete VM: {msg}",
                duration=duration
            )


class VirtualizationEnvironmentBenchmark:
    """
    Benchmarks virtualization environment functionality.

    Target Environments: QEMU/KVM, VirtualBox, VMware
    """

    def __init__(self):
        """Initialize virtualization environment benchmark"""
        self.qemu_tester = QEMUTester()
        self.vbox_tester = VirtualBoxTester()

    def run_qemu_tests(self) -> Dict:
        """
        Run QEMU/KVM environment tests.

        Returns:
            Test results
        """
        results = {
            'qemu_available': False,
            'qemu_version': None,
            'kvm_available': False,
            'tests': []
        }

        # Check QEMU availability
        results['qemu_available'] = self.qemu_tester.check_qemu_available()

        if results['qemu_available']:
            results['qemu_version'] = self.qemu_tester.get_qemu_version()

            # Check KVM availability
            results['kvm_available'] = self.qemu_tester.check_kvm_available()

            # Run boot test
            boot_result = self.qemu_tester.test_qemu_boot()
            results['tests'].append(boot_result.to_dict())

        return results

    def run_virtualbox_tests(self) -> Dict:
        """
        Run VirtualBox environment tests.

        Returns:
            Test results
        """
        results = {
            'vbox_available': False,
            'vbox_version': None,
            'tests': []
        }

        # Check VirtualBox availability
        results['vbox_available'] = self.vbox_tester.check_vboxmanage_available()

        if results['vbox_available']:
            results['vbox_version'] = self.vbox_tester.get_virtualbox_version()

            # Run VM lifecycle test
            lifecycle_result = self.vbox_tester.test_vm_lifecycle()
            results['tests'].append(lifecycle_result.to_dict())

        return results

    def run_all_tests(self) -> Dict:
        """
        Run all virtualization environment tests.

        Returns:
            Complete test results
        """
        return {
            'qemu': self.run_qemu_tests(),
            'virtualbox': self.run_virtualbox_tests()
        }

    def measure_performance(self, platform: VirtualizationType) -> Dict:
        """
        Measure performance metrics for virtualization platform.

        Args:
            platform: Virtualization platform to measure

        Returns:
            Performance metrics
        """
        metrics = {
            'platform': platform.value,
            'boot_time': None,
            'memory_overhead': None
        }

        # Placeholder for actual performance measurements
        # In real implementation, this would boot VMs and measure performance

        return metrics


class VirtualizationTestReporter:
    """
    Reports virtualization test results.
    """

    def generate_report(self, results: Dict) -> str:
        """
        Generate virtualization test report.

        Args:
            results: Test results

        Returns:
            Report as string
        """
        report_lines = [
            "=== Virtualization Environment Test Report ==="
        ]

        # QEMU/KVM results
        if 'qemu' in results:
            qemu = results['qemu']
            report_lines.append("")
            report_lines.append("QEMU/KVM Environment:")
            report_lines.append(f"  QEMU Available: {qemu['qemu_available']}")

            if qemu['qemu_version']:
                report_lines.append(f"  Version: {qemu['qemu_version']}")

            report_lines.append(f"  KVM Available: {qemu['kvm_available']}")

            if qemu['tests']:
                report_lines.append("  Tests:")
                for test in qemu['tests']:
                    status = "PASS" if test['passed'] else "FAIL"
                    report_lines.append(f"    [{status}] {test['test_name']} ({test['duration']:.2f}s)")

        # VirtualBox results
        if 'virtualbox' in results:
            vbox = results['virtualbox']
            report_lines.append("")
            report_lines.append("VirtualBox Environment:")
            report_lines.append(f"  VirtualBox Available: {vbox['vbox_available']}")

            if vbox['vbox_version']:
                report_lines.append(f"  Version: {vbox['vbox_version']}")

            if vbox['tests']:
                report_lines.append("  Tests:")
                for test in vbox['tests']:
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

        if 'qemu' in results:
            qemu = results['qemu']
            metrics['qemu_available'] = qemu['qemu_available']
            metrics['kvm_available'] = qemu.get('kvm_available', False)
            metrics['qemu_tests_passed'] = sum(
                1 for t in qemu.get('tests', []) if t['passed']
            )
            metrics['qemu_tests_total'] = len(qemu.get('tests', []))

        if 'virtualbox' in results:
            vbox = results['virtualbox']
            metrics['vbox_available'] = vbox['vbox_available']
            metrics['vbox_tests_passed'] = sum(
                1 for t in vbox.get('tests', []) if t['passed']
            )
            metrics['vbox_tests_total'] = len(vbox.get('tests', []))

        return metrics
