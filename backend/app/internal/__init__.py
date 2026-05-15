from __future__ import annotations

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

internal_app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@internal_app.middleware("http")
async def reject_external(request: Request, call_next):
    if request.headers.get("X-Internal-Secret") != settings.INTERNAL_API_SECRET:
        return Response(status_code=404)
    return await call_next(request)


from app.internal.export import router  # noqa: E402

internal_app.include_router(router)
