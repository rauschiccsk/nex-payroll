"""Tests for LeaveEntitlement Pydantic schemas (Create, Update, Read)."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.leave_entitlement import (
    LeaveEntitlementCreate,
    LeaveEntitlementRead,
    LeaveEntitlementUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_EMPLOYEE_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for LeaveEntitlementCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "employee_id": _EMPLOYEE_ID,
        "year": 2025,
        "total_days": 25,
        "remaining_days": 25,
    }


def _read_kwargs() -> dict:
    """Return a complete dict for constructing LeaveEntitlementRead."""
    now = datetime(2025, 6, 1, 12, 0, 0)
    return {
        "id": uuid4(),
        "tenant_id": _TENANT_ID,
        "employee_id": _EMPLOYEE_ID,
        "year": 2025,
        "total_days": 25,
        "used_days": 5,
        "remaining_days": 20,
        "carryover_days": 3,
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# LeaveEntitlementCreate
# ---------------------------------------------------------------------------


class TestLeaveEntitlementCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        """Valid creation with only required fields — defaults applied."""
        schema = LeaveEntitlementCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.year == 2025
        assert schema.total_days == 25
        assert schema.remaining_days == 25
        # defaults
        assert schema.used_days == 0
        assert schema.carryover_days == 0

    def test_valid_full(self):
        """Valid creation with all fields explicitly set."""
        schema = LeaveEntitlementCreate(
            **_valid_create_kwargs(),
            used_days=5,
            carryover_days=3,
        )
        assert schema.used_days == 5
        assert schema.carryover_days == 3

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_employee_id(self):
        kw = _valid_create_kwargs()
        del kw["employee_id"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "employee_id" in str(exc_info.value)

    def test_missing_required_year(self):
        kw = _valid_create_kwargs()
        del kw["year"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "year" in str(exc_info.value)

    def test_missing_required_total_days(self):
        kw = _valid_create_kwargs()
        del kw["total_days"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "total_days" in str(exc_info.value)

    def test_missing_required_remaining_days(self):
        kw = _valid_create_kwargs()
        del kw["remaining_days"]
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "remaining_days" in str(exc_info.value)

    # -- ge=0 constraints --

    def test_total_days_negative_rejected(self):
        kw = _valid_create_kwargs()
        kw["total_days"] = -1
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "total_days" in str(exc_info.value)

    def test_used_days_negative_rejected(self):
        kw = _valid_create_kwargs()
        kw["used_days"] = -1
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "used_days" in str(exc_info.value)

    def test_remaining_days_negative_rejected(self):
        kw = _valid_create_kwargs()
        kw["remaining_days"] = -1
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "remaining_days" in str(exc_info.value)

    def test_carryover_days_negative_rejected(self):
        kw = _valid_create_kwargs()
        kw["carryover_days"] = -1
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "carryover_days" in str(exc_info.value)

    # -- ge=0 boundary: zero is valid --

    def test_total_days_zero_accepted(self):
        kw = _valid_create_kwargs()
        kw["total_days"] = 0
        schema = LeaveEntitlementCreate(**kw)
        assert schema.total_days == 0

    def test_used_days_zero_accepted(self):
        kw = _valid_create_kwargs()
        kw["used_days"] = 0
        schema = LeaveEntitlementCreate(**kw)
        assert schema.used_days == 0

    def test_remaining_days_zero_accepted(self):
        kw = _valid_create_kwargs()
        kw["remaining_days"] = 0
        schema = LeaveEntitlementCreate(**kw)
        assert schema.remaining_days == 0

    def test_carryover_days_zero_accepted(self):
        kw = _valid_create_kwargs()
        kw["carryover_days"] = 0
        schema = LeaveEntitlementCreate(**kw)
        assert schema.carryover_days == 0

    # -- year range validation (ge=2000, le=2100) --

    def test_year_below_range_rejected(self):
        kw = _valid_create_kwargs()
        kw["year"] = 1999
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "year" in str(exc_info.value)

    def test_year_above_range_rejected(self):
        kw = _valid_create_kwargs()
        kw["year"] = 2101
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementCreate(**kw)
        assert "year" in str(exc_info.value)

    def test_year_at_lower_bound_accepted(self):
        kw = _valid_create_kwargs()
        kw["year"] = 2000
        schema = LeaveEntitlementCreate(**kw)
        assert schema.year == 2000

    def test_year_at_upper_bound_accepted(self):
        kw = _valid_create_kwargs()
        kw["year"] = 2100
        schema = LeaveEntitlementCreate(**kw)
        assert schema.year == 2100

    # -- default values --

    def test_default_used_days(self):
        """used_days defaults to 0."""
        schema = LeaveEntitlementCreate(**_valid_create_kwargs())
        assert schema.used_days == 0

    def test_default_carryover_days(self):
        """carryover_days defaults to 0."""
        schema = LeaveEntitlementCreate(**_valid_create_kwargs())
        assert schema.carryover_days == 0


# ---------------------------------------------------------------------------
# LeaveEntitlementUpdate
# ---------------------------------------------------------------------------


class TestLeaveEntitlementUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        """All fields default to None when no data supplied."""
        schema = LeaveEntitlementUpdate()
        assert schema.total_days is None
        assert schema.used_days is None
        assert schema.remaining_days is None
        assert schema.carryover_days is None

    def test_partial_update_total_days(self):
        """Only supplied fields are set; the rest remain None."""
        schema = LeaveEntitlementUpdate(total_days=30)
        assert schema.total_days == 30
        assert schema.used_days is None
        assert schema.remaining_days is None
        assert schema.carryover_days is None

    def test_partial_update_used_days(self):
        schema = LeaveEntitlementUpdate(used_days=10)
        assert schema.used_days == 10
        assert schema.total_days is None

    def test_partial_update_remaining_days(self):
        schema = LeaveEntitlementUpdate(remaining_days=15)
        assert schema.remaining_days == 15
        assert schema.total_days is None

    def test_partial_update_carryover_days(self):
        schema = LeaveEntitlementUpdate(carryover_days=5)
        assert schema.carryover_days == 5
        assert schema.total_days is None

    def test_full_update(self):
        """All fields explicitly set."""
        schema = LeaveEntitlementUpdate(
            total_days=30,
            used_days=10,
            remaining_days=20,
            carryover_days=5,
        )
        assert schema.total_days == 30
        assert schema.used_days == 10
        assert schema.remaining_days == 20
        assert schema.carryover_days == 5

    # -- ge=0 constraints in update --

    def test_update_total_days_negative_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementUpdate(total_days=-1)
        assert "total_days" in str(exc_info.value)

    def test_update_used_days_negative_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementUpdate(used_days=-1)
        assert "used_days" in str(exc_info.value)

    def test_update_remaining_days_negative_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementUpdate(remaining_days=-1)
        assert "remaining_days" in str(exc_info.value)

    def test_update_carryover_days_negative_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaveEntitlementUpdate(carryover_days=-1)
        assert "carryover_days" in str(exc_info.value)

    # -- ge=0 boundary: zero is valid in update --

    def test_update_total_days_zero_accepted(self):
        schema = LeaveEntitlementUpdate(total_days=0)
        assert schema.total_days == 0

    def test_update_used_days_zero_accepted(self):
        schema = LeaveEntitlementUpdate(used_days=0)
        assert schema.used_days == 0

    # -- no immutable fields --

    def test_update_excludes_tenant_id(self):
        """tenant_id is not updatable — field should not exist on Update schema."""
        assert "tenant_id" not in LeaveEntitlementUpdate.model_fields

    def test_update_excludes_employee_id(self):
        """employee_id is not updatable — field should not exist on Update schema."""
        assert "employee_id" not in LeaveEntitlementUpdate.model_fields

    def test_update_excludes_year(self):
        """year is part of unique key — not updatable."""
        assert "year" not in LeaveEntitlementUpdate.model_fields


# ---------------------------------------------------------------------------
# LeaveEntitlementRead
# ---------------------------------------------------------------------------


class TestLeaveEntitlementRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        """Construct Read schema from a plain dict."""
        kw = _read_kwargs()
        schema = LeaveEntitlementRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.year == 2025
        assert schema.total_days == 25
        assert schema.used_days == 5
        assert schema.remaining_days == 20
        assert schema.carryover_days == 3
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.tenant_id = _TENANT_ID
                self.employee_id = _EMPLOYEE_ID
                self.year = 2025
                self.total_days = 25
                self.used_days = 0
                self.remaining_days = 25
                self.carryover_days = 0
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)
                self.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = LeaveEntitlementRead.model_validate(orm_obj)
        assert schema.year == 2025
        assert schema.total_days == 25
        assert schema.used_days == 0
        assert schema.remaining_days == 25
        assert schema.carryover_days == 0

    def test_serialisation_roundtrip(self):
        """model_dump() produces a dict that can reconstruct the schema."""
        kw = _read_kwargs()
        schema = LeaveEntitlementRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["year"] == 2025
        assert dumped["total_days"] == 25
        assert dumped["used_days"] == 5
        assert dumped["remaining_days"] == 20
        assert dumped["carryover_days"] == 3

    def test_read_all_fields_present(self):
        """Read schema exposes every field from the model."""
        expected_fields = {
            "id",
            "tenant_id",
            "employee_id",
            "year",
            "total_days",
            "used_days",
            "remaining_days",
            "carryover_days",
            "created_at",
            "updated_at",
        }
        assert set(LeaveEntitlementRead.model_fields.keys()) == expected_fields
