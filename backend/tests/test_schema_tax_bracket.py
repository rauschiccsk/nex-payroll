"""Tests for TaxBracket Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.tax_bracket import (
    TaxBracketCreate,
    TaxBracketRead,
    TaxBracketUpdate,
)

# ---------------------------------------------------------------------------
# TaxBracketCreate
# ---------------------------------------------------------------------------


class TestTaxBracketCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        schema = TaxBracketCreate(
            bracket_order=1,
            min_amount=Decimal("0.00"),
            rate_percent=Decimal("19.00"),
            nczd_annual=Decimal("5646.48"),
            nczd_monthly=Decimal("470.54"),
            nczd_reduction_threshold=Decimal("24952.06"),
            nczd_reduction_formula="44.2 * ZM - ZD",
            valid_from=date(2025, 1, 1),
        )
        assert schema.bracket_order == 1
        assert schema.min_amount == Decimal("0.00")
        assert schema.max_amount is None
        assert schema.rate_percent == Decimal("19.00")
        assert schema.nczd_annual == Decimal("5646.48")
        assert schema.nczd_monthly == Decimal("470.54")
        assert schema.nczd_reduction_threshold == Decimal("24952.06")
        assert schema.nczd_reduction_formula == "44.2 * ZM - ZD"
        assert schema.valid_from == date(2025, 1, 1)
        assert schema.valid_to is None

    def test_valid_full(self):
        schema = TaxBracketCreate(
            bracket_order=2,
            min_amount=Decimal("47537.98"),
            max_amount=Decimal("100000.00"),
            rate_percent=Decimal("25.00"),
            nczd_annual=Decimal("0.00"),
            nczd_monthly=Decimal("0.00"),
            nczd_reduction_threshold=Decimal("24952.06"),
            nczd_reduction_formula="44.2 * ZM - ZD",
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
        )
        assert schema.max_amount == Decimal("100000.00")
        assert schema.valid_to == date(2025, 12, 31)
        assert schema.bracket_order == 2

    def test_missing_required_bracket_order(self):
        with pytest.raises(ValidationError) as exc_info:
            TaxBracketCreate(
                min_amount=Decimal("0.00"),
                rate_percent=Decimal("19.00"),
                nczd_annual=Decimal("5646.48"),
                nczd_monthly=Decimal("470.54"),
                nczd_reduction_threshold=Decimal("24952.06"),
                nczd_reduction_formula="44.2 * ZM - ZD",
                valid_from=date(2025, 1, 1),
            )
        assert "bracket_order" in str(exc_info.value)

    def test_missing_required_min_amount(self):
        with pytest.raises(ValidationError):
            TaxBracketCreate(
                bracket_order=1,
                rate_percent=Decimal("19.00"),
                nczd_annual=Decimal("5646.48"),
                nczd_monthly=Decimal("470.54"),
                nczd_reduction_threshold=Decimal("24952.06"),
                nczd_reduction_formula="44.2 * ZM - ZD",
                valid_from=date(2025, 1, 1),
            )

    def test_missing_required_rate_percent(self):
        with pytest.raises(ValidationError):
            TaxBracketCreate(
                bracket_order=1,
                min_amount=Decimal("0.00"),
                nczd_annual=Decimal("5646.48"),
                nczd_monthly=Decimal("470.54"),
                nczd_reduction_threshold=Decimal("24952.06"),
                nczd_reduction_formula="44.2 * ZM - ZD",
                valid_from=date(2025, 1, 1),
            )

    def test_missing_required_nczd_annual(self):
        with pytest.raises(ValidationError):
            TaxBracketCreate(
                bracket_order=1,
                min_amount=Decimal("0.00"),
                rate_percent=Decimal("19.00"),
                nczd_monthly=Decimal("470.54"),
                nczd_reduction_threshold=Decimal("24952.06"),
                nczd_reduction_formula="44.2 * ZM - ZD",
                valid_from=date(2025, 1, 1),
            )

    def test_missing_required_nczd_monthly(self):
        with pytest.raises(ValidationError):
            TaxBracketCreate(
                bracket_order=1,
                min_amount=Decimal("0.00"),
                rate_percent=Decimal("19.00"),
                nczd_annual=Decimal("5646.48"),
                nczd_reduction_threshold=Decimal("24952.06"),
                nczd_reduction_formula="44.2 * ZM - ZD",
                valid_from=date(2025, 1, 1),
            )

    def test_missing_required_nczd_reduction_threshold(self):
        with pytest.raises(ValidationError):
            TaxBracketCreate(
                bracket_order=1,
                min_amount=Decimal("0.00"),
                rate_percent=Decimal("19.00"),
                nczd_annual=Decimal("5646.48"),
                nczd_monthly=Decimal("470.54"),
                nczd_reduction_formula="44.2 * ZM - ZD",
                valid_from=date(2025, 1, 1),
            )

    def test_missing_required_nczd_reduction_formula(self):
        with pytest.raises(ValidationError):
            TaxBracketCreate(
                bracket_order=1,
                min_amount=Decimal("0.00"),
                rate_percent=Decimal("19.00"),
                nczd_annual=Decimal("5646.48"),
                nczd_monthly=Decimal("470.54"),
                nczd_reduction_threshold=Decimal("24952.06"),
                valid_from=date(2025, 1, 1),
            )

    def test_missing_required_valid_from(self):
        with pytest.raises(ValidationError):
            TaxBracketCreate(
                bracket_order=1,
                min_amount=Decimal("0.00"),
                rate_percent=Decimal("19.00"),
                nczd_annual=Decimal("5646.48"),
                nczd_monthly=Decimal("470.54"),
                nczd_reduction_threshold=Decimal("24952.06"),
                nczd_reduction_formula="44.2 * ZM - ZD",
            )

    def test_bracket_order_must_be_positive(self):
        with pytest.raises(ValidationError) as exc_info:
            TaxBracketCreate(
                bracket_order=0,
                min_amount=Decimal("0.00"),
                rate_percent=Decimal("19.00"),
                nczd_annual=Decimal("5646.48"),
                nczd_monthly=Decimal("470.54"),
                nczd_reduction_threshold=Decimal("24952.06"),
                nczd_reduction_formula="44.2 * ZM - ZD",
                valid_from=date(2025, 1, 1),
            )
        assert "bracket_order" in str(exc_info.value)

    def test_nczd_reduction_formula_max_length(self):
        with pytest.raises(ValidationError):
            TaxBracketCreate(
                bracket_order=1,
                min_amount=Decimal("0.00"),
                rate_percent=Decimal("19.00"),
                nczd_annual=Decimal("5646.48"),
                nczd_monthly=Decimal("470.54"),
                nczd_reduction_threshold=Decimal("24952.06"),
                nczd_reduction_formula="x" * 101,
                valid_from=date(2025, 1, 1),
            )


# ---------------------------------------------------------------------------
# TaxBracketUpdate
# ---------------------------------------------------------------------------


class TestTaxBracketUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        schema = TaxBracketUpdate()
        assert schema.bracket_order is None
        assert schema.min_amount is None
        assert schema.max_amount is None
        assert schema.rate_percent is None
        assert schema.nczd_annual is None
        assert schema.nczd_monthly is None
        assert schema.nczd_reduction_threshold is None
        assert schema.nczd_reduction_formula is None
        assert schema.valid_from is None
        assert schema.valid_to is None

    def test_partial_update(self):
        schema = TaxBracketUpdate(
            rate_percent=Decimal("25.00"),
            valid_to=date(2026, 12, 31),
        )
        assert schema.rate_percent == Decimal("25.00")
        assert schema.valid_to == date(2026, 12, 31)
        assert schema.bracket_order is None

    def test_bracket_order_must_be_positive_in_update(self):
        with pytest.raises(ValidationError):
            TaxBracketUpdate(bracket_order=0)

    def test_update_nczd_reduction_formula_max_length(self):
        with pytest.raises(ValidationError):
            TaxBracketUpdate(nczd_reduction_formula="x" * 101)


# ---------------------------------------------------------------------------
# TaxBracketRead
# ---------------------------------------------------------------------------


class TestTaxBracketRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        now = datetime(2025, 6, 1, 12, 0, 0)
        uid = uuid4()
        schema = TaxBracketRead(
            id=uid,
            bracket_order=1,
            min_amount=Decimal("0.00"),
            max_amount=None,
            rate_percent=Decimal("19.00"),
            nczd_annual=Decimal("5646.48"),
            nczd_monthly=Decimal("470.54"),
            nczd_reduction_threshold=Decimal("24952.06"),
            nczd_reduction_formula="44.2 * ZM - ZD",
            valid_from=date(2025, 1, 1),
            valid_to=None,
            created_at=now,
        )
        assert schema.id == uid
        assert schema.bracket_order == 1
        assert schema.rate_percent == Decimal("19.00")
        assert schema.created_at == now

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                self.id = uuid4()
                self.bracket_order = 2
                self.min_amount = Decimal("47537.98")
                self.max_amount = Decimal("100000.00")
                self.rate_percent = Decimal("25.00")
                self.nczd_annual = Decimal("0.00")
                self.nczd_monthly = Decimal("0.00")
                self.nczd_reduction_threshold = Decimal("24952.06")
                self.nczd_reduction_formula = "44.2 * ZM - ZD"
                self.valid_from = date(2025, 1, 1)
                self.valid_to = date(2025, 12, 31)
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = TaxBracketRead.model_validate(orm_obj)
        assert schema.bracket_order == 2
        assert schema.rate_percent == Decimal("25.00")
        assert schema.max_amount == Decimal("100000.00")
        assert schema.valid_to == date(2025, 12, 31)

    def test_serialisation_roundtrip(self):
        uid = uuid4()
        data = {
            "id": uid,
            "bracket_order": 1,
            "min_amount": Decimal("0.00"),
            "max_amount": None,
            "rate_percent": Decimal("19.00"),
            "nczd_annual": Decimal("5646.48"),
            "nczd_monthly": Decimal("470.54"),
            "nczd_reduction_threshold": Decimal("24952.06"),
            "nczd_reduction_formula": "44.2 * ZM - ZD",
            "valid_from": date(2025, 1, 1),
            "valid_to": None,
            "created_at": datetime(2025, 6, 1, 12, 0, 0),
        }
        schema = TaxBracketRead(**data)
        dumped = schema.model_dump()
        assert dumped["id"] == uid
        assert dumped["bracket_order"] == 1
        assert dumped["rate_percent"] == Decimal("19.00")
        assert dumped["nczd_annual"] == Decimal("5646.48")
