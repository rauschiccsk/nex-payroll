"""Tests for StatutoryDeadline API router.

Covers all CRUD endpoints:
  GET    /api/v1/statutory-deadlines         (list, paginated)
  GET    /api/v1/statutory-deadlines/{id}    (detail)
  POST   /api/v1/statutory-deadlines         (create)
  PATCH  /api/v1/statutory-deadlines/{id}    (partial update)
  DELETE /api/v1/statutory-deadlines/{id}    (delete)
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/statutory-deadlines"

_counter = 0


def _create_deadline_payload(**overrides):
    """Return a valid StatutoryDeadlineCreate dict with optional overrides."""
    global _counter  # noqa: PLW0603
    _counter += 1
    defaults = {
        "code": f"SP_MONTHLY_{_counter}",
        "name": "Mesacny vykaz SP",
        "deadline_type": "monthly",
        "institution": "Socialna poistovna",
        "day_of_month": 20,
        "description": "Mesacny vykaz poistneho a prispevkov",
        "valid_from": "2025-01-01",
        "valid_to": None,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# POST — Create
# ---------------------------------------------------------------------------
class TestCreateStatutoryDeadline:
    """POST /api/v1/statutory-deadlines"""

    def test_create_success(self, client: TestClient):
        payload = _create_deadline_payload()
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["deadline_type"] == "monthly"
        assert data["institution"] == "Socialna poistovna"
        assert data["day_of_month"] == 20
        assert data["description"] == "Mesacny vykaz poistneho a prispevkov"
        assert data["valid_from"] == "2025-01-01"
        assert data["valid_to"] is None
        assert "id" in data
        assert "created_at" in data

    def test_create_with_valid_to(self, client: TestClient):
        payload = _create_deadline_payload(valid_to="2025-12-31")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["valid_to"] == "2025-12-31"

    def test_create_with_business_days_rule(self, client: TestClient):
        payload = _create_deadline_payload(business_days_rule=True)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["business_days_rule"] is True

    def test_create_annual(self, client: TestClient):
        payload = _create_deadline_payload(
            deadline_type="annual",
            institution="Danovy urad",
            month_of_year=4,
        )
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["deadline_type"] == "annual"
        assert data["month_of_year"] == 4

    def test_create_one_time(self, client: TestClient):
        payload = _create_deadline_payload(
            deadline_type="one_time",
            institution="Danovy urad",
            day_of_month=25,
        )
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["deadline_type"] == "one_time"
        assert data["day_of_month"] == 25

    def test_create_missing_required_field(self, client: TestClient):
        payload = _create_deadline_payload()
        del payload["deadline_type"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_missing_institution(self, client: TestClient):
        payload = _create_deadline_payload()
        del payload["institution"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_missing_code(self, client: TestClient):
        payload = _create_deadline_payload()
        del payload["code"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_missing_name(self, client: TestClient):
        payload = _create_deadline_payload()
        del payload["name"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_missing_valid_from(self, client: TestClient):
        payload = _create_deadline_payload()
        del payload["valid_from"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_invalid_deadline_type(self, client: TestClient):
        payload = _create_deadline_payload(deadline_type="invalid_type")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_day_of_month_too_low(self, client: TestClient):
        payload = _create_deadline_payload(day_of_month=0)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_day_of_month_too_high(self, client: TestClient):
        payload = _create_deadline_payload(day_of_month=32)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET list — Paginated
# ---------------------------------------------------------------------------
class TestListStatutoryDeadlines:
    """GET /api/v1/statutory-deadlines"""

    def test_list_empty(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        client.post(BASE_URL, json=_create_deadline_payload())
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["deadline_type"] == "monthly"

    def test_list_pagination_skip(self, client: TestClient):
        # Create 3 deadlines with different types
        for dtype in ["monthly", "annual", "one_time"]:
            client.post(
                BASE_URL,
                json=_create_deadline_payload(
                    deadline_type=dtype,
                    institution=f"Institution {dtype}",
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
        for i, dtype in enumerate(["monthly", "annual", "one_time", "monthly", "annual"]):
            client.post(
                BASE_URL,
                json=_create_deadline_payload(
                    deadline_type=dtype,
                    institution=f"Limit Institution {i}",
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


# ---------------------------------------------------------------------------
# GET detail
# ---------------------------------------------------------------------------
class TestGetStatutoryDeadline:
    """GET /api/v1/statutory-deadlines/{deadline_id}"""

    def test_get_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_deadline_payload())
        deadline_id = create_resp.json()["id"]

        resp = client.get(f"{BASE_URL}/{deadline_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == deadline_id
        assert data["deadline_type"] == "monthly"

    def test_get_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Statutory deadline not found"

    def test_get_invalid_uuid(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH — Partial Update
# ---------------------------------------------------------------------------
class TestUpdateStatutoryDeadline:
    """PATCH /api/v1/statutory-deadlines/{deadline_id}"""

    def test_update_single_field(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_deadline_payload())
        deadline_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{deadline_id}",
            json={"institution": "Updated Institution"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["institution"] == "Updated Institution"
        # Other fields unchanged
        assert data["deadline_type"] == "monthly"

    def test_update_multiple_fields(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_deadline_payload())
        deadline_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{deadline_id}",
            json={
                "deadline_type": "annual",
                "institution": "VsZP",
                "day_of_month": 8,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deadline_type"] == "annual"
        assert data["institution"] == "VsZP"
        assert data["day_of_month"] == 8

    def test_update_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.patch(
            f"{BASE_URL}/{fake_id}",
            json={"institution": "Nope"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Statutory deadline not found"

    def test_update_valid_to(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_deadline_payload())
        deadline_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{deadline_id}",
            json={"valid_to": "2025-12-31"},
        )
        assert resp.status_code == 200
        assert resp.json()["valid_to"] == "2025-12-31"

    def test_update_business_days_rule(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_deadline_payload())
        deadline_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{deadline_id}",
            json={"business_days_rule": True},
        )
        assert resp.status_code == 200
        assert resp.json()["business_days_rule"] is True

    def test_update_invalid_deadline_type(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_deadline_payload())
        deadline_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{deadline_id}",
            json={"deadline_type": "invalid"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
class TestDeleteStatutoryDeadline:
    """DELETE /api/v1/statutory-deadlines/{deadline_id}"""

    def test_delete_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_deadline_payload())
        deadline_id = create_resp.json()["id"]

        resp = client.delete(f"{BASE_URL}/{deadline_id}")
        assert resp.status_code == 204

        # Verify gone
        get_resp = client.get(f"{BASE_URL}/{deadline_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404

    def test_delete_invalid_uuid(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422
