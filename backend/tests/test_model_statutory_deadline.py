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

    def test_deadline_type_column(self):
        col = self.mapper.columns["deadline_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 30
        assert col.nullable is False

    def test_institution_column(self):
        col = self.mapper.columns["institution"]
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert col.nullable is False

    def test_day_of_month_column(self):
        col = self.mapper.columns["day_of_month"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_description_column(self):
        col = self.mapper.columns["description"]
        assert isinstance(col.type, Text)
        assert col.nullable is False

    def test_valid_from_column(self):
        col = self.mapper.columns["valid_from"]
        assert isinstance(col.type, Date)
        assert col.nullable is False

    def test_valid_to_column(self):
        col = self.mapper.columns["valid_to"]
        assert isinstance(col.type, Date)
        assert col.nullable is True

    def test_is_active_column(self):
        col = self.mapper.columns["is_active"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

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
            deadline_type="invalid_type",
            institution="Test Institution",
            day_of_month=15,
            description="Test deadline",
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
            deadline_type="sp_monthly",
            institution="Sociálna poisťovňa",
            day_of_month=20,
            description="Mesačný výkaz pre Sociálnu poisťovňu",
            valid_from=date(2025, 1, 1),
        )

        result = repr(deadline)
        assert "sp_monthly" in result
        assert "Sociálna poisťovňa" in result
        assert "20" in result
        assert "2025-01-01" in result


class TestStatutoryDeadlineDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session):
        deadline = StatutoryDeadline(
            deadline_type="sp_monthly",
            institution="Sociálna poisťovňa",
            day_of_month=20,
            description="Mesačný výkaz pre Sociálnu poisťovňu",
            valid_from=date(2025, 1, 1),
            valid_to=None,
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.id is not None
        assert deadline.created_at is not None
        assert deadline.deadline_type == "sp_monthly"
        assert deadline.institution == "Sociálna poisťovňa"
        assert deadline.day_of_month == 20
        assert deadline.description == "Mesačný výkaz pre Sociálnu poisťovňu"
        assert deadline.valid_from == date(2025, 1, 1)
        assert deadline.valid_to is None
        assert deadline.is_active is True

    def test_create_with_valid_to(self, db_session):
        deadline = StatutoryDeadline(
            deadline_type="zp_monthly",
            institution="VšZP",
            day_of_month=3,
            description="Mesačný výkaz pre VšZP",
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.valid_from == date(2024, 1, 1)
        assert deadline.valid_to == date(2024, 12, 31)

    def test_create_inactive_deadline(self, db_session):
        deadline = StatutoryDeadline(
            deadline_type="tax_advance",
            institution="Daňový úrad",
            day_of_month=25,
            description="Preddavok na daň z príjmov",
            valid_from=date(2025, 1, 1),
            is_active=False,
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.is_active is False

    def test_create_tax_reconciliation(self, db_session):
        deadline = StatutoryDeadline(
            deadline_type="tax_reconciliation",
            institution="Daňový úrad",
            day_of_month=31,
            description="Ročné zúčtovanie dane",
            valid_from=date(2025, 1, 1),
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.deadline_type == "tax_reconciliation"
        assert deadline.day_of_month == 31

    def test_create_sp_annual(self, db_session):
        deadline = StatutoryDeadline(
            deadline_type="sp_annual",
            institution="Sociálna poisťovňa",
            day_of_month=30,
            description="Ročný výkaz pre Sociálnu poisťovňu",
            valid_from=date(2025, 1, 1),
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.deadline_type == "sp_annual"

    def test_create_zp_annual(self, db_session):
        deadline = StatutoryDeadline(
            deadline_type="zp_annual",
            institution="VšZP",
            day_of_month=31,
            description="Ročné zúčtovanie poistného na ZP",
            valid_from=date(2025, 1, 1),
        )
        db_session.add(deadline)
        db_session.flush()

        assert deadline.deadline_type == "zp_annual"
