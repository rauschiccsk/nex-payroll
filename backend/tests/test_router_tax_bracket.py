"""Tests for TaxBracket API router.

Covers all CRUD endpoints:
  GET    /api/v1/tax-brackets         (list, paginated)
  GET    /api/v1/tax-brackets/{id}    (detail)
  POST   /api/v1/tax-brackets         (create)
  PATCH  /api/v1/tax-brackets/{id}    (partial update)
  DELETE /api/v1/tax-brackets/{id}    (delete)
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/tax-brackets"


def _create_bracket_payload(**overrides):
    """Return a valid TaxBracketCreate dict with unique values per call."""
    unique = uuid.uuid4().int % 9000 + 1000
    defaults = {
        "bracket_order": unique,
        "min_amount": "0.00",
        "max_amount": "50000.00",
        "rate_percent": "19.00",
        "nczd_annual": "5646.48",
        "nczd_monthly": "470.54",
        "nczd_reduction_threshold": "24952.06",
        "nczd_reduction_formula": "44.2 * ZM - ZD",
        "valid_from": f"{2025 + (unique % 5)}-01-01",
        "valid_to": None,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# POST — Create
# ---------------------------------------------------------------------------
class TestCreateTaxBracket:
    """POST /api/v1/tax-brackets"""

    def test_create_success(self, client: TestClient):
        payload = _create_bracket_payload()
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["rate_percent"] == "19.00"
        assert data["nczd_annual"] == "5646.48"
        assert data["nczd_monthly"] == "470.54"
        assert data["nczd_reduction_formula"] == "44.2 * ZM - ZD"
        assert data["valid_to"] is None
        assert "id" in data
        assert "created_at" in data

    def test_create_with_valid_to(self, client: TestClient):
        payload = _create_bracket_payload(valid_to="2030-12-31")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["valid_to"] == "2030-12-31"

    def test_create_unlimited_max_amount(self, client: TestClient):
        payload = _create_bracket_payload(max_amount=None, rate_percent="25.00")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["max_amount"] is None
        assert data["rate_percent"] == "25.00"

    def test_create_missing_required_field(self, client: TestClient):
        payload = _create_bracket_payload()
        del payload["rate_percent"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_missing_bracket_order(self, client: TestClient):
        payload = _create_bracket_payload()
        del payload["bracket_order"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_missing_min_amount(self, client: TestClient):
        payload = _create_bracket_payload()
        del payload["min_amount"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_missing_valid_from(self, client: TestClient):
        payload = _create_bracket_payload()
        del payload["valid_from"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_bracket_order_too_low(self, client: TestClient):
        payload = _create_bracket_payload(bracket_order=0)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_duplicate_conflict(self, client: TestClient):
        payload = _create_bracket_payload(bracket_order=99, valid_from="2099-01-01")
        resp1 = client.post(BASE_URL, json=payload)
        assert resp1.status_code == 201

        payload2 = _create_bracket_payload(bracket_order=99, valid_from="2099-01-01")
        resp2 = client.post(BASE_URL, json=payload2)
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]

    def test_create_valid_to_before_valid_from(self, client: TestClient):
        payload = _create_bracket_payload(valid_from="2030-06-01", valid_to="2030-01-01")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET list — Paginated
# ---------------------------------------------------------------------------
class TestListTaxBrackets:
    """GET /api/v1/tax-brackets"""

    def test_list_empty(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        client.post(BASE_URL, json=_create_bracket_payload())
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_pagination_skip(self, client: TestClient):
        for i in range(3):
            client.post(
                BASE_URL,
                json=_create_bracket_payload(bracket_order=i + 1),
            )
        resp = client.get(BASE_URL, params={"skip": 1, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] == 3
        assert data["skip"] == 1
        assert data["limit"] == 2

    def test_list_pagination_limit(self, client: TestClient):
        for i in range(5):
            client.post(
                BASE_URL,
                json=_create_bracket_payload(bracket_order=i + 1),
            )
        resp = client.get(BASE_URL, params={"limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] == 5

    def test_list_invalid_skip(self, client: TestClient):
        resp = client.get(BASE_URL, params={"skip": -1})
        assert resp.status_code == 422

    def test_list_invalid_limit(self, client: TestClient):
        resp = client.get(BASE_URL, params={"limit": 0})
        assert resp.status_code == 422

    def test_list_limit_max(self, client: TestClient):
        resp = client.get(BASE_URL, params={"limit": 101})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET detail
# ---------------------------------------------------------------------------
class TestGetTaxBracket:
    """GET /api/v1/tax-brackets/{bracket_id}"""

    def test_get_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_bracket_payload())
        bracket_id = create_resp.json()["id"]

        resp = client.get(f"{BASE_URL}/{bracket_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == bracket_id

    def test_get_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Tax bracket not found"

    def test_get_invalid_uuid(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH — Partial Update
# ---------------------------------------------------------------------------
class TestUpdateTaxBracket:
    """PATCH /api/v1/tax-brackets/{bracket_id}"""

    def test_update_single_field(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_bracket_payload())
        bracket_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{bracket_id}",
            json={"rate_percent": "25.00"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rate_percent"] == "25.00"

    def test_update_multiple_fields(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_bracket_payload())
        bracket_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{bracket_id}",
            json={
                "rate_percent": "25.00",
                "nczd_annual": "6000.00",
                "nczd_monthly": "500.00",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rate_percent"] == "25.00"
        assert data["nczd_annual"] == "6000.00"
        assert data["nczd_monthly"] == "500.00"

    def test_update_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.patch(
            f"{BASE_URL}/{fake_id}",
            json={"rate_percent": "25.00"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Tax bracket not found"

    def test_update_valid_to(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_bracket_payload())
        bracket_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{bracket_id}",
            json={"valid_to": "2035-12-31"},
        )
        assert resp.status_code == 200
        assert resp.json()["valid_to"] == "2035-12-31"

    def test_update_duplicate_conflict(self, client: TestClient):
        resp1 = client.post(
            BASE_URL,
            json=_create_bracket_payload(bracket_order=91, valid_from="2091-01-01"),
        )
        resp2 = client.post(
            BASE_URL,
            json=_create_bracket_payload(bracket_order=92, valid_from="2091-01-01"),
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        bracket_b_id = resp2.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{bracket_b_id}",
            json={"bracket_order": 91},
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
class TestDeleteTaxBracket:
    """DELETE /api/v1/tax-brackets/{bracket_id}"""

    def test_delete_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_bracket_payload())
        bracket_id = create_resp.json()["id"]

        resp = client.delete(f"{BASE_URL}/{bracket_id}")
        assert resp.status_code == 204

        # Verify gone
        get_resp = client.get(f"{BASE_URL}/{bracket_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404

    def test_delete_invalid_uuid(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422
