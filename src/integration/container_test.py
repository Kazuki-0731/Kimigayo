"""
Container Environment Testing

Tests for Docker and Kubernetes deployment verification.

Target Environments:
- Docker
- Kubernetes
- Podman
"""

import os
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


class ContainerRuntime(Enum):
    """Container runtime types"""
    DOCKER = "docker"
    PODMAN = "podman"
    CONTAINERD = "containerd"


class ContainerStatus(Enum):
    """Container status"""
    RUNNING = "running"
    EXITED = "exited"
    CREATED = "created"
    PAUSED = "paused"
    UNKNOWN = "unknown"


@dataclass
class ContainerInfo:
    """Container information"""
    container_id: str
    name: str
    image: str
    status: str
    created: str

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class ContainerTestResult:
    """Container test result"""
    test_name: str
    passed: bool
    message: str
    duration: float = 0.0
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class DockerTester:
    """
    Tests Docker environment functionality.

    Target Environment: Docker
    """

    def __init__(self):
        """Initialize Docker tester"""
        self.runtime = ContainerRuntime.DOCKER
        self.test_results: List[ContainerTestResult] = []

    def check_docker_available(self) -> bool:
        """
        Check if Docker is available.

        Returns:
            True if Docker is available
        """
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def get_docker_version(self) -> Optional[str]:
        """
        Get Docker version.

        Returns:
            Docker version string or None
        """
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def build_image(
        self,
        dockerfile_path: str,
        image_name: str,
        context_path: str = "."
    ) -> Tuple[bool, str]:
        """
        Build Docker image.

        Args:
            dockerfile_path: Path to Dockerfile
            image_name: Name for the built image
            context_path: Build context path

        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = [
                'docker', 'build',
                '-f', dockerfile_path,
                '-t', image_name,
                context_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )

            if result.returncode == 0:
                return (True, f"Successfully built image: {image_name}")
            else:
                return (False, f"Build failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "Build timed out after 5 minutes")
        except (FileNotFoundError, OSError) as e:
            return (False, f"Build error: {str(e)}")

    def run_container(
        self,
        image_name: str,
        container_name: Optional[str] = None,
        command: Optional[List[str]] = None,
        detach: bool = True
    ) -> Tuple[bool, str]:
        """
        Run Docker container.

        Args:
            image_name: Image to run
            container_name: Optional container name
            command: Optional command to run
            detach: Run in detached mode

        Returns:
            Tuple of (success, container_id or error message)
        """
        try:
            cmd = ['docker', 'run']

            if detach:
                cmd.append('-d')

            if container_name:
                cmd.extend(['--name', container_name])

            cmd.append(image_name)

            if command:
                cmd.extend(command)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                container_id = result.stdout.strip()
                return (True, container_id)
            else:
                return (False, f"Run failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "Container start timed out")
        except (FileNotFoundError, OSError) as e:
            return (False, f"Run error: {str(e)}")

    def stop_container(self, container_id: str) -> Tuple[bool, str]:
        """
        Stop Docker container.

        Args:
            container_id: Container ID or name

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ['docker', 'stop', container_id],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return (True, f"Stopped container: {container_id}")
            else:
                return (False, f"Stop failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "Stop timed out")
        except (FileNotFoundError, OSError) as e:
            return (False, f"Stop error: {str(e)}")

    def remove_container(self, container_id: str, force: bool = False) -> Tuple[bool, str]:
        """
        Remove Docker container.

        Args:
            container_id: Container ID or name
            force: Force removal

        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ['docker', 'rm']
            if force:
                cmd.append('-f')
            cmd.append(container_id)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return (True, f"Removed container: {container_id}")
            else:
                return (False, f"Remove failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "Remove timed out")
        except (FileNotFoundError, OSError) as e:
            return (False, f"Remove error: {str(e)}")

    def get_container_status(self, container_id: str) -> Optional[str]:
        """
        Get container status.

        Args:
            container_id: Container ID or name

        Returns:
            Status string or None
        """
        try:
            result = subprocess.run(
                ['docker', 'inspect', '-f', '{{.State.Status}}', container_id],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip()
            return None

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def test_container_lifecycle(self, image_name: str = "alpine:latest") -> ContainerTestResult:
        """
        Test complete container lifecycle.

        Args:
            image_name: Image to test with

        Returns:
            Test result
        """
        start_time = time.time()
        test_name = "Container Lifecycle Test"

        # Run container
        success, container_id = self.run_container(
            image_name,
            container_name=f"kimigayo-test-{int(time.time())}",
            command=['sleep', '10']
        )

        if not success:
            duration = time.time() - start_time
            return ContainerTestResult(
                test_name=test_name,
                passed=False,
                message=f"Failed to run container: {container_id}",
                duration=duration
            )

        # Check status
        status = self.get_container_status(container_id)
        if status != "running":
            self.remove_container(container_id, force=True)
            duration = time.time() - start_time
            return ContainerTestResult(
                test_name=test_name,
                passed=False,
                message=f"Container not running (status: {status})",
                duration=duration
            )

        # Stop container
        success, msg = self.stop_container(container_id)
        if not success:
            self.remove_container(container_id, force=True)
            duration = time.time() - start_time
            return ContainerTestResult(
                test_name=test_name,
                passed=False,
                message=f"Failed to stop container: {msg}",
                duration=duration
            )

        # Remove container
        success, msg = self.remove_container(container_id)

        duration = time.time() - start_time

        if success:
            return ContainerTestResult(
                test_name=test_name,
                passed=True,
                message="Container lifecycle test passed",
                duration=duration,
                details={'container_id': container_id}
            )
        else:
            return ContainerTestResult(
                test_name=test_name,
                passed=False,
                message=f"Failed to remove container: {msg}",
                duration=duration
            )


class KubernetesTester:
    """
    Tests Kubernetes deployment functionality.

    Target Environment: Kubernetes
    """

    def __init__(self):
        """Initialize Kubernetes tester"""
        self.test_results: List[ContainerTestResult] = []

    def check_kubectl_available(self) -> bool:
        """
        Check if kubectl is available.

        Returns:
            True if kubectl is available
        """
        try:
            result = subprocess.run(
                ['kubectl', 'version', '--client'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def get_kubectl_version(self) -> Optional[str]:
        """
        Get kubectl version.

        Returns:
            kubectl version string or None
        """
        try:
            result = subprocess.run(
                ['kubectl', 'version', '--client', '--short'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def check_cluster_connection(self) -> Tuple[bool, str]:
        """
        Check connection to Kubernetes cluster.

        Returns:
            Tuple of (connected, message)
        """
        try:
            result = subprocess.run(
                ['kubectl', 'cluster-info'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return (True, "Connected to cluster")
            else:
                return (False, f"Connection failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "Connection timed out")
        except (FileNotFoundError, OSError) as e:
            return (False, f"Connection error: {str(e)}")

    def create_deployment(
        self,
        name: str,
        image: str,
        replicas: int = 1
    ) -> Tuple[bool, str]:
        """
        Create Kubernetes deployment.

        Args:
            name: Deployment name
            image: Container image
            replicas: Number of replicas

        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = [
                'kubectl', 'create', 'deployment',
                name,
                f'--image={image}',
                f'--replicas={replicas}'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return (True, f"Created deployment: {name}")
            else:
                return (False, f"Create failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "Create timed out")
        except (FileNotFoundError, OSError) as e:
            return (False, f"Create error: {str(e)}")

    def delete_deployment(self, name: str) -> Tuple[bool, str]:
        """
        Delete Kubernetes deployment.

        Args:
            name: Deployment name

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ['kubectl', 'delete', 'deployment', name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return (True, f"Deleted deployment: {name}")
            else:
                return (False, f"Delete failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, "Delete timed out")
        except (FileNotFoundError, OSError) as e:
            return (False, f"Delete error: {str(e)}")

    def test_deployment(self, image_name: str = "nginx:alpine") -> ContainerTestResult:
        """
        Test Kubernetes deployment.

        Args:
            image_name: Image to test with

        Returns:
            Test result
        """
        start_time = time.time()
        test_name = "Kubernetes Deployment Test"
        deployment_name = f"kimigayo-test-{int(time.time())}"

        # Check cluster connection
        connected, msg = self.check_cluster_connection()
        if not connected:
            duration = time.time() - start_time
            return ContainerTestResult(
                test_name=test_name,
                passed=False,
                message=f"Cluster not accessible: {msg}",
                duration=duration
            )

        # Create deployment
        success, msg = self.create_deployment(deployment_name, image_name)
        if not success:
            duration = time.time() - start_time
            return ContainerTestResult(
                test_name=test_name,
                passed=False,
                message=f"Failed to create deployment: {msg}",
                duration=duration
            )

        # Wait a bit for deployment
        time.sleep(2)

        # Delete deployment
        success, msg = self.delete_deployment(deployment_name)

        duration = time.time() - start_time

        if success:
            return ContainerTestResult(
                test_name=test_name,
                passed=True,
                message="Kubernetes deployment test passed",
                duration=duration,
                details={'deployment_name': deployment_name}
            )
        else:
            return ContainerTestResult(
                test_name=test_name,
                passed=False,
                message=f"Failed to delete deployment: {msg}",
                duration=duration
            )


class ContainerEnvironmentBenchmark:
    """
    Benchmarks container environment functionality.

    Target Environments: Docker, Kubernetes
    """

    def __init__(self):
        """Initialize container environment benchmark"""
        self.docker_tester = DockerTester()
        self.k8s_tester = KubernetesTester()

    def run_docker_tests(self) -> Dict:
        """
        Run Docker environment tests.

        Returns:
            Test results
        """
        results = {
            'docker_available': False,
            'docker_version': None,
            'tests': []
        }

        # Check Docker availability
        results['docker_available'] = self.docker_tester.check_docker_available()

        if results['docker_available']:
            results['docker_version'] = self.docker_tester.get_docker_version()

            # Run lifecycle test
            lifecycle_result = self.docker_tester.test_container_lifecycle()
            results['tests'].append(lifecycle_result.to_dict())

        return results

    def run_kubernetes_tests(self) -> Dict:
        """
        Run Kubernetes environment tests.

        Returns:
            Test results
        """
        results = {
            'kubectl_available': False,
            'kubectl_version': None,
            'cluster_connected': False,
            'tests': []
        }

        # Check kubectl availability
        results['kubectl_available'] = self.k8s_tester.check_kubectl_available()

        if results['kubectl_available']:
            results['kubectl_version'] = self.k8s_tester.get_kubectl_version()

            # Check cluster connection
            connected, msg = self.k8s_tester.check_cluster_connection()
            results['cluster_connected'] = connected

            if connected:
                # Run deployment test
                deployment_result = self.k8s_tester.test_deployment()
                results['tests'].append(deployment_result.to_dict())

        return results

    def run_all_tests(self) -> Dict:
        """
        Run all container environment tests.

        Returns:
            Complete test results
        """
        return {
            'docker': self.run_docker_tests(),
            'kubernetes': self.run_kubernetes_tests()
        }


class ContainerTestReporter:
    """
    Reports container test results.
    """

    def generate_report(self, results: Dict) -> str:
        """
        Generate container test report.

        Args:
            results: Test results

        Returns:
            Report as string
        """
        report_lines = [
            "=== Container Environment Test Report ==="
        ]

        # Docker results
        if 'docker' in results:
            docker = results['docker']
            report_lines.append("")
            report_lines.append("Docker Environment:")
            report_lines.append(f"  Available: {docker['docker_available']}")

            if docker['docker_version']:
                report_lines.append(f"  Version: {docker['docker_version']}")

            if docker['tests']:
                report_lines.append("  Tests:")
                for test in docker['tests']:
                    status = "PASS" if test['passed'] else "FAIL"
                    report_lines.append(f"    [{status}] {test['test_name']} ({test['duration']:.2f}s)")

        # Kubernetes results
        if 'kubernetes' in results:
            k8s = results['kubernetes']
            report_lines.append("")
            report_lines.append("Kubernetes Environment:")
            report_lines.append(f"  kubectl Available: {k8s['kubectl_available']}")

            if k8s['kubectl_version']:
                report_lines.append(f"  Version: {k8s['kubectl_version']}")

            report_lines.append(f"  Cluster Connected: {k8s['cluster_connected']}")

            if k8s['tests']:
                report_lines.append("  Tests:")
                for test in k8s['tests']:
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

        if 'docker' in results:
            docker = results['docker']
            metrics['docker_available'] = docker['docker_available']
            metrics['docker_tests_passed'] = sum(
                1 for t in docker.get('tests', []) if t['passed']
            )
            metrics['docker_tests_total'] = len(docker.get('tests', []))

        if 'kubernetes' in results:
            k8s = results['kubernetes']
            metrics['kubectl_available'] = k8s['kubectl_available']
            metrics['k8s_cluster_connected'] = k8s['cluster_connected']
            metrics['k8s_tests_passed'] = sum(
                1 for t in k8s.get('tests', []) if t['passed']
            )
            metrics['k8s_tests_total'] = len(k8s.get('tests', []))

        return metrics
