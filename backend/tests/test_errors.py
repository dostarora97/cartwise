"""Tests for ProblemDetailError handling."""

from httpx import AsyncClient

from app.errors import ProblemDetailError


async def test_problem_detail_response(client: AsyncClient, auth_headers: dict, test_user):
    """ProblemDetailError returns application/problem+json with correct shape."""
    from fastapi import APIRouter

    from app.main import app

    # Add a temporary test route that raises ProblemDetailError
    test_router = APIRouter()

    @test_router.get("/test-problem-detail")
    async def _raise_problem():
        raise ProblemDetailError(
            type="tag:cartwise.app,2026:problem/test-error",
            title="Test Error",
            status=422,
            detail="This is a test",
            provider="test",
        )

    app.include_router(test_router, prefix="/api/v1")

    resp = await client.get("/api/v1/test-problem-detail", headers=auth_headers)
    assert resp.status_code == 422
    assert resp.headers["content-type"] == "application/problem+json"
    body = resp.json()
    assert body["type"] == "tag:cartwise.app,2026:problem/test-error"
    assert body["title"] == "Test Error"
    assert body["status"] == 422
    assert body["detail"] == "This is a test"
    assert body["provider"] == "test"


def test_problem_detail_to_dict():
    """ProblemDetailError.to_dict() produces correct structure."""
    err = ProblemDetailError(
        type="tag:cartwise.app,2026:problem/auth-required",
        title="Auth Required",
        status=422,
        detail="Reconnect please",
        provider="swiggy",
        connect_url="/api/v1/auth/swiggy/connect",
    )
    d = err.to_dict()
    assert d == {
        "type": "tag:cartwise.app,2026:problem/auth-required",
        "title": "Auth Required",
        "status": 422,
        "detail": "Reconnect please",
        "provider": "swiggy",
        "connect_url": "/api/v1/auth/swiggy/connect",
    }
