"""Tests for StatutoryDeadline Pydantic schemas."""

from datetime import date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.statutory_deadline import (
    StatutoryDeadlineCreate,
    StatutoryDeadlineRead,
    StatutoryDeadlineUpdate,
)

# ---------------------------------------------------------------------------
# StatutoryDeadlineCreate
# ---------------------------------------------------------------------------


class TestStatutoryDeadlineCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        schema = StatutoryDeadlineCreate(
            deadline_type="sp_monthly",
            institution="Sociálna poisťovňa",
            day_of_month=20,
            description="Mesačný výkaz poistného a príspevkov",
            valid_from=date(2025, 1, 1),
        )
        assert schema.deadline_type == "sp_monthly"
        assert schema.institution == "Sociálna poisťovňa"
        assert schema.day_of_month == 20
        assert schema.description == "Mesačný výkaz poistného a príspevkov"
        assert schema.valid_from == date(2025, 1, 1)
        assert schema.valid_to is None
        assert schema.is_active is True

    def test_valid_full(self):
        schema = StatutoryDeadlineCreate(
            deadline_type="tax_advance",
            institution="Daňový úrad",
            day_of_month=25,
            description="Preddavok na daň z príjmov",
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
            is_active=False,
        )
        assert schema.deadline_type == "tax_advance"
        assert schema.institution == "Daňový úrad"
        assert schema.day_of_month == 25
        assert schema.valid_to == date(2025, 12, 31)
        assert schema.is_active is False

    def test_missing_required_deadline_type(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                institution="Sociálna poisťovňa",
                day_of_month=20,
                description="Mesačný výkaz",
                valid_from=date(2025, 1, 1),
            )
        assert "deadline_type" in str(exc_info.value)

    def test_missing_required_institution(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                deadline_type="sp_monthly",
                day_of_month=20,
                description="Mesačný výkaz",
                valid_from=date(2025, 1, 1),
            )
        assert "institution" in str(exc_info.value)

    def test_missing_required_day_of_month(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                deadline_type="sp_monthly",
                institution="Sociálna poisťovňa",
                description="Mesačný výkaz",
                valid_from=date(2025, 1, 1),
            )
        assert "day_of_month" in str(exc_info.value)

    def test_missing_required_description(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                deadline_type="sp_monthly",
                institution="Sociálna poisťovňa",
                day_of_month=20,
                valid_from=date(2025, 1, 1),
            )
        assert "description" in str(exc_info.value)

    def test_missing_required_valid_from(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                deadline_type="sp_monthly",
                institution="Sociálna poisťovňa",
                day_of_month=20,
                description="Mesačný výkaz",
            )
        assert "valid_from" in str(exc_info.value)

    def test_day_of_month_boundary_zero(self):
        """day_of_month=0 must be rejected (ge=1)."""
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                deadline_type="sp_monthly",
                institution="Sociálna poisťovňa",
                day_of_month=0,
                description="Mesačný výkaz",
                valid_from=date(2025, 1, 1),
            )
        assert "day_of_month" in str(exc_info.value)

    def test_day_of_month_boundary_32(self):
        """day_of_month=32 must be rejected (le=31)."""
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                deadline_type="sp_monthly",
                institution="Sociálna poisťovňa",
                day_of_month=32,
                description="Mesačný výkaz",
                valid_from=date(2025, 1, 1),
            )
        assert "day_of_month" in str(exc_info.value)

    def test_day_of_month_boundary_valid_min(self):
        """day_of_month=1 must be accepted (ge=1)."""
        schema = StatutoryDeadlineCreate(
            deadline_type="sp_monthly",
            institution="Sociálna poisťovňa",
            day_of_month=1,
            description="Mesačný výkaz",
            valid_from=date(2025, 1, 1),
        )
        assert schema.day_of_month == 1

    def test_day_of_month_boundary_valid_max(self):
        """day_of_month=31 must be accepted (le=31)."""
        schema = StatutoryDeadlineCreate(
            deadline_type="sp_monthly",
            institution="Sociálna poisťovňa",
            day_of_month=31,
            description="Mesačný výkaz",
            valid_from=date(2025, 1, 1),
        )
        assert schema.day_of_month == 31

    def test_institution_max_length(self):
        with pytest.raises(ValidationError):
            StatutoryDeadlineCreate(
                deadline_type="sp_monthly",
                institution="x" * 101,
                day_of_month=20,
                description="Mesačný výkaz",
                valid_from=date(2025, 1, 1),
            )

    def test_invalid_deadline_type(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                deadline_type="invalid_type",
                institution="Sociálna poisťovňa",
                day_of_month=20,
                description="Mesačný výkaz",
                valid_from=date(2025, 1, 1),
            )
        assert "deadline_type" in str(exc_info.value)

    def test_all_valid_deadline_types(self):
        """All 6 deadline types defined in the model must be accepted."""
        valid_types = [
            "sp_monthly",
            "zp_monthly",
            "tax_advance",
            "tax_reconciliation",
            "sp_annual",
            "zp_annual",
        ]
        for dtype in valid_types:
            schema = StatutoryDeadlineCreate(
                deadline_type=dtype,
                institution="Test",
                day_of_month=15,
                description="Test",
                valid_from=date(2025, 1, 1),
            )
            assert schema.deadline_type == dtype


# ---------------------------------------------------------------------------
# StatutoryDeadlineUpdate
# ---------------------------------------------------------------------------


class TestStatutoryDeadlineUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        schema = StatutoryDeadlineUpdate()
        assert schema.deadline_type is None
        assert schema.institution is None
        assert schema.day_of_month is None
        assert schema.description is None
        assert schema.valid_from is None
        assert schema.valid_to is None
        assert schema.is_active is None

    def test_partial_update(self):
        schema = StatutoryDeadlineUpdate(
            day_of_month=25,
            is_active=False,
        )
        assert schema.day_of_month == 25
        assert schema.is_active is False
        assert schema.deadline_type is None
        assert schema.institution is None

    def test_invalid_deadline_type_in_update(self):
        with pytest.raises(ValidationError):
            StatutoryDeadlineUpdate(deadline_type="invalid_type")

    def test_institution_max_length_in_update(self):
        with pytest.raises(ValidationError):
            StatutoryDeadlineUpdate(institution="x" * 101)

    def test_day_of_month_boundary_zero_in_update(self):
        with pytest.raises(ValidationError):
            StatutoryDeadlineUpdate(day_of_month=0)

    def test_day_of_month_boundary_32_in_update(self):
        with pytest.raises(ValidationError):
            StatutoryDeadlineUpdate(day_of_month=32)

    def test_day_of_month_valid_in_update(self):
        schema = StatutoryDeadlineUpdate(day_of_month=15)
        assert schema.day_of_month == 15


# ---------------------------------------------------------------------------
# StatutoryDeadlineRead
# ---------------------------------------------------------------------------


class TestStatutoryDeadlineRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        now = datetime(2025, 6, 1, 12, 0, 0)
        uid = uuid4()
        schema = StatutoryDeadlineRead(
            id=uid,
            deadline_type="sp_monthly",
            institution="Sociálna poisťovňa",
            day_of_month=20,
            description="Mesačný výkaz poistného a príspevkov",
            valid_from=date(2025, 1, 1),
            valid_to=None,
            is_active=True,
            created_at=now,
        )
        assert schema.id == uid
        assert schema.deadline_type == "sp_monthly"
        assert schema.institution == "Sociálna poisťovňa"
        assert schema.day_of_month == 20
        assert schema.is_active is True
        assert schema.created_at == now

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.deadline_type = "zp_monthly"
                self.institution = "VšZP"
                self.day_of_month = 3
                self.description = "Mesačný výkaz ZP"
                self.valid_from = date(2025, 1, 1)
                self.valid_to = date(2025, 12, 31)
                self.is_active = True
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = StatutoryDeadlineRead.model_validate(orm_obj)
        assert schema.deadline_type == "zp_monthly"
        assert schema.institution == "VšZP"
        assert schema.day_of_month == 3
        assert schema.valid_to == date(2025, 12, 31)

    def test_serialisation_roundtrip(self):
        uid = uuid4()
        data = {
            "id": uid,
            "deadline_type": "tax_advance",
            "institution": "Daňový úrad",
            "day_of_month": 25,
            "description": "Preddavok na daň z príjmov",
            "valid_from": date(2025, 1, 1),
            "valid_to": None,
            "is_active": True,
            "created_at": datetime(2025, 6, 1, 12, 0, 0),
        }
        schema = StatutoryDeadlineRead(**data)
        dumped = schema.model_dump()
        assert dumped["id"] == uid
        assert dumped["deadline_type"] == "tax_advance"
        assert dumped["institution"] == "Daňový úrad"
        assert dumped["day_of_month"] == 25
        assert dumped["is_active"] is True
