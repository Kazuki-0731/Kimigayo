"""
Compile-time Security Hardening

Manages compile-time security flags and build-time verification.

Requirements:
- 2.1: Compile-time security hardening - PIE, stack protection, FORTIFY_SOURCE
"""

import re
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


class SecurityLevel(Enum):
    """Security hardening levels"""
    NONE = "none"
    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"
    PARANOID = "paranoid"


class CompilerType(Enum):
    """Supported compiler types"""
    GCC = "gcc"
    CLANG = "clang"
    MUSL_GCC = "musl-gcc"


@dataclass
class SecurityFlags:
    """
    Security compilation flags.

    Requirement: 2.1 (Compile-time security hardening)
    """
    # PIE - Position Independent Executable
    pie_cflags: List[str] = field(default_factory=lambda: ["-fPIE"])
    pie_ldflags: List[str] = field(default_factory=lambda: ["-pie"])

    # Stack protection
    stack_protection: List[str] = field(default_factory=lambda: ["-fstack-protector-strong"])

    # FORTIFY_SOURCE - Buffer overflow detection
    fortify_source: List[str] = field(default_factory=lambda: ["-D_FORTIFY_SOURCE=2"])

    # RELRO - Relocation Read-Only
    relro_flags: List[str] = field(default_factory=lambda: ["-Wl,-z,relro", "-Wl,-z,now"])

    # Additional hardening flags
    additional_cflags: List[str] = field(default_factory=list)
    additional_ldflags: List[str] = field(default_factory=list)

    def get_all_cflags(self) -> List[str]:
        """
        Get all C compiler flags.

        Returns:
            List of CFLAGS
        """
        flags = []
        flags.extend(self.pie_cflags)
        flags.extend(self.stack_protection)
        flags.extend(self.fortify_source)
        flags.extend(self.additional_cflags)
        return flags

    def get_all_ldflags(self) -> List[str]:
        """
        Get all linker flags.

        Returns:
            List of LDFLAGS
        """
        flags = []
        flags.extend(self.pie_ldflags)
        flags.extend(self.relro_flags)
        flags.extend(self.additional_ldflags)
        return flags

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_level(cls, level: SecurityLevel) -> "SecurityFlags":
        """
        Create security flags from security level.

        Args:
            level: Security hardening level

        Returns:
            Security flags for the level
        """
        if level == SecurityLevel.NONE:
            return cls(
                pie_cflags=[],
                pie_ldflags=[],
                stack_protection=[],
                fortify_source=[],
                relro_flags=[]
            )
        elif level == SecurityLevel.MINIMAL:
            return cls(
                stack_protection=["-fstack-protector"]
            )
        elif level == SecurityLevel.STANDARD:
            return cls()  # Default values
        elif level == SecurityLevel.FULL:
            return cls(
                additional_cflags=["-fstack-clash-protection"],
                additional_ldflags=["-Wl,-z,noexecstack"]
            )
        elif level == SecurityLevel.PARANOID:
            return cls(
                stack_protection=["-fstack-protector-all"],
                fortify_source=["-D_FORTIFY_SOURCE=3"],
                additional_cflags=[
                    "-fstack-clash-protection",
                    "-fcf-protection=full",
                    "-Werror=format-security"
                ],
                additional_ldflags=[
                    "-Wl,-z,noexecstack",
                    "-Wl,-z,separate-code"
                ]
            )
        else:
            return cls()


@dataclass
class CompilationConfig:
    """Compilation configuration with security settings"""
    security_flags: SecurityFlags
    optimization_level: str = "-O2"
    debug_info: bool = False
    warnings: List[str] = field(default_factory=lambda: ["-Wall", "-Wextra"])

    def get_cflags(self) -> str:
        """Get complete CFLAGS string"""
        flags = [self.optimization_level]
        if self.debug_info:
            flags.append("-g")
        flags.extend(self.warnings)
        flags.extend(self.security_flags.get_all_cflags())
        return " ".join(flags)

    def get_ldflags(self) -> str:
        """Get complete LDFLAGS string"""
        return " ".join(self.security_flags.get_all_ldflags())


class SecurityHardeningManager:
    """
    Manages compile-time security hardening.

    Requirement: 2.1 (Compile-time security hardening)
    """

    def __init__(self, security_level: SecurityLevel = SecurityLevel.STANDARD):
        """
        Initialize security hardening manager.

        Args:
            security_level: Security hardening level
        """
        self.security_level = security_level
        self.security_flags = SecurityFlags.from_level(security_level)

    def get_required_flags(self) -> Dict[str, List[str]]:
        """
        Get required security flags.

        Requirement: 2.1 - PIE, stack protection, FORTIFY_SOURCE must be enabled

        Returns:
            Dictionary of flag categories
        """
        return {
            'pie': self.security_flags.pie_cflags + self.security_flags.pie_ldflags,
            'stack_protection': self.security_flags.stack_protection,
            'fortify_source': self.security_flags.fortify_source,
            'relro': self.security_flags.relro_flags
        }

    def verify_flags_enabled(self, cflags: str, ldflags: str) -> Tuple[bool, List[str]]:
        """
        Verify that required security flags are enabled.

        Requirement: 2.1 - Verify security flags are applied

        Args:
            cflags: Compiler flags string
            ldflags: Linker flags string

        Returns:
            Tuple of (all_enabled, list_of_missing_flags)
        """
        missing = []

        # Check PIE
        if '-fPIE' not in cflags and '-fPIC' not in cflags:
            missing.append('PIE compiler flag (-fPIE)')
        if '-pie' not in ldflags:
            missing.append('PIE linker flag (-pie)')

        # Check stack protection
        stack_protector_found = any(
            flag in cflags
            for flag in ['-fstack-protector', '-fstack-protector-strong', '-fstack-protector-all']
        )
        if not stack_protector_found:
            missing.append('Stack protector (-fstack-protector-strong)')

        # Check FORTIFY_SOURCE
        if '-D_FORTIFY_SOURCE' not in cflags:
            missing.append('FORTIFY_SOURCE (-D_FORTIFY_SOURCE=2)')

        return (len(missing) == 0, missing)

    def apply_to_config(self, config: Dict) -> Dict:
        """
        Apply security flags to build configuration.

        Args:
            config: Build configuration dictionary

        Returns:
            Updated configuration with security flags
        """
        config = config.copy()

        # Add CFLAGS
        existing_cflags = config.get('CFLAGS', '')
        new_cflags = self.security_flags.get_all_cflags()
        config['CFLAGS'] = f"{existing_cflags} {' '.join(new_cflags)}".strip()

        # Add LDFLAGS
        existing_ldflags = config.get('LDFLAGS', '')
        new_ldflags = self.security_flags.get_all_ldflags()
        config['LDFLAGS'] = f"{existing_ldflags} {' '.join(new_ldflags)}".strip()

        return config

    def generate_makefile_snippet(self) -> str:
        """
        Generate Makefile snippet with security flags.

        Returns:
            Makefile snippet as string
        """
        cflags = ' '.join(self.security_flags.get_all_cflags())
        ldflags = ' '.join(self.security_flags.get_all_ldflags())

        return f"""# Security Hardening Flags (Level: {self.security_level.value})
SECURITY_CFLAGS = {cflags}
SECURITY_LDFLAGS = {ldflags}

# Apply to compilation
CFLAGS += $(SECURITY_CFLAGS)
LDFLAGS += $(SECURITY_LDFLAGS)
"""


class BinarySecurityVerifier:
    """
    Verifies security features in compiled binaries.

    Requirement: 2.1 (Build-time verification)
    """

    def verify_binary(self, binary_path: Path) -> Dict[str, bool]:
        """
        Verify security features in a binary.

        Requirement: 2.1 - Verify PIE, stack protection, FORTIFY_SOURCE

        Args:
            binary_path: Path to binary file

        Returns:
            Dictionary of security features and their status
        """
        features = {
            'pie': False,
            'nx': False,
            'stack_canary': False,
            'relro': False,
            'full_relro': False,
            'fortify': False
        }

        if not binary_path.exists():
            return features

        try:
            # Read ELF binary
            with open(binary_path, 'rb') as f:
                data = f.read()

                # Check ELF header
                if data[:4] != b'\x7fELF':
                    return features

                # PIE: Check if ET_DYN (shared object type)
                e_type = int.from_bytes(data[16:18], byteorder='little')
                if e_type == 3:  # ET_DYN
                    features['pie'] = True

                # NX: Check for GNU_STACK program header
                if b'GNU_STACK' in data:
                    features['nx'] = True

                # Stack canary: Check for __stack_chk_fail symbol
                if b'__stack_chk_fail' in data:
                    features['stack_canary'] = True

                # RELRO: Check for GNU_RELRO
                if b'GNU_RELRO' in data:
                    features['relro'] = True

                # Full RELRO: Check for BIND_NOW
                if b'BIND_NOW' in data:
                    features['full_relro'] = True

                # FORTIFY: Check for fortified function symbols
                fortified_functions = [
                    b'__memcpy_chk',
                    b'__strcpy_chk',
                    b'__sprintf_chk',
                    b'__snprintf_chk'
                ]
                if any(func in data for func in fortified_functions):
                    features['fortify'] = True

        except Exception:
            pass

        return features

    def verify_required_features(self, binary_path: Path) -> Tuple[bool, List[str]]:
        """
        Verify that required security features are present.

        Requirement: 2.1 - All required features must be present

        Args:
            binary_path: Path to binary file

        Returns:
            Tuple of (all_present, list_of_missing_features)
        """
        features = self.verify_binary(binary_path)
        missing = []

        # Required features for Kimigayo OS
        if not features['pie']:
            missing.append('PIE (Position Independent Executable)')
        if not features['nx']:
            missing.append('NX (Non-Executable Stack)')
        if not features['stack_canary']:
            missing.append('Stack Canary')

        return (len(missing) == 0, missing)


class CompilerSecurityChecker:
    """
    Checks compiler support for security features.

    Requirement: 2.1 (Security configuration management)
    """

    def __init__(self, compiler: str = "gcc"):
        """
        Initialize compiler security checker.

        Args:
            compiler: Compiler command (e.g., 'gcc', 'clang')
        """
        self.compiler = compiler

    def check_flag_support(self, flag: str) -> bool:
        """
        Check if compiler supports a specific flag.

        Args:
            flag: Compiler flag to check

        Returns:
            True if flag is supported
        """
        try:
            # Try to compile with the flag
            result = subprocess.run(
                [self.compiler, flag, '-x', 'c', '-c', '-o', '/dev/null', '-'],
                input=b'int main(){return 0;}',
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_supported_security_flags(self) -> Dict[str, bool]:
        """
        Get all supported security flags.

        Returns:
            Dictionary of flags and their support status
        """
        flags_to_check = {
            'pie': '-fPIE',
            'stack_protector': '-fstack-protector-strong',
            'stack_protector_all': '-fstack-protector-all',
            'fortify_source': '-D_FORTIFY_SOURCE=2',
            'stack_clash': '-fstack-clash-protection',
            'cf_protection': '-fcf-protection=full'
        }

        support = {}
        for name, flag in flags_to_check.items():
            support[name] = self.check_flag_support(flag)

        return support


class SecurityConfigManager:
    """
    Manages security configuration for build system.

    Requirement: 2.1 (Security configuration management)
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize security configuration manager.

        Args:
            config_dir: Directory for security configurations
        """
        self.config_dir = config_dir or Path("/etc/kimigayo/security")
        self.hardening_manager = SecurityHardeningManager()
        self.verifier = BinarySecurityVerifier()

    def create_build_config(self, level: SecurityLevel) -> CompilationConfig:
        """
        Create build configuration for security level.

        Args:
            level: Security level

        Returns:
            Compilation configuration
        """
        flags = SecurityFlags.from_level(level)
        return CompilationConfig(security_flags=flags)

    def save_config(self, config: CompilationConfig, path: Path):
        """
        Save compilation configuration to file.

        Args:
            config: Compilation configuration
            path: File path
        """
        content = f"""# Kimigayo OS Security Configuration
CFLAGS={config.get_cflags()}
LDFLAGS={config.get_ldflags()}
"""
        path.write_text(content)

    def verify_build(self, binary_path: Path) -> bool:
        """
        Verify that a build meets security requirements.

        Requirement: 2.1 - Build-time verification

        Args:
            binary_path: Path to compiled binary

        Returns:
            True if all security requirements are met
        """
        all_present, missing = self.verifier.verify_required_features(binary_path)
        return all_present
