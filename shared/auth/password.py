"""Password hashing utilities using bcrypt.

Provides secure password hashing and verification functions.
"""

from passlib.context import CryptContext

# Configure passlib with bcrypt
# Using rounds=10 for balance between security and performance
# In production, consider rounds=12 for higher security
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        The bcrypt hash of the password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hash to verify against

    Returns:
        True if the password matches the hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)
