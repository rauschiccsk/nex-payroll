"""Tests for ZP monthly report XML generator service."""

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
from app.services.zp_report_generator import (
    REPORT_TYPE_TO_INSURER_CODE,
    ZP_NAMESPACE,
    generate_zp_report_xml,
    get_zp_report_deadline,
)

# Namespace for ElementTree XPath
NS = {"zp": ZP_NAMESPACE}


# ---------------------------------------------------------------------------
# Helpers -- create test data
# ---------------------------------------------------------------------------


def _make_health_insurer(db_session, **overrides) -> HealthInsurer:
    defaults = {
        "code": "25",
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
        "schema_name": f"tenant_zp_{uuid4().hex[:8]}",
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
# Unit tests -- get_zp_report_deadline
# ---------------------------------------------------------------------------


class TestGetZpReportDeadline:
    """Tests for ZP deadline calculation."""

    def test_regular_month(self):
        assert get_zp_report_deadline(2025, 1) == date(2025, 2, 5)

    def test_november(self):
        assert get_zp_report_deadline(2025, 11) == date(2025, 12, 5)

    def test_december_wraps_to_next_year(self):
        assert get_zp_report_deadline(2025, 12) == date(2026, 1, 5)

    def test_june(self):
        assert get_zp_report_deadline(2026, 6) == date(2026, 7, 5)


# ---------------------------------------------------------------------------
# Integration tests -- generate_zp_report_xml
# ---------------------------------------------------------------------------


class TestGenerateZpReportXml:
    """Tests for ZP monthly report XML generation."""

    def test_generates_valid_xml(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes, insurer_id = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )

        assert xml_bytes is not None
        assert len(xml_bytes) > 0
        assert insurer_id == hi.id
        root = ElementTree.fromstring(xml_bytes)
        assert "ZPMonthlyReport" in root.tag

    def test_xml_declaration_utf8(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )

        header = xml_bytes[:80].decode("utf-8").lower()
        assert "utf-8" in header

    def test_header_contains_period_and_insurer(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        year_el = root.find(".//zp:Header/zp:PeriodYear", NS)
        month_el = root.find(".//zp:Header/zp:PeriodMonth", NS)
        code_el = root.find(".//zp:Header/zp:InsurerCode", NS)
        rtype_el = root.find(".//zp:Header/zp:ReportType", NS)

        assert year_el is not None and year_el.text == "2025"
        assert month_el is not None and month_el.text == "1"
        assert code_el is not None and code_el.text == "25"
        assert rtype_el is not None and rtype_el.text == "zp_vszp"

    def test_header_contains_employer_info(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session, name="ACME s.r.o.", ico="87654321")
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        ico_el = root.find(".//zp:Header/zp:EmployerICO", NS)
        name_el = root.find(".//zp:Header/zp:EmployerName", NS)
        assert ico_el.text == "87654321"
        assert name_el.text == "ACME s.r.o."

    def test_employer_section(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
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

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        ico = root.find(".//zp:Employer/zp:ICO", NS)
        dic = root.find(".//zp:Employer/zp:DIC", NS)
        name = root.find(".//zp:Employer/zp:Name", NS)
        street = root.find(".//zp:Employer/zp:Address/zp:Street", NS)
        city = root.find(".//zp:Employer/zp:Address/zp:City", NS)

        assert ico.text == "11223344"
        assert dic.text == "2011223344"
        assert name.text == "Firma s.r.o."
        assert street.text == "Partizánska 5"
        assert city.text == "Žilina"

    def test_insurer_section(self, db_session):
        hi = _make_health_insurer(
            db_session,
            code="25",
            name="Všeobecná zdravotná poisťovňa, a.s.",
            iban="SK1234567890123456789012",
            bic="SUBASKBX",
        )
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        code = root.find(".//zp:Insurer/zp:Code", NS)
        name = root.find(".//zp:Insurer/zp:Name", NS)
        iban = root.find(".//zp:Insurer/zp:IBAN", NS)
        bic = root.find(".//zp:Insurer/zp:BIC", NS)

        assert code.text == "25"
        assert name.text == "Všeobecná zdravotná poisťovňa, a.s."
        assert iban.text == "SK1234567890123456789012"
        assert bic.text == "SUBASKBX"

    def test_insurer_section_without_bic(self, db_session):
        hi = _make_health_insurer(db_session, code="25", bic=None)
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        bic = root.find(".//zp:Insurer/zp:BIC", NS)
        assert bic is None

    def test_employee_zp_contributions(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        emp_el = root.find(".//zp:Employees/zp:Employee", NS)
        assert emp_el is not None

        base = emp_el.find("zp:AssessmentBase", NS)
        assert base.text == "2000.00"

        emp_amount = emp_el.find("zp:EmployeeContribution/zp:Amount", NS)
        assert emp_amount.text == "80.00"

        empr_amount = emp_el.find("zp:EmployerContribution/zp:Amount", NS)
        assert empr_amount.text == "220.00"

        total = emp_el.find("zp:TotalContribution", NS)
        assert total.text == "300.00"

    def test_employee_info_in_xml(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
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

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        emp_el = root.find(".//zp:Employees/zp:Employee", NS)
        assert emp_el.find("zp:EmployeeNumber", NS).text == "EMP100"
        assert emp_el.find("zp:FirstName", NS).text == "Mária"
        assert emp_el.find("zp:LastName", NS).text == "Horváthová"
        assert emp_el.find("zp:BirthDate", NS).text == "1985-06-15"
        assert emp_el.find("zp:Gender", NS).text == "F"

    def test_disabled_employee_flag(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_overrides={"is_disabled": True},
            payroll_overrides={
                "zp_employee": Decimal("40.00"),
                "zp_employer": Decimal("110.00"),
            },
        )

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        emp_el = root.find(".//zp:Employees/zp:Employee", NS)
        disabled = emp_el.find("zp:IsDisabled", NS)
        assert disabled.text == "true"
        assert emp_el.find("zp:EmployeeContribution/zp:Amount", NS).text == "40.00"
        assert emp_el.find("zp:EmployerContribution/zp:Amount", NS).text == "110.00"

    def test_multiple_employees_same_insurer(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
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
                "zp_assessment_base": Decimal("3000.00"),
                "zp_employee": Decimal("120.00"),
                "zp_employer": Decimal("330.00"),
            },
        )

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        employees = root.findall(".//zp:Employees/zp:Employee", NS)
        assert len(employees) == 2

    def test_only_insurer_employees_included(self, db_session):
        """Employees from other insurers must NOT appear in the report."""
        hi_vszp = _make_health_insurer(db_session, code="25")
        hi_dovera = _make_health_insurer(db_session, code="24", name="Dôvera")
        tenant = _make_tenant(db_session)

        # Employee at VšZP
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi_vszp.id,
            employee_number="VSZP001",
        )
        # Employee at Dôvera — should NOT be in VšZP report
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi_dovera.id,
            employee_number="DOV001",
        )

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        employees = root.findall(".//zp:Employees/zp:Employee", NS)
        assert len(employees) == 1
        assert employees[0].find("zp:EmployeeNumber", NS).text == "VSZP001"

    def test_dovera_report(self, db_session):
        """Generate report for Dôvera (code 24)."""
        hi = _make_health_insurer(db_session, code="24", name="Dôvera")
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="DOV001",
        )

        xml_bytes, insurer_id = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_dovera",
        )
        root = ElementTree.fromstring(xml_bytes)

        assert insurer_id == hi.id
        rtype = root.find(".//zp:Header/zp:ReportType", NS)
        assert rtype.text == "zp_dovera"
        code = root.find(".//zp:Header/zp:InsurerCode", NS)
        assert code.text == "24"

    def test_union_report(self, db_session):
        """Generate report for Union (code 27)."""
        hi = _make_health_insurer(db_session, code="27", name="Union")
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="UNI001",
        )

        xml_bytes, insurer_id = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_union",
        )
        root = ElementTree.fromstring(xml_bytes)

        assert insurer_id == hi.id
        rtype = root.find(".//zp:Header/zp:ReportType", NS)
        assert rtype.text == "zp_union"
        code = root.find(".//zp:Header/zp:InsurerCode", NS)
        assert code.text == "27"

    def test_totals_section(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        totals = root.find(".//zp:Totals", NS)
        assert totals is not None
        assert totals.find("zp:EmployeeCount", NS).text == "1"
        assert totals.find("zp:TotalAssessmentBase", NS).text == "2000.00"
        assert totals.find("zp:TotalEmployeeContributions", NS).text == "80.00"
        assert totals.find("zp:TotalEmployerContributions", NS).text == "220.00"
        assert totals.find("zp:GrandTotal", NS).text == "300.00"

    def test_totals_with_multiple_employees(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
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
                "zp_assessment_base": Decimal("3000.00"),
                "zp_employee": Decimal("120.00"),
                "zp_employer": Decimal("330.00"),
            },
        )

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        totals = root.find(".//zp:Totals", NS)
        assert totals.find("zp:EmployeeCount", NS).text == "2"
        assert totals.find("zp:TotalAssessmentBase", NS).text == "5000.00"
        assert totals.find("zp:TotalEmployeeContributions", NS).text == "200.00"
        assert totals.find("zp:TotalEmployerContributions", NS).text == "550.00"
        assert totals.find("zp:GrandTotal", NS).text == "750.00"

    def test_only_approved_payrolls_included(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)

        # Approved — included
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="APP001",
            payroll_overrides={"status": "approved"},
        )
        # Paid — included
        _create_full_employee_with_payroll(
            db_session,
            tenant.id,
            hi.id,
            employee_number="PAID001",
            payroll_overrides={"status": "paid"},
        )
        # Draft — NOT included
        emp3 = _make_employee(db_session, tenant.id, hi.id, employee_number="DRF001")
        con3 = _make_contract(db_session, tenant.id, emp3.id)
        _make_payroll(db_session, tenant.id, emp3.id, con3.id, status="draft")

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        employees = root.findall(".//zp:Employees/zp:Employee", NS)
        assert len(employees) == 2

    def test_no_payrolls_raises_value_error(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)
        # Employee exists but no payrolls
        _make_employee(db_session, tenant.id, hi.id)

        with pytest.raises(ValueError, match="No approved/paid payrolls"):
            generate_zp_report_xml(db_session, tenant.id, 2025, 1, "zp_vszp")

    def test_no_employees_raises_value_error(self, db_session):
        _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)

        with pytest.raises(ValueError, match="No employees assigned"):
            generate_zp_report_xml(db_session, tenant.id, 2025, 1, "zp_vszp")

    def test_tenant_not_found_raises_value_error(self, db_session):
        _make_health_insurer(db_session, code="25")

        with pytest.raises(ValueError, match="not found"):
            generate_zp_report_xml(db_session, uuid4(), 2025, 1, "zp_vszp")

    def test_invalid_report_type_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="Invalid ZP report type"):
            generate_zp_report_xml(db_session, uuid4(), 2025, 1, "zp_invalid")

    def test_insurer_not_found_raises_value_error(self, db_session):
        """If the insurer code doesn't exist in DB, raise ValueError."""
        # Don't create insurer with code 25
        _make_health_insurer(db_session, code="24", name="Dôvera")
        tenant = _make_tenant(db_session)

        with pytest.raises(ValueError, match="not found or inactive"):
            generate_zp_report_xml(db_session, tenant.id, 2025, 1, "zp_vszp")

    def test_namespace_present(self, db_session):
        hi = _make_health_insurer(db_session, code="25")
        tenant = _make_tenant(db_session)
        _create_full_employee_with_payroll(db_session, tenant.id, hi.id)

        xml_bytes, _ = generate_zp_report_xml(
            db_session,
            tenant.id,
            2025,
            1,
            "zp_vszp",
        )
        root = ElementTree.fromstring(xml_bytes)

        assert ZP_NAMESPACE in root.tag

    def test_report_type_to_insurer_code_mapping(self):
        """Verify the mapping covers all 3 Slovak health insurers."""
        assert REPORT_TYPE_TO_INSURER_CODE == {
            "zp_vszp": "25",
            "zp_dovera": "24",
            "zp_union": "27",
        }
