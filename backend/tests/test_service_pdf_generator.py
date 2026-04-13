"""Tests for pay slip PDF generator and PDF-related pay slip service functions.

Tests cover:
- PaySlipData construction
- PDF byte generation (valid PDF output)
- PDF path computation
- File writing to disk
- Integration with pay_slip service (generate single, batch, download bytes)
- Router endpoints for PDF download and batch generation
"""

import os
import tempfile
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.pay_slip import PaySlip
from app.models.payroll import Payroll
from app.models.tenant import Tenant
from app.services.pdf_generator import (
    PDF_BASE_PATH,
    PaySlipData,
    build_pay_slip_data_from_models,
    build_pay_slip_pdf,
    get_pdf_path,
    write_pdf_to_disk,
)

# ---------------------------------------------------------------------------
# Helpers — reuse pattern from test_service_pay_slip.py
# ---------------------------------------------------------------------------

_counter = 0


def _make_tenant(db_session, **overrides) -> Tenant:
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
    defaults = {
        "code": "25",
        "name": "VšZP",
        "iban": "SK0000000000000000000025",
    }
    defaults.update(overrides)
    hi = HealthInsurer(**defaults)
    db_session.add(hi)
    db_session.flush()
    return hi


def _make_employee(db_session, tenant, health_insurer, **overrides) -> Employee:
    defaults = {
        "tenant_id": tenant.id,
        "employee_number": "EMP-001",
        "first_name": "Ján",
        "last_name": "Novák",
        "birth_date": date(1990, 1, 1),
        "birth_number": "9001011234",
        "gender": "M",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "bank_iban": "SK3100000000000000000088",
        "health_insurer_id": health_insurer.id,
        "tax_declaration_type": "standard",
        "hire_date": date(2023, 1, 1),
    }
    defaults.update(overrides)
    emp = Employee(**defaults)
    db_session.add(emp)
    db_session.flush()
    return emp


def _make_contract(db_session, tenant, employee, **overrides) -> Contract:
    defaults = {
        "tenant_id": tenant.id,
        "employee_id": employee.id,
        "contract_number": "ZML-001",
        "contract_type": "permanent",
        "job_title": "Developer",
        "wage_type": "monthly",
        "base_wage": Decimal("2500.00"),
        "start_date": date(2023, 1, 1),
    }
    defaults.update(overrides)
    c = Contract(**defaults)
    db_session.add(c)
    db_session.flush()
    return c


def _make_payroll(db_session, tenant, employee, contract, **overrides) -> Payroll:
    defaults = {
        "tenant_id": tenant.id,
        "employee_id": employee.id,
        "contract_id": contract.id,
        "period_year": 2025,
        "period_month": 1,
        "status": "approved",
        "base_wage": Decimal("2500.00"),
        "overtime_hours": Decimal("0"),
        "overtime_amount": Decimal("0"),
        "bonus_amount": Decimal("0"),
        "supplement_amount": Decimal("0"),
        "gross_wage": Decimal("2500.00"),
        "sp_assessment_base": Decimal("2500.00"),
        "sp_nemocenske": Decimal("35.00"),
        "sp_starobne": Decimal("100.00"),
        "sp_invalidne": Decimal("75.00"),
        "sp_nezamestnanost": Decimal("25.00"),
        "sp_employee_total": Decimal("235.00"),
        "zp_assessment_base": Decimal("2500.00"),
        "zp_employee": Decimal("100.00"),
        "partial_tax_base": Decimal("2165.00"),
        "nczd_applied": Decimal("410.24"),
        "tax_base": Decimal("1754.76"),
        "tax_advance": Decimal("333.40"),
        "child_bonus": Decimal("0"),
        "tax_after_bonus": Decimal("333.40"),
        "net_wage": Decimal("1831.60"),
        "sp_employer_nemocenske": Decimal("35.00"),
        "sp_employer_starobne": Decimal("350.00"),
        "sp_employer_invalidne": Decimal("75.00"),
        "sp_employer_nezamestnanost": Decimal("25.00"),
        "sp_employer_garancne": Decimal("6.25"),
        "sp_employer_rezervny": Decimal("118.75"),
        "sp_employer_kurzarbeit": Decimal("12.50"),
        "sp_employer_urazove": Decimal("20.00"),
        "sp_employer_total": Decimal("642.50"),
        "zp_employer": Decimal("250.00"),
        "total_employer_cost": Decimal("3392.50"),
        "pillar2_amount": Decimal("0"),
    }
    defaults.update(overrides)
    p = Payroll(**defaults)
    db_session.add(p)
    db_session.flush()
    return p


def _setup_parent_chain(db_session, **overrides):
    """Create full FK parent chain with approved payroll."""
    global _counter  # noqa: PLW0603
    _counter += 1
    idx = str(_counter)

    tenant = _make_tenant(
        db_session,
        ico=f"P{idx:0>7}"[:8],
        schema_name=f"tenant_pdf_{idx}",
        **{k: v for k, v in overrides.items() if k.startswith("tenant_")},
    )
    hi = _make_health_insurer(
        db_session,
        code=f"P{idx}"[:4],
        iban=f"SK00000000000000000P{idx}"[:24],
    )
    employee = _make_employee(
        db_session,
        tenant,
        hi,
        employee_number=f"EMP-PDF-{idx}",
    )
    contract = _make_contract(
        db_session,
        tenant,
        employee,
        contract_number=f"ZML-PDF-{idx}",
    )
    payroll = _make_payroll(db_session, tenant, employee, contract)
    return {
        "tenant": tenant,
        "health_insurer": hi,
        "employee": employee,
        "contract": contract,
        "payroll": payroll,
    }


def _make_pay_slip_data(**overrides) -> PaySlipData:
    """Create a minimal PaySlipData for testing."""
    defaults = {
        "company_name": "Test s.r.o.",
        "company_ico": "12345678",
        "company_dic": "2024567890",
        "company_address": "Hlavná 1, 81101 Bratislava",
        "employee_name": "Ján Novák",
        "employee_number": "EMP-001",
        "employee_birth_date": "01.01.1990",
        "employee_address": "Hlavná 1, 81101 Bratislava",
        "period_year": 2025,
        "period_month": 1,
        "base_wage": Decimal("2500.00"),
        "overtime_hours": Decimal("0"),
        "overtime_amount": Decimal("0"),
        "bonus_amount": Decimal("0"),
        "supplement_amount": Decimal("0"),
        "gross_wage": Decimal("2500.00"),
        "sp_assessment_base": Decimal("2500.00"),
        "sp_nemocenske": Decimal("35.00"),
        "sp_starobne": Decimal("100.00"),
        "sp_invalidne": Decimal("75.00"),
        "sp_nezamestnanost": Decimal("25.00"),
        "sp_employee_total": Decimal("235.00"),
        "zp_assessment_base": Decimal("2500.00"),
        "zp_employee": Decimal("100.00"),
        "partial_tax_base": Decimal("2165.00"),
        "nczd_applied": Decimal("410.24"),
        "tax_base": Decimal("1754.76"),
        "tax_advance": Decimal("333.40"),
        "child_bonus": Decimal("0"),
        "tax_after_bonus": Decimal("333.40"),
        "net_wage": Decimal("1831.60"),
        "sp_employer_total": Decimal("642.50"),
        "zp_employer": Decimal("250.00"),
        "total_employer_cost": Decimal("3392.50"),
        "pillar2_amount": Decimal("0"),
    }
    defaults.update(overrides)
    return PaySlipData(**defaults)


# ===========================================================================
# Unit tests — PDF generator (no DB needed)
# ===========================================================================


class TestPaySlipData:
    """Tests for PaySlipData construction."""

    def test_create_with_all_fields(self):
        data = _make_pay_slip_data()
        assert data.company_name == "Test s.r.o."
        assert data.employee_name == "Ján Novák"
        assert data.period_year == 2025
        assert data.period_month == 1
        assert data.gross_wage == Decimal("2500.00")
        assert data.net_wage == Decimal("1831.60")

    def test_company_dic_optional(self):
        data = _make_pay_slip_data(company_dic=None)
        assert data.company_dic is None

    def test_period_month_names(self):
        from app.services.pdf_generator import MONTH_NAMES_SK

        assert MONTH_NAMES_SK[1] == "Január"
        assert MONTH_NAMES_SK[12] == "December"
        assert len(MONTH_NAMES_SK) == 12


class TestBuildPaySlipPdf:
    """Tests for build_pay_slip_pdf — generates raw PDF bytes."""

    def test_returns_bytes(self):
        data = _make_pay_slip_data()
        result = build_pay_slip_pdf(data)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_starts_with_pdf_header(self):
        data = _make_pay_slip_data()
        result = build_pay_slip_pdf(data)
        assert result[:5] == b"%PDF-"

    def test_pdf_size_reasonable(self):
        """PDF should be a reasonable size (> 1KB for a full pay slip)."""
        data = _make_pay_slip_data()
        result = build_pay_slip_pdf(data)
        assert len(result) > 1000

    def test_pdf_with_no_dic(self):
        """PDF should generate successfully even without DIČ."""
        data = _make_pay_slip_data(company_dic=None)
        result = build_pay_slip_pdf(data)
        assert result[:5] == b"%PDF-"

    def test_different_months_produce_different_pdfs(self):
        data_jan = _make_pay_slip_data(period_month=1)
        data_dec = _make_pay_slip_data(period_month=12)
        pdf_jan = build_pay_slip_pdf(data_jan)
        pdf_dec = build_pay_slip_pdf(data_dec)
        # Different month labels should produce different content
        assert pdf_jan != pdf_dec

    def test_pdf_with_overtime_and_bonus(self):
        data = _make_pay_slip_data(
            overtime_hours=Decimal("10.50"),
            overtime_amount=Decimal("125.00"),
            bonus_amount=Decimal("500.00"),
            supplement_amount=Decimal("100.00"),
            gross_wage=Decimal("3225.00"),
        )
        result = build_pay_slip_pdf(data)
        assert result[:5] == b"%PDF-"
        assert len(result) > 100

    def test_pdf_with_child_bonus(self):
        data = _make_pay_slip_data(
            child_bonus=Decimal("100.00"),
            tax_after_bonus=Decimal("233.40"),
        )
        result = build_pay_slip_pdf(data)
        assert result[:5] == b"%PDF-"

    def test_pdf_with_pillar2(self):
        data = _make_pay_slip_data(pillar2_amount=Decimal("100.00"))
        result = build_pay_slip_pdf(data)
        assert result[:5] == b"%PDF-"


class TestGetPdfPath:
    """Tests for get_pdf_path utility."""

    def test_standard_path(self):
        result = get_pdf_path("tenant_test", 2025, 1, "EMP-001")
        expected = f"{PDF_BASE_PATH}/tenant_test/2025/01/EMP-001.pdf"
        assert result == expected

    def test_month_zero_padded(self):
        result = get_pdf_path("tenant_test", 2025, 3, "EMP-001")
        assert "/03/" in result

    def test_december(self):
        result = get_pdf_path("tenant_test", 2025, 12, "EMP-001")
        assert "/12/" in result

    def test_different_tenant(self):
        result = get_pdf_path("tenant_abc", 2025, 6, "EMP-042")
        assert "/tenant_abc/" in result
        assert "EMP-042.pdf" in result


class TestWritePdfToDisk:
    """Tests for write_pdf_to_disk — file I/O."""

    def test_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "dir", "test.pdf")
            pdf_bytes = b"%PDF-1.4 test content"
            size = write_pdf_to_disk(pdf_bytes, path)

            assert os.path.exists(path)
            assert size == len(pdf_bytes)

            with open(path, "rb") as f:
                assert f.read() == pdf_bytes

    def test_creates_intermediate_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "a", "b", "c", "deep.pdf")
            write_pdf_to_disk(b"test", path)
            assert os.path.exists(path)

    def test_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.pdf")
            write_pdf_to_disk(b"old content", path)
            write_pdf_to_disk(b"new content", path)

            with open(path, "rb") as f:
                assert f.read() == b"new content"


class TestBuildPaySlipDataFromModels:
    """Tests for build_pay_slip_data_from_models — ORM to PaySlipData."""

    def test_extracts_fields(self, db_session):
        chain = _setup_parent_chain(db_session)
        data = build_pay_slip_data_from_models(
            tenant=chain["tenant"],
            employee=chain["employee"],
            payroll=chain["payroll"],
        )
        assert isinstance(data, PaySlipData)
        assert data.company_name == chain["tenant"].name
        assert data.company_ico == chain["tenant"].ico
        assert data.employee_number == chain["employee"].employee_number
        assert data.gross_wage == chain["payroll"].gross_wage
        assert data.net_wage == chain["payroll"].net_wage
        assert data.period_year == chain["payroll"].period_year
        assert data.period_month == chain["payroll"].period_month

    def test_employee_name_formatting(self, db_session):
        chain = _setup_parent_chain(db_session)
        data = build_pay_slip_data_from_models(
            tenant=chain["tenant"],
            employee=chain["employee"],
            payroll=chain["payroll"],
        )
        expected = f"{chain['employee'].first_name} {chain['employee'].last_name}"
        assert data.employee_name == expected

    def test_address_formatting(self, db_session):
        chain = _setup_parent_chain(db_session)
        data = build_pay_slip_data_from_models(
            tenant=chain["tenant"],
            employee=chain["employee"],
            payroll=chain["payroll"],
        )
        tenant = chain["tenant"]
        expected = f"{tenant.address_street}, {tenant.address_zip} {tenant.address_city}"
        assert data.company_address == expected


# ===========================================================================
# Integration tests — pay_slip service PDF functions (require DB)
# ===========================================================================


class TestGeneratePaySlipPdf:
    """Tests for pay_slip.generate_pay_slip_pdf service function."""

    def test_generates_and_creates_record(self, db_session):
        chain = _setup_parent_chain(db_session)
        tenant = chain["tenant"]
        employee = chain["employee"]
        payroll = chain["payroll"]

        with patch("app.services.pay_slip.write_pdf_to_disk") as mock_write:
            mock_write.return_value = 5000

            from app.services.pay_slip import generate_pay_slip_pdf

            result = generate_pay_slip_pdf(
                db_session,
                tenant_id=tenant.id,
                employee_id=employee.id,
                period_year=payroll.period_year,
                period_month=payroll.period_month,
            )

        assert isinstance(result, PaySlip)
        assert result.tenant_id == tenant.id
        assert result.employee_id == employee.id
        assert result.payroll_id == payroll.id
        assert result.file_size_bytes == 5000
        assert result.pdf_path.endswith(".pdf")
        mock_write.assert_called_once()

    def test_raises_for_nonexistent_tenant(self, db_session):
        from app.services.pay_slip import generate_pay_slip_pdf

        with pytest.raises(ValueError, match="Tenant.*not found"):
            generate_pay_slip_pdf(
                db_session,
                tenant_id=uuid4(),
                employee_id=uuid4(),
                period_year=2025,
                period_month=1,
            )

    def test_raises_for_nonexistent_employee(self, db_session):
        chain = _setup_parent_chain(db_session)

        from app.services.pay_slip import generate_pay_slip_pdf

        with pytest.raises(ValueError, match="Employee.*not found"):
            generate_pay_slip_pdf(
                db_session,
                tenant_id=chain["tenant"].id,
                employee_id=uuid4(),
                period_year=2025,
                period_month=1,
            )

    def test_raises_for_employee_wrong_tenant(self, db_session):
        chain1 = _setup_parent_chain(db_session)
        chain2 = _setup_parent_chain(db_session)

        from app.services.pay_slip import generate_pay_slip_pdf

        with pytest.raises(ValueError, match="does not belong to tenant"):
            generate_pay_slip_pdf(
                db_session,
                tenant_id=chain1["tenant"].id,
                employee_id=chain2["employee"].id,
                period_year=2025,
                period_month=1,
            )

    def test_raises_for_no_approved_payroll(self, db_session):
        chain = _setup_parent_chain(db_session)
        # Change payroll status to draft
        chain["payroll"].status = "draft"
        db_session.flush()

        from app.services.pay_slip import generate_pay_slip_pdf

        with pytest.raises(ValueError, match="Approved payroll.* not found"):
            generate_pay_slip_pdf(
                db_session,
                tenant_id=chain["tenant"].id,
                employee_id=chain["employee"].id,
                period_year=2025,
                period_month=1,
            )

    def test_updates_existing_pay_slip_on_regeneration(self, db_session):
        chain = _setup_parent_chain(db_session)
        tenant = chain["tenant"]
        employee = chain["employee"]
        payroll = chain["payroll"]

        with patch("app.services.pay_slip.write_pdf_to_disk") as mock_write:
            mock_write.return_value = 5000

            from app.services.pay_slip import generate_pay_slip_pdf

            first = generate_pay_slip_pdf(
                db_session,
                tenant_id=tenant.id,
                employee_id=employee.id,
                period_year=payroll.period_year,
                period_month=payroll.period_month,
            )

            # Regenerate — should update, not create duplicate
            mock_write.return_value = 6000
            second = generate_pay_slip_pdf(
                db_session,
                tenant_id=tenant.id,
                employee_id=employee.id,
                period_year=payroll.period_year,
                period_month=payroll.period_month,
            )

        assert first.id == second.id
        assert second.file_size_bytes == 6000


class TestGenerateAllPaySlips:
    """Tests for pay_slip.generate_all_pay_slips service function."""

    def test_generates_for_all_approved(self, db_session):
        chain = _setup_parent_chain(db_session)
        tenant = chain["tenant"]

        with patch("app.services.pay_slip.write_pdf_to_disk") as mock_write:
            mock_write.return_value = 4000

            from app.services.pay_slip import generate_all_pay_slips

            results = generate_all_pay_slips(
                db_session,
                tenant_id=tenant.id,
                period_year=2025,
                period_month=1,
            )

        assert len(results) == 1
        assert results[0].tenant_id == tenant.id

    def test_raises_for_no_approved_payrolls(self, db_session):
        chain = _setup_parent_chain(db_session)
        chain["payroll"].status = "draft"
        db_session.flush()

        from app.services.pay_slip import generate_all_pay_slips

        with pytest.raises(ValueError, match="Approved payrolls not found"):
            generate_all_pay_slips(
                db_session,
                tenant_id=chain["tenant"].id,
                period_year=2025,
                period_month=1,
            )

    def test_raises_for_nonexistent_tenant(self, db_session):
        from app.services.pay_slip import generate_all_pay_slips

        with pytest.raises(ValueError, match="Tenant.*not found"):
            generate_all_pay_slips(
                db_session,
                tenant_id=uuid4(),
                period_year=2025,
                period_month=1,
            )


class TestGetPaySlipPdfBytes:
    """Tests for pay_slip.get_pay_slip_pdf_bytes service function."""

    def test_returns_pdf_bytes_and_filename(self, db_session):
        chain = _setup_parent_chain(db_session)

        from app.services.pay_slip import get_pay_slip_pdf_bytes

        pdf_bytes, filename = get_pay_slip_pdf_bytes(
            db_session,
            tenant_id=chain["tenant"].id,
            employee_id=chain["employee"].id,
            period_year=2025,
            period_month=1,
        )

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"
        assert filename.endswith(".pdf")
        assert chain["employee"].employee_number in filename

    def test_raises_for_no_approved_payroll(self, db_session):
        chain = _setup_parent_chain(db_session)
        chain["payroll"].status = "calculated"
        db_session.flush()

        from app.services.pay_slip import get_pay_slip_pdf_bytes

        with pytest.raises(ValueError, match="Approved payroll.* not found"):
            get_pay_slip_pdf_bytes(
                db_session,
                tenant_id=chain["tenant"].id,
                employee_id=chain["employee"].id,
                period_year=2025,
                period_month=1,
            )


# ===========================================================================
# Router endpoint tests
# ===========================================================================


class TestDownloadPdfEndpoint:
    """Tests for GET /payslips/{year}/{month}/{employee_id}/pdf"""

    def test_download_returns_pdf(self, client, db_session):
        chain = _setup_parent_chain(db_session)

        response = client.get(
            f"/api/v1/payslips/2025/1/{chain['employee'].id}/pdf",
            params={"tenant_id": str(chain["tenant"].id)},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in response.headers
        assert response.content[:5] == b"%PDF-"

    def test_download_nonexistent_employee(self, client, db_session):
        chain = _setup_parent_chain(db_session)
        fake_id = uuid4()

        response = client.get(
            f"/api/v1/payslips/2025/1/{fake_id}/pdf",
            params={"tenant_id": str(chain["tenant"].id)},
        )

        assert response.status_code == 404

    def test_download_no_approved_payroll(self, client, db_session):
        chain = _setup_parent_chain(db_session)
        chain["payroll"].status = "draft"
        db_session.flush()

        response = client.get(
            f"/api/v1/payslips/2025/1/{chain['employee'].id}/pdf",
            params={"tenant_id": str(chain["tenant"].id)},
        )

        assert response.status_code == 404


class TestGenerateAllEndpoint:
    """Tests for POST /payslips/{year}/{month}/generate-all"""

    def test_generate_all_returns_201(self, client, db_session):
        chain = _setup_parent_chain(db_session)

        with patch("app.services.pay_slip.write_pdf_to_disk") as mock_write:
            mock_write.return_value = 3000

            response = client.post(
                "/api/v1/payslips/2025/1/generate-all",
                params={"tenant_id": str(chain["tenant"].id)},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["count"] == 1
        assert len(data["pay_slips"]) == 1
        assert data["pay_slips"][0]["pdf_path"].endswith(".pdf")

    def test_generate_all_no_approved(self, client, db_session):
        chain = _setup_parent_chain(db_session)
        chain["payroll"].status = "draft"
        db_session.flush()

        response = client.post(
            "/api/v1/payslips/2025/1/generate-all",
            params={"tenant_id": str(chain["tenant"].id)},
        )

        assert response.status_code == 404

    def test_generate_all_nonexistent_tenant(self, client, db_session):
        response = client.post(
            "/api/v1/payslips/2025/1/generate-all",
            params={"tenant_id": str(uuid4())},
        )

        assert response.status_code == 404
