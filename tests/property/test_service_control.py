"""
Property Tests for Service Control System

Tests service startup control and management commands.

Properties tested:
- Property 12: サービス起動制御 (Service Startup Control) - 要件 3.4
- Property 27: サービス管理コマンド (Service Management Commands) - 要件 7.5
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, Verbosity

from src.init.service import (
    ServiceConfig,
    ServiceState,
    ServiceManager,
    ServiceController,
    RunLevel,
)


@pytest.mark.property
class TestServiceStartupControl:
    """
    Property 12: サービス起動制御

    任意のサービス設定に対して、明示的に有効化されたサービスのみが起動されなければならない

    Requirement: 3.4
    """

    def test_service_config_creation(self):
        """Test: Service configurations can be created"""
        config = ServiceConfig(
            name="nginx",
            description="Web server",
            enabled=False
        )
        assert config.name == "nginx"
        assert config.enabled is False

    def test_service_manager_initialization(self):
        """Test: Service manager can be initialized"""
        manager = ServiceManager()
        assert manager is not None
        assert len(manager.services) == 0

    def test_service_registration(self):
        """Test: Services can be registered"""
        manager = ServiceManager()
        config = ServiceConfig(name="test-service", enabled=False)

        manager.register_service(config)

        assert "test-service" in manager.services
        assert manager.runtime_states["test-service"] == ServiceState.STOPPED

    def test_explicit_enablement_required(self):
        """
        Test: Only explicitly enabled services are in enabled list

        Requirement 3.4: Only explicitly enabled services should start
        """
        manager = ServiceManager()

        # Register services - one enabled, one disabled
        manager.register_service(ServiceConfig(name="enabled-svc", enabled=True))
        manager.register_service(ServiceConfig(name="disabled-svc", enabled=False))

        enabled = manager.get_enabled_services()

        # Only enabled service should be in the list
        assert len(enabled) == 1
        assert enabled[0].name == "enabled-svc"

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(
        service_name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
        enabled=st.booleans()
    )
    def test_only_enabled_services_start_on_boot(self, service_name, enabled):
        """
        Property Test: Only explicitly enabled services start

        For any service configuration, only enabled services should
        be started during system boot.
        """
        manager = ServiceManager()
        config = ServiceConfig(name=service_name, enabled=enabled)

        manager.register_service(config)

        # Start enabled services
        results = manager.start_enabled_services()

        if enabled:
            # Should have been started
            assert service_name in results
            assert results[service_name] is True
            assert manager.runtime_states[service_name] == ServiceState.RUNNING
        else:
            # Should NOT have been started
            assert service_name not in results or results[service_name] is False
            assert manager.runtime_states[service_name] == ServiceState.STOPPED

    def test_service_enable_disable(self):
        """Test: Services can be enabled and disabled"""
        manager = ServiceManager()
        config = ServiceConfig(name="test", enabled=False)

        manager.register_service(config)

        # Enable
        manager.enable_service("test")
        assert manager.services["test"].enabled is True

        # Disable
        manager.disable_service("test")
        assert manager.services["test"].enabled is False

    def test_run_level_filtering(self):
        """Test: Services can be filtered by run level"""
        manager = ServiceManager()

        manager.register_service(ServiceConfig(
            name="boot-service",
            enabled=True,
            run_levels=["boot"]
        ))
        manager.register_service(ServiceConfig(
            name="default-service",
            enabled=True,
            run_levels=["default"]
        ))

        # Get enabled services for boot run level
        boot_services = manager.get_enabled_services(run_level="boot")
        assert len(boot_services) == 1
        assert boot_services[0].name == "boot-service"

        # Get enabled services for default run level
        default_services = manager.get_enabled_services(run_level="default")
        assert len(default_services) == 1
        assert default_services[0].name == "default-service"

    def test_disabled_service_not_started_automatically(self):
        """
        Test: Disabled services are never started automatically

        Critical test for Requirement 3.4
        """
        manager = ServiceManager()

        # Register disabled service
        manager.register_service(ServiceConfig(name="disabled", enabled=False))

        # Start enabled services (should not start disabled service)
        results = manager.start_enabled_services()

        # Disabled service should not be in results
        assert "disabled" not in results or results["disabled"] is False
        assert manager.runtime_states["disabled"] == ServiceState.STOPPED


@pytest.mark.property
class TestServiceManagementCommands:
    """
    Property 27: サービス管理コマンド

    任意のサービスに対して、Init_Systemは開始、停止、再起動、ステータス操作の
    ためのコマンドを提供しなければならない

    Requirement: 7.5
    """

    def test_start_command_available(self):
        """Test: Start command is available"""
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name="test", enabled=True))

        # Start command should work
        result = manager.start_service("test")
        assert result is True
        assert manager.runtime_states["test"] == ServiceState.RUNNING

    def test_stop_command_available(self):
        """Test: Stop command is available"""
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name="test", enabled=True))

        # Start then stop
        manager.start_service("test")
        result = manager.stop_service("test")

        assert result is True
        assert manager.runtime_states["test"] == ServiceState.STOPPED

    def test_restart_command_available(self):
        """Test: Restart command is available"""
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name="test", enabled=True))

        # Start then restart
        manager.start_service("test")
        result = manager.restart_service("test")

        assert result is True
        assert manager.runtime_states["test"] == ServiceState.RUNNING

    def test_status_command_available(self):
        """Test: Status command is available"""
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name="test", enabled=True))

        # Get status
        status = manager.get_status("test")

        assert status is not None
        assert status.name == "test"
        assert status.state == ServiceState.STOPPED
        assert status.enabled is True

    @settings(verbosity=Verbosity.verbose, max_examples=10)
    @given(
        service_name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
    )
    def test_all_management_commands_available(self, service_name):
        """
        Property Test: All management commands are available

        For any service, Init_System must provide start, stop,
        restart, and status commands.
        """
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name=service_name, enabled=True))

        # All commands should be callable without errors
        status1 = manager.get_status(service_name)
        assert status1.state == ServiceState.STOPPED

        start_result = manager.start_service(service_name)
        assert start_result is True

        status2 = manager.get_status(service_name)
        assert status2.state == ServiceState.RUNNING

        restart_result = manager.restart_service(service_name)
        assert restart_result is True

        status3 = manager.get_status(service_name)
        assert status3.state == ServiceState.RUNNING

        stop_result = manager.stop_service(service_name)
        assert stop_result is True

        status4 = manager.get_status(service_name)
        assert status4.state == ServiceState.STOPPED

    def test_service_dependency_handling(self):
        """Test: Service dependencies are handled correctly"""
        manager = ServiceManager()

        # Register services with dependencies
        manager.register_service(ServiceConfig(name="base", enabled=True))
        manager.register_service(ServiceConfig(
            name="dependent",
            enabled=True,
            dependencies=["base"]
        ))

        # Starting dependent should auto-start base
        manager.start_service("dependent")

        assert manager.runtime_states["base"] == ServiceState.RUNNING
        assert manager.runtime_states["dependent"] == ServiceState.RUNNING

    def test_cannot_stop_service_with_dependents(self):
        """Test: Cannot stop service if others depend on it"""
        manager = ServiceManager()

        manager.register_service(ServiceConfig(name="base", enabled=True))
        manager.register_service(ServiceConfig(
            name="dependent",
            enabled=True,
            dependencies=["base"]
        ))

        # Start both
        manager.start_service("dependent")

        # Should not be able to stop base while dependent is running
        with pytest.raises(ValueError, match="depends on it"):
            manager.stop_service("base")

    def test_controller_start_command(self):
        """Test: Controller start command works"""
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name="test", enabled=True))

        controller = ServiceController(manager)
        exit_code = controller.cmd_start("test")

        assert exit_code == 0
        assert manager.runtime_states["test"] == ServiceState.RUNNING

    def test_controller_stop_command(self):
        """Test: Controller stop command works"""
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name="test", enabled=True))

        controller = ServiceController(manager)
        controller.cmd_start("test")
        exit_code = controller.cmd_stop("test")

        assert exit_code == 0
        assert manager.runtime_states["test"] == ServiceState.STOPPED

    def test_controller_restart_command(self):
        """Test: Controller restart command works"""
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name="test", enabled=True))

        controller = ServiceController(manager)
        controller.cmd_start("test")
        exit_code = controller.cmd_restart("test")

        assert exit_code == 0
        assert manager.runtime_states["test"] == ServiceState.RUNNING

    def test_controller_status_command(self):
        """Test: Controller status command works"""
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name="test", enabled=True))

        controller = ServiceController(manager)
        exit_code = controller.cmd_status("test")

        assert exit_code == 0

    def test_controller_list_command(self):
        """Test: Controller list command works"""
        manager = ServiceManager()
        manager.register_service(ServiceConfig(name="test1", enabled=True))
        manager.register_service(ServiceConfig(name="test2", enabled=False))

        controller = ServiceController(manager)
        exit_code = controller.cmd_list()

        assert exit_code == 0


@pytest.mark.property
class TestServiceConfigPersistence:
    """Test service configuration save/load"""

    def test_save_and_load_config(self):
        """Test: Service configurations can be saved and loaded"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "services.json"

            # Create and save
            manager1 = ServiceManager()
            manager1.register_service(ServiceConfig(
                name="nginx",
                description="Web server",
                enabled=True,
                dependencies=["network"]
            ))
            manager1.save_config(config_path)

            # Load
            manager2 = ServiceManager()
            manager2.load_config(config_path)

            assert "nginx" in manager2.services
            service = manager2.services["nginx"]
            assert service.description == "Web server"
            assert service.enabled is True
            assert service.dependencies == ["network"]

    @settings(verbosity=Verbosity.verbose, max_examples=5)
    @given(
        name=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd'))),
        enabled=st.booleans()
    )
    def test_config_roundtrip(self, name, enabled):
        """
        Property Test: Configuration roundtrip preserves data

        For any configuration, saving and loading must preserve settings.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            config = ServiceConfig(name=name, enabled=enabled)

            manager1 = ServiceManager()
            manager1.register_service(config)
            manager1.save_config(config_path)

            manager2 = ServiceManager()
            manager2.load_config(config_path)

            assert name in manager2.services
            assert manager2.services[name].enabled == enabled
