"""Unit tests for JWT validation and auth dependencies."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.auth.jwt import ALGORITHM, SupabaseUser, create_test_token, decode_supabase_jwt
from app.config import settings


def test_decode_valid_token():
    oauth_id = f"test-{uuid.uuid4()}"
    token = create_test_token(oauth_id, "user@test.com")
    result = decode_supabase_jwt(token)
    assert result is not None
    assert result.auth_id == oauth_id
    assert result.email == "user@test.com"
    assert isinstance(result, SupabaseUser)


def test_decode_expired_token():
    payload = {
        "sub": "test-id",
        "email": "expired@test.com",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "user_metadata": {},
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=ALGORITHM)
    assert decode_supabase_jwt(token) is None


def test_decode_wrong_signature():
    payload = {
        "sub": "test-id",
        "email": "wrong@test.com",
        "role": "authenticated",
        "aud": "authenticated",
        "user_metadata": {},
    }
    token = jwt.encode(payload, "wrong-secret-key-that-does-not-match!", algorithm=ALGORITHM)
    assert decode_supabase_jwt(token) is None


def test_decode_malformed_token():
    assert decode_supabase_jwt("not.a.jwt") is None
    assert decode_supabase_jwt("") is None
    assert decode_supabase_jwt("garbage") is None


def test_decode_missing_sub():
    payload = {
        "email": "nosub@test.com",
        "role": "authenticated",
        "aud": "authenticated",
        "user_metadata": {},
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=ALGORITHM)
    assert decode_supabase_jwt(token) is None


def test_decode_missing_email():
    payload = {
        "sub": "has-sub-no-email",
        "role": "authenticated",
        "aud": "authenticated",
        "user_metadata": {},
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=ALGORITHM)
    assert decode_supabase_jwt(token) is None


def test_decode_extracts_user_metadata():
    payload = {
        "sub": "meta-test",
        "email": "meta@test.com",
        "role": "authenticated",
        "aud": "authenticated",
        "user_metadata": {
            "full_name": "Meta User",
            "avatar_url": "https://example.com/avatar.jpg",
            "iss": "github",
        },
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=ALGORITHM)
    result = decode_supabase_jwt(token)
    assert result is not None
    assert result.name == "Meta User"
    assert result.avatar_url == "https://example.com/avatar.jpg"
    assert result.provider == "github"


def test_decode_falls_back_to_email_for_name():
    """When user_metadata has no name, email is used as fallback."""
    payload = {
        "sub": "noname-test",
        "email": "noname@test.com",
        "role": "authenticated",
        "aud": "authenticated",
        "user_metadata": {},
    }
    token = jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm=ALGORITHM)
    result = decode_supabase_jwt(token)
    assert result is not None
    assert result.name == "noname@test.com"


def test_create_test_token_roundtrips():
    oauth_id = "roundtrip-test"
    token = create_test_token(oauth_id, "rt@test.com")
    result = decode_supabase_jwt(token)
    assert result is not None
    assert result.auth_id == oauth_id
    assert result.email == "rt@test.com"
