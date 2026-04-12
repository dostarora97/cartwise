# Contributing

## Quick start

```bash
# Prerequisites: Python 3.14, Docker, uv, mise (optional)
git clone https://github.com/dostarora97/cartwise.git && cd cartwise

# Backend setup
cd backend

# Install dependencies
uv sync

# Install git hooks (must run after uv sync, from repo root)
cd .. && uv run --project backend pre-commit install && uv run --project backend pre-commit install --hook-type commit-msg && cd backend

# Start PostgreSQL
docker compose up -d postgres postgres-test

# Copy secrets template and fill in values
cp .secrets.toml.example .secrets.toml

# Run migrations
CARTWISE_ENV=development uv run alembic upgrade head

# Verify everything works
uv run pytest --ignore=tests/test_integration.py -v
uv run ruff check .
```

## Development server

```bash
cd backend
CARTWISE_ENV=development uv run uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

## Running tests

```bash
cd backend

# Unit tests (fast, no Ollama needed)
uv run pytest --ignore=tests/test_integration.py -v

# Integration tests (requires Ollama with qwen2.5:3b)
uv run pytest tests/test_integration.py -v -s

# With coverage report
uv run pytest --ignore=tests/test_integration.py --cov=app --cov-report=term-missing
```

## Commit messages

This project uses [Conventional Commits](https://conventionalcommits.org).
The pre-commit hook enforces the format:

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`, `revert`

## Pull requests

- Branch from `main`
- CI (lint + test) must pass
- Follow the PR template

## Architecture

See [backend/docs/architecture.md](backend/docs/architecture.md) for the full system design.
