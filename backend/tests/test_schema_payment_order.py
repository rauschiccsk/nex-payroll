"""Tests for PaymentOrder Pydantic schemas (Create, Update, Read)."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.payment_order import (
    PaymentOrderCreate,
    PaymentOrderRead,
    PaymentOrderUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_EMPLOYEE_ID = uuid4()
_HEALTH_INSURER_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for PaymentOrderCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "period_year": 2025,
        "period_month": 1,
        "payment_type": "net_wage",
        "recipient_name": "Jan Novak",
        "recipient_iban": "SK3112000000198742637541",
        "amount": Decimal("1234.56"),
    }


def _read_kwargs() -> dict:
    """Return a complete dict for constructing PaymentOrderRead."""
    now = datetime(2025, 6, 1, 12, 0, 0)
    return {
        "id": uuid4(),
        "tenant_id": _TENANT_ID,
        "period_year": 2025,
        "period_month": 1,
        "payment_type": "net_wage",
        "recipient_name": "Jan Novak",
        "recipient_iban": "SK3112000000198742637541",
        "recipient_bic": None,
        "amount": Decimal("1234.56"),
        "variable_symbol": None,
        "specific_symbol": None,
        "constant_symbol": None,
        "reference": None,
        "status": "pending",
        "employee_id": None,
        "health_insurer_id": None,
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# PaymentOrderCreate
# ---------------------------------------------------------------------------


class TestPaymentOrderCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        """Valid creation with only required fields — defaults applied."""
        schema = PaymentOrderCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.period_year == 2025
        assert schema.period_month == 1
        assert schema.payment_type == "net_wage"
        assert schema.recipient_name == "Jan Novak"
        assert schema.recipient_iban == "SK3112000000198742637541"
        assert schema.amount == Decimal("1234.56")
        # defaults
        assert schema.status == "pending"
        assert schema.recipient_bic is None
        assert schema.variable_symbol is None
        assert schema.specific_symbol is None
        assert schema.constant_symbol is None
        assert schema.reference is None
        assert schema.employee_id is None
        assert schema.health_insurer_id is None

    def test_valid_full(self):
        """Valid creation with all fields explicitly set."""
        schema = PaymentOrderCreate(
            **_valid_create_kwargs(),
            recipient_bic="TATRSKBX",
            variable_symbol="1234567890",
            specific_symbol="0012345678",
            constant_symbol="0558",
            reference="PAYROLL-2025-01-NOVAK",
            status="exported",
            employee_id=_EMPLOYEE_ID,
            health_insurer_id=_HEALTH_INSURER_ID,
        )
        assert schema.recipient_bic == "TATRSKBX"
        assert schema.variable_symbol == "1234567890"
        assert schema.specific_symbol == "0012345678"
        assert schema.constant_symbol == "0558"
        assert schema.reference == "PAYROLL-2025-01-NOVAK"
        assert schema.status == "exported"
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.health_insurer_id == _HEALTH_INSURER_ID

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_period_year(self):
        kw = _valid_create_kwargs()
        del kw["period_year"]
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_missing_required_period_month(self):
        kw = _valid_create_kwargs()
        del kw["period_month"]
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_missing_required_payment_type(self):
        kw = _valid_create_kwargs()
        del kw["payment_type"]
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "payment_type" in str(exc_info.value)

    def test_missing_required_recipient_name(self):
        kw = _valid_create_kwargs()
        del kw["recipient_name"]
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "recipient_name" in str(exc_info.value)

    def test_missing_required_recipient_iban(self):
        kw = _valid_create_kwargs()
        del kw["recipient_iban"]
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "recipient_iban" in str(exc_info.value)

    def test_missing_required_amount(self):
        kw = _valid_create_kwargs()
        del kw["amount"]
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "amount" in str(exc_info.value)

    # -- payment_type validation --

    def test_invalid_payment_type_rejected(self):
        """Invalid payment_type value must be rejected."""
        kw = _valid_create_kwargs()
        kw["payment_type"] = "invalid_type"
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "payment_type" in str(exc_info.value)

    def test_all_valid_payment_types(self):
        """All 7 payment types defined in DESIGN.md must be accepted."""
        valid_types = [
            "net_wage",
            "sp",
            "zp_vszp",
            "zp_dovera",
            "zp_union",
            "tax",
            "pillar2",
        ]
        for ptype in valid_types:
            kw = _valid_create_kwargs()
            kw["payment_type"] = ptype
            schema = PaymentOrderCreate(**kw)
            assert schema.payment_type == ptype

    # -- status validation --

    def test_invalid_status_rejected(self):
        """Invalid status value must be rejected."""
        kw = _valid_create_kwargs()
        kw["status"] = "invalid_status"
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "status" in str(exc_info.value)

    def test_all_valid_statuses(self):
        """All 3 status values from DESIGN.md must be accepted."""
        valid_statuses = ["pending", "exported", "paid"]
        for status in valid_statuses:
            kw = _valid_create_kwargs()
            kw["status"] = status
            schema = PaymentOrderCreate(**kw)
            assert schema.status == status

    # -- period_month boundary validation (ge=1, le=12) --

    def test_period_month_zero_rejected(self):
        """period_month=0 must be rejected (ge=1)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 0
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_period_month_13_rejected(self):
        """period_month=13 must be rejected (le=12)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 13
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_period_month_boundary_min(self):
        """period_month=1 must be accepted (ge=1)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 1
        schema = PaymentOrderCreate(**kw)
        assert schema.period_month == 1

    def test_period_month_boundary_max(self):
        """period_month=12 must be accepted (le=12)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 12
        schema = PaymentOrderCreate(**kw)
        assert schema.period_month == 12

    # -- period_year boundary validation (ge=2000, le=2100) --

    def test_period_year_below_range_rejected(self):
        kw = _valid_create_kwargs()
        kw["period_year"] = 1999
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_period_year_above_range_rejected(self):
        kw = _valid_create_kwargs()
        kw["period_year"] = 2101
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_period_year_at_lower_bound_accepted(self):
        kw = _valid_create_kwargs()
        kw["period_year"] = 2000
        schema = PaymentOrderCreate(**kw)
        assert schema.period_year == 2000

    def test_period_year_at_upper_bound_accepted(self):
        kw = _valid_create_kwargs()
        kw["period_year"] = 2100
        schema = PaymentOrderCreate(**kw)
        assert schema.period_year == 2100

    # -- max_length constraints --

    def test_recipient_name_max_length(self):
        kw = _valid_create_kwargs()
        kw["recipient_name"] = "x" * 201
        with pytest.raises(ValidationError):
            PaymentOrderCreate(**kw)

    def test_recipient_iban_max_length(self):
        kw = _valid_create_kwargs()
        kw["recipient_iban"] = "x" * 35
        with pytest.raises(ValidationError):
            PaymentOrderCreate(**kw)

    def test_recipient_bic_max_length(self):
        kw = _valid_create_kwargs()
        kw["recipient_bic"] = "x" * 12
        with pytest.raises(ValidationError):
            PaymentOrderCreate(**kw)

    def test_variable_symbol_max_length(self):
        kw = _valid_create_kwargs()
        kw["variable_symbol"] = "x" * 11
        with pytest.raises(ValidationError):
            PaymentOrderCreate(**kw)

    def test_specific_symbol_max_length(self):
        kw = _valid_create_kwargs()
        kw["specific_symbol"] = "x" * 11
        with pytest.raises(ValidationError):
            PaymentOrderCreate(**kw)

    def test_constant_symbol_max_length(self):
        kw = _valid_create_kwargs()
        kw["constant_symbol"] = "x" * 5
        with pytest.raises(ValidationError):
            PaymentOrderCreate(**kw)

    def test_reference_max_length(self):
        kw = _valid_create_kwargs()
        kw["reference"] = "x" * 141
        with pytest.raises(ValidationError):
            PaymentOrderCreate(**kw)

    # -- amount gt=0 validation --

    def test_amount_zero_rejected(self):
        """amount=0 must be rejected (gt=0)."""
        kw = _valid_create_kwargs()
        kw["amount"] = Decimal("0.00")
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "amount" in str(exc_info.value)

    def test_amount_negative_rejected(self):
        """Negative amount must be rejected (gt=0)."""
        kw = _valid_create_kwargs()
        kw["amount"] = Decimal("-100.00")
        with pytest.raises(ValidationError) as exc_info:
            PaymentOrderCreate(**kw)
        assert "amount" in str(exc_info.value)

    def test_amount_positive_accepted(self):
        """Small positive amount must be accepted."""
        kw = _valid_create_kwargs()
        kw["amount"] = Decimal("0.01")
        schema = PaymentOrderCreate(**kw)
        assert schema.amount == Decimal("0.01")


# ---------------------------------------------------------------------------
# PaymentOrderUpdate
# ---------------------------------------------------------------------------


class TestPaymentOrderUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        """All fields default to None when no data supplied."""
        schema = PaymentOrderUpdate()
        assert schema.recipient_name is None
        assert schema.recipient_iban is None
        assert schema.recipient_bic is None
        assert schema.amount is None
        assert schema.variable_symbol is None
        assert schema.specific_symbol is None
        assert schema.constant_symbol is None
        assert schema.reference is None
        assert schema.status is None
        assert schema.employee_id is None
        assert schema.health_insurer_id is None

    def test_partial_update_status(self):
        """Only supplied fields are set; the rest remain None."""
        schema = PaymentOrderUpdate(status="exported")
        assert schema.status == "exported"
        assert schema.recipient_name is None
        assert schema.amount is None

    def test_partial_update_amount(self):
        schema = PaymentOrderUpdate(amount=Decimal("999.99"))
        assert schema.amount == Decimal("999.99")
        assert schema.status is None

    def test_partial_update_recipient(self):
        schema = PaymentOrderUpdate(
            recipient_name="Updated Name",
            recipient_iban="SK9999999999999999999999",
        )
        assert schema.recipient_name == "Updated Name"
        assert schema.recipient_iban == "SK9999999999999999999999"
        assert schema.status is None

    def test_full_update(self):
        """All fields explicitly set."""
        schema = PaymentOrderUpdate(
            recipient_name="Updated Name",
            recipient_iban="SK9999999999999999999999",
            recipient_bic="TATRSKBX",
            amount=Decimal("5000.00"),
            variable_symbol="9876543210",
            specific_symbol="0098765432",
            constant_symbol="0308",
            reference="UPDATED-REF",
            status="paid",
            employee_id=_EMPLOYEE_ID,
            health_insurer_id=_HEALTH_INSURER_ID,
        )
        assert schema.recipient_name == "Updated Name"
        assert schema.recipient_iban == "SK9999999999999999999999"
        assert schema.recipient_bic == "TATRSKBX"
        assert schema.amount == Decimal("5000.00")
        assert schema.variable_symbol == "9876543210"
        assert schema.specific_symbol == "0098765432"
        assert schema.constant_symbol == "0308"
        assert schema.reference == "UPDATED-REF"
        assert schema.status == "paid"
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.health_insurer_id == _HEALTH_INSURER_ID

    # -- validation in update --

    def test_invalid_status_in_update(self):
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(status="invalid_status")

    def test_invalid_payment_type_not_in_update(self):
        """payment_type is not an updatable field — cannot be supplied."""
        assert "payment_type" not in PaymentOrderUpdate.model_fields

    def test_recipient_name_max_length_in_update(self):
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(recipient_name="x" * 201)

    def test_recipient_iban_max_length_in_update(self):
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(recipient_iban="x" * 35)

    def test_recipient_bic_max_length_in_update(self):
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(recipient_bic="x" * 12)

    def test_variable_symbol_max_length_in_update(self):
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(variable_symbol="x" * 11)

    def test_specific_symbol_max_length_in_update(self):
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(specific_symbol="x" * 11)

    def test_constant_symbol_max_length_in_update(self):
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(constant_symbol="x" * 5)

    def test_reference_max_length_in_update(self):
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(reference="x" * 141)

    def test_amount_gt_zero_in_update(self):
        """amount=0 must be rejected in update too (gt=0)."""
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(amount=Decimal("0.00"))

    def test_amount_negative_in_update(self):
        with pytest.raises(ValidationError):
            PaymentOrderUpdate(amount=Decimal("-1.00"))

    # -- Update excludes immutable / identity fields --

    def test_update_excludes_tenant_id(self):
        """tenant_id is not updatable — field should not exist on Update schema."""
        assert "tenant_id" not in PaymentOrderUpdate.model_fields

    def test_update_excludes_period_year(self):
        """period_year is part of business key — not updatable."""
        assert "period_year" not in PaymentOrderUpdate.model_fields

    def test_update_excludes_period_month(self):
        """period_month is part of business key — not updatable."""
        assert "period_month" not in PaymentOrderUpdate.model_fields

    def test_update_excludes_payment_type(self):
        """payment_type is part of business key — not updatable."""
        assert "payment_type" not in PaymentOrderUpdate.model_fields


# ---------------------------------------------------------------------------
# PaymentOrderRead
# ---------------------------------------------------------------------------


class TestPaymentOrderRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        """Construct Read schema from a plain dict."""
        kw = _read_kwargs()
        schema = PaymentOrderRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.period_year == 2025
        assert schema.period_month == 1
        assert schema.payment_type == "net_wage"
        assert schema.recipient_name == "Jan Novak"
        assert schema.recipient_iban == "SK3112000000198742637541"
        assert schema.recipient_bic is None
        assert schema.amount == Decimal("1234.56")
        assert schema.variable_symbol is None
        assert schema.specific_symbol is None
        assert schema.constant_symbol is None
        assert schema.reference is None
        assert schema.status == "pending"
        assert schema.employee_id is None
        assert schema.health_insurer_id is None
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.tenant_id = _TENANT_ID
                self.period_year = 2025
                self.period_month = 3
                self.payment_type = "sp"
                self.recipient_name = "Socialna poistovna"
                self.recipient_iban = "SK8975000000000012345678"
                self.recipient_bic = "CEKOSKBX"
                self.amount = Decimal("456.78")
                self.variable_symbol = "1234567890"
                self.specific_symbol = None
                self.constant_symbol = "0558"
                self.reference = "SP-2025-03"
                self.status = "exported"
                self.employee_id = None
                self.health_insurer_id = None
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)
                self.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = PaymentOrderRead.model_validate(orm_obj)
        assert schema.payment_type == "sp"
        assert schema.recipient_name == "Socialna poistovna"
        assert schema.recipient_bic == "CEKOSKBX"
        assert schema.amount == Decimal("456.78")
        assert schema.status == "exported"
        assert schema.constant_symbol == "0558"
        assert schema.reference == "SP-2025-03"

    def test_serialisation_roundtrip(self):
        """model_dump() produces a dict that can reconstruct the schema."""
        kw = _read_kwargs()
        schema = PaymentOrderRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["period_year"] == 2025
        assert dumped["period_month"] == 1
        assert dumped["payment_type"] == "net_wage"
        assert dumped["recipient_name"] == "Jan Novak"
        assert dumped["recipient_iban"] == "SK3112000000198742637541"
        assert dumped["amount"] == Decimal("1234.56")
        assert dumped["status"] == "pending"
        assert dumped["employee_id"] is None
        assert dumped["health_insurer_id"] is None

    def test_read_all_fields_present(self):
        """Read schema exposes every field from the model."""
        expected_fields = {
            "id",
            "tenant_id",
            "period_year",
            "period_month",
            "payment_type",
            "recipient_name",
            "recipient_iban",
            "recipient_bic",
            "amount",
            "variable_symbol",
            "specific_symbol",
            "constant_symbol",
            "reference",
            "status",
            "employee_id",
            "health_insurer_id",
            "created_at",
            "updated_at",
        }
        assert set(PaymentOrderRead.model_fields.keys()) == expected_fields
