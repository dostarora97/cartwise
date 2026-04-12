# mealsplit-backend

Grocery cost splitting with meal planning — FastAPI backend.

[![CI](https://github.com/dostarora97/mealsplit-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/dostarora97/mealsplit-backend/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/dostarora97/mealsplit-backend/graph/badge.svg)](https://codecov.io/gh/dostarora97/mealsplit-backend)

## Quick start

```bash
# Prerequisites: Docker, uv, Python 3.14

# Start PostgreSQL
docker compose up -d postgres postgres-test

# Install deps
uv sync

# Run migrations
MEALSPLIT_ENV=development uv run alembic upgrade head

# Start server
MEALSPLIT_ENV=development uv run uvicorn app.main:app --reload --port 8000

# Run tests (unit — no Ollama needed)
uv run pytest --ignore=tests/test_integration.py -v

# Run tests (integration — needs Ollama + qwen2.5:3b)
uv run pytest tests/test_integration.py -v -s

# Lint
uv run ruff check . && uv run ruff format --check .
```

Swagger UI: http://localhost:8000/docs
