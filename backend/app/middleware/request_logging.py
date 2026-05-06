"""
Request logging middleware.

Adds a request ID to every request and logs request/response details.
Logs mutation request/response bodies for observability.
"""

import time

import structlog
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging import generate_request_id

logger = structlog.get_logger()

_MAX_BODY_BYTES = 10_240  # 10KB
_MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _truncate_body(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return f"<binary {len(raw)} bytes>"
    if len(raw) > _MAX_BODY_BYTES:
        return text[:_MAX_BODY_BYTES] + f"... (truncated, total {len(raw)} bytes)"
    return text


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = generate_request_id()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        current_span = trace.get_current_span()
        if current_span.is_recording():
            current_span.set_attribute("app.request_id", request_id)

        if request.method in _MUTATION_METHODS:
            content_type = request.headers.get("content-type", "")
            if "multipart" in content_type:
                logger.info(
                    "request_body",
                    body_type="multipart",
                    content_type=content_type,
                    content_length=request.headers.get("content-length"),
                )
            else:
                body = await request.body()
                if body:
                    logger.info(
                        "request_body",
                        body_type="json",
                        body=_truncate_body(body),
                    )

        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        if request.method in _MUTATION_METHODS and hasattr(response, "body_iterator"):
            chunks = []
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    chunks.append(chunk.encode("utf-8"))
                else:
                    chunks.append(chunk)
            response_bytes = b"".join(chunks)
            if response_bytes:
                logger.info("response_body", body=_truncate_body(response_bytes))

            async def _body_gen():
                yield response_bytes

            response.body_iterator = _body_gen()

        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
