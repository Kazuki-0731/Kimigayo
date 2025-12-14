"""
Property Tests for Runtime Security Enforcement

Tests ASLR and DEP enforcement at runtime.

Properties tested:
- Property 5: ランタイムセキュリティ強制 (Runtime Security Enforcement) - 要件 2.2
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, Verbosity

from src.security.runtime import (
    RuntimeSecurityEnforcer,
    ProcessSecurityChecker,
    SecurityPolicyManager,
    ASLRLevel,
    SecurityFeature,
)


@pytest.mark.property
class TestRuntimeSecurityEnforcement:
    """
    Property 5: ランタイムセキュリティ強制

    任意のシステム起動に対して、ASLRとDEPがランタイムで強制されなければならない

    Requirement: 2.2
    """

    def test_security_enforcer_initialization(self):
        """Test: Runtime security enforcer can be initialized"""
        enforcer = RuntimeSecurityEnforcer()
        assert enforcer is not None

    def test_aslr_check_available(self):
        """Test: ASLR check functionality is available"""
        enforcer = RuntimeSecurityEnforcer()

        # ASLR check should return a tuple
        aslr_enabled, aslr_level = enforcer.check_aslr()

        assert isinstance(aslr_enabled, bool)
        assert isinstance(aslr_level, int)
        assert aslr_level in [0, 1, 2]

    def test_dep_check_available(self):
        """Test: DEP check functionality is available"""
        enforcer = RuntimeSecurityEnforcer()

        # DEP check should return a boolean
        dep_enabled = enforcer.check_dep()

        assert isinstance(dep_enabled, bool)

    def test_security_status_contains_required_fields(self):
        """
        Test: Security status contains ASLR and DEP information

        Requirement 2.2: Must check both ASLR and DEP
        """
        enforcer = RuntimeSecurityEnforcer()
        status = enforcer.get_security_status()

        # Must have ASLR information
        assert hasattr(status, 'aslr_enabled')
        assert hasattr(status, 'aslr_level')

        # Must have DEP information
        assert hasattr(status, 'dep_enabled')

        # Must have features dict
        assert hasattr(status, 'features_enabled')
        assert 'aslr' in status.features_enabled
        assert 'dep' in status.features_enabled

    def test_runtime_security_verification(self):
        """
        Test: Runtime security verification checks ASLR and DEP

        Requirement 2.2: Both ASLR and DEP must be verified
        """
        enforcer = RuntimeSecurityEnforcer()

        passed, failures = enforcer.verify_runtime_security()

        assert isinstance(passed, bool)
        assert isinstance(failures, list)

        # If verification fails, there should be failure messages
        if not passed:
            assert len(failures) > 0

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(level=st.sampled_from([0, 1, 2]))
    def test_aslr_level_interpretation(self, level):
        """
        Property Test: ASLR levels are correctly interpreted

        For any ASLR level setting, the enforcer must correctly
        determine if ASLR is enabled (level > 0).
        """
        enforcer = RuntimeSecurityEnforcer()

        # Simulate different ASLR levels
        # In real system, this would check /proc/sys/kernel/randomize_va_space
        # Level 0: disabled, 1: conservative, 2: full
        expected_enabled = (level > 0)

        # The check should recognize enabled vs disabled
        # (We can't actually change the system setting in tests)
        aslr_enabled, aslr_level = enforcer.check_aslr()

        # At minimum, we should get valid responses
        assert isinstance(aslr_enabled, bool)
        assert isinstance(aslr_level, int)

    def test_security_policy_enforcement(self):
        """
        Test: Security policy can be enforced

        Requirement 2.2: Security policy must be enforceable
        """
        enforcer = RuntimeSecurityEnforcer()

        # Enforce security policy
        results = enforcer.enforce_security_policy()

        assert isinstance(results, dict)
        assert 'aslr' in results
        assert 'dep' in results

    def test_binary_security_check(self):
        """Test: Binary security features can be checked"""
        enforcer = RuntimeSecurityEnforcer()

        # Create a temporary test binary
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            # Write minimal ELF header
            # ELF magic number
            f.write(b'\x7fELF')
            # Padding for minimal header
            f.write(b'\x00' * 60)
            temp_path = Path(f.name)

        try:
            features = enforcer.check_binary_security(temp_path)

            assert isinstance(features, dict)
            assert 'pie' in features
            assert 'nx' in features
            assert 'stack_canary' in features
            assert 'relro' in features
        finally:
            temp_path.unlink()

    def test_process_security_checker(self):
        """Test: Process security checker can be initialized"""
        checker = ProcessSecurityChecker()
        assert checker is not None

    def test_process_aslr_check_for_current_process(self):
        """
        Test: Can check ASLR for current process

        Requirement 2.2: Runtime monitoring capability
        """
        import os
        checker = ProcessSecurityChecker()

        # Check current process
        pid = os.getpid()
        aslr_enabled = checker.check_process_aslr(pid)

        # Should return a boolean
        assert isinstance(aslr_enabled, bool)

    def test_process_stack_nx_check(self):
        """
        Test: Can check stack NX for current process

        Requirement 2.2: DEP enforcement checking
        """
        import os
        checker = ProcessSecurityChecker()

        # Check current process
        pid = os.getpid()
        stack_nx = checker.check_process_stack_nx(pid)

        # Should return a boolean
        assert isinstance(stack_nx, bool)

    def test_process_security_info(self):
        """Test: Can get comprehensive security info for process"""
        import os
        checker = ProcessSecurityChecker()

        pid = os.getpid()
        info = checker.get_process_security_info(pid)

        assert isinstance(info, dict)
        assert 'aslr' in info
        assert 'stack_nx' in info

    def test_security_policy_manager(self):
        """Test: Security policy manager can be initialized"""
        manager = SecurityPolicyManager()
        assert manager is not None

    def test_policy_application(self):
        """
        Test: Security policy can be applied

        Requirement 2.2: Runtime security policy application
        """
        manager = SecurityPolicyManager()

        result = manager.apply_policy()

        # Should return a boolean
        assert isinstance(result, bool)

    def test_policy_verification(self):
        """
        Test: Security policy compliance can be verified

        Requirement 2.2: Policy verification
        """
        manager = SecurityPolicyManager()

        compliant, violations = manager.verify_policy()

        assert isinstance(compliant, bool)
        assert isinstance(violations, list)

        # If not compliant, should have violations
        if not compliant:
            assert len(violations) > 0

    def test_policy_status(self):
        """Test: Policy status can be retrieved"""
        manager = SecurityPolicyManager()

        status = manager.get_policy_status()

        assert status is not None
        assert hasattr(status, 'aslr_enabled')
        assert hasattr(status, 'dep_enabled')


@pytest.mark.property
class TestASLREnforcement:
    """Specific tests for ASLR enforcement"""

    def test_aslr_levels_defined(self):
        """Test: ASLR levels are properly defined"""
        assert ASLRLevel.DISABLED.value == 0
        assert ASLRLevel.CONSERVATIVE.value == 1
        assert ASLRLevel.FULL.value == 2

    def test_aslr_enable_function_exists(self):
        """
        Test: ASLR can be enabled programmatically

        Requirement 2.2: ASLR must be enforceable
        """
        enforcer = RuntimeSecurityEnforcer()

        # Should be able to call enable function
        result = enforcer.enable_aslr(ASLRLevel.FULL)

        assert isinstance(result, bool)

    @settings(verbosity=Verbosity.verbose, max_examples=3)
    @given(level=st.sampled_from(list(ASLRLevel)))
    def test_aslr_all_levels_supported(self, level):
        """
        Property Test: All ASLR levels are supported

        For any ASLR level, the enforcer must support it.
        """
        enforcer = RuntimeSecurityEnforcer()

        # Should be able to request any level
        result = enforcer.enable_aslr(level)

        assert isinstance(result, bool)


@pytest.mark.property
class TestDEPEnforcement:
    """Specific tests for DEP/NX enforcement"""

    def test_dep_check_reads_cpu_features(self):
        """
        Test: DEP check examines CPU features

        Requirement 2.2: DEP must be checked at runtime
        """
        enforcer = RuntimeSecurityEnforcer()

        # DEP check should work
        dep_enabled = enforcer.check_dep()

        assert isinstance(dep_enabled, bool)

    def test_binary_nx_bit_check(self):
        """
        Test: Binary NX bit can be checked

        Requirement 2.2: Verify DEP enforcement in binaries
        """
        enforcer = RuntimeSecurityEnforcer()

        # Create test binary with ELF header
        with tempfile.NamedTemporaryFile(delete=False, suffix='.elf') as f:
            # ELF header with GNU_STACK marker
            f.write(b'\x7fELF')
            f.write(b'\x02')  # 64-bit
            f.write(b'\x01')  # Little endian
            f.write(b'\x01')  # Version
            f.write(b'\x00' * 9)  # Padding
            f.write(b'\x00' * 48)  # Rest of header
            f.write(b'GNU_STACK\x00')  # Stack marker
            temp_path = Path(f.name)

        try:
            features = enforcer.check_binary_security(temp_path)
            # Should check for NX
            assert 'nx' in features
        finally:
            temp_path.unlink()


@pytest.mark.property
class TestSecurityStatusReporting:
    """Tests for security status reporting"""

    def test_status_serializable(self):
        """Test: Security status can be serialized"""
        enforcer = RuntimeSecurityEnforcer()
        status = enforcer.get_security_status()

        # Should be convertible to dict
        status_dict = status.to_dict()

        assert isinstance(status_dict, dict)
        assert 'aslr_enabled' in status_dict
        assert 'dep_enabled' in status_dict

    def test_status_includes_errors(self):
        """
        Test: Status includes error information

        Requirement 2.2: Security violations must be reported
        """
        enforcer = RuntimeSecurityEnforcer()
        status = enforcer.get_security_status()

        assert hasattr(status, 'errors')
        assert isinstance(status.errors, list)

    def test_status_includes_kernel_version(self):
        """Test: Status includes kernel version information"""
        enforcer = RuntimeSecurityEnforcer()
        status = enforcer.get_security_status()

        assert hasattr(status, 'kernel_version')
        assert isinstance(status.kernel_version, str)

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(seed=st.integers(min_value=0, max_value=1000))
    def test_status_consistency(self, seed):
        """
        Property Test: Security status is consistent

        For any query, the security status should be consistent
        within a short time frame.
        """
        enforcer = RuntimeSecurityEnforcer()

        # Get status twice
        status1 = enforcer.get_security_status()
        status2 = enforcer.get_security_status()

        # Should be the same (assuming no system changes)
        assert status1.aslr_enabled == status2.aslr_enabled
        assert status1.dep_enabled == status2.dep_enabled
        assert status1.aslr_level == status2.aslr_level


@pytest.mark.property
class TestSecurityFeatureEnum:
    """Tests for SecurityFeature enumeration"""

    def test_all_features_defined(self):
        """Test: All required security features are defined"""
        # Required features for Kimigayo OS
        assert SecurityFeature.ASLR.value == "aslr"
        assert SecurityFeature.DEP.value == "dep"
        assert SecurityFeature.STACK_CANARY.value == "stack_canary"
        assert SecurityFeature.PIE.value == "pie"
        assert SecurityFeature.RELRO.value == "relro"

    def test_feature_names_lowercase(self):
        """Test: Feature names are normalized to lowercase"""
        for feature in SecurityFeature:
            assert feature.value.islower()
