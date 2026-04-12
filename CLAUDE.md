# mealsplit-backend

A FastAPI backend for grocery cost splitting with meal planning.
Users create menu items (recipes with ingredients), build meal plans,
and when groceries are bought, the system splits costs based on who
eats what — using a bipartite graph model for minimum transactions.

## Orientation

Start here to understand the project:

- @docs/architecture.md — data flow, DB schema, auth, AI layer, config, design decisions
- @CONTRIBUTING.md — prerequisites, quick start, workflow

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
| `app/services/` | Business logic (extract, classify, correlate, split, storage) |

## Common commands

```bash
# Dev server
MEALSPLIT_ENV=development uv run uvicorn app.main:app --reload --port 8000

# Unit tests (fast, no Ollama)
uv run pytest --ignore=tests/test_integration.py -v

# Integration tests (needs Ollama + Docker postgres)
uv run pytest tests/test_integration.py -v -s

# Lint
uv run ruff check . && uv run ruff format --check .

# Migrations
MEALSPLIT_ENV=development uv run alembic revision --autogenerate -m "description"
MEALSPLIT_ENV=development uv run alembic upgrade head
```

## Conventions

- Async everywhere (FastAPI, SQLAlchemy, LiteLLM). Sync code (pdfplumber) via `asyncio.to_thread()`.
- SQLAlchemy 2.0 style: `Mapped[]`, `mapped_column()`, `from __future__ import annotations`.
- Pydantic v2: `ConfigDict(from_attributes=True)`, separate Create/Update/Response schemas.
- Config via Dynaconf: `settings.toml` (committed) + `.secrets.toml` (gitignored).
- Conventional Commits enforced by pre-commit hook.
- Tests: pytest + httpx + pytest-asyncio. Mock LLM via `app.ai.client.generate`.
