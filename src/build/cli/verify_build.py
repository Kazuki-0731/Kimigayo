#!/usr/bin/env python3
"""
Build Verification CLI Tool

Verifies reproducible builds and validates build metadata.

Usage:
    verify_build.py metadata <metadata-path>
    verify_build.py compare <build-dir1> <build-dir2>
    verify_build.py hash <file-path> <expected-hash>
    verify_build.py reproducible <output-dir> --builds N

Requirements:
- 6.4: Cryptographic verification of build reproducibility
- 6.5: Build metadata inclusion
"""

import sys
import argparse
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.build.reproducible import (
    BuildVerifier,
    BuildMetadata,
    calculate_build_checksum,
    verify_cross_environment_reproducibility,
)
from src.build.config import BuildConfig


def cmd_verify_metadata(args):
    """Verify build metadata file"""
    metadata_path = Path(args.metadata_path)

    if not metadata_path.exists():
        print(f"❌ Error: Metadata file not found: {metadata_path}", file=sys.stderr)
        return 1

    try:
        metadata = BuildVerifier.verify_metadata(metadata_path)

        print("✅ Metadata is valid")
        print()
        print("Build Information:")
        print(f"  Build ID: {metadata.build_id}")
        print(f"  Timestamp: {metadata.timestamp}")
        print(f"  Source Hash: {metadata.source_hash}")
        print(f"  Output Hash: {metadata.output_hash}")
        print()
        print("Environment:")
        print(f"  Hostname: {metadata.environment.hostname}")
        print(f"  Platform: {metadata.environment.platform_system} {metadata.environment.platform_release}")
        print(f"  Architecture: {metadata.environment.platform_machine}")
        print(f"  Python: {metadata.environment.python_version}")
        print()
        print(f"Dependencies ({len(metadata.dependencies)}):")
        for dep in metadata.dependencies:
            print(f"  - {dep.name}@{dep.version} ({dep.source})")

        return 0

    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        return 1


def cmd_compare_builds(args):
    """Compare two build directories"""
    build_dir1 = Path(args.build_dir1)
    build_dir2 = Path(args.build_dir2)

    if not build_dir1.exists():
        print(f"❌ Error: Build directory not found: {build_dir1}", file=sys.stderr)
        return 1

    if not build_dir2.exists():
        print(f"❌ Error: Build directory not found: {build_dir2}", file=sys.stderr)
        return 1

    try:
        results = BuildVerifier.compare_builds(build_dir1, build_dir2)

        print("Build Comparison Results:")
        print()

        all_passed = all(results.values())

        for check, passed in results.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check.replace('_', ' ').title()}")

        print()

        if all_passed:
            print("✅ Builds are reproducible and identical")
            return 0
        else:
            print("❌ Builds are not identical")
            return 1

    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        return 1


def cmd_verify_hash(args):
    """Verify file hash"""
    file_path = Path(args.file_path)
    expected_hash = args.expected_hash

    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}", file=sys.stderr)
        return 1

    try:
        actual_hash = calculate_build_checksum(file_path)

        print(f"File: {file_path}")
        print(f"Expected Hash: {expected_hash}")
        print(f"Actual Hash:   {actual_hash}")
        print()

        if BuildVerifier.verify_output_hash(file_path, expected_hash):
            print("✅ Hash verification passed")
            return 0
        else:
            print("❌ Hash verification failed")
            return 1

    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        return 1


def cmd_verify_reproducible(args):
    """Verify reproducible builds"""
    output_dir = Path(args.output_dir)
    num_builds = args.builds

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    try:
        # Create a minimal config for testing
        config = BuildConfig(
            architecture="x86_64",
            image_type="minimal",
            reproducible=True
        )

        print(f"Performing {num_builds} builds to verify reproducibility...")
        print()

        is_reproducible, checksums = verify_cross_environment_reproducibility(
            config=config,
            output_dir=output_dir,
            num_builds=num_builds
        )

        print("Build Checksums:")
        for i, checksum in enumerate(checksums, 1):
            print(f"  Build {i}: {checksum}")
        print()

        unique_checksums = len(set(checksums))
        print(f"Unique checksums: {unique_checksums}")
        print()

        if is_reproducible:
            print("✅ All builds are reproducible (identical checksums)")
            return 0
        else:
            print(f"❌ Builds are not reproducible ({unique_checksums} different checksums)")
            return 1

    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Kimigayo OS Build Verification Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify metadata file
  verify_build.py metadata /path/to/build-metadata.json

  # Compare two builds
  verify_build.py compare /path/to/build1 /path/to/build2

  # Verify file hash
  verify_build.py hash /path/to/file.tar.gz abc123def456...

  # Verify reproducibility with multiple builds
  verify_build.py reproducible /path/to/output --builds 3
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # metadata command
    parser_metadata = subparsers.add_parser('metadata', help='Verify build metadata')
    parser_metadata.add_argument('metadata_path', help='Path to build-metadata.json')

    # compare command
    parser_compare = subparsers.add_parser('compare', help='Compare two builds')
    parser_compare.add_argument('build_dir1', help='First build directory')
    parser_compare.add_argument('build_dir2', help='Second build directory')

    # hash command
    parser_hash = subparsers.add_parser('hash', help='Verify file hash')
    parser_hash.add_argument('file_path', help='Path to file')
    parser_hash.add_argument('expected_hash', help='Expected SHA-256 hash')

    # reproducible command
    parser_repro = subparsers.add_parser('reproducible', help='Verify reproducible builds')
    parser_repro.add_argument('output_dir', help='Output directory for builds')
    parser_repro.add_argument('--builds', type=int, default=2, help='Number of builds to perform (default: 2)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command handler
    if args.command == 'metadata':
        return cmd_verify_metadata(args)
    elif args.command == 'compare':
        return cmd_compare_builds(args)
    elif args.command == 'hash':
        return cmd_verify_hash(args)
    elif args.command == 'reproducible':
        return cmd_verify_reproducible(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
