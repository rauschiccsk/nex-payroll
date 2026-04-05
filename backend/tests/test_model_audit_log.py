"""Tests for AuditLog model (app.models.audit_log)."""

import uuid

import pytest
from sqlalchemy import TIMESTAMP, String, inspect, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.audit_log import AuditLog
from app.models.tenant import Tenant


def _make_tenant(db_session) -> Tenant:
    """Create a valid Tenant for FK references and return it."""
    tenant = Tenant(
        name="Audit Test s.r.o.",
        ico=str(uuid.uuid4().int)[:8],
        address_street="Testová 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000099",
        schema_name=f"tenant_{uuid.uuid4().hex[:12]}",
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


class TestAuditLogSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert AuditLog.__tablename__ == "audit_log"

    def test_schema_is_public(self):
        assert AuditLog.__table__.schema == "public"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(AuditLog, Base)


class TestAuditLogColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(AuditLog)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_tenant_id_column(self):
        col = self.mapper.columns["tenant_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_tenant_id_has_foreign_key(self):
        col = self.mapper.columns["tenant_id"]
        fk_targets = {fk.target_fullname for fk in col.foreign_keys}
        assert "public.tenants.id" in fk_targets

    def test_user_id_column(self):
        col = self.mapper.columns["user_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is True

    def test_action_column(self):
        col = self.mapper.columns["action"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False

    def test_entity_type_column(self):
        col = self.mapper.columns["entity_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert col.nullable is False

    def test_entity_id_column(self):
        col = self.mapper.columns["entity_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_old_values_column(self):
        col = self.mapper.columns["old_values"]
        assert isinstance(col.type, JSON)
        assert col.nullable is True

    def test_new_values_column(self):
        col = self.mapper.columns["new_values"]
        assert isinstance(col.type, JSON)
        assert col.nullable is True

    def test_ip_address_column(self):
        col = self.mapper.columns["ip_address"]
        assert isinstance(col.type, String)
        assert col.type.length == 45
        assert col.nullable is True

    def test_created_at_column(self):
        col = self.mapper.columns["created_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is False
        assert col.server_default is not None

    def test_no_updated_at_column(self):
        """AuditLog is immutable — no updated_at column."""
        col_names = [c.key for c in self.mapper.columns]
        assert "updated_at" not in col_names


class TestAuditLogIndexes:
    """Verify composite indexes on audit_log table."""

    def test_tenant_entity_index_exists(self):
        indexes = AuditLog.__table__.indexes
        idx_names = {idx.name for idx in indexes}
        assert "ix_audit_log_tenant_entity" in idx_names

    def test_tenant_entity_index_columns(self):
        indexes = AuditLog.__table__.indexes
        target = next(idx for idx in indexes if idx.name == "ix_audit_log_tenant_entity")
        col_names = [col.name for col in target.columns]
        assert col_names == ["tenant_id", "entity_type", "entity_id"]

    def test_tenant_created_index_exists(self):
        indexes = AuditLog.__table__.indexes
        idx_names = {idx.name for idx in indexes}
        assert "ix_audit_log_tenant_created" in idx_names

    def test_tenant_created_index_columns(self):
        indexes = AuditLog.__table__.indexes
        target = next(idx for idx in indexes if idx.name == "ix_audit_log_tenant_created")
        col_names = [col.name for col in target.columns]
        assert col_names == ["tenant_id", "created_at"]


class TestAuditLogConstraints:
    """Verify CHECK constraints on AuditLog model."""

    def test_action_check_constraint_exists(self):
        """Check constraint ck_audit_log_action must exist in table metadata."""
        constraints = AuditLog.__table__.constraints
        check_names = {c.name for c in constraints if hasattr(c, "sqltext")}
        assert "ck_audit_log_action" in check_names

    def test_action_check_constraint_rejects_invalid_value(self, db_session):
        """DB must reject action values outside ('CREATE', 'UPDATE', 'DELETE')."""
        tenant = _make_tenant(db_session)
        log_entry = AuditLog(
            tenant_id=tenant.id,
            action="INVALID",
            entity_type="tenants",
            entity_id=uuid.uuid4(),
        )
        db_session.add(log_entry)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_tenant_id_fk_rejects_invalid_tenant(self, db_session):
        """DB must reject tenant_id that does not reference an existing tenant."""
        log_entry = AuditLog(
            tenant_id=uuid.uuid4(),
            action="CREATE",
            entity_type="tenants",
            entity_id=uuid.uuid4(),
        )
        db_session.add(log_entry)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()


class TestAuditLogRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        entity_id = uuid.uuid4()
        log_entry = AuditLog(
            tenant_id=uuid.uuid4(),
            action="CREATE",
            entity_type="tenants",
            entity_id=entity_id,
        )

        result = repr(log_entry)
        assert "CREATE" in result
        assert "tenants" in result
        assert str(entity_id) in result


class TestAuditLogDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session):
        tenant = _make_tenant(db_session)
        entity_id = uuid.uuid4()
        log_entry = AuditLog(
            tenant_id=tenant.id,
            user_id=uuid.uuid4(),
            action="CREATE",
            entity_type="tenants",
            entity_id=entity_id,
            new_values={"name": "Test s.r.o.", "ico": "12345678"},
            ip_address="192.168.1.1",
        )
        db_session.add(log_entry)
        db_session.flush()

        assert log_entry.id is not None
        assert log_entry.created_at is not None
        assert log_entry.tenant_id == tenant.id
        assert log_entry.action == "CREATE"
        assert log_entry.entity_type == "tenants"
        assert log_entry.entity_id == entity_id
        assert log_entry.new_values == {"name": "Test s.r.o.", "ico": "12345678"}
        assert log_entry.old_values is None
        assert log_entry.ip_address == "192.168.1.1"

    def test_create_update_action(self, db_session):
        tenant = _make_tenant(db_session)
        entity_id = uuid.uuid4()
        log_entry = AuditLog(
            tenant_id=tenant.id,
            action="UPDATE",
            entity_type="employees",
            entity_id=entity_id,
            old_values={"name": "Old Name"},
            new_values={"name": "New Name"},
        )
        db_session.add(log_entry)
        db_session.flush()

        assert log_entry.action == "UPDATE"
        assert log_entry.old_values == {"name": "Old Name"}
        assert log_entry.new_values == {"name": "New Name"}

    def test_create_delete_action(self, db_session):
        tenant = _make_tenant(db_session)
        entity_id = uuid.uuid4()
        log_entry = AuditLog(
            tenant_id=tenant.id,
            action="DELETE",
            entity_type="contracts",
            entity_id=entity_id,
            old_values={"contract_number": "ZML-001"},
        )
        db_session.add(log_entry)
        db_session.flush()

        assert log_entry.action == "DELETE"
        assert log_entry.old_values == {"contract_number": "ZML-001"}
        assert log_entry.new_values is None

    def test_create_with_null_user_id(self, db_session):
        """System actions have NULL user_id."""
        tenant = _make_tenant(db_session)
        log_entry = AuditLog(
            tenant_id=tenant.id,
            user_id=None,
            action="CREATE",
            entity_type="tenants",
            entity_id=uuid.uuid4(),
        )
        db_session.add(log_entry)
        db_session.flush()

        assert log_entry.user_id is None

    def test_create_with_ipv6_address(self, db_session):
        tenant = _make_tenant(db_session)
        log_entry = AuditLog(
            tenant_id=tenant.id,
            action="UPDATE",
            entity_type="employees",
            entity_id=uuid.uuid4(),
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        )
        db_session.add(log_entry)
        db_session.flush()

        assert log_entry.ip_address == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"

    def test_fk_restrict_tenant_delete(self, db_session):
        """Cannot delete a tenant that has audit log entries (FK constraint)."""
        tenant = _make_tenant(db_session)
        log_entry = AuditLog(
            tenant_id=tenant.id,
            action="CREATE",
            entity_type="tenants",
            entity_id=uuid.uuid4(),
        )
        db_session.add(log_entry)
        db_session.flush()

        # Use raw SQL — ORM delete sets FK to NULL first (fails NOT NULL before FK check)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM public.tenants WHERE id = :id"),
                {"id": tenant.id},
            )
            db_session.flush()
        db_session.rollback()
