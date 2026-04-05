"""Tests for ContributionRate Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.contribution_rate import (
    ContributionRateCreate,
    ContributionRateRead,
    ContributionRateUpdate,
)

# ---------------------------------------------------------------------------
# ContributionRateCreate
# ---------------------------------------------------------------------------


class TestContributionRateCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        schema = ContributionRateCreate(
            rate_type="sp_employee_nemocenske",
            rate_percent=Decimal("1.4000"),
            payer="employee",
            fund="nemocenske",
            valid_from=date(2025, 1, 1),
        )
        assert schema.rate_type == "sp_employee_nemocenske"
        assert schema.rate_percent == Decimal("1.4000")
        assert schema.max_assessment_base is None
        assert schema.payer == "employee"
        assert schema.fund == "nemocenske"
        assert schema.valid_from == date(2025, 1, 1)
        assert schema.valid_to is None

    def test_valid_full(self):
        schema = ContributionRateCreate(
            rate_type="sp_employee_starobne",
            rate_percent=Decimal("4.0000"),
            max_assessment_base=Decimal("9128.00"),
            payer="employer",
            fund="starobne",
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
        )
        assert schema.max_assessment_base == Decimal("9128.00")
        assert schema.payer == "employer"
        assert schema.valid_to == date(2025, 12, 31)

    def test_missing_required_rate_type(self):
        with pytest.raises(ValidationError) as exc_info:
            ContributionRateCreate(
                rate_percent=Decimal("1.4000"),
                payer="employee",
                fund="nemocenske",
                valid_from=date(2025, 1, 1),
            )
        assert "rate_type" in str(exc_info.value)

    def test_missing_required_rate_percent(self):
        with pytest.raises(ValidationError):
            ContributionRateCreate(
                rate_type="sp_employee_nemocenske",
                payer="employee",
                fund="nemocenske",
                valid_from=date(2025, 1, 1),
            )

    def test_missing_required_payer(self):
        with pytest.raises(ValidationError):
            ContributionRateCreate(
                rate_type="sp_employee_nemocenske",
                rate_percent=Decimal("1.4000"),
                fund="nemocenske",
                valid_from=date(2025, 1, 1),
            )

    def test_missing_required_fund(self):
        with pytest.raises(ValidationError):
            ContributionRateCreate(
                rate_type="sp_employee_nemocenske",
                rate_percent=Decimal("1.4000"),
                payer="employee",
                valid_from=date(2025, 1, 1),
            )

    def test_missing_required_valid_from(self):
        with pytest.raises(ValidationError):
            ContributionRateCreate(
                rate_type="sp_employee_nemocenske",
                rate_percent=Decimal("1.4000"),
                payer="employee",
                fund="nemocenske",
            )

    def test_invalid_payer(self):
        with pytest.raises(ValidationError) as exc_info:
            ContributionRateCreate(
                rate_type="sp_employee_nemocenske",
                rate_percent=Decimal("1.4000"),
                payer="company",
                fund="nemocenske",
                valid_from=date(2025, 1, 1),
            )
        assert "payer" in str(exc_info.value)

    def test_rate_type_max_length(self):
        with pytest.raises(ValidationError):
            ContributionRateCreate(
                rate_type="x" * 51,
                rate_percent=Decimal("1.4000"),
                payer="employee",
                fund="nemocenske",
                valid_from=date(2025, 1, 1),
            )

    def test_fund_max_length(self):
        with pytest.raises(ValidationError):
            ContributionRateCreate(
                rate_type="sp_employee_nemocenske",
                rate_percent=Decimal("1.4000"),
                payer="employee",
                fund="x" * 51,
                valid_from=date(2025, 1, 1),
            )


# ---------------------------------------------------------------------------
# ContributionRateUpdate
# ---------------------------------------------------------------------------


class TestContributionRateUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        schema = ContributionRateUpdate()
        assert schema.rate_type is None
        assert schema.rate_percent is None
        assert schema.max_assessment_base is None
        assert schema.payer is None
        assert schema.fund is None
        assert schema.valid_from is None
        assert schema.valid_to is None

    def test_partial_update(self):
        schema = ContributionRateUpdate(
            rate_percent=Decimal("2.0000"),
            valid_to=date(2026, 12, 31),
        )
        assert schema.rate_percent == Decimal("2.0000")
        assert schema.valid_to == date(2026, 12, 31)
        assert schema.rate_type is None

    def test_invalid_payer_in_update(self):
        with pytest.raises(ValidationError):
            ContributionRateUpdate(payer="company")

    def test_update_rate_type_max_length(self):
        with pytest.raises(ValidationError):
            ContributionRateUpdate(rate_type="x" * 51)


# ---------------------------------------------------------------------------
# ContributionRateRead
# ---------------------------------------------------------------------------


class TestContributionRateRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        now = datetime(2025, 6, 1, 12, 0, 0)
        uid = uuid4()
        schema = ContributionRateRead(
            id=uid,
            rate_type="sp_employee_nemocenske",
            rate_percent=Decimal("1.4000"),
            max_assessment_base=None,
            payer="employee",
            fund="nemocenske",
            valid_from=date(2025, 1, 1),
            valid_to=None,
            created_at=now,
        )
        assert schema.id == uid
        assert schema.rate_type == "sp_employee_nemocenske"
        assert schema.created_at == now

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.rate_type = "zp_employee"
                self.rate_percent = Decimal("4.0000")
                self.max_assessment_base = Decimal("9128.00")
                self.payer = "employee"
                self.fund = "zdravotne"
                self.valid_from = date(2025, 1, 1)
                self.valid_to = date(2025, 12, 31)
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = ContributionRateRead.model_validate(orm_obj)
        assert schema.rate_type == "zp_employee"
        assert schema.max_assessment_base == Decimal("9128.00")
        assert schema.valid_to == date(2025, 12, 31)

    def test_serialisation_roundtrip(self):
        uid = uuid4()
        data = {
            "id": uid,
            "rate_type": "sp_employer_starobne",
            "rate_percent": Decimal("14.0000"),
            "max_assessment_base": None,
            "payer": "employer",
            "fund": "starobne",
            "valid_from": date(2025, 1, 1),
            "valid_to": None,
            "created_at": datetime(2025, 6, 1, 12, 0, 0),
        }
        schema = ContributionRateRead(**data)
        dumped = schema.model_dump()
        assert dumped["id"] == uid
        assert dumped["rate_type"] == "sp_employer_starobne"
        assert dumped["rate_percent"] == Decimal("14.0000")
