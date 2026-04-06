"""Tests for AuditLog router endpoints.

Verifies:
- GET /api/v1/audit-logs (list with pagination and filters)
- GET /api/v1/audit-logs/{entry_id} (single entry)
- No POST, PUT, DELETE endpoints exposed (immutable audit trail)
"""

from uuid import uuid4

import pytest

from app.models.audit_log import AuditLog
from app.models.tenant import Tenant


@pytest.fixture()
def tenant(db_session) -> Tenant:
    """Create a tenant required by AuditLog FK constraint."""
    t = Tenant(
        name="Test Firma s.r.o.",
        ico="99999999",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        address_country="SK",
        bank_iban="SK8975000000000012345678",
        schema_name="tenant_test_firma_99999999",
    )
    db_session.add(t)
    db_session.flush()
    return t


def _create_entry(db_session, tenant, **overrides) -> AuditLog:
    """Insert an AuditLog row directly for test setup."""
    defaults = {
        "tenant_id": tenant.id,
        "user_id": None,
        "action": "CREATE",
        "entity_type": "employees",
        "entity_id": uuid4(),
        "old_values": None,
        "new_values": {"first_name": "Ján"},
        "ip_address": "192.168.1.1",
    }
    defaults.update(overrides)
    entry = AuditLog(**defaults)
    db_session.add(entry)
    db_session.flush()
    return entry


# ---------------------------------------------------------------------------
# GET /api/v1/audit-logs — list with pagination
# ---------------------------------------------------------------------------


class TestListAuditLogs:
    """Tests for the list endpoint."""

    def test_list_empty(self, client):
        resp = client.get("/api/v1/audit-logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_entries(self, client, db_session, tenant):
        _create_entry(db_session, tenant)
        _create_entry(db_session, tenant, action="DELETE")

        resp = client.get("/api/v1/audit-logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_pagination(self, client, db_session, tenant):
        for _ in range(5):
            _create_entry(db_session, tenant)

        resp = client.get("/api/v1/audit-logs?skip=2&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["skip"] == 2
        assert data["limit"] == 2

    def test_list_limit_max_100(self, client):
        resp = client.get("/api/v1/audit-logs?limit=200")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/audit-logs — filters
# ---------------------------------------------------------------------------


class TestListAuditLogsFilters:
    """Tests for filter query parameters."""

    def test_filter_by_tenant_id(self, client, db_session, tenant):
        _create_entry(db_session, tenant)

        resp = client.get(f"/api/v1/audit-logs?tenant_id={tenant.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

        resp2 = client.get(f"/api/v1/audit-logs?tenant_id={uuid4()}")
        assert resp2.json()["total"] == 0

    def test_filter_by_entity_type(self, client, db_session, tenant):
        _create_entry(db_session, tenant, entity_type="employees")
        _create_entry(db_session, tenant, entity_type="contracts")

        resp = client.get("/api/v1/audit-logs?entity_type=employees")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_type"] == "employees"

    def test_filter_by_action(self, client, db_session, tenant):
        _create_entry(db_session, tenant, action="CREATE")
        _create_entry(db_session, tenant, action="DELETE")

        resp = client.get("/api/v1/audit-logs?action=DELETE")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "DELETE"

    def test_filter_by_entity_id(self, client, db_session, tenant):
        target_id = uuid4()
        _create_entry(db_session, tenant, entity_id=target_id)
        _create_entry(db_session, tenant)

        resp = client.get(f"/api/v1/audit-logs?entity_id={target_id}")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_id"] == str(target_id)

    def test_filter_by_user_id(self, client, db_session, tenant):
        uid = uuid4()
        _create_entry(db_session, tenant, user_id=uid)
        _create_entry(db_session, tenant, user_id=None)

        resp = client.get(f"/api/v1/audit-logs?user_id={uid}")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == str(uid)

    def test_filter_combined(self, client, db_session, tenant):
        _create_entry(db_session, tenant, action="CREATE", entity_type="employees")
        _create_entry(db_session, tenant, action="UPDATE", entity_type="employees")
        _create_entry(db_session, tenant, action="CREATE", entity_type="contracts")

        resp = client.get("/api/v1/audit-logs?action=CREATE&entity_type=employees")
        data = resp.json()
        assert data["total"] == 1

    def test_filter_count_matches_items(self, client, db_session, tenant):
        """Total count must match the filtered result, not the unfiltered total."""
        _create_entry(db_session, tenant, action="CREATE")
        _create_entry(db_session, tenant, action="CREATE")
        _create_entry(db_session, tenant, action="DELETE")

        resp = client.get("/api/v1/audit-logs?action=CREATE")
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# GET /api/v1/audit-logs/{entry_id} — single entry
# ---------------------------------------------------------------------------


class TestGetAuditLog:
    """Tests for the detail endpoint."""

    def test_get_existing(self, client, db_session, tenant):
        entry = _create_entry(db_session, tenant)

        resp = client.get(f"/api/v1/audit-logs/{entry.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(entry.id)
        assert data["action"] == "CREATE"
        assert data["entity_type"] == "employees"

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get(f"/api/v1/audit-logs/{uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Immutability — no POST, PUT, DELETE
# ---------------------------------------------------------------------------


class TestImmutability:
    """Verify that no mutating endpoints exist."""

    def test_post_not_allowed(self, client):
        resp = client.post(
            "/api/v1/audit-logs",
            json={
                "tenant_id": str(uuid4()),
                "action": "CREATE",
                "entity_type": "employees",
                "entity_id": str(uuid4()),
            },
        )
        assert resp.status_code == 405

    def test_put_not_allowed(self, client):
        resp = client.put(
            f"/api/v1/audit-logs/{uuid4()}",
            json={
                "ip_address": "10.0.0.1",
            },
        )
        assert resp.status_code == 405

    def test_delete_not_allowed(self, client):
        resp = client.delete(f"/api/v1/audit-logs/{uuid4()}")
        assert resp.status_code == 405
