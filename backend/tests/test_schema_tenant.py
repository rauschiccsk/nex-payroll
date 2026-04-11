"""Tests for Tenant Pydantic schemas."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.tenant import (
    TenantCreate,
    TenantRead,
    TenantUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_CREATE = {
    "name": "Firma s.r.o.",
    "ico": "12345678",
    "address_street": "Hlavná 1",
    "address_city": "Bratislava",
    "address_zip": "81101",
    "bank_iban": "SK8975000000000012345678",
}


# ---------------------------------------------------------------------------
# TenantCreate
# ---------------------------------------------------------------------------


class TestTenantCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        schema = TenantCreate(**_VALID_CREATE)
        assert schema.name == "Firma s.r.o."
        assert schema.ico == "12345678"
        assert schema.dic is None
        assert schema.ic_dph is None
        assert schema.address_street == "Hlavná 1"
        assert schema.address_city == "Bratislava"
        assert schema.address_zip == "81101"
        assert schema.address_country == "SK"
        assert schema.bank_iban == "SK8975000000000012345678"
        assert schema.bank_bic is None
        assert schema.default_role == "accountant"
        assert schema.is_active is True

    def test_valid_full(self):
        schema = TenantCreate(
            name="Veľká Firma a.s.",
            ico="87654321",
            dic="2087654321",
            ic_dph="SK2087654321",
            address_street="Obchodná 42",
            address_city="Košice",
            address_zip="04001",
            address_country="CZ",
            bank_iban="SK8975000000000098765432",
            bank_bic="SUBASKBX",
            default_role="director",
            is_active=False,
        )
        assert schema.dic == "2087654321"
        assert schema.ic_dph == "SK2087654321"
        assert schema.address_country == "CZ"
        assert schema.bank_bic == "SUBASKBX"
        assert schema.default_role == "director"
        assert schema.is_active is False

    def test_missing_required_name(self):
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(**{k: v for k, v in _VALID_CREATE.items() if k != "name"})
        assert "name" in str(exc_info.value)

    def test_missing_required_ico(self):
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(**{k: v for k, v in _VALID_CREATE.items() if k != "ico"})
        assert "ico" in str(exc_info.value)

    def test_missing_required_address_street(self):
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(**{k: v for k, v in _VALID_CREATE.items() if k != "address_street"})
        assert "address_street" in str(exc_info.value)

    def test_missing_required_address_city(self):
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(**{k: v for k, v in _VALID_CREATE.items() if k != "address_city"})
        assert "address_city" in str(exc_info.value)

    def test_missing_required_address_zip(self):
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(**{k: v for k, v in _VALID_CREATE.items() if k != "address_zip"})
        assert "address_zip" in str(exc_info.value)

    def test_missing_required_bank_iban(self):
        with pytest.raises(ValidationError) as exc_info:
            TenantCreate(**{k: v for k, v in _VALID_CREATE.items() if k != "bank_iban"})
        assert "bank_iban" in str(exc_info.value)

    # -- Name validation --

    def test_name_blank_rejected(self):
        with pytest.raises(ValidationError, match="Name must not be blank"):
            TenantCreate(**{**_VALID_CREATE, "name": "   "})

    def test_name_stripped(self):
        schema = TenantCreate(**{**_VALID_CREATE, "name": "  Firma s.r.o.  "})
        assert schema.name == "Firma s.r.o."

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            TenantCreate(**{**_VALID_CREATE, "name": "x" * 201})

    # -- IČO validation --

    def test_ico_must_be_8_digits(self):
        with pytest.raises(ValidationError, match="IČO must be exactly 8 digits"):
            TenantCreate(**{**_VALID_CREATE, "ico": "1234567"})

    def test_ico_non_digits_rejected(self):
        with pytest.raises(ValidationError, match="IČO must be exactly 8 digits"):
            TenantCreate(**{**_VALID_CREATE, "ico": "1234567A"})

    def test_ico_9_digits_rejected(self):
        with pytest.raises(ValidationError):
            TenantCreate(**{**_VALID_CREATE, "ico": "123456789"})

    # -- DIČ validation --

    def test_dic_valid_10_digits(self):
        schema = TenantCreate(**{**_VALID_CREATE, "dic": "2012345678"})
        assert schema.dic == "2012345678"

    def test_dic_valid_12_digits(self):
        schema = TenantCreate(**{**_VALID_CREATE, "dic": "201234567890"})
        assert schema.dic == "201234567890"

    def test_dic_non_digits_rejected(self):
        with pytest.raises(ValidationError, match="DIČ must be 10-12 digits"):
            TenantCreate(**{**_VALID_CREATE, "dic": "20123456AB"})

    def test_dic_too_short_rejected(self):
        with pytest.raises(ValidationError, match="DIČ must be 10-12 digits"):
            TenantCreate(**{**_VALID_CREATE, "dic": "123456789"})

    # -- IČ DPH validation --

    def test_ic_dph_valid(self):
        schema = TenantCreate(**{**_VALID_CREATE, "ic_dph": "SK2012345678"})
        assert schema.ic_dph == "SK2012345678"

    def test_ic_dph_lowercase_normalised(self):
        schema = TenantCreate(**{**_VALID_CREATE, "ic_dph": "sk2012345678"})
        assert schema.ic_dph == "SK2012345678"

    def test_ic_dph_missing_sk_prefix_rejected(self):
        with pytest.raises(ValidationError, match="IČ DPH must match format"):
            TenantCreate(**{**_VALID_CREATE, "ic_dph": "CZ2012345678"})

    def test_ic_dph_wrong_length_rejected(self):
        with pytest.raises(ValidationError, match="IČ DPH must match format"):
            TenantCreate(**{**_VALID_CREATE, "ic_dph": "SK20123456"})

    # -- Country code validation --

    def test_country_code_uppercase_normalised(self):
        schema = TenantCreate(**{**_VALID_CREATE, "address_country": "cz"})
        assert schema.address_country == "CZ"

    def test_country_code_too_long_rejected(self):
        with pytest.raises(ValidationError):
            TenantCreate(**{**_VALID_CREATE, "address_country": "SVK"})

    def test_country_code_digits_only_rejected(self):
        with pytest.raises(ValidationError, match="2-letter ISO"):
            TenantCreate(**{**_VALID_CREATE, "address_country": "12"})

    # -- IBAN validation --

    def test_iban_spaces_normalised(self):
        schema = TenantCreate(**{**_VALID_CREATE, "bank_iban": "SK89 7500 0000 0000 1234 5678"})
        assert schema.bank_iban == "SK8975000000000012345678"

    def test_iban_lowercase_normalised(self):
        schema = TenantCreate(**{**_VALID_CREATE, "bank_iban": "sk8975000000000012345678"})
        assert schema.bank_iban == "SK8975000000000012345678"

    def test_iban_invalid_format_rejected(self):
        with pytest.raises(ValidationError, match="Invalid IBAN"):
            TenantCreate(**{**_VALID_CREATE, "bank_iban": "12345678"})

    # -- BIC validation --

    def test_bic_valid_8_chars(self):
        schema = TenantCreate(**{**_VALID_CREATE, "bank_bic": "SUBASKBX"})
        assert schema.bank_bic == "SUBASKBX"

    def test_bic_valid_11_chars(self):
        schema = TenantCreate(**{**_VALID_CREATE, "bank_bic": "SUBASKBXXXX"})
        assert schema.bank_bic == "SUBASKBXXXX"

    def test_bic_invalid_rejected(self):
        with pytest.raises(ValidationError, match="Invalid BIC"):
            TenantCreate(**{**_VALID_CREATE, "bank_bic": "SHORT"})

    # -- default_role Literal validation --

    def test_default_role_invalid_rejected(self):
        with pytest.raises(ValidationError):
            TenantCreate(**{**_VALID_CREATE, "default_role": "admin"})

    def test_default_role_all_valid_values(self):
        for role in ("director", "accountant", "employee"):
            schema = TenantCreate(**{**_VALID_CREATE, "default_role": role})
            assert schema.default_role == role


# ---------------------------------------------------------------------------
# TenantUpdate
# ---------------------------------------------------------------------------


class TestTenantUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        schema = TenantUpdate()
        assert schema.name is None
        assert schema.ico is None
        assert schema.dic is None
        assert schema.ic_dph is None
        assert schema.address_street is None
        assert schema.address_city is None
        assert schema.address_zip is None
        assert schema.address_country is None
        assert schema.bank_iban is None
        assert schema.bank_bic is None
        assert schema.default_role is None
        assert schema.is_active is None

    def test_partial_update(self):
        schema = TenantUpdate(
            name="Updated Firma s.r.o.",
            is_active=False,
        )
        assert schema.name == "Updated Firma s.r.o."
        assert schema.is_active is False
        assert schema.ico is None
        assert schema.address_street is None

    def test_update_name_blank_rejected(self):
        with pytest.raises(ValidationError, match="Name must not be blank"):
            TenantUpdate(name="   ")

    def test_update_name_stripped(self):
        schema = TenantUpdate(name="  New Name  ")
        assert schema.name == "New Name"

    def test_update_name_max_length(self):
        with pytest.raises(ValidationError):
            TenantUpdate(name="x" * 201)

    def test_update_ico_invalid_rejected(self):
        with pytest.raises(ValidationError, match="IČO must be exactly 8 digits"):
            TenantUpdate(ico="1234")

    def test_update_ico_valid(self):
        schema = TenantUpdate(ico="87654321")
        assert schema.ico == "87654321"

    def test_update_dic_invalid_rejected(self):
        with pytest.raises(ValidationError, match="DIČ must be 10-12 digits"):
            TenantUpdate(dic="short")

    def test_update_ic_dph_invalid_rejected(self):
        with pytest.raises(ValidationError, match="IČ DPH must match format"):
            TenantUpdate(ic_dph="CZ2012345678")

    def test_update_ic_dph_normalised(self):
        schema = TenantUpdate(ic_dph="sk2012345678")
        assert schema.ic_dph == "SK2012345678"

    def test_update_country_too_long_rejected(self):
        with pytest.raises(ValidationError):
            TenantUpdate(address_country="SVK")

    def test_update_country_digits_rejected(self):
        with pytest.raises(ValidationError, match="2-letter ISO"):
            TenantUpdate(address_country="12")

    def test_update_country_normalised(self):
        schema = TenantUpdate(address_country="cz")
        assert schema.address_country == "CZ"

    def test_update_iban_invalid_rejected(self):
        with pytest.raises(ValidationError, match="Invalid IBAN"):
            TenantUpdate(bank_iban="bad")

    def test_update_iban_normalised(self):
        schema = TenantUpdate(bank_iban="sk89 7500 0000 0000 1234 5678")
        assert schema.bank_iban == "SK8975000000000012345678"

    def test_update_bic_invalid_rejected(self):
        with pytest.raises(ValidationError, match="Invalid BIC"):
            TenantUpdate(bank_bic="X")

    def test_update_bic_normalised(self):
        schema = TenantUpdate(bank_bic="subaskbx")
        assert schema.bank_bic == "SUBASKBX"

    def test_update_default_role_invalid_rejected(self):
        with pytest.raises(ValidationError):
            TenantUpdate(default_role="admin")

    def test_update_default_role_valid(self):
        schema = TenantUpdate(default_role="director")
        assert schema.default_role == "director"


# ---------------------------------------------------------------------------
# TenantRead
# ---------------------------------------------------------------------------


class TestTenantRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        now = datetime(2025, 6, 1, 12, 0, 0)
        uid = uuid4()
        schema = TenantRead(
            id=uid,
            name="Firma s.r.o.",
            ico="12345678",
            dic="2012345678",
            ic_dph="SK2012345678",
            address_street="Hlavná 1",
            address_city="Bratislava",
            address_zip="81101",
            address_country="SK",
            bank_iban="SK8975000000000012345678",
            bank_bic=None,
            schema_name="tenant_12345678",
            default_role="accountant",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert schema.id == uid
        assert schema.name == "Firma s.r.o."
        assert schema.ico == "12345678"
        assert schema.schema_name == "tenant_12345678"
        assert schema.is_active is True
        assert schema.created_at == now
        assert schema.updated_at == now

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.name = "Firma s.r.o."
                self.ico = "12345678"
                self.dic = None
                self.ic_dph = None
                self.address_street = "Hlavná 1"
                self.address_city = "Bratislava"
                self.address_zip = "81101"
                self.address_country = "SK"
                self.bank_iban = "SK8975000000000012345678"
                self.bank_bic = None
                self.schema_name = "tenant_12345678"
                self.default_role = "accountant"
                self.is_active = True
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)
                self.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = TenantRead.model_validate(orm_obj)
        assert schema.name == "Firma s.r.o."
        assert schema.ico == "12345678"
        assert schema.schema_name == "tenant_12345678"
        assert schema.is_active is True

    def test_serialisation_roundtrip(self):
        uid = uuid4()
        now = datetime(2025, 6, 1, 12, 0, 0)
        data = {
            "id": uid,
            "name": "Firma s.r.o.",
            "ico": "12345678",
            "dic": "2012345678",
            "ic_dph": None,
            "address_street": "Hlavná 1",
            "address_city": "Bratislava",
            "address_zip": "81101",
            "address_country": "SK",
            "bank_iban": "SK8975000000000012345678",
            "bank_bic": "SUBASKBX",
            "schema_name": "tenant_12345678",
            "default_role": "accountant",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        schema = TenantRead(**data)
        dumped = schema.model_dump()
        assert dumped["id"] == uid
        assert dumped["name"] == "Firma s.r.o."
        assert dumped["ico"] == "12345678"
        assert dumped["bank_bic"] == "SUBASKBX"
        assert dumped["is_active"] is True
