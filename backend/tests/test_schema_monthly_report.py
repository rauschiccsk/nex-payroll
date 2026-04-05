"""Tests for MonthlyReport Pydantic schemas (Create, Update, Read)."""

from datetime import date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.monthly_report import (
    MonthlyReportCreate,
    MonthlyReportRead,
    MonthlyReportUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_HEALTH_INSURER_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for MonthlyReportCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "period_year": 2025,
        "period_month": 1,
        "report_type": "sp_monthly",
        "file_path": "/opt/nex-payroll-src/data/reports/2025/01/sp_monthly.xml",
        "deadline_date": date(2025, 2, 20),
        "institution": "Sociálna poisťovňa",
    }


def _read_kwargs() -> dict:
    """Return a complete dict for constructing MonthlyReportRead."""
    now = datetime(2025, 6, 1, 12, 0, 0)
    return {
        "id": uuid4(),
        "tenant_id": _TENANT_ID,
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
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# MonthlyReportCreate
# ---------------------------------------------------------------------------


class TestMonthlyReportCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        """Valid creation with only required fields — defaults applied."""
        schema = MonthlyReportCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.period_year == 2025
        assert schema.period_month == 1
        assert schema.report_type == "sp_monthly"
        assert schema.file_path == "/opt/nex-payroll-src/data/reports/2025/01/sp_monthly.xml"
        assert schema.deadline_date == date(2025, 2, 20)
        assert schema.institution == "Sociálna poisťovňa"
        # defaults
        assert schema.file_format == "xml"
        assert schema.status == "generated"
        assert schema.submitted_at is None
        assert schema.health_insurer_id is None

    def test_valid_full(self):
        """Valid creation with all fields explicitly set."""
        schema = MonthlyReportCreate(
            **_valid_create_kwargs(),
            file_format="pdf",
            status="submitted",
            submitted_at=datetime(2025, 2, 15, 10, 0, 0),
            health_insurer_id=_HEALTH_INSURER_ID,
        )
        assert schema.file_format == "pdf"
        assert schema.status == "submitted"
        assert schema.submitted_at == datetime(2025, 2, 15, 10, 0, 0)
        assert schema.health_insurer_id == _HEALTH_INSURER_ID

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_period_year(self):
        kw = _valid_create_kwargs()
        del kw["period_year"]
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_missing_required_period_month(self):
        kw = _valid_create_kwargs()
        del kw["period_month"]
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_missing_required_report_type(self):
        kw = _valid_create_kwargs()
        del kw["report_type"]
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "report_type" in str(exc_info.value)

    def test_missing_required_file_path(self):
        kw = _valid_create_kwargs()
        del kw["file_path"]
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "file_path" in str(exc_info.value)

    def test_missing_required_deadline_date(self):
        kw = _valid_create_kwargs()
        del kw["deadline_date"]
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "deadline_date" in str(exc_info.value)

    def test_missing_required_institution(self):
        kw = _valid_create_kwargs()
        del kw["institution"]
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "institution" in str(exc_info.value)

    # -- report_type validation --

    def test_invalid_report_type_rejected(self):
        """Invalid report_type value must be rejected."""
        kw = _valid_create_kwargs()
        kw["report_type"] = "invalid_type"
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "report_type" in str(exc_info.value)

    def test_all_valid_report_types(self):
        """All 5 report types defined in DESIGN.md must be accepted."""
        valid_types = [
            "sp_monthly",
            "zp_vszp",
            "zp_dovera",
            "zp_union",
            "tax_prehled",
        ]
        for rtype in valid_types:
            kw = _valid_create_kwargs()
            kw["report_type"] = rtype
            schema = MonthlyReportCreate(**kw)
            assert schema.report_type == rtype

    # -- status validation --

    def test_invalid_status_rejected(self):
        """Invalid status value must be rejected."""
        kw = _valid_create_kwargs()
        kw["status"] = "invalid_status"
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "status" in str(exc_info.value)

    def test_all_valid_statuses(self):
        """All 4 status values from DESIGN.md must be accepted."""
        valid_statuses = ["generated", "submitted", "accepted", "rejected"]
        for status in valid_statuses:
            kw = _valid_create_kwargs()
            kw["status"] = status
            schema = MonthlyReportCreate(**kw)
            assert schema.status == status

    # -- file_format validation (Literal["xml", "pdf"]) --

    def test_invalid_file_format_rejected(self):
        """Invalid file_format value must be rejected."""
        kw = _valid_create_kwargs()
        kw["file_format"] = "csv"
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "file_format" in str(exc_info.value)

    def test_all_valid_file_formats(self):
        """Both valid file formats must be accepted."""
        for fmt in ("xml", "pdf"):
            kw = _valid_create_kwargs()
            kw["file_format"] = fmt
            schema = MonthlyReportCreate(**kw)
            assert schema.file_format == fmt

    # -- period_month boundary validation (ge=1, le=12) --

    def test_period_month_zero_rejected(self):
        """period_month=0 must be rejected (ge=1)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 0
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_period_month_13_rejected(self):
        """period_month=13 must be rejected (le=12)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 13
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_period_month_boundary_min(self):
        """period_month=1 must be accepted (ge=1)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 1
        schema = MonthlyReportCreate(**kw)
        assert schema.period_month == 1

    def test_period_month_boundary_max(self):
        """period_month=12 must be accepted (le=12)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 12
        schema = MonthlyReportCreate(**kw)
        assert schema.period_month == 12

    # -- period_year boundary validation (ge=2000, le=2100) --

    def test_period_year_below_range_rejected(self):
        kw = _valid_create_kwargs()
        kw["period_year"] = 1999
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_period_year_above_range_rejected(self):
        kw = _valid_create_kwargs()
        kw["period_year"] = 2101
        with pytest.raises(ValidationError) as exc_info:
            MonthlyReportCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_period_year_at_lower_bound_accepted(self):
        kw = _valid_create_kwargs()
        kw["period_year"] = 2000
        schema = MonthlyReportCreate(**kw)
        assert schema.period_year == 2000

    def test_period_year_at_upper_bound_accepted(self):
        kw = _valid_create_kwargs()
        kw["period_year"] = 2100
        schema = MonthlyReportCreate(**kw)
        assert schema.period_year == 2100

    # -- max_length constraints --

    def test_file_path_max_length(self):
        kw = _valid_create_kwargs()
        kw["file_path"] = "x" * 501
        with pytest.raises(ValidationError):
            MonthlyReportCreate(**kw)

    def test_institution_max_length(self):
        kw = _valid_create_kwargs()
        kw["institution"] = "x" * 101
        with pytest.raises(ValidationError):
            MonthlyReportCreate(**kw)


# ---------------------------------------------------------------------------
# MonthlyReportUpdate
# ---------------------------------------------------------------------------


class TestMonthlyReportUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        """All fields default to None when no data supplied."""
        schema = MonthlyReportUpdate()
        assert schema.file_path is None
        assert schema.file_format is None
        assert schema.status is None
        assert schema.deadline_date is None
        assert schema.institution is None
        assert schema.submitted_at is None
        assert schema.health_insurer_id is None

    def test_partial_update_status(self):
        """Only supplied fields are set; the rest remain None."""
        schema = MonthlyReportUpdate(status="submitted")
        assert schema.status == "submitted"
        assert schema.file_path is None
        assert schema.file_format is None

    def test_partial_update_file_path(self):
        schema = MonthlyReportUpdate(file_path="/new/path/report.xml")
        assert schema.file_path == "/new/path/report.xml"
        assert schema.status is None

    def test_partial_update_file_format(self):
        schema = MonthlyReportUpdate(file_format="pdf")
        assert schema.file_format == "pdf"
        assert schema.status is None

    def test_full_update(self):
        """All fields explicitly set."""
        schema = MonthlyReportUpdate(
            file_path="/new/path.xml",
            file_format="pdf",
            status="accepted",
            deadline_date=date(2025, 3, 20),
            institution="VšZP",
            submitted_at=datetime(2025, 3, 1, 10, 0, 0),
            health_insurer_id=_HEALTH_INSURER_ID,
        )
        assert schema.file_path == "/new/path.xml"
        assert schema.file_format == "pdf"
        assert schema.status == "accepted"
        assert schema.deadline_date == date(2025, 3, 20)
        assert schema.institution == "VšZP"
        assert schema.submitted_at == datetime(2025, 3, 1, 10, 0, 0)
        assert schema.health_insurer_id == _HEALTH_INSURER_ID

    # -- validation in update --

    def test_invalid_status_in_update(self):
        with pytest.raises(ValidationError):
            MonthlyReportUpdate(status="invalid_status")

    def test_invalid_file_format_in_update(self):
        """Invalid file_format must be rejected in Update schema too."""
        with pytest.raises(ValidationError):
            MonthlyReportUpdate(file_format="csv")

    def test_institution_max_length_in_update(self):
        with pytest.raises(ValidationError):
            MonthlyReportUpdate(institution="x" * 101)

    def test_file_path_max_length_in_update(self):
        with pytest.raises(ValidationError):
            MonthlyReportUpdate(file_path="x" * 501)

    # -- Update excludes immutable / identity fields --

    def test_update_excludes_tenant_id(self):
        """tenant_id is not updatable — field should not exist on Update schema."""
        assert "tenant_id" not in MonthlyReportUpdate.model_fields

    def test_update_excludes_period_year(self):
        """period_year is part of unique key — not updatable."""
        assert "period_year" not in MonthlyReportUpdate.model_fields

    def test_update_excludes_period_month(self):
        """period_month is part of unique key — not updatable."""
        assert "period_month" not in MonthlyReportUpdate.model_fields

    def test_update_excludes_report_type(self):
        """report_type is part of unique key — not updatable."""
        assert "report_type" not in MonthlyReportUpdate.model_fields


# ---------------------------------------------------------------------------
# MonthlyReportRead
# ---------------------------------------------------------------------------


class TestMonthlyReportRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        """Construct Read schema from a plain dict."""
        kw = _read_kwargs()
        schema = MonthlyReportRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.period_year == 2025
        assert schema.period_month == 1
        assert schema.report_type == "sp_monthly"
        assert schema.file_path == "/opt/nex-payroll-src/data/reports/2025/01/sp_monthly.xml"
        assert schema.file_format == "xml"
        assert schema.status == "generated"
        assert schema.deadline_date == date(2025, 2, 20)
        assert schema.institution == "Sociálna poisťovňa"
        assert schema.submitted_at is None
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
                self.report_type = "zp_vszp"
                self.file_path = "/data/reports/2025/03/zp_vszp.xml"
                self.file_format = "xml"
                self.status = "submitted"
                self.deadline_date = date(2025, 4, 3)
                self.institution = "VšZP"
                self.submitted_at = datetime(2025, 4, 1, 10, 0, 0)
                self.health_insurer_id = _HEALTH_INSURER_ID
                self.created_at = datetime(2025, 1, 1, 0, 0, 0)
                self.updated_at = datetime(2025, 1, 1, 0, 0, 0)

        orm_obj = FakeORM()
        schema = MonthlyReportRead.model_validate(orm_obj)
        assert schema.report_type == "zp_vszp"
        assert schema.institution == "VšZP"
        assert schema.submitted_at == datetime(2025, 4, 1, 10, 0, 0)
        assert schema.health_insurer_id == _HEALTH_INSURER_ID

    def test_serialisation_roundtrip(self):
        """model_dump() produces a dict that can reconstruct the schema."""
        kw = _read_kwargs()
        schema = MonthlyReportRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["period_year"] == 2025
        assert dumped["period_month"] == 1
        assert dumped["report_type"] == "sp_monthly"
        assert dumped["file_format"] == "xml"
        assert dumped["status"] == "generated"

    def test_read_all_fields_present(self):
        """Read schema exposes every field from the model."""
        expected_fields = {
            "id",
            "tenant_id",
            "period_year",
            "period_month",
            "report_type",
            "file_path",
            "file_format",
            "status",
            "deadline_date",
            "institution",
            "submitted_at",
            "health_insurer_id",
            "created_at",
            "updated_at",
        }
        assert set(MonthlyReportRead.model_fields.keys()) == expected_fields
