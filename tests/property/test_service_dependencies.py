"""
Property 24: Service Dependency Order

Verifies that the init system starts services in correct dependency order.
Testing requirement 7.2.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path

from src.init.openrc import (
    InitConfig,
    ServiceConfig,
    RunLevel,
    DependencyResolver,
    InitSystem,
    build_init_system,
)


# Strategy for generating valid service names
@st.composite
def service_name_strategy(draw):
    """Generate valid service names"""
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), max_codepoint=127),
        min_size=1,
        max_size=20
    ))
    # Ensure name starts with a letter
    if not name or not name[0].isalpha():
        name = "svc" + name
    return name


# Strategy for generating service configurations
@st.composite
def service_config_strategy(draw, name=None, available_services=None):
    """Generate a valid service configuration"""
    if name is None:
        name = draw(service_name_strategy())

    description = draw(st.text(max_size=100))

    # Generate dependencies from available services
    dependencies = []
    if available_services:
        num_deps = draw(st.integers(min_value=0, max_value=min(3, len(available_services))))
        dependencies = draw(st.lists(
            st.sampled_from(available_services),
            min_size=num_deps,
            max_size=num_deps,
            unique=True
        ))

    runlevel = draw(st.sampled_from([RunLevel.BOOT, RunLevel.DEFAULT]))

    return ServiceConfig(
        name=name,
        description=description,
        dependencies=dependencies,
        runlevels=[runlevel],
    )


@pytest.mark.property
class TestServiceDependencyOrder:
    """Test property 24: Service dependency order correctness"""

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_linear_dependency_chain(self, num_services):
        """
        Property: For a linear dependency chain (A->B->C->D),
        services must start in correct order
        """
        # Create linear chain of services
        services = []
        for i in range(num_services):
            deps = [f"service_{i-1}"] if i > 0 else []
            services.append(ServiceConfig(
                name=f"service_{i}",
                dependencies=deps,
                runlevels=[RunLevel.DEFAULT]
            ))

        # Build init system
        config = InitConfig()
        init_system = build_init_system(config, services)

        # Get startup order
        order = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)

        # Verify order is correct (service_0, service_1, ..., service_n)
        expected_order = [f"service_{i}" for i in range(num_services)]
        assert order == expected_order

        # Verify each service appears before its dependents
        for i, service_name in enumerate(order):
            service_idx = int(service_name.split("_")[1])
            # All services with higher index should come after this one
            for j in range(i + 1, len(order)):
                later_service_idx = int(order[j].split("_")[1])
                if service_idx > 0:
                    assert later_service_idx >= service_idx

    @given(st.integers(min_value=2, max_value=8))
    @settings(max_examples=50)
    def test_diamond_dependency_pattern(self, num_layers):
        """
        Property: For diamond dependency pattern (A depends on B and C,
        both B and C depend on D), D must start first
        """
        services = []

        # Root service (no dependencies)
        services.append(ServiceConfig(
            name="root",
            dependencies=[],
            runlevels=[RunLevel.DEFAULT]
        ))

        # Middle layer services (depend on root)
        services.append(ServiceConfig(
            name="middle_1",
            dependencies=["root"],
            runlevels=[RunLevel.DEFAULT]
        ))
        services.append(ServiceConfig(
            name="middle_2",
            dependencies=["root"],
            runlevels=[RunLevel.DEFAULT]
        ))

        # Top service (depends on both middle services)
        services.append(ServiceConfig(
            name="top",
            dependencies=["middle_1", "middle_2"],
            runlevels=[RunLevel.DEFAULT]
        ))

        # Build init system
        config = InitConfig()
        init_system = build_init_system(config, services)

        # Get startup order
        order = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)

        # Verify root comes first
        assert order[0] == "root"

        # Verify middle services come before top
        middle_1_idx = order.index("middle_1")
        middle_2_idx = order.index("middle_2")
        top_idx = order.index("top")

        assert middle_1_idx < top_idx
        assert middle_2_idx < top_idx

    @given(st.integers(min_value=3, max_value=10))
    @settings(max_examples=50)
    def test_no_circular_dependencies_detected(self, num_services):
        """
        Property: Circular dependencies must be detected and rejected
        """
        # Create a circular dependency: A->B->C->A
        services = []
        for i in range(num_services):
            next_idx = (i + 1) % num_services
            services.append(ServiceConfig(
                name=f"service_{i}",
                dependencies=[f"service_{next_idx}"],
                runlevels=[RunLevel.DEFAULT]
            ))

        # Build init system
        config = InitConfig()
        init_system = build_init_system(config, services)

        # Attempting to resolve should raise ValueError
        with pytest.raises(ValueError, match="Circular dependency"):
            init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_independent_services_can_start_in_any_order(self, num_services):
        """
        Property: Services with no dependencies can start in any order
        """
        # Create independent services
        services = []
        for i in range(num_services):
            services.append(ServiceConfig(
                name=f"service_{i}",
                dependencies=[],
                runlevels=[RunLevel.DEFAULT]
            ))

        # Build init system
        config = InitConfig()
        init_system = build_init_system(config, services)

        # Get startup order
        order = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)

        # Verify all services are in the order
        assert len(order) == num_services
        assert set(order) == {f"service_{i}" for i in range(num_services)}

    @given(st.integers(min_value=1, max_value=8))
    @settings(max_examples=50)
    def test_virtual_service_resolution(self, num_services):
        """
        Property: Virtual services (provides) are correctly resolved
        """
        # Create a service that provides a virtual service
        provider = ServiceConfig(
            name="network_provider",
            provides=["network"],
            runlevels=[RunLevel.DEFAULT]
        )

        # Create services that depend on the virtual service
        dependents = []
        for i in range(num_services):
            dependents.append(ServiceConfig(
                name=f"service_{i}",
                dependencies=["network"],
                runlevels=[RunLevel.DEFAULT]
            ))

        # Build init system
        config = InitConfig()
        all_services = [provider] + dependents
        init_system = build_init_system(config, all_services)

        # Get startup order
        order = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)

        # Verify provider starts first
        assert order[0] == "network_provider"

        # Verify all dependents start after provider
        provider_idx = order.index("network_provider")
        for i in range(num_services):
            dependent_idx = order.index(f"service_{i}")
            assert dependent_idx > provider_idx

    @given(st.integers(min_value=2, max_value=10))
    @settings(max_examples=50)
    def test_runlevel_filtering(self, num_services):
        """
        Property: Only services for the target runlevel are started
        """
        # Create services split between boot and default runlevels
        services = []
        for i in range(num_services):
            runlevel = RunLevel.BOOT if i % 2 == 0 else RunLevel.DEFAULT
            services.append(ServiceConfig(
                name=f"service_{i}",
                runlevels=[runlevel]
            ))

        # Build init system
        config = InitConfig()
        init_system = build_init_system(config, services)

        # Get startup order for BOOT runlevel
        boot_order = init_system.resolver.resolve_dependency_order(RunLevel.BOOT)

        # Verify only boot services are included
        expected_boot_services = {f"service_{i}" for i in range(0, num_services, 2)}
        assert set(boot_order) == expected_boot_services

        # Get startup order for DEFAULT runlevel
        default_order = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)

        # Verify only default services are included
        expected_default_services = {f"service_{i}" for i in range(1, num_services, 2)}
        assert set(default_order) == expected_default_services

    @given(st.integers(min_value=3, max_value=10))
    @settings(max_examples=50)
    def test_dependency_transitivity(self, num_services):
        """
        Property: If A depends on B and B depends on C, then A transitively depends on C
        """
        # Create chain: service_0 <- service_1 <- service_2 <- ... <- service_n
        services = []
        for i in range(num_services):
            deps = [f"service_{i-1}"] if i > 0 else []
            services.append(ServiceConfig(
                name=f"service_{i}",
                dependencies=deps,
                runlevels=[RunLevel.DEFAULT]
            ))

        # Build init system
        config = InitConfig()
        init_system = build_init_system(config, services)

        # Get startup order
        order = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)

        # For each service, verify all transitive dependencies start before it
        for i in range(1, num_services):
            service_idx = order.index(f"service_{i}")

            # All services 0..i-1 should start before service_i
            for j in range(i):
                dep_idx = order.index(f"service_{j}")
                assert dep_idx < service_idx, (
                    f"service_{j} should start before service_{i}"
                )

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_deterministic_ordering(self, num_services):
        """
        Property: Dependency resolution must be deterministic
        """
        # Create services with no dependencies
        services = []
        for i in range(num_services):
            services.append(ServiceConfig(
                name=f"service_{i}",
                runlevels=[RunLevel.DEFAULT]
            ))

        # Build init system
        config = InitConfig()
        init_system = build_init_system(config, services)

        # Resolve order multiple times
        order1 = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)
        order2 = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)
        order3 = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)

        # Verify all resolutions produce same order
        assert order1 == order2
        assert order2 == order3

    @given(st.integers(min_value=1, max_value=8))
    @settings(max_examples=50)
    def test_partial_dependency_ordering(self, num_branches):
        """
        Property: Services are started respecting partial ordering constraints
        """
        # Create a root service
        services = [ServiceConfig(
            name="root",
            runlevels=[RunLevel.DEFAULT]
        )]

        # Create branches that depend on root
        for i in range(num_branches):
            # Branch root depends on main root
            services.append(ServiceConfig(
                name=f"branch_{i}_root",
                dependencies=["root"],
                runlevels=[RunLevel.DEFAULT]
            ))

            # Branch leaf depends on branch root
            services.append(ServiceConfig(
                name=f"branch_{i}_leaf",
                dependencies=[f"branch_{i}_root"],
                runlevels=[RunLevel.DEFAULT]
            ))

        # Build init system
        config = InitConfig()
        init_system = build_init_system(config, services)

        # Get startup order
        order = init_system.resolver.resolve_dependency_order(RunLevel.DEFAULT)

        # Verify root is first
        assert order[0] == "root"

        # Verify each branch's ordering
        root_idx = order.index("root")
        for i in range(num_branches):
            branch_root_idx = order.index(f"branch_{i}_root")
            branch_leaf_idx = order.index(f"branch_{i}_leaf")

            # Branch root must come after main root
            assert branch_root_idx > root_idx

            # Branch leaf must come after branch root
            assert branch_leaf_idx > branch_root_idx
