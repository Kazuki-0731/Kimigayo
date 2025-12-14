"""
BusyBox configuration and build system for Kimigayo OS

Provides modular configuration of essential Unix utilities with size optimization.
"""

import hashlib
from pathlib import Path
from typing import List, Set, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum


class UtilityCategory(Enum):
    """Categories of BusyBox utilities"""
    CORE = "core"  # Essential core utilities
    SHELL = "shell"  # Shell utilities
    FILE = "file"  # File operations
    TEXT = "text"  # Text processing
    NETWORK = "network"  # Network utilities
    SYSTEM = "system"  # System administration
    PROCESS = "process"  # Process management


@dataclass
class BusyBoxUtility:
    """Represents a BusyBox utility"""
    name: str
    category: UtilityCategory
    essential: bool = False  # Must be included in minimal builds
    description: str = ""
    size_bytes: int = 0  # Approximate size contribution

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, BusyBoxUtility):
            return self.name == other.name
        return False


# Essential utilities that must be included
ESSENTIAL_UTILITIES = [
    BusyBoxUtility("sh", UtilityCategory.SHELL, True, "Shell", 50000),
    BusyBoxUtility("ls", UtilityCategory.FILE, True, "List directory", 5000),
    BusyBoxUtility("cp", UtilityCategory.FILE, True, "Copy files", 3000),
    BusyBoxUtility("mv", UtilityCategory.FILE, True, "Move files", 3000),
    BusyBoxUtility("rm", UtilityCategory.FILE, True, "Remove files", 2000),
    BusyBoxUtility("mkdir", UtilityCategory.FILE, True, "Create directory", 2000),
    BusyBoxUtility("cat", UtilityCategory.TEXT, True, "Concatenate files", 2000),
    BusyBoxUtility("echo", UtilityCategory.CORE, True, "Display text", 1000),
    BusyBoxUtility("mount", UtilityCategory.SYSTEM, True, "Mount filesystem", 5000),
    BusyBoxUtility("umount", UtilityCategory.SYSTEM, True, "Unmount filesystem", 3000),
    BusyBoxUtility("ps", UtilityCategory.PROCESS, True, "Process status", 3000),
    BusyBoxUtility("kill", UtilityCategory.PROCESS, True, "Kill process", 2000),
    BusyBoxUtility("grep", UtilityCategory.TEXT, True, "Search text", 5000),
    BusyBoxUtility("sed", UtilityCategory.TEXT, True, "Stream editor", 8000),
    BusyBoxUtility("awk", UtilityCategory.TEXT, True, "Text processing", 10000),
    BusyBoxUtility("init", UtilityCategory.SYSTEM, True, "Init process", 8000),
]

# Optional utilities
OPTIONAL_UTILITIES = [
    BusyBoxUtility("wget", UtilityCategory.NETWORK, False, "Download files", 15000),
    BusyBoxUtility("tar", UtilityCategory.FILE, False, "Archive utility", 12000),
    BusyBoxUtility("gzip", UtilityCategory.FILE, False, "Compression", 8000),
    BusyBoxUtility("gunzip", UtilityCategory.FILE, False, "Decompression", 5000),
    BusyBoxUtility("find", UtilityCategory.FILE, False, "Find files", 8000),
    BusyBoxUtility("vi", UtilityCategory.TEXT, False, "Text editor", 25000),
    BusyBoxUtility("top", UtilityCategory.PROCESS, False, "Process monitor", 8000),
    BusyBoxUtility("ifconfig", UtilityCategory.NETWORK, False, "Network config", 8000),
    BusyBoxUtility("ping", UtilityCategory.NETWORK, False, "Network ping", 5000),
    BusyBoxUtility("netstat", UtilityCategory.NETWORK, False, "Network statistics", 8000),
    BusyBoxUtility("chmod", UtilityCategory.FILE, False, "Change permissions", 3000),
    BusyBoxUtility("chown", UtilityCategory.FILE, False, "Change owner", 3000),
    BusyBoxUtility("ln", UtilityCategory.FILE, False, "Create links", 2000),
    BusyBoxUtility("df", UtilityCategory.SYSTEM, False, "Disk free", 3000),
    BusyBoxUtility("du", UtilityCategory.SYSTEM, False, "Disk usage", 4000),
]


class ImageProfile(Enum):
    """BusyBox build profiles"""
    MINIMAL = "minimal"  # Only essential utilities
    STANDARD = "standard"  # Essential + common utilities
    EXTENDED = "extended"  # Full featured


@dataclass
class BusyBoxConfig:
    """BusyBox build configuration"""
    profile: ImageProfile = ImageProfile.MINIMAL
    utilities: Set[BusyBoxUtility] = field(default_factory=set)
    enable_static: bool = True
    enable_size_optimization: bool = True
    enable_security_hardening: bool = True
    custom_cflags: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Initialize utilities based on profile if not set
        if not self.utilities:
            self.utilities = self._get_profile_utilities()

    def _get_profile_utilities(self) -> Set[BusyBoxUtility]:
        """Get utilities based on profile"""
        utilities = set(ESSENTIAL_UTILITIES)

        if self.profile == ImageProfile.STANDARD:
            # Add common optional utilities
            common = ["wget", "tar", "gzip", "gunzip", "find", "chmod", "chown", "ln", "df", "du"]
            utilities.update(u for u in OPTIONAL_UTILITIES if u.name in common)

        elif self.profile == ImageProfile.EXTENDED:
            # Add all utilities
            utilities.update(OPTIONAL_UTILITIES)

        return utilities

    def get_utility_names(self) -> List[str]:
        """Get list of utility names"""
        return sorted([u.name for u in self.utilities])

    def add_utility(self, utility: BusyBoxUtility) -> bool:
        """Add a utility to the configuration"""
        if utility not in self.utilities:
            self.utilities.add(utility)
            return True
        return False

    def remove_utility(self, utility: BusyBoxUtility) -> bool:
        """Remove a utility from the configuration"""
        if utility.essential:
            raise ValueError(f"Cannot remove essential utility: {utility.name}")

        if utility in self.utilities:
            self.utilities.remove(utility)
            return True
        return False

    def get_estimated_size(self) -> int:
        """Get estimated total size of selected utilities"""
        base_size = 100000  # Base BusyBox size
        utilities_size = sum(u.size_bytes for u in self.utilities)

        # Apply optimization factor
        optimization_factor = 0.8 if self.enable_size_optimization else 1.0

        return int((base_size + utilities_size) * optimization_factor)

    def verify_essential_utilities(self) -> bool:
        """Verify that all essential utilities are included"""
        essential = set(u for u in ESSENTIAL_UTILITIES)
        return essential.issubset(self.utilities)

    def get_cflags(self) -> List[str]:
        """Get compilation flags"""
        flags = list(self.custom_cflags)

        if self.enable_size_optimization:
            flags.extend(["-Os", "-ffunction-sections", "-fdata-sections"])

        if self.enable_security_hardening:
            flags.extend([
                "-fPIE",
                "-fstack-protector-strong",
                "-D_FORTIFY_SOURCE=2",
            ])

        return flags

    def get_ldflags(self) -> List[str]:
        """Get linker flags"""
        flags = []

        if self.enable_static:
            flags.append("-static")

        if self.enable_size_optimization:
            flags.extend(["-Wl,--gc-sections", "-Wl,--strip-all"])

        if self.enable_security_hardening:
            flags.extend([
                "-Wl,-z,relro",
                "-Wl,-z,now",
                "-Wl,-z,noexecstack",
            ])

        return flags


@dataclass
class BusyBoxBuildResult:
    """Result of BusyBox build"""
    binary_path: Path
    config: BusyBoxConfig
    size_bytes: int
    checksum: str
    utilities: List[str]

    def verify_checksum(self, expected: str) -> bool:
        """Verify binary checksum"""
        return self.checksum == expected

    def verify_utilities(self) -> bool:
        """Verify that all configured utilities are present"""
        configured = set(self.config.get_utility_names())
        built = set(self.utilities)
        return configured == built


class BusyBoxBuilder:
    """BusyBox build system"""

    def __init__(self, config: BusyBoxConfig, output_dir: Path):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_config_file(self) -> Path:
        """Generate BusyBox .config file"""
        config_file = self.output_dir / ".config"

        # Generate configuration content
        config_content = self._generate_config_content()

        config_file.write_text(config_content)
        return config_file

    def _generate_config_content(self) -> str:
        """Generate BusyBox configuration content"""
        lines = [
            "# Kimigayo OS BusyBox Configuration",
            f"# Profile: {self.config.profile.value}",
            "",
        ]

        # Static linking
        if self.config.enable_static:
            lines.append("CONFIG_STATIC=y")
        else:
            lines.append("# CONFIG_STATIC is not set")

        # Size optimization
        if self.config.enable_size_optimization:
            lines.append("CONFIG_FEATURE_PREFER_APPLETS=y")
            lines.append("CONFIG_FEATURE_SH_STANDALONE=y")

        lines.append("")
        lines.append("# Enabled utilities:")

        # List enabled utilities
        for utility in sorted(self.config.utilities, key=lambda u: u.name):
            utility_config = f"CONFIG_{utility.name.upper()}=y"
            lines.append(utility_config)

        return "\n".join(lines)

    def build(self) -> BusyBoxBuildResult:
        """Build BusyBox with current configuration"""
        # Verify essential utilities
        if not self.config.verify_essential_utilities():
            raise ValueError("Missing essential utilities")

        # Generate config file
        config_file = self.generate_config_file()

        # Build binary (mock implementation)
        binary_path = self.output_dir / "busybox"

        # Create mock binary with size based on configuration
        estimated_size = self.config.get_estimated_size()
        mock_data = b"BUSYBOX" * (estimated_size // 7)
        binary_path.write_bytes(mock_data[:estimated_size])

        # Calculate checksum
        checksum = self._calculate_checksum(binary_path)

        # Get actual size
        size_bytes = binary_path.stat().st_size

        return BusyBoxBuildResult(
            binary_path=binary_path,
            config=self.config,
            size_bytes=size_bytes,
            checksum=checksum,
            utilities=self.config.get_utility_names(),
        )

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def list_available_utilities(self) -> Dict[str, List[BusyBoxUtility]]:
        """List all available utilities by category"""
        all_utilities = ESSENTIAL_UTILITIES + OPTIONAL_UTILITIES

        by_category = {}
        for utility in all_utilities:
            category = utility.category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(utility)

        return by_category


def build_busybox(config: BusyBoxConfig, output_dir: Path) -> BusyBoxBuildResult:
    """Build BusyBox with specified configuration"""
    builder = BusyBoxBuilder(config, output_dir)
    return builder.build()
