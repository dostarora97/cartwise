#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Starting Supabase local stack..."
supabase start

echo ""
echo "==> Creating test database..."
psql "postgresql://postgres:postgres@localhost:54322/postgres" \
  -c "CREATE DATABASE cartwise_test;" 2>/dev/null || echo "    (already exists)"

echo ""
echo "==> Running Alembic migrations (development)..."
CARTWISE_ENV=development uv run alembic upgrade head

echo ""
echo "==> Running Alembic migrations (testing)..."
CARTWISE_ENV=testing uv run alembic upgrade head

echo ""
echo "==> Done! Local stack is ready."
echo ""
echo "Supabase Studio:  http://127.0.0.1:54323"
echo "Supabase API:     http://127.0.0.1:54321"
echo "Postgres:         postgresql://postgres:postgres@localhost:54322/postgres"
echo ""
echo "Start backend:    CARTWISE_ENV=development uv run uvicorn app.main:app --reload --port 8000"
echo "Start frontend:   cd ../ui && bun dev"
