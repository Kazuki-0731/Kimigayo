"""
Service Control System

Manages system services with explicit enablement control.

Requirements:
- 3.4: Service startup control - only explicitly enabled services start
- 7.5: Service management commands - start, stop, restart, status
"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict, field
from enum import Enum


class ServiceState(Enum):
    """Service runtime state"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


class RunLevel(Enum):
    """System run levels"""
    BOOT = "boot"
    DEFAULT = "default"
    SHUTDOWN = "shutdown"


@dataclass
class ServiceConfig:
    """
    Service configuration.

    Requirement: 3.4 (Service startup control)
    """
    name: str
    description: str = ""
    enabled: bool = False
    dependencies: List[str] = field(default_factory=list)
    run_levels: List[str] = field(default_factory=lambda: ["default"])
    start_command: Optional[str] = None
    stop_command: Optional[str] = None
    restart_command: Optional[str] = None
    pid_file: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ServiceConfig":
        """Create from dictionary"""
        return cls(**data)


@dataclass
class ServiceStatus:
    """Service status information"""
    name: str
    state: ServiceState
    enabled: bool
    pid: Optional[int] = None
    uptime: Optional[int] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['state'] = self.state.value
        return data


class ServiceManager:
    """
    Manages system services.

    Requirement: 3.4 (Service startup control)
    Requirement: 7.5 (Service management commands)
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize service manager.

        Args:
            config_dir: Directory for service configurations
        """
        self.config_dir = config_dir or Path("/etc/kimigayo/services")
        self.services: Dict[str, ServiceConfig] = {}
        self.runtime_states: Dict[str, ServiceState] = {}

    def register_service(self, config: ServiceConfig):
        """
        Register a service.

        Args:
            config: Service configuration
        """
        self.services[config.name] = config
        self.runtime_states[config.name] = ServiceState.STOPPED

    def enable_service(self, name: str, run_level: str = "default"):
        """
        Enable a service for automatic startup.

        Requirement: 3.4 - Only explicitly enabled services start

        Args:
            name: Service name
            run_level: Run level to enable service in

        Raises:
            ValueError: If service not found
        """
        service = self.services.get(name)
        if not service:
            raise ValueError(f"Service not found: {name}")

        service.enabled = True
        if run_level not in service.run_levels:
            service.run_levels.append(run_level)

    def disable_service(self, name: str):
        """
        Disable a service from automatic startup.

        Args:
            name: Service name

        Raises:
            ValueError: If service not found
        """
        service = self.services.get(name)
        if not service:
            raise ValueError(f"Service not found: {name}")

        service.enabled = False

    def start_service(self, name: str) -> bool:
        """
        Start a service.

        Requirement: 7.5 - Service management commands (start)

        Args:
            name: Service name

        Returns:
            True if service started successfully

        Raises:
            ValueError: If service not found or dependencies not satisfied
        """
        service = self.services.get(name)
        if not service:
            raise ValueError(f"Service not found: {name}")

        # Check dependencies
        for dep in service.dependencies:
            dep_service = self.services.get(dep)
            if not dep_service:
                raise ValueError(f"Dependency not found: {dep}")
            if self.runtime_states.get(dep) != ServiceState.RUNNING:
                # Auto-start dependency
                if not self.start_service(dep):
                    raise ValueError(f"Failed to start dependency: {dep}")

        # Update state
        self.runtime_states[name] = ServiceState.STARTING

        try:
            # Execute start command (simplified - in real implementation would use subprocess)
            if service.start_command:
                # Simulate service start
                self.runtime_states[name] = ServiceState.RUNNING
                return True
            else:
                self.runtime_states[name] = ServiceState.RUNNING
                return True
        except Exception as e:
            self.runtime_states[name] = ServiceState.FAILED
            return False

    def stop_service(self, name: str) -> bool:
        """
        Stop a service.

        Requirement: 7.5 - Service management commands (stop)

        Args:
            name: Service name

        Returns:
            True if service stopped successfully

        Raises:
            ValueError: If service not found
        """
        service = self.services.get(name)
        if not service:
            raise ValueError(f"Service not found: {name}")

        # Check if other running services depend on this one
        for svc_name, svc in self.services.items():
            if (name in svc.dependencies and
                self.runtime_states.get(svc_name) == ServiceState.RUNNING):
                raise ValueError(f"Cannot stop {name}: {svc_name} depends on it")

        # Update state
        self.runtime_states[name] = ServiceState.STOPPING

        try:
            # Execute stop command (simplified)
            if service.stop_command:
                # Simulate service stop
                self.runtime_states[name] = ServiceState.STOPPED
                return True
            else:
                self.runtime_states[name] = ServiceState.STOPPED
                return True
        except Exception as e:
            self.runtime_states[name] = ServiceState.FAILED
            return False

    def restart_service(self, name: str) -> bool:
        """
        Restart a service.

        Requirement: 7.5 - Service management commands (restart)

        Args:
            name: Service name

        Returns:
            True if service restarted successfully
        """
        service = self.services.get(name)
        if not service:
            raise ValueError(f"Service not found: {name}")

        # Use restart command if available, otherwise stop and start
        if service.restart_command:
            try:
                # Simulate restart
                self.runtime_states[name] = ServiceState.RUNNING
                return True
            except Exception:
                return False
        else:
            if self.runtime_states.get(name) == ServiceState.RUNNING:
                if not self.stop_service(name):
                    return False
            return self.start_service(name)

    def get_status(self, name: str) -> ServiceStatus:
        """
        Get service status.

        Requirement: 7.5 - Service management commands (status)

        Args:
            name: Service name

        Returns:
            Service status

        Raises:
            ValueError: If service not found
        """
        service = self.services.get(name)
        if not service:
            raise ValueError(f"Service not found: {name}")

        state = self.runtime_states.get(name, ServiceState.STOPPED)

        return ServiceStatus(
            name=name,
            state=state,
            enabled=service.enabled
        )

    def get_enabled_services(self, run_level: Optional[str] = None) -> List[ServiceConfig]:
        """
        Get all enabled services.

        Requirement: 3.4 - Only explicitly enabled services

        Args:
            run_level: Optional run level filter

        Returns:
            List of enabled services
        """
        enabled = [s for s in self.services.values() if s.enabled]

        if run_level:
            enabled = [s for s in enabled if run_level in s.run_levels]

        return enabled

    def start_enabled_services(self, run_level: str = "default") -> Dict[str, bool]:
        """
        Start all enabled services for a run level.

        Requirement: 3.4 - Only explicitly enabled services start

        Args:
            run_level: Run level to start services for

        Returns:
            Dictionary of service names to start success status
        """
        enabled = self.get_enabled_services(run_level)
        results = {}

        for service in enabled:
            try:
                results[service.name] = self.start_service(service.name)
            except Exception as e:
                results[service.name] = False

        return results

    def list_services(self) -> List[str]:
        """Get list of all service names"""
        return list(self.services.keys())

    def save_config(self, path: Path):
        """
        Save service configurations to file.

        Args:
            path: File path
        """
        data = {
            name: config.to_dict()
            for name, config in self.services.items()
        }
        path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def load_config(self, path: Path):
        """
        Load service configurations from file.

        Args:
            path: File path
        """
        data = json.loads(path.read_text())

        self.services.clear()
        self.runtime_states.clear()

        for name, config_data in data.items():
            config = ServiceConfig.from_dict(config_data)
            self.register_service(config)


class ServiceController:
    """
    CLI interface for service management.

    Requirement: 7.5 (Service management commands)
    """

    def __init__(self, manager: ServiceManager):
        """
        Initialize service controller.

        Args:
            manager: Service manager instance
        """
        self.manager = manager

    def cmd_start(self, service_name: str) -> int:
        """
        Start a service.

        Args:
            service_name: Name of service to start

        Returns:
            Exit code (0 for success)
        """
        try:
            if self.manager.start_service(service_name):
                print(f"✓ Service {service_name} started")
                return 0
            else:
                print(f"✗ Failed to start service {service_name}")
                return 1
        except Exception as e:
            print(f"✗ Error: {e}")
            return 1

    def cmd_stop(self, service_name: str) -> int:
        """
        Stop a service.

        Args:
            service_name: Name of service to stop

        Returns:
            Exit code (0 for success)
        """
        try:
            if self.manager.stop_service(service_name):
                print(f"✓ Service {service_name} stopped")
                return 0
            else:
                print(f"✗ Failed to stop service {service_name}")
                return 1
        except Exception as e:
            print(f"✗ Error: {e}")
            return 1

    def cmd_restart(self, service_name: str) -> int:
        """
        Restart a service.

        Args:
            service_name: Name of service to restart

        Returns:
            Exit code (0 for success)
        """
        try:
            if self.manager.restart_service(service_name):
                print(f"✓ Service {service_name} restarted")
                return 0
            else:
                print(f"✗ Failed to restart service {service_name}")
                return 1
        except Exception as e:
            print(f"✗ Error: {e}")
            return 1

    def cmd_status(self, service_name: str) -> int:
        """
        Show service status.

        Args:
            service_name: Name of service

        Returns:
            Exit code (0 for success)
        """
        try:
            status = self.manager.get_status(service_name)
            print(f"Service: {status.name}")
            print(f"  State: {status.state.value}")
            print(f"  Enabled: {'yes' if status.enabled else 'no'}")
            if status.pid:
                print(f"  PID: {status.pid}")
            if status.uptime:
                print(f"  Uptime: {status.uptime}s")
            if status.error_message:
                print(f"  Error: {status.error_message}")
            return 0
        except Exception as e:
            print(f"✗ Error: {e}")
            return 1

    def cmd_list(self) -> int:
        """
        List all services.

        Returns:
            Exit code (0 for success)
        """
        services = self.manager.list_services()

        if not services:
            print("No services registered")
            return 0

        print("Services:")
        for name in sorted(services):
            status = self.manager.get_status(name)
            enabled = "enabled" if status.enabled else "disabled"
            state = status.state.value
            print(f"  {name:20s} {state:10s} [{enabled}]")

        return 0
