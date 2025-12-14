"""
Security Update Priority System for Kimigayo OS Package Manager

Implements priority-based update system where security updates
take precedence over regular updates.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from datetime import datetime
import json
from pathlib import Path


class UpdatePriority(Enum):
    """Priority levels for package updates"""
    CRITICAL_SECURITY = 0   # Critical security vulnerabilities
    HIGH_SECURITY = 1       # High priority security updates
    MEDIUM_SECURITY = 2     # Medium priority security updates
    LOW_SECURITY = 3        # Low priority security updates
    ENHANCEMENT = 4         # Feature enhancements
    BUGFIX = 5             # Non-security bug fixes
    OPTIONAL = 6           # Optional updates


class UpdateType(Enum):
    """Type of update"""
    SECURITY = "security"
    BUGFIX = "bugfix"
    ENHANCEMENT = "enhancement"
    OPTIONAL = "optional"


@dataclass
class SecurityAdvisory:
    """Security advisory information"""
    advisory_id: str
    cve_ids: List[str] = field(default_factory=list)
    severity: str = "medium"  # critical, high, medium, low
    description: str = ""
    published_date: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "advisory_id": self.advisory_id,
            "cve_ids": self.cve_ids,
            "severity": self.severity,
            "description": self.description,
            "published_date": self.published_date.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SecurityAdvisory":
        """Create from dictionary"""
        return cls(
            advisory_id=data["advisory_id"],
            cve_ids=data.get("cve_ids", []),
            severity=data.get("severity", "medium"),
            description=data.get("description", ""),
            published_date=datetime.fromisoformat(data.get("published_date", datetime.now().isoformat()))
        )


@dataclass
class PackageUpdate:
    """Package update information"""
    package_name: str
    current_version: str
    new_version: str
    update_type: UpdateType
    priority: UpdatePriority
    security_advisory: Optional[SecurityAdvisory] = None
    size_bytes: int = 0
    description: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "package_name": self.package_name,
            "current_version": self.current_version,
            "new_version": self.new_version,
            "update_type": self.update_type.value,
            "priority": self.priority.value,
            "security_advisory": self.security_advisory.to_dict() if self.security_advisory else None,
            "size_bytes": self.size_bytes,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PackageUpdate":
        """Create from dictionary"""
        return cls(
            package_name=data["package_name"],
            current_version=data["current_version"],
            new_version=data["new_version"],
            update_type=UpdateType(data["update_type"]),
            priority=UpdatePriority(data["priority"]),
            security_advisory=SecurityAdvisory.from_dict(data["security_advisory"]) if data.get("security_advisory") else None,
            size_bytes=data.get("size_bytes", 0),
            description=data.get("description", "")
        )


class UpdatePriorityManager:
    """Manages update priorities and security updates"""

    def __init__(self, security_db_path: Optional[Path] = None):
        """
        Initialize priority manager.

        Args:
            security_db_path: Path to security advisory database
        """
        self.security_db_path = security_db_path
        self.security_advisories: Dict[str, SecurityAdvisory] = {}

        if security_db_path and security_db_path.exists():
            self._load_security_advisories()

    def _load_security_advisories(self):
        """Load security advisories from database"""
        if not self.security_db_path or not self.security_db_path.exists():
            return

        with open(self.security_db_path, 'r') as f:
            data = json.load(f)

        for advisory_data in data.get("advisories", []):
            advisory = SecurityAdvisory.from_dict(advisory_data)
            self.security_advisories[advisory.advisory_id] = advisory

    def calculate_priority(
        self,
        update_type: UpdateType,
        severity: Optional[str] = None
    ) -> UpdatePriority:
        """
        Calculate priority for an update.

        Args:
            update_type: Type of update
            severity: Security severity (if applicable)

        Returns:
            Calculated priority level
        """
        if update_type == UpdateType.SECURITY:
            if severity == "critical":
                return UpdatePriority.CRITICAL_SECURITY
            elif severity == "high":
                return UpdatePriority.HIGH_SECURITY
            elif severity == "medium":
                return UpdatePriority.MEDIUM_SECURITY
            else:
                return UpdatePriority.LOW_SECURITY
        elif update_type == UpdateType.BUGFIX:
            return UpdatePriority.BUGFIX
        elif update_type == UpdateType.ENHANCEMENT:
            return UpdatePriority.ENHANCEMENT
        else:
            return UpdatePriority.OPTIONAL

    def classify_update(
        self,
        package_name: str,
        current_version: str,
        new_version: str,
        advisory_id: Optional[str] = None
    ) -> PackageUpdate:
        """
        Classify an update and assign priority.

        Args:
            package_name: Name of package
            current_version: Current version
            new_version: New version
            advisory_id: Security advisory ID (if applicable)

        Returns:
            PackageUpdate with assigned priority
        """
        # Check if this is a security update
        if advisory_id and advisory_id in self.security_advisories:
            advisory = self.security_advisories[advisory_id]
            priority = self.calculate_priority(
                UpdateType.SECURITY,
                advisory.severity
            )

            return PackageUpdate(
                package_name=package_name,
                current_version=current_version,
                new_version=new_version,
                update_type=UpdateType.SECURITY,
                priority=priority,
                security_advisory=advisory
            )

        # Default to enhancement for non-security updates
        return PackageUpdate(
            package_name=package_name,
            current_version=current_version,
            new_version=new_version,
            update_type=UpdateType.ENHANCEMENT,
            priority=UpdatePriority.ENHANCEMENT
        )

    def sort_updates(self, updates: List[PackageUpdate]) -> List[PackageUpdate]:
        """
        Sort updates by priority.

        Args:
            updates: List of package updates

        Returns:
            Sorted list (highest priority first)
        """
        return sorted(updates, key=lambda u: (u.priority.value, u.package_name))

    def filter_security_updates(
        self,
        updates: List[PackageUpdate]
    ) -> List[PackageUpdate]:
        """
        Filter only security updates.

        Args:
            updates: List of package updates

        Returns:
            List of security updates only
        """
        return [u for u in updates if u.update_type == UpdateType.SECURITY]

    def get_critical_updates(
        self,
        updates: List[PackageUpdate]
    ) -> List[PackageUpdate]:
        """
        Get critical security updates.

        Args:
            updates: List of package updates

        Returns:
            List of critical security updates
        """
        return [
            u for u in updates
            if u.priority == UpdatePriority.CRITICAL_SECURITY
        ]


class AutoUpdateManager:
    """Manages automatic security updates"""

    def __init__(
        self,
        priority_manager: UpdatePriorityManager,
        auto_update_enabled: bool = False
    ):
        """
        Initialize auto-update manager.

        Args:
            priority_manager: Priority manager instance
            auto_update_enabled: Whether auto-updates are enabled
        """
        self.priority_manager = priority_manager
        self.auto_update_enabled = auto_update_enabled
        self.auto_update_log: List[Dict] = []

    def should_auto_update(self, update: PackageUpdate) -> bool:
        """
        Determine if an update should be automatically applied.

        Args:
            update: Package update

        Returns:
            True if should auto-update, False otherwise
        """
        if not self.auto_update_enabled:
            return False

        # Auto-update critical and high security updates
        return update.priority in (
            UpdatePriority.CRITICAL_SECURITY,
            UpdatePriority.HIGH_SECURITY
        )

    def get_auto_update_candidates(
        self,
        updates: List[PackageUpdate]
    ) -> List[PackageUpdate]:
        """
        Get updates that should be automatically applied.

        Args:
            updates: List of available updates

        Returns:
            List of updates to auto-apply
        """
        return [u for u in updates if self.should_auto_update(u)]

    def log_auto_update(
        self,
        update: PackageUpdate,
        success: bool,
        error_message: str = ""
    ):
        """
        Log an auto-update operation.

        Args:
            update: Package update
            success: Whether update succeeded
            error_message: Error message if failed
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "package": update.package_name,
            "version": f"{update.current_version} -> {update.new_version}",
            "priority": update.priority.name,
            "success": success,
            "error_message": error_message
        }
        self.auto_update_log.append(log_entry)

    def get_update_log(self) -> List[Dict]:
        """
        Get auto-update log.

        Returns:
            List of log entries
        """
        return self.auto_update_log.copy()


class UpdateScheduler:
    """Schedules and manages update operations"""

    def __init__(self, priority_manager: UpdatePriorityManager):
        """
        Initialize update scheduler.

        Args:
            priority_manager: Priority manager instance
        """
        self.priority_manager = priority_manager
        self.pending_updates: List[PackageUpdate] = []

    def add_update(self, update: PackageUpdate):
        """
        Add an update to the schedule.

        Args:
            update: Package update to add
        """
        self.pending_updates.append(update)

    def get_next_update(self) -> Optional[PackageUpdate]:
        """
        Get the next update to apply (highest priority).

        Returns:
            Next update or None if no updates pending
        """
        if not self.pending_updates:
            return None

        # Sort by priority and return highest
        sorted_updates = self.priority_manager.sort_updates(self.pending_updates)
        return sorted_updates[0] if sorted_updates else None

    def remove_update(self, package_name: str):
        """
        Remove an update from the schedule.

        Args:
            package_name: Name of package to remove
        """
        self.pending_updates = [
            u for u in self.pending_updates
            if u.package_name != package_name
        ]

    def get_scheduled_updates(
        self,
        priority_filter: Optional[UpdatePriority] = None
    ) -> List[PackageUpdate]:
        """
        Get scheduled updates, optionally filtered by priority.

        Args:
            priority_filter: Filter by this priority level

        Returns:
            List of scheduled updates
        """
        updates = self.pending_updates.copy()

        if priority_filter is not None:
            updates = [u for u in updates if u.priority == priority_filter]

        return self.priority_manager.sort_updates(updates)

    def clear_schedule(self):
        """Clear all scheduled updates"""
        self.pending_updates.clear()
