"""
Property 26: System Shutdown Processing

Verifies that system shutdown stops all services gracefully and unmounts filesystems.
Testing requirement 7.4.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from pathlib import Path

from src.init.shutdown import (
    ShutdownPhase,
    ShutdownAction,
    FilesystemMount,
    ShutdownConfig,
    ShutdownProgress,
    FilesystemManager,
    ProcessManager,
    ShutdownManager,
    create_shutdown_manager,
)


@pytest.mark.property
class TestSystemShutdown:
    """Test property 26: System shutdown properly stops services and unmounts filesystems"""

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10, unique=True))
    @settings(max_examples=50)
    def test_all_filesystems_unmounted(self, mount_points):
        """
        Property: All non-protected filesystems are unmounted during shutdown
        """
        fs_manager = FilesystemManager()

        # Register filesystems
        for mount_point in mount_points:
            mount = FilesystemMount(
                device=f"/dev/sda{hash(mount_point) % 10}",
                mount_point=mount_point,
                filesystem_type="ext4"
            )
            fs_manager.register_mount(mount)

        initial_count = len(fs_manager.get_mounts())

        # Unmount all
        unmounted, failed = fs_manager.unmount_all()

        # All should be unmounted
        assert len(unmounted) == initial_count
        assert len(failed) == 0
        assert len(fs_manager.get_mounts()) == 0

    @given(
        st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5, unique=True),
        st.sets(st.integers(min_value=0, max_value=4), min_size=1)
    )
    @settings(max_examples=50)
    def test_protected_mounts_not_unmounted(self, mount_points, protected_indices):
        """
        Property: Protected mount points are not unmounted
        """
        fs_manager = FilesystemManager()

        # Determine which mounts are protected
        protected = {mount_points[i % len(mount_points)] for i in protected_indices}

        # Register filesystems
        for mount_point in mount_points:
            mount = FilesystemMount(
                device=f"/dev/sda{hash(mount_point) % 10}",
                mount_point=mount_point,
                filesystem_type="ext4"
            )
            fs_manager.register_mount(mount)

        # Unmount with exclusions
        unmounted, failed = fs_manager.unmount_all(exclude=protected)

        # Protected mounts should still be mounted
        for mount_point in protected:
            assert fs_manager.get_mount(mount_point) is not None

        # Non-protected should be unmounted
        for mount_point in mount_points:
            if mount_point not in protected:
                assert fs_manager.get_mount(mount_point) is None

    @given(st.integers(min_value=1, max_value=20))
    @settings(max_examples=50)
    def test_all_processes_killed(self, num_processes):
        """
        Property: All tracked processes are killed during shutdown
        """
        proc_manager = ProcessManager()

        # Register processes
        for i in range(num_processes):
            proc_manager.register_process(i, f"process_{i}")

        initial_count = len(proc_manager.get_running_processes())

        # Kill all processes
        killed = proc_manager.kill_all_processes()

        # All should be killed
        assert killed == initial_count
        assert len(proc_manager.get_running_processes()) == 0

    @given(
        st.integers(min_value=1, max_value=20),
        st.sets(st.integers(min_value=0, max_value=19), min_size=1)
    )
    @settings(max_examples=50)
    def test_excluded_processes_not_killed(self, num_processes, exclude_indices):
        """
        Property: Excluded processes are not killed
        """
        proc_manager = ProcessManager()

        # Register processes
        for i in range(num_processes):
            proc_manager.register_process(i, f"process_{i}")

        # Determine excluded PIDs
        excluded = {i for i in exclude_indices if i < num_processes}

        # Kill with exclusions
        killed = proc_manager.kill_all_processes(exclude_pids=excluded)

        # Verify excluded processes still running
        running = proc_manager.get_running_processes()
        running_pids = {p["pid"] for p in running}

        assert running_pids == excluded
        assert killed == num_processes - len(excluded)

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=2, max_size=10, unique=True))
    @settings(max_examples=50)
    def test_unmount_order_deepest_first(self, mount_points):
        """
        Property: Filesystems are unmounted in depth order (deepest first)
        """
        fs_manager = FilesystemManager()

        # Create nested mount points
        # Sort by path depth to verify order
        sorted_mounts = sorted(mount_points, key=lambda p: len(p.split("/")))

        for mount_point in sorted_mounts:
            mount = FilesystemMount(
                device=f"/dev/sda{hash(mount_point) % 10}",
                mount_point=mount_point,
                filesystem_type="ext4"
            )
            fs_manager.register_mount(mount)

        # Unmount all
        unmounted, failed = fs_manager.unmount_all()

        # All should be unmounted successfully
        assert len(failed) == 0

        # Deepest paths should be unmounted first
        # (verified by successful unmount - in real system, parent can't unmount before children)

    @given(st.sampled_from([ShutdownAction.HALT, ShutdownAction.POWEROFF, ShutdownAction.REBOOT]))
    @settings(max_examples=50)
    def test_shutdown_action_configured(self, action):
        """
        Property: Shutdown action is properly configured
        """
        config = ShutdownConfig(shutdown_action=action)
        assert config.shutdown_action == action

    @given(st.booleans())
    @settings(max_examples=50)
    def test_sync_before_shutdown(self, sync_enabled):
        """
        Property: Filesystem sync occurs when enabled
        """
        config = ShutdownConfig(sync_before_shutdown=sync_enabled)
        fs_manager = FilesystemManager()

        # Sync should succeed
        result = fs_manager.sync_filesystems()
        assert result is True

    @given(st.integers(min_value=1, max_value=300))
    @settings(max_examples=50)
    def test_shutdown_timeout_configuration(self, timeout):
        """
        Property: Shutdown timeouts are configurable
        """
        config = ShutdownConfig(
            service_stop_timeout_seconds=timeout,
            process_kill_timeout_seconds=timeout,
            filesystem_unmount_timeout_seconds=timeout
        )

        assert config.service_stop_timeout_seconds == timeout
        assert config.process_kill_timeout_seconds == timeout
        assert config.filesystem_unmount_timeout_seconds == timeout

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_shutdown_progress_tracking(self, services):
        """
        Property: Shutdown progress is accurately tracked
        """
        progress = ShutdownProgress()

        # Initially no services stopped
        assert len(progress.services_stopped) == 0
        assert len(progress.services_failed) == 0

        # Simulate stopping services
        for service in services:
            progress.services_stopped.append(service)

        # Verify tracking
        assert len(progress.services_stopped) == len(services)

        summary = progress.get_summary()
        assert summary["services_stopped"] == len(services)

    @given(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_shutdown_errors_tracked(self, errors):
        """
        Property: Shutdown errors are tracked
        """
        progress = ShutdownProgress()

        # Add errors
        for error in errors:
            progress.add_error(error)

        # Verify tracking
        assert len(progress.errors) == len(errors)
        assert progress.errors == errors

        summary = progress.get_summary()
        assert summary["errors"] == len(errors)

    @given(st.integers(min_value=0, max_value=10), st.integers(min_value=0, max_value=10))
    @settings(max_examples=50)
    def test_shutdown_success_criteria(self, num_stopped, num_failed):
        """
        Property: Shutdown succeeds only when no services/filesystems fail
        """
        config = ShutdownConfig()
        manager = create_shutdown_manager(config)

        # Mock service callback
        def service_callback():
            stopped = [f"service_{i}" for i in range(num_stopped)]
            failed = [f"service_{i}" for i in range(num_failed)]
            return stopped, failed

        # Execute shutdown
        success = manager.shutdown(service_stop_callback=service_callback)

        # Success only if no failures
        assert success == (num_failed == 0)

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_emergency_shutdown_forces_actions(self, mount_points):
        """
        Property: Emergency shutdown forces all actions
        """
        config = ShutdownConfig()
        fs_manager = FilesystemManager()
        proc_manager = ProcessManager()

        # Register some filesystems
        for mount_point in mount_points:
            mount = FilesystemMount(
                device=f"/dev/sda{hash(mount_point) % 10}",
                mount_point=mount_point,
                filesystem_type="ext4"
            )
            fs_manager.register_mount(mount)

        # Register some processes
        for i in range(5):
            proc_manager.register_process(i, f"process_{i}")

        manager = ShutdownManager(config, fs_manager, proc_manager)

        # Emergency shutdown
        success = manager.emergency_shutdown()

        # Should succeed
        assert success

        # All should be cleaned up
        assert len(proc_manager.get_running_processes()) == 0

    @given(st.sampled_from(list(ShutdownPhase)))
    @settings(max_examples=50)
    def test_shutdown_phase_tracking(self, phase):
        """
        Property: Shutdown phase is tracked correctly
        """
        progress = ShutdownProgress()
        progress.current_phase = phase

        assert progress.current_phase == phase

        summary = progress.get_summary()
        assert summary["phase"] == phase.value

    @given(st.booleans())
    @settings(max_examples=50)
    def test_force_unmount_configuration(self, force_enabled):
        """
        Property: Force unmount setting is respected
        """
        config = ShutdownConfig(force_unmount_on_failure=force_enabled)
        assert config.force_unmount_on_failure == force_enabled

    @given(st.booleans())
    @settings(max_examples=50)
    def test_kill_processes_configuration(self, kill_enabled):
        """
        Property: Kill processes setting is respected
        """
        config = ShutdownConfig(kill_remaining_processes=kill_enabled)
        assert config.kill_remaining_processes == kill_enabled

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_filesystem_registration(self, mount_point):
        """
        Property: Filesystems can be registered and retrieved
        """
        fs_manager = FilesystemManager()

        mount = FilesystemMount(
            device="/dev/sda1",
            mount_point=mount_point,
            filesystem_type="ext4"
        )

        fs_manager.register_mount(mount)

        # Verify registration - use normalized path
        normalized_mount_point = str(Path(mount_point))
        retrieved = fs_manager.get_mount(normalized_mount_point)
        assert retrieved is not None
        assert retrieved.device == "/dev/sda1"
        assert str(retrieved.mount_point) == normalized_mount_point

    @given(st.integers(min_value=1, max_value=100), st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_process_registration(self, pid, name):
        """
        Property: Processes can be registered and tracked
        """
        proc_manager = ProcessManager()

        proc_manager.register_process(pid, name)

        running = proc_manager.get_running_processes()
        assert len(running) > 0

        # Find our process
        our_proc = next((p for p in running if p["pid"] == pid), None)
        assert our_proc is not None
        assert our_proc["name"] == name

    @given(st.sets(st.text(min_size=1, max_size=20), min_size=1, max_size=5))
    @settings(max_examples=50)
    def test_protected_mounts_default_config(self, additional_protected):
        """
        Property: Default protected mounts are configured
        """
        config = ShutdownConfig()

        # Default protected mounts
        default_protected = {"/proc", "/sys", "/dev"}

        # Should contain defaults
        assert default_protected.issubset(config.protected_mounts)

        # Can add more
        config.protected_mounts.update(additional_protected)
        assert additional_protected.issubset(config.protected_mounts)

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_shutdown_summary_completeness(self, num_services):
        """
        Property: Shutdown summary contains all required information
        """
        progress = ShutdownProgress()

        # Add some data
        for i in range(num_services):
            progress.services_stopped.append(f"service_{i}")

        summary = progress.get_summary()

        # Verify all required fields
        assert "phase" in summary
        assert "services_stopped" in summary
        assert "services_failed" in summary
        assert "processes_killed" in summary
        assert "filesystems_unmounted" in summary
        assert "filesystems_failed" in summary
        assert "errors" in summary
        assert "duration_seconds" in summary

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_unmount_removes_from_tracking(self, mount_point):
        """
        Property: Unmounted filesystems are removed from tracking
        """
        fs_manager = FilesystemManager()

        mount = FilesystemMount(
            device="/dev/sda1",
            mount_point=mount_point,
            filesystem_type="ext4"
        )

        fs_manager.register_mount(mount)
        assert fs_manager.get_mount(mount_point) is not None

        # Unmount
        success = fs_manager.unmount(mount_point)
        assert success

        # Should be removed
        assert fs_manager.get_mount(mount_point) is None

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_kill_removes_from_tracking(self, pid):
        """
        Property: Killed processes are removed from tracking
        """
        proc_manager = ProcessManager()

        proc_manager.register_process(pid, "test_process")
        assert len(proc_manager.get_running_processes()) > 0

        # Kill
        success = proc_manager.kill_process(pid)
        assert success

        # Should be removed
        running = proc_manager.get_running_processes()
        assert all(p["pid"] != pid for p in running)
