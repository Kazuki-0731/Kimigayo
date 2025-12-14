"""
Ed25519 Signature Verification Tests

Tests for Ed25519 signature verification functionality.
"""

import pytest
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False

from src.pkg.security import (
    Ed25519Verifier,
    PackageVerifier,
    VerificationResult,
    HashVerifier,
    ED25519_AVAILABLE as MODULE_ED25519_AVAILABLE,
)


@pytest.mark.skipif(not ED25519_AVAILABLE, reason="cryptography library not installed")
@pytest.mark.property
class TestEd25519Verification:
    """Test Ed25519 signature verification"""

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=30)
    def test_valid_signature_verification(self, content):
        """
        Property: Valid Ed25519 signature is verified successfully
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Generate key pair
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()

            # Sign the file
            with open(pkg_path, 'rb') as f:
                message = f.read()
            signature = private_key.sign(message)

            # Convert to hex
            signature_hex = signature.hex()
            public_key_hex = public_key.public_bytes_raw().hex()

            # Verify
            verifier = Ed25519Verifier()
            success, error = verifier.verify_signature(
                pkg_path,
                signature_hex,
                public_key_hex
            )

            assert success is True
            assert error == ""
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=30)
    def test_invalid_signature_rejected(self, content):
        """
        Property: Invalid Ed25519 signature is rejected
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Generate key pair
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()

            # Create invalid signature (all zeros)
            invalid_signature_hex = "0" * 128
            public_key_hex = public_key.public_bytes_raw().hex()

            # Verify
            verifier = Ed25519Verifier()
            success, error = verifier.verify_signature(
                pkg_path,
                invalid_signature_hex,
                public_key_hex
            )

            assert success is False
            assert "invalid" in error.lower()
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=30)
    def test_wrong_public_key_rejected(self, content):
        """
        Property: Signature with wrong public key is rejected
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Generate two key pairs
            private_key1 = Ed25519PrivateKey.generate()
            private_key2 = Ed25519PrivateKey.generate()
            public_key2 = private_key2.public_key()

            # Sign with key1
            with open(pkg_path, 'rb') as f:
                message = f.read()
            signature = private_key1.sign(message)

            # Try to verify with key2
            signature_hex = signature.hex()
            wrong_public_key_hex = public_key2.public_bytes_raw().hex()

            verifier = Ed25519Verifier()
            success, error = verifier.verify_signature(
                pkg_path,
                signature_hex,
                wrong_public_key_hex
            )

            assert success is False
            assert "invalid" in error.lower()
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=1, max_size=500), st.binary(min_size=1, max_size=500))
    @settings(max_examples=30)
    def test_tampered_content_detected(self, original_content, tampered_content):
        """
        Property: Tampering with signed content is detected
        """
        # Ensure content is different
        if original_content == tampered_content:
            return

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(original_content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Generate key pair and sign original content
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()

            with open(pkg_path, 'rb') as f:
                message = f.read()
            signature = private_key.sign(message)

            signature_hex = signature.hex()
            public_key_hex = public_key.public_bytes_raw().hex()

            # Replace content with tampered version
            with open(pkg_path, 'wb') as f:
                f.write(tampered_content)

            # Verify should fail
            verifier = Ed25519Verifier()
            success, error = verifier.verify_signature(
                pkg_path,
                signature_hex,
                public_key_hex
            )

            assert success is False
        finally:
            pkg_path.unlink()

    def test_signature_length_validation(self):
        """
        Property: Invalid signature length is rejected
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()
            pkg_path = Path(f.name)

        try:
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            public_key_hex = public_key.public_bytes_raw().hex()

            # Too short signature
            short_sig = "ab" * 30  # 60 chars instead of 128
            verifier = Ed25519Verifier()
            success, error = verifier.verify_signature(
                pkg_path,
                short_sig,
                public_key_hex
            )

            assert success is False
            assert "length" in error.lower()
        finally:
            pkg_path.unlink()

    def test_public_key_length_validation(self):
        """
        Property: Invalid public key length is rejected
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Too short public key
            short_key = "ab" * 20  # 40 chars instead of 64
            valid_sig = "00" * 64  # Valid length but wrong signature

            verifier = Ed25519Verifier()
            success, error = verifier.verify_signature(
                pkg_path,
                valid_sig,
                short_key
            )

            assert success is False
            assert "length" in error.lower()
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=30)
    def test_trusted_key_verification(self, content):
        """
        Property: Trusted key verification works correctly
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Generate key pair
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            public_key_hex = public_key.public_bytes_raw().hex()

            # Sign
            with open(pkg_path, 'rb') as f:
                message = f.read()
            signature = private_key.sign(message)
            signature_hex = signature.hex()

            # Create verifier with trusted key
            verifier = Ed25519Verifier({"official-key": public_key_hex})

            # Verify with trusted key
            success, error = verifier.verify_with_trusted_key(
                pkg_path,
                signature_hex,
                "official-key"
            )

            assert success is True
            assert error == ""
        finally:
            pkg_path.unlink()

    def test_missing_trusted_key(self):
        """
        Property: Verification fails when trusted key not found
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()
            pkg_path = Path(f.name)

        try:
            verifier = Ed25519Verifier({})
            success, error = verifier.verify_with_trusted_key(
                pkg_path,
                "00" * 64,
                "nonexistent-key"
            )

            assert success is False
            assert "not found" in error.lower()
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=30)
    def test_package_verifier_ed25519(self, content):
        """
        Property: PackageVerifier works with Ed25519 signatures
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Calculate hash
            hash_verifier = HashVerifier()
            expected_hash = hash_verifier.calculate_sha256(pkg_path)

            # Generate key and sign
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            public_key_hex = public_key.public_bytes_raw().hex()

            with open(pkg_path, 'rb') as f:
                message = f.read()
            signature = private_key.sign(message)
            signature_hex = signature.hex()

            # Verify package
            verifier = PackageVerifier()
            report = verifier.verify_package_ed25519(
                pkg_path,
                expected_hash,
                signature_hex,
                public_key_hex
            )

            assert report.is_success()
            assert report.hash_verified
            assert report.signature_verified
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=30)
    def test_package_verifier_ed25519_wrong_hash(self, content):
        """
        Property: PackageVerifier rejects package with wrong hash
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Use wrong hash
            wrong_hash = "0" * 64

            # Generate valid signature
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            public_key_hex = public_key.public_bytes_raw().hex()

            with open(pkg_path, 'rb') as f:
                message = f.read()
            signature = private_key.sign(message)
            signature_hex = signature.hex()

            # Verify should fail on hash
            verifier = PackageVerifier()
            report = verifier.verify_package_ed25519(
                pkg_path,
                wrong_hash,
                signature_hex,
                public_key_hex
            )

            assert not report.is_success()
            assert not report.hash_verified
            assert report.result == VerificationResult.HASH_MISMATCH
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=30)
    def test_key_length_consistency(self, content):
        """
        Property: Ed25519 keys are always 32 bytes (64 hex chars)
        """
        # Generate multiple keys
        for _ in range(5):
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            public_key_hex = public_key.public_bytes_raw().hex()

            # Should always be 64 hex characters
            assert len(public_key_hex) == 64

    @given(st.binary(min_size=1, max_size=1000))
    @settings(max_examples=30)
    def test_signature_length_consistency(self, content):
        """
        Property: Ed25519 signatures are always 64 bytes (128 hex chars)
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            private_key = Ed25519PrivateKey.generate()

            with open(pkg_path, 'rb') as f:
                message = f.read()
            signature = private_key.sign(message)
            signature_hex = signature.hex()

            # Should always be 128 hex characters
            assert len(signature_hex) == 128
        finally:
            pkg_path.unlink()
