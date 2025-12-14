"""
Base Image Size Verification

Verifies and optimizes base image sizes.

Design Goal:
- Minimal: 5MB or less
- Standard: 15MB or less
- Extended: 50MB or less
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum


class ImageType(Enum):
    """Image types with size targets"""
    MINIMAL = ("minimal", 5.0)  # 5MB
    STANDARD = ("standard", 15.0)  # 15MB
    EXTENDED = ("extended", 50.0)  # 50MB

    def __init__(self, name: str, target_mb: float):
        self._name = name
        self._target_mb = target_mb

    @property
    def image_name(self) -> str:
        """Get image name"""
        return self._name

    @property
    def target_mb(self) -> float:
        """Get target size in MB"""
        return self._target_mb


@dataclass
class ComponentSize:
    """Size of a component"""
    name: str
    path: str
    size_bytes: int

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    def size_mb(self) -> float:
        """Get size in MB"""
        return self.size_bytes / (1024 * 1024)

    def size_kb(self) -> float:
        """Get size in KB"""
        return self.size_bytes / 1024


@dataclass
class ImageSizeProfile:
    """Image size profile"""
    image_type: str
    total_size_bytes: int
    components: List[ComponentSize] = field(default_factory=list)
    target_mb: float = 0.0
    meets_target: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'image_type': self.image_type,
            'total_size_bytes': self.total_size_bytes,
            'total_size_mb': self.total_mb(),
            'components': [c.to_dict() for c in self.components],
            'target_mb': self.target_mb,
            'meets_target': self.meets_target
        }

    def total_mb(self) -> float:
        """Get total size in MB"""
        return self.total_size_bytes / (1024 * 1024)

    def total_kb(self) -> float:
        """Get total size in KB"""
        return self.total_size_bytes / 1024


class ImageSizeAnalyzer:
    """
    Analyzes image sizes.

    Design Goal: Verify image size targets
    """

    def __init__(self):
        """Initialize image size analyzer"""
        self.image_types = {
            ImageType.MINIMAL.image_name: ImageType.MINIMAL,
            ImageType.STANDARD.image_name: ImageType.STANDARD,
            ImageType.EXTENDED.image_name: ImageType.EXTENDED
        }

    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes
        """
        try:
            return os.path.getsize(file_path)
        except (OSError, IOError):
            return 0

    def get_directory_size(self, directory: str) -> int:
        """
        Get total size of directory recursively.

        Args:
            directory: Path to directory

        Returns:
            Total size in bytes
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, IOError):
                        continue
        except (OSError, IOError):
            pass
        return total_size

    def analyze_components(self, image_path: str, component_paths: List[str]) -> List[ComponentSize]:
        """
        Analyze component sizes.

        Args:
            image_path: Base path for the image
            component_paths: List of component paths relative to image_path

        Returns:
            List of component sizes
        """
        components = []

        for comp_path in component_paths:
            full_path = os.path.join(image_path, comp_path)

            if os.path.isfile(full_path):
                size = self.get_file_size(full_path)
            elif os.path.isdir(full_path):
                size = self.get_directory_size(full_path)
            else:
                size = 0

            component = ComponentSize(
                name=comp_path,
                path=full_path,
                size_bytes=size
            )
            components.append(component)

        return components

    def verify_image_size(
        self,
        image_type: ImageType,
        total_size_bytes: int,
        components: Optional[List[ComponentSize]] = None
    ) -> ImageSizeProfile:
        """
        Verify image size meets target.

        Args:
            image_type: Type of image
            total_size_bytes: Total image size in bytes
            components: Optional list of components

        Returns:
            Image size profile
        """
        total_mb = total_size_bytes / (1024 * 1024)
        meets_target = total_mb <= image_type.target_mb

        profile = ImageSizeProfile(
            image_type=image_type.image_name,
            total_size_bytes=total_size_bytes,
            components=components or [],
            target_mb=image_type.target_mb,
            meets_target=meets_target
        )

        return profile

    def analyze_image(
        self,
        image_type: ImageType,
        image_path: str,
        component_paths: Optional[List[str]] = None
    ) -> ImageSizeProfile:
        """
        Analyze complete image.

        Args:
            image_type: Type of image
            image_path: Path to image directory or file
            component_paths: Optional list of component paths to analyze

        Returns:
            Image size profile
        """
        # Get total size
        if os.path.isfile(image_path):
            total_size = self.get_file_size(image_path)
            components = []
        elif os.path.isdir(image_path):
            total_size = self.get_directory_size(image_path)

            # Analyze components if provided
            if component_paths:
                components = self.analyze_components(image_path, component_paths)
            else:
                components = []
        else:
            total_size = 0
            components = []

        return self.verify_image_size(image_type, total_size, components)


class ImageOptimizer:
    """
    Optimizes image sizes.

    Design Goal: Achieve image size targets
    """

    def __init__(self, analyzer: Optional[ImageSizeAnalyzer] = None):
        """
        Initialize image optimizer.

        Args:
            analyzer: Image size analyzer instance
        """
        self.analyzer = analyzer or ImageSizeAnalyzer()
        self.optimizations_applied = []

    def suggest_optimizations(self, profile: ImageSizeProfile) -> List[str]:
        """
        Suggest image size optimizations.

        Args:
            profile: Image size profile

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        if not profile.meets_target:
            excess_mb = profile.total_mb() - profile.target_mb
            suggestions.append(
                f"Image size exceeds target by {excess_mb:.2f}MB"
            )

        # Analyze component sizes
        sorted_components = sorted(
            profile.components,
            key=lambda c: c.size_bytes,
            reverse=True
        )

        # Suggest optimizations for large components
        for component in sorted_components[:5]:
            component_mb = component.size_mb()

            if component_mb > 1.0:
                suggestions.append(
                    f"Large component: {component.name} ({component_mb:.2f}MB)"
                )

                # Specific suggestions based on component type
                if 'kernel' in component.name.lower():
                    suggestions.append("Consider minimal kernel configuration")
                    suggestions.append("Remove unnecessary kernel modules")

                if 'lib' in component.name.lower() or 'library' in component.name.lower():
                    suggestions.append("Use static linking where possible")
                    suggestions.append("Strip debug symbols from libraries")

                if 'bin' in component.name.lower():
                    suggestions.append("Use BusyBox for combined utilities")
                    suggestions.append("Strip binaries")

                if 'doc' in component.name.lower() or 'man' in component.name.lower():
                    suggestions.append(f"Remove documentation: {component.name}")

        # General optimization suggestions
        if profile.image_type == ImageType.MINIMAL.image_name:
            suggestions.append("For minimal image: Include only essential binaries")
            suggestions.append("Use musl libc for smaller footprint")
            suggestions.append("Disable all optional features")

        return suggestions

    def apply_optimization(self, optimization: str) -> bool:
        """
        Apply an image optimization.

        Args:
            optimization: Optimization to apply

        Returns:
            True if successfully applied
        """
        self.optimizations_applied.append(optimization)
        return True

    def optimize_for_target(self, profile: ImageSizeProfile) -> List[str]:
        """
        Apply optimizations to meet size target.

        Args:
            profile: Current image size profile

        Returns:
            List of optimizations applied
        """
        suggestions = self.suggest_optimizations(profile)

        actions = []
        for suggestion in suggestions:
            if self.apply_optimization(suggestion):
                actions.append(f"Applied: {suggestion}")

        return actions

    def get_optimization_status(self) -> Dict:
        """
        Get optimization status.

        Returns:
            Dictionary with optimization information
        """
        return {
            'optimizations_applied': self.optimizations_applied,
            'optimization_count': len(self.optimizations_applied)
        }


class ImageSizeBenchmark:
    """
    Benchmarks image sizes.

    Design Goal: Verify all image size targets
    """

    def __init__(self):
        """Initialize image size benchmark"""
        self.analyzer = ImageSizeAnalyzer()
        self.optimizer = ImageOptimizer(self.analyzer)

    def verify_minimal_image(self, image_path: str) -> Tuple[bool, str]:
        """
        Verify minimal image size (5MB target).

        Args:
            image_path: Path to minimal image

        Returns:
            Tuple of (meets_target, status_message)
        """
        profile = self.analyzer.analyze_image(
            ImageType.MINIMAL,
            image_path
        )

        if profile.meets_target:
            message = f"Minimal image {profile.total_mb():.2f}MB meets target (≤{ImageType.MINIMAL.target_mb}MB)"
        else:
            excess = profile.total_mb() - ImageType.MINIMAL.target_mb
            message = f"Minimal image {profile.total_mb():.2f}MB exceeds target by {excess:.2f}MB"

        return (profile.meets_target, message)

    def verify_standard_image(self, image_path: str) -> Tuple[bool, str]:
        """
        Verify standard image size (15MB target).

        Args:
            image_path: Path to standard image

        Returns:
            Tuple of (meets_target, status_message)
        """
        profile = self.analyzer.analyze_image(
            ImageType.STANDARD,
            image_path
        )

        if profile.meets_target:
            message = f"Standard image {profile.total_mb():.2f}MB meets target (≤{ImageType.STANDARD.target_mb}MB)"
        else:
            excess = profile.total_mb() - ImageType.STANDARD.target_mb
            message = f"Standard image {profile.total_mb():.2f}MB exceeds target by {excess:.2f}MB"

        return (profile.meets_target, message)

    def verify_extended_image(self, image_path: str) -> Tuple[bool, str]:
        """
        Verify extended image size (50MB target).

        Args:
            image_path: Path to extended image

        Returns:
            Tuple of (meets_target, status_message)
        """
        profile = self.analyzer.analyze_image(
            ImageType.EXTENDED,
            image_path
        )

        if profile.meets_target:
            message = f"Extended image {profile.total_mb():.2f}MB meets target (≤{ImageType.EXTENDED.target_mb}MB)"
        else:
            excess = profile.total_mb() - ImageType.EXTENDED.target_mb
            message = f"Extended image {profile.total_mb():.2f}MB exceeds target by {excess:.2f}MB"

        return (profile.meets_target, message)

    def verify_all_images(
        self,
        minimal_path: Optional[str] = None,
        standard_path: Optional[str] = None,
        extended_path: Optional[str] = None
    ) -> Dict:
        """
        Verify all image types.

        Args:
            minimal_path: Path to minimal image
            standard_path: Path to standard image
            extended_path: Path to extended image

        Returns:
            Verification results
        """
        results = {
            'all_passed': True,
            'images': {}
        }

        if minimal_path:
            meets_target, message = self.verify_minimal_image(minimal_path)
            results['images']['minimal'] = {
                'meets_target': meets_target,
                'message': message
            }
            if not meets_target:
                results['all_passed'] = False

        if standard_path:
            meets_target, message = self.verify_standard_image(standard_path)
            results['images']['standard'] = {
                'meets_target': meets_target,
                'message': message
            }
            if not meets_target:
                results['all_passed'] = False

        if extended_path:
            meets_target, message = self.verify_extended_image(extended_path)
            results['images']['extended'] = {
                'meets_target': meets_target,
                'message': message
            }
            if not meets_target:
                results['all_passed'] = False

        return results

    def optimize_and_verify(
        self,
        profile: ImageSizeProfile
    ) -> Dict:
        """
        Optimize image and verify target is met.

        Args:
            profile: Current image size profile

        Returns:
            Optimization results
        """
        optimizations = self.optimizer.optimize_for_target(profile)

        return {
            'initial_size_mb': profile.total_mb(),
            'target_mb': profile.target_mb,
            'meets_target': profile.meets_target,
            'optimizations_applied': optimizations
        }


class ImageSizeReporter:
    """
    Reports image size metrics.
    """

    def generate_report(self, profile: ImageSizeProfile) -> str:
        """
        Generate image size report.

        Args:
            profile: Image size profile

        Returns:
            Report as string
        """
        report_lines = [
            f"=== {profile.image_type.upper()} Image Size Report ===",
            f"Total Size: {profile.total_mb():.2f}MB ({profile.total_kb():.2f}KB)",
            f"Target: ≤{profile.target_mb}MB",
            f"Status: {'PASS' if profile.meets_target else 'FAIL'}",
        ]

        if not profile.meets_target:
            excess = profile.total_mb() - profile.target_mb
            report_lines.append(f"Exceeds target by: {excess:.2f}MB")

        if profile.components:
            report_lines.append("")
            report_lines.append("Component Breakdown:")

            # Sort by size
            sorted_components = sorted(
                profile.components,
                key=lambda c: c.size_bytes,
                reverse=True
            )

            for component in sorted_components:
                percentage = (component.size_bytes / profile.total_size_bytes * 100) if profile.total_size_bytes > 0 else 0
                report_lines.append(
                    f"  {component.name:30s} {component.size_mb():8.2f}MB ({percentage:5.1f}%)"
                )

        return "\n".join(report_lines)

    def generate_comparison_report(
        self,
        profiles: Dict[str, ImageSizeProfile]
    ) -> str:
        """
        Generate comparison report for multiple images.

        Args:
            profiles: Dictionary of image type to profile

        Returns:
            Comparison report as string
        """
        report_lines = [
            "=== Image Size Comparison Report ===",
            ""
        ]

        for image_type in ['minimal', 'standard', 'extended']:
            if image_type in profiles:
                profile = profiles[image_type]
                status = 'PASS' if profile.meets_target else 'FAIL'
                report_lines.append(
                    f"{image_type.upper():10s}: {profile.total_mb():6.2f}MB / {profile.target_mb:5.1f}MB [{status}]"
                )

        return "\n".join(report_lines)

    def export_metrics(self, profile: ImageSizeProfile) -> Dict:
        """
        Export metrics in structured format.

        Args:
            profile: Image size profile

        Returns:
            Metrics dictionary
        """
        return {
            'image_type': profile.image_type,
            'total_size_mb': profile.total_mb(),
            'total_size_bytes': profile.total_size_bytes,
            'target_mb': profile.target_mb,
            'meets_target': profile.meets_target,
            'component_count': len(profile.components)
        }
