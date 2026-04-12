# cartwise

Grocery cost splitting with meal planning.

[![CI](https://github.com/dostarora97/cartwise/actions/workflows/ci.yml/badge.svg)](https://github.com/dostarora97/cartwise/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/dostarora97/cartwise/graph/badge.svg)](https://codecov.io/gh/dostarora97/cartwise)

## Structure

```
backend/   — FastAPI API server (Python)
ui/        — Frontend (Next.js + React + Tailwind) — coming soon
```

## Quick start

```bash
git clone https://github.com/dostarora97/cartwise.git && cd cartwise

# Backend
cd backend
uv sync
docker compose up -d postgres postgres-test
cp .secrets.toml.example .secrets.toml  # fill in values
CARTWISE_ENV=development uv run alembic upgrade head
CARTWISE_ENV=development uv run uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs
