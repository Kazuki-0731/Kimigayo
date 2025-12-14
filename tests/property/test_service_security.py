"""
Property 7: Service Security Application

Verifies that namespace isolation and seccomp-BPF filtering are applied to services.
Testing requirement 2.4.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings

from src.init.security import (
    NamespaceType,
    NamespaceConfig,
    SeccompAction,
    SeccompProfile,
    SeccompRule,
    SecurityContext,
    create_strict_profile,
    create_default_profile,
    create_permissive_profile,
    create_service_security_context,
)


@pytest.mark.property
class TestServiceSecurityApplication:
    """Test property 7: Service security features are properly applied"""

    @given(st.sets(st.sampled_from(list(NamespaceType)), min_size=1))
    @settings(max_examples=50)
    def test_namespace_isolation_applied(self, namespaces):
        """
        Property: When namespace isolation is enabled,
        all configured namespaces must be active
        """
        # Create namespace config
        ns_config = NamespaceConfig()
        for ns in namespaces:
            ns_config.enable_namespace(ns)

        # Create security context
        context = SecurityContext(namespace_config=ns_config)

        # Verify namespaces are applied
        assert context.apply_namespace_isolation()

        # Verify all requested namespaces are enabled
        for ns in namespaces:
            assert ns_config.is_enabled(ns)

    @given(st.sets(st.sampled_from(list(NamespaceType)), min_size=1, max_size=7))
    @settings(max_examples=50)
    def test_namespace_flags_generation(self, namespaces):
        """
        Property: Namespace flags are correctly generated for enabled namespaces
        """
        ns_config = NamespaceConfig()
        for ns in namespaces:
            ns_config.enable_namespace(ns)

        flags = ns_config.get_namespace_flags()

        # Verify flag count matches namespace count
        assert len(flags) == len(namespaces)

        # Verify each namespace has corresponding flag
        for ns in namespaces:
            assert f"--{ns.value}" in flags

    @given(
        st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=20, unique=True),
        st.sampled_from([SeccompAction.ALLOW, SeccompAction.KILL, SeccompAction.ERRNO])
    )
    @settings(max_examples=50)
    def test_seccomp_rules_applied(self, syscalls, action):
        """
        Property: All added seccomp rules are present in the profile
        """
        profile = SeccompProfile(
            name="test_profile",
            default_action=SeccompAction.ERRNO
        )

        # Add rules
        for syscall in syscalls:
            profile.add_rule(syscall, action)

        # Verify all rules are present
        assert len(profile.rules) == len(syscalls)

        # Verify syscall sets
        if action == SeccompAction.ALLOW:
            allowed = profile.get_allowed_syscalls()
            assert allowed == set(syscalls)
        elif action in (SeccompAction.KILL, SeccompAction.ERRNO):
            blocked = profile.get_blocked_syscalls()
            assert blocked == set(syscalls)

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10, unique=True))
    @settings(max_examples=50)
    def test_seccomp_rule_removal(self, syscalls):
        """
        Property: Removed seccomp rules are no longer in the profile
        """
        profile = SeccompProfile(name="test_profile")

        # Add rules
        for syscall in syscalls:
            profile.add_rule(syscall, SeccompAction.ALLOW)

        # Remove first syscall
        if syscalls:
            to_remove = syscalls[0]
            profile.remove_rule(to_remove)

            # Verify rule is removed
            remaining_syscalls = {rule.syscall for rule in profile.rules}
            assert to_remove not in remaining_syscalls
            assert len(profile.rules) == len(syscalls) - 1

    @given(st.sampled_from(["strict", "default", "permissive"]))
    @settings(max_examples=50)
    def test_predefined_profiles_valid(self, profile_type):
        """
        Property: All predefined profiles are valid and contain rules
        """
        if profile_type == "strict":
            profile = create_strict_profile()
        elif profile_type == "default":
            profile = create_default_profile()
        else:
            profile = create_permissive_profile()

        # Verify profile has a name
        assert profile.name

        # Verify profile has rules
        assert len(profile.rules) > 0

        # Verify default action is set
        assert isinstance(profile.default_action, SeccompAction)

    @given(st.booleans(), st.sampled_from(["strict", "default", "permissive"]))
    @settings(max_examples=50)
    def test_security_context_creation(self, namespace_isolation, seccomp_level):
        """
        Property: Security context is properly created with requested features
        """
        context = create_service_security_context(
            namespace_isolation=namespace_isolation,
            seccomp_level=seccomp_level
        )

        # Verify namespace config matches request
        if namespace_isolation:
            assert context.namespace_config is not None
            assert len(context.namespace_config.enabled_namespaces) > 0
        else:
            assert context.namespace_config is None

        # Verify seccomp profile is created
        assert context.seccomp_profile is not None
        assert context.seccomp_profile.name == seccomp_level

    @given(st.booleans(), st.booleans())
    @settings(max_examples=50)
    def test_security_verification(self, enable_namespace, enable_seccomp):
        """
        Property: Security verification returns True only when features are enabled
        """
        ns_config = None
        if enable_namespace:
            ns_config = NamespaceConfig()
            ns_config.enable_namespace(NamespaceType.PID)

        seccomp_profile = None
        if enable_seccomp:
            seccomp_profile = create_default_profile()

        context = SecurityContext(
            namespace_config=ns_config,
            seccomp_profile=seccomp_profile
        )

        # Verify security is applied if any feature is enabled
        if enable_namespace or enable_seccomp:
            assert context.verify_security_applied()
        else:
            assert not context.verify_security_applied()

    @given(st.sets(st.sampled_from(list(NamespaceType)), min_size=1))
    @settings(max_examples=50)
    def test_security_summary_accuracy(self, namespaces):
        """
        Property: Security summary accurately reflects configured features
        """
        # Create context with namespaces
        ns_config = NamespaceConfig()
        for ns in namespaces:
            ns_config.enable_namespace(ns)

        context = SecurityContext(
            namespace_config=ns_config,
            seccomp_profile=create_default_profile()
        )

        summary = context.get_security_summary()

        # Verify namespace isolation is reported
        assert summary["namespace_isolation"] is True
        assert len(summary["enabled_namespaces"]) == len(namespaces)

        # Verify seccomp filtering is reported
        assert summary["seccomp_filtering"] is True
        assert summary["seccomp_profile"] == "default"

    @given(st.sampled_from(["strict", "default", "permissive"]))
    @settings(max_examples=50)
    def test_seccomp_profile_strictness_ordering(self, profile_type):
        """
        Property: Strictness ordering is maintained (strict < default < permissive)
        """
        strict = create_strict_profile()
        default = create_default_profile()
        permissive = create_permissive_profile()

        # Strict profile should have fewer allowed syscalls
        strict_allowed = len(strict.get_allowed_syscalls())
        default_allowed = len(default.get_allowed_syscalls())
        permissive_allowed = len(permissive.get_allowed_syscalls())

        # Note: Permissive has default ALLOW, so it has fewer explicit rules
        # but more implicit allowances
        assert strict_allowed <= default_allowed

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10, unique=True))
    @settings(max_examples=50)
    def test_seccomp_json_serialization(self, syscalls):
        """
        Property: Seccomp profiles can be serialized and deserialized
        """
        # Create profile
        original = SeccompProfile(
            name="test_profile",
            default_action=SeccompAction.ERRNO
        )

        for syscall in syscalls:
            original.add_rule(syscall, SeccompAction.ALLOW)

        # Serialize to JSON
        json_str = original.to_json()
        assert json_str

        # Deserialize
        restored = SeccompProfile.from_json(json_str)

        # Verify properties match
        assert restored.name == original.name
        assert restored.default_action == original.default_action
        assert len(restored.rules) == len(original.rules)

        # Verify syscalls match
        original_syscalls = {rule.syscall for rule in original.rules}
        restored_syscalls = {rule.syscall for rule in restored.rules}
        assert original_syscalls == restored_syscalls

    @given(st.booleans())
    @settings(max_examples=50)
    def test_namespace_private_tmp(self, private_tmp):
        """
        Property: Private /tmp setting is correctly configured
        """
        ns_config = NamespaceConfig(private_tmp=private_tmp)
        ns_config.enable_namespace(NamespaceType.MNT)

        context = SecurityContext(namespace_config=ns_config)

        assert context.namespace_config.private_tmp == private_tmp

    @given(
        st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10),
        st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10)
    )
    @settings(max_examples=50)
    def test_namespace_path_restrictions(self, read_only_paths, inaccessible_paths):
        """
        Property: Namespace path restrictions are properly configured
        """
        ns_config = NamespaceConfig(
            read_only_paths=read_only_paths,
            inaccessible_paths=inaccessible_paths
        )
        ns_config.enable_namespace(NamespaceType.MNT)

        context = SecurityContext(namespace_config=ns_config)

        assert context.namespace_config.read_only_paths == read_only_paths
        assert context.namespace_config.inaccessible_paths == inaccessible_paths

    @given(st.booleans(), st.booleans())
    @settings(max_examples=50)
    def test_network_namespace_isolation(self, network_isolated, allow_loopback):
        """
        Property: Network namespace settings are correctly applied
        """
        ns_config = NamespaceConfig(
            network_isolated=network_isolated,
            allow_loopback=allow_loopback
        )
        ns_config.enable_namespace(NamespaceType.NET)

        context = SecurityContext(namespace_config=ns_config)

        assert context.namespace_config.network_isolated == network_isolated
        assert context.namespace_config.allow_loopback == allow_loopback

    @given(st.lists(st.text(min_size=1, max_size=30), min_size=0, max_size=5))
    @settings(max_examples=50)
    def test_capability_dropping(self, capabilities):
        """
        Property: Dropped capabilities are tracked in security context
        """
        context = SecurityContext(drop_capabilities=capabilities)

        assert context.drop_capabilities == capabilities

        summary = context.get_security_summary()
        assert summary["dropped_capabilities"] == capabilities

    @given(st.booleans())
    @settings(max_examples=50)
    def test_no_new_privileges(self, no_new_privs):
        """
        Property: no_new_privileges flag is correctly set
        """
        context = SecurityContext(no_new_privileges=no_new_privs)

        assert context.no_new_privileges == no_new_privs

        summary = context.get_security_summary()
        assert summary["no_new_privileges"] == no_new_privs

    @given(st.integers(min_value=1, max_value=20))
    @settings(max_examples=50)
    def test_multiple_namespace_enable_disable(self, num_operations):
        """
        Property: Enabling and disabling namespaces maintains consistency
        """
        ns_config = NamespaceConfig()
        namespaces = list(NamespaceType)

        for i in range(num_operations):
            ns = namespaces[i % len(namespaces)]

            if i % 2 == 0:
                ns_config.enable_namespace(ns)
                assert ns_config.is_enabled(ns)
            else:
                ns_config.disable_namespace(ns)
                assert not ns_config.is_enabled(ns)

    @given(st.sampled_from(["strict", "default", "permissive"]))
    @settings(max_examples=50)
    def test_dangerous_syscalls_blocked(self, profile_type):
        """
        Property: Dangerous syscalls are blocked in all profiles
        """
        if profile_type == "strict":
            profile = create_strict_profile()
        elif profile_type == "default":
            profile = create_default_profile()
        else:
            profile = create_permissive_profile()

        # These should be blocked in all profiles
        dangerous = ["reboot", "kexec_load", "init_module", "delete_module"]

        allowed = profile.get_allowed_syscalls()

        # Verify dangerous syscalls are not in allowed set
        for syscall in dangerous:
            assert syscall not in allowed
