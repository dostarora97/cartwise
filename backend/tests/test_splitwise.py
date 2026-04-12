"""Unit tests for Splitwise service — feature toggle, payload building, audit flow."""

import pytest

from app.services.splitwise import (
    SplitwiseDisabledError,
    _build_expense_payload,
    _check_enabled,
    _payload_hash,
)

# --- Feature toggle ---


def test_check_enabled_raises_when_disabled(monkeypatch):
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=False))
    with pytest.raises(SplitwiseDisabledError):
        _check_enabled()


def test_check_enabled_passes_when_enabled(monkeypatch):
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))
    _check_enabled()  # Should not raise


def test_get_current_user_raises_when_disabled(monkeypatch):
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=False))
    from app.services.splitwise import get_current_user

    with pytest.raises(SplitwiseDisabledError):
        get_current_user()


# --- Payload building ---


def test_build_expense_payload_two_members():
    payload = _build_expense_payload(
        description="Groceries",
        cost=100.0,
        payer_sw_id=1,
        member_sw_ids=[1, 2],
    )

    assert payload["cost"] == "100.00"
    assert payload["description"] == "Groceries"
    assert payload["currency_code"] == "INR"

    # Payer paid everything
    assert payload["users__0__user_id"] == 1
    assert payload["users__0__paid_share"] == "100.00"
    assert payload["users__0__owed_share"] == "50.00"

    # Other member paid nothing
    assert payload["users__1__user_id"] == 2
    assert payload["users__1__paid_share"] == "0.00"
    assert payload["users__1__owed_share"] == "50.00"


def test_build_expense_payload_three_members():
    payload = _build_expense_payload(
        description="Split 3 ways",
        cost=100.0,
        payer_sw_id=1,
        member_sw_ids=[1, 2, 3],
    )

    shares = [float(payload[f"users__{i}__owed_share"]) for i in range(3)]
    assert sum(shares) == 100.0  # Shares sum to cost


def test_build_expense_payload_odd_amount():
    """Test rounding: 10 / 3 = 3.33... → shares must still sum to 10."""
    payload = _build_expense_payload(
        description="Odd split",
        cost=10.0,
        payer_sw_id=1,
        member_sw_ids=[1, 2, 3],
    )

    shares = [float(payload[f"users__{i}__owed_share"]) for i in range(3)]
    assert sum(shares) == 10.0


def test_build_expense_payload_single_member():
    payload = _build_expense_payload(
        description="Solo",
        cost=50.0,
        payer_sw_id=1,
        member_sw_ids=[1],
    )

    assert payload["users__0__paid_share"] == "50.00"
    assert payload["users__0__owed_share"] == "50.00"


def test_build_expense_payload_with_details():
    payload = _build_expense_payload(
        description="Test",
        cost=10.0,
        payer_sw_id=1,
        member_sw_ids=[1],
        details="Item 1\nItem 2",
    )

    assert payload["details"] == "Item 1\nItem 2"


def test_build_expense_payload_without_details():
    payload = _build_expense_payload(
        description="Test",
        cost=10.0,
        payer_sw_id=1,
        member_sw_ids=[1],
    )

    assert "details" not in payload


# --- Payload hash ---


def test_payload_hash_deterministic():
    p1 = {"cost": "100.00", "description": "test"}
    p2 = {"description": "test", "cost": "100.00"}  # Different order, same content

    assert _payload_hash(p1) == _payload_hash(p2)


def test_payload_hash_different_for_different_payloads():
    p1 = {"cost": "100.00"}
    p2 = {"cost": "200.00"}

    assert _payload_hash(p1) != _payload_hash(p2)


class _FakeSettings:
    def __init__(self, splitwise_enabled=False, api_key="test"):
        self.SPLITWISE_API_KEY = api_key
        self._enabled = splitwise_enabled

    def get(self, key, default=None):
        if key == "SPLITWISE_ENABLED":
            return self._enabled
        return default
