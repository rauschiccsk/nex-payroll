"""Tests for ContributionRate API router.

Covers all CRUD endpoints:
  GET    /api/v1/contribution-rates         (list, paginated)
  GET    /api/v1/contribution-rates/{id}    (detail)
  POST   /api/v1/contribution-rates         (create)
  PATCH  /api/v1/contribution-rates/{id}    (update)
  DELETE /api/v1/contribution-rates/{id}    (delete)
"""

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/contribution-rates"


def _create_rate_payload(**overrides):
    """Return a valid ContributionRateCreate dict with optional overrides."""
    defaults = {
        "rate_type": "sp_employee_nemocenske",
        "rate_percent": "1.4000",
        "max_assessment_base": "8477.00",
        "payer": "employee",
        "fund": "nemocenske",
        "valid_from": "2025-01-01",
        "valid_to": None,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# POST — Create
# ---------------------------------------------------------------------------
class TestCreateContributionRate:
    """POST /api/v1/contribution-rates"""

    def test_create_success(self, client: TestClient):
        payload = _create_rate_payload()
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["rate_type"] == "sp_employee_nemocenske"
        assert Decimal(data["rate_percent"]) == Decimal("1.4000")
        assert Decimal(data["max_assessment_base"]) == Decimal("8477.00")
        assert data["payer"] == "employee"
        assert data["fund"] == "nemocenske"
        assert data["valid_from"] == "2025-01-01"
        assert data["valid_to"] is None
        assert "id" in data
        assert "created_at" in data

    def test_create_without_max_assessment_base(self, client: TestClient):
        payload = _create_rate_payload(max_assessment_base=None)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["max_assessment_base"] is None

    def test_create_with_valid_to(self, client: TestClient):
        payload = _create_rate_payload(valid_to="2025-12-31")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["valid_to"] == "2025-12-31"

    def test_create_employer_payer(self, client: TestClient):
        payload = _create_rate_payload(payer="employer")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["payer"] == "employer"

    def test_create_missing_required_field(self, client: TestClient):
        payload = _create_rate_payload()
        del payload["rate_type"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_invalid_payer(self, client: TestClient):
        payload = _create_rate_payload(payer="invalid")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET list — Paginated
# ---------------------------------------------------------------------------
class TestListContributionRates:
    """GET /api/v1/contribution-rates"""

    def test_list_empty(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        client.post(BASE_URL, json=_create_rate_payload())
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["rate_type"] == "sp_employee_nemocenske"

    def test_list_pagination_skip(self, client: TestClient):
        # Create 3 rates
        for i in range(3):
            client.post(
                BASE_URL,
                json=_create_rate_payload(
                    rate_type=f"rate_{i}",
                    valid_from=f"2025-0{i + 1}-01",
                ),
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
                json=_create_rate_payload(
                    rate_type=f"limit_rate_{i}",
                    valid_from=f"2025-0{i + 1}-01",
                ),
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

    def test_list_filter_by_rate_type(self, client: TestClient):
        client.post(BASE_URL, json=_create_rate_payload(rate_type="sp_employee_nemocenske"))
        client.post(BASE_URL, json=_create_rate_payload(rate_type="zp_employee", fund="zdravotne"))
        resp = client.get(BASE_URL, params={"rate_type": "zp_employee"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert all(item["rate_type"] == "zp_employee" for item in data["items"])

    def test_list_filter_by_payer(self, client: TestClient):
        client.post(BASE_URL, json=_create_rate_payload(payer="employee"))
        client.post(BASE_URL, json=_create_rate_payload(payer="employer", rate_type="sp_employer_nemocenske"))
        resp = client.get(BASE_URL, params={"payer": "employer"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert all(item["payer"] == "employer" for item in data["items"])

    def test_list_filter_combined(self, client: TestClient):
        client.post(BASE_URL, json=_create_rate_payload(rate_type="sp_emp_a", payer="employee"))
        client.post(BASE_URL, json=_create_rate_payload(rate_type="sp_emp_a", payer="employer"))
        client.post(BASE_URL, json=_create_rate_payload(rate_type="zp_emp_b", payer="employee"))
        resp = client.get(BASE_URL, params={"rate_type": "sp_emp_a", "payer": "employee"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["rate_type"] == "sp_emp_a"
        assert data["items"][0]["payer"] == "employee"


# ---------------------------------------------------------------------------
# GET detail
# ---------------------------------------------------------------------------
class TestGetContributionRate:
    """GET /api/v1/contribution-rates/{rate_id}"""

    def test_get_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_rate_payload())
        rate_id = create_resp.json()["id"]

        resp = client.get(f"{BASE_URL}/{rate_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == rate_id
        assert data["rate_type"] == "sp_employee_nemocenske"

    def test_get_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Contribution rate not found"

    def test_get_invalid_uuid(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH — Update
# ---------------------------------------------------------------------------
class TestUpdateContributionRate:
    """PATCH /api/v1/contribution-rates/{rate_id}"""

    def test_update_single_field(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_rate_payload())
        rate_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{rate_id}", json={"rate_percent": "2.0000"})
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["rate_percent"]) == Decimal("2.0000")
        # Other fields unchanged
        assert data["rate_type"] == "sp_employee_nemocenske"

    def test_update_multiple_fields(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_rate_payload())
        rate_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{rate_id}",
            json={
                "rate_type": "zp_employee",
                "fund": "zdravotne",
                "payer": "employer",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rate_type"] == "zp_employee"
        assert data["fund"] == "zdravotne"
        assert data["payer"] == "employer"

    def test_update_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.patch(f"{BASE_URL}/{fake_id}", json={"rate_percent": "2.0000"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Contribution rate not found"

    def test_update_valid_to(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_rate_payload())
        rate_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{rate_id}", json={"valid_to": "2025-12-31"})
        assert resp.status_code == 200
        assert resp.json()["valid_to"] == "2025-12-31"

    def test_update_invalid_payer(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_rate_payload())
        rate_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{rate_id}", json={"payer": "invalid"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
class TestDeleteContributionRate:
    """DELETE /api/v1/contribution-rates/{rate_id}"""

    def test_delete_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_rate_payload())
        rate_id = create_resp.json()["id"]

        resp = client.delete(f"{BASE_URL}/{rate_id}")
        assert resp.status_code == 204

        # Verify gone
        get_resp = client.get(f"{BASE_URL}/{rate_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404

    def test_delete_invalid_uuid(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422
