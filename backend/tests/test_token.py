from __future__ import annotations

import base64
import json

from app.services.importer.token import DecodedToken, decode_token, encode_token


class TestDecodeToken:
    def test_valid_token(self):
        inner = json.dumps({"supplier": "cartwise", "payload": "abc123"})
        token = base64.urlsafe_b64encode(inner.encode()).rstrip(b"=").decode()

        result = decode_token(token)

        assert result == DecodedToken(supplier="cartwise", payload="abc123")

    def test_roundtrip(self):
        token = encode_token("cartwise", "eyJmb28iOiJiYXIifQ")
        result = decode_token(token)

        assert result is not None
        assert result.supplier == "cartwise"
        assert result.payload == "eyJmb28iOiJiYXIifQ"

    def test_invalid_base64(self):
        assert decode_token("!!!invalid!!!") is None

    def test_invalid_json(self):
        token = base64.urlsafe_b64encode(b"not json").rstrip(b"=").decode()
        assert decode_token(token) is None

    def test_missing_supplier(self):
        inner = json.dumps({"payload": "abc"})
        token = base64.urlsafe_b64encode(inner.encode()).rstrip(b"=").decode()
        assert decode_token(token) is None

    def test_missing_payload(self):
        inner = json.dumps({"supplier": "x"})
        token = base64.urlsafe_b64encode(inner.encode()).rstrip(b"=").decode()
        assert decode_token(token) is None

    def test_non_string_values(self):
        inner = json.dumps({"supplier": 123, "payload": "abc"})
        token = base64.urlsafe_b64encode(inner.encode()).rstrip(b"=").decode()
        assert decode_token(token) is None

    def test_empty_string(self):
        assert decode_token("") is None


class TestEncodeToken:
    def test_produces_url_safe_string(self):
        token = encode_token("cartwise", "payload123")
        assert "+" not in token
        assert "/" not in token
        assert "=" not in token

    def test_decodable(self):
        token = encode_token("myapp", "opaque-data")
        raw = base64.urlsafe_b64decode(token + "==")
        data = json.loads(raw)
        assert data["supplier"] == "myapp"
        assert data["payload"] == "opaque-data"
