"""
Property 6: Package Verification Completeness
Property 14: Package Integrity Verification

Verifies that package security verification is complete and correct.
Testing requirements 2.3 and 4.3.
"""

import pytest
import tempfile
import hashlib
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path

from src.pkg.security import (
    HashVerifier,
    GPGVerifier,
    PackageVerifier,
    VerificationResult,
)


@st.composite
def package_content_strategy(draw):
    """Generate random package content"""
    size = draw(st.integers(min_value=1, max_value=10000))
    content = draw(st.binary(min_size=size, max_size=size))
    return content


@pytest.mark.property
class TestPackageVerification:
    """Test property 6 and 14: Package verification completeness and integrity"""

    @given(package_content_strategy())
    @settings(max_examples=50)
    def test_hash_verification_correct_hash(self, content):
        """
        Property: Package with correct hash is verified successfully
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Calculate expected hash
            expected_hash = HashVerifier.calculate_sha256(pkg_path)

            # Verify
            verifier = HashVerifier()
            result = verifier.verify_hash(pkg_path, expected_hash)

            assert result is True
        finally:
            pkg_path.unlink()

    @given(package_content_strategy())
    @settings(max_examples=50)
    def test_hash_verification_incorrect_hash(self, content):
        """
        Property: Package with incorrect hash fails verification
        """
        assume(len(content) > 0)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Use wrong hash
            wrong_hash = "0" * 64  # Invalid hash

            # Verify
            verifier = HashVerifier()
            result = verifier.verify_hash(pkg_path, wrong_hash)

            assert result is False
        finally:
            pkg_path.unlink()

    @given(package_content_strategy())
    @settings(max_examples=50)
    def test_hash_calculation_deterministic(self, content):
        """
        Property: Hash calculation is deterministic
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            verifier = HashVerifier()

            # Calculate hash multiple times
            hash1 = verifier.calculate_sha256(pkg_path)
            hash2 = verifier.calculate_sha256(pkg_path)
            hash3 = verifier.calculate_sha256(pkg_path)

            # Should be identical
            assert hash1 == hash2 == hash3
            assert len(hash1) == 64  # SHA-256 is 256 bits = 64 hex chars
        finally:
            pkg_path.unlink()

    @given(package_content_strategy())
    @settings(max_examples=50)
    def test_hash_case_insensitive(self, content):
        """
        Property: Hash verification is case-insensitive
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            verifier = HashVerifier()
            hash_lower = verifier.calculate_sha256(pkg_path).lower()
            hash_upper = hash_lower.upper()

            # Both should verify
            assert verifier.verify_hash(pkg_path, hash_lower)
            assert verifier.verify_hash(pkg_path, hash_upper)
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=1, max_size=1000), st.binary(min_size=1, max_size=1000))
    @settings(max_examples=50)
    def test_different_content_different_hash(self, content1, content2):
        """
        Property: Different content produces different hash (collision resistance)
        """
        assume(content1 != content2)

        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(content1)
            f1.flush()
            path1 = Path(f1.name)

        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(content2)
            f2.flush()
            path2 = Path(f2.name)

        try:
            verifier = HashVerifier()
            hash1 = verifier.calculate_sha256(path1)
            hash2 = verifier.calculate_sha256(path2)

            # Different content should produce different hashes
            assert hash1 != hash2
        finally:
            path1.unlink()
            path2.unlink()

    @given(package_content_strategy())
    @settings(max_examples=50)
    def test_package_verifier_correct_hash_no_signature(self, content):
        """
        Property: Package with correct hash passes verification (no signature required)
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Calculate expected hash
            expected_hash = HashVerifier.calculate_sha256(pkg_path)

            # Verify package
            verifier = PackageVerifier()
            report = verifier.verify_package(
                pkg_path,
                expected_hash,
                require_signature=False
            )

            assert report.is_success()
            assert report.hash_verified
            assert report.result == VerificationResult.SUCCESS
        finally:
            pkg_path.unlink()

    @given(package_content_strategy())
    @settings(max_examples=50)
    def test_package_verifier_incorrect_hash(self, content):
        """
        Property: Package with incorrect hash fails verification
        """
        assume(len(content) > 0)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Use wrong hash
            wrong_hash = "a" * 64

            # Verify package
            verifier = PackageVerifier()
            report = verifier.verify_package(
                pkg_path,
                wrong_hash,
                require_signature=False
            )

            assert not report.is_success()
            assert not report.hash_verified
            assert report.result == VerificationResult.HASH_MISMATCH
        finally:
            pkg_path.unlink()

    @given(package_content_strategy())
    @settings(max_examples=50)
    def test_package_verifier_missing_signature(self, content):
        """
        Property: Package requiring signature but missing it fails verification
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Calculate correct hash
            expected_hash = HashVerifier.calculate_sha256(pkg_path)

            # Verify package (require signature but don't provide it)
            verifier = PackageVerifier()
            report = verifier.verify_package(
                pkg_path,
                expected_hash,
                signature_path=None,
                require_signature=True
            )

            assert not report.is_success()
            assert report.result == VerificationResult.SIGNATURE_MISSING
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=100, max_size=1000))
    @settings(max_examples=50)
    def test_hash_length_consistency(self, content):
        """
        Property: SHA-256 hash always produces 64 character hex string
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            verifier = HashVerifier()
            hash_value = verifier.calculate_sha256(pkg_path)

            # SHA-256 should always be 64 hex characters
            assert len(hash_value) == 64
            assert all(c in '0123456789abcdef' for c in hash_value.lower())
        finally:
            pkg_path.unlink()

    @given(package_content_strategy())
    @settings(max_examples=30)
    def test_verification_report_structure(self, content):
        """
        Property: Verification report always has consistent structure
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            expected_hash = HashVerifier.calculate_sha256(pkg_path)
            verifier = PackageVerifier()
            report = verifier.verify_package(
                pkg_path,
                expected_hash,
                require_signature=False
            )

            # Report should have required fields
            assert hasattr(report, 'result')
            assert hasattr(report, 'hash_verified')
            assert hasattr(report, 'signature_verified')
            assert hasattr(report, 'error_message')
            assert isinstance(report.result, VerificationResult)
            assert isinstance(report.hash_verified, bool)
            assert isinstance(report.signature_verified, bool)
            assert isinstance(report.error_message, str)
        finally:
            pkg_path.unlink()

    @given(package_content_strategy())
    @settings(max_examples=30)
    def test_metadata_verification(self, content):
        """
        Property: Package verification from metadata works correctly
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Calculate hash
            expected_hash = HashVerifier.calculate_sha256(pkg_path)

            # Create metadata
            metadata = {
                "checksum_sha256": expected_hash,
                "gpg_signature": None
            }

            # Verify
            verifier = PackageVerifier()
            report = verifier.verify_package_metadata(pkg_path, metadata)

            assert report.is_success()
            assert report.hash_verified
        finally:
            pkg_path.unlink()

    @given(package_content_strategy())
    @settings(max_examples=30)
    def test_metadata_verification_missing_checksum(self, content):
        """
        Property: Verification fails gracefully when metadata lacks checksum
        """
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Create metadata without checksum
            metadata = {}

            # Verify
            verifier = PackageVerifier()
            report = verifier.verify_package_metadata(pkg_path, metadata)

            assert not report.is_success()
            assert report.result == VerificationResult.VERIFICATION_ERROR
            assert "checksum" in report.error_message.lower()
        finally:
            pkg_path.unlink()

    @given(st.binary(min_size=1, max_size=100))
    @settings(max_examples=30)
    def test_tampered_content_detected(self, original_content):
        """
        Property: Any modification to content is detected by hash verification
        """
        assume(len(original_content) > 0)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(original_content)
            f.flush()
            pkg_path = Path(f.name)

        try:
            # Calculate hash of original
            verifier = HashVerifier()
            original_hash = verifier.calculate_sha256(pkg_path)

            # Modify content (flip one byte)
            modified_content = bytearray(original_content)
            modified_content[0] = (modified_content[0] + 1) % 256

            # Write modified content
            with open(pkg_path, 'wb') as f:
                f.write(bytes(modified_content))

            # Verify with original hash should fail
            result = verifier.verify_hash(pkg_path, original_hash)
            assert result is False
        finally:
            pkg_path.unlink()
