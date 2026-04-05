"""Tests for MonthlyReport model (app.models.monthly_report)."""

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Integer, String, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.health_insurer import HealthInsurer
from app.models.monthly_report import MonthlyReport
from app.models.tenant import Tenant

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent."""
    t = Tenant(
        name="MonthlyReport Test Firma s.r.o.",
        ico="99000011",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000011",
        schema_name="tenant_test_monthly_report",
    )
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture()
def health_insurer(db_session):
    """Create a HealthInsurer for ZP-type reports."""
    hi = HealthInsurer(
        code="25",
        name="Všeobecná zdravotná poisťovňa, a.s.",
        iban="SK0000000000000000000025",
    )
    db_session.add(hi)
    db_session.flush()
    return hi


def _make_report(tenant, **overrides):
    """Return a MonthlyReport instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "period_year": 2025,
        "period_month": 1,
        "report_type": "sp_monthly",
        "file_path": "/data/reports/2025/01/sp_monthly.xml",
        "deadline_date": date(2025, 2, 8),
        "institution": "Sociálna poisťovňa",
    }
    defaults.update(overrides)
    return MonthlyReport(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestMonthlyReportSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert MonthlyReport.__tablename__ == "monthly_reports"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(MonthlyReport, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(MonthlyReport, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(MonthlyReport, TimestampMixin)


class TestMonthlyReportColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(MonthlyReport)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_tenant_id_column(self):
        col = self.mapper.columns["tenant_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_health_insurer_id_column(self):
        col = self.mapper.columns["health_insurer_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is True

    def test_period_year_column(self):
        col = self.mapper.columns["period_year"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_period_month_column(self):
        col = self.mapper.columns["period_month"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_report_type_column(self):
        col = self.mapper.columns["report_type"]
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_file_path_column(self):
        col = self.mapper.columns["file_path"]
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_file_format_column(self):
        col = self.mapper.columns["file_format"]
        assert isinstance(col.type, String)
        assert col.nullable is False
        assert col.server_default is not None

    def test_status_column(self):
        col = self.mapper.columns["status"]
        assert isinstance(col.type, String)
        assert col.nullable is False
        assert col.server_default is not None

    def test_deadline_date_column(self):
        col = self.mapper.columns["deadline_date"]
        assert col.nullable is False

    def test_institution_column(self):
        col = self.mapper.columns["institution"]
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_submitted_at_column(self):
        col = self.mapper.columns["submitted_at"]
        assert col.nullable is True

    def test_unique_constraint_tenant_period_type(self):
        """UniqueConstraint with explicit name must exist."""
        table = MonthlyReport.__table__
        uq_names = [
            c.name
            for c in table.constraints
            if hasattr(c, "columns") and len(c.columns) > 1
        ]
        assert "uq_monthly_reports_tenant_year_month_type" in uq_names

    def test_check_constraint_report_type(self):
        """CheckConstraint for report_type must exist."""
        table = MonthlyReport.__table__
        ck_names = [c.name for c in table.constraints if hasattr(c, "sqltext")]
        assert "ck_monthly_reports_report_type" in ck_names

    def test_check_constraint_status(self):
        """CheckConstraint for status must exist."""
        table = MonthlyReport.__table__
        ck_names = [c.name for c in table.constraints if hasattr(c, "sqltext")]
        assert "ck_monthly_reports_status" in ck_names


# ===================================================================
# Repr
# ===================================================================


class TestMonthlyReportRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        report = MonthlyReport(
            report_type="sp_monthly",
            period_year=2025,
            period_month=1,
            status="generated",
        )
        result = repr(report)
        assert "MonthlyReport" in result
        assert "sp_monthly" in result
        assert "2025" in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestMonthlyReportConstraints:
    """DB-level constraint enforcement."""

    def test_fk_tenant_nonexistent(self, db_session, tenant):
        """FK to tenant must exist."""
        report = _make_report(tenant, tenant_id=uuid.uuid4())
        db_session.add(report)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_health_insurer_nonexistent(self, db_session, tenant):
        """FK to health_insurer must exist if set."""
        report = _make_report(
            tenant,
            health_insurer_id=uuid.uuid4(),
            report_type="zp_vszp",
        )
        db_session.add(report)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_unique_tenant_period_type(self, db_session, tenant):
        """Duplicate (tenant_id, period_year, period_month, report_type) must be rejected."""
        r1 = _make_report(tenant)
        db_session.add(r1)
        db_session.flush()

        r2 = _make_report(tenant)
        db_session.add(r2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_unique_different_type_allowed(self, db_session, tenant, health_insurer):
        """Same (tenant_id, period_year, period_month) with different report_type is allowed."""
        r1 = _make_report(tenant, report_type="sp_monthly")
        r2 = _make_report(
            tenant,
            report_type="zp_vszp",
            health_insurer_id=health_insurer.id,
            institution="VšZP",
        )
        db_session.add_all([r1, r2])
        db_session.flush()
        assert r1.id != r2.id

    def test_unique_different_month_allowed(self, db_session, tenant):
        """Same (tenant_id, period_year, report_type) with different month is allowed."""
        r1 = _make_report(tenant, period_month=1)
        r2 = _make_report(tenant, period_month=2)
        db_session.add_all([r1, r2])
        db_session.flush()
        assert r1.id != r2.id

    def test_check_invalid_report_type(self, db_session, tenant):
        """Invalid report_type must be rejected."""
        report = _make_report(tenant, report_type="invalid_type")
        db_session.add(report)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_invalid_status(self, db_session, tenant):
        """Invalid status must be rejected."""
        report = _make_report(tenant, status="invalid_status")
        db_session.add(report)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_report_type(self, db_session, tenant):
        """report_type cannot be NULL."""
        report = _make_report(tenant, report_type=None)
        db_session.add(report)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_file_path(self, db_session, tenant):
        """file_path cannot be NULL."""
        report = _make_report(tenant, file_path=None)
        db_session.add(report)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_deadline_date(self, db_session, tenant):
        """deadline_date cannot be NULL."""
        report = _make_report(tenant, deadline_date=None)
        db_session.add(report)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_institution(self, db_session, tenant):
        """institution cannot be NULL."""
        report = _make_report(tenant, institution=None)
        db_session.add(report)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_tenant_restrict_delete(self, db_session, tenant):
        """Deleting a tenant with monthly reports must be rejected (RESTRICT).

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        report = _make_report(tenant)
        db_session.add(report)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM tenants WHERE id = :id"),
                {"id": str(tenant.id)},
            )
        db_session.rollback()


# ===================================================================
# Database integration tests
# ===================================================================


class TestMonthlyReportDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, health_insurer):
        """Full create with all fields — verify round-trip."""
        submitted = datetime(2025, 2, 5, 10, 0, 0, tzinfo=UTC)
        report = _make_report(
            tenant,
            period_year=2025,
            period_month=1,
            report_type="zp_vszp",
            file_path="/data/reports/2025/01/zp_vszp.xml",
            file_format="xml",
            status="submitted",
            deadline_date=date(2025, 2, 8),
            institution="VšZP",
            health_insurer_id=health_insurer.id,
            submitted_at=submitted,
        )
        db_session.add(report)
        db_session.flush()

        assert report.id is not None
        assert report.created_at is not None
        assert report.updated_at is not None
        assert report.tenant_id == tenant.id
        assert report.health_insurer_id == health_insurer.id
        assert report.period_year == 2025
        assert report.period_month == 1
        assert report.report_type == "zp_vszp"
        assert report.file_path == "/data/reports/2025/01/zp_vszp.xml"
        assert report.file_format == "xml"
        assert report.status == "submitted"
        assert report.deadline_date == date(2025, 2, 8)
        assert report.institution == "VšZP"
        assert report.submitted_at == submitted

    def test_create_minimal_defaults(self, db_session, tenant):
        """Create with only required fields — verify all server_defaults."""
        report = _make_report(tenant)
        db_session.add(report)
        db_session.flush()

        assert report.id is not None
        assert report.file_format == "xml"
        assert report.status == "generated"
        assert report.health_insurer_id is None
        assert report.submitted_at is None

    def test_update_status(self, db_session, tenant):
        """Status can be updated from generated to submitted."""
        report = _make_report(tenant)
        db_session.add(report)
        db_session.flush()

        report.status = "submitted"
        report.submitted_at = datetime(2025, 2, 5, 10, 0, 0, tzinfo=UTC)
        db_session.flush()

        assert report.status == "submitted"
        assert report.submitted_at is not None

    def test_health_insurer_nullable(self, db_session, tenant):
        """health_insurer_id can be NULL (e.g. for SP or tax reports)."""
        report = _make_report(tenant, health_insurer_id=None)
        db_session.add(report)
        db_session.flush()
        assert report.health_insurer_id is None

    def test_health_insurer_with_zp_type(self, db_session, tenant, health_insurer):
        """health_insurer_id can be set for ZP-type reports."""
        report = _make_report(
            tenant,
            report_type="zp_vszp",
            health_insurer_id=health_insurer.id,
        )
        db_session.add(report)
        db_session.flush()
        assert report.health_insurer_id == health_insurer.id
