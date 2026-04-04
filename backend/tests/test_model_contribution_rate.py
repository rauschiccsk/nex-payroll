"""Tests for ContributionRate model (app.models.contribution_rate)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Date, Numeric, String, inspect
from sqlalchemy.dialects.postgresql import UUID

from app.models.contribution_rate import ContributionRate


class TestContributionRateSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert ContributionRate.__tablename__ == "contribution_rates"

    def test_schema_is_shared(self):
        assert ContributionRate.__table__.schema == "shared"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(ContributionRate, Base)


class TestContributionRateColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(ContributionRate)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_rate_type_column(self):
        col = self.mapper.columns["rate_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 50
        assert col.nullable is False

    def test_rate_percent_column(self):
        col = self.mapper.columns["rate_percent"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 6
        assert col.type.scale == 4
        assert col.nullable is False

    def test_max_assessment_base_column(self):
        col = self.mapper.columns["max_assessment_base"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 12
        assert col.type.scale == 2
        assert col.nullable is True

    def test_payer_column(self):
        col = self.mapper.columns["payer"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False

    def test_fund_column(self):
        col = self.mapper.columns["fund"]
        assert isinstance(col.type, String)
        assert col.type.length == 50
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
        """ContributionRate is immutable — no updated_at column."""
        col_names = [c.key for c in self.mapper.columns]
        assert "updated_at" not in col_names


class TestContributionRateIndex:
    """Verify composite index on (rate_type, valid_from)."""

    def test_rate_type_valid_from_index_exists(self):
        indexes = ContributionRate.__table__.indexes
        idx_names = {idx.name for idx in indexes}
        assert "ix_contribution_rates_rate_type_valid_from" in idx_names

    def test_rate_type_valid_from_index_columns(self):
        indexes = ContributionRate.__table__.indexes
        target = next(
            idx for idx in indexes if idx.name == "ix_contribution_rates_rate_type_valid_from"
        )
        col_names = [col.name for col in target.columns]
        assert col_names == ["rate_type", "valid_from"]


class TestContributionRateRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        rate = ContributionRate(
            rate_type="sp_employee_nemocenske",
            payer="employee",
            rate_percent=Decimal("1.4000"),
            fund="nemocenske_poistenie",
            valid_from=date(2025, 1, 1),
        )

        result = repr(rate)
        assert "sp_employee_nemocenske" in result
        assert "employee" in result
        assert "1.4000" in result
        assert "2025-01-01" in result


class TestContributionRateDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session):
        rate = ContributionRate(
            rate_type="sp_employee_starobne",
            rate_percent=Decimal("4.0000"),
            max_assessment_base=Decimal("9128.00"),
            payer="employee",
            fund="starobne_poistenie",
            valid_from=date(2025, 1, 1),
            valid_to=None,
        )
        db_session.add(rate)
        db_session.flush()

        assert rate.id is not None
        assert rate.created_at is not None
        assert rate.rate_type == "sp_employee_starobne"
        assert rate.rate_percent == Decimal("4.0000")
        assert rate.max_assessment_base == Decimal("9128.00")
        assert rate.payer == "employee"
        assert rate.fund == "starobne_poistenie"
        assert rate.valid_from == date(2025, 1, 1)
        assert rate.valid_to is None

    def test_create_without_max_assessment_base(self, db_session):
        rate = ContributionRate(
            rate_type="sp_employee_nemocenske",
            rate_percent=Decimal("1.4000"),
            payer="employee",
            fund="nemocenske_poistenie",
            valid_from=date(2025, 1, 1),
        )
        db_session.add(rate)
        db_session.flush()

        assert rate.id is not None
        assert rate.max_assessment_base is None

    def test_create_employer_rate(self, db_session):
        rate = ContributionRate(
            rate_type="sp_employer_starobne",
            rate_percent=Decimal("14.0000"),
            max_assessment_base=Decimal("9128.00"),
            payer="employer",
            fund="starobne_poistenie",
            valid_from=date(2025, 1, 1),
        )
        db_session.add(rate)
        db_session.flush()

        assert rate.payer == "employer"
        assert rate.rate_percent == Decimal("14.0000")

    def test_valid_to_date(self, db_session):
        rate = ContributionRate(
            rate_type="zp_employee",
            rate_percent=Decimal("4.0000"),
            payer="employee",
            fund="zdravotne_poistenie",
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
        )
        db_session.add(rate)
        db_session.flush()

        assert rate.valid_from == date(2024, 1, 1)
        assert rate.valid_to == date(2024, 12, 31)
