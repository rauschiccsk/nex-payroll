"""Tests for Employee Pydantic schemas."""

from datetime import date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.employee import (
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_INSURER_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for EmployeeCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "employee_number": "EMP001",
        "first_name": "Ján",
        "last_name": "Novák",
        "birth_date": date(1990, 5, 15),
        "birth_number": "9005150001",
        "gender": "M",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "bank_iban": "SK8975000000000012345678",
        "health_insurer_id": _INSURER_ID,
        "tax_declaration_type": "standard",
        "hire_date": date(2024, 1, 15),
    }


# ---------------------------------------------------------------------------
# EmployeeCreate
# ---------------------------------------------------------------------------


class TestEmployeeCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        schema = EmployeeCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_number == "EMP001"
        assert schema.first_name == "Ján"
        assert schema.last_name == "Novák"
        assert schema.title_before is None
        assert schema.title_after is None
        assert schema.birth_date == date(1990, 5, 15)
        assert schema.birth_number == "9005150001"
        assert schema.gender == "M"
        assert schema.nationality == "SK"
        assert schema.address_street == "Hlavná 1"
        assert schema.address_city == "Bratislava"
        assert schema.address_zip == "81101"
        assert schema.address_country == "SK"
        assert schema.bank_iban == "SK8975000000000012345678"
        assert schema.bank_bic is None
        assert schema.health_insurer_id == _INSURER_ID
        assert schema.tax_declaration_type == "standard"
        assert schema.nczd_applied is True
        assert schema.pillar2_saver is False
        assert schema.is_disabled is False
        assert schema.status == "active"
        assert schema.hire_date == date(2024, 1, 15)
        assert schema.termination_date is None
        assert schema.is_deleted is False

    def test_valid_full(self):
        schema = EmployeeCreate(
            **_valid_create_kwargs(),
            title_before="Ing.",
            title_after="PhD.",
            nationality="CZ",
            address_country="CZ",
            bank_bic="SUBASKBX",
            nczd_applied=False,
            pillar2_saver=True,
            is_disabled=True,
            status="inactive",
            termination_date=date(2025, 12, 31),
            is_deleted=True,
        )
        assert schema.title_before == "Ing."
        assert schema.title_after == "PhD."
        assert schema.nationality == "CZ"
        assert schema.address_country == "CZ"
        assert schema.bank_bic == "SUBASKBX"
        assert schema.nczd_applied is False
        assert schema.pillar2_saver is True
        assert schema.is_disabled is True
        assert schema.status == "inactive"
        assert schema.termination_date == date(2025, 12, 31)
        assert schema.is_deleted is True

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_employee_number(self):
        kw = _valid_create_kwargs()
        del kw["employee_number"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "employee_number" in str(exc_info.value)

    def test_missing_required_first_name(self):
        kw = _valid_create_kwargs()
        del kw["first_name"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "first_name" in str(exc_info.value)

    def test_missing_required_last_name(self):
        kw = _valid_create_kwargs()
        del kw["last_name"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "last_name" in str(exc_info.value)

    def test_missing_required_birth_date(self):
        kw = _valid_create_kwargs()
        del kw["birth_date"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "birth_date" in str(exc_info.value)

    def test_missing_required_birth_number(self):
        kw = _valid_create_kwargs()
        del kw["birth_number"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "birth_number" in str(exc_info.value)

    def test_missing_required_gender(self):
        kw = _valid_create_kwargs()
        del kw["gender"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "gender" in str(exc_info.value)

    def test_missing_required_address_street(self):
        kw = _valid_create_kwargs()
        del kw["address_street"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "address_street" in str(exc_info.value)

    def test_missing_required_address_city(self):
        kw = _valid_create_kwargs()
        del kw["address_city"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "address_city" in str(exc_info.value)

    def test_missing_required_address_zip(self):
        kw = _valid_create_kwargs()
        del kw["address_zip"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "address_zip" in str(exc_info.value)

    def test_missing_required_bank_iban(self):
        kw = _valid_create_kwargs()
        del kw["bank_iban"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "bank_iban" in str(exc_info.value)

    def test_missing_required_health_insurer_id(self):
        kw = _valid_create_kwargs()
        del kw["health_insurer_id"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "health_insurer_id" in str(exc_info.value)

    def test_missing_required_tax_declaration_type(self):
        kw = _valid_create_kwargs()
        del kw["tax_declaration_type"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "tax_declaration_type" in str(exc_info.value)

    def test_missing_required_hire_date(self):
        kw = _valid_create_kwargs()
        del kw["hire_date"]
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "hire_date" in str(exc_info.value)

    # -- max_length validation --

    def test_employee_number_max_length(self):
        kw = _valid_create_kwargs()
        kw["employee_number"] = "x" * 21
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_first_name_max_length(self):
        kw = _valid_create_kwargs()
        kw["first_name"] = "x" * 101
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_last_name_max_length(self):
        kw = _valid_create_kwargs()
        kw["last_name"] = "x" * 101
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_title_before_max_length(self):
        kw = _valid_create_kwargs()
        kw["title_before"] = "x" * 51
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_title_after_max_length(self):
        kw = _valid_create_kwargs()
        kw["title_after"] = "x" * 51
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_birth_number_max_length(self):
        kw = _valid_create_kwargs()
        kw["birth_number"] = "x" * 21
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_nationality_max_length(self):
        kw = _valid_create_kwargs()
        kw["nationality"] = "SVK"
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_address_street_max_length(self):
        kw = _valid_create_kwargs()
        kw["address_street"] = "x" * 201
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_address_city_max_length(self):
        kw = _valid_create_kwargs()
        kw["address_city"] = "x" * 101
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_address_zip_max_length(self):
        kw = _valid_create_kwargs()
        kw["address_zip"] = "x" * 11
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_address_country_max_length(self):
        kw = _valid_create_kwargs()
        kw["address_country"] = "SVK"
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_bank_iban_max_length(self):
        kw = _valid_create_kwargs()
        kw["bank_iban"] = "x" * 35
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    def test_bank_bic_max_length(self):
        kw = _valid_create_kwargs()
        kw["bank_bic"] = "x" * 12
        with pytest.raises(ValidationError):
            EmployeeCreate(**kw)

    # -- Literal validation --

    def test_invalid_gender(self):
        kw = _valid_create_kwargs()
        kw["gender"] = "X"
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "gender" in str(exc_info.value)

    def test_invalid_tax_declaration_type(self):
        kw = _valid_create_kwargs()
        kw["tax_declaration_type"] = "invalid"
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "tax_declaration_type" in str(exc_info.value)

    def test_invalid_status(self):
        kw = _valid_create_kwargs()
        kw["status"] = "fired"
        with pytest.raises(ValidationError) as exc_info:
            EmployeeCreate(**kw)
        assert "status" in str(exc_info.value)

    def test_gender_female(self):
        kw = _valid_create_kwargs()
        kw["gender"] = "F"
        schema = EmployeeCreate(**kw)
        assert schema.gender == "F"

    def test_tax_declaration_secondary(self):
        kw = _valid_create_kwargs()
        kw["tax_declaration_type"] = "secondary"
        schema = EmployeeCreate(**kw)
        assert schema.tax_declaration_type == "secondary"

    def test_tax_declaration_none(self):
        kw = _valid_create_kwargs()
        kw["tax_declaration_type"] = "none"
        schema = EmployeeCreate(**kw)
        assert schema.tax_declaration_type == "none"

    def test_status_terminated(self):
        kw = _valid_create_kwargs()
        kw["status"] = "terminated"
        schema = EmployeeCreate(**kw)
        assert schema.status == "terminated"


# ---------------------------------------------------------------------------
# EmployeeUpdate
# ---------------------------------------------------------------------------


class TestEmployeeUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        schema = EmployeeUpdate()
        assert schema.tenant_id is None
        assert schema.employee_number is None
        assert schema.first_name is None
        assert schema.last_name is None
        assert schema.title_before is None
        assert schema.title_after is None
        assert schema.birth_date is None
        assert schema.birth_number is None
        assert schema.gender is None
        assert schema.nationality is None
        assert schema.address_street is None
        assert schema.address_city is None
        assert schema.address_zip is None
        assert schema.address_country is None
        assert schema.bank_iban is None
        assert schema.bank_bic is None
        assert schema.health_insurer_id is None
        assert schema.tax_declaration_type is None
        assert schema.nczd_applied is None
        assert schema.pillar2_saver is None
        assert schema.is_disabled is None
        assert schema.status is None
        assert schema.hire_date is None
        assert schema.termination_date is None
        assert schema.is_deleted is None

    def test_partial_update(self):
        schema = EmployeeUpdate(
            first_name="Peter",
            last_name="Horváth",
            status="inactive",
        )
        assert schema.first_name == "Peter"
        assert schema.last_name == "Horváth"
        assert schema.status == "inactive"
        assert schema.employee_number is None
        assert schema.birth_date is None

    # -- max_length validation in update --

    def test_update_employee_number_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(employee_number="x" * 21)

    def test_update_first_name_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(first_name="x" * 101)

    def test_update_last_name_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(last_name="x" * 101)

    def test_update_title_before_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(title_before="x" * 51)

    def test_update_title_after_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(title_after="x" * 51)

    def test_update_birth_number_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(birth_number="x" * 21)

    def test_update_nationality_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(nationality="SVK")

    def test_update_address_street_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(address_street="x" * 201)

    def test_update_address_city_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(address_city="x" * 101)

    def test_update_address_zip_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(address_zip="x" * 11)

    def test_update_address_country_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(address_country="SVK")

    def test_update_bank_iban_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(bank_iban="x" * 35)

    def test_update_bank_bic_max_length(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(bank_bic="x" * 12)

    # -- Literal validation in update --

    def test_update_invalid_gender(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(gender="X")

    def test_update_invalid_tax_declaration_type(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(tax_declaration_type="invalid")

    def test_update_invalid_status(self):
        with pytest.raises(ValidationError):
            EmployeeUpdate(status="fired")


# ---------------------------------------------------------------------------
# EmployeeRead
# ---------------------------------------------------------------------------


class TestEmployeeRead:
    """Tests for the Read schema — from_attributes=True."""

    def _read_kwargs(self) -> dict:
        """Return a complete dict for constructing EmployeeRead."""
        now = datetime(2025, 6, 1, 12, 0, 0)
        return {
            "id": uuid4(),
            "tenant_id": _TENANT_ID,
            "employee_number": "EMP001",
            "first_name": "Ján",
            "last_name": "Novák",
            "title_before": "Ing.",
            "title_after": "PhD.",
            "birth_date": date(1990, 5, 15),
            "birth_number": "9005150001",
            "gender": "M",
            "nationality": "SK",
            "address_street": "Hlavná 1",
            "address_city": "Bratislava",
            "address_zip": "81101",
            "address_country": "SK",
            "bank_iban": "SK8975000000000012345678",
            "bank_bic": None,
            "health_insurer_id": _INSURER_ID,
            "tax_declaration_type": "standard",
            "nczd_applied": True,
            "pillar2_saver": False,
            "is_disabled": False,
            "status": "active",
            "hire_date": date(2024, 1, 15),
            "termination_date": None,
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }

    def test_from_dict(self):
        kw = self._read_kwargs()
        schema = EmployeeRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_number == "EMP001"
        assert schema.first_name == "Ján"
        assert schema.last_name == "Novák"
        assert schema.title_before == "Ing."
        assert schema.title_after == "PhD."
        assert schema.birth_date == date(1990, 5, 15)
        assert schema.birth_number == "9005150001"
        assert schema.gender == "M"
        assert schema.nationality == "SK"
        assert schema.address_street == "Hlavná 1"
        assert schema.address_city == "Bratislava"
        assert schema.address_zip == "81101"
        assert schema.address_country == "SK"
        assert schema.bank_iban == "SK8975000000000012345678"
        assert schema.bank_bic is None
        assert schema.health_insurer_id == _INSURER_ID
        assert schema.tax_declaration_type == "standard"
        assert schema.nczd_applied is True
        assert schema.pillar2_saver is False
        assert schema.is_disabled is False
        assert schema.status == "active"
        assert schema.hire_date == date(2024, 1, 15)
        assert schema.termination_date is None
        assert schema.is_deleted is False
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.tenant_id = _TENANT_ID
                self.employee_number = "EMP001"
                self.first_name = "Ján"
                self.last_name = "Novák"
                self.title_before = None
                self.title_after = None
                self.birth_date = date(1990, 5, 15)
                self.birth_number = "9005150001"
                self.gender = "M"
                self.nationality = "SK"
                self.address_street = "Hlavná 1"
                self.address_city = "Bratislava"
                self.address_zip = "81101"
                self.address_country = "SK"
                self.bank_iban = "SK8975000000000012345678"
                self.bank_bic = None
                self.health_insurer_id = _INSURER_ID
                self.tax_declaration_type = "standard"
                self.nczd_applied = True
                self.pillar2_saver = False
                self.is_disabled = False
                self.status = "active"
                self.hire_date = date(2024, 1, 15)
                self.termination_date = None
                self.is_deleted = False
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)
                self.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = EmployeeRead.model_validate(orm_obj)
        assert schema.employee_number == "EMP001"
        assert schema.first_name == "Ján"
        assert schema.status == "active"
        assert schema.nczd_applied is True
        assert schema.is_deleted is False

    def test_serialisation_roundtrip(self):
        kw = self._read_kwargs()
        schema = EmployeeRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["employee_number"] == "EMP001"
        assert dumped["first_name"] == "Ján"
        assert dumped["last_name"] == "Novák"
        assert dumped["gender"] == "M"
        assert dumped["status"] == "active"
        assert dumped["bank_bic"] is None
        assert dumped["termination_date"] is None
        assert dumped["is_deleted"] is False
