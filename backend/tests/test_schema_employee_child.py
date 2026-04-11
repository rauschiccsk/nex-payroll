"""Tests for EmployeeChild Pydantic schemas (Create, Update, Read)."""

from datetime import date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.employee_child import (
    EmployeeChildCreate,
    EmployeeChildRead,
    EmployeeChildUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_EMPLOYEE_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for EmployeeChildCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "employee_id": _EMPLOYEE_ID,
        "first_name": "Anna",
        "last_name": "Nováková",
        "birth_date": date(2015, 3, 20),
    }


def _read_kwargs() -> dict:
    """Return a complete dict for constructing EmployeeChildRead."""
    now = datetime(2025, 6, 1, 12, 0, 0)
    return {
        "id": uuid4(),
        "tenant_id": _TENANT_ID,
        "employee_id": _EMPLOYEE_ID,
        "first_name": "Anna",
        "last_name": "Nováková",
        "birth_date": date(2015, 3, 20),
        "birth_number": "1503200001",
        "is_tax_bonus_eligible": True,
        "custody_from": date(2015, 3, 20),
        "custody_to": None,
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# EmployeeChildCreate
# ---------------------------------------------------------------------------


class TestEmployeeChildCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        """Valid creation with only required fields — defaults applied."""
        schema = EmployeeChildCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.first_name == "Anna"
        assert schema.last_name == "Nováková"
        assert schema.birth_date == date(2015, 3, 20)
        # defaults
        assert schema.birth_number is None
        assert schema.is_tax_bonus_eligible is True
        assert schema.custody_from is None
        assert schema.custody_to is None

    def test_valid_full(self):
        """Valid creation with all fields explicitly set."""
        schema = EmployeeChildCreate(
            **_valid_create_kwargs(),
            birth_number="1503200001",
            is_tax_bonus_eligible=False,
            custody_from=date(2015, 3, 20),
            custody_to=date(2030, 12, 31),
        )
        assert schema.birth_number == "1503200001"
        assert schema.is_tax_bonus_eligible is False
        assert schema.custody_from == date(2015, 3, 20)
        assert schema.custody_to == date(2030, 12, 31)

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_employee_id(self):
        kw = _valid_create_kwargs()
        del kw["employee_id"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "employee_id" in str(exc_info.value)

    def test_missing_required_first_name(self):
        kw = _valid_create_kwargs()
        del kw["first_name"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "first_name" in str(exc_info.value)

    def test_missing_required_last_name(self):
        kw = _valid_create_kwargs()
        del kw["last_name"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "last_name" in str(exc_info.value)

    def test_missing_required_birth_date(self):
        kw = _valid_create_kwargs()
        del kw["birth_date"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "birth_date" in str(exc_info.value)

    # -- max_length validation --

    def test_first_name_max_length(self):
        kw = _valid_create_kwargs()
        kw["first_name"] = "x" * 101
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "first_name" in str(exc_info.value)

    def test_last_name_max_length(self):
        kw = _valid_create_kwargs()
        kw["last_name"] = "x" * 101
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "last_name" in str(exc_info.value)

    def test_birth_number_max_length(self):
        kw = _valid_create_kwargs()
        kw["birth_number"] = "x" * 21
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "birth_number" in str(exc_info.value)

    # -- boundary: exactly at max_length --

    def test_first_name_at_max_length(self):
        kw = _valid_create_kwargs()
        kw["first_name"] = "A" * 100
        schema = EmployeeChildCreate(**kw)
        assert len(schema.first_name) == 100

    def test_last_name_at_max_length(self):
        kw = _valid_create_kwargs()
        kw["last_name"] = "B" * 100
        schema = EmployeeChildCreate(**kw)
        assert len(schema.last_name) == 100

    def test_birth_number_at_valid_length(self):
        """Valid 10-digit birth number is accepted."""
        kw = _valid_create_kwargs()
        kw["birth_number"] = "1503200001"
        schema = EmployeeChildCreate(**kw)
        assert schema.birth_number == "1503200001"

    # -- validator: strip whitespace / not blank --

    def test_first_name_stripped(self):
        kw = _valid_create_kwargs()
        kw["first_name"] = "  Anna  "
        schema = EmployeeChildCreate(**kw)
        assert schema.first_name == "Anna"

    def test_first_name_blank_rejected(self):
        kw = _valid_create_kwargs()
        kw["first_name"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "must not be blank" in str(exc_info.value)

    def test_last_name_stripped(self):
        kw = _valid_create_kwargs()
        kw["last_name"] = "  Nováková  "
        schema = EmployeeChildCreate(**kw)
        assert schema.last_name == "Nováková"

    def test_last_name_blank_rejected(self):
        kw = _valid_create_kwargs()
        kw["last_name"] = "   "
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "must not be blank" in str(exc_info.value)

    # -- validator: birth_number format --

    def test_birth_number_valid_without_slash(self):
        kw = _valid_create_kwargs()
        kw["birth_number"] = "1503200001"
        schema = EmployeeChildCreate(**kw)
        assert schema.birth_number == "1503200001"

    def test_birth_number_valid_with_slash(self):
        kw = _valid_create_kwargs()
        kw["birth_number"] = "150320/0001"
        schema = EmployeeChildCreate(**kw)
        assert schema.birth_number == "1503200001"  # slash stripped

    def test_birth_number_invalid_format(self):
        kw = _valid_create_kwargs()
        kw["birth_number"] = "ABCDEF"
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "Birth number" in str(exc_info.value)

    # -- validator: custody_to >= custody_from --

    def test_custody_to_before_from_rejected(self):
        kw = _valid_create_kwargs()
        kw["custody_from"] = date(2020, 6, 1)
        kw["custody_to"] = date(2020, 1, 1)
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildCreate(**kw)
        assert "custody_to" in str(exc_info.value)

    def test_custody_to_equal_from_accepted(self):
        kw = _valid_create_kwargs()
        kw["custody_from"] = date(2020, 6, 1)
        kw["custody_to"] = date(2020, 6, 1)
        schema = EmployeeChildCreate(**kw)
        assert schema.custody_from == schema.custody_to

    # -- default values --

    def test_default_is_tax_bonus_eligible(self):
        """is_tax_bonus_eligible defaults to True."""
        schema = EmployeeChildCreate(**_valid_create_kwargs())
        assert schema.is_tax_bonus_eligible is True

    def test_default_nullable_fields(self):
        """Nullable fields default to None."""
        schema = EmployeeChildCreate(**_valid_create_kwargs())
        assert schema.birth_number is None
        assert schema.custody_from is None
        assert schema.custody_to is None


# ---------------------------------------------------------------------------
# EmployeeChildUpdate
# ---------------------------------------------------------------------------


class TestEmployeeChildUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        """All fields default to None when no data supplied."""
        schema = EmployeeChildUpdate()
        assert schema.first_name is None
        assert schema.last_name is None
        assert schema.birth_date is None
        assert schema.birth_number is None
        assert schema.is_tax_bonus_eligible is None
        assert schema.custody_from is None
        assert schema.custody_to is None

    def test_partial_update(self):
        """Only supplied fields are set; the rest remain None."""
        schema = EmployeeChildUpdate(
            first_name="Mária",
            is_tax_bonus_eligible=False,
        )
        assert schema.first_name == "Mária"
        assert schema.is_tax_bonus_eligible is False
        assert schema.last_name is None
        assert schema.birth_date is None
        assert schema.birth_number is None
        assert schema.custody_from is None
        assert schema.custody_to is None

    def test_partial_update_birth_date(self):
        schema = EmployeeChildUpdate(birth_date=date(2016, 7, 10))
        assert schema.birth_date == date(2016, 7, 10)
        assert schema.first_name is None

    def test_partial_update_custody(self):
        schema = EmployeeChildUpdate(
            custody_from=date(2020, 1, 1),
            custody_to=date(2025, 12, 31),
        )
        assert schema.custody_from == date(2020, 1, 1)
        assert schema.custody_to == date(2025, 12, 31)

    # -- max_length validation in update --

    def test_update_first_name_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeChildUpdate(first_name="x" * 101)

    def test_update_last_name_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeChildUpdate(last_name="x" * 101)

    def test_update_birth_number_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeChildUpdate(birth_number="x" * 21)

    # -- validator: strip whitespace / not blank --

    def test_update_first_name_stripped(self):
        schema = EmployeeChildUpdate(first_name="  Mária  ")
        assert schema.first_name == "Mária"

    def test_update_first_name_blank_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildUpdate(first_name="   ")
        assert "must not be blank" in str(exc_info.value)

    def test_update_last_name_stripped(self):
        schema = EmployeeChildUpdate(last_name="  Kováčová  ")
        assert schema.last_name == "Kováčová"

    def test_update_last_name_blank_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildUpdate(last_name="   ")
        assert "must not be blank" in str(exc_info.value)

    # -- validator: birth_number format --

    def test_update_birth_number_valid(self):
        schema = EmployeeChildUpdate(birth_number="150320/0001")
        assert schema.birth_number == "1503200001"

    def test_update_birth_number_invalid(self):
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildUpdate(birth_number="ABCDEF")
        assert "Birth number" in str(exc_info.value)

    # -- validator: custody_to >= custody_from --

    def test_update_custody_to_before_from_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            EmployeeChildUpdate(
                custody_from=date(2020, 6, 1),
                custody_to=date(2020, 1, 1),
            )
        assert "custody_to" in str(exc_info.value)


# ---------------------------------------------------------------------------
# EmployeeChildRead
# ---------------------------------------------------------------------------


class TestEmployeeChildRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        """Construct Read schema from a plain dict."""
        kw = _read_kwargs()
        schema = EmployeeChildRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.first_name == "Anna"
        assert schema.last_name == "Nováková"
        assert schema.birth_date == date(2015, 3, 20)
        assert schema.birth_number == "1503200001"
        assert schema.is_tax_bonus_eligible is True
        assert schema.custody_from == date(2015, 3, 20)
        assert schema.custody_to is None
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.tenant_id = _TENANT_ID
                self.employee_id = _EMPLOYEE_ID
                self.first_name = "Anna"
                self.last_name = "Nováková"
                self.birth_date = date(2015, 3, 20)
                self.birth_number = None
                self.is_tax_bonus_eligible = True
                self.custody_from = None
                self.custody_to = None
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)
                self.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = EmployeeChildRead.model_validate(orm_obj)
        assert schema.first_name == "Anna"
        assert schema.last_name == "Nováková"
        assert schema.birth_number is None
        assert schema.is_tax_bonus_eligible is True

    def test_serialisation_roundtrip(self):
        """model_dump() produces a dict that can reconstruct the schema."""
        kw = _read_kwargs()
        schema = EmployeeChildRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["first_name"] == "Anna"
        assert dumped["last_name"] == "Nováková"
        assert dumped["birth_date"] == date(2015, 3, 20)
        assert dumped["birth_number"] == "1503200001"
        assert dumped["is_tax_bonus_eligible"] is True
        assert dumped["custody_from"] == date(2015, 3, 20)
        assert dumped["custody_to"] is None

    def test_read_with_null_birth_number(self):
        """Read schema handles null birth_number correctly."""
        kw = _read_kwargs()
        kw["birth_number"] = None
        schema = EmployeeChildRead(**kw)
        assert schema.birth_number is None
