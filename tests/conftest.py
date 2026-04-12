import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force testing environment before importing app
os.environ["MEALSPLIT_ENV"] = "testing"

from app.auth.jwt import create_test_token
from app.config import settings
from app.database import get_session
from app.main import app
from app.models import Base
from app.models.user import User

engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=pool.NullPool)
test_async_session = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session() -> AsyncSession:
    async with test_async_session() as s:
        yield s


@pytest.fixture
async def client(session: AsyncSession) -> AsyncClient:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(session: AsyncSession) -> User:
    """Create a test user in the database."""
    user = User(
        email="test@example.com",
        name="Test User",
        oauth_provider="google",
        oauth_id="test-oauth-id",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Create auth headers with a Supabase-style JWT for the test user."""
    token = create_test_token(test_user.oauth_id, test_user.email)
    return {"Authorization": f"Bearer {token}"}
