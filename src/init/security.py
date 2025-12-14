"""
Security features for Kimigayo OS Init System

Provides namespace isolation and seccomp-BPF filtering for services.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
import json


class NamespaceType(Enum):
    """Linux namespace types"""
    PID = "pid"          # Process ID namespace
    NET = "net"          # Network namespace
    MNT = "mnt"          # Mount namespace
    IPC = "ipc"          # IPC namespace
    UTS = "uts"          # Hostname namespace
    USER = "user"        # User namespace
    CGROUP = "cgroup"    # Cgroup namespace


class SeccompAction(Enum):
    """Seccomp filter actions"""
    ALLOW = "SCMP_ACT_ALLOW"
    KILL = "SCMP_ACT_KILL"
    ERRNO = "SCMP_ACT_ERRNO"
    TRAP = "SCMP_ACT_TRAP"
    TRACE = "SCMP_ACT_TRACE"


@dataclass
class NamespaceConfig:
    """Configuration for namespace isolation"""

    # Enabled namespaces
    enabled_namespaces: Set[NamespaceType] = field(default_factory=set)

    # Network namespace settings
    network_isolated: bool = False
    allow_loopback: bool = True

    # Mount namespace settings
    private_tmp: bool = True
    read_only_paths: List[str] = field(default_factory=list)
    inaccessible_paths: List[str] = field(default_factory=list)

    # User namespace settings
    map_current_user: bool = False
    uid_map: Optional[Dict[int, int]] = None
    gid_map: Optional[Dict[int, int]] = None

    def enable_namespace(self, ns_type: NamespaceType):
        """Enable a specific namespace type"""
        self.enabled_namespaces.add(ns_type)

    def disable_namespace(self, ns_type: NamespaceType):
        """Disable a specific namespace type"""
        self.enabled_namespaces.discard(ns_type)

    def is_enabled(self, ns_type: NamespaceType) -> bool:
        """Check if a namespace type is enabled"""
        return ns_type in self.enabled_namespaces

    def get_namespace_flags(self) -> List[str]:
        """Get list of namespace flags for execution"""
        flags = []
        for ns in self.enabled_namespaces:
            flags.append(f"--{ns.value}")
        return flags


@dataclass
class SeccompRule:
    """A single seccomp filter rule"""
    syscall: str
    action: SeccompAction
    args: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary format"""
        rule = {
            "syscall": self.syscall,
            "action": self.action.value
        }
        if self.args:
            rule["args"] = self.args
        return rule


@dataclass
class SeccompProfile:
    """Seccomp-BPF filter profile"""

    name: str
    default_action: SeccompAction = SeccompAction.ERRNO
    rules: List[SeccompRule] = field(default_factory=list)

    # Predefined syscall groups
    allow_basic: bool = True      # Allow basic syscalls (read, write, etc.)
    allow_network: bool = False   # Allow network syscalls
    allow_filesystem: bool = False # Allow filesystem modification
    allow_process: bool = False   # Allow process creation

    def add_rule(self, syscall: str, action: SeccompAction, args: Optional[List[Dict[str, Any]]] = None):
        """Add a seccomp rule"""
        self.rules.append(SeccompRule(syscall, action, args))

    def remove_rule(self, syscall: str):
        """Remove all rules for a syscall"""
        self.rules = [r for r in self.rules if r.syscall != syscall]

    def get_allowed_syscalls(self) -> Set[str]:
        """Get set of explicitly allowed syscalls"""
        allowed = set()
        for rule in self.rules:
            if rule.action == SeccompAction.ALLOW:
                allowed.add(rule.syscall)
        return allowed

    def get_blocked_syscalls(self) -> Set[str]:
        """Get set of explicitly blocked syscalls"""
        blocked = set()
        for rule in self.rules:
            if rule.action in (SeccompAction.KILL, SeccompAction.ERRNO):
                blocked.add(rule.syscall)
        return blocked

    def to_json(self) -> str:
        """Export profile to JSON format"""
        profile = {
            "name": self.name,
            "defaultAction": self.default_action.value,
            "syscalls": [rule.to_dict() for rule in self.rules]
        }
        return json.dumps(profile, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "SeccompProfile":
        """Load profile from JSON format"""
        data = json.loads(json_str)
        profile = cls(
            name=data["name"],
            default_action=SeccompAction(data["defaultAction"])
        )

        for syscall_data in data.get("syscalls", []):
            profile.add_rule(
                syscall=syscall_data["syscall"],
                action=SeccompAction(syscall_data["action"]),
                args=syscall_data.get("args")
            )

        return profile


# Predefined seccomp profiles

def create_strict_profile() -> SeccompProfile:
    """
    Create a strict seccomp profile that allows only essential syscalls.
    Suitable for highly restricted services.
    """
    profile = SeccompProfile(
        name="strict",
        default_action=SeccompAction.ERRNO,
        allow_basic=True,
        allow_network=False,
        allow_filesystem=False,
        allow_process=False
    )

    # Allow only essential syscalls
    essential_syscalls = [
        "read", "write", "close", "fstat", "lseek",
        "mmap", "munmap", "brk", "rt_sigaction", "rt_sigprocmask",
        "exit", "exit_group", "getpid", "getuid", "getgid"
    ]

    for syscall in essential_syscalls:
        profile.add_rule(syscall, SeccompAction.ALLOW)

    return profile


def create_default_profile() -> SeccompProfile:
    """
    Create a default seccomp profile with reasonable restrictions.
    Suitable for most services.
    """
    profile = SeccompProfile(
        name="default",
        default_action=SeccompAction.ERRNO,
        allow_basic=True,
        allow_network=True,
        allow_filesystem=True,
        allow_process=False
    )

    # Allow common syscalls
    common_syscalls = [
        # File operations
        "read", "write", "open", "openat", "close", "fstat", "lseek",
        "readv", "writev", "pread64", "pwrite64", "stat", "lstat",

        # Memory operations
        "mmap", "munmap", "mprotect", "brk", "mremap",

        # Network operations
        "socket", "connect", "bind", "listen", "accept", "accept4",
        "sendto", "recvfrom", "sendmsg", "recvmsg", "shutdown",
        "getsockname", "getpeername", "setsockopt", "getsockopt",

        # Signal handling
        "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",

        # Process info
        "getpid", "getppid", "getuid", "getgid", "geteuid", "getegid",

        # Exit
        "exit", "exit_group"
    ]

    for syscall in common_syscalls:
        profile.add_rule(syscall, SeccompAction.ALLOW)

    # Block dangerous syscalls
    dangerous_syscalls = [
        "ptrace", "personality", "reboot", "kexec_load",
        "init_module", "finit_module", "delete_module",
        "iopl", "ioperm", "modify_ldt"
    ]

    for syscall in dangerous_syscalls:
        profile.add_rule(syscall, SeccompAction.KILL)

    return profile


def create_permissive_profile() -> SeccompProfile:
    """
    Create a permissive seccomp profile that allows most operations.
    Suitable for services that need broad system access.
    """
    profile = SeccompProfile(
        name="permissive",
        default_action=SeccompAction.ALLOW,
        allow_basic=True,
        allow_network=True,
        allow_filesystem=True,
        allow_process=True
    )

    # Block only extremely dangerous syscalls
    blocked_syscalls = [
        "reboot", "kexec_load", "init_module", "finit_module",
        "delete_module", "iopl", "ioperm"
    ]

    for syscall in blocked_syscalls:
        profile.add_rule(syscall, SeccompAction.KILL)

    return profile


@dataclass
class SecurityContext:
    """Security context for a service"""

    namespace_config: Optional[NamespaceConfig] = None
    seccomp_profile: Optional[SeccompProfile] = None

    # Additional security settings
    drop_capabilities: List[str] = field(default_factory=list)
    no_new_privileges: bool = True

    def apply_namespace_isolation(self) -> bool:
        """
        Apply namespace isolation settings.
        In real implementation, would use unshare() or clone() syscalls.
        """
        if not self.namespace_config:
            return False

        # Mock implementation - would actually create namespaces
        return len(self.namespace_config.enabled_namespaces) > 0

    def apply_seccomp_filter(self) -> bool:
        """
        Apply seccomp filter.
        In real implementation, would use prctl(PR_SET_SECCOMP, ...).
        """
        if not self.seccomp_profile:
            return False

        # Mock implementation - would actually load BPF filter
        return len(self.seccomp_profile.rules) > 0

    def verify_security_applied(self) -> bool:
        """
        Verify that all security features are properly applied.
        Returns True if all enabled features are active.
        """
        results = []

        # Check namespace isolation
        if self.namespace_config:
            results.append(self.apply_namespace_isolation())

        # Check seccomp filter
        if self.seccomp_profile:
            results.append(self.apply_seccomp_filter())

        # If no security features enabled, return False
        if not results:
            return False

        # All enabled features must be active
        return all(results)

    def get_security_summary(self) -> Dict[str, Any]:
        """Get summary of applied security features"""
        summary = {
            "namespace_isolation": False,
            "seccomp_filtering": False,
            "no_new_privileges": self.no_new_privileges,
            "dropped_capabilities": self.drop_capabilities.copy()
        }

        if self.namespace_config:
            summary["namespace_isolation"] = True
            summary["enabled_namespaces"] = [
                ns.value for ns in self.namespace_config.enabled_namespaces
            ]

        if self.seccomp_profile:
            summary["seccomp_filtering"] = True
            summary["seccomp_profile"] = self.seccomp_profile.name
            summary["allowed_syscalls_count"] = len(self.seccomp_profile.get_allowed_syscalls())
            summary["blocked_syscalls_count"] = len(self.seccomp_profile.get_blocked_syscalls())

        return summary


def create_service_security_context(
    namespace_isolation: bool = False,
    seccomp_level: str = "default"
) -> SecurityContext:
    """
    Create a security context for a service.

    Args:
        namespace_isolation: Whether to enable namespace isolation
        seccomp_level: Seccomp profile level (strict, default, permissive)

    Returns:
        Configured SecurityContext
    """
    # Create namespace config if isolation is enabled
    ns_config = None
    if namespace_isolation:
        ns_config = NamespaceConfig()
        # Enable common namespaces for service isolation
        ns_config.enable_namespace(NamespaceType.PID)
        ns_config.enable_namespace(NamespaceType.MNT)
        ns_config.enable_namespace(NamespaceType.IPC)
        ns_config.private_tmp = True

    # Create seccomp profile based on level
    seccomp_profile = None
    if seccomp_level == "strict":
        seccomp_profile = create_strict_profile()
    elif seccomp_level == "default":
        seccomp_profile = create_default_profile()
    elif seccomp_level == "permissive":
        seccomp_profile = create_permissive_profile()

    # Create security context
    context = SecurityContext(
        namespace_config=ns_config,
        seccomp_profile=seccomp_profile,
        no_new_privileges=True,
        drop_capabilities=["CAP_SYS_ADMIN", "CAP_SYS_MODULE"]
    )

    return context
