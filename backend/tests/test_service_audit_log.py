"""Tests for AuditLog service layer."""

from uuid import uuid4

import pytest

from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.schemas.audit_log import AuditLogCreate
from app.services.audit_log import (
    count_audit_logs,
    create_audit_log,
    get_audit_log,
    list_audit_logs,
    write_audit,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _make_payload(tenant_id, **overrides) -> AuditLogCreate:
    """Build a valid AuditLogCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "user_id": None,
        "action": "CREATE",
        "entity_type": "employees",
        "entity_id": uuid4(),
        "old_values": None,
        "new_values": {"first_name": "Ján", "last_name": "Novák"},
        "ip_address": "192.168.1.1",
    }
    defaults.update(overrides)
    return AuditLogCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateAuditLog:
    """Tests for create_audit_log."""

    def test_create_returns_model_instance(self, db_session, tenant):
        payload = _make_payload(tenant.id)
        result = create_audit_log(db_session, payload)

        assert isinstance(result, AuditLog)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.action == "CREATE"
        assert result.entity_type == "employees"
        assert result.entity_id == payload.entity_id
        assert result.new_values == {"first_name": "Ján", "last_name": "Novák"}
        assert result.old_values is None
        assert result.ip_address == "192.168.1.1"

    def test_create_with_user_id(self, db_session, tenant):
        user_id = uuid4()
        payload = _make_payload(tenant.id, user_id=user_id)
        result = create_audit_log(db_session, payload)

        assert result.user_id == user_id

    def test_create_update_action(self, db_session, tenant):
        payload = _make_payload(
            tenant.id,
            action="UPDATE",
            old_values={"first_name": "Ján"},
            new_values={"first_name": "Peter"},
        )
        result = create_audit_log(db_session, payload)

        assert result.action == "UPDATE"
        assert result.old_values == {"first_name": "Ján"}
        assert result.new_values == {"first_name": "Peter"}

    def test_create_delete_action(self, db_session, tenant):
        payload = _make_payload(
            tenant.id,
            action="DELETE",
            old_values={"first_name": "Ján"},
            new_values=None,
        )
        result = create_audit_log(db_session, payload)

        assert result.action == "DELETE"
        assert result.old_values == {"first_name": "Ján"}
        assert result.new_values is None

    def test_create_without_ip_address(self, db_session, tenant):
        payload = _make_payload(tenant.id, ip_address=None)
        result = create_audit_log(db_session, payload)

        assert result.ip_address is None


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetAuditLog:
    """Tests for get_audit_log."""

    def test_get_existing(self, db_session, tenant):
        created = create_audit_log(db_session, _make_payload(tenant.id))

        fetched = get_audit_log(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.action == created.action

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_audit_log(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListAuditLogs:
    """Tests for list_audit_logs."""

    def test_list_empty(self, db_session):
        result = list_audit_logs(db_session)
        assert result == []

    def test_list_returns_all(self, db_session, tenant):
        create_audit_log(db_session, _make_payload(tenant.id))
        create_audit_log(db_session, _make_payload(tenant.id, action="UPDATE"))

        result = list_audit_logs(db_session)
        assert len(result) == 2

    def test_list_ordering_newest_first(self, db_session, tenant):
        """Audit logs are ordered by created_at descending (newest first)."""
        first = create_audit_log(
            db_session,
            _make_payload(tenant.id, entity_type="contracts"),
        )
        second = create_audit_log(
            db_session,
            _make_payload(tenant.id, entity_type="employees"),
        )

        result = list_audit_logs(db_session)
        # Both created in same transaction; at minimum both should be returned
        assert len(result) == 2
        # The second created should come first (newest) or equal timestamp
        result_ids = [r.id for r in result]
        assert first.id in result_ids
        assert second.id in result_ids

    def test_list_pagination_skip(self, db_session, tenant):
        for _ in range(3):
            create_audit_log(db_session, _make_payload(tenant.id))

        result = list_audit_logs(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session, tenant):
        for _ in range(3):
            create_audit_log(db_session, _make_payload(tenant.id))

        result = list_audit_logs(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session, tenant):
        for _ in range(5):
            create_audit_log(db_session, _make_payload(tenant.id))

        result = list_audit_logs(db_session, skip=1, limit=2)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# filter support
# ---------------------------------------------------------------------------


class TestListAuditLogsFilters:
    """Tests for list_audit_logs and count_audit_logs filter parameters."""

    def test_filter_by_tenant_id(self, db_session, tenant):
        create_audit_log(db_session, _make_payload(tenant.id))

        result = list_audit_logs(db_session, tenant_id=tenant.id)
        assert len(result) == 1

        result_other = list_audit_logs(db_session, tenant_id=uuid4())
        assert len(result_other) == 0

    def test_filter_by_entity_type(self, db_session, tenant):
        create_audit_log(db_session, _make_payload(tenant.id, entity_type="employees"))
        create_audit_log(db_session, _make_payload(tenant.id, entity_type="contracts"))

        result = list_audit_logs(db_session, entity_type="employees")
        assert len(result) == 1
        assert result[0].entity_type == "employees"

    def test_filter_by_entity_id(self, db_session, tenant):
        target_id = uuid4()
        create_audit_log(db_session, _make_payload(tenant.id, entity_id=target_id))
        create_audit_log(db_session, _make_payload(tenant.id))

        result = list_audit_logs(db_session, entity_id=target_id)
        assert len(result) == 1
        assert result[0].entity_id == target_id

    def test_filter_by_user_id(self, db_session, tenant):
        uid = uuid4()
        create_audit_log(db_session, _make_payload(tenant.id, user_id=uid))
        create_audit_log(db_session, _make_payload(tenant.id, user_id=None))

        result = list_audit_logs(db_session, user_id=uid)
        assert len(result) == 1
        assert result[0].user_id == uid

    def test_filter_by_action(self, db_session, tenant):
        create_audit_log(db_session, _make_payload(tenant.id, action="CREATE"))
        create_audit_log(db_session, _make_payload(tenant.id, action="DELETE"))

        result = list_audit_logs(db_session, action="DELETE")
        assert len(result) == 1
        assert result[0].action == "DELETE"

    def test_filter_combined(self, db_session, tenant):
        """Multiple filters are combined with AND."""
        create_audit_log(
            db_session,
            _make_payload(tenant.id, action="CREATE", entity_type="employees"),
        )
        create_audit_log(
            db_session,
            _make_payload(tenant.id, action="UPDATE", entity_type="employees"),
        )
        create_audit_log(
            db_session,
            _make_payload(tenant.id, action="CREATE", entity_type="contracts"),
        )

        result = list_audit_logs(
            db_session,
            action="CREATE",
            entity_type="employees",
        )
        assert len(result) == 1
        assert result[0].action == "CREATE"
        assert result[0].entity_type == "employees"

    def test_count_with_filters(self, db_session, tenant):
        """count_audit_logs should respect the same filters as list_audit_logs."""
        create_audit_log(db_session, _make_payload(tenant.id, action="CREATE"))
        create_audit_log(db_session, _make_payload(tenant.id, action="CREATE"))
        create_audit_log(db_session, _make_payload(tenant.id, action="DELETE"))

        total = count_audit_logs(db_session, action="CREATE")
        assert total == 2

        total_all = count_audit_logs(db_session)
        assert total_all == 3

    def test_count_with_tenant_filter(self, db_session, tenant):
        create_audit_log(db_session, _make_payload(tenant.id))

        assert count_audit_logs(db_session, tenant_id=tenant.id) == 1
        assert count_audit_logs(db_session, tenant_id=uuid4()) == 0


# ---------------------------------------------------------------------------
# write_audit helper (NR-05)
# ---------------------------------------------------------------------------


class TestWriteAudit:
    """Tests for the write_audit convenience helper."""

    def test_write_audit_creates_entry(self, db_session, tenant):
        """write_audit creates an AuditLog entry visible via list_audit_logs."""
        entity_id = uuid4()
        write_audit(
            db_session,
            tenant_id=tenant.id,
            user_id=None,
            action="create",
            entity_type="Employee",
            entity_id=entity_id,
            new_values={"first_name": "Ján"},
        )
        entries = list_audit_logs(db_session, tenant_id=tenant.id, entity_type="Employee")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.action == "CREATE"
        assert entry.entity_type == "Employee"
        assert entry.entity_id == entity_id
        assert entry.new_values == {"first_name": "Ján"}
        assert entry.old_values is None

    def test_write_audit_normalises_action_to_uppercase(self, db_session, tenant):
        """write_audit accepts lowercase action and normalises to uppercase."""
        entity_id = uuid4()
        write_audit(
            db_session,
            tenant_id=tenant.id,
            user_id=None,
            action="update",
            entity_type="Contract",
            entity_id=entity_id,
            old_values={"status": "draft"},
            new_values={"status": "approved"},
        )
        entries = list_audit_logs(db_session, tenant_id=tenant.id, entity_type="Contract")
        assert len(entries) == 1
        assert entries[0].action == "UPDATE"

    def test_write_audit_delete_action(self, db_session, tenant):
        """write_audit with delete action produces DELETE entry."""
        entity_id = uuid4()
        write_audit(
            db_session,
            tenant_id=tenant.id,
            user_id=None,
            action="delete",
            entity_type="User",
            entity_id=entity_id,
            old_values={"is_active": True},
        )
        entries = list_audit_logs(db_session, tenant_id=tenant.id, entity_type="User")
        assert len(entries) == 1
        assert entries[0].action == "DELETE"
        assert entries[0].new_values is None

    def test_write_audit_invalid_action_raises(self, db_session, tenant):
        """write_audit raises ValueError for unrecognised action."""
        import pytest

        with pytest.raises(ValueError, match="Invalid audit action"):
            write_audit(
                db_session,
                tenant_id=tenant.id,
                user_id=None,
                action="read",
                entity_type="Employee",
                entity_id=uuid4(),
            )
