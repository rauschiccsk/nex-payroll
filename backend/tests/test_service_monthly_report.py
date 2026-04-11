"""Tests for MonthlyReport service layer."""

from datetime import date
from uuid import uuid4

import pytest

from app.models.health_insurer import HealthInsurer
from app.models.monthly_report import MonthlyReport
from app.models.tenant import Tenant
from app.schemas.monthly_report import MonthlyReportCreate, MonthlyReportUpdate
from app.services.monthly_report import (
    ALLOWED_REPORT_TYPES,
    ALLOWED_STATUSES,
    count_monthly_reports,
    create_monthly_report,
    delete_monthly_report,
    get_monthly_report,
    list_monthly_reports,
    update_monthly_report,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestServiceConstants:
    """Verify allowed values match DESIGN.md CHECK constraints."""

    def test_allowed_report_types(self):
        expected = {"sp_monthly", "zp_vszp", "zp_dovera", "zp_union", "tax_prehled"}
        assert expected == ALLOWED_REPORT_TYPES

    def test_allowed_statuses(self):
        expected = {"generated", "submitted", "accepted", "rejected"}
        assert expected == ALLOWED_STATUSES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session, **overrides) -> Tenant:
    """Insert a minimal Tenant and flush; return the instance."""
    defaults = {
        "name": "Test s.r.o.",
        "ico": "12345678",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "schema_name": "tenant_test_12345678",
    }
    defaults.update(overrides)
    tenant = Tenant(**defaults)
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _make_health_insurer(db_session, **overrides) -> HealthInsurer:
    """Insert a minimal HealthInsurer and flush; return the instance."""
    defaults = {
        "code": "25",
        "name": "Všeobecná zdravotná poisťovňa, a.s.",
        "iban": "SK8975000000000012345679",
    }
    defaults.update(overrides)
    hi = HealthInsurer(**defaults)
    db_session.add(hi)
    db_session.flush()
    return hi


def _make_report_payload(tenant_id, **overrides) -> MonthlyReportCreate:
    """Build a valid MonthlyReportCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "period_year": 2025,
        "period_month": 1,
        "report_type": "sp_monthly",
        "file_path": "/opt/nex-payroll-src/data/reports/2025/01/sp_monthly.xml",
        "file_format": "xml",
        "status": "generated",
        "deadline_date": date(2025, 2, 20),
        "institution": "Sociálna poisťovňa",
        "submitted_at": None,
        "health_insurer_id": None,
    }
    defaults.update(overrides)
    return MonthlyReportCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateMonthlyReport:
    """Tests for create_monthly_report."""

    def test_create_returns_model_instance(self, db_session):
        tenant = _make_tenant(db_session)
        payload = _make_report_payload(tenant.id)

        result = create_monthly_report(db_session, payload)

        assert isinstance(result, MonthlyReport)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.period_year == 2025
        assert result.period_month == 1
        assert result.report_type == "sp_monthly"
        assert result.file_path == "/opt/nex-payroll-src/data/reports/2025/01/sp_monthly.xml"
        assert result.file_format == "xml"
        assert result.status == "generated"
        assert result.deadline_date == date(2025, 2, 20)
        assert result.institution == "Sociálna poisťovňa"
        assert result.submitted_at is None
        assert result.health_insurer_id is None

    def test_create_different_report_types_same_period(self, db_session):
        """Different report types for the same period are allowed."""
        tenant = _make_tenant(db_session)
        hi = _make_health_insurer(db_session)

        rpt_a = create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, report_type="sp_monthly"),
        )
        rpt_b = create_monthly_report(
            db_session,
            _make_report_payload(
                tenant.id,
                report_type="zp_vszp",
                file_path="/opt/nex-payroll-src/data/reports/2025/01/zp_vszp.xml",
                institution="VšZP",
                health_insurer_id=hi.id,
            ),
        )

        assert rpt_a.id != rpt_b.id
        assert rpt_a.report_type == "sp_monthly"
        assert rpt_b.report_type == "zp_vszp"

    def test_create_same_type_different_months(self, db_session):
        """Same report type for different months is allowed."""
        tenant = _make_tenant(db_session)

        rpt_jan = create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_month=1),
        )
        rpt_feb = create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_month=2),
        )

        assert rpt_jan.id != rpt_feb.id
        assert rpt_jan.period_month == 1
        assert rpt_feb.period_month == 2

    def test_create_duplicate_raises_value_error(self, db_session):
        """Duplicate (tenant_id, period_year, period_month, report_type) must raise ValueError."""
        tenant = _make_tenant(db_session)
        payload = _make_report_payload(tenant.id)

        create_monthly_report(db_session, payload)

        with pytest.raises(ValueError, match="already exists"):
            create_monthly_report(db_session, payload)

    def test_create_invalid_report_type_raises_value_error(self, db_session):
        """Creating with an invalid report_type must raise ValueError at service level."""
        tenant = _make_tenant(db_session)
        # Use model_construct to bypass Pydantic Literal validation
        payload = MonthlyReportCreate.model_construct(
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            report_type="invalid_type",
            file_path="/data/report.xml",
            file_format="xml",
            status="generated",
            deadline_date=date(2025, 2, 20),
            institution="Test",
            submitted_at=None,
            health_insurer_id=None,
        )

        with pytest.raises(ValueError, match="Invalid report_type"):
            create_monthly_report(db_session, payload)

    def test_create_invalid_status_raises_value_error(self, db_session):
        """Creating with an invalid status must raise ValueError at service level."""
        tenant = _make_tenant(db_session)
        # Use model_construct to bypass Pydantic Literal validation
        payload = MonthlyReportCreate.model_construct(
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            report_type="sp_monthly",
            file_path="/data/report.xml",
            file_format="xml",
            status="invalid_status",
            deadline_date=date(2025, 2, 20),
            institution="Test",
            submitted_at=None,
            health_insurer_id=None,
        )

        with pytest.raises(ValueError, match="Invalid status"):
            create_monthly_report(db_session, payload)


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetMonthlyReport:
    """Tests for get_monthly_report."""

    def test_get_existing(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_monthly_report(db_session, _make_report_payload(tenant.id))

        fetched = get_monthly_report(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.report_type == created.report_type

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_monthly_report(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListMonthlyReports:
    """Tests for list_monthly_reports."""

    def test_list_empty(self, db_session):
        result = list_monthly_reports(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        tenant = _make_tenant(db_session)
        hi = _make_health_insurer(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, report_type="sp_monthly"),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(
                tenant.id,
                report_type="zp_vszp",
                file_path="/data/zp.xml",
                institution="VšZP",
                health_insurer_id=hi.id,
            ),
        )

        result = list_monthly_reports(db_session)
        assert len(result) == 2

    def test_list_ordering_by_period_desc(self, db_session):
        """Reports are ordered by year desc, month desc."""
        tenant = _make_tenant(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_year=2024, period_month=12),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_year=2025, period_month=3),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_year=2025, period_month=1),
        )

        result = list_monthly_reports(db_session)
        assert result[0].period_year == 2025
        assert result[0].period_month == 3
        assert result[1].period_year == 2025
        assert result[1].period_month == 1
        assert result[2].period_year == 2024
        assert result[2].period_month == 12

    def test_list_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")

        create_monthly_report(db_session, _make_report_payload(tenant_a.id))
        create_monthly_report(db_session, _make_report_payload(tenant_b.id))

        result = list_monthly_reports(db_session, tenant_id=tenant_a.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id

    def test_list_scoped_by_report_type(self, db_session):
        tenant = _make_tenant(db_session)
        hi = _make_health_insurer(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, report_type="sp_monthly"),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(
                tenant.id,
                report_type="zp_vszp",
                file_path="/data/zp.xml",
                institution="VšZP",
                health_insurer_id=hi.id,
            ),
        )

        result = list_monthly_reports(db_session, report_type="sp_monthly")
        assert len(result) == 1
        assert result[0].report_type == "sp_monthly"

    def test_list_scoped_by_status(self, db_session):
        tenant = _make_tenant(db_session)
        hi = _make_health_insurer(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, status="generated"),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(
                tenant.id,
                report_type="zp_vszp",
                file_path="/data/zp.xml",
                institution="VšZP",
                status="submitted",
                health_insurer_id=hi.id,
            ),
        )

        result = list_monthly_reports(db_session, status="generated")
        assert len(result) == 1
        assert result[0].status == "generated"

    def test_list_scoped_by_period_year(self, db_session):
        tenant = _make_tenant(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_year=2024),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_year=2025),
        )

        result = list_monthly_reports(db_session, period_year=2024)
        assert len(result) == 1
        assert result[0].period_year == 2024

    def test_list_scoped_by_period_month(self, db_session):
        tenant = _make_tenant(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_month=1),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_month=6),
        )

        result = list_monthly_reports(db_session, period_month=1)
        assert len(result) == 1
        assert result[0].period_month == 1

    def test_list_pagination_skip(self, db_session):
        tenant = _make_tenant(db_session)

        for m in range(1, 4):
            create_monthly_report(
                db_session,
                _make_report_payload(tenant.id, period_month=m),
            )

        result = list_monthly_reports(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        tenant = _make_tenant(db_session)

        for m in range(1, 4):
            create_monthly_report(
                db_session,
                _make_report_payload(tenant.id, period_month=m),
            )

        result = list_monthly_reports(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        tenant = _make_tenant(db_session)

        for m in range(1, 7):
            create_monthly_report(
                db_session,
                _make_report_payload(tenant.id, period_month=m),
            )

        result = list_monthly_reports(db_session, skip=1, limit=2)
        assert len(result) == 2

    def test_list_default_limit_is_50(self, db_session):
        """Default limit should be 50 per project convention."""
        import inspect

        sig = inspect.signature(list_monthly_reports)
        assert sig.parameters["limit"].default == 50

    def test_list_invalid_report_type_raises_value_error(self, db_session):
        """Filtering by an invalid report_type must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid report_type"):
            list_monthly_reports(db_session, report_type="bad_type")

    def test_list_invalid_status_raises_value_error(self, db_session):
        """Filtering by an invalid status must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            list_monthly_reports(db_session, status="bad_status")


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountMonthlyReports:
    """Tests for count_monthly_reports."""

    def test_count_empty(self, db_session):
        result = count_monthly_reports(db_session)
        assert result == 0

    def test_count_all(self, db_session):
        tenant = _make_tenant(db_session)
        for m in range(1, 4):
            create_monthly_report(
                db_session,
                _make_report_payload(tenant.id, period_month=m),
            )

        result = count_monthly_reports(db_session)
        assert result == 3

    def test_count_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")

        create_monthly_report(db_session, _make_report_payload(tenant_a.id))
        create_monthly_report(db_session, _make_report_payload(tenant_b.id))

        assert count_monthly_reports(db_session, tenant_id=tenant_a.id) == 1
        assert count_monthly_reports(db_session, tenant_id=tenant_b.id) == 1

    def test_count_scoped_by_report_type(self, db_session):
        tenant = _make_tenant(db_session)
        hi = _make_health_insurer(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, report_type="sp_monthly"),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(
                tenant.id,
                report_type="zp_vszp",
                file_path="/data/zp.xml",
                institution="VšZP",
                health_insurer_id=hi.id,
            ),
        )

        assert count_monthly_reports(db_session, report_type="sp_monthly") == 1
        assert count_monthly_reports(db_session, report_type="zp_vszp") == 1

    def test_count_scoped_by_status(self, db_session):
        tenant = _make_tenant(db_session)
        hi = _make_health_insurer(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, status="generated"),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(
                tenant.id,
                report_type="zp_vszp",
                file_path="/data/zp.xml",
                institution="VšZP",
                status="submitted",
                health_insurer_id=hi.id,
            ),
        )

        assert count_monthly_reports(db_session, status="generated") == 1
        assert count_monthly_reports(db_session, status="submitted") == 1

    def test_count_scoped_by_period_year(self, db_session):
        tenant = _make_tenant(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_year=2024),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_year=2025),
        )

        assert count_monthly_reports(db_session, period_year=2024) == 1
        assert count_monthly_reports(db_session, period_year=2025) == 1

    def test_count_scoped_by_period_month(self, db_session):
        tenant = _make_tenant(db_session)

        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_month=1),
        )
        create_monthly_report(
            db_session,
            _make_report_payload(tenant.id, period_month=6),
        )

        assert count_monthly_reports(db_session, period_month=1) == 1
        assert count_monthly_reports(db_session, period_month=6) == 1

    def test_count_invalid_report_type_raises_value_error(self, db_session):
        """Counting with an invalid report_type must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid report_type"):
            count_monthly_reports(db_session, report_type="bad_type")

    def test_count_invalid_status_raises_value_error(self, db_session):
        """Counting with an invalid status must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            count_monthly_reports(db_session, status="bad_status")


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateMonthlyReport:
    """Tests for update_monthly_report."""

    def test_update_single_field(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_monthly_report(db_session, _make_report_payload(tenant.id))

        updated = update_monthly_report(
            db_session,
            created.id,
            MonthlyReportUpdate(status="submitted"),
        )

        assert updated is not None
        assert updated.status == "submitted"
        # unchanged fields stay the same
        assert updated.report_type == "sp_monthly"
        assert updated.institution == "Sociálna poisťovňa"

    def test_update_multiple_fields(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_monthly_report(db_session, _make_report_payload(tenant.id))

        updated = update_monthly_report(
            db_session,
            created.id,
            MonthlyReportUpdate(
                status="submitted",
                file_path="/new/path/report.xml",
            ),
        )

        assert updated is not None
        assert updated.status == "submitted"
        assert updated.file_path == "/new/path/report.xml"

    def test_update_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            update_monthly_report(
                db_session,
                uuid4(),
                MonthlyReportUpdate(status="submitted"),
            )

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        tenant = _make_tenant(db_session)
        created = create_monthly_report(db_session, _make_report_payload(tenant.id))

        updated = update_monthly_report(
            db_session,
            created.id,
            MonthlyReportUpdate(),
        )

        assert updated is not None
        assert updated.status == created.status
        assert updated.file_path == created.file_path

    def test_update_institution(self, db_session):
        """Update institution field."""
        tenant = _make_tenant(db_session)
        created = create_monthly_report(db_session, _make_report_payload(tenant.id))

        updated = update_monthly_report(
            db_session,
            created.id,
            MonthlyReportUpdate(institution="Dôvera ZP"),
        )

        assert updated is not None
        assert updated.institution == "Dôvera ZP"

    def test_update_invalid_status_raises_value_error(self, db_session):
        """Updating with an invalid status must raise ValueError at service level."""
        tenant = _make_tenant(db_session)
        created = create_monthly_report(db_session, _make_report_payload(tenant.id))

        # Use model_construct to bypass Pydantic Literal validation
        payload = MonthlyReportUpdate.model_construct(status="invalid_status")

        with pytest.raises(ValueError, match="Invalid status"):
            update_monthly_report(db_session, created.id, payload)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteMonthlyReport:
    """Tests for delete_monthly_report."""

    def test_delete_existing(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_monthly_report(db_session, _make_report_payload(tenant.id))

        result = delete_monthly_report(db_session, created.id)

        assert result is None
        assert get_monthly_report(db_session, created.id) is None

    def test_delete_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            delete_monthly_report(db_session, uuid4())
