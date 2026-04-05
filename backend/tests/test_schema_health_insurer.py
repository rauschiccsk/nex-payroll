"""Tests for HealthInsurer Pydantic schemas."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.health_insurer import (
    HealthInsurerCreate,
    HealthInsurerRead,
    HealthInsurerUpdate,
)

# ---------------------------------------------------------------------------
# HealthInsurerCreate
# ---------------------------------------------------------------------------


class TestHealthInsurerCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        schema = HealthInsurerCreate(
            code="25",
            name="Všeobecná zdravotná poisťovňa, a.s.",
            iban="SK8975000000000012345678",
        )
        assert schema.code == "25"
        assert schema.name == "Všeobecná zdravotná poisťovňa, a.s."
        assert schema.iban == "SK8975000000000012345678"
        assert schema.bic is None
        assert schema.is_active is True

    def test_valid_full(self):
        schema = HealthInsurerCreate(
            code="24",
            name="Dôvera zdravotná poisťovňa, a.s.",
            iban="SK8975000000000012345678",
            bic="SUBASKBX",
            is_active=False,
        )
        assert schema.code == "24"
        assert schema.bic == "SUBASKBX"
        assert schema.is_active is False

    def test_missing_required_code(self):
        with pytest.raises(ValidationError) as exc_info:
            HealthInsurerCreate(
                name="Dôvera zdravotná poisťovňa, a.s.",
                iban="SK8975000000000012345678",
            )
        assert "code" in str(exc_info.value)

    def test_missing_required_name(self):
        with pytest.raises(ValidationError) as exc_info:
            HealthInsurerCreate(
                code="25",
                iban="SK8975000000000012345678",
            )
        assert "name" in str(exc_info.value)

    def test_missing_required_iban(self):
        with pytest.raises(ValidationError) as exc_info:
            HealthInsurerCreate(
                code="25",
                name="Všeobecná zdravotná poisťovňa, a.s.",
            )
        assert "iban" in str(exc_info.value)

    def test_code_max_length(self):
        with pytest.raises(ValidationError):
            HealthInsurerCreate(
                code="12345",
                name="Test",
                iban="SK8975000000000012345678",
            )

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            HealthInsurerCreate(
                code="25",
                name="x" * 201,
                iban="SK8975000000000012345678",
            )

    def test_iban_max_length(self):
        with pytest.raises(ValidationError):
            HealthInsurerCreate(
                code="25",
                name="Test",
                iban="x" * 35,
            )

    def test_bic_max_length(self):
        with pytest.raises(ValidationError):
            HealthInsurerCreate(
                code="25",
                name="Test",
                iban="SK8975000000000012345678",
                bic="x" * 12,
            )


# ---------------------------------------------------------------------------
# HealthInsurerUpdate
# ---------------------------------------------------------------------------


class TestHealthInsurerUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        schema = HealthInsurerUpdate()
        assert schema.code is None
        assert schema.name is None
        assert schema.iban is None
        assert schema.bic is None
        assert schema.is_active is None

    def test_partial_update(self):
        schema = HealthInsurerUpdate(
            name="Updated Name",
            is_active=False,
        )
        assert schema.name == "Updated Name"
        assert schema.is_active is False
        assert schema.code is None

    def test_update_code_max_length(self):
        with pytest.raises(ValidationError):
            HealthInsurerUpdate(code="12345")

    def test_update_name_max_length(self):
        with pytest.raises(ValidationError):
            HealthInsurerUpdate(name="x" * 201)

    def test_update_iban_max_length(self):
        with pytest.raises(ValidationError):
            HealthInsurerUpdate(iban="x" * 35)

    def test_update_bic_max_length(self):
        with pytest.raises(ValidationError):
            HealthInsurerUpdate(bic="x" * 12)


# ---------------------------------------------------------------------------
# HealthInsurerRead
# ---------------------------------------------------------------------------


class TestHealthInsurerRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        now = datetime(2025, 6, 1, 12, 0, 0)
        uid = uuid4()
        schema = HealthInsurerRead(
            id=uid,
            code="25",
            name="Všeobecná zdravotná poisťovňa, a.s.",
            iban="SK8975000000000012345678",
            bic=None,
            is_active=True,
            created_at=now,
        )
        assert schema.id == uid
        assert schema.code == "25"
        assert schema.is_active is True
        assert schema.created_at == now

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.code = "24"
                self.name = "Dôvera zdravotná poisťovňa, a.s."
                self.iban = "SK8975000000000012345678"
                self.bic = "SUBASKBX"
                self.is_active = True
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = HealthInsurerRead.model_validate(orm_obj)
        assert schema.code == "24"
        assert schema.bic == "SUBASKBX"
        assert schema.is_active is True

    def test_serialisation_roundtrip(self):
        uid = uuid4()
        data = {
            "id": uid,
            "code": "27",
            "name": "Union zdravotná poisťovňa, a.s.",
            "iban": "SK8975000000000012345678",
            "bic": None,
            "is_active": True,
            "created_at": datetime(2025, 6, 1, 12, 0, 0),
        }
        schema = HealthInsurerRead(**data)
        dumped = schema.model_dump()
        assert dumped["id"] == uid
        assert dumped["code"] == "27"
        assert dumped["is_active"] is True
