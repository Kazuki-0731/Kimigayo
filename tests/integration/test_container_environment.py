"""
Integration Tests for Container Environment

Tests Docker and Kubernetes deployment functionality.

Target Environments:
- Docker
- Kubernetes
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.integration.container_test import (
    ContainerRuntime,
    ContainerStatus,
    ContainerInfo,
    ContainerTestResult,
    DockerTester,
    KubernetesTester,
    ContainerEnvironmentBenchmark,
    ContainerTestReporter,
)


class TestContainerRuntime:
    """Tests for container runtime enum"""

    def test_docker_runtime(self):
        """Test: Docker runtime is defined"""
        assert ContainerRuntime.DOCKER.value == "docker"

    def test_podman_runtime(self):
        """Test: Podman runtime is defined"""
        assert ContainerRuntime.PODMAN.value == "podman"


class TestContainerStatus:
    """Tests for container status enum"""

    def test_running_status(self):
        """Test: Running status is defined"""
        assert ContainerStatus.RUNNING.value == "running"

    def test_exited_status(self):
        """Test: Exited status is defined"""
        assert ContainerStatus.EXITED.value == "exited"


class TestContainerInfo:
    """Tests for container info data structure"""

    def test_container_info_creation(self):
        """Test: Container info can be created"""
        info = ContainerInfo(
            container_id="abc123",
            name="test-container",
            image="alpine:latest",
            status="running",
            created="2024-01-01"
        )

        assert info.container_id == "abc123"
        assert info.name == "test-container"
        assert info.status == "running"

    def test_to_dict(self):
        """Test: Can convert to dictionary"""
        info = ContainerInfo(
            container_id="abc123",
            name="test",
            image="alpine",
            status="running",
            created="2024-01-01"
        )

        info_dict = info.to_dict()

        assert isinstance(info_dict, dict)
        assert info_dict['container_id'] == "abc123"


class TestContainerTestResult:
    """Tests for container test result"""

    def test_result_creation(self):
        """Test: Test result can be created"""
        result = ContainerTestResult(
            test_name="Test Container",
            passed=True,
            message="Test passed",
            duration=1.5
        )

        assert result.test_name == "Test Container"
        assert result.passed is True
        assert result.duration == 1.5

    def test_result_with_details(self):
        """Test: Result can contain details"""
        result = ContainerTestResult(
            test_name="Test",
            passed=True,
            message="OK",
            details={'container_id': 'abc123'}
        )

        assert 'container_id' in result.details


class TestDockerTester:
    """Tests for Docker tester"""

    def test_docker_tester_initialization(self):
        """Test: Docker tester can be initialized"""
        tester = DockerTester()

        assert tester is not None
        assert tester.runtime == ContainerRuntime.DOCKER

    @patch('subprocess.run')
    def test_check_docker_available_true(self, mock_run):
        """Test: Detects when Docker is available"""
        mock_run.return_value = Mock(returncode=0)

        tester = DockerTester()
        available = tester.check_docker_available()

        assert available is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_check_docker_available_false(self, mock_run):
        """Test: Detects when Docker is not available"""
        mock_run.side_effect = FileNotFoundError()

        tester = DockerTester()
        available = tester.check_docker_available()

        assert available is False

    @patch('subprocess.run')
    def test_get_docker_version(self, mock_run):
        """Test: Can get Docker version"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Docker version 24.0.0"
        )

        tester = DockerTester()
        version = tester.get_docker_version()

        assert version == "Docker version 24.0.0"

    @patch('subprocess.run')
    def test_build_image_success(self, mock_run):
        """Test: Can build Docker image"""
        mock_run.return_value = Mock(returncode=0)

        tester = DockerTester()
        success, msg = tester.build_image(
            dockerfile_path="Dockerfile",
            image_name="test-image"
        )

        assert success is True
        assert "Successfully built" in msg

    @patch('subprocess.run')
    def test_build_image_failure(self, mock_run):
        """Test: Handles build failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Build error"
        )

        tester = DockerTester()
        success, msg = tester.build_image(
            dockerfile_path="Dockerfile",
            image_name="test-image"
        )

        assert success is False
        assert "Build failed" in msg

    @patch('subprocess.run')
    def test_run_container_success(self, mock_run):
        """Test: Can run Docker container"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="abc123def456\n"
        )

        tester = DockerTester()
        success, container_id = tester.run_container("alpine:latest")

        assert success is True
        assert container_id == "abc123def456"

    @patch('subprocess.run')
    def test_run_container_failure(self, mock_run):
        """Test: Handles container run failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Run error"
        )

        tester = DockerTester()
        success, msg = tester.run_container("invalid-image")

        assert success is False
        assert "Run failed" in msg

    @patch('subprocess.run')
    def test_stop_container_success(self, mock_run):
        """Test: Can stop Docker container"""
        mock_run.return_value = Mock(returncode=0)

        tester = DockerTester()
        success, msg = tester.stop_container("abc123")

        assert success is True
        assert "Stopped container" in msg

    @patch('subprocess.run')
    def test_remove_container_success(self, mock_run):
        """Test: Can remove Docker container"""
        mock_run.return_value = Mock(returncode=0)

        tester = DockerTester()
        success, msg = tester.remove_container("abc123")

        assert success is True
        assert "Removed container" in msg

    @patch('subprocess.run')
    def test_remove_container_force(self, mock_run):
        """Test: Can force remove Docker container"""
        mock_run.return_value = Mock(returncode=0)

        tester = DockerTester()
        success, msg = tester.remove_container("abc123", force=True)

        assert success is True
        # Check that -f flag was used
        call_args = mock_run.call_args[0][0]
        assert '-f' in call_args

    @patch('subprocess.run')
    def test_get_container_status(self, mock_run):
        """Test: Can get container status"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="running\n"
        )

        tester = DockerTester()
        status = tester.get_container_status("abc123")

        assert status == "running"

    @patch('subprocess.run')
    def test_get_container_status_not_found(self, mock_run):
        """Test: Returns None for non-existent container"""
        mock_run.return_value = Mock(returncode=1)

        tester = DockerTester()
        status = tester.get_container_status("nonexistent")

        assert status is None


class TestKubernetesTester:
    """Tests for Kubernetes tester"""

    def test_k8s_tester_initialization(self):
        """Test: Kubernetes tester can be initialized"""
        tester = KubernetesTester()

        assert tester is not None

    @patch('subprocess.run')
    def test_check_kubectl_available_true(self, mock_run):
        """Test: Detects when kubectl is available"""
        mock_run.return_value = Mock(returncode=0)

        tester = KubernetesTester()
        available = tester.check_kubectl_available()

        assert available is True

    @patch('subprocess.run')
    def test_check_kubectl_available_false(self, mock_run):
        """Test: Detects when kubectl is not available"""
        mock_run.side_effect = FileNotFoundError()

        tester = KubernetesTester()
        available = tester.check_kubectl_available()

        assert available is False

    @patch('subprocess.run')
    def test_get_kubectl_version(self, mock_run):
        """Test: Can get kubectl version"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Client Version: v1.28.0"
        )

        tester = KubernetesTester()
        version = tester.get_kubectl_version()

        assert version == "Client Version: v1.28.0"

    @patch('subprocess.run')
    def test_check_cluster_connection_success(self, mock_run):
        """Test: Can check cluster connection"""
        mock_run.return_value = Mock(returncode=0)

        tester = KubernetesTester()
        connected, msg = tester.check_cluster_connection()

        assert connected is True
        assert "Connected" in msg

    @patch('subprocess.run')
    def test_check_cluster_connection_failure(self, mock_run):
        """Test: Handles cluster connection failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Connection refused"
        )

        tester = KubernetesTester()
        connected, msg = tester.check_cluster_connection()

        assert connected is False
        assert "Connection failed" in msg

    @patch('subprocess.run')
    def test_create_deployment_success(self, mock_run):
        """Test: Can create Kubernetes deployment"""
        mock_run.return_value = Mock(returncode=0)

        tester = KubernetesTester()
        success, msg = tester.create_deployment(
            name="test-deployment",
            image="nginx:alpine"
        )

        assert success is True
        assert "Created deployment" in msg

    @patch('subprocess.run')
    def test_create_deployment_failure(self, mock_run):
        """Test: Handles deployment creation failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Create error"
        )

        tester = KubernetesTester()
        success, msg = tester.create_deployment(
            name="test-deployment",
            image="invalid-image"
        )

        assert success is False
        assert "Create failed" in msg

    @patch('subprocess.run')
    def test_delete_deployment_success(self, mock_run):
        """Test: Can delete Kubernetes deployment"""
        mock_run.return_value = Mock(returncode=0)

        tester = KubernetesTester()
        success, msg = tester.delete_deployment("test-deployment")

        assert success is True
        assert "Deleted deployment" in msg


class TestContainerEnvironmentBenchmark:
    """Tests for container environment benchmark"""

    def test_benchmark_initialization(self):
        """Test: Container environment benchmark can be initialized"""
        benchmark = ContainerEnvironmentBenchmark()

        assert benchmark is not None
        assert benchmark.docker_tester is not None
        assert benchmark.k8s_tester is not None

    @patch.object(DockerTester, 'check_docker_available')
    @patch.object(DockerTester, 'get_docker_version')
    def test_run_docker_tests_available(self, mock_version, mock_available):
        """Test: Runs Docker tests when available"""
        mock_available.return_value = True
        mock_version.return_value = "Docker version 24.0.0"

        benchmark = ContainerEnvironmentBenchmark()
        results = benchmark.run_docker_tests()

        assert results['docker_available'] is True
        assert results['docker_version'] == "Docker version 24.0.0"

    @patch.object(DockerTester, 'check_docker_available')
    def test_run_docker_tests_not_available(self, mock_available):
        """Test: Handles Docker not available"""
        mock_available.return_value = False

        benchmark = ContainerEnvironmentBenchmark()
        results = benchmark.run_docker_tests()

        assert results['docker_available'] is False
        assert results['docker_version'] is None

    @patch.object(KubernetesTester, 'check_kubectl_available')
    @patch.object(KubernetesTester, 'get_kubectl_version')
    def test_run_kubernetes_tests_available(self, mock_version, mock_available):
        """Test: Runs Kubernetes tests when available"""
        mock_available.return_value = True
        mock_version.return_value = "Client Version: v1.28.0"

        benchmark = ContainerEnvironmentBenchmark()
        results = benchmark.run_kubernetes_tests()

        assert results['kubectl_available'] is True
        assert results['kubectl_version'] == "Client Version: v1.28.0"

    @patch.object(KubernetesTester, 'check_kubectl_available')
    def test_run_kubernetes_tests_not_available(self, mock_available):
        """Test: Handles kubectl not available"""
        mock_available.return_value = False

        benchmark = ContainerEnvironmentBenchmark()
        results = benchmark.run_kubernetes_tests()

        assert results['kubectl_available'] is False

    @patch.object(ContainerEnvironmentBenchmark, 'run_docker_tests')
    @patch.object(ContainerEnvironmentBenchmark, 'run_kubernetes_tests')
    def test_run_all_tests(self, mock_k8s, mock_docker):
        """Test: Runs all container tests"""
        mock_docker.return_value = {'docker_available': True}
        mock_k8s.return_value = {'kubectl_available': True}

        benchmark = ContainerEnvironmentBenchmark()
        results = benchmark.run_all_tests()

        assert 'docker' in results
        assert 'kubernetes' in results


class TestContainerTestReporter:
    """Tests for container test reporter"""

    def test_reporter_initialization(self):
        """Test: Container test reporter can be initialized"""
        reporter = ContainerTestReporter()

        assert reporter is not None

    def test_generate_report(self):
        """Test: Can generate test report"""
        results = {
            'docker': {
                'docker_available': True,
                'docker_version': "Docker version 24.0.0",
                'tests': [
                    {
                        'test_name': 'Lifecycle Test',
                        'passed': True,
                        'duration': 1.5,
                        'message': 'OK'
                    }
                ]
            },
            'kubernetes': {
                'kubectl_available': True,
                'kubectl_version': "v1.28.0",
                'cluster_connected': True,
                'tests': []
            }
        }

        reporter = ContainerTestReporter()
        report = reporter.generate_report(results)

        assert isinstance(report, str)
        assert "Container Environment Test Report" in report
        assert "Docker Environment" in report
        assert "Kubernetes Environment" in report
        assert "PASS" in report

    def test_export_metrics(self):
        """Test: Can export metrics"""
        results = {
            'docker': {
                'docker_available': True,
                'tests': [
                    {'passed': True},
                    {'passed': True}
                ]
            },
            'kubernetes': {
                'kubectl_available': True,
                'cluster_connected': True,
                'tests': [
                    {'passed': True}
                ]
            }
        }

        reporter = ContainerTestReporter()
        metrics = reporter.export_metrics(results)

        assert isinstance(metrics, dict)
        assert metrics['docker_available'] is True
        assert metrics['docker_tests_passed'] == 2
        assert metrics['docker_tests_total'] == 2
        assert metrics['kubectl_available'] is True
        assert metrics['k8s_cluster_connected'] is True


class TestContainerEnvironmentCompliance:
    """Tests for container environment target compliance"""

    def test_docker_target_environment(self):
        """
        Test: Docker is a target environment

        Target Environment: Docker
        """
        assert ContainerRuntime.DOCKER.value == "docker"

    def test_kubernetes_support(self):
        """
        Test: Kubernetes deployment is supported

        Target Environment: Kubernetes
        """
        tester = KubernetesTester()
        assert tester is not None

    def test_podman_defined(self):
        """
        Test: Podman runtime is defined

        Target Environment: Podman (alternative)
        """
        assert ContainerRuntime.PODMAN.value == "podman"
