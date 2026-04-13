"""SP (Sociálna poisťovňa) monthly report XML generator.

Generates the *Mesačný výkaz poistného a príspevkov* XML document
with per-employee and per-fund breakdown of social insurance
contributions (both employee and employer shares).

Uses ``lxml`` for XML construction (per DESIGN.md tech stack).
All functions are synchronous (def, not async def).
"""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from lxml import etree
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.payroll import Payroll
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# XML namespace for NEX Payroll SP monthly report
SP_NAMESPACE = "urn:sk:sp:mesacny-vykaz:2026"
NSMAP = {None: SP_NAMESPACE}

# Fund definitions — order matters for XML output
EMPLOYEE_FUNDS = ("nemocenske", "starobne", "invalidne", "nezamestnanost")
EMPLOYER_FUNDS = (
    "nemocenske",
    "starobne",
    "invalidne",
    "nezamestnanost",
    "garancne",
    "rezervny",
    "kurzarbeit",
    "urazove",
)

# Mapping from fund name to Payroll model field names
_EMPLOYEE_FIELD_MAP = {
    "nemocenske": "sp_nemocenske",
    "starobne": "sp_starobne",
    "invalidne": "sp_invalidne",
    "nezamestnanost": "sp_nezamestnanost",
}

_EMPLOYER_FIELD_MAP = {
    "nemocenske": "sp_employer_nemocenske",
    "starobne": "sp_employer_starobne",
    "invalidne": "sp_employer_invalidne",
    "nezamestnanost": "sp_employer_nezamestnanost",
    "garancne": "sp_employer_garancne",
    "rezervny": "sp_employer_rezervny",
    "kurzarbeit": "sp_employer_kurzarbeit",
    "urazove": "sp_employer_urazove",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt(value: Decimal) -> str:
    """Format Decimal to string with 2 decimal places."""
    return f"{value:.2f}"


def _sub(parent: etree._Element, tag: str, text: str | None = None) -> etree._Element:
    """Create a sub-element with optional text content."""
    el = etree.SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


# ---------------------------------------------------------------------------
# Core XML generation
# ---------------------------------------------------------------------------


def _build_header(
    root: etree._Element,
    tenant: Tenant,
    period_year: int,
    period_month: int,
) -> None:
    """Build the Header section."""
    header = _sub(root, "Header")
    _sub(header, "ReportType", "sp_monthly")
    _sub(header, "PeriodYear", str(period_year))
    _sub(header, "PeriodMonth", str(period_month))
    _sub(header, "GeneratedAt", datetime.now(UTC).isoformat())
    _sub(header, "EmployerICO", tenant.ico)
    _sub(header, "EmployerName", tenant.name)


def _build_employer(root: etree._Element, tenant: Tenant) -> None:
    """Build the Employer identification section."""
    employer = _sub(root, "Employer")
    _sub(employer, "ICO", tenant.ico)
    _sub(employer, "DIC", tenant.dic or "")
    _sub(employer, "Name", tenant.name)

    address = _sub(employer, "Address")
    _sub(address, "Street", tenant.address_street)
    _sub(address, "City", tenant.address_city)
    _sub(address, "ZIP", tenant.address_zip)
    _sub(address, "Country", tenant.address_country)


def _build_employee_element(
    parent: etree._Element,
    employee: Employee,
    payroll: Payroll,
) -> None:
    """Build a single Employee element with fund breakdown."""
    emp_el = _sub(parent, "Employee")
    _sub(emp_el, "EmployeeNumber", employee.employee_number)
    _sub(emp_el, "FirstName", employee.first_name)
    _sub(emp_el, "LastName", employee.last_name)
    _sub(emp_el, "BirthDate", employee.birth_date.isoformat())
    _sub(emp_el, "Gender", employee.gender)
    _sub(emp_el, "AssessmentBase", _fmt(payroll.sp_assessment_base))

    # Employee contributions
    emp_contrib = _sub(emp_el, "EmployeeContributions")
    for fund in EMPLOYEE_FUNDS:
        field = _EMPLOYEE_FIELD_MAP[fund]
        _sub(emp_contrib, fund.capitalize(), _fmt(getattr(payroll, field)))
    _sub(emp_contrib, "Total", _fmt(payroll.sp_employee_total))

    # Employer contributions
    empr_contrib = _sub(emp_el, "EmployerContributions")
    for fund in EMPLOYER_FUNDS:
        field = _EMPLOYER_FIELD_MAP[fund]
        _sub(empr_contrib, fund.capitalize(), _fmt(getattr(payroll, field)))
    _sub(empr_contrib, "Total", _fmt(payroll.sp_employer_total))


def _build_fund_summary(
    root: etree._Element,
    payrolls: list[Payroll],
) -> None:
    """Build the FundSummary section with totals per fund."""
    summary = _sub(root, "FundSummary")

    # Employee-side funds
    for fund in EMPLOYEE_FUNDS:
        fund_el = _sub(summary, "Fund")
        fund_el.set("name", fund)
        fund_el.set("side", "employee")

        field = _EMPLOYEE_FIELD_MAP[fund]
        total = sum((getattr(p, field) for p in payrolls), Decimal("0.00"))
        _sub(fund_el, "Total", _fmt(total))

    # Employer-side funds
    for fund in EMPLOYER_FUNDS:
        fund_el = _sub(summary, "Fund")
        fund_el.set("name", fund)
        fund_el.set("side", "employer")

        field = _EMPLOYER_FIELD_MAP[fund]
        total = sum((getattr(p, field) for p in payrolls), Decimal("0.00"))
        _sub(fund_el, "Total", _fmt(total))


def _build_totals(
    root: etree._Element,
    payrolls: list[Payroll],
) -> None:
    """Build the Totals section."""
    totals = _sub(root, "Totals")
    _sub(totals, "EmployeeCount", str(len(payrolls)))

    total_base = sum((p.sp_assessment_base for p in payrolls), Decimal("0.00"))
    total_employee = sum((p.sp_employee_total for p in payrolls), Decimal("0.00"))
    total_employer = sum((p.sp_employer_total for p in payrolls), Decimal("0.00"))

    _sub(totals, "TotalAssessmentBase", _fmt(total_base))
    _sub(totals, "TotalEmployeeContributions", _fmt(total_employee))
    _sub(totals, "TotalEmployerContributions", _fmt(total_employer))
    _sub(totals, "GrandTotal", _fmt(total_employee + total_employer))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_sp_report_xml(
    db: Session,
    tenant_id: UUID,
    period_year: int,
    period_month: int,
) -> bytes:
    """Generate SP monthly report XML with fund breakdown.

    Parameters
    ----------
    db : Session
        SQLAlchemy session (caller owns the transaction).
    tenant_id : UUID
        Owning tenant — employer identification taken from tenant record.
    period_year, period_month : int
        Payroll period for the report.

    Returns
    -------
    bytes
        UTF-8 encoded XML document.

    Raises
    ------
    ValueError
        If tenant not found or no approved/paid payrolls exist for the period.
    """
    # --- Resolve tenant ---
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant with id={tenant_id} not found")

    # --- Fetch approved/paid payrolls for the period ---
    stmt = (
        select(Payroll)
        .where(
            Payroll.tenant_id == tenant_id,
            Payroll.period_year == period_year,
            Payroll.period_month == period_month,
            Payroll.status.in_(["approved", "paid"]),
        )
        .order_by(Payroll.employee_id)
    )
    payrolls: list[Payroll] = list(db.execute(stmt).scalars().all())

    if not payrolls:
        raise ValueError(f"No approved/paid payrolls for tenant={tenant_id}, period={period_year}/{period_month:02d}")

    # --- Fetch employees for the payrolls ---
    employee_ids = [p.employee_id for p in payrolls]
    emp_stmt = select(Employee).where(Employee.id.in_(employee_ids))
    employees = {e.id: e for e in db.execute(emp_stmt).scalars().all()}

    # --- Build XML ---
    root = etree.Element("SPMonthlyReport", nsmap=NSMAP)

    _build_header(root, tenant, period_year, period_month)
    _build_employer(root, tenant)

    # Employees section
    employees_el = _sub(root, "Employees")
    for payroll in payrolls:
        employee = employees.get(payroll.employee_id)
        if employee is None:
            logger.warning(
                "Employee %s not found for payroll %s — skipping",
                payroll.employee_id,
                payroll.id,
            )
            continue
        _build_employee_element(employees_el, employee, payroll)

    _build_fund_summary(root, payrolls)
    _build_totals(root, payrolls)

    xml_bytes = etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )

    logger.info(
        "Generated SP monthly report for tenant=%s period=%d/%02d: %d employees, %d bytes",
        tenant_id,
        period_year,
        period_month,
        len(payrolls),
        len(xml_bytes),
    )

    return xml_bytes


def get_sp_report_deadline(period_year: int, period_month: int) -> date:
    """Return the statutory deadline for SP monthly report.

    Deadline is the 20th of the month following the payroll period.
    """
    if period_month == 12:
        return date(period_year + 1, 1, 20)
    return date(period_year, period_month + 1, 20)
