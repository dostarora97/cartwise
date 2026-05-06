"""Unit tests for Splitwise service — feature toggle, payload building, audit flow."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.splitwise_audit import SplitwiseAuditLog
from app.models.user import User
from app.services.splitwise import (
    SplitwiseDisabledError,
    _build_expense_payload,
    _check_enabled,
    _headers,
    _payload_hash,
    create_expense_audited,
    delete_expense_audited,
    get_audit_log,
    get_current_user,
    get_friends,
    get_groups,
    push_splits_audited,
    rollback_order_expenses,
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
    def __init__(self, splitwise_enabled=False, api_key="test", base_url="http://mock"):
        self.SPLITWISE_API_KEY = api_key
        self.SPLITWISE_BASE_URL = base_url
        self._enabled = splitwise_enabled

    def get(self, key, default=None):
        if key == "SPLITWISE_ENABLED":
            return self._enabled
        if key == "SPLITWISE_BASE_URL":
            return self.SPLITWISE_BASE_URL
        if key == "SPLITWISE_API_KEY":
            return self.SPLITWISE_API_KEY
        return default


# --- _headers() ---


def test_headers_with_explicit_token(monkeypatch):
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))
    h = _headers("my-token")
    assert h == {"Authorization": "Bearer my-token"}


def test_headers_fallback_to_settings(monkeypatch):
    monkeypatch.setattr(
        "app.services.splitwise.settings",
        _FakeSettings(splitwise_enabled=True, api_key="settings-key"),
    )
    h = _headers(None)
    assert h == {"Authorization": "Bearer settings-key"}


def test_headers_raises_when_no_token(monkeypatch):
    monkeypatch.setattr(
        "app.services.splitwise.settings",
        _FakeSettings(splitwise_enabled=True, api_key=""),
    )
    with pytest.raises(SplitwiseDisabledError, match="No Splitwise token"):
        _headers(None)


# --- Read-only operations (get_current_user, get_friends, get_groups) ---


def test_get_current_user_success(monkeypatch):
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"user": {"id": 1, "first_name": "Alice"}}
    mock_http = MagicMock()
    mock_http.get.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    result = get_current_user()
    assert result == {"id": 1, "first_name": "Alice"}
    mock_http.get.assert_called_once()


def test_get_friends_success(monkeypatch):
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"friends": [{"id": 2, "first_name": "Bob"}]}
    mock_http = MagicMock()
    mock_http.get.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    result = get_friends()
    assert result == [{"id": 2, "first_name": "Bob"}]


def test_get_groups_success(monkeypatch):
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"groups": [{"id": 10, "name": "House"}]}
    mock_http = MagicMock()
    mock_http.get.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    result = get_groups()
    assert result == [{"id": 10, "name": "House"}]


# --- _base_url() ---


def test_base_url_raises_when_empty(monkeypatch):
    from app.services.splitwise import _base_url

    monkeypatch.setattr(
        "app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True, base_url="")
    )
    with pytest.raises(SplitwiseDisabledError, match="SPLITWISE_BASE_URL"):
        _base_url()


# --- Audited write operations (DB-backed) ---


@pytest.fixture
async def order_with_user(session: AsyncSession):
    """Create a user and an order for audit tests."""
    user = User(
        email="sw-test@example.com",
        name="SW Test",
        oauth_provider="google",
        oauth_id="sw-test-oauth",
        splitwise_user_id=99001,
    )
    session.add(user)
    await session.flush()

    order = Order(paid_by=user.id, status="draft")
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order, user


async def test_create_expense_audited_success(session: AsyncSession, order_with_user, monkeypatch):
    """create_expense_audited creates audit row, calls API, marks success."""
    order, _user = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"expenses": [{"id": 5001}], "errors": []}
    mock_resp.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.post.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    audit = await create_expense_audited(
        session=session,
        description="Groceries",
        cost=100.0,
        payer_sw_id=99001,
        member_sw_ids=[99001, 99002],
        order_id=order.id,
        token="fake-token",
    )

    assert audit.status == "success"
    assert audit.splitwise_expense_id == 5001
    assert audit.action == "create_expense"
    assert audit.order_id == order.id


async def test_create_expense_audited_api_errors(
    session: AsyncSession, order_with_user, monkeypatch
):
    """create_expense_audited marks failed when API returns errors."""
    order, _ = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"expenses": [], "errors": ["Invalid user"]}
    mock_resp.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.post.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    audit = await create_expense_audited(
        session=session,
        description="Test",
        cost=50.0,
        payer_sw_id=99001,
        member_sw_ids=[99001],
        order_id=order.id,
        token="fake-token",
    )

    assert audit.status == "failed"
    assert "Invalid user" in audit.error_message


async def test_create_expense_audited_http_exception(
    session: AsyncSession, order_with_user, monkeypatch
):
    """create_expense_audited marks failed on network error."""
    order, _ = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    mock_http = MagicMock()
    mock_http.post.side_effect = ConnectionError("timeout")
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    audit = await create_expense_audited(
        session=session,
        description="Test",
        cost=25.0,
        payer_sw_id=99001,
        member_sw_ids=[99001],
        order_id=order.id,
        token="fake-token",
    )

    assert audit.status == "failed"
    assert "timeout" in audit.error_message


async def test_create_expense_audited_idempotent(
    session: AsyncSession, order_with_user, monkeypatch
):
    """create_expense_audited skips duplicate if same payload already succeeded."""
    order, _ = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"expenses": [{"id": 6001}], "errors": []}
    mock_resp.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.post.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    # First call
    audit1 = await create_expense_audited(
        session=session,
        description="Groceries",
        cost=100.0,
        payer_sw_id=99001,
        member_sw_ids=[99001, 99002],
        order_id=order.id,
        token="fake-token",
    )
    assert audit1.status == "success"

    # Second call with same params — should return existing row, not call API again
    mock_http.post.reset_mock()
    audit2 = await create_expense_audited(
        session=session,
        description="Groceries",
        cost=100.0,
        payer_sw_id=99001,
        member_sw_ids=[99001, 99002],
        order_id=order.id,
        token="fake-token",
    )
    assert audit2.id == audit1.id
    mock_http.post.assert_not_called()


async def test_delete_expense_audited_success(session: AsyncSession, order_with_user, monkeypatch):
    """delete_expense_audited creates audit row and marks success."""
    order, _ = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": True}
    mock_resp.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.post.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    audit = await delete_expense_audited(
        session=session,
        splitwise_expense_id=5001,
        order_id=order.id,
        token="fake-token",
    )

    assert audit.status == "success"
    assert audit.action == "delete_expense"
    assert audit.splitwise_expense_id == 5001


async def test_delete_expense_audited_failure(session: AsyncSession, order_with_user, monkeypatch):
    """delete_expense_audited marks failed when API returns errors."""
    order, _ = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": False, "errors": {"base": ["Not found"]}}
    mock_resp.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.post.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    audit = await delete_expense_audited(
        session=session,
        splitwise_expense_id=9999,
        order_id=order.id,
        token="fake-token",
    )

    assert audit.status == "failed"


async def test_delete_expense_audited_http_error(
    session: AsyncSession, order_with_user, monkeypatch
):
    """delete_expense_audited marks failed on network error."""
    order, _ = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    mock_http = MagicMock()
    mock_http.post.side_effect = ConnectionError("refused")
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    audit = await delete_expense_audited(
        session=session,
        splitwise_expense_id=1234,
        order_id=order.id,
        token="fake-token",
    )

    assert audit.status == "failed"
    assert "refused" in audit.error_message


# --- push_splits_audited ---


async def test_push_splits_audited_success(session: AsyncSession, order_with_user, monkeypatch):
    """push_splits_audited creates one audit per split group."""
    order, user = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"expenses": [{"id": 7001}], "errors": []}
    mock_resp.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.post.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    split_result = {
        "paidBy": str(user.id),
        "splits": [
            {
                "amount": 80.0,
                "groceryItems": [
                    {"description": "Chicken", "total": 50.0},
                    {"description": "Rice", "total": 30.0},
                ],
                "splitEquallyAmong": [str(user.id), "member-2"],
            },
            {
                "amount": 20.0,
                "groceryItems": [{"description": "Delivery Fee", "total": 20.0}],
                "splitEquallyAmong": [str(user.id), "member-2"],
            },
        ],
    }

    audits = await push_splits_audited(
        session=session,
        order_id=order.id,
        split_result=split_result,
        member_id_to_sw_id={str(user.id): 99001, "member-2": 99002},
        payer_sw_id=99001,
        token="fake-token",
    )

    assert len(audits) == 2
    assert all(a.status == "success" for a in audits)


async def test_push_splits_audited_missing_sw_id(
    session: AsyncSession, order_with_user, monkeypatch
):
    """push_splits_audited raises ValueError when member has no SW ID."""
    order, user = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    split_result = {
        "paidBy": str(user.id),
        "splits": [
            {
                "amount": 50.0,
                "groceryItems": [{"description": "Item", "total": 50.0}],
                "splitEquallyAmong": [str(user.id), "unknown-member"],
            },
        ],
    }

    with pytest.raises(ValueError, match="No Splitwise user ID"):
        await push_splits_audited(
            session=session,
            order_id=order.id,
            split_result=split_result,
            member_id_to_sw_id={str(user.id): 99001},
            payer_sw_id=99001,
            token="fake-token",
        )


async def test_push_splits_audited_skips_payer_only(
    session: AsyncSession, order_with_user, monkeypatch
):
    """push_splits_audited skips splits where payer is the sole member."""
    order, user = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"expenses": [{"id": 8001}], "errors": []}
    mock_resp.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.post.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    split_result = {
        "paidBy": str(user.id),
        "splits": [
            {
                "amount": 100.0,
                "groceryItems": [{"description": "Chicken", "total": 100.0}],
                "splitEquallyAmong": [str(user.id)],
            },
            {
                "amount": 50.0,
                "groceryItems": [{"description": "Rice", "total": 50.0}],
                "splitEquallyAmong": [str(user.id), "member-2"],
            },
        ],
    }

    audits = await push_splits_audited(
        session=session,
        order_id=order.id,
        split_result=split_result,
        member_id_to_sw_id={str(user.id): 99001, "member-2": 99002},
        payer_sw_id=99001,
        token="fake-token",
    )

    assert len(audits) == 1
    assert audits[0].status == "success"
    assert mock_http.post.call_count == 1


# --- rollback_order_expenses ---


async def test_rollback_order_expenses(session: AsyncSession, order_with_user, monkeypatch):
    """rollback_order_expenses deletes all successful expenses for an order."""
    order, _ = order_with_user
    monkeypatch.setattr("app.services.splitwise.settings", _FakeSettings(splitwise_enabled=True))

    # Create a "success" audit row as if a previous expense was created
    audit = SplitwiseAuditLog(
        order_id=order.id,
        action="create_expense",
        status="success",
        request_payload={"cost": "50.00"},
        splitwise_expense_id=8001,
    )
    session.add(audit)
    await session.commit()

    # Mock the delete API call
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"success": True}
    mock_resp.raise_for_status = MagicMock()
    mock_http = MagicMock()
    mock_http.post.return_value = mock_resp
    monkeypatch.setattr("app.services.splitwise._http", mock_http)

    delete_audits = await rollback_order_expenses(session=session, order_id=order.id, token="t")

    assert len(delete_audits) == 1
    assert delete_audits[0].action == "delete_expense"
    assert delete_audits[0].status == "success"


# --- get_audit_log ---


async def test_get_audit_log(session: AsyncSession, order_with_user, monkeypatch):
    """get_audit_log returns all audit entries for an order."""
    order, _ = order_with_user

    for i in range(3):
        session.add(
            SplitwiseAuditLog(
                order_id=order.id,
                action="create_expense",
                status="success",
                request_payload={"i": i},
                splitwise_expense_id=9000 + i,
            )
        )
    await session.commit()

    logs = await get_audit_log(session=session, order_id=order.id)
    assert len(logs) == 3


async def test_get_audit_log_empty(session: AsyncSession, order_with_user):
    """get_audit_log returns empty list for order with no audit entries."""
    order, _ = order_with_user
    logs = await get_audit_log(session=session, order_id=order.id)
    assert logs == []
