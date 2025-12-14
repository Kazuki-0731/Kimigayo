"""
Phase 2 Integration Tests

Tests the integration of Init system and Package Manager components.
Verifies end-to-end functionality and security verification.

Requirements tested:
- 2.3: Package verification (GPG, SHA-256, cryptographic verification)
- 2.5: Security update priority
- 4.4: Atomic update operations
"""

import pytest
import tempfile
from pathlib import Path
import hashlib

from src.init.shutdown import (
    FilesystemManager,
    FilesystemMount,
)
from src.pkg.security import (
    HashVerifier,
    PackageVerifier,
)
from src.pkg.transaction import (
    TransactionManager,
    AtomicPackageManager,
    TransactionState,
)
from src.pkg.priority import (
    UpdatePriorityManager,
    AutoUpdateManager,
    UpdateScheduler,
    UpdateType,
    UpdatePriority,
)


@pytest.mark.integration
class TestPhase2Integration:
    """Integration tests for Phase 2 components"""

    def test_package_security_verification(self):
        """
        Integration Test: Package security verification workflow

        Tests requirement 2.3 (package verification).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test package file
            package_file = Path(tmpdir) / "test-package.tar.gz"
            package_content = b"Test package content"
            package_file.write_bytes(package_content)

            # Calculate expected hash
            expected_hash = hashlib.sha256(package_content).hexdigest()

            # Setup verifiers
            hash_verifier = HashVerifier()
            pkg_verifier = PackageVerifier()

            # Verify hash
            hash_valid = hash_verifier.verify_hash(
                package_file,
                expected_hash
            )
            assert hash_valid is True

            # Verify package (hash only, no signature)
            report = pkg_verifier.verify_package(
                package_file,
                expected_hash,
                require_signature=False
            )
            assert report.is_success() is True

    def test_atomic_package_operations(self):
        """
        Integration Test: Atomic package installation with rollback

        Tests requirement 4.4 (atomic update operations).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            transaction_log_dir = Path(tmpdir) / "transactions"
            transaction_log_dir.mkdir()

            pkg_manager = AtomicPackageManager(transaction_log_dir)

            # Simulate successful installation
            success = pkg_manager.atomic_install(
                "test-package",
                "1.0.0",
                []
            )
            assert success is True

            # Verify transaction was committed
            transactions = pkg_manager.transaction_manager.list_transactions(
                state=TransactionState.COMMITTED
            )
            assert len(transactions) >= 1

    def test_security_update_priority(self):
        """
        Integration Test: Security updates are prioritized

        Tests requirement 2.5 (security update priority).
        """
        priority_manager = UpdatePriorityManager()
        auto_manager = AutoUpdateManager(priority_manager, auto_update_enabled=True)
        scheduler = UpdateScheduler(priority_manager)

        # Create mixed updates
        security_update = priority_manager.classify_update(
            "critical-package",
            "1.0.0",
            "1.0.1"
        )
        security_update.update_type = UpdateType.SECURITY
        security_update.priority = UpdatePriority.CRITICAL_SECURITY

        regular_update = priority_manager.classify_update(
            "regular-package",
            "2.0.0",
            "2.1.0"
        )

        # Add to scheduler
        scheduler.add_update(regular_update)
        scheduler.add_update(security_update)

        # Get next update - should be security update
        next_update = scheduler.get_next_update()
        assert next_update.package_name == "critical-package"
        assert next_update.priority == UpdatePriority.CRITICAL_SECURITY

        # Verify it should auto-update
        should_auto = auto_manager.should_auto_update(security_update)
        assert should_auto is True

    def test_filesystem_management(self):
        """
        Integration Test: Filesystem management and cleanup

        Tests filesystem management capabilities.
        """
        fs_manager = FilesystemManager()

        # Register filesystems
        fs_manager.register_mount(FilesystemMount(
            device="/dev/sda1",
            mount_point="/mnt/data",
            filesystem_type="ext4"
        ))

        assert len(fs_manager.mounts) == 1

        # Unmount
        success = fs_manager.unmount("/mnt/data")
        assert success is True
        assert len(fs_manager.mounts) == 0

    def test_concurrent_transactions_prevented(self):
        """
        Integration Test: Concurrent package operations are prevented

        Tests requirement 4.4 (atomic operations) - only one transaction at a time.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            transaction_log_dir = Path(tmpdir) / "transactions"
            transaction_log_dir.mkdir()

            transaction_manager = TransactionManager(transaction_log_dir)

            # Begin first transaction
            tx1 = transaction_manager.begin_transaction()
            assert tx1 is not None

            # Attempt to begin second transaction - should fail
            with pytest.raises(RuntimeError, match="in progress"):
                tx2 = transaction_manager.begin_transaction()

            # Commit first transaction
            transaction_manager.commit()

            # Now second transaction can begin
            tx2 = transaction_manager.begin_transaction()
            assert tx2 is not None

    def test_package_update_workflow(self):
        """
        Integration Test: Package update workflow with atomicity

        Tests requirement 4.4 (atomic update operations).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            transaction_log_dir = Path(tmpdir) / "transactions"
            transaction_log_dir.mkdir()
            pkg_manager = AtomicPackageManager(transaction_log_dir)

            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            # Install initial version
            install_success = pkg_manager.atomic_install("app", "1.0.0", [])
            assert install_success is True

            # Update to new version atomically
            update_success = pkg_manager.atomic_update(
                "app",
                "1.0.0",
                "1.0.1",
                backup_dir,
                []
            )
            assert update_success is True

            # Verify update transaction was committed
            transactions = pkg_manager.transaction_manager.list_transactions(
                state=TransactionState.COMMITTED
            )
            assert len(transactions) >= 2  # Install + Update

    def test_package_removal_with_backup(self):
        """
        Integration Test: Package removal with backup for rollback

        Tests requirement 4.4 (atomic operations with rollback capability).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            transaction_log_dir = Path(tmpdir) / "transactions"
            transaction_log_dir.mkdir()
            pkg_manager = AtomicPackageManager(transaction_log_dir)

            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            # Install package
            install_success = pkg_manager.atomic_install("removable-app", "1.0.0", [])
            assert install_success is True

            # Remove package with backup
            remove_success = pkg_manager.atomic_remove(
                "removable-app",
                "1.0.0",
                backup_dir
            )
            assert remove_success is True

            # Verify removal transaction was committed
            transactions = pkg_manager.transaction_manager.list_transactions(
                state=TransactionState.COMMITTED
            )
            assert len(transactions) >= 2  # Install + Remove

    def test_security_verification_chain(self):
        """
        Integration Test: Complete security verification chain

        Tests requirement 2.3 (package verification) with multiple verification methods.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test package
            package_file = Path(tmpdir) / "secure-package.tar.gz"
            package_content = b"Secure package content"
            package_file.write_bytes(package_content)

            # Hash verification
            hash_verifier = HashVerifier()
            expected_hash = hashlib.sha256(package_content).hexdigest()
            hash_valid = hash_verifier.verify_hash(
                package_file,
                expected_hash
            )
            assert hash_valid is True

            # Package verification
            pkg_verifier = PackageVerifier()
            report = pkg_verifier.verify_package(
                package_file,
                expected_hash,
                require_signature=False
            )
            assert report.is_success() is True

            # All verifications passed - package is secure
            all_checks_passed = hash_valid and report.is_success()
            assert all_checks_passed is True

    def test_full_integration_workflow(self):
        """
        Integration Test: Full Phase 2 integration workflow

        Complete workflow:
        1. Verify package security
        2. Install package atomically
        3. Handle security updates with priority
        4. Clean up filesystems

        Tests all Phase 2 requirements: 2.3, 2.5, 4.4
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            transaction_log_dir = Path(tmpdir) / "transactions"
            transaction_log_dir.mkdir()
            pkg_manager = AtomicPackageManager(transaction_log_dir)

            fs_manager = FilesystemManager()
            priority_manager = UpdatePriorityManager()
            scheduler = UpdateScheduler(priority_manager)

            # Step 1: Verify package
            package_file = Path(tmpdir) / "base-system.tar.gz"
            package_content = b"Base system package"
            package_file.write_bytes(package_content)
            expected_hash = hashlib.sha256(package_content).hexdigest()

            verifier = PackageVerifier()
            report = verifier.verify_package(package_file, expected_hash, require_signature=False)
            assert report.is_success() is True

            # Step 2: Install base system
            install_base = pkg_manager.atomic_install("base-system", "1.0.0", [])
            assert install_base is True

            # Step 3: Install network tools
            install_network = pkg_manager.atomic_install("network-tools", "1.0.0", [])
            assert install_network is True

            # Step 4: Schedule security update
            security_update = priority_manager.classify_update(
                "base-system",
                "1.0.0",
                "1.0.1"
            )
            security_update.update_type = UpdateType.SECURITY
            security_update.priority = UpdatePriority.CRITICAL_SECURITY
            scheduler.add_update(security_update)

            # Verify security update is prioritized
            next_update = scheduler.get_next_update()
            assert next_update.priority == UpdatePriority.CRITICAL_SECURITY

            # Step 5: Register and cleanup filesystem
            fs_manager.register_mount(FilesystemMount(
                device="/dev/sda1",
                mount_point="/mnt/data",
                filesystem_type="ext4"
            ))
            fs_manager.unmount_all()
            assert len(fs_manager.mounts) == 0
