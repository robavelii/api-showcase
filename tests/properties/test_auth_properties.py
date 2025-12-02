"""Property-based tests for authentication utilities.

**Feature: openapi-showcase**
"""

import pytest
from hypothesis import given, settings, strategies as st, assume

from shared.auth.password import hash_password, verify_password


# Use ASCII-only strategy for passwords to avoid encoding issues
password_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
    min_size=1,
    max_size=32
)


class TestPasswordHashingProperties:
    """
    **Feature: openapi-showcase, Property 32: Password hashing**
    """

    @settings(max_examples=20)
    @given(password=password_strategy)
    def test_password_hash_is_bcrypt_format(self, password: str):
        """
        **Feature: openapi-showcase, Property 32: Password hashing**
        
        For any password stored in the system, the stored value SHALL be a bcrypt hash
        (not plaintext) that follows the bcrypt format.
        """
        hashed = hash_password(password)
        
        # The hash should start with bcrypt identifier
        assert hashed.startswith("$2")
        
        # The hash should have the expected bcrypt format: $2b$rounds$salt+hash
        # Total length should be 60 characters for bcrypt
        assert len(hashed) == 60
        
        # The hash should not equal the original password (not stored in plaintext)
        assert hashed != password

    @settings(max_examples=20)
    @given(password=password_strategy)
    def test_password_verification_succeeds_for_correct_password(self, password: str):
        """
        **Feature: openapi-showcase, Property 32: Password hashing**
        
        For any password, verifying the original password against the hash SHALL succeed.
        """
        hashed = hash_password(password)
        
        # Verification with correct password should succeed
        assert verify_password(password, hashed) is True

    @settings(max_examples=20)
    @given(
        password=password_strategy,
        wrong_password=password_strategy,
    )
    def test_password_verification_fails_for_wrong_password(
        self, password: str, wrong_password: str
    ):
        """
        **Feature: openapi-showcase, Property 32: Password hashing**
        
        For any password and a different wrong password, verification SHALL fail.
        """
        # Skip if passwords happen to be the same
        assume(password != wrong_password)
            
        hashed = hash_password(password)
        
        # Verification with wrong password should fail
        assert verify_password(wrong_password, hashed) is False

    @settings(max_examples=10, deadline=None)  # bcrypt is intentionally slow
    @given(password=password_strategy)
    def test_same_password_produces_different_hashes(self, password: str):
        """
        **Feature: openapi-showcase, Property 32: Password hashing**
        
        For any password, hashing it twice SHALL produce different hashes (due to salt).
        """
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Same password should produce different hashes (different salts)
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
