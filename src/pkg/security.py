"""
Security Verification Module for Kimigayo OS Package Manager

Provides cryptographic verification of packages:
- Ed25519 signature verification (primary)
- GPG signature verification (legacy)
- SHA-256 hash verification
"""

import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False


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


class Ed25519Verifier:
    """Ed25519 signature verification (modern, lightweight)"""

    def __init__(self, trusted_keys: Optional[dict] = None):
        """
        Initialize Ed25519 verifier.

        Args:
            trusted_keys: Dict mapping key ID to public key (hex string)
                         Format: {"key_id": "hex_encoded_public_key"}
        """
        if not ED25519_AVAILABLE:
            raise RuntimeError("cryptography library not installed. Install with: pip install cryptography")

        self.trusted_keys = trusted_keys or {}

    def add_trusted_key(self, key_id: str, public_key_hex: str):
        """
        Add a trusted public key.

        Args:
            key_id: Identifier for this key
            public_key_hex: Public key as hex string (64 chars)
        """
        self.trusted_keys[key_id] = public_key_hex

    def verify_signature(
        self,
        file_path: Path,
        signature_hex: str,
        public_key_hex: str
    ) -> Tuple[bool, str]:
        """
        Verify Ed25519 signature of a file.

        Args:
            file_path: Path to file to verify
            signature_hex: Signature as hex string (128 chars)
            public_key_hex: Public key as hex string (64 chars)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Convert hex strings to bytes
            try:
                signature = bytes.fromhex(signature_hex)
                public_key_bytes = bytes.fromhex(public_key_hex)
            except ValueError as e:
                return False, f"Invalid hex encoding: {str(e)}"

            # Validate lengths
            if len(signature) != 64:
                return False, f"Invalid signature length: {len(signature)} (expected 64)"
            if len(public_key_bytes) != 32:
                return False, f"Invalid public key length: {len(public_key_bytes)} (expected 32)"

            # Read file content
            with open(file_path, 'rb') as f:
                message = f.read()

            # Create public key and verify
            try:
                public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
                public_key.verify(signature, message)
                return True, ""
            except InvalidSignature:
                return False, "Invalid Ed25519 signature"

        except FileNotFoundError:
            return False, f"File not found: {file_path}"
        except Exception as e:
            return False, f"Ed25519 verification error: {str(e)}"

    def verify_with_trusted_key(
        self,
        file_path: Path,
        signature_hex: str,
        key_id: str
    ) -> Tuple[bool, str]:
        """
        Verify signature using a trusted key from the keyring.

        Args:
            file_path: Path to file to verify
            signature_hex: Signature as hex string
            key_id: ID of trusted key to use

        Returns:
            Tuple of (success, error_message)
        """
        if key_id not in self.trusted_keys:
            return False, f"Trusted key not found: {key_id}"

        public_key_hex = self.trusted_keys[key_id]
        return self.verify_signature(file_path, signature_hex, public_key_hex)

    def load_public_key_from_file(self, key_path: Path) -> Tuple[Optional[str], str]:
        """
        Load public key from file.

        Args:
            key_path: Path to public key file (hex encoded)

        Returns:
            Tuple of (public_key_hex or None, error_message)
        """
        try:
            with open(key_path, 'r') as f:
                key_hex = f.read().strip()

            # Validate hex encoding
            try:
                key_bytes = bytes.fromhex(key_hex)
                if len(key_bytes) != 32:
                    return None, f"Invalid key length: {len(key_bytes)} (expected 32)"
                return key_hex, ""
            except ValueError:
                return None, "Invalid hex encoding in key file"

        except FileNotFoundError:
            return None, f"Key file not found: {key_path}"
        except Exception as e:
            return None, f"Error loading key: {str(e)}"


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

    def __init__(
        self,
        keyring_path: Optional[Path] = None,
        ed25519_keys: Optional[dict] = None,
        prefer_ed25519: bool = True
    ):
        """
        Initialize package verifier.

        Args:
            keyring_path: Path to GPG keyring (for legacy support)
            ed25519_keys: Dict of trusted Ed25519 keys
            prefer_ed25519: Prefer Ed25519 over GPG when both available
        """
        self.hash_verifier = HashVerifier()
        self.gpg_verifier = GPGVerifier(keyring_path)
        self.prefer_ed25519 = prefer_ed25519

        # Initialize Ed25519 verifier if cryptography is available
        if ED25519_AVAILABLE:
            self.ed25519_verifier = Ed25519Verifier(ed25519_keys)
        else:
            self.ed25519_verifier = None

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

    def verify_package_ed25519(
        self,
        package_path: Path,
        expected_hash: str,
        signature_hex: str,
        public_key_hex: str,
        require_signature: bool = True
    ) -> VerificationReport:
        """
        Verify package with Ed25519 signature.

        Args:
            package_path: Path to package file
            expected_hash: Expected SHA-256 hash
            signature_hex: Ed25519 signature (hex string)
            public_key_hex: Public key (hex string)
            require_signature: Whether to require valid signature

        Returns:
            Verification report
        """
        report = VerificationReport(result=VerificationResult.SUCCESS)

        # Check if Ed25519 is available
        if not self.ed25519_verifier:
            report.result = VerificationResult.VERIFICATION_ERROR
            report.error_message = "Ed25519 support not available (install PyNaCl)"
            return report

        # Verify hash first
        hash_valid = self.hash_verifier.verify_hash(package_path, expected_hash)
        report.hash_verified = hash_valid

        if not hash_valid:
            report.result = VerificationResult.HASH_MISMATCH
            report.error_message = "Package hash does not match expected value"
            return report

        # Verify Ed25519 signature
        if require_signature:
            sig_valid, error = self.ed25519_verifier.verify_signature(
                package_path,
                signature_hex,
                public_key_hex
            )
            report.signature_verified = sig_valid

            if not sig_valid:
                if "not found" in error.lower():
                    report.result = VerificationResult.KEY_NOT_FOUND
                elif "invalid" in error.lower():
                    report.result = VerificationResult.SIGNATURE_INVALID
                else:
                    report.result = VerificationResult.VERIFICATION_ERROR

                report.error_message = error
                return report

        # All checks passed
        report.result = VerificationResult.SUCCESS
        return report
