"""Tests for Tenant API router.

Covers all CRUD endpoints:
  GET    /api/v1/tenants         (list, paginated, with is_active filter)
  GET    /api/v1/tenants/{id}    (detail)
  POST   /api/v1/tenants         (create)
  PATCH  /api/v1/tenants/{id}    (partial update)
  DELETE /api/v1/tenants/{id}    (delete)
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/tenants"


def _create_tenant_payload(**overrides):
    """Return a valid TenantCreate dict with optional overrides."""
    defaults = {
        "name": "Firma s.r.o.",
        "ico": "12345678",
        "dic": "2012345678",
        "ic_dph": "SK2012345678",
        "address_street": "Hlavna 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "bank_bic": "TATRSKBX",
        "default_role": "accountant",
        "is_active": True,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# POST — Create
# ---------------------------------------------------------------------------
class TestCreateTenant:
    """POST /api/v1/tenants"""

    def test_create_success(self, client: TestClient):
        payload = _create_tenant_payload()
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Firma s.r.o."
        assert data["ico"] == "12345678"
        assert data["dic"] == "2012345678"
        assert data["ic_dph"] == "SK2012345678"
        assert data["address_street"] == "Hlavna 1"
        assert data["address_city"] == "Bratislava"
        assert data["address_zip"] == "81101"
        assert data["address_country"] == "SK"
        assert data["bank_iban"] == "SK8975000000000012345678"
        assert data["bank_bic"] == "TATRSKBX"
        assert data["default_role"] == "accountant"
        assert data["is_active"] is True
        assert "id" in data
        assert "schema_name" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_minimal(self, client: TestClient):
        """Create tenant with only required fields."""
        payload = {
            "name": "Minimal s.r.o.",
            "ico": "87654321",
            "address_street": "Dolna 2",
            "address_city": "Kosice",
            "address_zip": "04001",
            "bank_iban": "SK1234567890123456789012",
        }
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["dic"] is None
        assert data["ic_dph"] is None
        assert data["bank_bic"] is None
        assert data["address_country"] == "SK"
        assert data["default_role"] == "accountant"
        assert data["is_active"] is True

    def test_create_duplicate_ico(self, client: TestClient):
        payload = _create_tenant_payload()
        resp1 = client.post(BASE_URL, json=payload)
        assert resp1.status_code == 201

        resp2 = client.post(BASE_URL, json=payload)
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]

    def test_create_missing_required_field(self, client: TestClient):
        payload = _create_tenant_payload()
        del payload["name"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_invalid_ico_format(self, client: TestClient):
        """IČO must be exactly 8 digits."""
        payload = _create_tenant_payload(ico="1234")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_invalid_iban(self, client: TestClient):
        """IBAN must match expected format."""
        payload = _create_tenant_payload(bank_iban="INVALID")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_schema_name_auto_generated(self, client: TestClient):
        """schema_name should be auto-generated from name + ico."""
        payload = _create_tenant_payload(name="Test Company", ico="99887766")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "schema_name" in data
        assert "99887766" in data["schema_name"]
        assert data["schema_name"].startswith("tenant_")

    def test_create_with_director_role(self, client: TestClient):
        """Allow creating tenant with director default_role."""
        payload = _create_tenant_payload(ico="55667788", default_role="director")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        assert resp.json()["default_role"] == "director"

    def test_create_invalid_default_role(self, client: TestClient):
        """Only director/accountant/employee are valid roles."""
        payload = _create_tenant_payload(default_role="superadmin")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET list — Paginated
# ---------------------------------------------------------------------------
class TestListTenants:
    """GET /api/v1/tenants"""

    def test_list_empty(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        client.post(BASE_URL, json=_create_tenant_payload())
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["ico"] == "12345678"

    def test_list_pagination_skip(self, client: TestClient):
        for i in range(3):
            client.post(
                BASE_URL,
                json=_create_tenant_payload(
                    name=f"Firma {i} s.r.o.",
                    ico=f"1000000{i}",
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
                json=_create_tenant_payload(
                    name=f"Limit Firma {i}",
                    ico=f"2000000{i}",
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

    def test_list_filter_is_active_true(self, client: TestClient):
        """Filter tenants by is_active=true."""
        client.post(BASE_URL, json=_create_tenant_payload(ico="30000001", is_active=True))
        client.post(BASE_URL, json=_create_tenant_payload(ico="30000002", is_active=False))

        resp = client.get(BASE_URL, params={"is_active": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert all(item["is_active"] is True for item in data["items"])

    def test_list_filter_is_active_false(self, client: TestClient):
        """Filter tenants by is_active=false."""
        client.post(BASE_URL, json=_create_tenant_payload(ico="40000001", is_active=True))
        client.post(BASE_URL, json=_create_tenant_payload(ico="40000002", is_active=False))

        resp = client.get(BASE_URL, params={"is_active": False})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert all(item["is_active"] is False for item in data["items"])

    def test_list_no_filter_returns_all(self, client: TestClient):
        """Without is_active filter, return all tenants."""
        client.post(BASE_URL, json=_create_tenant_payload(ico="50000001", is_active=True))
        client.post(BASE_URL, json=_create_tenant_payload(ico="50000002", is_active=False))

        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2


# ---------------------------------------------------------------------------
# GET detail
# ---------------------------------------------------------------------------
class TestGetTenant:
    """GET /api/v1/tenants/{tenant_id}"""

    def test_get_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_tenant_payload())
        tenant_id = create_resp.json()["id"]

        resp = client.get(f"{BASE_URL}/{tenant_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == tenant_id
        assert data["name"] == "Firma s.r.o."

    def test_get_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Tenant not found"

    def test_get_invalid_uuid(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH — Partial Update
# ---------------------------------------------------------------------------
class TestUpdateTenant:
    """PATCH /api/v1/tenants/{tenant_id}"""

    def test_update_single_field(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_tenant_payload())
        tenant_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{tenant_id}", json={"name": "Nova Firma s.r.o."})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Nova Firma s.r.o."
        # Other fields unchanged
        assert data["ico"] == "12345678"

    def test_update_multiple_fields(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_tenant_payload())
        tenant_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{tenant_id}",
            json={
                "address_city": "Kosice",
                "address_zip": "04001",
                "is_active": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["address_city"] == "Kosice"
        assert data["address_zip"] == "04001"
        assert data["is_active"] is False

    def test_update_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.patch(f"{BASE_URL}/{fake_id}", json={"name": "X"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Tenant not found"

    def test_update_duplicate_ico(self, client: TestClient):
        client.post(BASE_URL, json=_create_tenant_payload(ico="11111111"))
        create_resp = client.post(BASE_URL, json=_create_tenant_payload(ico="22222222"))
        tenant_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{tenant_id}", json={"ico": "11111111"})
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_update_empty_body(self, client: TestClient):
        """PATCH with empty body should return current state unchanged."""
        create_resp = client.post(BASE_URL, json=_create_tenant_payload())
        tenant_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{tenant_id}", json={})
        assert resp.status_code == 200
        assert resp.json()["ico"] == "12345678"

    def test_update_invalid_ico_format(self, client: TestClient):
        """PATCH with invalid IČO format should return 422."""
        create_resp = client.post(BASE_URL, json=_create_tenant_payload())
        tenant_id = create_resp.json()["id"]

        resp = client.patch(f"{BASE_URL}/{tenant_id}", json={"ico": "ABC"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
class TestDeleteTenant:
    """DELETE /api/v1/tenants/{tenant_id}"""

    def test_delete_existing(self, client: TestClient):
        create_resp = client.post(BASE_URL, json=_create_tenant_payload())
        tenant_id = create_resp.json()["id"]

        resp = client.delete(f"{BASE_URL}/{tenant_id}")
        assert resp.status_code == 204

        # Verify gone
        get_resp = client.get(f"{BASE_URL}/{tenant_id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404

    def test_delete_invalid_uuid(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422

    def test_delete_with_dependent_user(self, client: TestClient, db_session):
        """DELETE should return 409 when tenant has dependent users."""
        from app.models.user import User

        # Create a tenant via API
        create_resp = client.post(BASE_URL, json=_create_tenant_payload())
        assert create_resp.status_code == 201
        tenant_id = create_resp.json()["id"]

        # Insert a dependent user directly via session
        user = User(
            tenant_id=tenant_id,
            username="testuser",
            email="test@example.com",
            password_hash="fakehash",
            role="accountant",
        )
        db_session.add(user)
        db_session.flush()

        # Attempt to delete tenant should fail with 409
        resp = client.delete(f"{BASE_URL}/{tenant_id}")
        assert resp.status_code == 409
        assert "dependent" in resp.json()["detail"].lower()

    def test_delete_idempotent(self, client: TestClient):
        """Deleting same tenant twice should return 404 the second time."""
        create_resp = client.post(BASE_URL, json=_create_tenant_payload())
        tenant_id = create_resp.json()["id"]

        resp1 = client.delete(f"{BASE_URL}/{tenant_id}")
        assert resp1.status_code == 204

        resp2 = client.delete(f"{BASE_URL}/{tenant_id}")
        assert resp2.status_code == 404
