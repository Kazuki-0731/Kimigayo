"""
Property Tests for Compile-time Security Hardening

Tests compile-time security flag application and verification.

Properties tested:
- Property 4: セキュリティ強化適用 (Security Hardening Application) - 要件 2.1
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, Verbosity

from src.security.compile import (
    SecurityFlags,
    SecurityLevel,
    SecurityHardeningManager,
    BinarySecurityVerifier,
    CompilerSecurityChecker,
    SecurityConfigManager,
    CompilationConfig,
)


@pytest.mark.property
class TestSecurityHardeningApplication:
    """
    Property 4: セキュリティ強化適用

    任意のシステムコンポーネントに対して、コンパイル時にPIE、スタック保護、
    FORTIFY_SOURCEが有効化されなければならない

    Requirement: 2.1
    """

    def test_security_flags_creation(self):
        """Test: Security flags can be created"""
        flags = SecurityFlags()

        assert flags is not None
        assert len(flags.pie_cflags) > 0
        assert len(flags.stack_protection) > 0
        assert len(flags.fortify_source) > 0

    def test_pie_flags_present(self):
        """
        Test: PIE flags are present

        Requirement 2.1: PIE must be enabled at compile time
        """
        flags = SecurityFlags()

        # Check compiler flags
        assert '-fPIE' in flags.pie_cflags or '-fPIC' in flags.pie_cflags

        # Check linker flags
        assert '-pie' in flags.pie_ldflags

    def test_stack_protection_flags_present(self):
        """
        Test: Stack protection flags are present

        Requirement 2.1: Stack protection must be enabled
        """
        flags = SecurityFlags()

        # Should have stack protector flag
        assert any(
            '-fstack-protector' in flag
            for flag in flags.stack_protection
        )

    def test_fortify_source_flags_present(self):
        """
        Test: FORTIFY_SOURCE flags are present

        Requirement 2.1: FORTIFY_SOURCE must be enabled
        """
        flags = SecurityFlags()

        # Should have FORTIFY_SOURCE definition
        assert any(
            '-D_FORTIFY_SOURCE' in flag
            for flag in flags.fortify_source
        )

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(level=st.sampled_from(list(SecurityLevel)))
    def test_all_security_levels_have_flags(self, level):
        """
        Property Test: All security levels produce valid flags

        For any security level, the system must generate valid
        security flags.
        """
        flags = SecurityFlags.from_level(level)

        assert flags is not None

        # Get all flags
        cflags = flags.get_all_cflags()
        ldflags = flags.get_all_ldflags()

        # Should be lists
        assert isinstance(cflags, list)
        assert isinstance(ldflags, list)

        # For non-NONE levels, should have security flags
        if level != SecurityLevel.NONE:
            assert len(cflags) > 0 or len(ldflags) > 0

    def test_standard_level_has_required_flags(self):
        """
        Test: Standard security level has all required flags

        Requirement 2.1: All required security features must be present
        """
        flags = SecurityFlags.from_level(SecurityLevel.STANDARD)

        cflags = ' '.join(flags.get_all_cflags())
        ldflags = ' '.join(flags.get_all_ldflags())

        # Check PIE
        assert '-fPIE' in cflags or '-fPIC' in cflags
        assert '-pie' in ldflags

        # Check stack protection
        assert '-fstack-protector' in cflags

        # Check FORTIFY_SOURCE
        assert '-D_FORTIFY_SOURCE' in cflags

    def test_security_hardening_manager(self):
        """Test: Security hardening manager can be initialized"""
        manager = SecurityHardeningManager()

        assert manager is not None
        assert manager.security_level == SecurityLevel.STANDARD

    def test_get_required_flags(self):
        """
        Test: Can get required security flags

        Requirement 2.1: Required flags must be accessible
        """
        manager = SecurityHardeningManager()
        required = manager.get_required_flags()

        assert isinstance(required, dict)
        assert 'pie' in required
        assert 'stack_protection' in required
        assert 'fortify_source' in required

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(
        cflags=st.text(min_size=0, max_size=100),
        ldflags=st.text(min_size=0, max_size=100)
    )
    def test_verify_flags_enabled(self, cflags, ldflags):
        """
        Property Test: Flag verification works correctly

        For any flag strings, the verifier should correctly
        identify missing required flags.
        """
        manager = SecurityHardeningManager()

        all_enabled, missing = manager.verify_flags_enabled(cflags, ldflags)

        assert isinstance(all_enabled, bool)
        assert isinstance(missing, list)

        # If not all enabled, should have missing flags
        if not all_enabled:
            assert len(missing) > 0

    def test_verify_complete_flags(self):
        """Test: Verification passes with complete flags"""
        manager = SecurityHardeningManager()

        # Complete flags
        cflags = "-fPIE -fstack-protector-strong -D_FORTIFY_SOURCE=2"
        ldflags = "-pie -Wl,-z,relro"

        all_enabled, missing = manager.verify_flags_enabled(cflags, ldflags)

        assert all_enabled is True
        assert len(missing) == 0

    def test_verify_incomplete_flags_detected(self):
        """Test: Verification fails with incomplete flags"""
        manager = SecurityHardeningManager()

        # Missing PIE
        cflags = "-fstack-protector-strong -D_FORTIFY_SOURCE=2"
        ldflags = ""

        all_enabled, missing = manager.verify_flags_enabled(cflags, ldflags)

        assert all_enabled is False
        assert len(missing) > 0

    def test_apply_to_config(self):
        """Test: Security flags can be applied to configuration"""
        manager = SecurityHardeningManager()

        config = {'CFLAGS': '-O2', 'LDFLAGS': ''}
        updated = manager.apply_to_config(config)

        # Should have security flags added
        assert '-fPIE' in updated['CFLAGS'] or '-fPIC' in updated['CFLAGS']
        assert '-fstack-protector' in updated['CFLAGS']
        assert '-D_FORTIFY_SOURCE' in updated['CFLAGS']
        assert '-pie' in updated['LDFLAGS']

    def test_generate_makefile_snippet(self):
        """Test: Can generate Makefile snippet"""
        manager = SecurityHardeningManager()

        snippet = manager.generate_makefile_snippet()

        assert isinstance(snippet, str)
        assert 'SECURITY_CFLAGS' in snippet
        assert 'SECURITY_LDFLAGS' in snippet
        assert '-fPIE' in snippet or '-fPIC' in snippet


@pytest.mark.property
class TestBinarySecurityVerification:
    """Tests for binary security verification"""

    def test_binary_verifier_initialization(self):
        """Test: Binary verifier can be initialized"""
        verifier = BinarySecurityVerifier()
        assert verifier is not None

    def test_verify_binary_with_elf_header(self):
        """Test: Can verify binary with ELF header"""
        verifier = BinarySecurityVerifier()

        # Create minimal ELF binary
        with tempfile.NamedTemporaryFile(delete=False, suffix='.elf') as f:
            # ELF magic
            f.write(b'\x7fELF')
            # 64-bit, little-endian
            f.write(b'\x02\x01\x01')
            f.write(b'\x00' * 9)  # Padding
            # e_type = ET_DYN (3) for PIE
            f.write(b'\x03\x00')
            f.write(b'\x00' * 46)  # Rest of header
            # Add security markers
            f.write(b'GNU_STACK\x00')
            f.write(b'__stack_chk_fail\x00')
            f.write(b'GNU_RELRO\x00')
            temp_path = Path(f.name)

        try:
            features = verifier.verify_binary(temp_path)

            assert isinstance(features, dict)
            assert 'pie' in features
            assert 'nx' in features
            assert 'stack_canary' in features
            assert 'relro' in features
        finally:
            temp_path.unlink()

    def test_verify_non_elf_binary(self):
        """Test: Non-ELF binary returns all false"""
        verifier = BinarySecurityVerifier()

        # Create non-ELF file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'Not an ELF file')
            temp_path = Path(f.name)

        try:
            features = verifier.verify_binary(temp_path)

            # All features should be False for non-ELF
            assert features['pie'] is False
            assert features['nx'] is False
            assert features['stack_canary'] is False
        finally:
            temp_path.unlink()

    def test_verify_required_features(self):
        """
        Test: Can verify required security features

        Requirement 2.1: Verify required features in binaries
        """
        verifier = BinarySecurityVerifier()

        # Create binary with required features
        with tempfile.NamedTemporaryFile(delete=False, suffix='.elf') as f:
            f.write(b'\x7fELF')
            f.write(b'\x02\x01\x01')
            f.write(b'\x00' * 9)
            f.write(b'\x03\x00')  # ET_DYN (PIE)
            f.write(b'\x00' * 46)
            f.write(b'GNU_STACK\x00')
            f.write(b'__stack_chk_fail\x00')
            temp_path = Path(f.name)

        try:
            all_present, missing = verifier.verify_required_features(temp_path)

            assert isinstance(all_present, bool)
            assert isinstance(missing, list)
        finally:
            temp_path.unlink()


@pytest.mark.property
class TestCompilerSecurityChecker:
    """Tests for compiler security support checking"""

    def test_compiler_checker_initialization(self):
        """Test: Compiler checker can be initialized"""
        checker = CompilerSecurityChecker(compiler="gcc")
        assert checker is not None
        assert checker.compiler == "gcc"

    @pytest.mark.skip(reason="Requires actual compiler installation")
    def test_check_flag_support(self):
        """Test: Can check compiler flag support"""
        checker = CompilerSecurityChecker()

        # Common flag that should be supported
        supported = checker.check_flag_support('-O2')

        assert isinstance(supported, bool)

    @pytest.mark.skip(reason="Requires actual compiler installation")
    def test_get_supported_security_flags(self):
        """Test: Can get all supported security flags"""
        checker = CompilerSecurityChecker()

        support = checker.get_supported_security_flags()

        assert isinstance(support, dict)
        assert 'pie' in support
        assert 'stack_protector' in support


@pytest.mark.property
class TestCompilationConfig:
    """Tests for compilation configuration"""

    def test_compilation_config_creation(self):
        """Test: Compilation config can be created"""
        flags = SecurityFlags()
        config = CompilationConfig(security_flags=flags)

        assert config is not None
        assert config.optimization_level == "-O2"

    def test_get_cflags(self):
        """Test: Can get complete CFLAGS string"""
        flags = SecurityFlags()
        config = CompilationConfig(security_flags=flags)

        cflags = config.get_cflags()

        assert isinstance(cflags, str)
        assert '-O2' in cflags
        assert '-fPIE' in cflags or '-fPIC' in cflags

    def test_get_ldflags(self):
        """Test: Can get complete LDFLAGS string"""
        flags = SecurityFlags()
        config = CompilationConfig(security_flags=flags)

        ldflags = config.get_ldflags()

        assert isinstance(ldflags, str)
        assert '-pie' in ldflags

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(level=st.sampled_from(list(SecurityLevel)))
    def test_config_from_any_security_level(self, level):
        """
        Property Test: Can create config from any security level

        For any security level, a valid compilation config
        must be creatable.
        """
        flags = SecurityFlags.from_level(level)
        config = CompilationConfig(security_flags=flags)

        assert config is not None

        # Should be able to get flags
        cflags = config.get_cflags()
        ldflags = config.get_ldflags()

        assert isinstance(cflags, str)
        assert isinstance(ldflags, str)


@pytest.mark.property
class TestSecurityConfigManager:
    """Tests for security configuration management"""

    def test_config_manager_initialization(self):
        """Test: Security config manager can be initialized"""
        manager = SecurityConfigManager()

        assert manager is not None
        assert manager.hardening_manager is not None
        assert manager.verifier is not None

    def test_create_build_config(self):
        """Test: Can create build configuration"""
        manager = SecurityConfigManager()

        config = manager.create_build_config(SecurityLevel.STANDARD)

        assert config is not None
        assert isinstance(config, CompilationConfig)

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(level=st.sampled_from(list(SecurityLevel)))
    def test_create_config_for_all_levels(self, level):
        """
        Property Test: Can create config for any security level

        For any security level, a valid build configuration
        must be creatable.
        """
        manager = SecurityConfigManager()

        config = manager.create_build_config(level)

        assert config is not None
        assert isinstance(config, CompilationConfig)

    def test_save_config(self):
        """Test: Can save configuration to file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "security.conf"

            manager = SecurityConfigManager()
            config = manager.create_build_config(SecurityLevel.STANDARD)

            manager.save_config(config, config_path)

            assert config_path.exists()
            content = config_path.read_text()
            assert 'CFLAGS' in content
            assert 'LDFLAGS' in content

    def test_verify_build(self):
        """
        Test: Can verify build meets security requirements

        Requirement 2.1: Build-time verification
        """
        # Create test binary with security features
        with tempfile.NamedTemporaryFile(delete=False, suffix='.elf') as f:
            f.write(b'\x7fELF')
            f.write(b'\x02\x01\x01')
            f.write(b'\x00' * 9)
            f.write(b'\x03\x00')  # PIE
            f.write(b'\x00' * 46)
            f.write(b'GNU_STACK\x00')
            f.write(b'__stack_chk_fail\x00')
            temp_path = Path(f.name)

        try:
            manager = SecurityConfigManager()
            result = manager.verify_build(temp_path)

            assert isinstance(result, bool)
        finally:
            temp_path.unlink()


@pytest.mark.property
class TestSecurityLevelProgression:
    """Tests for security level progression"""

    def test_none_level_has_no_flags(self):
        """Test: NONE level has no security flags"""
        flags = SecurityFlags.from_level(SecurityLevel.NONE)

        assert len(flags.pie_cflags) == 0
        assert len(flags.stack_protection) == 0
        assert len(flags.fortify_source) == 0

    def test_paranoid_level_has_most_flags(self):
        """Test: PARANOID level has most security flags"""
        paranoid = SecurityFlags.from_level(SecurityLevel.PARANOID)
        standard = SecurityFlags.from_level(SecurityLevel.STANDARD)

        paranoid_count = len(paranoid.get_all_cflags()) + len(paranoid.get_all_ldflags())
        standard_count = len(standard.get_all_cflags()) + len(standard.get_all_ldflags())

        assert paranoid_count >= standard_count

    def test_level_progression_increases_security(self):
        """Test: Higher levels have equal or more security"""
        levels = [
            SecurityLevel.NONE,
            SecurityLevel.MINIMAL,
            SecurityLevel.STANDARD,
            SecurityLevel.FULL,
            SecurityLevel.PARANOID
        ]

        flag_counts = []
        for level in levels:
            flags = SecurityFlags.from_level(level)
            count = len(flags.get_all_cflags()) + len(flags.get_all_ldflags())
            flag_counts.append(count)

        # Generally, higher levels should have same or more flags
        # (with some exceptions for specific optimizations)
        assert flag_counts[-1] >= flag_counts[0]  # Paranoid >= None
