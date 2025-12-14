"""
Property Tests for Modular System Configuration

Tests kernel module selection and component management.

Properties tested:
- Property 9: カーネルモジュール選択柔軟性 (Kernel Module Selection Flexibility) - 要件 3.1
- Property 10: コンポーネント動的管理 (Dynamic Component Management) - 要件 3.2
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, Verbosity

from src.system.config import (
    KernelModule,
    SystemComponent,
    ComponentCategory,
    SecurityLevel,
    SystemConfig,
    KernelModuleManager,
    ComponentManager,
    SystemConfigManager,
)


@pytest.mark.property
class TestKernelModuleSelectionFlexibility:
    """
    Property 9: カーネルモジュール選択柔軟性

    任意のモジュール選択に対して、Build_Systemは個別のカーネルモジュール選択を
    許可しなければならない

    Requirement: 3.1
    """

    def test_kernel_module_creation(self):
        """Test: Kernel modules can be created"""
        module = KernelModule(
            name="network-core",
            category="network",
            required=False
        )
        assert module.name == "network-core"
        assert module.category == "network"
        assert module.required is False

    def test_kernel_module_manager_registration(self):
        """Test: Modules can be registered"""
        manager = KernelModuleManager()
        module = KernelModule(name="test-module", category="core")

        manager.register_module(module)

        assert manager.get_module("test-module") is not None
        assert manager.get_module("test-module").name == "test-module"

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(
        module_name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
        category=st.sampled_from(["core", "network", "storage", "security"])
    )
    def test_individual_module_selection(self, module_name, category):
        """
        Property Test: Individual modules can be selected

        For any module selection, Build_System must allow individual
        kernel module selection.
        """
        manager = KernelModuleManager()
        module = KernelModule(name=module_name, category=category)

        manager.register_module(module)

        # Should be able to select this module
        selected = manager.select_modules([module_name])

        assert len(selected) >= 1
        assert any(m.name == module_name for m in selected)

    def test_module_dependency_resolution(self):
        """Test: Module dependencies are resolved"""
        manager = KernelModuleManager()

        base = KernelModule(name="base", category="core", required=True)
        network = KernelModule(name="network", category="network", dependencies=["base"])

        manager.register_module(base)
        manager.register_module(network)

        # Selecting network should also select base
        selected = manager.select_modules(["network"])

        assert len(selected) == 2
        names = [m.name for m in selected]
        assert "base" in names
        assert "network" in names

    def test_module_conflict_detection(self):
        """Test: Module conflicts are detected"""
        manager = KernelModuleManager()

        ipv4 = KernelModule(name="ipv4", category="network", conflicts=["ipv6-only"])
        ipv6 = KernelModule(name="ipv6-only", category="network", conflicts=["ipv4"])

        manager.register_module(ipv4)
        manager.register_module(ipv6)

        # Should not be able to select both
        with pytest.raises(ValueError, match="conflict"):
            manager.select_modules(["ipv4", "ipv6-only"])

    def test_required_modules_are_identified(self):
        """Test: Required modules are identified"""
        manager = KernelModuleManager()

        manager.register_module(KernelModule(name="core", category="core", required=True))
        manager.register_module(KernelModule(name="optional", category="network", required=False))

        required = manager.get_required_modules()

        assert len(required) == 1
        assert required[0].name == "core"


@pytest.mark.property
class TestDynamicComponentManagement:
    """
    Property 10: コンポーネント動的管理

    任意のCore_Utilitiesコンポーネントに対して、システム設定時の追加・削除操作が
    正常に動作しなければならない

    Requirement: 3.2
    """

    def test_component_creation(self):
        """Test: Components can be created"""
        comp = SystemComponent(
            name="busybox",
            category=ComponentCategory.CORE,
            enabled=True
        )
        assert comp.name == "busybox"
        assert comp.category == ComponentCategory.CORE
        assert comp.enabled is True

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(
        comp_name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
        category=st.sampled_from(list(ComponentCategory))
    )
    def test_component_add_remove(self, comp_name, category):
        """
        Property Test: Components can be added and removed

        For any Core_Utilities component, add and remove operations
        must work correctly at system configuration time.
        """
        manager = ComponentManager()
        component = SystemComponent(name=comp_name, category=category)

        # Add component
        manager.add_component(component)
        assert comp_name in manager.components

        # Remove component
        removed = manager.remove_component(comp_name)
        assert removed is True
        assert comp_name not in manager.components

    def test_component_enable_disable(self):
        """Test: Components can be enabled and disabled"""
        manager = ComponentManager()
        comp = SystemComponent(name="test", category=ComponentCategory.CORE, enabled=False)

        manager.add_component(comp)

        # Enable
        manager.enable_component("test")
        assert manager.components["test"].enabled is True

        # Disable
        manager.disable_component("test")
        assert manager.components["test"].enabled is False

    def test_component_dependency_enforcement(self):
        """Test: Component dependencies are enforced"""
        manager = ComponentManager()

        base = SystemComponent(name="base", category=ComponentCategory.CORE, enabled=True)
        network = SystemComponent(name="network", category=ComponentCategory.NETWORK,
                                 enabled=True, dependencies=["base"])

        manager.add_component(base)
        manager.add_component(network)

        # Cannot remove base while network depends on it
        with pytest.raises(ValueError, match="depends on it"):
            manager.remove_component("base")

    def test_component_conflict_detection(self):
        """Test: Component conflicts are detected"""
        manager = ComponentManager()

        comp1 = SystemComponent(name="comp1", category=ComponentCategory.CORE, conflicts=["comp2"])
        comp2 = SystemComponent(name="comp2", category=ComponentCategory.CORE, conflicts=["comp1"])

        manager.add_component(comp1)

        # Should not be able to add comp2
        with pytest.raises(ValueError, match="conflicts"):
            manager.add_component(comp2)

    def test_get_components_by_category(self):
        """Test: Components can be filtered by category"""
        manager = ComponentManager()

        manager.add_component(SystemComponent(name="core1", category=ComponentCategory.CORE))
        manager.add_component(SystemComponent(name="net1", category=ComponentCategory.NETWORK))
        manager.add_component(SystemComponent(name="core2", category=ComponentCategory.CORE))

        core_comps = manager.get_components_by_category(ComponentCategory.CORE)

        assert len(core_comps) == 2
        assert all(c.category == ComponentCategory.CORE for c in core_comps)


@pytest.mark.property
class TestSystemConfigIntegration:
    """Test system configuration integration"""

    def test_system_config_creation(self):
        """Test: SystemConfig can be created"""
        config = SystemConfig(
            architecture="x86_64",
            security_level=SecurityLevel.HIGH
        )
        assert config.architecture == "x86_64"
        assert config.security_level == SecurityLevel.HIGH

    def test_system_config_serialization(self):
        """Test: SystemConfig can be serialized"""
        config = SystemConfig(
            architecture="x86_64",
            security_level=SecurityLevel.STANDARD,
            kernel_modules=[
                KernelModule(name="core", category="core", required=True)
            ],
            components=[
                SystemComponent(name="busybox", category=ComponentCategory.CORE)
            ]
        )

        # To JSON
        json_str = config.to_json()
        assert "x86_64" in json_str
        assert "core" in json_str

        # From JSON
        restored = SystemConfig.from_json(json_str)
        assert restored.architecture == "x86_64"
        assert len(restored.kernel_modules) == 1
        assert len(restored.components) == 1

    def test_system_config_manager_save_load(self):
        """Test: SystemConfigManager can save and load configurations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "system.yaml"

            # Create and save
            manager = SystemConfigManager()
            manager.kernel_manager.register_module(
                KernelModule(name="test", category="test")
            )
            manager.save_config(config_path, format="yaml")

            # Load
            manager2 = SystemConfigManager()
            manager2.load_config(config_path, format="yaml")

            assert manager2.kernel_manager.get_module("test") is not None

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(
        arch=st.sampled_from(["x86_64", "aarch64", "armv7"]),
        security=st.sampled_from(list(SecurityLevel))
    )
    def test_configuration_roundtrip(self, arch, security):
        """
        Property Test: Configuration roundtrip preserves data

        For any configuration, saving and loading must preserve all settings.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            config = SystemConfig(
                architecture=arch,
                security_level=security
            )

            manager = SystemConfigManager(config)
            manager.save_config(config_path)

            manager2 = SystemConfigManager()
            manager2.load_config(config_path)

            assert manager2.config.architecture == arch
            assert manager2.config.security_level == security
