"""Tests for PaymentOrder API router.

Covers all CRUD endpoints:
  GET    /api/v1/payment-orders            (list, paginated)
  GET    /api/v1/payment-orders/{id}       (detail)
  POST   /api/v1/payment-orders            (create)
  PATCH  /api/v1/payment-orders/{id}       (update)
  DELETE /api/v1/payment-orders/{id}       (delete)
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/payments"
TENANT_URL = "/api/v1/tenants"


def _create_tenant(client: TestClient, **overrides) -> dict:
    """Helper -- create a tenant and return response JSON."""
    defaults = {
        "name": "Test Firma s.r.o.",
        "ico": "12345678",
        "address_street": "Hlavna 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "bank_iban": "SK8975000000000012345678",
    }
    defaults.update(overrides)
    resp = client.post(TENANT_URL, json=defaults)
    assert resp.status_code == 201
    return resp.json()


def _order_payload(tenant_id: str, **overrides) -> dict:
    """Return a valid PaymentOrderCreate dict with optional overrides."""
    defaults = {
        "tenant_id": tenant_id,
        "period_year": 2025,
        "period_month": 1,
        "payment_type": "sp",
        "recipient_name": "Socialna poistovna",
        "recipient_iban": "SK3112000000198742637541",
        "amount": "1234.56",
        "status": "pending",
    }
    defaults.update(overrides)
    return defaults


# -- LIST -------------------------------------------------------------------


class TestListPaymentOrders:
    def test_empty_list(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        tenant = _create_tenant(client)
        payload = _order_payload(tenant["id"])
        client.post(BASE_URL, json=payload)

        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["payment_type"] == "sp"

    def test_pagination(self, client: TestClient):
        tenant = _create_tenant(client)
        for month in (1, 2, 3):
            payload = _order_payload(tenant["id"], period_month=month)
            client.post(BASE_URL, json=payload)

        resp = client.get(BASE_URL, params={"skip": 0, "limit": 2})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_filter_by_tenant(self, client: TestClient):
        tenant = _create_tenant(client)
        payload = _order_payload(tenant["id"])
        client.post(BASE_URL, json=payload)

        resp = client.get(BASE_URL, params={"tenant_id": tenant["id"]})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"tenant_id": str(uuid.uuid4())})
        assert resp.json()["total"] == 0

    def test_filter_by_payment_type(self, client: TestClient):
        tenant = _create_tenant(client)
        client.post(BASE_URL, json=_order_payload(tenant["id"], payment_type="sp"))
        client.post(
            BASE_URL,
            json=_order_payload(tenant["id"], payment_type="tax", period_month=2),
        )

        resp = client.get(BASE_URL, params={"payment_type": "tax"})
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["payment_type"] == "tax"

    def test_filter_by_status(self, client: TestClient):
        tenant = _create_tenant(client)
        client.post(BASE_URL, json=_order_payload(tenant["id"], status="pending"))
        client.post(
            BASE_URL,
            json=_order_payload(tenant["id"], status="paid", period_month=2),
        )

        resp = client.get(BASE_URL, params={"status": "paid"})
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "paid"

    def test_filter_by_period(self, client: TestClient):
        tenant = _create_tenant(client)
        client.post(BASE_URL, json=_order_payload(tenant["id"], period_year=2025, period_month=1))
        client.post(BASE_URL, json=_order_payload(tenant["id"], period_year=2025, period_month=2))

        resp = client.get(BASE_URL, params={"period_year": 2025, "period_month": 1})
        data = resp.json()
        assert data["total"] == 1

    def test_invalid_payment_type_filter(self, client: TestClient):
        resp = client.get(BASE_URL, params={"payment_type": "invalid"})
        assert resp.status_code == 422


# -- GET DETAIL -------------------------------------------------------------


class TestGetPaymentOrder:
    def test_get_existing(self, client: TestClient):
        tenant = _create_tenant(client)
        payload = _order_payload(tenant["id"])
        created = client.post(BASE_URL, json=payload).json()

        resp = client.get(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]
        assert data["recipient_name"] == "Socialna poistovna"
        assert data["amount"] == "1234.56"

    def test_get_not_found(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404


# -- CREATE -----------------------------------------------------------------


class TestCreatePaymentOrder:
    def test_create_success(self, client: TestClient):
        tenant = _create_tenant(client)
        payload = _order_payload(tenant["id"])
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["tenant_id"] == tenant["id"]
        assert data["payment_type"] == "sp"
        assert data["recipient_iban"] == "SK3112000000198742637541"
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_all_payment_types(self, client: TestClient):
        tenant = _create_tenant(client)
        # Types that don't require extra FK references
        simple_types = ("sp", "tax", "pillar2")
        for idx, ptype in enumerate(simple_types, start=1):
            payload = _order_payload(tenant["id"], payment_type=ptype, period_month=idx)
            resp = client.post(BASE_URL, json=payload)
            assert resp.status_code == 201, f"Failed to create payment_type={ptype}"
            assert resp.json()["payment_type"] == ptype

    def test_create_with_optional_fields(self, client: TestClient):
        tenant = _create_tenant(client)
        payload = _order_payload(
            tenant["id"],
            recipient_bic="TATRSKBX",
            variable_symbol="1234567890",
            specific_symbol="0012345678",
            constant_symbol="0558",
            reference="PAYROLL-2025-01-NOVAK",
        )
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["recipient_bic"] == "TATRSKBX"
        assert data["variable_symbol"] == "1234567890"
        assert data["constant_symbol"] == "0558"
        assert data["reference"] == "PAYROLL-2025-01-NOVAK"


# -- UPDATE -----------------------------------------------------------------


class TestUpdatePaymentOrder:
    def test_update_success(self, client: TestClient):
        tenant = _create_tenant(client)
        payload = _order_payload(tenant["id"])
        created = client.post(BASE_URL, json=payload).json()

        resp = client.patch(
            f"{BASE_URL}/{created['id']}",
            json={"status": "exported", "amount": "999.99"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "exported"
        assert data["amount"] == "999.99"
        # unchanged
        assert data["recipient_name"] == "Socialna poistovna"

    def test_update_not_found(self, client: TestClient):
        resp = client.patch(
            f"{BASE_URL}/{uuid.uuid4()}",
            json={"status": "paid"},
        )
        assert resp.status_code == 404


# -- DELETE -----------------------------------------------------------------


class TestDeletePaymentOrder:
    def test_delete_success(self, client: TestClient):
        tenant = _create_tenant(client)
        payload = _order_payload(tenant["id"])
        created = client.post(BASE_URL, json=payload).json()

        resp = client.delete(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 204

        # confirm gone
        resp = client.get(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 404

    def test_delete_not_found(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404
