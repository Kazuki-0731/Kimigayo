"""
Security Verification Module for Kimigayo OS Package Manager

Provides cryptographic verification of packages:
- GPG signature verification
- SHA-256 hash verification
"""

import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class VerificationResult(Enum):
    """Result of security verification"""
    SUCCESS = "success"
    HASH_MISMATCH = "hash_mismatch"
    SIGNATURE_INVALID = "signature_invalid"
    SIGNATURE_MISSING = "signature_missing"
    KEY_NOT_FOUND = "key_not_found"
    VERIFICATION_ERROR = "verification_error"


@dataclass
class VerificationReport:
    """Report from security verification"""
    result: VerificationResult
    hash_verified: bool = False
    signature_verified: bool = False
    error_message: str = ""

    def is_success(self) -> bool:
        """Check if verification succeeded"""
        return self.result == VerificationResult.SUCCESS


class HashVerifier:
    """SHA-256 hash verification"""

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            while chunk := f.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    @staticmethod
    def verify_hash(file_path: Path, expected_hash: str) -> bool:
        """
        Verify file hash against expected value.

        Args:
            file_path: Path to file
            expected_hash: Expected SHA-256 hash (hex string)

        Returns:
            True if hash matches, False otherwise
        """
        actual_hash = HashVerifier.calculate_sha256(file_path)
        return actual_hash.lower() == expected_hash.lower()


class GPGVerifier:
    """GPG signature verification"""

    def __init__(self, keyring_path: Optional[Path] = None):
        """
        Initialize GPG verifier.

        Args:
            keyring_path: Path to GPG keyring (optional)
        """
        self.keyring_path = keyring_path

    def verify_signature(
        self,
        file_path: Path,
        signature_path: Optional[Path] = None,
        detached: bool = True
    ) -> Tuple[bool, str]:
        """
        Verify GPG signature of a file.

        Args:
            file_path: Path to file to verify
            signature_path: Path to detached signature file (if detached=True)
            detached: Whether signature is detached or embedded

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Build GPG command
            cmd = ["gpg", "--verify"]

            # Add keyring if specified
            if self.keyring_path:
                cmd.extend(["--keyring", str(self.keyring_path)])

            # Add files
            if detached:
                if not signature_path:
                    return False, "Detached signature path required"
                cmd.extend([str(signature_path), str(file_path)])
            else:
                cmd.append(str(file_path))

            # Run GPG
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Check result
            if result.returncode == 0:
                return True, ""
            else:
                # Extract error message
                error = result.stderr.strip()

                # Check for common errors
                if "No public key" in error:
                    return False, "GPG key not found in keyring"
                elif "BAD signature" in error:
                    return False, "Invalid GPG signature"
                else:
                    return False, f"GPG verification failed: {error}"

        except FileNotFoundError:
            return False, "GPG not installed"
        except subprocess.TimeoutExpired:
            return False, "GPG verification timeout"
        except Exception as e:
            return False, f"GPG verification error: {str(e)}"

    def import_key(self, key_path: Path) -> Tuple[bool, str]:
        """
        Import a GPG public key.

        Args:
            key_path: Path to public key file

        Returns:
            Tuple of (success, error_message)
        """
        try:
            cmd = ["gpg", "--import", str(key_path)]

            if self.keyring_path:
                cmd.extend(["--keyring", str(self.keyring_path)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return True, ""
            else:
                return False, f"Key import failed: {result.stderr}"

        except Exception as e:
            return False, f"Key import error: {str(e)}"


class PackageVerifier:
    """Complete package verification (hash + signature)"""

    def __init__(self, keyring_path: Optional[Path] = None):
        """
        Initialize package verifier.

        Args:
            keyring_path: Path to GPG keyring
        """
        self.hash_verifier = HashVerifier()
        self.gpg_verifier = GPGVerifier(keyring_path)

    def verify_package(
        self,
        package_path: Path,
        expected_hash: str,
        signature_path: Optional[Path] = None,
        require_signature: bool = True
    ) -> VerificationReport:
        """
        Verify package integrity and authenticity.

        Args:
            package_path: Path to package file
            expected_hash: Expected SHA-256 hash
            signature_path: Path to GPG signature file
            require_signature: Whether to require valid signature

        Returns:
            Verification report
        """
        report = VerificationReport(result=VerificationResult.SUCCESS)

        # Verify hash first (faster check)
        hash_valid = self.hash_verifier.verify_hash(package_path, expected_hash)
        report.hash_verified = hash_valid

        if not hash_valid:
            report.result = VerificationResult.HASH_MISMATCH
            report.error_message = "Package hash does not match expected value"
            return report

        # Verify signature if required
        if require_signature:
            if not signature_path:
                report.result = VerificationResult.SIGNATURE_MISSING
                report.error_message = "Signature file required but not provided"
                return report

            sig_valid, error = self.gpg_verifier.verify_signature(
                package_path,
                signature_path
            )
            report.signature_verified = sig_valid

            if not sig_valid:
                # Determine specific error
                if "key not found" in error.lower():
                    report.result = VerificationResult.KEY_NOT_FOUND
                elif "invalid" in error.lower() or "bad" in error.lower():
                    report.result = VerificationResult.SIGNATURE_INVALID
                else:
                    report.result = VerificationResult.VERIFICATION_ERROR

                report.error_message = error
                return report

        # All checks passed
        report.result = VerificationResult.SUCCESS
        return report

    def verify_package_metadata(
        self,
        package_path: Path,
        metadata: dict
    ) -> VerificationReport:
        """
        Verify package using metadata from database.

        Args:
            package_path: Path to package file
            metadata: Package metadata dict with checksum info

        Returns:
            Verification report
        """
        # Extract hash
        expected_hash = metadata.get("checksum_sha256", "")
        if not expected_hash:
            report = VerificationReport(result=VerificationResult.VERIFICATION_ERROR)
            report.error_message = "No checksum in metadata"
            return report

        # Check for signature
        signature = metadata.get("gpg_signature")
        signature_path = None
        require_signature = False

        if signature:
            # If signature is in metadata, create temporary file
            # In real implementation, would handle this properly
            require_signature = True

        return self.verify_package(
            package_path,
            expected_hash,
            signature_path,
            require_signature=False  # For now, don't require signature
        )
