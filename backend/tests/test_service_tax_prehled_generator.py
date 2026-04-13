"""Tests for DÚ tax monthly prehľad XML generator service."""

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
from app.services.tax_prehled_generator import (
    TAX_NAMESPACE,
    generate_tax_prehled_xml,
    get_tax_prehled_deadline,
)

# Namespace for ElementTree XPath
NS = {"tx": TAX_NAMESPACE}


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
        "schema_name": f"tenant_tax_{uuid4().hex[:8]}",
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
        "child_bonus": Decimal("100.00"),
        "tax_after_bonus": Decimal("138.31"),
        # Net
        "net_wage": Decimal("1593.69"),
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
# Unit tests — get_tax_prehled_deadline
# ---------------------------------------------------------------------------


class TestGetTaxPrehledDeadline:
    """Tests for deadline calculation."""

    def test_january_deadline_is_end_of_february(self):
        # 2025-02-28 (non-leap year)
        assert get_tax_prehled_deadline(2025, 1) == date(2025, 2, 28)

    def test_february_deadline_is_end_of_march(self):
        assert get_tax_prehled_deadline(2025, 2) == date(2025, 3, 31)

    def test_november_deadline_is_end_of_december(self):
        assert get_tax_prehled_deadline(2025, 11) == date(2025, 12, 31)

    def test_december_wraps_to_january(self):
        assert get_tax_prehled_deadline(2025, 12) == date(2026, 1, 31)

    def test_leap_year_february(self):
        # 2024 is leap year — January prehľad deadline is Feb 29
        assert get_tax_prehled_deadline(2024, 1) == date(2024, 2, 29)

    def test_june_deadline(self):
        assert get_tax_prehled_deadline(2026, 6) == date(2026, 7, 31)

    def test_april_deadline_has_30_days(self):
        # March prehľad → April 30
        assert get_tax_prehled_deadline(2025, 3) == date(2025, 4, 30)


# ---------------------------------------------------------------------------
# Integration tests — generate_tax_prehled_xml
# ---------------------------------------------------------------------------


class TestGenerateTaxPrehledXml:
    """Tests for DÚ tax monthly prehľad XML generation."""

    def test_generates_valid_xml(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)

        assert xml_bytes is not None
        assert len(xml_bytes) > 0
        root = ElementTree.fromstring(xml_bytes)
        assert "TaxMonthlyPrehled" in root.tag

    def test_xml_declaration_utf8(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)

        header = xml_bytes[:80].decode("utf-8").lower()
        assert "utf-8" in header

    def test_header_contains_period(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        year_el = root.find(".//tx:Header/tx:PeriodYear", NS)
        month_el = root.find(".//tx:Header/tx:PeriodMonth", NS)
        assert year_el is not None
        assert year_el.text == "2025"
        assert month_el is not None
        assert month_el.text == "1"

    def test_header_contains_employer_info(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session, name="ACME s.r.o.", ico="87654321", dic="2087654321")
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        ico_el = root.find(".//tx:Header/tx:EmployerICO", NS)
        dic_el = root.find(".//tx:Header/tx:EmployerDIC", NS)
        name_el = root.find(".//tx:Header/tx:EmployerName", NS)
        assert ico_el.text == "87654321"
        assert dic_el.text == "2087654321"
        assert name_el.text == "ACME s.r.o."

    def test_report_type_in_header(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        report_type = root.find(".//tx:Header/tx:ReportType", NS)
        assert report_type.text == "tax_prehled"

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

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        ico = root.find(".//tx:Employer/tx:ICO", NS)
        dic = root.find(".//tx:Employer/tx:DIC", NS)
        name = root.find(".//tx:Employer/tx:Name", NS)
        street = root.find(".//tx:Employer/tx:Address/tx:Street", NS)
        city = root.find(".//tx:Employer/tx:Address/tx:City", NS)

        assert ico.text == "11223344"
        assert dic.text == "2011223344"
        assert name.text == "Firma s.r.o."
        assert street.text == "Partizánska 5"
        assert city.text == "Žilina"

    def test_employee_tax_details(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        emp_el = root.find(".//tx:Employees/tx:Employee", NS)
        assert emp_el is not None

        assert emp_el.find("tx:GrossWage", NS).text == "2000.00"
        assert emp_el.find("tx:SPEmployeeTotal", NS).text == "188.00"
        assert emp_el.find("tx:ZPEmployee", NS).text == "80.00"
        assert emp_el.find("tx:PartialTaxBase", NS).text == "1732.00"
        assert emp_el.find("tx:NCZDApplied", NS).text == "477.74"
        assert emp_el.find("tx:TaxBase", NS).text == "1254.26"
        assert emp_el.find("tx:TaxAdvance", NS).text == "238.31"
        assert emp_el.find("tx:ChildBonus", NS).text == "100.00"
        assert emp_el.find("tx:TaxAfterBonus", NS).text == "138.31"

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

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        emp_el = root.find(".//tx:Employees/tx:Employee", NS)
        assert emp_el.find("tx:EmployeeNumber", NS).text == "EMP100"
        assert emp_el.find("tx:FirstName", NS).text == "Mária"
        assert emp_el.find("tx:LastName", NS).text == "Horváthová"
        assert emp_el.find("tx:BirthDate", NS).text == "1985-06-15"
        assert emp_el.find("tx:Gender", NS).text == "F"

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
                "zp_assessment_base": Decimal("3000.00"),
                "zp_employee": Decimal("120.00"),
                "partial_tax_base": Decimal("2598.00"),
                "nczd_applied": Decimal("477.74"),
                "tax_base": Decimal("2120.26"),
                "tax_advance": Decimal("402.85"),
                "child_bonus": Decimal("0.00"),
                "tax_after_bonus": Decimal("402.85"),
                "net_wage": Decimal("2195.15"),
                "sp_employer_nemocenske": Decimal("42.00"),
                "sp_employer_starobne": Decimal("420.00"),
                "sp_employer_invalidne": Decimal("90.00"),
                "sp_employer_nezamestnanost": Decimal("30.00"),
                "sp_employer_garancne": Decimal("7.50"),
                "sp_employer_rezervny": Decimal("142.50"),
                "sp_employer_kurzarbeit": Decimal("9.00"),
                "sp_employer_urazove": Decimal("24.00"),
                "sp_employer_total": Decimal("765.00"),
                "zp_employer": Decimal("330.00"),
                "total_employer_cost": Decimal("4095.00"),
            },
        )

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        employees = root.findall(".//tx:Employees/tx:Employee", NS)
        assert len(employees) == 2

    def test_totals_section(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        totals = root.find(".//tx:Totals", NS)
        assert totals is not None

        assert totals.find("tx:EmployeeCount", NS).text == "1"
        assert totals.find("tx:TotalGrossWage", NS).text == "2000.00"
        assert totals.find("tx:TotalSPEmployee", NS).text == "188.00"
        assert totals.find("tx:TotalZPEmployee", NS).text == "80.00"
        assert totals.find("tx:TotalPartialTaxBase", NS).text == "1732.00"
        assert totals.find("tx:TotalNCZDApplied", NS).text == "477.74"
        assert totals.find("tx:TotalTaxBase", NS).text == "1254.26"
        assert totals.find("tx:TotalTaxAdvance", NS).text == "238.31"
        assert totals.find("tx:TotalChildBonus", NS).text == "100.00"
        assert totals.find("tx:TotalTaxAfterBonus", NS).text == "138.31"

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
                "base_wage": Decimal("3000.00"),
                "gross_wage": Decimal("3000.00"),
                "sp_employee_total": Decimal("282.00"),
                "zp_employee": Decimal("120.00"),
                "partial_tax_base": Decimal("2598.00"),
                "nczd_applied": Decimal("477.74"),
                "tax_base": Decimal("2120.26"),
                "tax_advance": Decimal("402.85"),
                "child_bonus": Decimal("50.00"),
                "tax_after_bonus": Decimal("352.85"),
            },
        )

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        totals = root.find(".//tx:Totals", NS)
        assert totals.find("tx:EmployeeCount", NS).text == "2"
        assert totals.find("tx:TotalGrossWage", NS).text == "5000.00"
        assert totals.find("tx:TotalSPEmployee", NS).text == "470.00"
        assert totals.find("tx:TotalZPEmployee", NS).text == "200.00"
        assert totals.find("tx:TotalPartialTaxBase", NS).text == "4330.00"
        assert totals.find("tx:TotalNCZDApplied", NS).text == "955.48"
        assert totals.find("tx:TotalTaxBase", NS).text == "3374.52"
        assert totals.find("tx:TotalTaxAdvance", NS).text == "641.16"
        assert totals.find("tx:TotalChildBonus", NS).text == "150.00"
        assert totals.find("tx:TotalTaxAfterBonus", NS).text == "491.16"

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

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        employees = root.findall(".//tx:Employees/tx:Employee", NS)
        assert len(employees) == 2

    def test_no_payrolls_raises_value_error(self, db_session):
        tenant = _make_tenant(db_session)

        with pytest.raises(ValueError, match="No approved/paid payrolls"):
            generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)

    def test_only_draft_payrolls_raises_value_error(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        emp = _make_employee(db_session, tenant.id, hi.id)
        con = _make_contract(db_session, tenant.id, emp.id)
        _make_payroll(db_session, tenant.id, emp.id, con.id, status="draft")

        with pytest.raises(ValueError, match="No approved/paid payrolls"):
            generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)

    def test_tenant_not_found_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            generate_tax_prehled_xml(db_session, uuid4(), 2025, 1)

    def test_namespace_present(self, db_session):
        hi = _make_health_insurer(db_session)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes = generate_tax_prehled_xml(db_session, tenant.id, 2025, 1)
        root = ElementTree.fromstring(xml_bytes)

        assert TAX_NAMESPACE in root.tag
