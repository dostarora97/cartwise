"""
Global exception handler.

Catches unhandled exceptions and returns consistent JSON error responses.
"""

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from httpx import ConnectError, TimeoutException
from pdfminer.pdfparser import PDFSyntaxError
from sqlalchemy.exc import SQLAlchemyError

logger = structlog.get_logger()


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": "http_error"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("database_error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "A database error occurred", "error_code": "database_error"},
        )

    @app.exception_handler(ConnectError)
    async def ollama_connect_error_handler(request: Request, exc: ConnectError) -> JSONResponse:
        logger.error("ollama_unreachable", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={
                "detail": "LLM service (Ollama) is not reachable",
                "error_code": "ollama_unreachable",
            },
        )

    @app.exception_handler(TimeoutException)
    async def ollama_timeout_handler(request: Request, exc: TimeoutException) -> JSONResponse:
        logger.error("ollama_timeout", error=str(exc))
        return JSONResponse(
            status_code=504,
            content={
                "detail": "LLM service (Ollama) timed out",
                "error_code": "ollama_timeout",
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning("validation_error", error=str(exc))
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_code": "validation_error"},
        )

    @app.exception_handler(PDFSyntaxError)
    async def pdf_error_handler(request: Request, exc: PDFSyntaxError) -> JSONResponse:
        logger.error("pdf_parse_error", error=str(exc))
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Failed to parse the uploaded PDF",
                "error_code": "pdf_parse_error",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", error=str(exc), exc_type=type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred", "error_code": "internal_error"},
        )
