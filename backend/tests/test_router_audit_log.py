"""Tests for AuditLog router endpoints.

Verifies:
- GET /api/v1/audit-logs (list with pagination and filters)
- GET /api/v1/audit-logs/{entry_id} (single entry)
- POST /api/v1/audit-logs (create)
- PATCH /api/v1/audit-logs/{entry_id} (partial update — metadata only)
- DELETE /api/v1/audit-logs/{entry_id} (delete)
- Date range filtering (date_from / date_to)
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text

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
# GET /api/v1/audit-logs — date range filters
# ---------------------------------------------------------------------------


class TestListAuditLogsDateFilters:
    """Tests for date_from / date_to query parameters."""

    def test_filter_by_date_from(self, client, db_session, tenant):
        """Entries with created_at >= date_from are returned."""
        entry = _create_entry(db_session, tenant)
        # Set created_at to a known past timestamp
        db_session.execute(
            text("UPDATE audit_log SET created_at = :ts WHERE id = :id"),
            {"ts": datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC), "id": entry.id},
        )
        entry2 = _create_entry(db_session, tenant, action="UPDATE")
        db_session.execute(
            text("UPDATE audit_log SET created_at = :ts WHERE id = :id"),
            {"ts": datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC), "id": entry2.id},
        )
        db_session.flush()

        # Only the June entry should match
        resp = client.get("/api/v1/audit-logs?date_from=2024-06-01T00:00:00")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(entry2.id)

    def test_filter_by_date_to(self, client, db_session, tenant):
        """Entries with created_at <= date_to are returned."""
        entry = _create_entry(db_session, tenant)
        db_session.execute(
            text("UPDATE audit_log SET created_at = :ts WHERE id = :id"),
            {"ts": datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC), "id": entry.id},
        )
        entry2 = _create_entry(db_session, tenant, action="UPDATE")
        db_session.execute(
            text("UPDATE audit_log SET created_at = :ts WHERE id = :id"),
            {"ts": datetime(2024, 6, 15, 10, 0, 0, tzinfo=UTC), "id": entry2.id},
        )
        db_session.flush()

        # Only the January entry should match
        resp = client.get("/api/v1/audit-logs?date_to=2024-03-01T00:00:00")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(entry.id)

    def test_filter_by_date_range(self, client, db_session, tenant):
        """Combine date_from and date_to to select a window."""
        entry_jan = _create_entry(db_session, tenant)
        db_session.execute(
            text("UPDATE audit_log SET created_at = :ts WHERE id = :id"),
            {"ts": datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC), "id": entry_jan.id},
        )
        entry_apr = _create_entry(db_session, tenant, action="UPDATE")
        db_session.execute(
            text("UPDATE audit_log SET created_at = :ts WHERE id = :id"),
            {"ts": datetime(2024, 4, 15, 10, 0, 0, tzinfo=UTC), "id": entry_apr.id},
        )
        entry_oct = _create_entry(db_session, tenant, action="DELETE")
        db_session.execute(
            text("UPDATE audit_log SET created_at = :ts WHERE id = :id"),
            {"ts": datetime(2024, 10, 15, 10, 0, 0, tzinfo=UTC), "id": entry_oct.id},
        )
        db_session.flush()

        resp = client.get("/api/v1/audit-logs?date_from=2024-03-01T00:00:00&date_to=2024-06-01T00:00:00")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == str(entry_apr.id)

    def test_date_filter_combined_with_action(self, client, db_session, tenant):
        """Date filters work together with other filters."""
        entry1 = _create_entry(db_session, tenant, action="CREATE")
        db_session.execute(
            text("UPDATE audit_log SET created_at = :ts WHERE id = :id"),
            {"ts": datetime(2024, 5, 1, 10, 0, 0, tzinfo=UTC), "id": entry1.id},
        )
        entry2 = _create_entry(db_session, tenant, action="DELETE")
        db_session.execute(
            text("UPDATE audit_log SET created_at = :ts WHERE id = :id"),
            {"ts": datetime(2024, 5, 2, 10, 0, 0, tzinfo=UTC), "id": entry2.id},
        )
        db_session.flush()

        resp = client.get("/api/v1/audit-logs?date_from=2024-04-01T00:00:00&action=DELETE")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "DELETE"


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
# POST /api/v1/audit-logs — create
# ---------------------------------------------------------------------------


class TestCreateAuditLog:
    """Tests for the create endpoint."""

    def test_create_entry(self, client, db_session, tenant):
        entity_id = str(uuid4())
        payload = {
            "tenant_id": str(tenant.id),
            "action": "CREATE",
            "entity_type": "employees",
            "entity_id": entity_id,
            "new_values": {"first_name": "Ján"},
            "ip_address": "10.0.0.1",
        }
        resp = client.post("/api/v1/audit-logs", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["action"] == "CREATE"
        assert data["entity_type"] == "employees"
        assert data["entity_id"] == entity_id
        assert data["tenant_id"] == str(tenant.id)
        assert data["ip_address"] == "10.0.0.1"
        assert "id" in data
        assert "created_at" in data

    def test_create_entry_minimal(self, client, db_session, tenant):
        """Create with only required fields."""
        payload = {
            "tenant_id": str(tenant.id),
            "action": "DELETE",
            "entity_type": "contracts",
            "entity_id": str(uuid4()),
        }
        resp = client.post("/api/v1/audit-logs", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] is None
        assert data["old_values"] is None
        assert data["new_values"] is None
        assert data["ip_address"] is None

    def test_create_entry_invalid_payload(self, client):
        """Missing required fields returns 422."""
        resp = client.post("/api/v1/audit-logs", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/v1/audit-logs/{entry_id} — partial update (metadata only)
# ---------------------------------------------------------------------------


class TestUpdateAuditLog:
    """Tests for the PATCH endpoint — only metadata fields are mutable."""

    def test_update_ip_address(self, client, db_session, tenant):
        entry = _create_entry(db_session, tenant, ip_address="10.0.0.1")

        resp = client.patch(
            f"/api/v1/audit-logs/{entry.id}",
            json={"ip_address": "192.168.0.100"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ip_address"] == "192.168.0.100"
        # Identity fields unchanged
        assert data["action"] == "CREATE"
        assert data["entity_type"] == "employees"

    def test_update_old_values(self, client, db_session, tenant):
        entry = _create_entry(db_session, tenant, old_values=None)

        resp = client.patch(
            f"/api/v1/audit-logs/{entry.id}",
            json={"old_values": {"status": "active"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["old_values"] == {"status": "active"}

    def test_update_new_values(self, client, db_session, tenant):
        entry = _create_entry(db_session, tenant)

        resp = client.patch(
            f"/api/v1/audit-logs/{entry.id}",
            json={"new_values": {"first_name": "Peter"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_values"] == {"first_name": "Peter"}

    def test_update_nonexistent_returns_404(self, client):
        resp = client.patch(
            f"/api/v1/audit-logs/{uuid4()}",
            json={"ip_address": "10.0.0.1"},
        )
        assert resp.status_code == 404

    def test_update_empty_payload_no_change(self, client, db_session, tenant):
        """Empty payload should return the entry unchanged."""
        entry = _create_entry(db_session, tenant, ip_address="10.0.0.1")

        resp = client.patch(
            f"/api/v1/audit-logs/{entry.id}",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ip_address"] == "10.0.0.1"


# ---------------------------------------------------------------------------
# DELETE /api/v1/audit-logs/{entry_id}
# ---------------------------------------------------------------------------


class TestDeleteAuditLog:
    """Tests for the DELETE endpoint."""

    def test_delete_existing(self, client, db_session, tenant):
        entry = _create_entry(db_session, tenant)

        resp = client.delete(f"/api/v1/audit-logs/{entry.id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp2 = client.get(f"/api/v1/audit-logs/{entry.id}")
        assert resp2.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete(f"/api/v1/audit-logs/{uuid4()}")
        assert resp.status_code == 404
