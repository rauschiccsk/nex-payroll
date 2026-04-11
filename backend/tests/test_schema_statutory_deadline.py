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
            code="SP_MONTHLY",
            name="Mesačný výkaz SP",
            deadline_type="monthly",
            institution="Sociálna poisťovňa",
            valid_from=date(2025, 1, 1),
        )
        assert schema.code == "SP_MONTHLY"
        assert schema.name == "Mesačný výkaz SP"
        assert schema.deadline_type == "monthly"
        assert schema.institution == "Sociálna poisťovňa"
        assert schema.valid_from == date(2025, 1, 1)
        assert schema.valid_to is None
        assert schema.day_of_month is None
        assert schema.month_of_year is None
        assert schema.business_days_rule is False
        assert schema.description is None

    def test_valid_full(self):
        schema = StatutoryDeadlineCreate(
            code="TAX_ANNUAL",
            name="Hlásenie o dani (ročné)",
            description="Ročné hlásenie o dani z príjmov",
            deadline_type="annual",
            institution="Daňový úrad",
            day_of_month=30,
            month_of_year=4,
            business_days_rule=True,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
        )
        assert schema.deadline_type == "annual"
        assert schema.institution == "Daňový úrad"
        assert schema.day_of_month == 30
        assert schema.month_of_year == 4
        assert schema.business_days_rule is True
        assert schema.valid_to == date(2025, 12, 31)

    def test_missing_required_code(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                name="Test",
                deadline_type="monthly",
                institution="Sociálna poisťovňa",
                valid_from=date(2025, 1, 1),
            )
        assert "code" in str(exc_info.value)

    def test_missing_required_name(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                deadline_type="monthly",
                institution="Sociálna poisťovňa",
                valid_from=date(2025, 1, 1),
            )
        assert "name" in str(exc_info.value)

    def test_missing_required_deadline_type(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                name="Test",
                institution="Sociálna poisťovňa",
                valid_from=date(2025, 1, 1),
            )
        assert "deadline_type" in str(exc_info.value)

    def test_missing_required_institution(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                name="Test",
                deadline_type="monthly",
                valid_from=date(2025, 1, 1),
            )
        assert "institution" in str(exc_info.value)

    def test_missing_required_valid_from(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                name="Test",
                deadline_type="monthly",
                institution="Sociálna poisťovňa",
            )
        assert "valid_from" in str(exc_info.value)

    def test_day_of_month_boundary_zero(self):
        """day_of_month=0 must be rejected (ge=1)."""
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                name="Test",
                deadline_type="monthly",
                institution="Sociálna poisťovňa",
                day_of_month=0,
                valid_from=date(2025, 1, 1),
            )
        assert "day_of_month" in str(exc_info.value)

    def test_day_of_month_boundary_32(self):
        """day_of_month=32 must be rejected (le=31)."""
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                name="Test",
                deadline_type="monthly",
                institution="Sociálna poisťovňa",
                day_of_month=32,
                valid_from=date(2025, 1, 1),
            )
        assert "day_of_month" in str(exc_info.value)

    def test_day_of_month_boundary_valid_min(self):
        """day_of_month=1 must be accepted (ge=1)."""
        schema = StatutoryDeadlineCreate(
            code="SP_MONTHLY",
            name="Test",
            deadline_type="monthly",
            institution="Sociálna poisťovňa",
            day_of_month=1,
            valid_from=date(2025, 1, 1),
        )
        assert schema.day_of_month == 1

    def test_day_of_month_boundary_valid_max(self):
        """day_of_month=31 must be accepted (le=31)."""
        schema = StatutoryDeadlineCreate(
            code="SP_MONTHLY",
            name="Test",
            deadline_type="monthly",
            institution="Sociálna poisťovňa",
            day_of_month=31,
            valid_from=date(2025, 1, 1),
        )
        assert schema.day_of_month == 31

    def test_month_of_year_boundary_zero(self):
        """month_of_year=0 must be rejected (ge=1)."""
        with pytest.raises(ValidationError):
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                name="Test",
                deadline_type="annual",
                institution="Test",
                month_of_year=0,
                valid_from=date(2025, 1, 1),
            )

    def test_month_of_year_boundary_13(self):
        """month_of_year=13 must be rejected (le=12)."""
        with pytest.raises(ValidationError):
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                name="Test",
                deadline_type="annual",
                institution="Test",
                month_of_year=13,
                valid_from=date(2025, 1, 1),
            )

    def test_institution_max_length(self):
        with pytest.raises(ValidationError):
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                name="Test",
                deadline_type="monthly",
                institution="x" * 101,
                valid_from=date(2025, 1, 1),
            )

    def test_invalid_deadline_type(self):
        with pytest.raises(ValidationError) as exc_info:
            StatutoryDeadlineCreate(
                code="SP_MONTHLY",
                name="Test",
                deadline_type="invalid_type",
                institution="Sociálna poisťovňa",
                valid_from=date(2025, 1, 1),
            )
        assert "deadline_type" in str(exc_info.value)

    def test_all_valid_deadline_types(self):
        """All 3 deadline types defined in the model must be accepted."""
        valid_types = ["monthly", "annual", "one_time"]
        for dtype in valid_types:
            schema = StatutoryDeadlineCreate(
                code=f"TEST_{dtype.upper()}",
                name="Test",
                deadline_type=dtype,
                institution="Test",
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
        assert schema.code is None
        assert schema.name is None
        assert schema.deadline_type is None
        assert schema.institution is None
        assert schema.day_of_month is None
        assert schema.month_of_year is None
        assert schema.business_days_rule is None
        assert schema.description is None
        assert schema.valid_from is None
        assert schema.valid_to is None

    def test_partial_update(self):
        schema = StatutoryDeadlineUpdate(
            day_of_month=25,
            business_days_rule=True,
        )
        assert schema.day_of_month == 25
        assert schema.business_days_rule is True
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
            code="SP_MONTHLY",
            name="Mesačný výkaz SP",
            description="Mesačný výkaz poistného a príspevkov",
            deadline_type="monthly",
            institution="Sociálna poisťovňa",
            day_of_month=20,
            month_of_year=None,
            business_days_rule=False,
            valid_from=date(2025, 1, 1),
            valid_to=None,
            created_at=now,
        )
        assert schema.id == uid
        assert schema.code == "SP_MONTHLY"
        assert schema.deadline_type == "monthly"
        assert schema.institution == "Sociálna poisťovňa"
        assert schema.day_of_month == 20
        assert schema.business_days_rule is False
        assert schema.created_at == now

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.code = "ZP_MONTHLY"
                self.name = "Mesačný prehľad ZP"
                self.description = "Mesačný výkaz ZP"
                self.deadline_type = "monthly"
                self.institution = "VšZP"
                self.day_of_month = 3
                self.month_of_year = None
                self.business_days_rule = True
                self.valid_from = date(2025, 1, 1)
                self.valid_to = date(2025, 12, 31)
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = StatutoryDeadlineRead.model_validate(orm_obj)
        assert schema.deadline_type == "monthly"
        assert schema.institution == "VšZP"
        assert schema.day_of_month == 3
        assert schema.valid_to == date(2025, 12, 31)

    def test_serialisation_roundtrip(self):
        uid = uuid4()
        data = {
            "id": uid,
            "code": "TAX_MONTHLY",
            "name": "Preddavok dane",
            "description": "Preddavok na daň z príjmov",
            "deadline_type": "monthly",
            "institution": "Daňový úrad",
            "day_of_month": 25,
            "month_of_year": None,
            "business_days_rule": False,
            "valid_from": date(2025, 1, 1),
            "valid_to": None,
            "created_at": datetime(2025, 6, 1, 12, 0, 0),
        }
        schema = StatutoryDeadlineRead(**data)
        dumped = schema.model_dump()
        assert dumped["id"] == uid
        assert dumped["code"] == "TAX_MONTHLY"
        assert dumped["deadline_type"] == "monthly"
        assert dumped["institution"] == "Daňový úrad"
        assert dumped["day_of_month"] == 25
