"""Tests for StatutoryDeadline model (app.models.statutory_deadline)."""

from datetime import date

import pytest
from sqlalchemy import TIMESTAMP, Boolean, Date, Integer, String, Text, inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.statutory_deadline import StatutoryDeadline


class TestStatutoryDeadlineSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert StatutoryDeadline.__tablename__ == "statutory_deadlines"

    def test_schema_is_shared(self):
        assert StatutoryDeadline.__table__.schema == "shared"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(StatutoryDeadline, Base)


class TestStatutoryDeadlineColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(StatutoryDeadline)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_code_column(self):
        col = self.mapper.columns["code"]
        assert isinstance(col.type, String)
        assert col.type.length == 50
        assert col.nullable is False

    def test_code_unique_constraint_in_table_args(self):
        """code uniqueness enforced via UniqueConstraint in __table_args__."""
        from sqlalchemy import UniqueConstraint as UC

        constraints = StatutoryDeadline.__table__.constraints
        uq_names = {c.name for c in constraints if isinstance(c, UC)}
        assert "uq_statutory_deadlines_code" in uq_names

    def test_name_column(self):
        col = self.mapper.columns["name"]
        assert isinstance(col.type, String)
        assert col.type.length == 200
        assert col.nullable is False

    def test_description_column(self):
        col = self.mapper.columns["description"]
        assert isinstance(col.type, Text)
        assert col.nullable is True

    def test_deadline_type_column(self):
        col = self.mapper.columns["deadline_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False

    def test_day_of_month_column(self):
        col = self.mapper.columns["day_of_month"]
        assert isinstance(col.type, Integer)
        assert col.nullable is True

    def test_month_of_year_column(self):
        col = self.mapper.columns["month_of_year"]
        assert isinstance(col.type, Integer)
        assert col.nullable is True

    def test_business_days_rule_column(self):
        col = self.mapper.columns["business_days_rule"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_institution_column(self):
        col = self.mapper.columns["institution"]
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
        """StatutoryDeadline is immutable — no updated_at column."""
        col_names = [c.key for c in self.mapper.columns]
        assert "updated_at" not in col_names

    def test_no_is_active_column(self):
        """is_active is not part of the spec — use valid_to instead."""
        col_names = [c.key for c in self.mapper.columns]
        assert "is_active" not in col_names


class TestStatutoryDeadlineIndexes:
    """Verify indexes on statutory_deadlines table."""

    def test_deadline_type_index_exists(self):
        indexes = StatutoryDeadline.__table__.indexes
        idx_names = {idx.name for idx in indexes}
        assert "ix_statutory_deadlines_deadline_type" in idx_names

    def test_deadline_type_index_columns(self):
        indexes = StatutoryDeadline.__table__.indexes
        target = next(idx for idx in indexes if idx.name == "ix_statutory_deadlines_deadline_type")
        col_names = [col.name for col in target.columns]
        assert col_names == ["deadline_type"]

    def test_valid_from_index_exists(self):
        indexes = StatutoryDeadline.__table__.indexes
        idx_names = {idx.name for idx in indexes}
        assert "ix_statutory_deadlines_valid_from" in idx_names

    def test_valid_from_index_columns(self):
        indexes = StatutoryDeadline.__table__.indexes
        target = next(idx for idx in indexes if idx.name == "ix_statutory_deadlines_valid_from")
        col_names = [col.name for col in target.columns]
        assert col_names == ["valid_from"]


class TestStatutoryDeadlineConstraints:
    """Verify CHECK constraints on StatutoryDeadline model."""

    def test_deadline_type_check_constraint_exists(self):
        """Check constraint ck_statutory_deadlines_deadline_type must exist."""
        constraints = StatutoryDeadline.__table__.constraints
        check_names = {c.name for c in constraints if hasattr(c, "sqltext")}
        assert "ck_statutory_deadlines_deadline_type" in check_names

    def test_deadline_type_check_constraint_rejects_invalid_value(self, db_session):
        """DB must reject deadline_type values outside the allowed set."""
        deadline = StatutoryDeadline(
            code="INVALID_TEST",
            name="Invalid Test",
            deadline_type="invalid_type",
            institution="Test Institution",
            day_of_month=15,
            valid_from=date(2025, 1, 1),
        )
        db_session.add(deadline)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()


class TestStatutoryDeadlineRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        deadline = StatutoryDeadline(
            code="SP_MONTHLY",
            name="Mesačný výkaz SP",
            deadline_type="monthly",
            institution="Sociálna poisťovňa",
            day_of_month=20,
            valid_from=date(2025, 1, 1),
        )

        result = repr(deadline)
        assert "SP_MONTHLY" in result
        assert "monthly" in result
        assert "Sociálna poisťovňa" in result
        assert "20" in result
        assert "2025-01-01" in result


class TestStatutoryDeadlineDB:
    """Integration tests with actual database."""

    def test_create_monthly_deadline(self, db_session):
        deadline = StatutoryDeadline(
            code="SP_MONTHLY",
            name="Mesačný výkaz SP",
            deadline_type="monthly",
            institution="Sociálna poisťovňa",
            day_of_month=20,
            valid_from=date(2025, 1, 1),
            valid_to=None,
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.id is not None
        assert deadline.created_at is not None
        assert deadline.code == "SP_MONTHLY"
        assert deadline.name == "Mesačný výkaz SP"
        assert deadline.deadline_type == "monthly"
        assert deadline.institution == "Sociálna poisťovňa"
        assert deadline.day_of_month == 20
        assert deadline.month_of_year is None
        assert deadline.description is None
        assert deadline.business_days_rule is False
        assert deadline.valid_from == date(2025, 1, 1)
        assert deadline.valid_to is None

    def test_create_monthly_with_business_days_rule(self, db_session):
        deadline = StatutoryDeadline(
            code="ZP_MONTHLY",
            name="Mesačný prehľad ZP",
            deadline_type="monthly",
            institution="ZP",
            day_of_month=3,
            business_days_rule=True,
            valid_from=date(2025, 1, 1),
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.business_days_rule is True
        assert deadline.day_of_month == 3

    def test_create_annual_deadline(self, db_session):
        deadline = StatutoryDeadline(
            code="TAX_ANNUAL",
            name="Hlásenie o dani (ročné)",
            deadline_type="annual",
            institution="Daňový úrad",
            day_of_month=30,
            month_of_year=4,
            valid_from=date(2025, 1, 1),
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.deadline_type == "annual"
        assert deadline.month_of_year == 4
        assert deadline.day_of_month == 30

    def test_create_one_time_deadline(self, db_session):
        deadline = StatutoryDeadline(
            code="SPECIAL_2025",
            name="Jednorazový termín 2025",
            deadline_type="one_time",
            institution="Sociálna poisťovňa",
            day_of_month=15,
            month_of_year=6,
            valid_from=date(2025, 1, 1),
            valid_to=date(2025, 12, 31),
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.deadline_type == "one_time"
        assert deadline.valid_to == date(2025, 12, 31)

    def test_create_with_description(self, db_session):
        deadline = StatutoryDeadline(
            code="CERT_ANNUAL",
            name="Potvrdenie o príjmoch",
            description="Potvrdenie o príjmoch zo závislej činnosti za predchádzajúci rok",
            deadline_type="annual",
            institution="Zamestnávateľ",
            day_of_month=10,
            month_of_year=3,
            valid_from=date(2025, 1, 1),
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.description == ("Potvrdenie o príjmoch zo závislej činnosti za predchádzajúci rok")

    def test_code_unique_constraint(self, db_session):
        """code must be unique across the table."""
        d1 = StatutoryDeadline(
            code="UNIQUE_TEST",
            name="First",
            deadline_type="monthly",
            institution="Test",
            day_of_month=1,
            valid_from=date(2025, 1, 1),
        )
        db_session.add(d1)
        db_session.flush()

        d2 = StatutoryDeadline(
            code="UNIQUE_TEST",
            name="Second",
            deadline_type="annual",
            institution="Test",
            day_of_month=1,
            valid_from=date(2025, 1, 1),
        )
        db_session.add(d2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_nullable_day_and_month(self, db_session):
        """day_of_month and month_of_year can be NULL."""
        deadline = StatutoryDeadline(
            code="TAX_MONTHLY_LAST",
            name="Preddavok dane",
            deadline_type="monthly",
            institution="Daňový úrad",
            day_of_month=None,
            month_of_year=None,
            valid_from=date(2025, 1, 1),
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.day_of_month is None
        assert deadline.month_of_year is None
