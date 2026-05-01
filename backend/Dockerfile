FROM us-central1-docker.pkg.dev/serverless-runtimes/google-24/runtimes/python314

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_CACHE_DIR=/tmp/.uv-cache
ENV UV_PYTHON_INSTALL_DIR=/tmp/.uv-python
ENV UV_PYTHON=python3

# Copy dependency files first for caching
COPY pyproject.toml uv.lock* ./

# Install production dependencies only
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "exec uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
