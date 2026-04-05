"""Tests for Leave Pydantic schemas (Create, Update, Read)."""

from datetime import date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.leave import LeaveCreate, LeaveRead, LeaveUpdate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_EMPLOYEE_ID = uuid4()
_USER_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for LeaveCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "employee_id": _EMPLOYEE_ID,
        "leave_type": "annual",
        "start_date": date(2025, 7, 1),
        "end_date": date(2025, 7, 14),
        "business_days": 10,
    }


def _read_kwargs() -> dict:
    """Return a complete dict for constructing LeaveRead."""
    now = datetime(2025, 6, 1, 12, 0, 0)
    return {
        "id": uuid4(),
        "tenant_id": _TENANT_ID,
        "employee_id": _EMPLOYEE_ID,
        "leave_type": "annual",
        "start_date": date(2025, 7, 1),
        "end_date": date(2025, 7, 14),
        "business_days": 10,
        "status": "pending",
        "note": None,
        "approved_by": None,
        "approved_at": None,
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# LeaveCreate
# ---------------------------------------------------------------------------


class TestLeaveCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        """Valid creation with only required fields — defaults applied."""
        schema = LeaveCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.leave_type == "annual"
        assert schema.start_date == date(2025, 7, 1)
        assert schema.end_date == date(2025, 7, 14)
        assert schema.business_days == 10
        # defaults
        assert schema.status == "pending"
        assert schema.note is None
        assert schema.approved_by is None
        assert schema.approved_at is None

    def test_valid_full(self):
        """Valid creation with all fields explicitly set."""
        approved_at = datetime(2025, 6, 15, 10, 0, 0)
        schema = LeaveCreate(
            **_valid_create_kwargs(),
            status="approved",
            note="Letná dovolenka",
            approved_by=_USER_ID,
            approved_at=approved_at,
        )
        assert schema.status == "approved"
        assert schema.note == "Letná dovolenka"
        assert schema.approved_by == _USER_ID
        assert schema.approved_at == approved_at

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_employee_id(self):
        kw = _valid_create_kwargs()
        del kw["employee_id"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "employee_id" in str(exc_info.value)

    def test_missing_required_leave_type(self):
        kw = _valid_create_kwargs()
        del kw["leave_type"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "leave_type" in str(exc_info.value)

    def test_missing_required_start_date(self):
        kw = _valid_create_kwargs()
        del kw["start_date"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "start_date" in str(exc_info.value)

    def test_missing_required_end_date(self):
        kw = _valid_create_kwargs()
        del kw["end_date"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "end_date" in str(exc_info.value)

    def test_missing_required_business_days(self):
        kw = _valid_create_kwargs()
        del kw["business_days"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "business_days" in str(exc_info.value)

    # -- leave_type Literal validation --

    def test_invalid_leave_type_rejected(self):
        kw = _valid_create_kwargs()
        kw["leave_type"] = "vacation"
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "leave_type" in str(exc_info.value)

    @pytest.mark.parametrize(
        "leave_type",
        [
            "annual",
            "sick_employer",
            "sick_sp",
            "ocr",
            "maternity",
            "parental",
            "unpaid",
            "obstacle",
        ],
    )
    def test_all_valid_leave_types_accepted(self, leave_type: str):
        kw = _valid_create_kwargs()
        kw["leave_type"] = leave_type
        schema = LeaveCreate(**kw)
        assert schema.leave_type == leave_type

    # -- status Literal validation --

    def test_invalid_status_rejected(self):
        kw = _valid_create_kwargs()
        kw["status"] = "deleted"
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "status" in str(exc_info.value)

    @pytest.mark.parametrize("status", ["pending", "approved", "rejected", "cancelled"])
    def test_all_valid_statuses_accepted(self, status: str):
        kw = _valid_create_kwargs()
        kw["status"] = status
        schema = LeaveCreate(**kw)
        assert schema.status == status

    # -- business_days ge=1 constraint --

    def test_business_days_zero_rejected(self):
        kw = _valid_create_kwargs()
        kw["business_days"] = 0
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "business_days" in str(exc_info.value)

    def test_business_days_negative_rejected(self):
        kw = _valid_create_kwargs()
        kw["business_days"] = -1
        with pytest.raises(ValidationError) as exc_info:
            LeaveCreate(**kw)
        assert "business_days" in str(exc_info.value)

    def test_business_days_one_accepted(self):
        kw = _valid_create_kwargs()
        kw["business_days"] = 1
        schema = LeaveCreate(**kw)
        assert schema.business_days == 1

    # -- default values --

    def test_default_status(self):
        """status defaults to 'pending'."""
        schema = LeaveCreate(**_valid_create_kwargs())
        assert schema.status == "pending"

    def test_default_note(self):
        """note defaults to None."""
        schema = LeaveCreate(**_valid_create_kwargs())
        assert schema.note is None

    def test_default_approved_by(self):
        """approved_by defaults to None."""
        schema = LeaveCreate(**_valid_create_kwargs())
        assert schema.approved_by is None

    def test_default_approved_at(self):
        """approved_at defaults to None."""
        schema = LeaveCreate(**_valid_create_kwargs())
        assert schema.approved_at is None


# ---------------------------------------------------------------------------
# LeaveUpdate
# ---------------------------------------------------------------------------


class TestLeaveUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        """All fields default to None when no data supplied."""
        schema = LeaveUpdate()
        assert schema.leave_type is None
        assert schema.start_date is None
        assert schema.end_date is None
        assert schema.business_days is None
        assert schema.status is None
        assert schema.note is None
        assert schema.approved_by is None
        assert schema.approved_at is None

    def test_partial_update_status(self):
        """Only supplied fields are set; the rest remain None."""
        schema = LeaveUpdate(status="approved")
        assert schema.status == "approved"
        assert schema.leave_type is None
        assert schema.start_date is None

    def test_partial_update_leave_type(self):
        schema = LeaveUpdate(leave_type="sick_employer")
        assert schema.leave_type == "sick_employer"
        assert schema.status is None

    def test_partial_update_dates(self):
        schema = LeaveUpdate(start_date=date(2025, 8, 1), end_date=date(2025, 8, 10))
        assert schema.start_date == date(2025, 8, 1)
        assert schema.end_date == date(2025, 8, 10)
        assert schema.business_days is None

    def test_partial_update_approval(self):
        now = datetime(2025, 7, 1, 10, 0, 0)
        schema = LeaveUpdate(approved_by=_USER_ID, approved_at=now)
        assert schema.approved_by == _USER_ID
        assert schema.approved_at == now

    def test_full_update(self):
        """All fields explicitly set."""
        now = datetime(2025, 7, 1, 10, 0, 0)
        schema = LeaveUpdate(
            leave_type="sick_sp",
            start_date=date(2025, 8, 1),
            end_date=date(2025, 8, 5),
            business_days=3,
            status="approved",
            note="PN potvrdená",
            approved_by=_USER_ID,
            approved_at=now,
        )
        assert schema.leave_type == "sick_sp"
        assert schema.start_date == date(2025, 8, 1)
        assert schema.end_date == date(2025, 8, 5)
        assert schema.business_days == 3
        assert schema.status == "approved"
        assert schema.note == "PN potvrdená"
        assert schema.approved_by == _USER_ID
        assert schema.approved_at == now

    # -- Literal validation in update --

    def test_update_invalid_leave_type_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaveUpdate(leave_type="vacation")
        assert "leave_type" in str(exc_info.value)

    def test_update_invalid_status_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaveUpdate(status="deleted")
        assert "status" in str(exc_info.value)

    # -- business_days ge=1 constraint in update --

    def test_update_business_days_zero_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaveUpdate(business_days=0)
        assert "business_days" in str(exc_info.value)

    def test_update_business_days_negative_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaveUpdate(business_days=-1)
        assert "business_days" in str(exc_info.value)

    def test_update_business_days_one_accepted(self):
        schema = LeaveUpdate(business_days=1)
        assert schema.business_days == 1

    # -- immutable fields excluded --

    def test_update_excludes_tenant_id(self):
        """tenant_id is not updatable — field should not exist on Update schema."""
        assert "tenant_id" not in LeaveUpdate.model_fields

    def test_update_excludes_employee_id(self):
        """employee_id is not updatable — field should not exist on Update schema."""
        assert "employee_id" not in LeaveUpdate.model_fields


# ---------------------------------------------------------------------------
# LeaveRead
# ---------------------------------------------------------------------------


class TestLeaveRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        """Construct Read schema from a plain dict."""
        kw = _read_kwargs()
        schema = LeaveRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.leave_type == "annual"
        assert schema.start_date == date(2025, 7, 1)
        assert schema.end_date == date(2025, 7, 14)
        assert schema.business_days == 10
        assert schema.status == "pending"
        assert schema.note is None
        assert schema.approved_by is None
        assert schema.approved_at is None
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_from_dict_with_approval(self):
        """Read schema with approval fields populated."""
        kw = _read_kwargs()
        approved_at = datetime(2025, 6, 20, 14, 30, 0)
        kw["status"] = "approved"
        kw["approved_by"] = _USER_ID
        kw["approved_at"] = approved_at
        kw["note"] = "Schválené riaditeľom"
        schema = LeaveRead(**kw)
        assert schema.status == "approved"
        assert schema.approved_by == _USER_ID
        assert schema.approved_at == approved_at
        assert schema.note == "Schválené riaditeľom"

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.tenant_id = _TENANT_ID
                self.employee_id = _EMPLOYEE_ID
                self.leave_type = "sick_employer"
                self.start_date = date(2025, 3, 10)
                self.end_date = date(2025, 3, 14)
                self.business_days = 5
                self.status = "approved"
                self.note = "PN"
                self.approved_by = _USER_ID
                self.approved_at = datetime(2025, 3, 10, 8, 0, 0)
                self.created_at = datetime(2025, 3, 10, 7, 0, 0)
                self.updated_at = datetime(2025, 3, 10, 8, 0, 0)

        orm_obj = FakeORM()
        schema = LeaveRead.model_validate(orm_obj)
        assert schema.leave_type == "sick_employer"
        assert schema.business_days == 5
        assert schema.status == "approved"
        assert schema.approved_by == _USER_ID

    def test_serialisation_roundtrip(self):
        """model_dump() produces a dict that can reconstruct the schema."""
        kw = _read_kwargs()
        schema = LeaveRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["leave_type"] == "annual"
        assert dumped["business_days"] == 10
        assert dumped["status"] == "pending"
        assert dumped["note"] is None
        assert dumped["approved_by"] is None
        assert dumped["approved_at"] is None

    def test_read_all_fields_present(self):
        """Read schema exposes every field from the model."""
        expected_fields = {
            "id",
            "tenant_id",
            "employee_id",
            "leave_type",
            "start_date",
            "end_date",
            "business_days",
            "status",
            "note",
            "approved_by",
            "approved_at",
            "created_at",
            "updated_at",
        }
        assert set(LeaveRead.model_fields.keys()) == expected_fields
