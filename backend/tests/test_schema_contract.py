"""Tests for Contract Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.contract import (
    ContractCreate,
    ContractRead,
    ContractUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_EMPLOYEE_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for ContractCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "employee_id": _EMPLOYEE_ID,
        "contract_number": "PZ-2024-001",
        "contract_type": "permanent",
        "job_title": "Softverovy inzinier",
        "wage_type": "monthly",
        "base_wage": Decimal("2500.00"),
        "start_date": date(2024, 1, 15),
    }


# ---------------------------------------------------------------------------
# ContractCreate
# ---------------------------------------------------------------------------


class TestContractCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        schema = ContractCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.contract_number == "PZ-2024-001"
        assert schema.contract_type == "permanent"
        assert schema.job_title == "Softverovy inzinier"
        assert schema.wage_type == "monthly"
        assert schema.base_wage == Decimal("2500.00")
        assert schema.hours_per_week == Decimal("40.0")
        assert schema.start_date == date(2024, 1, 15)
        assert schema.end_date is None
        assert schema.probation_end_date is None
        assert schema.termination_date is None
        assert schema.termination_reason is None
        assert schema.is_current is True

    def test_valid_full(self):
        schema = ContractCreate(
            **_valid_create_kwargs(),
            hours_per_week=Decimal("20.0"),
            end_date=date(2025, 12, 31),
            probation_end_date=date(2024, 4, 15),
            termination_date=date(2025, 6, 30),
            termination_reason="Dohoda",
            is_current=False,
        )
        assert schema.hours_per_week == Decimal("20.0")
        assert schema.end_date == date(2025, 12, 31)
        assert schema.probation_end_date == date(2024, 4, 15)
        assert schema.termination_date == date(2025, 6, 30)
        assert schema.termination_reason == "Dohoda"
        assert schema.is_current is False

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_employee_id(self):
        kw = _valid_create_kwargs()
        del kw["employee_id"]
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "employee_id" in str(exc_info.value)

    def test_missing_required_contract_number(self):
        kw = _valid_create_kwargs()
        del kw["contract_number"]
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "contract_number" in str(exc_info.value)

    def test_missing_required_contract_type(self):
        kw = _valid_create_kwargs()
        del kw["contract_type"]
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "contract_type" in str(exc_info.value)

    def test_missing_required_job_title(self):
        kw = _valid_create_kwargs()
        del kw["job_title"]
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "job_title" in str(exc_info.value)

    def test_missing_required_wage_type(self):
        kw = _valid_create_kwargs()
        del kw["wage_type"]
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "wage_type" in str(exc_info.value)

    def test_missing_required_base_wage(self):
        kw = _valid_create_kwargs()
        del kw["base_wage"]
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "base_wage" in str(exc_info.value)

    def test_missing_required_start_date(self):
        kw = _valid_create_kwargs()
        del kw["start_date"]
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "start_date" in str(exc_info.value)

    # -- max_length validation --

    def test_contract_number_max_length(self):
        kw = _valid_create_kwargs()
        kw["contract_number"] = "x" * 51
        with pytest.raises(ValidationError):
            ContractCreate(**kw)

    def test_job_title_max_length(self):
        kw = _valid_create_kwargs()
        kw["job_title"] = "x" * 201
        with pytest.raises(ValidationError):
            ContractCreate(**kw)

    def test_termination_reason_max_length(self):
        kw = _valid_create_kwargs()
        kw["termination_reason"] = "x" * 201
        with pytest.raises(ValidationError):
            ContractCreate(**kw)

    # -- Literal validation --

    def test_invalid_contract_type(self):
        kw = _valid_create_kwargs()
        kw["contract_type"] = "freelance"
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "contract_type" in str(exc_info.value)

    def test_invalid_wage_type(self):
        kw = _valid_create_kwargs()
        kw["wage_type"] = "daily"
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "wage_type" in str(exc_info.value)

    def test_contract_type_fixed_term(self):
        kw = _valid_create_kwargs()
        kw["contract_type"] = "fixed_term"
        schema = ContractCreate(**kw)
        assert schema.contract_type == "fixed_term"

    def test_contract_type_agreement_work(self):
        kw = _valid_create_kwargs()
        kw["contract_type"] = "agreement_work"
        schema = ContractCreate(**kw)
        assert schema.contract_type == "agreement_work"

    def test_contract_type_agreement_activity(self):
        kw = _valid_create_kwargs()
        kw["contract_type"] = "agreement_activity"
        schema = ContractCreate(**kw)
        assert schema.contract_type == "agreement_activity"

    def test_wage_type_hourly(self):
        kw = _valid_create_kwargs()
        kw["wage_type"] = "hourly"
        schema = ContractCreate(**kw)
        assert schema.wage_type == "hourly"

    # -- strip / blank validators --

    def test_contract_number_stripped(self):
        kw = _valid_create_kwargs()
        kw["contract_number"] = "  PZ-001  "
        schema = ContractCreate(**kw)
        assert schema.contract_number == "PZ-001"

    def test_contract_number_blank_rejected(self):
        kw = _valid_create_kwargs()
        kw["contract_number"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "blank" in str(exc_info.value).lower()

    def test_job_title_stripped(self):
        kw = _valid_create_kwargs()
        kw["job_title"] = "  Developer  "
        schema = ContractCreate(**kw)
        assert schema.job_title == "Developer"

    def test_job_title_blank_rejected(self):
        kw = _valid_create_kwargs()
        kw["job_title"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "blank" in str(exc_info.value).lower()

    # -- positive wage / hours validators --

    def test_base_wage_zero_rejected(self):
        kw = _valid_create_kwargs()
        kw["base_wage"] = Decimal("0.00")
        with pytest.raises(ValidationError):
            ContractCreate(**kw)

    def test_base_wage_negative_rejected(self):
        kw = _valid_create_kwargs()
        kw["base_wage"] = Decimal("-100.00")
        with pytest.raises(ValidationError):
            ContractCreate(**kw)

    def test_hours_per_week_zero_rejected(self):
        kw = _valid_create_kwargs()
        kw["hours_per_week"] = Decimal("0.0")
        with pytest.raises(ValidationError):
            ContractCreate(**kw)

    # -- date range validators --

    def test_end_date_before_start_rejected(self):
        kw = _valid_create_kwargs()
        kw["start_date"] = date(2024, 6, 1)
        kw["end_date"] = date(2024, 1, 1)
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "end date" in str(exc_info.value).lower()

    def test_end_date_same_as_start_accepted(self):
        kw = _valid_create_kwargs()
        kw["start_date"] = date(2024, 6, 1)
        kw["end_date"] = date(2024, 6, 1)
        schema = ContractCreate(**kw)
        assert schema.end_date == schema.start_date

    def test_termination_date_before_start_rejected(self):
        kw = _valid_create_kwargs()
        kw["start_date"] = date(2024, 6, 1)
        kw["termination_date"] = date(2024, 1, 1)
        with pytest.raises(ValidationError) as exc_info:
            ContractCreate(**kw)
        assert "termination date" in str(exc_info.value).lower()

    def test_termination_date_same_as_start_accepted(self):
        kw = _valid_create_kwargs()
        kw["start_date"] = date(2024, 6, 1)
        kw["termination_date"] = date(2024, 6, 1)
        schema = ContractCreate(**kw)
        assert schema.termination_date == schema.start_date


# ---------------------------------------------------------------------------
# ContractUpdate
# ---------------------------------------------------------------------------


class TestContractUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        schema = ContractUpdate()
        assert schema.contract_type is None
        assert schema.job_title is None
        assert schema.wage_type is None
        assert schema.base_wage is None
        assert schema.hours_per_week is None
        assert schema.start_date is None
        assert schema.end_date is None
        assert schema.probation_end_date is None
        assert schema.termination_date is None
        assert schema.termination_reason is None
        assert schema.is_current is None

    def test_partial_update(self):
        schema = ContractUpdate(
            job_title="Senior developer",
            base_wage=Decimal("3500.00"),
            is_current=False,
        )
        assert schema.job_title == "Senior developer"
        assert schema.base_wage == Decimal("3500.00")
        assert schema.is_current is False
        assert schema.contract_type is None
        assert schema.wage_type is None

    # -- max_length validation in update --

    def test_update_job_title_max_length(self):
        with pytest.raises(ValidationError):
            ContractUpdate(job_title="x" * 201)

    def test_update_termination_reason_max_length(self):
        with pytest.raises(ValidationError):
            ContractUpdate(termination_reason="x" * 201)

    # -- Literal validation in update --

    def test_update_invalid_contract_type(self):
        with pytest.raises(ValidationError):
            ContractUpdate(contract_type="freelance")

    def test_update_invalid_wage_type(self):
        with pytest.raises(ValidationError):
            ContractUpdate(wage_type="daily")

    # -- strip / blank validators in update --

    def test_update_contract_number_stripped(self):
        schema = ContractUpdate(contract_number="  PZ-002  ")
        assert schema.contract_number == "PZ-002"

    def test_update_contract_number_blank_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ContractUpdate(contract_number="   ")
        assert "blank" in str(exc_info.value).lower()

    def test_update_job_title_stripped(self):
        schema = ContractUpdate(job_title="  Lead  ")
        assert schema.job_title == "Lead"

    def test_update_job_title_blank_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ContractUpdate(job_title="   ")
        assert "blank" in str(exc_info.value).lower()

    # -- positive wage in update --

    def test_update_base_wage_zero_rejected(self):
        with pytest.raises(ValidationError):
            ContractUpdate(base_wage=Decimal("0.00"))

    def test_update_base_wage_negative_rejected(self):
        with pytest.raises(ValidationError):
            ContractUpdate(base_wage=Decimal("-50.00"))

    def test_update_hours_per_week_zero_rejected(self):
        with pytest.raises(ValidationError):
            ContractUpdate(hours_per_week=Decimal("0.0"))


# ---------------------------------------------------------------------------
# ContractRead
# ---------------------------------------------------------------------------


class TestContractRead:
    """Tests for the Read schema — from_attributes=True."""

    def _read_kwargs(self) -> dict:
        """Return a complete dict for constructing ContractRead."""
        now = datetime(2025, 6, 1, 12, 0, 0)
        return {
            "id": uuid4(),
            "tenant_id": _TENANT_ID,
            "employee_id": _EMPLOYEE_ID,
            "contract_number": "PZ-2024-001",
            "contract_type": "permanent",
            "job_title": "Softverovy inzinier",
            "wage_type": "monthly",
            "base_wage": Decimal("2500.00"),
            "hours_per_week": Decimal("40.0"),
            "start_date": date(2024, 1, 15),
            "end_date": None,
            "probation_end_date": None,
            "termination_date": None,
            "termination_reason": None,
            "is_current": True,
            "created_at": now,
            "updated_at": now,
        }

    def test_from_dict(self):
        kw = self._read_kwargs()
        schema = ContractRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.contract_number == "PZ-2024-001"
        assert schema.contract_type == "permanent"
        assert schema.job_title == "Softverovy inzinier"
        assert schema.wage_type == "monthly"
        assert schema.base_wage == Decimal("2500.00")
        assert schema.hours_per_week == Decimal("40.0")
        assert schema.start_date == date(2024, 1, 15)
        assert schema.end_date is None
        assert schema.probation_end_date is None
        assert schema.termination_date is None
        assert schema.termination_reason is None
        assert schema.is_current is True
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.tenant_id = _TENANT_ID
                self.employee_id = _EMPLOYEE_ID
                self.contract_number = "PZ-2024-001"
                self.contract_type = "permanent"
                self.job_title = "Softverovy inzinier"
                self.wage_type = "monthly"
                self.base_wage = Decimal("2500.00")
                self.hours_per_week = Decimal("40.0")
                self.start_date = date(2024, 1, 15)
                self.end_date = None
                self.probation_end_date = None
                self.termination_date = None
                self.termination_reason = None
                self.is_current = True
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)
                self.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = ContractRead.model_validate(orm_obj)
        assert schema.contract_number == "PZ-2024-001"
        assert schema.contract_type == "permanent"
        assert schema.job_title == "Softverovy inzinier"
        assert schema.is_current is True

    def test_serialisation_roundtrip(self):
        kw = self._read_kwargs()
        schema = ContractRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["contract_number"] == "PZ-2024-001"
        assert dumped["contract_type"] == "permanent"
        assert dumped["job_title"] == "Softverovy inzinier"
        assert dumped["wage_type"] == "monthly"
        assert dumped["is_current"] is True
        assert dumped["end_date"] is None
        assert dumped["termination_date"] is None
        assert dumped["termination_reason"] is None
