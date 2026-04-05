"""Tests for AuditLog Pydantic schemas."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.audit_log import (
    AuditLogCreate,
    AuditLogRead,
    AuditLogUpdate,
)

# ---------------------------------------------------------------------------
# AuditLogCreate
# ---------------------------------------------------------------------------


class TestAuditLogCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        schema = AuditLogCreate(
            tenant_id=uuid4(),
            action="CREATE",
            entity_type="employees",
            entity_id=uuid4(),
        )
        assert schema.user_id is None
        assert schema.old_values is None
        assert schema.new_values is None
        assert schema.ip_address is None

    def test_valid_full(self):
        tenant_id = uuid4()
        user_id = uuid4()
        entity_id = uuid4()
        schema = AuditLogCreate(
            tenant_id=tenant_id,
            user_id=user_id,
            action="UPDATE",
            entity_type="contracts",
            entity_id=entity_id,
            old_values={"base_wage": "1200.00"},
            new_values={"base_wage": "1500.00"},
            ip_address="192.168.1.1",
        )
        assert schema.tenant_id == tenant_id
        assert schema.user_id == user_id
        assert schema.action == "UPDATE"
        assert schema.entity_type == "contracts"
        assert schema.entity_id == entity_id
        assert schema.old_values == {"base_wage": "1200.00"}
        assert schema.new_values == {"base_wage": "1500.00"}
        assert schema.ip_address == "192.168.1.1"

    def test_valid_delete_action(self):
        schema = AuditLogCreate(
            tenant_id=uuid4(),
            action="DELETE",
            entity_type="employees",
            entity_id=uuid4(),
            old_values={"first_name": "Ján", "last_name": "Novák"},
        )
        assert schema.action == "DELETE"
        assert schema.new_values is None

    def test_missing_required_tenant_id(self):
        with pytest.raises(ValidationError) as exc_info:
            AuditLogCreate(
                action="CREATE",
                entity_type="employees",
                entity_id=uuid4(),
            )
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_action(self):
        with pytest.raises(ValidationError) as exc_info:
            AuditLogCreate(
                tenant_id=uuid4(),
                entity_type="employees",
                entity_id=uuid4(),
            )
        assert "action" in str(exc_info.value)

    def test_missing_required_entity_type(self):
        with pytest.raises(ValidationError) as exc_info:
            AuditLogCreate(
                tenant_id=uuid4(),
                action="CREATE",
                entity_id=uuid4(),
            )
        assert "entity_type" in str(exc_info.value)

    def test_missing_required_entity_id(self):
        with pytest.raises(ValidationError) as exc_info:
            AuditLogCreate(
                tenant_id=uuid4(),
                action="CREATE",
                entity_type="employees",
            )
        assert "entity_id" in str(exc_info.value)

    def test_invalid_action_literal(self):
        with pytest.raises(ValidationError) as exc_info:
            AuditLogCreate(
                tenant_id=uuid4(),
                action="INVALID",
                entity_type="employees",
                entity_id=uuid4(),
            )
        assert "action" in str(exc_info.value)

    def test_entity_type_max_length(self):
        with pytest.raises(ValidationError):
            AuditLogCreate(
                tenant_id=uuid4(),
                action="CREATE",
                entity_type="x" * 101,
                entity_id=uuid4(),
            )

    def test_ip_address_max_length(self):
        with pytest.raises(ValidationError):
            AuditLogCreate(
                tenant_id=uuid4(),
                action="CREATE",
                entity_type="employees",
                entity_id=uuid4(),
                ip_address="x" * 46,
            )

    def test_ipv6_address(self):
        schema = AuditLogCreate(
            tenant_id=uuid4(),
            action="CREATE",
            entity_type="employees",
            entity_id=uuid4(),
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        )
        assert schema.ip_address == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"


# ---------------------------------------------------------------------------
# AuditLogUpdate
# ---------------------------------------------------------------------------


class TestAuditLogUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        schema = AuditLogUpdate()
        assert schema.tenant_id is None
        assert schema.user_id is None
        assert schema.action is None
        assert schema.entity_type is None
        assert schema.entity_id is None
        assert schema.old_values is None
        assert schema.new_values is None
        assert schema.ip_address is None

    def test_partial_update(self):
        schema = AuditLogUpdate(
            ip_address="10.0.0.1",
        )
        assert schema.ip_address == "10.0.0.1"
        assert schema.tenant_id is None
        assert schema.action is None

    def test_update_entity_type_max_length(self):
        with pytest.raises(ValidationError):
            AuditLogUpdate(entity_type="x" * 101)

    def test_update_ip_address_max_length(self):
        with pytest.raises(ValidationError):
            AuditLogUpdate(ip_address="x" * 46)

    def test_update_invalid_action_literal(self):
        with pytest.raises(ValidationError):
            AuditLogUpdate(action="INVALID")

    def test_update_valid_action(self):
        schema = AuditLogUpdate(action="DELETE")
        assert schema.action == "DELETE"


# ---------------------------------------------------------------------------
# AuditLogRead
# ---------------------------------------------------------------------------


class TestAuditLogRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        now = datetime(2025, 6, 1, 12, 0, 0)
        uid = uuid4()
        tenant_id = uuid4()
        user_id = uuid4()
        entity_id = uuid4()
        schema = AuditLogRead(
            id=uid,
            tenant_id=tenant_id,
            user_id=user_id,
            action="CREATE",
            entity_type="employees",
            entity_id=entity_id,
            old_values=None,
            new_values={"first_name": "Ján"},
            ip_address="192.168.1.1",
            created_at=now,
        )
        assert schema.id == uid
        assert schema.tenant_id == tenant_id
        assert schema.user_id == user_id
        assert schema.action == "CREATE"
        assert schema.entity_type == "employees"
        assert schema.entity_id == entity_id
        assert schema.old_values is None
        assert schema.new_values == {"first_name": "Ján"}
        assert schema.ip_address == "192.168.1.1"
        assert schema.created_at == now

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.tenant_id = uuid4()
                self.user_id = None
                self.action = "DELETE"
                self.entity_type = "contracts"
                self.entity_id = uuid4()
                self.old_values = {"job_title": "Developer"}
                self.new_values = None
                self.ip_address = None
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = AuditLogRead.model_validate(orm_obj)
        assert schema.action == "DELETE"
        assert schema.entity_type == "contracts"
        assert schema.user_id is None
        assert schema.old_values == {"job_title": "Developer"}
        assert schema.new_values is None
        assert schema.ip_address is None

    def test_serialisation_roundtrip(self):
        uid = uuid4()
        tenant_id = uuid4()
        entity_id = uuid4()
        now = datetime(2025, 6, 1, 12, 0, 0)
        data = {
            "id": uid,
            "tenant_id": tenant_id,
            "user_id": None,
            "action": "UPDATE",
            "entity_type": "payrolls",
            "entity_id": entity_id,
            "old_values": {"status": "draft"},
            "new_values": {"status": "approved"},
            "ip_address": "10.0.0.1",
            "created_at": now,
        }
        schema = AuditLogRead(**data)
        dumped = schema.model_dump()
        assert dumped["id"] == uid
        assert dumped["tenant_id"] == tenant_id
        assert dumped["action"] == "UPDATE"
        assert dumped["entity_type"] == "payrolls"
        assert dumped["old_values"] == {"status": "draft"}
        assert dumped["new_values"] == {"status": "approved"}
        assert dumped["ip_address"] == "10.0.0.1"

    def test_nullable_fields(self):
        schema = AuditLogRead(
            id=uuid4(),
            tenant_id=uuid4(),
            user_id=None,
            action="CREATE",
            entity_type="employees",
            entity_id=uuid4(),
            old_values=None,
            new_values=None,
            ip_address=None,
            created_at=datetime(2025, 1, 1, 0, 0, 0),
        )
        assert schema.user_id is None
        assert schema.old_values is None
        assert schema.new_values is None
        assert schema.ip_address is None
