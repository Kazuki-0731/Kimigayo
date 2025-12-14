"""
System Configuration Management

Manages modular system configuration including kernel modules
and component selection.

Requirements:
- 3.1: Kernel module selection flexibility
- 3.2: Dynamic component management
"""

import json
import yaml
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum


class SecurityLevel(Enum):
    """Security hardening levels"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    HIGH = "high"
    PARANOID = "paranoid"


class ComponentCategory(Enum):
    """Component categories"""
    CORE = "core"
    NETWORK = "network"
    STORAGE = "storage"
    SECURITY = "security"
    DEVELOPMENT = "development"


@dataclass
class KernelModule:
    """
    Kernel module configuration.

    Requirement: 3.1 (Kernel module selection flexibility)
    """
    name: str
    category: str
    required: bool = False
    conflicts: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    description: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "KernelModule":
        """Create from dictionary"""
        return cls(**data)


@dataclass
class SystemComponent:
    """
    System component configuration.

    Requirement: 3.2 (Dynamic component management)
    """
    name: str
    category: ComponentCategory
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    package: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['category'] = self.category.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "SystemComponent":
        """Create from dictionary"""
        data = data.copy()
        if 'category' in data and isinstance(data['category'], str):
            data['category'] = ComponentCategory(data['category'])
        return cls(**data)


@dataclass
class SystemConfig:
    """
    Complete system configuration.

    Manages kernel modules and components.
    """
    architecture: str
    security_level: SecurityLevel
    kernel_modules: List[KernelModule] = field(default_factory=list)
    components: List[SystemComponent] = field(default_factory=list)
    custom_settings: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "architecture": self.architecture,
            "security_level": self.security_level.value,
            "kernel_modules": [m.to_dict() for m in self.kernel_modules],
            "components": [c.to_dict() for c in self.components],
            "custom_settings": self.custom_settings
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_yaml(self) -> str:
        """Convert to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Dict) -> "SystemConfig":
        """Create from dictionary"""
        data = data.copy()
        if 'security_level' in data and isinstance(data['security_level'], str):
            data['security_level'] = SecurityLevel(data['security_level'])
        if 'kernel_modules' in data:
            data['kernel_modules'] = [KernelModule.from_dict(m) for m in data['kernel_modules']]
        if 'components' in data:
            data['components'] = [SystemComponent.from_dict(c) for c in data['components']]
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "SystemConfig":
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "SystemConfig":
        """Create from YAML string"""
        return cls.from_dict(yaml.safe_load(yaml_str))


class KernelModuleManager:
    """
    Manages kernel module selection.

    Requirement: 3.1 (Kernel module selection flexibility)
    """

    def __init__(self):
        """Initialize kernel module manager"""
        self.modules: Dict[str, KernelModule] = {}

    def register_module(self, module: KernelModule):
        """
        Register a kernel module.

        Args:
            module: Kernel module to register
        """
        self.modules[module.name] = module

    def get_module(self, name: str) -> Optional[KernelModule]:
        """Get module by name"""
        return self.modules.get(name)

    def select_modules(self, module_names: List[str]) -> List[KernelModule]:
        """
        Select modules and resolve dependencies.

        Args:
            module_names: List of module names to select

        Returns:
            List of modules including dependencies

        Raises:
            ValueError: If module conflicts or dependencies cannot be resolved
        """
        selected = set()
        to_process = set(module_names)

        while to_process:
            name = to_process.pop()

            if name in selected:
                continue

            module = self.modules.get(name)
            if not module:
                raise ValueError(f"Module not found: {name}")

            # Check conflicts
            for conflict in module.conflicts:
                if conflict in selected:
                    raise ValueError(f"Module conflict: {name} conflicts with {conflict}")

            selected.add(name)

            # Add dependencies
            for dep in module.dependencies:
                if dep not in selected:
                    to_process.add(dep)

        return [self.modules[name] for name in selected]

    def get_required_modules(self) -> List[KernelModule]:
        """Get all required modules"""
        return [m for m in self.modules.values() if m.required]

    def validate_selection(self, module_names: List[str]) -> bool:
        """
        Validate module selection.

        Args:
            module_names: List of module names

        Returns:
            True if selection is valid
        """
        try:
            self.select_modules(module_names)
            return True
        except ValueError:
            return False


class ComponentManager:
    """
    Manages system components dynamically.

    Requirement: 3.2 (Dynamic component management)
    """

    def __init__(self):
        """Initialize component manager"""
        self.components: Dict[str, SystemComponent] = {}

    def add_component(self, component: SystemComponent):
        """
        Add a system component.

        Args:
            component: Component to add

        Raises:
            ValueError: If component conflicts with existing components
        """
        # Check conflicts
        for existing in self.components.values():
            if component.name in existing.conflicts:
                raise ValueError(f"Component {component.name} conflicts with {existing.name}")
            if existing.name in component.conflicts:
                raise ValueError(f"Component {component.name} conflicts with {existing.name}")

        self.components[component.name] = component

    def remove_component(self, name: str) -> bool:
        """
        Remove a component.

        Args:
            name: Component name

        Returns:
            True if component was removed

        Raises:
            ValueError: If other components depend on this component
        """
        if name not in self.components:
            return False

        # Check if other components depend on this one
        for comp in self.components.values():
            if name in comp.dependencies and comp.enabled:
                raise ValueError(f"Cannot remove {name}: {comp.name} depends on it")

        del self.components[name]
        return True

    def enable_component(self, name: str):
        """
        Enable a component.

        Args:
            name: Component name

        Raises:
            ValueError: If component not found or dependencies not satisfied
        """
        component = self.components.get(name)
        if not component:
            raise ValueError(f"Component not found: {name}")

        # Check dependencies
        for dep in component.dependencies:
            dep_comp = self.components.get(dep)
            if not dep_comp or not dep_comp.enabled:
                raise ValueError(f"Dependency not satisfied: {dep}")

        component.enabled = True

    def disable_component(self, name: str):
        """
        Disable a component.

        Args:
            name: Component name

        Raises:
            ValueError: If other enabled components depend on this component
        """
        component = self.components.get(name)
        if not component:
            raise ValueError(f"Component not found: {name}")

        # Check if other enabled components depend on this one
        for comp in self.components.values():
            if comp.enabled and name in comp.dependencies:
                raise ValueError(f"Cannot disable {name}: {comp.name} depends on it")

        component.enabled = False

    def get_enabled_components(self) -> List[SystemComponent]:
        """Get all enabled components"""
        return [c for c in self.components.values() if c.enabled]

    def get_components_by_category(self, category: ComponentCategory) -> List[SystemComponent]:
        """Get components by category"""
        return [c for c in self.components.values() if c.category == category]

    def validate_configuration(self) -> bool:
        """
        Validate entire component configuration.

        Returns:
            True if configuration is valid
        """
        try:
            # Check all enabled components have their dependencies satisfied
            for comp in self.get_enabled_components():
                for dep in comp.dependencies:
                    dep_comp = self.components.get(dep)
                    if not dep_comp or not dep_comp.enabled:
                        return False

            # Check no conflicts
            enabled = self.get_enabled_components()
            for i, comp1 in enumerate(enabled):
                for comp2 in enabled[i+1:]:
                    if comp1.name in comp2.conflicts or comp2.name in comp1.conflicts:
                        return False

            return True
        except Exception:
            return False


class SystemConfigManager:
    """
    Manages complete system configuration.

    Combines kernel module and component management.
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Initialize system config manager.

        Args:
            config: Initial system configuration
        """
        self.config = config or SystemConfig(
            architecture="x86_64",
            security_level=SecurityLevel.STANDARD
        )
        self.kernel_manager = KernelModuleManager()
        self.component_manager = ComponentManager()

        # Load initial configuration
        if config:
            for module in config.kernel_modules:
                self.kernel_manager.register_module(module)
            for component in config.components:
                self.component_manager.add_component(component)

    def save_config(self, path: Path, format: str = "yaml"):
        """
        Save configuration to file.

        Args:
            path: File path
            format: File format (yaml or json)
        """
        # Update config with current state
        self.config.kernel_modules = list(self.kernel_manager.modules.values())
        self.config.components = list(self.component_manager.components.values())

        if format == "yaml":
            content = self.config.to_yaml()
        elif format == "json":
            content = self.config.to_json()
        else:
            raise ValueError(f"Unsupported format: {format}")

        path.write_text(content)

    def load_config(self, path: Path, format: str = "yaml"):
        """
        Load configuration from file.

        Args:
            path: File path
            format: File format (yaml or json)
        """
        content = path.read_text()

        if format == "yaml":
            self.config = SystemConfig.from_yaml(content)
        elif format == "json":
            self.config = SystemConfig.from_json(content)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Reload managers
        self.kernel_manager = KernelModuleManager()
        self.component_manager = ComponentManager()

        for module in self.config.kernel_modules:
            self.kernel_manager.register_module(module)
        for component in self.config.components:
            self.component_manager.add_component(component)

    def validate(self) -> bool:
        """Validate entire system configuration"""
        return self.component_manager.validate_configuration()
