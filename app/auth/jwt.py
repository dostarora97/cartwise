"""
Supabase JWT validation.

Supabase Auth issues JWTs after OAuth login. Our backend validates them
using the project's JWT secret and extracts user information.

Supabase JWT claims:
  - sub: Supabase Auth user UUID
  - email: user's email
  - user_metadata: {name, avatar_url, provider, ...}
  - role: "authenticated" for logged-in users
"""

from dataclasses import dataclass

import jwt

from app.config import settings

ALGORITHM = "HS256"


@dataclass
class SupabaseUser:
    """Decoded user info from a Supabase JWT."""

    auth_id: str  # Supabase Auth UUID (sub claim)
    email: str
    name: str
    avatar_url: str | None
    provider: str


def decode_supabase_jwt(token: str) -> SupabaseUser | None:
    """Validate and decode a Supabase-issued JWT.

    Returns SupabaseUser if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            audience="authenticated",
        )
    except (jwt.InvalidTokenError, ValueError):  # fmt: skip
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
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=ALGORITHM)
