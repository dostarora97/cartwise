from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.logging import setup_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routes import auth, meal_plans, menu_items, orders, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title="Splitwise Backend",
    description="Grocery cost splitting with meal planning",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (order matters — outermost first)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers — all under /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(menu_items.router, prefix="/api/v1")
app.include_router(meal_plans.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
