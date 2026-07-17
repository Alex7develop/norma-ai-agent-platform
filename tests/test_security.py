"""Security primitive tests."""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.security import (
    AuthenticationError,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("secure-password-12")
    assert hashed != "secure-password-12"
    assert verify_password("secure-password-12", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip() -> None:
    user_id = uuid4()
    token = create_token(
        user_id=user_id,
        token_type="access",
        lifetime=timedelta(minutes=5),
    )
    claims = decode_token(token, expected_type="access")
    assert claims.user_id == user_id
    assert claims.token_type == "access"


def test_token_type_mismatch_is_rejected() -> None:
    token = create_token(
        user_id=uuid4(),
        token_type="access",
        lifetime=timedelta(minutes=5),
    )
    with pytest.raises(AuthenticationError):
        decode_token(token, expected_type="refresh")
