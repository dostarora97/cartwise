from __future__ import annotations

from fastapi import HTTPException

from app.config import settings

from ..client import SupplierClient
from ..token import DecodedToken, decode_token
from .connector import ConnectorSupplier


def _lookup_registry(supplier: str) -> dict | None:
    configs = settings.IMPORT_SUPPLIERS
    return next((c for c in configs if c["id"] == supplier), None)


def resolve_supplier_client(token: str) -> tuple[SupplierClient, DecodedToken]:
    decoded = decode_token(token)
    if decoded is None:
        raise HTTPException(404, "Invalid supplier token")
    config = _lookup_registry(decoded.supplier)
    if config is None:
        raise HTTPException(404, "Unknown supplier")
    client = SupplierClient(
        url=config["url"],
        payload=decoded.payload,
        internal_secret=settings.INTERNAL_API_SECRET,
    )
    return client, decoded


__all__ = ["ConnectorSupplier", "resolve_supplier_client"]
