"""Tests for User API router.

Covers all CRUD endpoints:
  GET    /api/v1/users         (list, paginated)
  GET    /api/v1/users/{id}    (detail)
  POST   /api/v1/users         (create)
  PUT    /api/v1/users/{id}    (update)
  DELETE /api/v1/users/{id}    (delete / soft-delete)
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.tenant import Tenant

BASE_URL = "/api/v1/users"


def _create_tenant(db_session: Session, **overrides) -> Tenant:
    """Insert a minimal Tenant directly via ORM and return it."""
    defaults = {
        "name": "Test s.r.o.",
        "ico": "12345678",
        "address_street": "Hlavna 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "schema_name": "tenant_test_12345678",
    }
    defaults.update(overrides)
    tenant = Tenant(**defaults)
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _user_payload(tenant_id: str, **overrides) -> dict:
    """Return a valid user creation payload with optional overrides."""
    defaults = {
        "tenant_id": tenant_id,
        "username": "jnovak",
        "email": "jan.novak@example.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fakehashvalue",
        "role": "accountant",
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# POST -- Create
# ---------------------------------------------------------------------------
class TestCreateUser:
    """POST /api/v1/users"""

    def test_create_success(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        payload = _user_payload(str(tenant.id))
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "jnovak"
        assert data["email"] == "jan.novak@example.com"
        assert data["role"] == "accountant"
        assert data["is_active"] is True
        assert data["tenant_id"] == str(tenant.id)
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        # password_hash must NOT be in response
        assert "password_hash" not in data

    def test_create_duplicate_username(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        payload = _user_payload(str(tenant.id))
        resp1 = client.post(BASE_URL, json=payload)
        assert resp1.status_code == 201

        resp2 = client.post(
            BASE_URL,
            json=_user_payload(str(tenant.id), email="other@example.com"),
        )
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]

    def test_create_duplicate_email(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        resp1 = client.post(BASE_URL, json=_user_payload(str(tenant.id)))
        assert resp1.status_code == 201

        resp2 = client.post(
            BASE_URL,
            json=_user_payload(str(tenant.id), username="other_user"),
        )
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]

    def test_create_missing_required_field(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        payload = _user_payload(str(tenant.id))
        del payload["username"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET list -- Paginated
# ---------------------------------------------------------------------------
class TestListUsers:
    """GET /api/v1/users"""

    def test_list_empty(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        client.post(BASE_URL, json=_user_payload(str(tenant.id)))
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_filter_by_tenant(self, client: TestClient, db_session: Session):
        t1 = _create_tenant(db_session, ico="11111111", schema_name="t_11111111")
        t2 = _create_tenant(db_session, ico="22222222", schema_name="t_22222222")
        client.post(BASE_URL, json=_user_payload(str(t1.id), username="u1", email="u1@e.com"))
        client.post(BASE_URL, json=_user_payload(str(t2.id), username="u2", email="u2@e.com"))

        resp = client.get(BASE_URL, params={"tenant_id": str(t1.id)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["tenant_id"] == str(t1.id)

    def test_list_filter_by_role(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        client.post(
            BASE_URL,
            json=_user_payload(str(tenant.id), username="acc", email="acc@e.com", role="accountant"),
        )
        client.post(
            BASE_URL,
            json=_user_payload(str(tenant.id), username="dir", email="dir@e.com", role="director"),
        )

        resp = client.get(BASE_URL, params={"role": "director"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["role"] == "director"

    def test_list_pagination(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        for i in range(3):
            client.post(
                BASE_URL,
                json=_user_payload(str(tenant.id), username=f"user{i}", email=f"u{i}@e.com"),
            )
        resp = client.get(BASE_URL, params={"skip": 1, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] == 3
        assert data["skip"] == 1
        assert data["limit"] == 2

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
class TestGetUser:
    """GET /api/v1/users/{user_id}"""

    def test_get_existing(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        create_resp = client.post(BASE_URL, json=_user_payload(str(tenant.id)))
        user_id = create_resp.json()["id"]

        resp = client.get(f"{BASE_URL}/{user_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user_id
        assert data["username"] == "jnovak"

    def test_get_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    def test_get_invalid_uuid(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT -- Update
# ---------------------------------------------------------------------------
class TestUpdateUser:
    """PUT /api/v1/users/{user_id}"""

    def test_update_single_field(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        create_resp = client.post(BASE_URL, json=_user_payload(str(tenant.id)))
        user_id = create_resp.json()["id"]

        resp = client.put(f"{BASE_URL}/{user_id}", json={"username": "peter_novak"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "peter_novak"
        # Other fields unchanged
        assert data["email"] == "jan.novak@example.com"

    def test_update_multiple_fields(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        create_resp = client.post(BASE_URL, json=_user_payload(str(tenant.id)))
        user_id = create_resp.json()["id"]

        resp = client.put(
            f"{BASE_URL}/{user_id}",
            json={"email": "new@example.com", "role": "director"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["role"] == "director"

    def test_update_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.put(f"{BASE_URL}/{fake_id}", json={"username": "X"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    def test_update_duplicate_username(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        client.post(
            BASE_URL,
            json=_user_payload(str(tenant.id), username="user1", email="u1@e.com"),
        )
        create_resp = client.post(
            BASE_URL,
            json=_user_payload(str(tenant.id), username="user2", email="u2@e.com"),
        )
        user_id = create_resp.json()["id"]

        resp = client.put(f"{BASE_URL}/{user_id}", json={"username": "user1"})
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_update_does_not_accept_tenant_id(self, client: TestClient, db_session: Session):
        """tenant_id is immutable — must not be accepted in update payload."""
        tenant = _create_tenant(db_session)
        create_resp = client.post(BASE_URL, json=_user_payload(str(tenant.id)))
        user_id = create_resp.json()["id"]
        new_tenant_id = str(uuid.uuid4())

        # Sending tenant_id should be ignored (not in UserUpdate schema)
        resp = client.put(f"{BASE_URL}/{user_id}", json={"tenant_id": new_tenant_id})
        assert resp.status_code == 200
        data = resp.json()
        # tenant_id remains unchanged
        assert data["tenant_id"] == str(tenant.id)


# ---------------------------------------------------------------------------
# DELETE -- Soft delete
# ---------------------------------------------------------------------------
class TestDeleteUser:
    """DELETE /api/v1/users/{user_id}"""

    def test_delete_existing(self, client: TestClient, db_session: Session):
        tenant = _create_tenant(db_session)
        create_resp = client.post(BASE_URL, json=_user_payload(str(tenant.id)))
        user_id = create_resp.json()["id"]

        resp = client.delete(f"{BASE_URL}/{user_id}")
        assert resp.status_code == 204

    def test_delete_is_soft(self, client: TestClient, db_session: Session):
        """Soft delete sets is_active=False; user still visible with include_inactive."""
        tenant = _create_tenant(db_session)
        create_resp = client.post(BASE_URL, json=_user_payload(str(tenant.id)))
        user_id = create_resp.json()["id"]

        resp = client.delete(f"{BASE_URL}/{user_id}")
        assert resp.status_code == 204

        # User should still exist when fetched by ID (GET detail doesn't filter by is_active)
        get_resp = client.get(f"{BASE_URL}/{user_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["is_active"] is False

        # User should be excluded from default list
        list_resp = client.get(BASE_URL)
        user_ids = [u["id"] for u in list_resp.json()["items"]]
        assert user_id not in user_ids

        # User should appear when include_inactive=true
        list_resp2 = client.get(BASE_URL, params={"include_inactive": "true"})
        user_ids2 = [u["id"] for u in list_resp2.json()["items"]]
        assert user_id in user_ids2

    def test_delete_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404

    def test_delete_invalid_uuid(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422
