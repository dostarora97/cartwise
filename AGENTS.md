## Cursor Cloud specific instructions

### Services overview

| Service | How to start | Port |
|---|---|---|
| FastAPI dev server | `cd backend && CARTWISE_ENV=development uv run uvicorn app.main:app --reload --port 8000` | 8000 |
| PostgreSQL (dev) | `cd backend && sudo docker compose up -d postgres` | 5432 |
| PostgreSQL (test) | `cd backend && sudo docker compose up -d postgres-test` | 5433 |

### Prerequisites (already installed in snapshot)

- Python 3.14 via deadsnakes PPA (`python3.14`)
- `uv` package manager (`~/.local/bin/uv`)
- Docker (with `fuse-overlayfs` storage driver and `iptables-legacy` for nested container support)

### Startup sequence

1. Start Docker daemon: `sudo dockerd &>/tmp/dockerd.log &` (wait ~3s)
2. Start PostgreSQL containers: `cd /workspace/backend && sudo docker compose up -d postgres postgres-test`
3. Wait for healthy: `sudo docker compose ps` (both should show "healthy")
4. Run migrations: `cd /workspace/backend && CARTWISE_ENV=development uv run alembic upgrade head`
5. Start dev server: `cd /workspace/backend && CARTWISE_ENV=development uv run uvicorn app.main:app --reload --port 8000`
6. Swagger UI at http://localhost:8000/docs

### Key caveats

- **PATH**: `uv` is installed at `~/.local/bin/uv`. Ensure `$HOME/.local/bin` is on PATH.
- **Docker nested containers**: The VM runs inside a Docker container in Firecracker. Docker requires `fuse-overlayfs` storage driver and `iptables-legacy`. Both are configured in `/etc/docker/daemon.json` and via `update-alternatives`.
- **`.secrets.toml`**: Must exist (gitignored). Copy from `.secrets.toml.example`. For local dev, the development `SUPABASE_*` values can be placeholders — `DEBUG=true` enables `POST /auth/dev-login` which bypasses real Supabase auth.
- **Trailing slashes**: FastAPI routes in this project require trailing slashes (e.g. `/api/v1/menu-items/`). Requests without trailing slashes return 307 redirects.
- **Unit tests** don't need Ollama; LLM calls are mocked. Run with: `uv run pytest --ignore=tests/test_integration.py -v`
- **Integration tests** require Ollama with `qwen2.5:3b` model running on port 11434. These are typically skipped in Cloud Agent environments.
- Standard commands for lint, test, build, and run are documented in `CLAUDE.md` and `CONTRIBUTING.md`.
