"""
Package Database for Kimigayo OS Package Manager

Provides SQLite-based package database with CRUD operations.
"""

import sqlite3
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Any, Tuple
from datetime import datetime
import json


class PackageStatus(Enum):
    """Package installation status"""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    PENDING_INSTALL = "pending_install"
    PENDING_REMOVE = "pending_remove"
    BROKEN = "broken"


@dataclass
class PackageMetadata:
    """Metadata for a package"""
    name: str
    version: str
    architecture: str

    # Dependencies
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)

    # Package info
    description: str = ""
    size: int = 0  # Size in bytes
    installed_size: int = 0  # Size after installation

    # Security
    checksum_sha256: str = ""
    gpg_signature: Optional[str] = None

    # Build info
    build_timestamp: Optional[str] = None
    build_hash: Optional[str] = None

    # Installation info
    status: PackageStatus = PackageStatus.NOT_INSTALLED
    install_timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageMetadata":
        """Create from dictionary"""
        # Convert status string to enum
        if "status" in data and isinstance(data["status"], str):
            data["status"] = PackageStatus(data["status"])
        return cls(**data)


@dataclass
class DependencyConstraint:
    """Dependency constraint specification"""
    package_name: str
    operator: str = ""  # "", ">=", "<=", "=", ">", "<"
    version: str = ""

    @classmethod
    def parse(cls, constraint_str: str) -> "DependencyConstraint":
        """
        Parse dependency constraint string.

        Examples:
            - "package" -> DependencyConstraint("package", "", "")
            - "package>=1.0" -> DependencyConstraint("package", ">=", "1.0")
            - "package=2.0.0" -> DependencyConstraint("package", "=", "2.0.0")
        """
        constraint_str = constraint_str.strip()
        operators = [">=", "<=", "=", ">", "<"]

        for op in operators:
            if op in constraint_str:
                parts = constraint_str.split(op, 1)  # Split only once
                if len(parts) == 2:
                    return cls(
                        package_name=parts[0].strip(),
                        operator=op,
                        version=parts[1].strip()
                    )

        # No operator found
        return cls(package_name=constraint_str)

    def to_string(self) -> str:
        """Convert to string representation"""
        if self.operator and self.version:
            return f"{self.package_name}{self.operator}{self.version}"
        return self.package_name

    def is_satisfied_by(self, version: str) -> bool:
        """
        Check if a version satisfies this constraint.

        Simple string comparison for now.
        In production, would use proper semantic versioning.
        """
        if not self.operator:
            return True  # Any version satisfies

        if self.operator == "=":
            return version == self.version
        elif self.operator == ">=":
            return version >= self.version
        elif self.operator == "<=":
            return version <= self.version
        elif self.operator == ">":
            return version > self.version
        elif self.operator == "<":
            return version < self.version

        return False


class PackageDatabase:
    """SQLite-based package database"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self):
        """Connect to database"""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def _init_schema(self):
        """Initialize database schema"""
        cursor = self.connection.cursor()

        # Packages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS packages (
                name TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                architecture TEXT NOT NULL,
                description TEXT,
                size INTEGER,
                installed_size INTEGER,
                checksum_sha256 TEXT,
                gpg_signature TEXT,
                build_timestamp TEXT,
                build_hash TEXT,
                status TEXT NOT NULL,
                install_timestamp TEXT
            )
        """)

        # Dependencies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dependencies (
                package_name TEXT NOT NULL,
                dependency TEXT NOT NULL,
                FOREIGN KEY (package_name) REFERENCES packages(name),
                PRIMARY KEY (package_name, dependency)
            )
        """)

        # Conflicts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conflicts (
                package_name TEXT NOT NULL,
                conflict TEXT NOT NULL,
                FOREIGN KEY (package_name) REFERENCES packages(name),
                PRIMARY KEY (package_name, conflict)
            )
        """)

        # Provides table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS provides (
                package_name TEXT NOT NULL,
                virtual_package TEXT NOT NULL,
                FOREIGN KEY (package_name) REFERENCES packages(name),
                PRIMARY KEY (package_name, virtual_package)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_package_status ON packages(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dependencies ON dependencies(dependency)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_provides ON provides(virtual_package)")

        self.connection.commit()

    def add_package(self, pkg: PackageMetadata) -> bool:
        """
        Add a package to the database.

        Returns:
            True if added successfully, False if already exists
        """
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()

        try:
            # Insert package
            cursor.execute("""
                INSERT INTO packages (
                    name, version, architecture, description, size, installed_size,
                    checksum_sha256, gpg_signature, build_timestamp, build_hash,
                    status, install_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pkg.name, pkg.version, pkg.architecture, pkg.description,
                pkg.size, pkg.installed_size, pkg.checksum_sha256, pkg.gpg_signature,
                pkg.build_timestamp, pkg.build_hash, pkg.status.value, pkg.install_timestamp
            ))

            # Insert dependencies
            for dep in pkg.dependencies:
                cursor.execute(
                    "INSERT INTO dependencies (package_name, dependency) VALUES (?, ?)",
                    (pkg.name, dep)
                )

            # Insert conflicts
            for conflict in pkg.conflicts:
                cursor.execute(
                    "INSERT INTO conflicts (package_name, conflict) VALUES (?, ?)",
                    (pkg.name, conflict)
                )

            # Insert provides
            for virtual in pkg.provides:
                cursor.execute(
                    "INSERT INTO provides (package_name, virtual_package) VALUES (?, ?)",
                    (pkg.name, virtual)
                )

            self.connection.commit()
            return True

        except sqlite3.IntegrityError:
            return False

    def get_package(self, name: str) -> Optional[PackageMetadata]:
        """Get package by name"""
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()

        # Get package info
        cursor.execute("SELECT * FROM packages WHERE name = ?", (name,))
        row = cursor.fetchone()

        if not row:
            return None

        # Get dependencies
        cursor.execute("SELECT dependency FROM dependencies WHERE package_name = ?", (name,))
        dependencies = [r[0] for r in cursor.fetchall()]

        # Get conflicts
        cursor.execute("SELECT conflict FROM conflicts WHERE package_name = ?", (name,))
        conflicts = [r[0] for r in cursor.fetchall()]

        # Get provides
        cursor.execute("SELECT virtual_package FROM provides WHERE package_name = ?", (name,))
        provides = [r[0] for r in cursor.fetchall()]

        # Create metadata object
        return PackageMetadata(
            name=row["name"],
            version=row["version"],
            architecture=row["architecture"],
            description=row["description"] or "",
            size=row["size"] or 0,
            installed_size=row["installed_size"] or 0,
            checksum_sha256=row["checksum_sha256"] or "",
            gpg_signature=row["gpg_signature"],
            build_timestamp=row["build_timestamp"],
            build_hash=row["build_hash"],
            status=PackageStatus(row["status"]),
            install_timestamp=row["install_timestamp"],
            dependencies=dependencies,
            conflicts=conflicts,
            provides=provides
        )

    def update_package(self, pkg: PackageMetadata) -> bool:
        """Update existing package"""
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()

        try:
            # Update package
            cursor.execute("""
                UPDATE packages SET
                    version = ?, architecture = ?, description = ?, size = ?,
                    installed_size = ?, checksum_sha256 = ?, gpg_signature = ?,
                    build_timestamp = ?, build_hash = ?, status = ?, install_timestamp = ?
                WHERE name = ?
            """, (
                pkg.version, pkg.architecture, pkg.description, pkg.size,
                pkg.installed_size, pkg.checksum_sha256, pkg.gpg_signature,
                pkg.build_timestamp, pkg.build_hash, pkg.status.value,
                pkg.install_timestamp, pkg.name
            ))

            if cursor.rowcount == 0:
                return False

            # Update dependencies
            cursor.execute("DELETE FROM dependencies WHERE package_name = ?", (pkg.name,))
            for dep in pkg.dependencies:
                cursor.execute(
                    "INSERT INTO dependencies (package_name, dependency) VALUES (?, ?)",
                    (pkg.name, dep)
                )

            # Update conflicts
            cursor.execute("DELETE FROM conflicts WHERE package_name = ?", (pkg.name,))
            for conflict in pkg.conflicts:
                cursor.execute(
                    "INSERT INTO conflicts (package_name, conflict) VALUES (?, ?)",
                    (pkg.name, conflict)
                )

            # Update provides
            cursor.execute("DELETE FROM provides WHERE package_name = ?", (pkg.name,))
            for virtual in pkg.provides:
                cursor.execute(
                    "INSERT INTO provides (package_name, virtual_package) VALUES (?, ?)",
                    (pkg.name, virtual)
                )

            self.connection.commit()
            return True

        except sqlite3.Error:
            return False

    def delete_package(self, name: str) -> bool:
        """Delete package from database"""
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()

        # Delete related records first (foreign key constraints)
        cursor.execute("DELETE FROM dependencies WHERE package_name = ?", (name,))
        cursor.execute("DELETE FROM conflicts WHERE package_name = ?", (name,))
        cursor.execute("DELETE FROM provides WHERE package_name = ?", (name,))

        # Delete package
        cursor.execute("DELETE FROM packages WHERE name = ?", (name,))

        success = cursor.rowcount > 0
        self.connection.commit()
        return success

    def list_packages(
        self,
        status: Optional[PackageStatus] = None,
        architecture: Optional[str] = None
    ) -> List[PackageMetadata]:
        """List packages with optional filters"""
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()

        query = "SELECT name FROM packages WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if architecture:
            query += " AND architecture = ?"
            params.append(architecture)

        cursor.execute(query, params)

        packages = []
        for row in cursor.fetchall():
            pkg = self.get_package(row[0])
            if pkg:
                packages.append(pkg)

        return packages

    def search_packages(self, query: str) -> List[PackageMetadata]:
        """Search packages by name or description"""
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT name FROM packages
            WHERE name LIKE ? OR description LIKE ?
        """, (f"%{query}%", f"%{query}%"))

        packages = []
        for row in cursor.fetchall():
            pkg = self.get_package(row[0])
            if pkg:
                packages.append(pkg)

        return packages

    def get_providers(self, virtual_package: str) -> List[str]:
        """Get packages that provide a virtual package"""
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT package_name FROM provides WHERE virtual_package = ?",
            (virtual_package,)
        )

        return [row[0] for row in cursor.fetchall()]

    def get_dependents(self, package_name: str) -> List[str]:
        """Get packages that depend on this package"""
        if not self.connection:
            raise RuntimeError("Database not connected")

        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT package_name FROM dependencies WHERE dependency LIKE ?",
            (f"{package_name}%",)
        )

        return [row[0] for row in cursor.fetchall()]
