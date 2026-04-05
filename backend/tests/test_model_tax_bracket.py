"""Tests for TaxBracket model (app.models.tax_bracket)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date, Integer, Numeric, String, inspect
from sqlalchemy.dialects.postgresql import UUID

from app.models.tax_bracket import TaxBracket


class TestTaxBracketSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert TaxBracket.__tablename__ == "tax_brackets"

    def test_schema_is_shared(self):
        assert TaxBracket.__table__.schema == "shared"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(TaxBracket, Base)


class TestTaxBracketColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(TaxBracket)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_bracket_order_column(self):
        col = self.mapper.columns["bracket_order"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_min_amount_column(self):
        col = self.mapper.columns["min_amount"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 12
        assert col.type.scale == 2
        assert col.nullable is False

    def test_max_amount_column(self):
        col = self.mapper.columns["max_amount"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 12
        assert col.type.scale == 2
        assert col.nullable is True

    def test_rate_percent_column(self):
        col = self.mapper.columns["rate_percent"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 5
        assert col.type.scale == 2
        assert col.nullable is False

    def test_nczd_annual_column(self):
        col = self.mapper.columns["nczd_annual"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 2
        assert col.nullable is False

    def test_nczd_monthly_column(self):
        col = self.mapper.columns["nczd_monthly"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 2
        assert col.nullable is False

    def test_nczd_reduction_threshold_column(self):
        col = self.mapper.columns["nczd_reduction_threshold"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 12
        assert col.type.scale == 2
        assert col.nullable is False

    def test_nczd_reduction_formula_column(self):
        col = self.mapper.columns["nczd_reduction_formula"]
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert col.nullable is False

    def test_valid_from_column(self):
        col = self.mapper.columns["valid_from"]
        assert isinstance(col.type, Date)
        assert col.nullable is False

    def test_valid_to_column(self):
        col = self.mapper.columns["valid_to"]
        assert isinstance(col.type, Date)
        assert col.nullable is True

    def test_created_at_column(self):
        col = self.mapper.columns["created_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is False
        assert col.server_default is not None

    def test_no_updated_at_column(self):
        """TaxBracket is immutable — no updated_at column."""
        col_names = [c.key for c in self.mapper.columns]
        assert "updated_at" not in col_names


class TestTaxBracketIndex:
    """Verify composite index on (valid_from, bracket_order)."""

    def test_valid_from_bracket_order_index_exists(self):
        indexes = TaxBracket.__table__.indexes
        idx_names = {idx.name for idx in indexes}
        assert "ix_tax_brackets_valid_from_bracket_order" in idx_names

    def test_valid_from_bracket_order_index_columns(self):
        indexes = TaxBracket.__table__.indexes
        target = next(
            idx
            for idx in indexes
            if idx.name == "ix_tax_brackets_valid_from_bracket_order"
        )
        col_names = [col.name for col in target.columns]
        assert col_names == ["valid_from", "bracket_order"]


class TestTaxBracketRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        bracket = TaxBracket(
            bracket_order=1,
            min_amount=Decimal("0.00"),
            max_amount=Decimal("44579.76"),
            rate_percent=Decimal("19.00"),
            nczd_annual=Decimal("5646.48"),
            nczd_monthly=Decimal("470.54"),
            nczd_reduction_threshold=Decimal("24952.06"),
            nczd_reduction_formula="44.2 * ZM - ZD",
            valid_from=date(2025, 1, 1),
        )

        result = repr(bracket)
        assert "order=1" in result
        assert "19.00" in result
        assert "0.00" in result
        assert "44579.76" in result
        assert "2025-01-01" in result


class TestTaxBracketDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session):
        bracket = TaxBracket(
            bracket_order=1,
            min_amount=Decimal("0.00"),
            max_amount=Decimal("44579.76"),
            rate_percent=Decimal("19.00"),
            nczd_annual=Decimal("5646.48"),
            nczd_monthly=Decimal("470.54"),
            nczd_reduction_threshold=Decimal("24952.06"),
            nczd_reduction_formula="44.2 * ZM - ZD",
            valid_from=date(2025, 1, 1),
            valid_to=None,
        )
        db_session.add(bracket)
        db_session.flush()

        assert bracket.id is not None
        assert bracket.created_at is not None
        assert bracket.bracket_order == 1
        assert bracket.min_amount == Decimal("0.00")
        assert bracket.max_amount == Decimal("44579.76")
        assert bracket.rate_percent == Decimal("19.00")
        assert bracket.nczd_annual == Decimal("5646.48")
        assert bracket.nczd_monthly == Decimal("470.54")
        assert bracket.nczd_reduction_threshold == Decimal("24952.06")
        assert bracket.nczd_reduction_formula == "44.2 * ZM - ZD"
        assert bracket.valid_from == date(2025, 1, 1)
        assert bracket.valid_to is None

    def test_create_second_bracket(self, db_session):
        """Test higher tax bracket (25%) with no max_amount."""
        bracket = TaxBracket(
            bracket_order=2,
            min_amount=Decimal("44579.77"),
            max_amount=None,
            rate_percent=Decimal("25.00"),
            nczd_annual=Decimal("5646.48"),
            nczd_monthly=Decimal("470.54"),
            nczd_reduction_threshold=Decimal("24952.06"),
            nczd_reduction_formula="44.2 * ZM - ZD",
            valid_from=date(2025, 1, 1),
        )
        db_session.add(bracket)
        db_session.flush()

        assert bracket.id is not None
        assert bracket.bracket_order == 2
        assert bracket.max_amount is None
        assert bracket.rate_percent == Decimal("25.00")

    def test_valid_to_date(self, db_session):
        bracket = TaxBracket(
            bracket_order=1,
            min_amount=Decimal("0.00"),
            max_amount=Decimal("38553.01"),
            rate_percent=Decimal("19.00"),
            nczd_annual=Decimal("4922.82"),
            nczd_monthly=Decimal("410.24"),
            nczd_reduction_threshold=Decimal("21754.18"),
            nczd_reduction_formula="44.2 * ZM - ZD",
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
        )
        db_session.add(bracket)
        db_session.flush()

        assert bracket.valid_from == date(2024, 1, 1)
        assert bracket.valid_to == date(2024, 12, 31)
