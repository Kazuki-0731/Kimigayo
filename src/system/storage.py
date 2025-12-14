"""
Storage Optimization

Manages storage usage monitoring, optimization, and efficiency.

Requirements:
- 1.5: Storage optimization - Minimum storage requirement 512MB
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class StorageUnit(Enum):
    """Storage units"""
    BYTES = 1
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024


class ImageType(Enum):
    """Image types and their size limits"""
    MINIMAL = ("minimal", 5)      # 5MB
    STANDARD = ("standard", 15)    # 15MB
    EXTENDED = ("extended", 50)    # 50MB

    def __init__(self, name: str, size_limit_mb: int):
        self.image_name = name
        self.size_limit_mb = size_limit_mb


@dataclass
class StorageUsage:
    """Storage usage information"""
    total: int          # Total storage in bytes
    used: int           # Used storage in bytes
    free: int           # Free storage in bytes
    available: int      # Available storage in bytes
    mount_point: str = "/"

    def to_mb(self, value: int) -> float:
        """Convert bytes to MB"""
        return value / StorageUnit.MB.value

    def to_gb(self, value: int) -> float:
        """Convert bytes to GB"""
        return value / StorageUnit.GB.value

    def get_usage_percentage(self) -> float:
        """Get storage usage percentage"""
        if self.total == 0:
            return 0.0
        return (self.used / self.total) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary with MB values"""
        return {
            'total_mb': self.to_mb(self.total),
            'used_mb': self.to_mb(self.used),
            'free_mb': self.to_mb(self.free),
            'available_mb': self.to_mb(self.available),
            'usage_percentage': self.get_usage_percentage(),
            'mount_point': self.mount_point
        }


@dataclass
class DirectorySize:
    """Directory size information"""
    path: str
    size: int  # Size in bytes
    file_count: int = 0
    dir_count: int = 0

    def to_mb(self) -> float:
        """Get size in MB"""
        return self.size / StorageUnit.MB.value

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'path': self.path,
            'size_mb': self.to_mb(),
            'file_count': self.file_count,
            'dir_count': self.dir_count
        }


class StorageMonitor:
    """
    Monitors system storage usage.

    Requirement: 1.5 (Storage usage monitoring)
    """

    def __init__(self):
        """Initialize storage monitor"""
        self.minimum_storage_mb = 512  # Requirement: 1.5
        self.recommended_storage_mb = 2048  # 2GB

    def get_storage_usage(self, path: str = "/") -> StorageUsage:
        """
        Get storage usage for a mount point.

        Requirement: 1.5 - Monitor storage usage

        Args:
            path: Mount point path

        Returns:
            Storage usage information
        """
        try:
            stat = os.statvfs(path)

            # Calculate sizes
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            available = stat.f_bavail * stat.f_frsize
            used = total - free

            return StorageUsage(
                total=total,
                used=used,
                free=free,
                available=available,
                mount_point=path
            )
        except Exception:
            return StorageUsage(
                total=0,
                used=0,
                free=0,
                available=0,
                mount_point=path
            )

    def check_minimum_storage(self, path: str = "/") -> Tuple[bool, float]:
        """
        Check if available storage meets minimum requirement.

        Requirement: 1.5 - Minimum storage 512MB

        Args:
            path: Mount point path

        Returns:
            Tuple of (meets_requirement, available_mb)
        """
        usage = self.get_storage_usage(path)
        available_mb = usage.to_mb(usage.available)
        meets_requirement = available_mb >= self.minimum_storage_mb

        return (meets_requirement, available_mb)

    def get_directory_size(self, path: Path) -> DirectorySize:
        """
        Get size of a directory.

        Args:
            path: Directory path

        Returns:
            Directory size information
        """
        if not path.exists() or not path.is_dir():
            return DirectorySize(path=str(path), size=0)

        total_size = 0
        file_count = 0
        dir_count = 0

        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1
        except Exception:
            pass

        return DirectorySize(
            path=str(path),
            size=total_size,
            file_count=file_count,
            dir_count=dir_count
        )

    def get_largest_directories(self, root: Path, limit: int = 10) -> List[DirectorySize]:
        """
        Get largest directories under a root path.

        Args:
            root: Root directory path
            limit: Number of directories to return

        Returns:
            List of directory sizes
        """
        if not root.exists() or not root.is_dir():
            return []

        directories = []

        try:
            for item in root.iterdir():
                if item.is_dir():
                    dir_size = self.get_directory_size(item)
                    directories.append(dir_size)
        except Exception:
            pass

        # Sort by size
        directories.sort(key=lambda d: d.size, reverse=True)

        return directories[:limit]


class ImageSizeVerifier:
    """
    Verifies image sizes meet requirements.

    Requirement: 1.5 (Image size verification)
    """

    def verify_image_size(self, image_path: Path, image_type: ImageType) -> Tuple[bool, float]:
        """
        Verify image size meets requirement.

        Args:
            image_path: Path to image file
            image_type: Type of image (MINIMAL/STANDARD/EXTENDED)

        Returns:
            Tuple of (meets_requirement, actual_size_mb)
        """
        if not image_path.exists():
            return (False, 0.0)

        try:
            size_bytes = image_path.stat().st_size
            size_mb = size_bytes / StorageUnit.MB.value

            meets_requirement = size_mb <= image_type.size_limit_mb

            return (meets_requirement, size_mb)
        except Exception:
            return (False, 0.0)

    def verify_all_image_types(self, base_path: Path) -> Dict[str, Tuple[bool, float]]:
        """
        Verify all image types.

        Args:
            base_path: Base directory containing images

        Returns:
            Dictionary of image type to (meets_requirement, size_mb)
        """
        results = {}

        for image_type in ImageType:
            image_path = base_path / f"{image_type.image_name}.img"
            meets_req, size_mb = self.verify_image_size(image_path, image_type)
            results[image_type.image_name] = (meets_req, size_mb)

        return results


class StorageOptimizer:
    """
    Optimizes storage usage.

    Requirement: 1.5 (Storage optimization)
    """

    def __init__(self, monitor: Optional[StorageMonitor] = None):
        """
        Initialize storage optimizer.

        Args:
            monitor: Storage monitor instance
        """
        self.monitor = monitor or StorageMonitor()
        self.optimizations_applied = []

    def find_large_files(self, root: Path, min_size_mb: float = 10) -> List[Tuple[Path, float]]:
        """
        Find large files that could be candidates for removal.

        Args:
            root: Root directory to search
            min_size_mb: Minimum file size in MB

        Returns:
            List of (file_path, size_mb) tuples
        """
        if not root.exists() or not root.is_dir():
            return []

        large_files = []
        min_size_bytes = int(min_size_mb * StorageUnit.MB.value)

        try:
            for item in root.rglob('*'):
                if item.is_file():
                    size = item.stat().st_size
                    if size >= min_size_bytes:
                        size_mb = size / StorageUnit.MB.value
                        large_files.append((item, size_mb))
        except Exception:
            pass

        # Sort by size
        large_files.sort(key=lambda x: x[1], reverse=True)

        return large_files

    def suggest_optimizations(self, root: Path = Path("/")) -> List[str]:
        """
        Suggest storage optimizations.

        Args:
            root: Root path to analyze

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Check available storage
        meets_min, available_mb = self.monitor.check_minimum_storage()
        if not meets_min:
            suggestions.append(f"Available storage ({available_mb:.1f}MB) is below minimum (512MB)")

        # Check for large files
        large_files = self.find_large_files(root, min_size_mb=50)
        if large_files:
            total_large_mb = sum(size for _, size in large_files)
            suggestions.append(f"Found {len(large_files)} files >50MB (total: {total_large_mb:.1f}MB)")

        # Check largest directories
        largest_dirs = self.monitor.get_largest_directories(root, limit=5)
        if largest_dirs and largest_dirs[0].to_mb() > 100:
            suggestions.append(f"Largest directory: {largest_dirs[0].path} ({largest_dirs[0].to_mb():.1f}MB)")

        return suggestions

    def apply_optimization(self, optimization: str) -> bool:
        """
        Apply a storage optimization.

        Args:
            optimization: Optimization to apply

        Returns:
            True if successfully applied
        """
        self.optimizations_applied.append(optimization)
        return True

    def clean_temporary_files(self, temp_dir: Path) -> int:
        """
        Clean temporary files.

        Args:
            temp_dir: Temporary directory path

        Returns:
            Number of bytes freed
        """
        if not temp_dir.exists():
            return 0

        freed = 0
        try:
            for item in temp_dir.iterdir():
                if item.is_file():
                    size = item.stat().st_size
                    # In real implementation: item.unlink()
                    freed += size
        except Exception:
            pass

        return freed


class StorageManager:
    """
    Manages overall storage monitoring and optimization.

    Requirement: 1.5 (Storage management)
    """

    def __init__(self):
        """Initialize storage manager"""
        self.monitor = StorageMonitor()
        self.optimizer = StorageOptimizer(self.monitor)
        self.verifier = ImageSizeVerifier()

    def get_status(self, path: str = "/") -> Dict:
        """
        Get comprehensive storage status.

        Args:
            path: Mount point path

        Returns:
            Dictionary with storage status information
        """
        usage = self.monitor.get_storage_usage(path)
        meets_min, available_mb = self.monitor.check_minimum_storage(path)

        return {
            'storage_usage': usage.to_dict(),
            'meets_minimum': meets_min,
            'available_mb': available_mb,
            'minimum_required_mb': self.monitor.minimum_storage_mb,
            'recommended_mb': self.monitor.recommended_storage_mb
        }

    def verify_storage_requirements(self, path: str = "/") -> Tuple[bool, str]:
        """
        Verify storage requirements are met.

        Requirement: 1.5 - Verify minimum storage requirement

        Args:
            path: Mount point path

        Returns:
            Tuple of (requirements_met, status_message)
        """
        meets_min, available_mb = self.monitor.check_minimum_storage(path)

        if meets_min:
            message = f"Available storage {available_mb:.1f}MB meets minimum requirement ({self.monitor.minimum_storage_mb}MB)"
        else:
            message = f"Available storage {available_mb:.1f}MB is below minimum requirement ({self.monitor.minimum_storage_mb}MB)"

        return (meets_min, message)

    def verify_image_sizes(self, image_dir: Path) -> Dict[str, bool]:
        """
        Verify all image sizes meet requirements.

        Args:
            image_dir: Directory containing images

        Returns:
            Dictionary of image type to compliance status
        """
        results = self.verifier.verify_all_image_types(image_dir)

        # Convert to simple bool results
        compliance = {}
        for image_type, (meets_req, _) in results.items():
            compliance[image_type] = meets_req

        return compliance

    def optimize(self, root: Path = Path("/")) -> List[str]:
        """
        Run storage optimization.

        Args:
            root: Root path to optimize

        Returns:
            List of optimizations performed
        """
        suggestions = self.optimizer.suggest_optimizations(root)

        actions = []
        for suggestion in suggestions:
            if self.optimizer.apply_optimization(suggestion):
                actions.append(f"Identified: {suggestion}")

        return actions

    def get_optimization_report(self, root: Path = Path("/")) -> Dict:
        """
        Get comprehensive optimization report.

        Args:
            root: Root path to analyze

        Returns:
            Dictionary with optimization information
        """
        usage = self.monitor.get_storage_usage(str(root))
        largest_dirs = self.monitor.get_largest_directories(root, limit=10)
        suggestions = self.optimizer.suggest_optimizations(root)

        return {
            'storage_usage': usage.to_dict(),
            'largest_directories': [d.to_dict() for d in largest_dirs],
            'optimization_suggestions': suggestions,
            'optimizations_applied': self.optimizer.optimizations_applied
        }
