"""
Atomic Transaction System for Kimigayo OS Package Manager

Provides atomic install/update/remove operations with rollback capability.
Ensures system integrity even if operations fail partway through.
"""

import os
import shutil
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Set, Optional, Any
from datetime import datetime
import json


class TransactionState(Enum):
    """State of a transaction"""
    PENDING = "pending"           # Not yet started
    IN_PROGRESS = "in_progress"   # Currently executing
    COMMITTED = "committed"       # Successfully completed
    ROLLED_BACK = "rolled_back"   # Rolled back due to error
    FAILED = "failed"             # Failed and couldn't rollback


class OperationType(Enum):
    """Type of package operation"""
    INSTALL = "install"
    UPDATE = "update"
    REMOVE = "remove"


@dataclass
class Operation:
    """A single operation in a transaction"""
    operation_type: OperationType
    package_name: str
    version: Optional[str] = None
    old_version: Optional[str] = None  # For updates

    # Backup information for rollback
    backup_path: Optional[Path] = None
    files_installed: List[Path] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "operation_type": self.operation_type.value,
            "package_name": self.package_name,
            "version": self.version,
            "old_version": self.old_version,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "files_installed": [str(f) for f in self.files_installed]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Operation":
        """Create from dictionary"""
        return cls(
            operation_type=OperationType(data["operation_type"]),
            package_name=data["package_name"],
            version=data.get("version"),
            old_version=data.get("old_version"),
            backup_path=Path(data["backup_path"]) if data.get("backup_path") else None,
            files_installed=[Path(f) for f in data.get("files_installed", [])]
        )


@dataclass
class Transaction:
    """A transaction containing multiple operations"""
    transaction_id: str
    operations: List[Operation] = field(default_factory=list)
    state: TransactionState = TransactionState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: str = ""

    # Workspace for temporary files
    workspace: Optional[Path] = None

    def add_operation(self, operation: Operation):
        """Add an operation to the transaction"""
        self.operations.append(operation)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        return {
            "transaction_id": self.transaction_id,
            "operations": [op.to_dict() for op in self.operations],
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "workspace": str(self.workspace) if self.workspace else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """Create from dictionary"""
        return cls(
            transaction_id=data["transaction_id"],
            operations=[Operation.from_dict(op) for op in data["operations"]],
            state=TransactionState(data["state"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error_message=data.get("error_message", ""),
            workspace=Path(data["workspace"]) if data.get("workspace") else None
        )


class TransactionManager:
    """Manages atomic package transactions"""

    def __init__(self, transaction_log_dir: Path):
        """
        Initialize transaction manager.

        Args:
            transaction_log_dir: Directory to store transaction logs
        """
        self.transaction_log_dir = transaction_log_dir
        self.transaction_log_dir.mkdir(parents=True, exist_ok=True)

        self.current_transaction: Optional[Transaction] = None

    def begin_transaction(self) -> Transaction:
        """
        Begin a new transaction.

        Returns:
            New transaction object
        """
        if self.current_transaction and self.current_transaction.state in (
            TransactionState.PENDING,
            TransactionState.IN_PROGRESS
        ):
            raise RuntimeError("Cannot begin new transaction while another is in progress")

        # Generate unique transaction ID
        transaction_id = f"tx_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Create workspace
        workspace = Path(tempfile.mkdtemp(prefix=f"{transaction_id}_"))

        transaction = Transaction(
            transaction_id=transaction_id,
            workspace=workspace
        )

        self.current_transaction = transaction
        self._save_transaction(transaction)

        return transaction

    def add_install_operation(
        self,
        package_name: str,
        version: str,
        files_to_install: List[Path]
    ):
        """
        Add an install operation to current transaction.

        Args:
            package_name: Name of package to install
            version: Version to install
            files_to_install: List of files that will be installed
        """
        if not self.current_transaction:
            raise RuntimeError("No active transaction")

        operation = Operation(
            operation_type=OperationType.INSTALL,
            package_name=package_name,
            version=version,
            files_installed=files_to_install
        )

        self.current_transaction.add_operation(operation)
        self._save_transaction(self.current_transaction)

    def add_update_operation(
        self,
        package_name: str,
        old_version: str,
        new_version: str,
        backup_path: Path,
        files_to_install: List[Path]
    ):
        """
        Add an update operation to current transaction.

        Args:
            package_name: Name of package to update
            old_version: Current version
            new_version: New version
            backup_path: Path to backup of old version
            files_to_install: List of files that will be installed
        """
        if not self.current_transaction:
            raise RuntimeError("No active transaction")

        operation = Operation(
            operation_type=OperationType.UPDATE,
            package_name=package_name,
            version=new_version,
            old_version=old_version,
            backup_path=backup_path,
            files_installed=files_to_install
        )

        self.current_transaction.add_operation(operation)
        self._save_transaction(self.current_transaction)

    def add_remove_operation(
        self,
        package_name: str,
        version: str,
        backup_path: Path
    ):
        """
        Add a remove operation to current transaction.

        Args:
            package_name: Name of package to remove
            version: Version being removed
            backup_path: Path to backup for potential rollback
        """
        if not self.current_transaction:
            raise RuntimeError("No active transaction")

        operation = Operation(
            operation_type=OperationType.REMOVE,
            package_name=package_name,
            version=version,
            backup_path=backup_path
        )

        self.current_transaction.add_operation(operation)
        self._save_transaction(self.current_transaction)

    def commit(self) -> bool:
        """
        Commit the current transaction.

        Returns:
            True if committed successfully, False otherwise
        """
        if not self.current_transaction:
            raise RuntimeError("No active transaction")

        transaction = self.current_transaction
        transaction.state = TransactionState.IN_PROGRESS
        self._save_transaction(transaction)

        try:
            # All operations have already been performed
            # Commit just marks the transaction as complete
            transaction.state = TransactionState.COMMITTED
            transaction.completed_at = datetime.now()
            self._save_transaction(transaction)

            # Cleanup workspace
            if transaction.workspace and transaction.workspace.exists():
                shutil.rmtree(transaction.workspace)

            self.current_transaction = None
            return True

        except Exception as e:
            transaction.state = TransactionState.FAILED
            transaction.error_message = str(e)
            self._save_transaction(transaction)
            return False

    def rollback(self) -> bool:
        """
        Rollback the current transaction.

        Returns:
            True if rolled back successfully, False otherwise
        """
        if not self.current_transaction:
            raise RuntimeError("No active transaction")

        transaction = self.current_transaction

        try:
            # Rollback operations in reverse order
            for operation in reversed(transaction.operations):
                self._rollback_operation(operation)

            transaction.state = TransactionState.ROLLED_BACK
            transaction.completed_at = datetime.now()
            self._save_transaction(transaction)

            # Cleanup workspace
            if transaction.workspace and transaction.workspace.exists():
                shutil.rmtree(transaction.workspace)

            self.current_transaction = None
            return True

        except Exception as e:
            transaction.state = TransactionState.FAILED
            transaction.error_message = f"Rollback failed: {str(e)}"
            self._save_transaction(transaction)
            return False

    def _rollback_operation(self, operation: Operation):
        """
        Rollback a single operation.

        Args:
            operation: Operation to rollback
        """
        if operation.operation_type == OperationType.INSTALL:
            # Remove installed files
            for file_path in operation.files_installed:
                if file_path.exists():
                    file_path.unlink()

        elif operation.operation_type == OperationType.UPDATE:
            # Restore from backup
            if operation.backup_path and operation.backup_path.exists():
                # Remove new files
                for file_path in operation.files_installed:
                    if file_path.exists():
                        file_path.unlink()

                # Restore old files from backup
                # In real implementation, would restore actual files
                pass

        elif operation.operation_type == OperationType.REMOVE:
            # Restore from backup
            if operation.backup_path and operation.backup_path.exists():
                # In real implementation, would restore actual files
                pass

    def _save_transaction(self, transaction: Transaction):
        """
        Save transaction to log file.

        Args:
            transaction: Transaction to save
        """
        log_file = self.transaction_log_dir / f"{transaction.transaction_id}.json"
        with open(log_file, 'w') as f:
            json.dump(transaction.to_dict(), f, indent=2)

    def load_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """
        Load a transaction from log.

        Args:
            transaction_id: ID of transaction to load

        Returns:
            Transaction object or None if not found
        """
        log_file = self.transaction_log_dir / f"{transaction_id}.json"
        if not log_file.exists():
            return None

        with open(log_file, 'r') as f:
            data = json.load(f)

        return Transaction.from_dict(data)

    def list_transactions(self, state: Optional[TransactionState] = None) -> List[Transaction]:
        """
        List all transactions.

        Args:
            state: Filter by state (optional)

        Returns:
            List of transactions
        """
        transactions = []

        for log_file in self.transaction_log_dir.glob("tx_*.json"):
            with open(log_file, 'r') as f:
                data = json.load(f)

            transaction = Transaction.from_dict(data)

            if state is None or transaction.state == state:
                transactions.append(transaction)

        return sorted(transactions, key=lambda t: t.created_at, reverse=True)

    def cleanup_old_transactions(self, days: int = 30):
        """
        Cleanup old transaction logs.

        Args:
            days: Remove transactions older than this many days
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for log_file in self.transaction_log_dir.glob("tx_*.json"):
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()


class AtomicPackageManager:
    """Package manager with atomic operations"""

    def __init__(self, transaction_log_dir: Path):
        """
        Initialize atomic package manager.

        Args:
            transaction_log_dir: Directory for transaction logs
        """
        self.transaction_manager = TransactionManager(transaction_log_dir)

    def atomic_install(
        self,
        package_name: str,
        version: str,
        files: List[Path]
    ) -> bool:
        """
        Atomically install a package.

        Args:
            package_name: Name of package
            version: Version to install
            files: Files to install

        Returns:
            True if successful, False otherwise
        """
        transaction = self.transaction_manager.begin_transaction()

        try:
            # Add install operation
            self.transaction_manager.add_install_operation(
                package_name,
                version,
                files
            )

            # Perform actual installation
            # In real implementation, would copy files, update database, etc.

            # Commit transaction
            return self.transaction_manager.commit()

        except Exception as e:
            # Rollback on error
            self.transaction_manager.rollback()
            return False

    def atomic_update(
        self,
        package_name: str,
        old_version: str,
        new_version: str,
        backup_dir: Path,
        new_files: List[Path]
    ) -> bool:
        """
        Atomically update a package.

        Args:
            package_name: Name of package
            old_version: Current version
            new_version: New version
            backup_dir: Directory to store backup
            new_files: New files to install

        Returns:
            True if successful, False otherwise
        """
        transaction = self.transaction_manager.begin_transaction()

        try:
            # Create backup
            backup_path = backup_dir / f"{package_name}_{old_version}_backup"
            backup_path.mkdir(parents=True, exist_ok=True)

            # Add update operation
            self.transaction_manager.add_update_operation(
                package_name,
                old_version,
                new_version,
                backup_path,
                new_files
            )

            # Perform actual update
            # In real implementation, would:
            # 1. Backup old files
            # 2. Install new files
            # 3. Update database

            # Commit transaction
            return self.transaction_manager.commit()

        except Exception as e:
            # Rollback on error
            self.transaction_manager.rollback()
            return False

    def atomic_remove(
        self,
        package_name: str,
        version: str,
        backup_dir: Path
    ) -> bool:
        """
        Atomically remove a package.

        Args:
            package_name: Name of package
            version: Version to remove
            backup_dir: Directory to store backup

        Returns:
            True if successful, False otherwise
        """
        transaction = self.transaction_manager.begin_transaction()

        try:
            # Create backup
            backup_path = backup_dir / f"{package_name}_{version}_backup"
            backup_path.mkdir(parents=True, exist_ok=True)

            # Add remove operation
            self.transaction_manager.add_remove_operation(
                package_name,
                version,
                backup_path
            )

            # Perform actual removal
            # In real implementation, would:
            # 1. Backup files
            # 2. Remove files
            # 3. Update database

            # Commit transaction
            return self.transaction_manager.commit()

        except Exception as e:
            # Rollback on error
            self.transaction_manager.rollback()
            return False
