"""Tests for HealthInsurer API router.

Covers all CRUD endpoints:
  GET    /api/v1/health-insurers         (list, paginated)
  GET    /api/v1/health-insurers/{id}    (detail)
  POST   /api/v1/health-insurers         (create)
  PATCH  /api/v1/health-insurers/{id}    (partial update)
  DELETE /api/v1/health-insurers/{id}    (delete)
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/health-insurers"


def _create_insurer_payload(**overrides):
    """Return a valid HealthInsurerCreate dict with optional overrides."""
    defaults = {
        "code": "25",
        "name": "Všeobecná zdravotná poisťovňa, a.s.",
        "iban": "SK8975000000000012345678",
        "bic": "CEKOSKBX",
        "is_active": True,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# POST — Create
# ---------------------------------------------------------------------------
class TestCreateHealthInsurer:
    """POST /api/v1/health-insurers"""

    def test_create_success(self, client: TestClient):
        payload = _create_insurer_payload()
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "25"
        assert data["name"] == "Všeobecná zdravotná poisťovňa, a.s."
        assert data["iban"] == "SK8975000000000012345678"
        assert data["bic"] == "CEKOSKBX"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_without_bic(self, client: TestClient):
        payload = _create_insurer_payload(code="24", bic=None)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["bic"] is None

    def test_create_inactive(self, client: TestClient):
        payload = _create_insurer_payload(code="27", is_active=False)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["is_active"] is False

    def test_create_missing_required_field(self, client: TestClient):
        payload = _create_insurer_payload()
        del payload["code"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_missing_name(self, client: TestClient):
        payload = _create_insurer_payload()
        del payload["name"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_missing_iban(self, client: TestClient):
        payload = _create_insurer_payload()
        del payload["iban"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_duplicate_code_409(self, client: TestClient):
        """Creating two insurers with the same code returns 409 Conflict."""
        payload = _create_insurer_payload(code="99")
        resp1 = client.post(BASE_URL, json=payload)
        assert resp1.status_code == 201

        payload2 = _create_insurer_payload(code="99", name="Duplicate Insurer")
        resp2 = client.post(BASE_URL, json=payload2)
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]


# ---------------------------------------------------------------------------
# GET list — Paginated
# ---------------------------------------------------------------------------
class TestListHealthInsurers:
    """GET /api/v1/health-insurers"""

    def test_list_empty(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        client.post(BASE_URL, json=_create_insurer_payload())
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["code"] == "25"

    def test_list_pagination_skip(self, client: TestClient):
        # Create 3 insurers with unique codes
        for i, code in enumerate(["21", "22", "23"]):
            client.post(BASE_URL, json=_create_insurer_payload(code=code, name=f"Insurer {i}"))
        resp = client.get(BASE_URL, params={"skip": 1, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] == 3
        assert data["skip"] == 1
        assert data["limit"] == 2

    def test_list_pagination_limit(self, client: TestClient):
        for i, code in enumerate(["31", "32", "33", "34", "35"]):
            client.post(BASE_URL, json=_create_insurer_payload(code=code, name=f"Limit Insurer {i}"))
        resp = client.get(BASE_URL, params={"limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] == 5

    def test_list_filter_is_active(self, client: TestClient):
        """Filter by is_active returns only matching insurers."""
        client.post(BASE_URL, json=_create_insurer_payload(code="51", is_active=True))
        client.post(
            BASE_URL,
            json=_create_insurer_payload(code="52", name="Inactive Ins", is_active=False),
        )
        # Only active
        resp = client.get(BASE_URL, params={"is_active": True})
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["is_active"] is True for item in data["items"])
        assert data["total"] >= 1

        # Only inactive
        resp2 = client.get(BASE_URL, params={"is_active": False})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert all(item["is_active"] is False for item in data2["items"])
        assert data2["total"] >= 1

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
class TestGetHealthInsurer:
    """GET /api/v1/health-insurers/{insurer_id}"""

    def test_get_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_insurer_payload())
        insurer_id = create_resp.json()["id"]

        resp = client.get(f"{BASE_URL}/{insurer_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == insurer_id
        assert data["code"] == "25"

    def test_get_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Health insurer not found"

    def test_get_invalid_uuid(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH — Partial Update
# ---------------------------------------------------------------------------
class TestUpdateHealthInsurer:
    """PATCH /api/v1/health-insurers/{insurer_id}"""

    def test_update_single_field(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_insurer_payload())
        insurer_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{insurer_id}", json={"name": "Updated Insurer"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Insurer"
        # Other fields unchanged
        assert data["code"] == "25"

    def test_update_multiple_fields(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_insurer_payload())
        insurer_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{insurer_id}",
            json={
                "code": "24",
                "name": "Dôvera zdravotná poisťovňa, a.s.",
                "iban": "SK1234567890123456789012",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "24"
        assert data["name"] == "Dôvera zdravotná poisťovňa, a.s."
        assert data["iban"] == "SK1234567890123456789012"

    def test_update_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.patch(f"{BASE_URL}/{fake_id}", json={"name": "Nope"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Health insurer not found"

    def test_update_is_active(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_insurer_payload())
        insurer_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{insurer_id}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_update_bic_to_none(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_insurer_payload())
        insurer_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{insurer_id}", json={"bic": None})
        assert resp.status_code == 200
        assert resp.json()["bic"] is None

    def test_update_duplicate_code_409(self, client: TestClient):
        """Updating code to one already taken returns 409 Conflict."""
        resp1 = client.post(BASE_URL, json=_create_insurer_payload(code="41"))
        assert resp1.status_code == 201

        resp2 = client.post(
            BASE_URL,
            json=_create_insurer_payload(code="42", name="Second Insurer"),
        )
        assert resp2.status_code == 201
        second_id = resp2.json()["id"]

        resp3 = client.patch(f"{BASE_URL}/{second_id}", json={"code": "41"})
        assert resp3.status_code == 409
        assert "already exists" in resp3.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
class TestDeleteHealthInsurer:
    """DELETE /api/v1/health-insurers/{insurer_id}"""

    def test_delete_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_insurer_payload())
        insurer_id = create_resp.json()["id"]

        resp = client.delete(f"{BASE_URL}/{insurer_id}")
        assert resp.status_code == 204

        # Verify gone
        get_resp = client.get(f"{BASE_URL}/{insurer_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404

    def test_delete_invalid_uuid(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422
