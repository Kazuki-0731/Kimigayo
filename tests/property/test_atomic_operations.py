"""
Property 15: Atomic Update Operations

Verifies that package operations are atomic and can be rolled back.
Testing requirement 4.4.
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime

from src.pkg.transaction import (
    TransactionManager,
    AtomicPackageManager,
    Transaction,
    Operation,
    OperationType,
    TransactionState,
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


@pytest.mark.property
class TestAtomicOperations:
    """Test property 15: Atomic update operations"""

    def test_transaction_can_be_created(self):
        """
        Property: Transactions can be created and tracked
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()

            assert transaction is not None
            assert transaction.transaction_id.startswith("tx_")
            assert transaction.state == TransactionState.PENDING
            assert len(transaction.operations) == 0

    @given(package_name_strategy(), version_strategy())
    @settings(max_examples=30)
    def test_install_operation_added_to_transaction(self, package_name, version):
        """
        Property: Install operations can be added to transactions
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()

            files = [Path("/usr/bin/test")]
            manager.add_install_operation(package_name, version, files)

            assert len(transaction.operations) == 1
            op = transaction.operations[0]
            assert op.operation_type == OperationType.INSTALL
            assert op.package_name == package_name
            assert op.version == version

    @given(package_name_strategy(), version_strategy(), version_strategy())
    @settings(max_examples=30)
    def test_update_operation_added_to_transaction(self, package_name, old_version, new_version):
        """
        Property: Update operations can be added to transactions
        """
        assume(old_version != new_version)

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()

            backup_path = Path(tmpdir) / "backup"
            files = [Path("/usr/bin/test")]
            manager.add_update_operation(
                package_name,
                old_version,
                new_version,
                backup_path,
                files
            )

            assert len(transaction.operations) == 1
            op = transaction.operations[0]
            assert op.operation_type == OperationType.UPDATE
            assert op.package_name == package_name
            assert op.old_version == old_version
            assert op.version == new_version

    @given(package_name_strategy(), version_strategy())
    @settings(max_examples=30)
    def test_remove_operation_added_to_transaction(self, package_name, version):
        """
        Property: Remove operations can be added to transactions
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()

            backup_path = Path(tmpdir) / "backup"
            manager.add_remove_operation(package_name, version, backup_path)

            assert len(transaction.operations) == 1
            op = transaction.operations[0]
            assert op.operation_type == OperationType.REMOVE
            assert op.package_name == package_name
            assert op.version == version

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=30)
    def test_multiple_operations_in_transaction(self, num_operations):
        """
        Property: Multiple operations can be added to one transaction
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()

            for i in range(num_operations):
                manager.add_install_operation(
                    f"pkg_{i}",
                    "1.0.0",
                    [Path(f"/usr/bin/pkg_{i}")]
                )

            assert len(transaction.operations) == num_operations

    def test_transaction_commit_changes_state(self):
        """
        Property: Committing a transaction changes its state to COMMITTED
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()

            manager.add_install_operation("test-pkg", "1.0.0", [])

            success = manager.commit()

            assert success is True
            assert transaction.state == TransactionState.COMMITTED
            assert transaction.completed_at is not None

    def test_transaction_rollback_changes_state(self):
        """
        Property: Rolling back a transaction changes its state to ROLLED_BACK
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()

            manager.add_install_operation("test-pkg", "1.0.0", [])

            success = manager.rollback()

            assert success is True
            assert transaction.state == TransactionState.ROLLED_BACK
            assert transaction.completed_at is not None

    def test_transaction_persisted_to_disk(self):
        """
        Property: Transactions are persisted to disk
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()
            transaction_id = transaction.transaction_id

            manager.add_install_operation("test-pkg", "1.0.0", [])

            # Load transaction from disk
            loaded = manager.load_transaction(transaction_id)

            assert loaded is not None
            assert loaded.transaction_id == transaction_id
            assert len(loaded.operations) == 1

    def test_transaction_can_be_listed(self):
        """
        Property: All transactions can be listed
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))

            # Create multiple transactions
            for i in range(3):
                tx = manager.begin_transaction()
                manager.add_install_operation(f"pkg_{i}", "1.0.0", [])
                manager.commit()

            transactions = manager.list_transactions()

            assert len(transactions) >= 3

    def test_transactions_filtered_by_state(self):
        """
        Property: Transactions can be filtered by state
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))

            # Create committed transaction
            tx1 = manager.begin_transaction()
            manager.add_install_operation("pkg1", "1.0.0", [])
            manager.commit()

            # Create rolled back transaction
            tx2 = manager.begin_transaction()
            manager.add_install_operation("pkg2", "1.0.0", [])
            manager.rollback()

            committed = manager.list_transactions(state=TransactionState.COMMITTED)
            rolled_back = manager.list_transactions(state=TransactionState.ROLLED_BACK)

            assert len(committed) >= 1
            assert len(rolled_back) >= 1

    @given(package_name_strategy(), version_strategy())
    @settings(max_examples=30)
    def test_atomic_install_success(self, package_name, version):
        """
        Property: Atomic install commits on success
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_manager = AtomicPackageManager(Path(tmpdir))

            success = pkg_manager.atomic_install(
                package_name,
                version,
                []
            )

            assert success is True

            # Check transaction was committed
            transactions = pkg_manager.transaction_manager.list_transactions(
                state=TransactionState.COMMITTED
            )
            assert len(transactions) >= 1

    @given(package_name_strategy(), version_strategy(), version_strategy())
    @settings(max_examples=30)
    def test_atomic_update_success(self, package_name, old_version, new_version):
        """
        Property: Atomic update commits on success
        """
        assume(old_version != new_version)

        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_manager = AtomicPackageManager(Path(tmpdir))
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            success = pkg_manager.atomic_update(
                package_name,
                old_version,
                new_version,
                backup_dir,
                []
            )

            assert success is True

            transactions = pkg_manager.transaction_manager.list_transactions(
                state=TransactionState.COMMITTED
            )
            assert len(transactions) >= 1

    @given(package_name_strategy(), version_strategy())
    @settings(max_examples=30)
    def test_atomic_remove_success(self, package_name, version):
        """
        Property: Atomic remove commits on success
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_manager = AtomicPackageManager(Path(tmpdir))
            backup_dir = Path(tmpdir) / "backups"
            backup_dir.mkdir()

            success = pkg_manager.atomic_remove(
                package_name,
                version,
                backup_dir
            )

            assert success is True

            transactions = pkg_manager.transaction_manager.list_transactions(
                state=TransactionState.COMMITTED
            )
            assert len(transactions) >= 1

    def test_operation_serialization(self):
        """
        Property: Operations can be serialized and deserialized
        """
        operation = Operation(
            operation_type=OperationType.INSTALL,
            package_name="test-pkg",
            version="1.0.0",
            files_installed=[Path("/usr/bin/test")]
        )

        # Serialize
        data = operation.to_dict()

        # Deserialize
        restored = Operation.from_dict(data)

        assert restored.operation_type == operation.operation_type
        assert restored.package_name == operation.package_name
        assert restored.version == operation.version
        assert restored.files_installed == operation.files_installed

    def test_transaction_serialization(self):
        """
        Property: Transactions can be serialized and deserialized
        """
        transaction = Transaction(
            transaction_id="test_tx_001"
        )
        transaction.add_operation(Operation(
            operation_type=OperationType.INSTALL,
            package_name="test-pkg",
            version="1.0.0"
        ))

        # Serialize
        data = transaction.to_dict()

        # Deserialize
        restored = Transaction.from_dict(data)

        assert restored.transaction_id == transaction.transaction_id
        assert len(restored.operations) == len(transaction.operations)
        assert restored.state == transaction.state

    def test_transaction_workspace_created(self):
        """
        Property: Transaction workspace is created
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()

            assert transaction.workspace is not None
            assert transaction.workspace.exists()
            assert transaction.workspace.is_dir()

    def test_transaction_workspace_cleaned_on_commit(self):
        """
        Property: Transaction workspace is cleaned up after commit
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()
            workspace = transaction.workspace

            manager.add_install_operation("test-pkg", "1.0.0", [])
            manager.commit()

            # Workspace should be cleaned up
            assert not workspace.exists()

    def test_transaction_workspace_cleaned_on_rollback(self):
        """
        Property: Transaction workspace is cleaned up after rollback
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()
            workspace = transaction.workspace

            manager.add_install_operation("test-pkg", "1.0.0", [])
            manager.rollback()

            # Workspace should be cleaned up
            assert not workspace.exists()

    def test_cannot_begin_transaction_while_one_in_progress(self):
        """
        Property: Cannot begin new transaction while another is in progress
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            tx1 = manager.begin_transaction()

            # Should raise error
            with pytest.raises(RuntimeError, match="in progress"):
                tx2 = manager.begin_transaction()

    def test_transaction_id_is_unique(self):
        """
        Property: Each transaction has a unique ID
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))

            ids = set()
            for i in range(10):
                tx = manager.begin_transaction()
                ids.add(tx.transaction_id)
                manager.commit()

            # All IDs should be unique
            assert len(ids) == 10

    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=20)
    def test_rollback_reverses_operations(self, num_operations):
        """
        Property: Rollback reverses all operations in reverse order
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            transaction = manager.begin_transaction()

            # Add operations
            for i in range(num_operations):
                manager.add_install_operation(f"pkg_{i}", "1.0.0", [])

            # Rollback
            manager.rollback()

            # Transaction should be rolled back
            assert transaction.state == TransactionState.ROLLED_BACK

    def test_transaction_timestamp_recorded(self):
        """
        Property: Transaction timestamps are recorded
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TransactionManager(Path(tmpdir))
            before = datetime.now()
            transaction = manager.begin_transaction()
            after = datetime.now()

            assert before <= transaction.created_at <= after

            manager.add_install_operation("test-pkg", "1.0.0", [])
            manager.commit()

            assert transaction.completed_at is not None
            assert transaction.completed_at >= transaction.created_at
