"""Tests for Splitwise OAuth flow and signed state helpers."""

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from app.routes.auth import _sign_state, _verify_state

AUTHLIB_PATH = "authlib.integrations.httpx_client.AsyncOAuth2Client"


class TestSignedState:
    """Unit tests for _sign_state / _verify_state helpers."""

    def test_roundtrip(self):
        user_id = "2376dc61-0e27-47e9-a117-d7a283515794"
        state = _sign_state(user_id, "random-nonce")
        assert _verify_state(state) == user_id

    def test_different_nonces_produce_different_states(self):
        user_id = "abc-123"
        s1 = _sign_state(user_id, "nonce1")
        s2 = _sign_state(user_id, "nonce2")
        assert s1 != s2
        assert _verify_state(s1) == user_id
        assert _verify_state(s2) == user_id

    def test_tampered_signature_rejected(self):
        state = _sign_state("user-id", "nonce")
        tampered = "0000000000000000" + state[16:]
        assert _verify_state(tampered) is None

    def test_tampered_payload_rejected(self):
        state = _sign_state("user-id", "nonce")
        sig, _ = state.split(".", 1)
        tampered = f"{sig}.attacker-id:nonce"
        assert _verify_state(tampered) is None

    def test_garbage_input_returns_none(self):
        assert _verify_state("") is None
        assert _verify_state("no-dot-here") is None
        assert _verify_state("a.b") is None  # no colon in payload

    def test_none_input_returns_none(self):
        assert _verify_state(None) is None  # type: ignore[arg-type]


class TestSplitwiseConnect:
    """Integration tests for POST /auth/splitwise/connect."""

    async def test_returns_authorize_url_and_redirect_uri(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        response = await client.post("/api/v1/auth/splitwise/connect", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "authorize_url" in data
        assert "redirect_uri" in data
        assert "/oauth/authorize" in data["authorize_url"]
        assert "state=" in data["authorize_url"]
        assert data["redirect_uri"].endswith("/auth/connect/splitwise")

    async def test_state_contains_user_id(self, client: AsyncClient, auth_headers: dict, test_user):
        response = await client.post("/api/v1/auth/splitwise/connect", headers=auth_headers)
        url = response.json()["authorize_url"]
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        state = parse_qs(parsed.query)["state"][0]
        assert _verify_state(state) == str(test_user.id)

    async def test_redirect_uri_in_authorize_url_matches_response(
        self, client: AsyncClient, auth_headers: dict, test_user
    ):
        response = await client.post("/api/v1/auth/splitwise/connect", headers=auth_headers)
        data = response.json()
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(data["authorize_url"])
        url_redirect_uri = parse_qs(parsed.query)["redirect_uri"][0]
        assert url_redirect_uri == data["redirect_uri"]

    async def test_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/splitwise/connect")
        assert response.status_code in (401, 403)


class TestSplitwiseExchange:
    """Integration tests for POST /auth/splitwise/exchange."""

    async def test_invalid_state_returns_400(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/splitwise/exchange",
            json={"code": "fake", "state": "garbage", "redirect_uri": "http://x/cb"},
        )
        assert response.status_code == 400
        assert "Invalid state" in response.json()["detail"]

    async def test_successful_exchange(self, client: AsyncClient, test_user, session):
        state = _sign_state(str(test_user.id), "test-nonce")

        mock_token_resp = {"access_token": "mock_token_abc", "token_type": "bearer"}
        mock_user_resp = {"user": {"id": 12345, "first_name": "Test", "last_name": "SW"}}

        instance = AsyncMock()
        instance.fetch_token = AsyncMock(return_value=mock_token_resp)
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = mock_user_resp
        instance.get = AsyncMock(return_value=mock_get_resp)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=instance)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(AUTHLIB_PATH, return_value=mock_ctx),
            patch("app.routes.auth.store_secret", new_callable=AsyncMock) as mock_vault,
        ):
            response = await client.post(
                "/api/v1/auth/splitwise/exchange",
                json={
                    "code": "real-code",
                    "state": state,
                    "redirect_uri": "http://localhost:3000/auth/splitwise/callback",
                },
            )

        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_vault.assert_called_once_with(
            session,
            f"splitwise_token:{test_user.id}",
            "mock_token_abc",
            f"Splitwise token for user {test_user.id}",
        )

    async def test_token_exchange_failure_returns_502(self, client: AsyncClient, test_user):
        state = _sign_state(str(test_user.id), "test-nonce")

        instance = AsyncMock()
        instance.fetch_token = AsyncMock(side_effect=Exception("network error"))

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=instance)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(AUTHLIB_PATH, return_value=mock_ctx):
            response = await client.post(
                "/api/v1/auth/splitwise/exchange",
                json={
                    "code": "bad-code",
                    "state": state,
                    "redirect_uri": "http://localhost:3000/auth/splitwise/callback",
                },
            )

        assert response.status_code == 502

    async def test_no_access_token_returns_502(self, client: AsyncClient, test_user):
        state = _sign_state(str(test_user.id), "test-nonce")

        instance = AsyncMock()
        instance.fetch_token = AsyncMock(return_value={"error": "invalid_grant"})

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=instance)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(AUTHLIB_PATH, return_value=mock_ctx):
            response = await client.post(
                "/api/v1/auth/splitwise/exchange",
                json={
                    "code": "expired-code",
                    "state": state,
                    "redirect_uri": "http://localhost:3000/auth/splitwise/callback",
                },
            )

        assert response.status_code == 502
