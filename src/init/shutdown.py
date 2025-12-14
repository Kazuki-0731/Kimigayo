"""
System Shutdown Management for Kimigayo OS

Provides graceful shutdown with service stopping, filesystem unmounting,
and resource cleanup.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Any, Tuple
from datetime import datetime


class ShutdownPhase(Enum):
    """Phases of system shutdown"""
    INIT = "init"                          # Initialization
    STOP_SERVICES = "stop_services"        # Stopping services
    KILL_PROCESSES = "kill_processes"      # Kill remaining processes
    UNMOUNT_FILESYSTEMS = "unmount_fs"     # Unmount filesystems
    CLEANUP_RESOURCES = "cleanup"          # Resource cleanup
    POWEROFF = "poweroff"                  # Final poweroff/halt/reboot


class ShutdownAction(Enum):
    """System shutdown actions"""
    HALT = "halt"         # Halt system
    POWEROFF = "poweroff" # Power off system
    REBOOT = "reboot"     # Reboot system


@dataclass
class FilesystemMount:
    """Information about a mounted filesystem"""
    device: str
    mount_point: Path
    filesystem_type: str
    options: List[str] = field(default_factory=list)
    read_only: bool = False

    def __post_init__(self):
        if isinstance(self.mount_point, str):
            self.mount_point = Path(self.mount_point)


@dataclass
class ShutdownConfig:
    """Configuration for system shutdown"""

    # Timeouts
    service_stop_timeout_seconds: int = 30
    process_kill_timeout_seconds: int = 10
    filesystem_unmount_timeout_seconds: int = 15

    # Behavior
    kill_remaining_processes: bool = True
    force_unmount_on_failure: bool = False
    sync_before_shutdown: bool = True

    # Protected mounts (never unmount these)
    protected_mounts: Set[str] = field(default_factory=lambda: {"/proc", "/sys", "/dev"})

    # Actions
    shutdown_action: ShutdownAction = ShutdownAction.POWEROFF


@dataclass
class ShutdownProgress:
    """Track shutdown progress"""
    current_phase: ShutdownPhase = ShutdownPhase.INIT
    services_stopped: List[str] = field(default_factory=list)
    services_failed: List[str] = field(default_factory=list)
    processes_killed: int = 0
    filesystems_unmounted: List[str] = field(default_factory=list)
    filesystems_failed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)

    def get_summary(self) -> Dict[str, Any]:
        """Get shutdown summary"""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return {
            "phase": self.current_phase.value,
            "services_stopped": len(self.services_stopped),
            "services_failed": len(self.services_failed),
            "processes_killed": self.processes_killed,
            "filesystems_unmounted": len(self.filesystems_unmounted),
            "filesystems_failed": len(self.filesystems_failed),
            "errors": len(self.errors),
            "duration_seconds": duration
        }


class FilesystemManager:
    """Manages filesystem mounting and unmounting"""

    def __init__(self):
        self.mounts: Dict[str, FilesystemMount] = {}

    def register_mount(self, mount: FilesystemMount):
        """Register a mounted filesystem"""
        self.mounts[str(mount.mount_point)] = mount

    def get_mounts(self) -> List[FilesystemMount]:
        """Get all registered mounts"""
        return list(self.mounts.values())

    def get_mount(self, mount_point: str) -> Optional[FilesystemMount]:
        """Get mount by mount point"""
        return self.mounts.get(mount_point)

    def unmount(self, mount_point: str, force: bool = False) -> bool:
        """
        Unmount a filesystem.

        Args:
            mount_point: Path to unmount
            force: Force unmount if normal unmount fails

        Returns:
            True if unmounted successfully
        """
        mount = self.mounts.get(mount_point)
        if not mount:
            return False

        # Mock implementation - would call umount syscall
        # In real implementation:
        # - Try normal unmount first
        # - If force=True and normal fails, try lazy unmount (-l) or force (-f)

        # Remove from tracking
        del self.mounts[mount_point]
        return True

    def unmount_all(
        self,
        exclude: Optional[Set[str]] = None,
        force: bool = False
    ) -> Tuple[List[str], List[str]]:
        """
        Unmount all filesystems.

        Args:
            exclude: Set of mount points to exclude
            force: Force unmount if normal unmount fails

        Returns:
            Tuple of (successfully unmounted, failed to unmount)
        """
        if exclude is None:
            exclude = set()

        success = []
        failed = []

        # Get mounts sorted by depth (deepest first)
        mounts = sorted(
            self.mounts.values(),
            key=lambda m: len(str(m.mount_point).split("/")),
            reverse=True
        )

        for mount in mounts:
            mount_point = str(mount.mount_point)

            # Skip excluded mounts
            if mount_point in exclude:
                continue

            # Try to unmount
            if self.unmount(mount_point, force=force):
                success.append(mount_point)
            else:
                failed.append(mount_point)

        return success, failed

    def sync_filesystems(self) -> bool:
        """
        Sync all filesystems.
        Ensures all pending writes are flushed to disk.

        Returns:
            True if sync succeeded
        """
        # Mock implementation - would call sync() syscall
        return True


class ProcessManager:
    """Manages process tracking and termination"""

    def __init__(self):
        self.processes: Dict[int, Dict[str, Any]] = {}

    def register_process(self, pid: int, name: str, service: Optional[str] = None):
        """Register a tracked process"""
        self.processes[pid] = {
            "name": name,
            "service": service
        }

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """
        Kill a process.

        Args:
            pid: Process ID to kill
            force: Use SIGKILL instead of SIGTERM

        Returns:
            True if process was killed
        """
        if pid not in self.processes:
            return False

        # Mock implementation - would send signal to process
        # In real implementation:
        # - If force=False, send SIGTERM and wait
        # - If force=True or SIGTERM times out, send SIGKILL

        del self.processes[pid]
        return True

    def kill_all_processes(
        self,
        exclude_pids: Optional[Set[int]] = None,
        force: bool = False
    ) -> int:
        """
        Kill all tracked processes.

        Args:
            exclude_pids: Set of PIDs to exclude
            force: Use SIGKILL instead of SIGTERM

        Returns:
            Number of processes killed
        """
        if exclude_pids is None:
            exclude_pids = set()

        killed = 0
        pids_to_kill = [pid for pid in self.processes.keys() if pid not in exclude_pids]

        for pid in pids_to_kill:
            if self.kill_process(pid, force=force):
                killed += 1

        return killed

    def get_running_processes(self) -> List[Dict[str, Any]]:
        """Get list of running processes"""
        return [
            {"pid": pid, **info}
            for pid, info in self.processes.items()
        ]


class ShutdownManager:
    """Manages system shutdown process"""

    def __init__(
        self,
        config: ShutdownConfig,
        filesystem_manager: FilesystemManager,
        process_manager: ProcessManager
    ):
        self.config = config
        self.fs_manager = filesystem_manager
        self.proc_manager = process_manager
        self.progress = ShutdownProgress()

    def shutdown(self, service_stop_callback=None) -> bool:
        """
        Execute full system shutdown.

        Args:
            service_stop_callback: Callback function to stop services.
                                   Should return (stopped, failed) lists.

        Returns:
            True if shutdown completed successfully
        """
        self.progress.start_time = datetime.now()

        try:
            # Phase 1: Stop services
            self.progress.current_phase = ShutdownPhase.STOP_SERVICES
            if service_stop_callback:
                stopped, failed = service_stop_callback()
                self.progress.services_stopped = stopped
                self.progress.services_failed = failed

                if failed:
                    self.progress.add_error(f"Failed to stop {len(failed)} services")

            # Phase 2: Kill remaining processes
            if self.config.kill_remaining_processes:
                self.progress.current_phase = ShutdownPhase.KILL_PROCESSES
                killed = self.proc_manager.kill_all_processes()
                self.progress.processes_killed = killed

            # Phase 3: Sync filesystems
            if self.config.sync_before_shutdown:
                if not self.fs_manager.sync_filesystems():
                    self.progress.add_error("Failed to sync filesystems")

            # Phase 4: Unmount filesystems
            self.progress.current_phase = ShutdownPhase.UNMOUNT_FILESYSTEMS
            unmounted, failed = self.fs_manager.unmount_all(
                exclude=self.config.protected_mounts,
                force=self.config.force_unmount_on_failure
            )
            self.progress.filesystems_unmounted = unmounted
            self.progress.filesystems_failed = failed

            if failed:
                self.progress.add_error(f"Failed to unmount {len(failed)} filesystems")

            # Phase 5: Cleanup
            self.progress.current_phase = ShutdownPhase.CLEANUP_RESOURCES
            # Additional cleanup could be performed here

            # Phase 6: Final action
            self.progress.current_phase = ShutdownPhase.POWEROFF
            # Would execute halt/poweroff/reboot here

            self.progress.end_time = datetime.now()

            # Success if no critical errors
            return len(self.progress.services_failed) == 0 and \
                   len(self.progress.filesystems_failed) == 0

        except Exception as e:
            self.progress.add_error(f"Shutdown error: {str(e)}")
            self.progress.end_time = datetime.now()
            return False

    def emergency_shutdown(self) -> bool:
        """
        Emergency shutdown - fast but less graceful.
        Skips most cleanup and forces actions.

        Returns:
            True if emergency shutdown completed
        """
        try:
            # Kill all processes immediately
            self.proc_manager.kill_all_processes(force=True)

            # Force unmount all filesystems
            self.fs_manager.unmount_all(
                exclude=self.config.protected_mounts,
                force=True
            )

            return True

        except Exception:
            return False

    def get_progress(self) -> ShutdownProgress:
        """Get current shutdown progress"""
        return self.progress


def create_shutdown_manager(
    config: Optional[ShutdownConfig] = None
) -> ShutdownManager:
    """
    Create a shutdown manager with default components.

    Args:
        config: Optional shutdown configuration

    Returns:
        Configured ShutdownManager
    """
    if config is None:
        config = ShutdownConfig()

    fs_manager = FilesystemManager()
    proc_manager = ProcessManager()

    return ShutdownManager(config, fs_manager, proc_manager)
