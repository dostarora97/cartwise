from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.internal import internal_app
from app.logging import setup_logging
from app.middleware.error_handler import register_error_handlers
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routes import auth, imports, meal_plans, menu_items, orders, users
from app.services.seed import reconcile_fixtures
from app.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    setup_tracing(app)
    await reconcile_fixtures()
    yield


app = FastAPI(
    title="CartWise Backend",
    description="Grocery cost splitting with meal planning",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — last added runs first)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Trace-ID"],
)

# Dev-only: slow down API responses to test loading states
if settings.DEBUG:
    import asyncio

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    DEV_DELAY_MS = 0

    class SlowMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            if DEV_DELAY_MS and request.url.path != "/health":
                await asyncio.sleep(DEV_DELAY_MS / 1000)
            return await call_next(request)

    app.add_middleware(SlowMiddleware)

# Error handlers
register_error_handlers(app)

# Routers — all under /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(menu_items.router, prefix="/api/v1")
app.include_router(meal_plans.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(imports.router, prefix="/api/v1")

app.mount("/internal", internal_app)


@app.get("/health")
async def health():
    return {"status": "ok"}
