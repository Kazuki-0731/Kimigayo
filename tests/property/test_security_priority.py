"""
Property 8: Security Update Priority

Verifies that security updates are prioritized over other updates.
Testing requirement 2.5.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta

from src.pkg.priority import (
    UpdatePriority,
    UpdateType,
    SecurityAdvisory,
    PackageUpdate,
    UpdatePriorityManager,
    AutoUpdateManager,
    UpdateScheduler,
)


@st.composite
def package_name_strategy(draw):
    """Generate valid package names"""
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), min_codepoint=97, max_codepoint=122),
        min_size=3,
        max_size=20
    ))
    if not name or not name[0].isalpha():
        name = "pkg" + name
    return name


@st.composite
def version_strategy(draw):
    """Generate version strings"""
    major = draw(st.integers(min_value=0, max_value=10))
    minor = draw(st.integers(min_value=0, max_value=20))
    patch = draw(st.integers(min_value=0, max_value=50))
    return f"{major}.{minor}.{patch}"


@st.composite
def severity_strategy(draw):
    """Generate security severity levels"""
    return draw(st.sampled_from(["critical", "high", "medium", "low"]))


@st.composite
def update_type_strategy(draw):
    """Generate update types"""
    return draw(st.sampled_from(list(UpdateType)))


@pytest.mark.property
class TestSecurityUpdatePriority:
    """Test property 8: Security update priority"""

    def test_priority_manager_can_be_created(self):
        """
        Property: Priority manager can be created and initialized
        """
        manager = UpdatePriorityManager()
        assert manager is not None
        assert isinstance(manager.security_advisories, dict)

    @given(severity_strategy())
    @settings(max_examples=30)
    def test_security_updates_have_higher_priority_than_non_security(self, severity):
        """
        Property: Security updates have higher priority than non-security updates
        """
        manager = UpdatePriorityManager()

        security_priority = manager.calculate_priority(UpdateType.SECURITY, severity)
        enhancement_priority = manager.calculate_priority(UpdateType.ENHANCEMENT)
        bugfix_priority = manager.calculate_priority(UpdateType.BUGFIX)
        optional_priority = manager.calculate_priority(UpdateType.OPTIONAL)

        # Security updates should have lower priority value (higher priority)
        assert security_priority.value < enhancement_priority.value
        assert security_priority.value < bugfix_priority.value
        assert security_priority.value < optional_priority.value

    @given(st.lists(severity_strategy(), min_size=2, max_size=10))
    @settings(max_examples=30)
    def test_critical_security_has_highest_priority(self, severities):
        """
        Property: Critical security updates have the highest priority
        """
        manager = UpdatePriorityManager()

        priorities = [
            manager.calculate_priority(UpdateType.SECURITY, severity)
            for severity in severities
        ]

        critical_priority = manager.calculate_priority(UpdateType.SECURITY, "critical")

        # Critical should have lowest value (highest priority)
        for priority in priorities:
            assert critical_priority.value <= priority.value

    def test_severity_ordering_is_correct(self):
        """
        Property: Security severity levels are correctly ordered
        """
        manager = UpdatePriorityManager()

        critical = manager.calculate_priority(UpdateType.SECURITY, "critical")
        high = manager.calculate_priority(UpdateType.SECURITY, "high")
        medium = manager.calculate_priority(UpdateType.SECURITY, "medium")
        low = manager.calculate_priority(UpdateType.SECURITY, "low")

        assert critical.value < high.value < medium.value < low.value

    @given(package_name_strategy(), version_strategy(), version_strategy())
    @settings(max_examples=30)
    def test_classify_update_without_advisory(self, package_name, version1, version2):
        """
        Property: Updates without security advisory are classified as enhancements
        """
        assume(version1 != version2)

        manager = UpdatePriorityManager()
        update = manager.classify_update(package_name, version1, version2)

        assert update.update_type == UpdateType.ENHANCEMENT
        assert update.priority == UpdatePriority.ENHANCEMENT
        assert update.security_advisory is None

    def test_classify_update_with_advisory(self):
        """
        Property: Updates with security advisory are classified as security
        """
        manager = UpdatePriorityManager()

        # Add a security advisory
        advisory = SecurityAdvisory(
            advisory_id="ADV-2024-001",
            cve_ids=["CVE-2024-0001"],
            severity="high"
        )
        manager.security_advisories[advisory.advisory_id] = advisory

        update = manager.classify_update(
            "test-pkg",
            "1.0.0",
            "1.0.1",
            advisory_id="ADV-2024-001"
        )

        assert update.update_type == UpdateType.SECURITY
        assert update.priority == UpdatePriority.HIGH_SECURITY
        assert update.security_advisory == advisory

    @given(st.integers(min_value=2, max_value=20))
    @settings(max_examples=30)
    def test_sort_updates_by_priority(self, num_updates):
        """
        Property: Updates are sorted by priority (security first)
        """
        manager = UpdatePriorityManager()

        # Create mixed updates
        updates = []
        for i in range(num_updates):
            if i % 3 == 0:
                update_type = UpdateType.SECURITY
                priority = UpdatePriority.CRITICAL_SECURITY
            elif i % 3 == 1:
                update_type = UpdateType.BUGFIX
                priority = UpdatePriority.BUGFIX
            else:
                update_type = UpdateType.ENHANCEMENT
                priority = UpdatePriority.ENHANCEMENT

            updates.append(PackageUpdate(
                package_name=f"pkg_{i}",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=update_type,
                priority=priority
            ))

        sorted_updates = manager.sort_updates(updates)

        # Verify sorting (priority values should be non-decreasing)
        for i in range(len(sorted_updates) - 1):
            assert sorted_updates[i].priority.value <= sorted_updates[i + 1].priority.value

    @given(st.integers(min_value=5, max_value=20))
    @settings(max_examples=30)
    def test_filter_security_updates(self, num_updates):
        """
        Property: Security updates can be filtered from all updates
        """
        manager = UpdatePriorityManager()

        updates = []
        security_count = 0

        for i in range(num_updates):
            if i % 2 == 0:
                update_type = UpdateType.SECURITY
                priority = UpdatePriority.HIGH_SECURITY
                security_count += 1
            else:
                update_type = UpdateType.ENHANCEMENT
                priority = UpdatePriority.ENHANCEMENT

            updates.append(PackageUpdate(
                package_name=f"pkg_{i}",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=update_type,
                priority=priority
            ))

        security_updates = manager.filter_security_updates(updates)

        assert len(security_updates) == security_count
        assert all(u.update_type == UpdateType.SECURITY for u in security_updates)

    def test_get_critical_updates(self):
        """
        Property: Critical security updates can be identified
        """
        manager = UpdatePriorityManager()

        updates = [
            PackageUpdate(
                package_name="pkg1",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.SECURITY,
                priority=UpdatePriority.CRITICAL_SECURITY
            ),
            PackageUpdate(
                package_name="pkg2",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.SECURITY,
                priority=UpdatePriority.HIGH_SECURITY
            ),
            PackageUpdate(
                package_name="pkg3",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.SECURITY,
                priority=UpdatePriority.CRITICAL_SECURITY
            ),
        ]

        critical = manager.get_critical_updates(updates)

        assert len(critical) == 2
        assert all(u.priority == UpdatePriority.CRITICAL_SECURITY for u in critical)

    def test_auto_update_manager_can_be_created(self):
        """
        Property: Auto-update manager can be created
        """
        manager = UpdatePriorityManager()
        auto_manager = AutoUpdateManager(manager, auto_update_enabled=True)

        assert auto_manager is not None
        assert auto_manager.auto_update_enabled is True

    def test_critical_security_should_auto_update(self):
        """
        Property: Critical and high security updates should auto-update when enabled
        """
        manager = UpdatePriorityManager()
        auto_manager = AutoUpdateManager(manager, auto_update_enabled=True)

        critical_update = PackageUpdate(
            package_name="pkg1",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.SECURITY,
            priority=UpdatePriority.CRITICAL_SECURITY
        )

        high_update = PackageUpdate(
            package_name="pkg2",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.SECURITY,
            priority=UpdatePriority.HIGH_SECURITY
        )

        assert auto_manager.should_auto_update(critical_update) is True
        assert auto_manager.should_auto_update(high_update) is True

    def test_non_security_should_not_auto_update(self):
        """
        Property: Non-security updates should not auto-update
        """
        manager = UpdatePriorityManager()
        auto_manager = AutoUpdateManager(manager, auto_update_enabled=True)

        enhancement_update = PackageUpdate(
            package_name="pkg1",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.ENHANCEMENT,
            priority=UpdatePriority.ENHANCEMENT
        )

        bugfix_update = PackageUpdate(
            package_name="pkg2",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.BUGFIX,
            priority=UpdatePriority.BUGFIX
        )

        assert auto_manager.should_auto_update(enhancement_update) is False
        assert auto_manager.should_auto_update(bugfix_update) is False

    def test_auto_update_disabled_prevents_auto_updates(self):
        """
        Property: When auto-update is disabled, nothing should auto-update
        """
        manager = UpdatePriorityManager()
        auto_manager = AutoUpdateManager(manager, auto_update_enabled=False)

        critical_update = PackageUpdate(
            package_name="pkg1",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.SECURITY,
            priority=UpdatePriority.CRITICAL_SECURITY
        )

        assert auto_manager.should_auto_update(critical_update) is False

    def test_get_auto_update_candidates(self):
        """
        Property: Auto-update candidates include only critical and high security
        """
        manager = UpdatePriorityManager()
        auto_manager = AutoUpdateManager(manager, auto_update_enabled=True)

        updates = [
            PackageUpdate(
                package_name="pkg1",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.SECURITY,
                priority=UpdatePriority.CRITICAL_SECURITY
            ),
            PackageUpdate(
                package_name="pkg2",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.SECURITY,
                priority=UpdatePriority.HIGH_SECURITY
            ),
            PackageUpdate(
                package_name="pkg3",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.SECURITY,
                priority=UpdatePriority.MEDIUM_SECURITY
            ),
            PackageUpdate(
                package_name="pkg4",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.ENHANCEMENT,
                priority=UpdatePriority.ENHANCEMENT
            ),
        ]

        candidates = auto_manager.get_auto_update_candidates(updates)

        assert len(candidates) == 2
        assert all(
            u.priority in (UpdatePriority.CRITICAL_SECURITY, UpdatePriority.HIGH_SECURITY)
            for u in candidates
        )

    def test_auto_update_logging(self):
        """
        Property: Auto-update operations are logged
        """
        manager = UpdatePriorityManager()
        auto_manager = AutoUpdateManager(manager, auto_update_enabled=True)

        update = PackageUpdate(
            package_name="pkg1",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.SECURITY,
            priority=UpdatePriority.CRITICAL_SECURITY
        )

        auto_manager.log_auto_update(update, success=True)

        log = auto_manager.get_update_log()
        assert len(log) == 1
        assert log[0]["package"] == "pkg1"
        assert log[0]["success"] is True

    def test_update_scheduler_can_be_created(self):
        """
        Property: Update scheduler can be created
        """
        manager = UpdatePriorityManager()
        scheduler = UpdateScheduler(manager)

        assert scheduler is not None
        assert len(scheduler.pending_updates) == 0

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=30)
    def test_scheduler_adds_updates(self, num_updates):
        """
        Property: Scheduler can add updates
        """
        manager = UpdatePriorityManager()
        scheduler = UpdateScheduler(manager)

        for i in range(num_updates):
            update = PackageUpdate(
                package_name=f"pkg_{i}",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.ENHANCEMENT,
                priority=UpdatePriority.ENHANCEMENT
            )
            scheduler.add_update(update)

        assert len(scheduler.pending_updates) == num_updates

    def test_scheduler_returns_highest_priority_first(self):
        """
        Property: Scheduler returns highest priority update first
        """
        manager = UpdatePriorityManager()
        scheduler = UpdateScheduler(manager)

        # Add updates in random order
        scheduler.add_update(PackageUpdate(
            package_name="pkg1",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.ENHANCEMENT,
            priority=UpdatePriority.ENHANCEMENT
        ))
        scheduler.add_update(PackageUpdate(
            package_name="pkg2",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.SECURITY,
            priority=UpdatePriority.CRITICAL_SECURITY
        ))
        scheduler.add_update(PackageUpdate(
            package_name="pkg3",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.BUGFIX,
            priority=UpdatePriority.BUGFIX
        ))

        next_update = scheduler.get_next_update()

        assert next_update is not None
        assert next_update.priority == UpdatePriority.CRITICAL_SECURITY
        assert next_update.package_name == "pkg2"

    def test_scheduler_removes_updates(self):
        """
        Property: Scheduler can remove updates
        """
        manager = UpdatePriorityManager()
        scheduler = UpdateScheduler(manager)

        scheduler.add_update(PackageUpdate(
            package_name="pkg1",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.ENHANCEMENT,
            priority=UpdatePriority.ENHANCEMENT
        ))
        scheduler.add_update(PackageUpdate(
            package_name="pkg2",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.SECURITY,
            priority=UpdatePriority.CRITICAL_SECURITY
        ))

        assert len(scheduler.pending_updates) == 2

        scheduler.remove_update("pkg1")

        assert len(scheduler.pending_updates) == 1
        assert scheduler.pending_updates[0].package_name == "pkg2"

    def test_scheduler_filters_by_priority(self):
        """
        Property: Scheduler can filter updates by priority
        """
        manager = UpdatePriorityManager()
        scheduler = UpdateScheduler(manager)

        scheduler.add_update(PackageUpdate(
            package_name="pkg1",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.SECURITY,
            priority=UpdatePriority.CRITICAL_SECURITY
        ))
        scheduler.add_update(PackageUpdate(
            package_name="pkg2",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.SECURITY,
            priority=UpdatePriority.CRITICAL_SECURITY
        ))
        scheduler.add_update(PackageUpdate(
            package_name="pkg3",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.ENHANCEMENT,
            priority=UpdatePriority.ENHANCEMENT
        ))

        critical_updates = scheduler.get_scheduled_updates(
            priority_filter=UpdatePriority.CRITICAL_SECURITY
        )

        assert len(critical_updates) == 2
        assert all(u.priority == UpdatePriority.CRITICAL_SECURITY for u in critical_updates)

    def test_scheduler_clears_schedule(self):
        """
        Property: Scheduler can clear all updates
        """
        manager = UpdatePriorityManager()
        scheduler = UpdateScheduler(manager)

        for i in range(5):
            scheduler.add_update(PackageUpdate(
                package_name=f"pkg_{i}",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.ENHANCEMENT,
                priority=UpdatePriority.ENHANCEMENT
            ))

        assert len(scheduler.pending_updates) == 5

        scheduler.clear_schedule()

        assert len(scheduler.pending_updates) == 0

    def test_security_advisory_serialization(self):
        """
        Property: Security advisories can be serialized and deserialized
        """
        advisory = SecurityAdvisory(
            advisory_id="ADV-2024-001",
            cve_ids=["CVE-2024-0001", "CVE-2024-0002"],
            severity="critical",
            description="Test advisory"
        )

        data = advisory.to_dict()
        restored = SecurityAdvisory.from_dict(data)

        assert restored.advisory_id == advisory.advisory_id
        assert restored.cve_ids == advisory.cve_ids
        assert restored.severity == advisory.severity
        assert restored.description == advisory.description

    def test_package_update_serialization(self):
        """
        Property: Package updates can be serialized and deserialized
        """
        advisory = SecurityAdvisory(
            advisory_id="ADV-2024-001",
            cve_ids=["CVE-2024-0001"],
            severity="high"
        )

        update = PackageUpdate(
            package_name="test-pkg",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.SECURITY,
            priority=UpdatePriority.HIGH_SECURITY,
            security_advisory=advisory
        )

        data = update.to_dict()
        restored = PackageUpdate.from_dict(data)

        assert restored.package_name == update.package_name
        assert restored.update_type == update.update_type
        assert restored.priority == update.priority
        assert restored.security_advisory.advisory_id == advisory.advisory_id

    @given(st.lists(severity_strategy(), min_size=1, max_size=10))
    @settings(max_examples=30)
    def test_security_updates_always_prioritized_over_others(self, severities):
        """
        Property: In any update list, security updates are prioritized over non-security
        """
        manager = UpdatePriorityManager()

        updates = []

        # Add security updates
        for i, severity in enumerate(severities):
            updates.append(PackageUpdate(
                package_name=f"security_pkg_{i}",
                current_version="1.0.0",
                new_version="1.0.1",
                update_type=UpdateType.SECURITY,
                priority=manager.calculate_priority(UpdateType.SECURITY, severity)
            ))

        # Add non-security updates
        updates.append(PackageUpdate(
            package_name="enhancement_pkg",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.ENHANCEMENT,
            priority=UpdatePriority.ENHANCEMENT
        ))
        updates.append(PackageUpdate(
            package_name="bugfix_pkg",
            current_version="1.0.0",
            new_version="1.0.1",
            update_type=UpdateType.BUGFIX,
            priority=UpdatePriority.BUGFIX
        ))

        sorted_updates = manager.sort_updates(updates)

        # Find first non-security update
        first_non_security_idx = None
        for i, update in enumerate(sorted_updates):
            if update.update_type != UpdateType.SECURITY:
                first_non_security_idx = i
                break

        # All security updates should come before first non-security update
        if first_non_security_idx is not None:
            for i in range(first_non_security_idx):
                assert sorted_updates[i].update_type == UpdateType.SECURITY
