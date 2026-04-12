# cartwise backend

FastAPI backend for grocery cost splitting with meal planning.

## Key files

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI app, middleware, routers |
| `app/config.py` | Dynaconf settings |
| `app/database.py` | Async SQLAlchemy engine + session |
| `app/ai/client.py` | LiteLLM wrapper for LLM calls |
| `app/auth/jwt.py` | Supabase JWT validation |
| `app/auth/dependencies.py` | `CurrentUser` auth dependency |
| `app/models/` | SQLAlchemy ORM models |
| `app/schemas/` | Pydantic request/response schemas |
| `app/routes/` | API endpoint handlers |
| `app/services/` | Business logic (extract, classify, correlate, split, splitwise, storage) |

## Commands (run from `backend/`)

```bash
# Dev server
CARTWISE_ENV=development uv run uvicorn app.main:app --reload --port 8000

# Mock Splitwise
uv run uvicorn mock.splitwise:app --port 8001

# Unit tests
uv run pytest --ignore=tests/test_integration.py -v

# Integration tests (needs Ollama + Docker postgres)
uv run pytest tests/test_integration.py -v -s

# Lint
uv run ruff check . && uv run ruff format --check .

# Migrations
CARTWISE_ENV=development uv run alembic revision --autogenerate -m "description"
CARTWISE_ENV=development uv run alembic upgrade head
```

## Conventions

- Async everywhere (FastAPI, SQLAlchemy, LiteLLM). Sync code (pdfplumber) via `asyncio.to_thread()`.
- SQLAlchemy 2.0 style: `Mapped[]`, `mapped_column()`, `from __future__ import annotations`.
- Pydantic v2: `ConfigDict(from_attributes=True)`, separate Create/Update/Response schemas.
- Config via Dynaconf: `settings.toml` (committed) + `.secrets.toml` (gitignored).
- Conventional Commits enforced by pre-commit hook.
- Tests: pytest + httpx + pytest-asyncio. Mock LLM via `app.ai.client.generate`.
