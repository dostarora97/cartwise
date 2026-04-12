# Contributing

## Quick start

```bash
# Prerequisites: Python 3.14, Docker, uv, mise (optional)
git clone https://github.com/dostarora97/mealsplit-backend.git && cd mealsplit-backend

# Install dependencies
uv sync

# Install git hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg

# Start PostgreSQL
docker compose up -d postgres postgres-test

# Copy secrets template and fill in values
cp .secrets.toml.example .secrets.toml

# Run migrations
MEALSPLIT_ENV=development uv run alembic upgrade head

# Verify everything works
uv run pytest --ignore=tests/test_integration.py -v
uv run ruff check .
```

## Development server

```bash
MEALSPLIT_ENV=development uv run uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

## Running tests

```bash
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
- Coverage must stay above 84%
- Follow the PR template

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full system design.
