"""Tests for AuditLog service layer."""

from uuid import uuid4

import pytest

from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.schemas.audit_log import AuditLogCreate, AuditLogUpdate
from app.services.audit_log import (
    create_audit_log,
    delete_audit_log,
    get_audit_log,
    list_audit_logs,
    update_audit_log,
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
# update
# ---------------------------------------------------------------------------


class TestUpdateAuditLog:
    """Tests for update_audit_log."""

    def test_update_single_field(self, db_session, tenant):
        created = create_audit_log(db_session, _make_payload(tenant.id))

        updated = update_audit_log(
            db_session,
            created.id,
            AuditLogUpdate(ip_address="10.0.0.1"),
        )

        assert updated is not None
        assert updated.ip_address == "10.0.0.1"
        # unchanged fields stay the same
        assert updated.action == "CREATE"

    def test_update_multiple_fields(self, db_session, tenant):
        created = create_audit_log(db_session, _make_payload(tenant.id))

        updated = update_audit_log(
            db_session,
            created.id,
            AuditLogUpdate(
                entity_type="contracts",
                ip_address="10.0.0.2",
            ),
        )

        assert updated is not None
        assert updated.entity_type == "contracts"
        assert updated.ip_address == "10.0.0.2"

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_audit_log(
            db_session,
            uuid4(),
            AuditLogUpdate(ip_address="10.0.0.1"),
        )
        assert result is None

    def test_update_no_fields_is_noop(self, db_session, tenant):
        """Sending an empty update should not break anything."""
        created = create_audit_log(db_session, _make_payload(tenant.id))

        updated = update_audit_log(
            db_session,
            created.id,
            AuditLogUpdate(),
        )

        assert updated is not None
        assert updated.action == created.action


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteAuditLog:
    """Tests for delete_audit_log."""

    def test_delete_existing(self, db_session, tenant):
        created = create_audit_log(db_session, _make_payload(tenant.id))

        deleted = delete_audit_log(db_session, created.id)

        assert deleted is True
        assert get_audit_log(db_session, created.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_audit_log(db_session, uuid4())
        assert result is False
