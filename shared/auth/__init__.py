"""Authentication utilities.

Provides JWT handling, password hashing, and FastAPI dependencies.
"""

from shared.auth.dependencies import (
    AuthenticationError,
    CurrentUserID,
    OptionalToken,
    OptionalUserID,
    RequiredToken,
    get_current_user_id,
    get_optional_token_payload,
    get_optional_user_id,
    get_token_payload,
    security_scheme,
)
from shared.auth.jwt import (
    TokenBlocklist,
    TokenPair,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    get_token_jti,
)
from shared.auth.password import hash_password, verify_password

__all__ = [
    # JWT utilities
    "TokenPayload",
    "TokenPair",
    "TokenBlocklist",
    "create_access_token",
    "create_refresh_token",
    "create_token_pair",
    "decode_token",
    "get_token_jti",
    # Password utilities
    "hash_password",
    "verify_password",
    # Dependencies
    "AuthenticationError",
    "security_scheme",
    "get_token_payload",
    "get_optional_token_payload",
    "get_current_user_id",
    "get_optional_user_id",
    "CurrentUserID",
    "OptionalUserID",
    "RequiredToken",
    "OptionalToken",
]
