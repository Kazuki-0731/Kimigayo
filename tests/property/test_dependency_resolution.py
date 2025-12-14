"""
Property 13: Dependency Resolution Completeness
Property 11: Optimal Dependency Resolution

Verifies that the package manager resolves all dependencies correctly and optimally.
Testing requirements 4.2 and 3.3.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path
import tempfile

from src.pkg.database import (
    PackageMetadata,
    PackageStatus,
    DependencyConstraint,
    PackageDatabase,
)
from src.pkg.resolver import (
    DependencyResolver,
    ResolutionResult,
    ResolutionPlan,
)


@st.composite
def package_name_strategy(draw):
    """Generate valid package names"""
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), min_codepoint=97, max_codepoint=122),
        min_size=2,
        max_size=20
    ))
    # Ensure name starts with a letter
    if not name or not name[0].isalpha():
        name = "pkg" + name
    return name


@pytest.mark.property
class TestDependencyResolution:
    """Test property 13 and 11: Dependency resolution completeness and optimality"""

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_linear_dependency_chain(self, num_packages):
        """
        Property: Linear dependency chain (A->B->C) is resolved completely
        """
        # Create packages with linear dependencies
        packages = {}
        for i in range(num_packages):
            deps = [f"pkg_{i-1}"] if i > 0 else []
            packages[f"pkg_{i}"] = PackageMetadata(
                name=f"pkg_{i}",
                version="1.0.0",
                architecture="x86_64",
                dependencies=deps,
                status=PackageStatus.NOT_INSTALLED
            )

        resolver = DependencyResolver(packages)

        # Resolve top-level package
        plan = resolver.resolve_install(f"pkg_{num_packages-1}")

        # Should succeed
        assert plan.is_success()
        assert len(plan.to_install) == num_packages

        # Should be in correct order (pkg_0, pkg_1, ..., pkg_n)
        expected = [f"pkg_{i}" for i in range(num_packages)]
        assert plan.to_install == expected

    @given(st.integers(min_value=2, max_value=8))
    @settings(max_examples=50)
    def test_diamond_dependency_pattern(self, depth):
        """
        Property: Diamond dependencies (A depends on B and C, both depend on D) are resolved
        """
        packages = {}

        # Root package (no dependencies)
        packages["root"] = PackageMetadata(
            name="root",
            version="1.0.0",
            architecture="x86_64",
            status=PackageStatus.NOT_INSTALLED
        )

        # Middle packages (depend on root)
        packages["mid_a"] = PackageMetadata(
            name="mid_a",
            version="1.0.0",
            architecture="x86_64",
            dependencies=["root"],
            status=PackageStatus.NOT_INSTALLED
        )
        packages["mid_b"] = PackageMetadata(
            name="mid_b",
            version="1.0.0",
            architecture="x86_64",
            dependencies=["root"],
            status=PackageStatus.NOT_INSTALLED
        )

        # Top package (depends on both middle)
        packages["top"] = PackageMetadata(
            name="top",
            version="1.0.0",
            architecture="x86_64",
            dependencies=["mid_a", "mid_b"],
            status=PackageStatus.NOT_INSTALLED
        )

        resolver = DependencyResolver(packages)
        plan = resolver.resolve_install("top")

        # Should succeed
        assert plan.is_success()

        # All packages should be installed
        assert set(plan.to_install) == {"root", "mid_a", "mid_b", "top"}

        # Root should come before middle packages
        root_idx = plan.to_install.index("root")
        mid_a_idx = plan.to_install.index("mid_a")
        mid_b_idx = plan.to_install.index("mid_b")
        top_idx = plan.to_install.index("top")

        assert root_idx < mid_a_idx
        assert root_idx < mid_b_idx
        assert mid_a_idx < top_idx
        assert mid_b_idx < top_idx

    @given(st.integers(min_value=2, max_value=8))
    @settings(max_examples=50)
    def test_circular_dependency_detected(self, num_packages):
        """
        Property: Circular dependencies are detected and rejected
        """
        # Create circular dependency
        packages = {}
        for i in range(num_packages):
            next_idx = (i + 1) % num_packages
            packages[f"pkg_{i}"] = PackageMetadata(
                name=f"pkg_{i}",
                version="1.0.0",
                architecture="x86_64",
                dependencies=[f"pkg_{next_idx}"],
                status=PackageStatus.NOT_INSTALLED
            )

        resolver = DependencyResolver(packages)
        plan = resolver.resolve_install("pkg_0")

        # Should fail with circular dependency
        assert not plan.is_success()
        assert plan.result == ResolutionResult.CIRCULAR_DEPENDENCY

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_missing_dependency_detected(self, num_packages):
        """
        Property: Missing dependencies are detected
        """
        packages = {}
        for i in range(num_packages):
            packages[f"pkg_{i}"] = PackageMetadata(
                name=f"pkg_{i}",
                version="1.0.0",
                architecture="x86_64",
                dependencies=["missing_package"],  # Depends on non-existent package
                status=PackageStatus.NOT_INSTALLED
            )

        resolver = DependencyResolver(packages)
        plan = resolver.resolve_install("pkg_0")

        # Should fail with missing dependency
        assert not plan.is_success()
        assert plan.result == ResolutionResult.MISSING_DEPENDENCY

    @given(st.lists(st.text(min_size=3, max_size=20), min_size=2, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_conflict_detection(self, package_names):
        """
        Property: Package conflicts are detected
        """
        assume(len(package_names) >= 2)

        pkg1_name = package_names[0]
        pkg2_name = package_names[1]

        packages = {
            pkg1_name: PackageMetadata(
                name=pkg1_name,
                version="1.0.0",
                architecture="x86_64",
                conflicts=[pkg2_name],
                status=PackageStatus.NOT_INSTALLED
            ),
            pkg2_name: PackageMetadata(
                name=pkg2_name,
                version="1.0.0",
                architecture="x86_64",
                status=PackageStatus.NOT_INSTALLED
            )
        }

        resolver = DependencyResolver(packages)

        # Install pkg2 first
        installed = {pkg2_name}

        # Try to install pkg1 (conflicts with pkg2)
        plan = resolver.resolve_install(pkg1_name, installed)

        # Should fail with conflict
        assert not plan.is_success()
        assert plan.result == ResolutionResult.CONFLICT

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_virtual_package_resolution(self, num_providers):
        """
        Property: Virtual packages are resolved to real packages
        """
        packages = {}

        # Create providers for virtual package
        for i in range(num_providers):
            packages[f"provider_{i}"] = PackageMetadata(
                name=f"provider_{i}",
                version="1.0.0",
                architecture="x86_64",
                provides=["virtual-pkg"],
                status=PackageStatus.NOT_INSTALLED
            )

        # Create package depending on virtual package
        packages["consumer"] = PackageMetadata(
            name="consumer",
            version="1.0.0",
            architecture="x86_64",
            dependencies=["virtual-pkg"],
            status=PackageStatus.NOT_INSTALLED
        )

        resolver = DependencyResolver(packages)
        plan = resolver.resolve_install("consumer")

        # Should succeed
        assert plan.is_success()

        # Should install consumer and one provider
        assert len(plan.to_install) == 2
        assert "consumer" in plan.to_install

        # One of the providers should be installed
        providers_in_plan = [p for p in plan.to_install if p.startswith("provider_")]
        assert len(providers_in_plan) == 1

    @given(st.integers(min_value=1, max_value=8))
    @settings(max_examples=50)
    def test_already_installed_packages_skipped(self, num_packages):
        """
        Property: Already installed packages are not reinstalled
        """
        packages = {}
        for i in range(num_packages):
            deps = [f"pkg_{i-1}"] if i > 0 else []
            packages[f"pkg_{i}"] = PackageMetadata(
                name=f"pkg_{i}",
                version="1.0.0",
                architecture="x86_64",
                dependencies=deps,
                status=PackageStatus.NOT_INSTALLED
            )

        # Mark first half as installed
        installed = {f"pkg_{i}" for i in range(num_packages // 2)}

        resolver = DependencyResolver(packages)
        plan = resolver.resolve_install(f"pkg_{num_packages-1}", installed)

        # Should succeed
        assert plan.is_success()

        # Should only install packages not yet installed
        for pkg in plan.to_install:
            assert pkg not in installed

    @given(st.lists(st.text(alphabet=st.characters(whitelist_categories=("Ll", "Nd"), min_codepoint=97, max_codepoint=122), min_size=3, max_size=20), min_size=2, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_remove_with_dependents_fails(self, package_names):
        """
        Property: Cannot remove package if other packages depend on it
        """
        assume(len(package_names) >= 2)

        pkg1_name = package_names[0]
        pkg2_name = package_names[1]

        packages = {
            pkg1_name: PackageMetadata(
                name=pkg1_name,
                version="1.0.0",
                architecture="x86_64",
                status=PackageStatus.INSTALLED
            ),
            pkg2_name: PackageMetadata(
                name=pkg2_name,
                version="1.0.0",
                architecture="x86_64",
                dependencies=[pkg1_name],
                status=PackageStatus.INSTALLED
            )
        }

        installed = {pkg1_name, pkg2_name}

        resolver = DependencyResolver(packages)
        plan = resolver.resolve_remove(pkg1_name, installed)

        # Should fail
        assert not plan.is_success()
        assert plan.result == ResolutionResult.CONFLICT

    @given(st.lists(st.text(min_size=3, max_size=20), min_size=1, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_optimal_solution_minimizes_installations(self, package_names):
        """
        Property 11: Optimal solution installs minimum necessary packages
        """
        # Create packages where some share dependencies
        packages = {}

        # Shared dependency
        packages["shared"] = PackageMetadata(
            name="shared",
            version="1.0.0",
            architecture="x86_64",
            status=PackageStatus.NOT_INSTALLED
        )

        # Packages that depend on shared
        for name in package_names:
            packages[name] = PackageMetadata(
                name=name,
                version="1.0.0",
                architecture="x86_64",
                dependencies=["shared"],
                status=PackageStatus.NOT_INSTALLED
            )

        resolver = DependencyResolver(packages)
        plan = resolver.find_optimal_solution(package_names, set())

        # Should succeed
        assert plan.is_success()

        # Should install all requested packages plus shared (only once)
        assert len(plan.to_install) == len(package_names) + 1
        assert "shared" in plan.to_install

        # Each requested package should be in plan
        for name in package_names:
            assert name in plan.to_install

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_dependency_graph_generation(self, num_packages):
        """
        Property: Dependency graph is correctly generated
        """
        packages = {}
        for i in range(num_packages):
            deps = [f"pkg_{i-1}"] if i > 0 else []
            packages[f"pkg_{i}"] = PackageMetadata(
                name=f"pkg_{i}",
                version="1.0.0",
                architecture="x86_64",
                dependencies=deps,
                status=PackageStatus.NOT_INSTALLED
            )

        resolver = DependencyResolver(packages)
        graph = resolver.get_dependency_graph(f"pkg_{num_packages-1}")

        # Should have all packages
        assert len(graph) == num_packages

        # Verify graph structure
        for i in range(num_packages):
            assert f"pkg_{i}" in graph
            if i > 0:
                assert f"pkg_{i-1}" in graph[f"pkg_{i}"]
            else:
                assert len(graph[f"pkg_{i}"]) == 0

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_version_constraint_checking(self, version_num):
        """
        Property: Version constraints are correctly checked
        """
        # Create constraint with padded version for string comparison
        version_str = f"{version_num:03d}.0.0"  # Pad for proper string comparison

        constraint = DependencyConstraint(
            package_name="test-pkg",
            operator=">=",
            version=version_str
        )

        # Test version satisfaction (equal version)
        assert constraint.is_satisfied_by(version_str)

        # Greater version
        greater_version = f"{version_num + 1:03d}.0.0"
        assert constraint.is_satisfied_by(greater_version)

        # Lesser version
        if version_num > 0:
            lesser_version = f"{version_num - 1:03d}.0.0"
            assert not constraint.is_satisfied_by(lesser_version)

    @given(st.text(alphabet=st.characters(whitelist_categories=("Ll", "Nd"), min_codepoint=97, max_codepoint=122), min_size=3, max_size=20))
    @settings(max_examples=50)
    def test_constraint_parsing(self, package_name):
        """
        Property: Dependency constraints are parsed correctly
        """
        # Sanitize package name (remove special characters that might interfere with parsing)
        package_name = package_name.strip()
        if not package_name:
            package_name = "pkg"

        # Test different constraint formats
        tests = [
            (package_name, package_name, "", ""),
            (f"{package_name}>=1.0", package_name, ">=", "1.0"),
            (f"{package_name}=2.0.0", package_name, "=", "2.0.0"),
            (f"{package_name}<=3.0", package_name, "<=", "3.0"),
        ]

        for constraint_str, expected_name, expected_op, expected_ver in tests:
            constraint = DependencyConstraint.parse(constraint_str)
            assert constraint.package_name == expected_name
            assert constraint.operator == expected_op
            assert constraint.version == expected_ver

    @given(st.integers(min_value=2, max_value=10))
    @settings(max_examples=50)
    def test_deterministic_resolution(self, num_packages):
        """
        Property: Dependency resolution is deterministic
        """
        packages = {}
        for i in range(num_packages):
            deps = [f"pkg_{i-1}"] if i > 0 else []
            packages[f"pkg_{i}"] = PackageMetadata(
                name=f"pkg_{i}",
                version="1.0.0",
                architecture="x86_64",
                dependencies=deps,
                status=PackageStatus.NOT_INSTALLED
            )

        resolver = DependencyResolver(packages)

        # Resolve multiple times
        plan1 = resolver.resolve_install(f"pkg_{num_packages-1}")
        plan2 = resolver.resolve_install(f"pkg_{num_packages-1}")
        plan3 = resolver.resolve_install(f"pkg_{num_packages-1}")

        # Results should be identical
        assert plan1.to_install == plan2.to_install
        assert plan2.to_install == plan3.to_install
        assert plan1.result == plan2.result == plan3.result
