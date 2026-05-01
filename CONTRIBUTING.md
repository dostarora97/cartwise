# Contributing

## Prerequisites

- Python 3.14
- Docker (for Supabase local stack)
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/) (git hooks + frontend)
- [Supabase CLI](https://supabase.com/docs/guides/cli)

## Quick start

```bash
git clone https://github.com/dostarora97/cartwise.git && cd cartwise

# Install git hooks (from repo root — requires Bun)
bun install

# Backend setup
cd backend

# Install dependencies
uv sync

# Copy secrets template and fill in values
cp .secrets.toml.example .secrets.toml

# Copy Google OAuth secrets for local Supabase Auth
cp supabase/.env.example supabase/.env
# Fill in GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET

# Start local stack (Supabase + migrations)
bash scripts/setup-local.sh

# Note the anon key and JWT secret from the supabase start output
# and add them to .secrets.toml

# Verify everything works
uv run pytest --ignore=tests/test_integration.py -v
uv run ruff check .
```

## Google OAuth (local)

The local Supabase stack uses real Google OAuth — same flow as production.

One-time setup:

1. Go to [Google Cloud Console](https://console.cloud.google.com/auth/clients) → OAuth 2.0 Client IDs
2. Add `http://127.0.0.1:54321/auth/v1/callback` as an authorized redirect URI
3. Copy the Client ID and Secret into `backend/supabase/.env`
4. Restart Supabase: `supabase stop && supabase start` (from `backend/`)

## Development server

```bash
cd backend
CARTWISE_ENV=development uv run uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

Frontend (separate terminal):
```bash
cd ui
bun dev
```

App: http://localhost:3000

## Local services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Supabase Studio | http://127.0.0.1:54323 |
| Supabase API | http://127.0.0.1:54321 |
| Postgres | postgresql://postgres:postgres@localhost:54322/postgres |
| Inbucket (email) | http://127.0.0.1:54324 |

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

## Stopping the local stack

```bash
cd backend
supabase stop           # preserves data
supabase stop --no-backup  # wipes all data
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
