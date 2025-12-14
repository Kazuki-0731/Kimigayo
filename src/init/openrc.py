"""
OpenRC-based Init System for Kimigayo OS

Provides system initialization, service management, and dependency resolution.
Based on OpenRC design principles with security hardening.
"""

import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any
import hashlib
import json


class RunLevel(Enum):
    """System runlevels"""
    SYSINIT = "sysinit"     # System initialization
    BOOT = "boot"           # Boot-time services
    DEFAULT = "default"     # Normal operation
    SHUTDOWN = "shutdown"   # System shutdown


class ServiceState(Enum):
    """Service states"""
    STOPPED = "stopped"
    STARTING = "starting"
    STARTED = "started"
    STOPPING = "stopping"
    FAILED = "failed"
    INACTIVE = "inactive"


@dataclass
class ServiceConfig:
    """Configuration for a system service"""
    name: str
    description: str = ""

    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # Services that must start before this one
    provides: List[str] = field(default_factory=list)      # Virtual services this provides
    before: List[str] = field(default_factory=list)        # Services that must start after this one
    after: List[str] = field(default_factory=list)         # Services to start after

    # Service script paths
    start_script: Optional[Path] = None
    stop_script: Optional[Path] = None

    # Runlevels
    runlevels: List[RunLevel] = field(default_factory=lambda: [RunLevel.DEFAULT])

    # Security settings
    enable_namespace_isolation: bool = False
    enable_seccomp: bool = False
    seccomp_profile: Optional[str] = None  # Path to seccomp profile or profile name
    namespace_config: Optional[Dict[str, Any]] = None  # Namespace configuration

    # Recovery settings
    restart_on_failure: bool = False
    max_restart_attempts: int = 3
    restart_delay_seconds: int = 5

    def __post_init__(self):
        """Validate configuration"""
        if not self.name:
            raise ValueError("Service name cannot be empty")

        # Convert paths to Path objects
        if isinstance(self.start_script, str):
            self.start_script = Path(self.start_script)
        if isinstance(self.stop_script, str):
            self.stop_script = Path(self.stop_script)


@dataclass
class ServiceStatus:
    """Current status of a service"""
    name: str
    state: ServiceState
    pid: Optional[int] = None
    uptime_seconds: int = 0
    restart_count: int = 0
    last_error: Optional[str] = None


@dataclass
class InitConfig:
    """Configuration for the init system"""

    # Directory structure
    init_scripts_dir: Path = Path("/etc/init.d")
    runlevels_dir: Path = Path("/etc/runlevels")
    conf_dir: Path = Path("/etc/conf.d")

    # System settings
    default_runlevel: RunLevel = RunLevel.DEFAULT
    enable_parallel_startup: bool = True
    startup_timeout_seconds: int = 300  # 5 minutes

    # Security settings
    enforce_security_policies: bool = True
    enable_service_isolation: bool = True

    # Logging
    log_file: Path = Path("/var/log/init.log")
    log_level: str = "INFO"

    def __post_init__(self):
        """Convert string paths to Path objects"""
        if isinstance(self.init_scripts_dir, str):
            self.init_scripts_dir = Path(self.init_scripts_dir)
        if isinstance(self.runlevels_dir, str):
            self.runlevels_dir = Path(self.runlevels_dir)
        if isinstance(self.conf_dir, str):
            self.conf_dir = Path(self.conf_dir)
        if isinstance(self.log_file, str):
            self.log_file = Path(self.log_file)


class DependencyResolver:
    """Resolves service dependencies and determines startup order"""

    def __init__(self):
        self.services: Dict[str, ServiceConfig] = {}
        self.virtual_services: Dict[str, str] = {}  # Maps virtual service name to actual service

    def add_service(self, service: ServiceConfig):
        """Add a service to the dependency graph"""
        self.services[service.name] = service

        # Register virtual services
        for virtual in service.provides:
            self.virtual_services[virtual] = service.name

    def resolve_dependency_order(self, runlevel: RunLevel) -> List[str]:
        """
        Resolve the order in which services should be started for a runlevel.
        Returns a list of service names in dependency order.
        Raises ValueError if circular dependencies are detected.
        """
        # Filter services by runlevel
        services_to_start = [
            name for name, svc in self.services.items()
            if runlevel in svc.runlevels
        ]

        # Build dependency graph
        # Graph maps from dependency -> dependent (reverse direction for topological sort)
        graph: Dict[str, Set[str]] = {name: set() for name in services_to_start}

        for name in services_to_start:
            service = self.services[name]

            for dep in service.dependencies:
                # Resolve virtual services
                actual_dep = self.virtual_services.get(dep, dep)

                if actual_dep in services_to_start:
                    # Add edge from dependency to dependent
                    graph[actual_dep].add(name)

        # Topological sort using Kahn's algorithm
        return self._topological_sort(graph)

    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[str]:
        """
        Perform topological sort on dependency graph.
        Raises ValueError if circular dependencies detected.
        """
        # Count incoming edges
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1

        # Find nodes with no incoming edges
        queue = [node for node in graph if in_degree[node] == 0]
        result = []

        while queue:
            # Sort queue for deterministic ordering
            queue.sort()
            node = queue.pop(0)
            result.append(node)

            # Remove edges from this node
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(result) != len(graph):
            raise ValueError("Circular dependency detected in service dependencies")

        return result

    def get_dependencies(self, service_name: str) -> Set[str]:
        """Get all dependencies for a service"""
        if service_name not in self.services:
            return set()

        service = self.services[service_name]
        deps = set()

        for dep in service.dependencies:
            actual_dep = self.virtual_services.get(dep, dep)
            deps.add(actual_dep)

        return deps


class InitSystem:
    """Main init system implementation"""

    def __init__(self, config: InitConfig):
        self.config = config
        self.resolver = DependencyResolver()
        self.service_states: Dict[str, ServiceStatus] = {}
        self.current_runlevel = RunLevel.SYSINIT

    def register_service(self, service: ServiceConfig):
        """Register a service with the init system"""
        self.resolver.add_service(service)
        self.service_states[service.name] = ServiceStatus(
            name=service.name,
            state=ServiceState.INACTIVE
        )

    def start_service(self, service_name: str) -> bool:
        """
        Start a single service.
        Returns True if service started successfully, False otherwise.
        """
        if service_name not in self.resolver.services:
            raise ValueError(f"Unknown service: {service_name}")

        service = self.resolver.services[service_name]
        status = self.service_states[service_name]

        # Check if already started
        if status.state == ServiceState.STARTED:
            return True

        # Update state
        status.state = ServiceState.STARTING

        try:
            # Start dependencies first
            for dep in self.resolver.get_dependencies(service_name):
                if not self.start_service(dep):
                    status.state = ServiceState.FAILED
                    status.last_error = f"Dependency {dep} failed to start"
                    return False

            # Execute start script (mock implementation)
            if service.start_script and service.start_script.exists():
                # In real implementation, would execute the script
                pass

            # Mark as started
            status.state = ServiceState.STARTED
            status.restart_count = 0
            return True

        except Exception as e:
            status.state = ServiceState.FAILED
            status.last_error = str(e)
            return False

    def stop_service(self, service_name: str) -> bool:
        """
        Stop a single service.
        Returns True if service stopped successfully, False otherwise.
        """
        if service_name not in self.resolver.services:
            raise ValueError(f"Unknown service: {service_name}")

        service = self.resolver.services[service_name]
        status = self.service_states[service_name]

        # Check if already stopped
        if status.state == ServiceState.STOPPED:
            return True

        # Update state
        status.state = ServiceState.STOPPING

        try:
            # Execute stop script (mock implementation)
            if service.stop_script and service.stop_script.exists():
                # In real implementation, would execute the script
                pass

            # Mark as stopped
            status.state = ServiceState.STOPPED
            status.pid = None
            return True

        except Exception as e:
            status.state = ServiceState.FAILED
            status.last_error = str(e)
            return False

    def restart_service(self, service_name: str) -> bool:
        """Restart a service"""
        if self.stop_service(service_name):
            return self.start_service(service_name)
        return False

    def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """Get current status of a service"""
        return self.service_states.get(service_name)

    def switch_runlevel(self, runlevel: RunLevel) -> bool:
        """
        Switch to a different runlevel.
        Returns True if successful, False otherwise.
        """
        try:
            # Get startup order for new runlevel
            startup_order = self.resolver.resolve_dependency_order(runlevel)

            # Start services in order
            for service_name in startup_order:
                self.start_service(service_name)

            self.current_runlevel = runlevel
            return True

        except Exception as e:
            return False

    def shutdown(self) -> bool:
        """
        Gracefully shutdown all services.
        Returns True if all services stopped successfully.
        """
        # Stop services in reverse dependency order
        try:
            startup_order = self.resolver.resolve_dependency_order(self.current_runlevel)
            shutdown_order = list(reversed(startup_order))

            all_stopped = True
            for service_name in shutdown_order:
                if not self.stop_service(service_name):
                    all_stopped = False

            return all_stopped

        except Exception:
            return False


def build_init_system(config: InitConfig, services: List[ServiceConfig]) -> InitSystem:
    """
    Build and configure an init system with the given services.

    Args:
        config: Init system configuration
        services: List of services to register

    Returns:
        Configured InitSystem instance
    """
    init_system = InitSystem(config)

    for service in services:
        init_system.register_service(service)

    return init_system
