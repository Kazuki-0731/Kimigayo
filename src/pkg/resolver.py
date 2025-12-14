"""
Dependency Resolution Engine for Kimigayo OS Package Manager

Provides automatic dependency resolution with conflict detection.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum

from src.pkg.database import PackageMetadata, DependencyConstraint, PackageStatus


class ResolutionResult(Enum):
    """Result of dependency resolution"""
    SUCCESS = "success"
    CONFLICT = "conflict"
    MISSING_DEPENDENCY = "missing_dependency"
    CIRCULAR_DEPENDENCY = "circular_dependency"


@dataclass
class ResolutionPlan:
    """Plan for package installation/removal"""

    # Packages to install (in order)
    to_install: List[str] = field(default_factory=list)

    # Packages to remove
    to_remove: List[str] = field(default_factory=list)

    # Packages to upgrade
    to_upgrade: List[Tuple[str, str, str]] = field(default_factory=list)  # (name, old_version, new_version)

    # Result status
    result: ResolutionResult = ResolutionResult.SUCCESS

    # Error messages
    errors: List[str] = field(default_factory=list)

    # Conflicts detected
    conflicts: List[Tuple[str, str]] = field(default_factory=list)

    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)

    def add_conflict(self, pkg1: str, pkg2: str):
        """Add a conflict"""
        self.conflicts.append((pkg1, pkg2))

    def is_success(self) -> bool:
        """Check if resolution succeeded"""
        return self.result == ResolutionResult.SUCCESS and len(self.errors) == 0


class DependencyResolver:
    """Resolves package dependencies"""

    def __init__(self, available_packages: Dict[str, PackageMetadata]):
        """
        Initialize resolver.

        Args:
            available_packages: Dict mapping package name to metadata
        """
        self.available = available_packages
        self.virtual_providers: Dict[str, List[str]] = {}

        # Build virtual package map
        for name, pkg in available_packages.items():
            for virtual in pkg.provides:
                if virtual not in self.virtual_providers:
                    self.virtual_providers[virtual] = []
                self.virtual_providers[virtual].append(name)

    def resolve_install(
        self,
        package_name: str,
        installed: Optional[Set[str]] = None
    ) -> ResolutionPlan:
        """
        Resolve dependencies for installing a package.

        Args:
            package_name: Package to install
            installed: Set of currently installed packages

        Returns:
            Resolution plan
        """
        if installed is None:
            installed = set()

        plan = ResolutionPlan()

        # Check if package exists
        if package_name not in self.available:
            plan.result = ResolutionResult.MISSING_DEPENDENCY
            plan.add_error(f"Package not found: {package_name}")
            return plan

        # Resolve dependencies recursively
        visited = set()
        install_order = []

        def resolve_recursive(pkg_name: str, path: List[str]):
            """Recursively resolve dependencies"""

            # Check for circular dependencies
            if pkg_name in path:
                plan.result = ResolutionResult.CIRCULAR_DEPENDENCY
                cycle = " -> ".join(path[path.index(pkg_name):] + [pkg_name])
                plan.add_error(f"Circular dependency detected: {cycle}")
                return False

            # Skip if already installed or visited
            if pkg_name in installed or pkg_name in visited:
                return True

            visited.add(pkg_name)

            # Get package metadata
            pkg = self.available.get(pkg_name)
            if not pkg:
                # Try to resolve as virtual package
                providers = self.virtual_providers.get(pkg_name, [])
                if providers:
                    # Use first provider (could be optimized)
                    pkg_name = providers[0]
                    pkg = self.available.get(pkg_name)

                if not pkg:
                    plan.result = ResolutionResult.MISSING_DEPENDENCY
                    plan.add_error(f"Package not found: {pkg_name}")
                    return False

            # Check conflicts
            for conflict in pkg.conflicts:
                if conflict in installed or conflict in install_order:
                    plan.result = ResolutionResult.CONFLICT
                    plan.add_conflict(pkg_name, conflict)
                    plan.add_error(f"Conflict: {pkg_name} conflicts with {conflict}")
                    return False

            # Resolve dependencies first
            for dep_str in pkg.dependencies:
                constraint = DependencyConstraint.parse(dep_str)
                dep_name = constraint.package_name

                # Check if dependency is already satisfied
                if dep_name in installed:
                    # Verify version constraint
                    installed_pkg = self.available.get(dep_name)
                    if installed_pkg and constraint.is_satisfied_by(installed_pkg.version):
                        continue

                if not resolve_recursive(dep_name, path + [pkg_name]):
                    return False

            # Add to install order
            if pkg_name not in install_order:
                install_order.append(pkg_name)

            return True

        # Start resolution
        if resolve_recursive(package_name, []):
            plan.to_install = install_order
            plan.result = ResolutionResult.SUCCESS
        else:
            # Error already set in recursive function
            pass

        return plan

    def resolve_remove(
        self,
        package_name: str,
        installed: Set[str]
    ) -> ResolutionPlan:
        """
        Resolve dependencies for removing a package.

        Args:
            package_name: Package to remove
            installed: Set of currently installed packages

        Returns:
            Resolution plan
        """
        plan = ResolutionPlan()

        if package_name not in installed:
            plan.add_error(f"Package not installed: {package_name}")
            return plan

        # Find packages that depend on this one
        dependents = []
        for pkg_name in installed:
            if pkg_name == package_name:
                continue

            pkg = self.available.get(pkg_name)
            if not pkg:
                continue

            for dep_str in pkg.dependencies:
                constraint = DependencyConstraint.parse(dep_str)
                # Strip whitespace for comparison
                if constraint.package_name.strip() == package_name.strip():
                    dependents.append(pkg_name)
                    break

        if dependents:
            plan.result = ResolutionResult.CONFLICT
            plan.add_error(
                f"Cannot remove {package_name}: required by {', '.join(dependents)}"
            )
        else:
            plan.to_remove = [package_name]
            plan.result = ResolutionResult.SUCCESS

        return plan

    def find_optimal_solution(
        self,
        packages_to_install: List[str],
        installed: Set[str]
    ) -> ResolutionPlan:
        """
        Find optimal solution for installing multiple packages.
        Minimizes the number of additional packages to install.

        Args:
            packages_to_install: List of packages to install
            installed: Currently installed packages

        Returns:
            Optimized resolution plan
        """
        # Resolve each package individually
        all_to_install = set()
        plan = ResolutionPlan()

        for pkg_name in packages_to_install:
            pkg_plan = self.resolve_install(pkg_name, installed)

            if not pkg_plan.is_success():
                # Propagate errors
                plan.result = pkg_plan.result
                plan.errors.extend(pkg_plan.errors)
                plan.conflicts.extend(pkg_plan.conflicts)
                return plan

            all_to_install.update(pkg_plan.to_install)

        # Build dependency graph to determine optimal order
        install_order = []
        visited = set()

        def add_in_dependency_order(pkg_name: str):
            """Add package and its dependencies in order"""
            if pkg_name in visited:
                return

            visited.add(pkg_name)
            pkg = self.available.get(pkg_name)

            if pkg:
                # Add dependencies first
                for dep_str in pkg.dependencies:
                    constraint = DependencyConstraint.parse(dep_str)
                    dep_name = constraint.package_name

                    if dep_name in all_to_install:
                        add_in_dependency_order(dep_name)

            if pkg_name not in install_order:
                install_order.append(pkg_name)

        # Process all packages
        for pkg_name in sorted(all_to_install):  # Sort for determinism
            add_in_dependency_order(pkg_name)

        plan.to_install = install_order
        plan.result = ResolutionResult.SUCCESS
        return plan

    def check_conflicts(
        self,
        packages: List[str],
        installed: Set[str]
    ) -> List[Tuple[str, str]]:
        """
        Check for conflicts among packages.

        Args:
            packages: Packages to check
            installed: Currently installed packages

        Returns:
            List of conflicting package pairs
        """
        conflicts = []
        all_packages = set(packages) | installed

        for pkg_name in packages:
            pkg = self.available.get(pkg_name)
            if not pkg:
                continue

            for conflict in pkg.conflicts:
                if conflict in all_packages and conflict != pkg_name:
                    conflicts.append((pkg_name, conflict))

        return conflicts

    def get_dependency_graph(self, package_name: str) -> Dict[str, List[str]]:
        """
        Get dependency graph for a package.

        Returns:
            Dict mapping package name to list of its dependencies
        """
        graph = {}

        def build_graph(pkg_name: str, visited: Set[str]):
            if pkg_name in visited:
                return

            visited.add(pkg_name)
            pkg = self.available.get(pkg_name)

            if not pkg:
                return

            deps = []
            for dep_str in pkg.dependencies:
                constraint = DependencyConstraint.parse(dep_str)
                deps.append(constraint.package_name)
                build_graph(constraint.package_name, visited)

            graph[pkg_name] = deps

        build_graph(package_name, set())
        return graph
