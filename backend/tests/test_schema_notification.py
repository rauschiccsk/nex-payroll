"""Tests for Notification Pydantic schemas (Create, Update, Read)."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.notification import (
    NotificationCreate,
    NotificationRead,
    NotificationUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_USER_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for NotificationCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "user_id": _USER_ID,
        "type": "deadline",
        "title": "Blíži sa termín pre výkaz SP",
        "message": "Termín pre mesačný výkaz SP je o 3 dni.",
    }


def _read_kwargs() -> dict:
    """Return a complete dict for constructing NotificationRead."""
    now = datetime(2025, 6, 1, 12, 0, 0)
    return {
        "id": uuid4(),
        "tenant_id": _TENANT_ID,
        "user_id": _USER_ID,
        "type": "deadline",
        "severity": "info",
        "title": "Blíži sa termín pre výkaz SP",
        "message": "Termín pre mesačný výkaz SP je o 3 dni.",
        "related_entity": "payroll",
        "related_entity_id": uuid4(),
        "is_read": False,
        "read_at": None,
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# NotificationCreate
# ---------------------------------------------------------------------------


class TestNotificationCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        """Valid creation with only required fields — defaults applied."""
        schema = NotificationCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.user_id == _USER_ID
        assert schema.type == "deadline"
        assert schema.title == "Blíži sa termín pre výkaz SP"
        assert schema.message == "Termín pre mesačný výkaz SP je o 3 dni."
        # defaults
        assert schema.severity == "info"
        assert schema.related_entity is None
        assert schema.related_entity_id is None

    def test_valid_full(self):
        """Valid creation with all fields explicitly set."""
        entity_id = uuid4()
        schema = NotificationCreate(
            **_valid_create_kwargs(),
            severity="critical",
            related_entity="payroll",
            related_entity_id=entity_id,
        )
        assert schema.severity == "critical"
        assert schema.related_entity == "payroll"
        assert schema.related_entity_id == entity_id

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_user_id(self):
        kw = _valid_create_kwargs()
        del kw["user_id"]
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(**kw)
        assert "user_id" in str(exc_info.value)

    def test_missing_required_type(self):
        kw = _valid_create_kwargs()
        del kw["type"]
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(**kw)
        assert "type" in str(exc_info.value)

    def test_missing_required_title(self):
        kw = _valid_create_kwargs()
        del kw["title"]
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(**kw)
        assert "title" in str(exc_info.value)

    def test_missing_required_message(self):
        kw = _valid_create_kwargs()
        del kw["message"]
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(**kw)
        assert "message" in str(exc_info.value)

    # -- Literal constraints --

    def test_invalid_type_rejected(self):
        """Invalid notification type must be rejected."""
        kw = _valid_create_kwargs()
        kw["type"] = "invalid_type"
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(**kw)
        assert "type" in str(exc_info.value)

    def test_invalid_severity_rejected(self):
        """Invalid severity value must be rejected."""
        kw = _valid_create_kwargs()
        kw["severity"] = "low"
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(**kw)
        assert "severity" in str(exc_info.value)

    def test_all_valid_types_accepted(self):
        """All four valid notification types must be accepted."""
        for ntype in ("deadline", "anomaly", "system", "approval"):
            kw = _valid_create_kwargs()
            kw["type"] = ntype
            schema = NotificationCreate(**kw)
            assert schema.type == ntype

    def test_all_valid_severities_accepted(self):
        """All three valid severity levels must be accepted."""
        for sev in ("info", "warning", "critical"):
            kw = _valid_create_kwargs()
            kw["severity"] = sev
            schema = NotificationCreate(**kw)
            assert schema.severity == sev

    # -- max_length constraints --

    def test_title_max_length_exceeded(self):
        """Title exceeding 200 characters must be rejected."""
        kw = _valid_create_kwargs()
        kw["title"] = "A" * 201
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(**kw)
        assert "title" in str(exc_info.value)

    def test_title_max_length_accepted(self):
        """Title at exactly 200 characters must be accepted."""
        kw = _valid_create_kwargs()
        kw["title"] = "A" * 200
        schema = NotificationCreate(**kw)
        assert len(schema.title) == 200

    def test_related_entity_max_length_exceeded(self):
        """related_entity exceeding 50 characters must be rejected."""
        kw = _valid_create_kwargs()
        kw["related_entity"] = "X" * 51
        with pytest.raises(ValidationError) as exc_info:
            NotificationCreate(**kw)
        assert "related_entity" in str(exc_info.value)

    def test_related_entity_max_length_accepted(self):
        """related_entity at exactly 50 characters must be accepted."""
        kw = _valid_create_kwargs()
        kw["related_entity"] = "X" * 50
        schema = NotificationCreate(**kw)
        assert len(schema.related_entity) == 50

    # -- is_read / read_at excluded from Create --

    def test_create_excludes_is_read(self):
        """is_read is not a create-time field — should not exist on Create schema."""
        assert "is_read" not in NotificationCreate.model_fields

    def test_create_excludes_read_at(self):
        """read_at is not a create-time field — should not exist on Create schema."""
        assert "read_at" not in NotificationCreate.model_fields


# ---------------------------------------------------------------------------
# NotificationUpdate
# ---------------------------------------------------------------------------


class TestNotificationUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        """All fields default to None when no data supplied."""
        schema = NotificationUpdate()
        assert schema.type is None
        assert schema.severity is None
        assert schema.title is None
        assert schema.message is None
        assert schema.related_entity is None
        assert schema.related_entity_id is None
        assert schema.is_read is None
        assert schema.read_at is None

    def test_partial_update_is_read(self):
        """Only is_read supplied; the rest remain None."""
        schema = NotificationUpdate(is_read=True)
        assert schema.is_read is True
        assert schema.type is None
        assert schema.severity is None

    def test_partial_update_type(self):
        schema = NotificationUpdate(type="anomaly")
        assert schema.type == "anomaly"
        assert schema.severity is None

    def test_partial_update_severity(self):
        schema = NotificationUpdate(severity="critical")
        assert schema.severity == "critical"
        assert schema.type is None

    def test_full_update(self):
        """All fields explicitly set."""
        now = datetime(2025, 7, 1, 10, 0, 0)
        entity_id = uuid4()
        schema = NotificationUpdate(
            type="system",
            severity="warning",
            title="Updated title",
            message="Updated message body",
            related_entity="leave",
            related_entity_id=entity_id,
            is_read=True,
            read_at=now,
        )
        assert schema.type == "system"
        assert schema.severity == "warning"
        assert schema.title == "Updated title"
        assert schema.message == "Updated message body"
        assert schema.related_entity == "leave"
        assert schema.related_entity_id == entity_id
        assert schema.is_read is True
        assert schema.read_at == now

    # -- Literal constraints in update --

    def test_update_invalid_type_rejected(self):
        """Invalid notification type must be rejected in Update."""
        with pytest.raises(ValidationError) as exc_info:
            NotificationUpdate(type="invalid")
        assert "type" in str(exc_info.value)

    def test_update_invalid_severity_rejected(self):
        """Invalid severity must be rejected in Update."""
        with pytest.raises(ValidationError) as exc_info:
            NotificationUpdate(severity="low")
        assert "severity" in str(exc_info.value)

    # -- max_length in update --

    def test_update_title_max_length_exceeded(self):
        with pytest.raises(ValidationError) as exc_info:
            NotificationUpdate(title="A" * 201)
        assert "title" in str(exc_info.value)

    def test_update_related_entity_max_length_exceeded(self):
        with pytest.raises(ValidationError) as exc_info:
            NotificationUpdate(related_entity="X" * 51)
        assert "related_entity" in str(exc_info.value)

    # -- no immutable fields --

    def test_update_excludes_tenant_id(self):
        """tenant_id is not updatable — field should not exist on Update schema."""
        assert "tenant_id" not in NotificationUpdate.model_fields

    def test_update_excludes_user_id(self):
        """user_id is not updatable — field should not exist on Update schema."""
        assert "user_id" not in NotificationUpdate.model_fields


# ---------------------------------------------------------------------------
# NotificationRead
# ---------------------------------------------------------------------------


class TestNotificationRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        """Construct Read schema from a plain dict."""
        kw = _read_kwargs()
        schema = NotificationRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.user_id == _USER_ID
        assert schema.type == "deadline"
        assert schema.severity == "info"
        assert schema.title == "Blíži sa termín pre výkaz SP"
        assert schema.message == "Termín pre mesačný výkaz SP je o 3 dni."
        assert schema.related_entity == "payroll"
        assert schema.is_read is False
        assert schema.read_at is None
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.tenant_id = _TENANT_ID
                self.user_id = _USER_ID
                self.type = "anomaly"
                self.severity = "warning"
                self.title = "Anomália detekovaná"
                self.message = "Odchýlka v mzde zamestnanca."
                self.related_entity = "payroll"
                self.related_entity_id = uuid4()
                self.is_read = True
                self.read_at = datetime(2025, 7, 1, 10, 0, 0)
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)
                self.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = NotificationRead.model_validate(orm_obj)
        assert schema.type == "anomaly"
        assert schema.severity == "warning"
        assert schema.title == "Anomália detekovaná"
        assert schema.is_read is True
        assert schema.read_at == datetime(2025, 7, 1, 10, 0, 0)

    def test_serialisation_roundtrip(self):
        """model_dump() produces a dict that can reconstruct the schema."""
        kw = _read_kwargs()
        schema = NotificationRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["type"] == "deadline"
        assert dumped["severity"] == "info"
        assert dumped["is_read"] is False
        assert dumped["read_at"] is None

    def test_read_all_fields_present(self):
        """Read schema exposes every field from the model."""
        expected_fields = {
            "id",
            "tenant_id",
            "user_id",
            "type",
            "severity",
            "title",
            "message",
            "related_entity",
            "related_entity_id",
            "is_read",
            "read_at",
            "created_at",
            "updated_at",
        }
        assert set(NotificationRead.model_fields.keys()) == expected_fields

    def test_read_invalid_type_rejected(self):
        """NotificationRead should reject invalid type values."""
        kw = _read_kwargs()
        kw["type"] = "bogus"
        with pytest.raises(ValidationError) as exc_info:
            NotificationRead(**kw)
        assert "type" in str(exc_info.value)

    def test_read_invalid_severity_rejected(self):
        """NotificationRead should reject invalid severity values."""
        kw = _read_kwargs()
        kw["severity"] = "extreme"
        with pytest.raises(ValidationError) as exc_info:
            NotificationRead(**kw)
        assert "severity" in str(exc_info.value)
