from __future__ import annotations

import base64
import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecodedToken:
    supplier: str
    payload: str


def decode_token(token: str) -> DecodedToken | None:
    try:
        raw = base64.urlsafe_b64decode(token + "==")
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):  # fmt: skip
        return None

    if not isinstance(data, dict):
        return None
    supplier = data.get("supplier")
    payload = data.get("payload")
    if not isinstance(supplier, str) or not isinstance(payload, str):
        return None
    return DecodedToken(supplier=supplier, payload=payload)


def encode_token(supplier: str, payload: str) -> str:
    data = json.dumps({"supplier": supplier, "payload": payload}, separators=(",", ":"))
    return base64.urlsafe_b64encode(data.encode()).rstrip(b"=").decode()
