"""Tests for SP monthly report XML generator service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4
from xml.etree import ElementTree

import pytest

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.payroll import Payroll
from app.models.tenant import Tenant
from app.services.sp_report_generator import (
    SP_NAMESPACE,
    generate_sp_report_xml,
    get_sp_report_deadline,
)

# Namespace for ElementTree XPath
NS = {"sp": SP_NAMESPACE}


# ---------------------------------------------------------------------------
# Helpers — create test data
# ---------------------------------------------------------------------------


def _make_health_insurer(db_session, **overrides) -> HealthInsurer:
    defaults = {
        "code": f"{uuid4().int % 100:02d}",
        "name": "Všeobecná zdravotná poisťovňa, a.s.",
        "iban": "SK8975000000000012345999",
    }
    defaults.update(overrides)
    hi = HealthInsurer(**defaults)
    db_session.add(hi)
    db_session.flush()
    return hi


def _make_tenant(db_session, **overrides) -> Tenant:
    defaults = {
        "name": "Test s.r.o.",
        "ico": "12345678",
        "dic": "2012345678",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "bank_bic": "CEKOSKBX",
        "schema_name": f"tenant_sp_{uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    tenant = Tenant(**defaults)
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _make_employee(db_session, tenant_id, health_insurer_id, **overrides) -> Employee:
    emp_num = overrides.pop("employee_number", f"EMP{uuid4().hex[:6]}")
    defaults = {
        "tenant_id": tenant_id,
        "employee_number": emp_num,
        "first_name": "Ján",
        "last_name": "Novák",
        "birth_date": date(1990, 1, 15),
        "birth_number": "9001151234",
        "gender": "M",
        "nationality": "SK",
        "address_street": "Dlhá 42",
        "address_city": "Košice",
        "address_zip": "04001",
        "address_country": "SK",
        "bank_iban": "SK3112000000198742637541",
        "health_insurer_id": health_insurer_id,
        "tax_declaration_type": "standard",
        "status": "active",
        "hire_date": date(2020, 1, 1),
    }
    defaults.update(overrides)

    # health_insurer_id needs a real FK — skip for tests by setting nullable
    # We need to work around the FK constraint. Let's create without it.
    employee = Employee(**defaults)
    db_session.add(employee)
    db_session.flush()
    return employee


def _make_contract(db_session, tenant_id, employee_id, **overrides) -> Contract:
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "contract_number": f"CON{uuid4().hex[:6]}",
        "contract_type": "permanent",
        "job_title": "Developer",
        "wage_type": "monthly",
        "base_wage": Decimal("2000.00"),
        "hours_per_week": Decimal("40.0"),
        "start_date": date(2020, 1, 1),
    }
    defaults.update(overrides)
    contract = Contract(**defaults)
    db_session.add(contract)
    db_session.flush()
    return contract


def _make_payroll(db_session, tenant_id, employee_id, contract_id, **overrides) -> Payroll:
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "contract_id": contract_id,
        "period_year": 2025,
        "period_month": 1,
        "status": "approved",
        # Gross
        "base_wage": Decimal("2000.00"),
        "gross_wage": Decimal("2000.00"),
        # SP employee
        "sp_assessment_base": Decimal("2000.00"),
        "sp_nemocenske": Decimal("28.00"),
        "sp_starobne": Decimal("80.00"),
        "sp_invalidne": Decimal("60.00"),
        "sp_nezamestnanost": Decimal("20.00"),
        "sp_employee_total": Decimal("188.00"),
        # ZP employee
        "zp_assessment_base": Decimal("2000.00"),
        "zp_employee": Decimal("80.00"),
        # Tax
        "partial_tax_base": Decimal("1732.00"),
        "nczd_applied": Decimal("477.74"),
        "tax_base": Decimal("1254.26"),
        "tax_advance": Decimal("238.31"),
        "tax_after_bonus": Decimal("238.31"),
        # Net
        "net_wage": Decimal("1493.69"),
        # SP employer
        "sp_employer_nemocenske": Decimal("28.00"),
        "sp_employer_starobne": Decimal("280.00"),
        "sp_employer_invalidne": Decimal("60.00"),
        "sp_employer_nezamestnanost": Decimal("20.00"),
        "sp_employer_garancne": Decimal("5.00"),
        "sp_employer_rezervny": Decimal("95.00"),
        "sp_employer_kurzarbeit": Decimal("6.00"),
        "sp_employer_urazove": Decimal("16.00"),
        "sp_employer_total": Decimal("510.00"),
        # ZP employer
        "zp_employer": Decimal("220.00"),
        # Total cost
        "total_employer_cost": Decimal("2730.00"),
    }
    defaults.update(overrides)
    payroll = Payroll(**defaults)
    db_session.add(payroll)
    db_session.flush()
    return payroll


def _create_full_employee_with_payroll(
    db_session,
    tenant_id,
    health_insurer_id,
    *,
    employee_number=None,
    payroll_overrides=None,
    employee_overrides=None,
):
    """Create employee + contract + payroll in one step."""
    emp_kwargs = {"employee_number": employee_number} if employee_number else {}
    if employee_overrides:
        emp_kwargs.update(employee_overrides)
    employee = _make_employee(db_session, tenant_id, health_insurer_id, **emp_kwargs)
    contract = _make_contract(db_session, tenant_id, employee.id)
    p_kwargs = payroll_overrides or {}
    payroll = _make_payroll(db_session, tenant_id, employee.id, contract.id, **p_kwargs)
    return employee, contract, payroll


# ---------------------------------------------------------------------------
# Unit tests — get_sp_report_deadline
# ---------------------------------------------------------------------------


class TestGetSpReportDeadline:
    """Tests for deadline calculation."""

    def test_regular_month(self):
        assert get_sp_report_deadline(2025, 1) == date(2025, 2, 20)

    def test_november(self):
        assert get_sp_report_deadline(2025, 11) == date(2025, 12, 20)

    def test_december_wraps_to_next_year(self):
        assert get_sp_report_deadline(2025, 12) == date(2026, 1, 20)

    def test_june(self):
        assert get_sp_report_deadline(2026, 6) == date(2026, 7, 20)


# ---------------------------------------------------------------------------
# Integration tests — generate_sp_report_xml
# ---------------------------------------------------------------------------


class TestGenerateSpReportXml:
    """Tests for SP monthly report XML generation."""

    def test_generates_valid_xml(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)

        assert xml_bytes is not None
        assert len(xml_bytes) > 0
        # Must be valid XML
        root = ElementTree.fromstring(xml_bytes)
        assert "SPMonthlyReport" in root.tag

    def test_xml_declaration_utf8(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)

        header = xml_bytes[:80].decode("utf-8").lower()
        assert "utf-8" in header

    def test_header_contains_period(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        year_el = root.find(".//sp:Header/sp:PeriodYear", NS)
        month_el = root.find(".//sp:Header/sp:PeriodMonth", NS)
        assert year_el is not None
        assert year_el.text == "2025"
        assert month_el is not None
        assert month_el.text == "1"

    def test_header_contains_employer_info(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session, name="ACME s.r.o.", ico="87654321")
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        ico_el = root.find(".//sp:Header/sp:EmployerICO", NS)
        name_el = root.find(".//sp:Header/sp:EmployerName", NS)
        assert ico_el.text == "87654321"
        assert name_el.text == "ACME s.r.o."

    def test_employer_section(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(
            db_session,
            name="Firma s.r.o.",
            ico="11223344",
            dic="2011223344",
            address_street="Partizánska 5",
            address_city="Žilina",
            address_zip="01001",
        )
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        ico = root.find(".//sp:Employer/sp:ICO", NS)
        dic = root.find(".//sp:Employer/sp:DIC", NS)
        name = root.find(".//sp:Employer/sp:Name", NS)
        street = root.find(".//sp:Employer/sp:Address/sp:Street", NS)
        city = root.find(".//sp:Employer/sp:Address/sp:City", NS)

        assert ico.text == "11223344"
        assert dic.text == "2011223344"
        assert name.text == "Firma s.r.o."
        assert street.text == "Partizánska 5"
        assert city.text == "Žilina"

    def test_employee_contributions_breakdown(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        emp_el = root.find(".//sp:Employees/sp:Employee", NS)
        assert emp_el is not None

        base = emp_el.find("sp:AssessmentBase", NS)
        assert base.text == "2000.00"

        emp_contrib = emp_el.find("sp:EmployeeContributions", NS)
        assert emp_contrib.find("sp:Nemocenske", NS).text == "28.00"
        assert emp_contrib.find("sp:Starobne", NS).text == "80.00"
        assert emp_contrib.find("sp:Invalidne", NS).text == "60.00"
        assert emp_contrib.find("sp:Nezamestnanost", NS).text == "20.00"
        assert emp_contrib.find("sp:Total", NS).text == "188.00"

    def test_employer_contributions_breakdown(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        emp_el = root.find(".//sp:Employees/sp:Employee", NS)
        empr_contrib = emp_el.find("sp:EmployerContributions", NS)

        assert empr_contrib.find("sp:Nemocenske", NS).text == "28.00"
        assert empr_contrib.find("sp:Starobne", NS).text == "280.00"
        assert empr_contrib.find("sp:Invalidne", NS).text == "60.00"
        assert empr_contrib.find("sp:Nezamestnanost", NS).text == "20.00"
        assert empr_contrib.find("sp:Garancne", NS).text == "5.00"
        assert empr_contrib.find("sp:Rezervny", NS).text == "95.00"
        assert empr_contrib.find("sp:Kurzarbeit", NS).text == "6.00"
        assert empr_contrib.find("sp:Urazove", NS).text == "16.00"
        assert empr_contrib.find("sp:Total", NS).text == "510.00"

    def test_multiple_employees(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="EMP001",
        )
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="EMP002",
            payroll_overrides={
                "base_wage": Decimal("3000.00"),
                "gross_wage": Decimal("3000.00"),
                "sp_assessment_base": Decimal("3000.00"),
                "sp_nemocenske": Decimal("42.00"),
                "sp_starobne": Decimal("120.00"),
                "sp_invalidne": Decimal("90.00"),
                "sp_nezamestnanost": Decimal("30.00"),
                "sp_employee_total": Decimal("282.00"),
                "sp_employer_nemocenske": Decimal("42.00"),
                "sp_employer_starobne": Decimal("420.00"),
                "sp_employer_invalidne": Decimal("90.00"),
                "sp_employer_nezamestnanost": Decimal("30.00"),
                "sp_employer_garancne": Decimal("7.50"),
                "sp_employer_rezervny": Decimal("142.50"),
                "sp_employer_kurzarbeit": Decimal("9.00"),
                "sp_employer_urazove": Decimal("24.00"),
                "sp_employer_total": Decimal("765.00"),
                "zp_assessment_base": Decimal("3000.00"),
                "zp_employee": Decimal("120.00"),
                "partial_tax_base": Decimal("2598.00"),
                "nczd_applied": Decimal("477.74"),
                "tax_base": Decimal("2120.26"),
                "tax_advance": Decimal("402.85"),
                "tax_after_bonus": Decimal("402.85"),
                "net_wage": Decimal("2195.15"),
                "zp_employer": Decimal("330.00"),
                "total_employer_cost": Decimal("4095.00"),
            },
        )

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        employees = root.findall(".//sp:Employees/sp:Employee", NS)
        assert len(employees) == 2

    def test_fund_summary(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        fund_summary = root.find(".//sp:FundSummary", NS)
        assert fund_summary is not None

        funds = fund_summary.findall("sp:Fund", NS)
        assert len(funds) > 0

        # Check employee nemocenske fund
        emp_nemocenske = None
        for f in funds:
            if f.get("name") == "nemocenske" and f.get("side") == "employee":
                emp_nemocenske = f
                break
        assert emp_nemocenske is not None
        assert emp_nemocenske.find("sp:Total", NS).text == "28.00"

    def test_totals_section(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        totals = root.find(".//sp:Totals", NS)
        assert totals is not None

        assert totals.find("sp:EmployeeCount", NS).text == "1"
        assert totals.find("sp:TotalAssessmentBase", NS).text == "2000.00"
        assert totals.find("sp:TotalEmployeeContributions", NS).text == "188.00"
        assert totals.find("sp:TotalEmployerContributions", NS).text == "510.00"
        assert totals.find("sp:GrandTotal", NS).text == "698.00"

    def test_totals_with_multiple_employees(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="TOT001",
        )
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="TOT002",
            payroll_overrides={
                "sp_assessment_base": Decimal("3000.00"),
                "sp_employee_total": Decimal("282.00"),
                "sp_employer_total": Decimal("765.00"),
            },
        )

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        totals = root.find(".//sp:Totals", NS)
        assert totals.find("sp:EmployeeCount", NS).text == "2"
        assert totals.find("sp:TotalAssessmentBase", NS).text == "5000.00"
        assert totals.find("sp:TotalEmployeeContributions", NS).text == "470.00"
        assert totals.find("sp:TotalEmployerContributions", NS).text == "1275.00"
        assert totals.find("sp:GrandTotal", NS).text == "1745.00"

    def test_only_approved_payrolls_included(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)

        # Approved — should be included
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="APP001",
            payroll_overrides={"status": "approved"},
        )

        # Paid — should also be included
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="PAID001",
            payroll_overrides={"status": "paid"},
        )

        # Draft — should NOT be included
        emp3 = _make_employee(db_session, tenant.id, hi.id, employee_number="DRF001")
        con3 = _make_contract(db_session, tenant.id, emp3.id)
        _make_payroll(
            db_session,
            tenant.id,
            emp3.id,
            con3.id,
            status="draft",
        )

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        employees = root.findall(".//sp:Employees/sp:Employee", NS)
        assert len(employees) == 2

    def test_no_payrolls_raises_value_error(self, db_session):
        tenant = _make_tenant(db_session)

        with pytest.raises(ValueError, match="No approved/paid payrolls"):
            generate_sp_report_xml(db_session, tenant.id, 2025, 1)

    def test_only_draft_payrolls_raises_value_error(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        emp = _make_employee(db_session, tenant.id, hi.id)
        con = _make_contract(db_session, tenant.id, emp.id)
        _make_payroll(db_session, tenant.id, emp.id, con.id, status="draft")

        with pytest.raises(ValueError, match="No approved/paid payrolls"):
            generate_sp_report_xml(db_session, tenant.id, 2025, 1)

    def test_tenant_not_found_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            generate_sp_report_xml(db_session, uuid4(), 2025, 1)

    def test_employee_info_in_xml(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="EMP100",
            employee_overrides={
                "first_name": "Mária",
                "last_name": "Horváthová",
                "birth_date": date(1985, 6, 15),
                "gender": "F",
            },
        )

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        emp_el = root.find(".//sp:Employees/sp:Employee", NS)
        assert emp_el.find("sp:EmployeeNumber", NS).text == "EMP100"
        assert emp_el.find("sp:FirstName", NS).text == "Mária"
        assert emp_el.find("sp:LastName", NS).text == "Horváthová"
        assert emp_el.find("sp:BirthDate", NS).text == "1985-06-15"
        assert emp_el.find("sp:Gender", NS).text == "F"

    def test_namespace_present(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        assert SP_NAMESPACE in root.tag

    def test_report_type_in_header(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_sp_report_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        report_type = root.find(".//sp:Header/sp:ReportType", NS)
        assert report_type.text == "sp_monthly"
