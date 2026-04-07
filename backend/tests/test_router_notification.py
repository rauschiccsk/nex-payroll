"""Tests for Notification API router.

Covers all CRUD endpoints:
  GET    /api/v1/notifications           (list, paginated, with filters)
  GET    /api/v1/notifications/{id}      (detail)
  POST   /api/v1/notifications           (create)
  PATCH  /api/v1/notifications/{id}      (update)
  DELETE /api/v1/notifications/{id}      (delete)
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.user import User

BASE_URL = "/api/v1/notifications"


@pytest.fixture()
def tenant(db_session: Session) -> Tenant:
    """Create a tenant required by Notification FK constraint."""
    t = Tenant(
        name="Test Firma s.r.o.",
        ico="99999999",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        address_country="SK",
        bank_iban="SK8975000000000012345678",
        schema_name="tenant_notif_test_99999999",
    )
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture()
def user(db_session: Session, tenant: Tenant) -> User:
    """Create a user required by Notification FK constraint."""
    u = User(
        tenant_id=tenant.id,
        username="testuser",
        email="testuser@example.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="accountant",
    )
    db_session.add(u)
    db_session.flush()
    return u


def _create_notification_payload(tenant_id: uuid.UUID, user_id: uuid.UUID, **overrides):
    """Return a valid NotificationCreate dict with optional overrides."""
    defaults = {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "type": "deadline",
        "severity": "info",
        "title": "Blíži sa termín pre výkaz SP",
        "message": "Termín pre mesačný výkaz SP je o 3 dni.",
        "related_entity": None,
        "related_entity_id": None,
    }
    defaults.update(overrides)
    return defaults


def _insert_notification(db_session: Session, tenant: Tenant, user: User, **overrides) -> Notification:
    """Insert a notification directly via ORM for test setup."""
    defaults = {
        "tenant_id": tenant.id,
        "user_id": user.id,
        "type": "deadline",
        "severity": "info",
        "title": "Test notification",
        "message": "Test message body",
    }
    defaults.update(overrides)
    n = Notification(**defaults)
    db_session.add(n)
    db_session.flush()
    return n


# ---------------------------------------------------------------------------
# POST — Create
# ---------------------------------------------------------------------------
class TestCreateNotification:
    """POST /api/v1/notifications"""

    def test_create_success(self, client: TestClient, tenant: Tenant, user: User):
        payload = _create_notification_payload(tenant.id, user.id)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["tenant_id"] == str(tenant.id)
        assert data["user_id"] == str(user.id)
        assert data["type"] == "deadline"
        assert data["severity"] == "info"
        assert data["title"] == "Blíži sa termín pre výkaz SP"
        assert data["message"] == "Termín pre mesačný výkaz SP je o 3 dni."
        assert data["is_read"] is False
        assert data["read_at"] is None
        assert "id" in data
        assert "created_at" in data

    def test_create_with_related_entity(self, client: TestClient, tenant: Tenant, user: User):
        related_id = str(uuid.uuid4())
        payload = _create_notification_payload(
            tenant.id,
            user.id,
            related_entity="payroll",
            related_entity_id=related_id,
        )
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["related_entity"] == "payroll"
        assert data["related_entity_id"] == related_id

    def test_create_missing_required_field(self, client: TestClient, tenant: Tenant, user: User):
        payload = _create_notification_payload(tenant.id, user.id)
        del payload["title"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_invalid_type(self, client: TestClient, tenant: Tenant, user: User):
        payload = _create_notification_payload(tenant.id, user.id, type="invalid_type")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_invalid_severity(self, client: TestClient, tenant: Tenant, user: User):
        payload = _create_notification_payload(tenant.id, user.id, severity="extreme")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET list — Paginated
# ---------------------------------------------------------------------------
class TestListNotifications:
    """GET /api/v1/notifications"""

    def test_list_empty(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        _insert_notification(db_session, tenant, user)
        _insert_notification(db_session, tenant, user, type="anomaly")

        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_pagination(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        for i in range(5):
            _insert_notification(db_session, tenant, user, title=f"Notif {i}")

        resp = client.get(BASE_URL, params={"skip": 2, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["skip"] == 2
        assert data["limit"] == 2

    def test_list_limit_max_100(self, client: TestClient):
        resp = client.get(BASE_URL, params={"limit": 101})
        assert resp.status_code == 422

    def test_list_invalid_skip(self, client: TestClient):
        resp = client.get(BASE_URL, params={"skip": -1})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET list — Filters
# ---------------------------------------------------------------------------
class TestListNotificationsFilters:
    """Tests for filter query parameters."""

    def test_filter_by_tenant_id(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        _insert_notification(db_session, tenant, user)

        resp = client.get(BASE_URL, params={"tenant_id": str(tenant.id)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

        resp2 = client.get(BASE_URL, params={"tenant_id": str(uuid.uuid4())})
        assert resp2.json()["total"] == 0

    def test_filter_by_user_id(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        _insert_notification(db_session, tenant, user)

        resp = client.get(BASE_URL, params={"user_id": str(user.id)})
        data = resp.json()
        assert data["total"] == 1

        resp2 = client.get(BASE_URL, params={"user_id": str(uuid.uuid4())})
        assert resp2.json()["total"] == 0

    def test_filter_by_is_read(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        _insert_notification(db_session, tenant, user)  # default is_read=False

        resp = client.get(BASE_URL, params={"is_read": "false"})
        assert resp.json()["total"] == 1

        resp2 = client.get(BASE_URL, params={"is_read": "true"})
        assert resp2.json()["total"] == 0

    def test_filter_by_type(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        _insert_notification(db_session, tenant, user, type="deadline")
        _insert_notification(db_session, tenant, user, type="anomaly")

        resp = client.get(BASE_URL, params={"type": "deadline"})
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["type"] == "deadline"

    def test_filter_by_severity(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        _insert_notification(db_session, tenant, user, severity="info")
        _insert_notification(db_session, tenant, user, severity="critical")

        resp = client.get(BASE_URL, params={"severity": "critical"})
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["severity"] == "critical"

    def test_filter_combined(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        _insert_notification(db_session, tenant, user, type="deadline", severity="info")
        _insert_notification(db_session, tenant, user, type="deadline", severity="critical")
        _insert_notification(db_session, tenant, user, type="anomaly", severity="info")

        resp = client.get(BASE_URL, params={"type": "deadline", "severity": "critical"})
        data = resp.json()
        assert data["total"] == 1


# ---------------------------------------------------------------------------
# GET detail
# ---------------------------------------------------------------------------
class TestGetNotification:
    """GET /api/v1/notifications/{notification_id}"""

    def test_get_existing(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        notif = _insert_notification(db_session, tenant, user)

        resp = client.get(f"{BASE_URL}/{notif.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(notif.id)
        assert data["title"] == "Test notification"

    def test_get_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Notification not found"

    def test_get_invalid_uuid(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH — Update
# ---------------------------------------------------------------------------
class TestUpdateNotification:
    """PATCH /api/v1/notifications/{notification_id}"""

    def test_update_single_field(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        notif = _insert_notification(db_session, tenant, user)

        resp = client.patch(f"{BASE_URL}/{notif.id}", json={"title": "Updated title"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated title"
        # Other fields unchanged
        assert data["message"] == "Test message body"

    def test_update_mark_as_read(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        notif = _insert_notification(db_session, tenant, user)

        resp = client.patch(f"{BASE_URL}/{notif.id}", json={"is_read": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_read"] is True
        assert data["read_at"] is not None  # server-side timestamp

    def test_update_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.patch(f"{BASE_URL}/{fake_id}", json={"title": "X"})
        assert resp.status_code == 404

    def test_update_multiple_fields(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        notif = _insert_notification(db_session, tenant, user)

        resp = client.patch(
            f"{BASE_URL}/{notif.id}",
            json={
                "severity": "critical",
                "message": "Updated message",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["severity"] == "critical"
        assert data["message"] == "Updated message"


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------
class TestDeleteNotification:
    """DELETE /api/v1/notifications/{notification_id}"""

    def test_delete_existing(self, client: TestClient, db_session: Session, tenant: Tenant, user: User):
        notif = _insert_notification(db_session, tenant, user)

        resp = client.delete(f"{BASE_URL}/{notif.id}")
        assert resp.status_code == 204

        # Verify gone
        get_resp = client.get(f"{BASE_URL}/{notif.id}")
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404

    def test_delete_invalid_uuid(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422
