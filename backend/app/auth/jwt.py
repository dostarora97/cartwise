"""
Supabase JWT validation.

Supabase Auth issues JWTs after OAuth login. Our backend validates them
using JWKS (ES256) for production Supabase tokens, or the legacy shared
secret (HS256) for dev/test tokens.

Supabase JWT claims:
  - sub: Supabase Auth user UUID
  - email: user's email
  - user_metadata: {name, avatar_url, provider, ...}
  - role: "authenticated" for logged-in users
"""

from dataclasses import dataclass
from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.config import settings

HS256 = "HS256"


@dataclass
class SupabaseUser:
    """Decoded user info from a Supabase JWT."""

    auth_id: str  # Supabase Auth UUID (sub claim)
    email: str
    name: str
    avatar_url: str | None
    provider: str


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient | None:
    """Get a PyJWKClient for the Supabase JWKS endpoint. Cached."""
    supabase_url = settings.get("SUPABASE_URL", "")
    if not supabase_url or "supabase.co" not in supabase_url:
        return None
    return PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json")


def _decode_with_jwks(token: str) -> dict | None:
    """Try to decode using JWKS (ES256)."""
    jwks_client = _get_jwks_client()
    if not jwks_client:
        return None
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except (jwt.InvalidTokenError, jwt.exceptions.PyJWKClientError, ValueError, KeyError):  # fmt: skip
        return None


def _decode_with_secret(token: str) -> dict | None:
    """Try to decode using legacy HS256 shared secret."""
    try:
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[HS256],
            audience="authenticated",
        )
    except (jwt.InvalidTokenError, ValueError):  # fmt: skip
        return None


def decode_supabase_jwt(token: str) -> SupabaseUser | None:
    """Validate and decode a Supabase-issued JWT.

    Tries ES256 (JWKS) first, falls back to HS256 (shared secret).
    Returns SupabaseUser if valid, None otherwise.
    """
    payload = _decode_with_jwks(token) or _decode_with_secret(token)
    if payload is None:
        return None

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        return None

    user_metadata = payload.get("user_metadata", {})

    return SupabaseUser(
        auth_id=sub,
        email=email,
        name=user_metadata.get("full_name") or user_metadata.get("name") or email,
        avatar_url=user_metadata.get("avatar_url"),
        provider=user_metadata.get("iss", "unknown"),
    )


def create_test_token(oauth_id: str, email: str = "test@example.com") -> str:
    """Create a JWT for testing purposes. NOT for production."""
    payload = {
        "sub": oauth_id,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "user_metadata": {"full_name": "Test User"},
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=HS256)
