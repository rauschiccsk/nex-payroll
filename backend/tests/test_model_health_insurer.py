"""Tests for HealthInsurer model (app.models.health_insurer)."""

import pytest
from sqlalchemy import TIMESTAMP, Boolean, String, inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.health_insurer import HealthInsurer


class TestHealthInsurerSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert HealthInsurer.__tablename__ == "health_insurers"

    def test_schema_is_shared(self):
        assert HealthInsurer.__table__.schema == "shared"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(HealthInsurer, Base)


class TestHealthInsurerColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(HealthInsurer)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_code_column(self):
        col = self.mapper.columns["code"]
        assert isinstance(col.type, String)
        assert col.type.length == 4
        assert col.nullable is False
        assert col.unique is True

    def test_name_column(self):
        col = self.mapper.columns["name"]
        assert isinstance(col.type, String)
        assert col.type.length == 200
        assert col.nullable is False

    def test_iban_column(self):
        col = self.mapper.columns["iban"]
        assert isinstance(col.type, String)
        assert col.type.length == 34
        assert col.nullable is False

    def test_bic_column(self):
        col = self.mapper.columns["bic"]
        assert isinstance(col.type, String)
        assert col.type.length == 11
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
        """HealthInsurer is reference data — no updated_at column."""
        col_names = [c.key for c in self.mapper.columns]
        assert "updated_at" not in col_names


class TestHealthInsurerConstraints:
    """Verify UNIQUE constraint on code."""

    def test_code_unique_constraint(self, db_session):
        """DB must reject duplicate insurer codes."""
        insurer1 = HealthInsurer(
            code="25",
            name="VšZP",
            iban="SK0000000000000000000001",
        )
        db_session.add(insurer1)
        db_session.flush()

        insurer2 = HealthInsurer(
            code="25",
            name="Duplicate VšZP",
            iban="SK0000000000000000000002",
        )
        db_session.add(insurer2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()


class TestHealthInsurerRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        insurer = HealthInsurer(
            code="25",
            name="Všeobecná zdravotná poisťovňa, a.s.",
            iban="SK0000000000000000000001",
            is_active=True,
        )

        result = repr(insurer)
        assert "25" in result
        assert "Všeobecná zdravotná poisťovňa" in result
        assert "is_active=True" in result


class TestHealthInsurerDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session):
        insurer = HealthInsurer(
            code="24",
            name="Dôvera zdravotná poisťovňa, a.s.",
            iban="SK3100000000000000000024",
            bic="KOMBSKBA",
        )
        db_session.add(insurer)
        db_session.flush()

        assert insurer.id is not None
        assert insurer.created_at is not None
        assert insurer.code == "24"
        assert insurer.name == "Dôvera zdravotná poisťovňa, a.s."
        assert insurer.iban == "SK3100000000000000000024"
        assert insurer.bic == "KOMBSKBA"
        assert insurer.is_active is True

    def test_create_without_bic(self, db_session):
        insurer = HealthInsurer(
            code="27",
            name="Union zdravotná poisťovňa, a.s.",
            iban="SK3100000000000000000027",
        )
        db_session.add(insurer)
        db_session.flush()

        assert insurer.id is not None
        assert insurer.bic is None

    def test_is_active_defaults_to_true(self, db_session):
        insurer = HealthInsurer(
            code="25",
            name="VšZP",
            iban="SK3100000000000000000025",
        )
        db_session.add(insurer)
        db_session.flush()

        assert insurer.is_active is True

    def test_deactivate_insurer(self, db_session):
        insurer = HealthInsurer(
            code="99",
            name="Inactive Insurer",
            iban="SK3100000000000000000099",
            is_active=False,
        )
        db_session.add(insurer)
        db_session.flush()

        assert insurer.is_active is False
