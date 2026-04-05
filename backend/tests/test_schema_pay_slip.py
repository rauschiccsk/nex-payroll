"""Tests for PaySlip Pydantic schemas (Create, Update, Read)."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.pay_slip import (
    PaySlipCreate,
    PaySlipRead,
    PaySlipUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_PAYROLL_ID = uuid4()
_EMPLOYEE_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for PaySlipCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "payroll_id": _PAYROLL_ID,
        "employee_id": _EMPLOYEE_ID,
        "period_year": 2025,
        "period_month": 6,
        "pdf_path": "/opt/nex-payroll-src/data/payslips/tenant1/2025/06/EMP001.pdf",
    }


def _read_kwargs() -> dict:
    """Return a complete dict for constructing PaySlipRead."""
    now = datetime(2025, 6, 1, 12, 0, 0)
    kw = _valid_create_kwargs()
    kw.update(
        {
            "id": uuid4(),
            "file_size_bytes": 52480,
            "generated_at": now,
            "downloaded_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    return kw


# ---------------------------------------------------------------------------
# PaySlipCreate
# ---------------------------------------------------------------------------


class TestPaySlipCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        """Valid creation with only required fields — defaults applied."""
        schema = PaySlipCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.payroll_id == _PAYROLL_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.period_year == 2025
        assert schema.period_month == 6
        assert schema.pdf_path.endswith("EMP001.pdf")
        assert schema.file_size_bytes is None

    def test_valid_full(self):
        """Valid creation with all fields explicitly set."""
        schema = PaySlipCreate(
            **_valid_create_kwargs(),
            file_size_bytes=102400,
        )
        assert schema.file_size_bytes == 102400

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_payroll_id(self):
        kw = _valid_create_kwargs()
        del kw["payroll_id"]
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "payroll_id" in str(exc_info.value)

    def test_missing_required_employee_id(self):
        kw = _valid_create_kwargs()
        del kw["employee_id"]
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "employee_id" in str(exc_info.value)

    def test_missing_required_period_year(self):
        kw = _valid_create_kwargs()
        del kw["period_year"]
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_missing_required_period_month(self):
        kw = _valid_create_kwargs()
        del kw["period_month"]
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_missing_required_pdf_path(self):
        kw = _valid_create_kwargs()
        del kw["pdf_path"]
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "pdf_path" in str(exc_info.value)

    # -- period_year boundary validation (ge=2000, le=2100) --

    def test_period_year_below_min_rejected(self):
        """period_year=1999 must be rejected (ge=2000)."""
        kw = _valid_create_kwargs()
        kw["period_year"] = 1999
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_period_year_above_max_rejected(self):
        """period_year=2101 must be rejected (le=2100)."""
        kw = _valid_create_kwargs()
        kw["period_year"] = 2101
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_period_year_boundary_min(self):
        """period_year=2000 must be accepted (ge=2000)."""
        kw = _valid_create_kwargs()
        kw["period_year"] = 2000
        schema = PaySlipCreate(**kw)
        assert schema.period_year == 2000

    def test_period_year_boundary_max(self):
        """period_year=2100 must be accepted (le=2100)."""
        kw = _valid_create_kwargs()
        kw["period_year"] = 2100
        schema = PaySlipCreate(**kw)
        assert schema.period_year == 2100

    # -- period_month boundary validation (ge=1, le=12) --

    def test_period_month_zero_rejected(self):
        """period_month=0 must be rejected (ge=1)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 0
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_period_month_13_rejected(self):
        """period_month=13 must be rejected (le=12)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 13
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_period_month_boundary_min(self):
        """period_month=1 must be accepted (ge=1)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 1
        schema = PaySlipCreate(**kw)
        assert schema.period_month == 1

    def test_period_month_boundary_max(self):
        """period_month=12 must be accepted (le=12)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 12
        schema = PaySlipCreate(**kw)
        assert schema.period_month == 12

    # -- pdf_path validation --

    def test_pdf_path_max_length_rejected(self):
        """pdf_path exceeding 500 chars must be rejected."""
        kw = _valid_create_kwargs()
        kw["pdf_path"] = "/opt/" + "a" * 500
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "pdf_path" in str(exc_info.value)

    def test_pdf_path_at_max_length_accepted(self):
        """pdf_path exactly 500 chars must be accepted."""
        kw = _valid_create_kwargs()
        kw["pdf_path"] = "a" * 500
        schema = PaySlipCreate(**kw)
        assert len(schema.pdf_path) == 500

    # -- file_size_bytes validation --

    def test_file_size_bytes_negative_rejected(self):
        """file_size_bytes < 0 must be rejected (ge=0)."""
        kw = _valid_create_kwargs()
        kw["file_size_bytes"] = -1
        with pytest.raises(ValidationError) as exc_info:
            PaySlipCreate(**kw)
        assert "file_size_bytes" in str(exc_info.value)

    def test_file_size_bytes_zero_accepted(self):
        """file_size_bytes=0 must be accepted (ge=0)."""
        kw = _valid_create_kwargs()
        kw["file_size_bytes"] = 0
        schema = PaySlipCreate(**kw)
        assert schema.file_size_bytes == 0

    def test_file_size_bytes_none_accepted(self):
        """file_size_bytes=None must be accepted (nullable)."""
        kw = _valid_create_kwargs()
        kw["file_size_bytes"] = None
        schema = PaySlipCreate(**kw)
        assert schema.file_size_bytes is None


# ---------------------------------------------------------------------------
# PaySlipUpdate
# ---------------------------------------------------------------------------


class TestPaySlipUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        """All fields default to None when no data supplied."""
        schema = PaySlipUpdate()
        assert schema.payroll_id is None
        assert schema.employee_id is None
        assert schema.period_year is None
        assert schema.period_month is None
        assert schema.pdf_path is None
        assert schema.file_size_bytes is None
        assert schema.downloaded_at is None

    def test_partial_update(self):
        """Only supplied fields are set; the rest remain None."""
        schema = PaySlipUpdate(
            pdf_path="/opt/nex-payroll-src/data/payslips/t1/2025/07/EMP002.pdf",
            file_size_bytes=65536,
        )
        assert schema.pdf_path.endswith("EMP002.pdf")
        assert schema.file_size_bytes == 65536
        # everything else remains None
        assert schema.payroll_id is None
        assert schema.employee_id is None
        assert schema.period_year is None
        assert schema.period_month is None
        assert schema.downloaded_at is None

    def test_update_downloaded_at(self):
        """downloaded_at can be set for marking employee download."""
        ts = datetime(2025, 7, 1, 9, 30, 0)
        schema = PaySlipUpdate(downloaded_at=ts)
        assert schema.downloaded_at == ts

    def test_update_payroll_id(self):
        """payroll_id can be updated."""
        new_id = uuid4()
        schema = PaySlipUpdate(payroll_id=new_id)
        assert schema.payroll_id == new_id

    def test_update_employee_id(self):
        """employee_id can be updated."""
        new_id = uuid4()
        schema = PaySlipUpdate(employee_id=new_id)
        assert schema.employee_id == new_id

    def test_update_period_year(self):
        """period_year can be updated."""
        schema = PaySlipUpdate(period_year=2026)
        assert schema.period_year == 2026

    def test_update_period_month(self):
        """period_month can be updated."""
        schema = PaySlipUpdate(period_month=12)
        assert schema.period_month == 12

    # -- period_year boundary validation in update --

    def test_update_period_year_below_min_rejected(self):
        """period_year=1999 in update must be rejected (ge=2000)."""
        with pytest.raises(ValidationError) as exc_info:
            PaySlipUpdate(period_year=1999)
        assert "period_year" in str(exc_info.value)

    def test_update_period_year_above_max_rejected(self):
        """period_year=2101 in update must be rejected (le=2100)."""
        with pytest.raises(ValidationError) as exc_info:
            PaySlipUpdate(period_year=2101)
        assert "period_year" in str(exc_info.value)

    # -- period_month boundary validation in update --

    def test_update_period_month_zero_rejected(self):
        """period_month=0 in update must be rejected (ge=1)."""
        with pytest.raises(ValidationError) as exc_info:
            PaySlipUpdate(period_month=0)
        assert "period_month" in str(exc_info.value)

    def test_update_period_month_13_rejected(self):
        """period_month=13 in update must be rejected (le=12)."""
        with pytest.raises(ValidationError) as exc_info:
            PaySlipUpdate(period_month=13)
        assert "period_month" in str(exc_info.value)

    # -- pdf_path validation in update --

    def test_update_pdf_path_max_length_rejected(self):
        """pdf_path exceeding 500 chars in update must be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PaySlipUpdate(pdf_path="/opt/" + "a" * 500)
        assert "pdf_path" in str(exc_info.value)

    # -- file_size_bytes validation in update --

    def test_update_file_size_bytes_negative_rejected(self):
        """file_size_bytes < 0 in update must be rejected (ge=0)."""
        with pytest.raises(ValidationError) as exc_info:
            PaySlipUpdate(file_size_bytes=-1)
        assert "file_size_bytes" in str(exc_info.value)

    # -- tenant_id NOT in update schema --

    def test_tenant_id_not_in_update(self):
        """tenant_id must NOT be present in update schema (immutable FK)."""
        assert "tenant_id" not in PaySlipUpdate.model_fields


# ---------------------------------------------------------------------------
# PaySlipRead
# ---------------------------------------------------------------------------


class TestPaySlipRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        """Construct Read schema from a plain dict."""
        kw = _read_kwargs()
        schema = PaySlipRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.payroll_id == _PAYROLL_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.period_year == 2025
        assert schema.period_month == 6
        assert schema.pdf_path.endswith("EMP001.pdf")
        assert schema.file_size_bytes == 52480
        assert schema.generated_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.downloaded_at is None
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                kw = _read_kwargs()
                for key, value in kw.items():
                    setattr(self, key, value)

        orm_obj = FakeORM()
        schema = PaySlipRead.model_validate(orm_obj)
        assert schema.tenant_id == _TENANT_ID
        assert schema.payroll_id == _PAYROLL_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.period_year == 2025
        assert schema.period_month == 6
        assert schema.file_size_bytes == 52480

    def test_serialisation_roundtrip(self):
        """model_dump() produces a dict that can reconstruct the schema."""
        kw = _read_kwargs()
        schema = PaySlipRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["tenant_id"] == _TENANT_ID
        assert dumped["payroll_id"] == _PAYROLL_ID
        assert dumped["employee_id"] == _EMPLOYEE_ID
        assert dumped["period_year"] == 2025
        assert dumped["period_month"] == 6
        assert dumped["pdf_path"].endswith("EMP001.pdf")
        assert dumped["file_size_bytes"] == 52480
        assert dumped["generated_at"] == datetime(2025, 6, 1, 12, 0, 0)
        assert dumped["downloaded_at"] is None

    def test_read_all_fields_present(self):
        """Read schema exposes every field from the model."""
        expected_fields = {
            "id",
            "tenant_id",
            "payroll_id",
            "employee_id",
            "period_year",
            "period_month",
            "pdf_path",
            "file_size_bytes",
            "generated_at",
            "downloaded_at",
            "created_at",
            "updated_at",
        }
        assert set(PaySlipRead.model_fields.keys()) == expected_fields

    def test_read_downloaded_at_nullable(self):
        """downloaded_at can be None in Read schema."""
        kw = _read_kwargs()
        kw["downloaded_at"] = None
        schema = PaySlipRead(**kw)
        assert schema.downloaded_at is None

    def test_read_downloaded_at_with_value(self):
        """downloaded_at can hold a datetime value in Read schema."""
        kw = _read_kwargs()
        dl_ts = datetime(2025, 7, 15, 14, 0, 0)
        kw["downloaded_at"] = dl_ts
        schema = PaySlipRead(**kw)
        assert schema.downloaded_at == dl_ts

    def test_read_file_size_bytes_nullable(self):
        """file_size_bytes can be None in Read schema."""
        kw = _read_kwargs()
        kw["file_size_bytes"] = None
        schema = PaySlipRead(**kw)
        assert schema.file_size_bytes is None
