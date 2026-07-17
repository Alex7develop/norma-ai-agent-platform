"""Password hashing and signed token primitives."""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


class AuthenticationError(ValueError):
    """Raised when credentials or signed claims are invalid."""


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: UUID
    token_type: str
    expires_at: datetime
    session_id: UUID | None = None


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_token(
    *,
    user_id: UUID,
    token_type: str,
    lifetime: timedelta,
    session_id: UUID | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": str(user_id),
        "type": token_type,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + lifetime,
    }
    if session_id is not None:
        payload["sid"] = str(session_id)
    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, *, expected_type: str) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
        if payload.get("type") != expected_type:
            raise AuthenticationError("Token type is invalid")
        return TokenClaims(
            user_id=UUID(payload["sub"]),
            token_type=payload["type"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            session_id=UUID(payload["sid"]) if payload.get("sid") else None,
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError("Token is invalid or expired") from exc


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
