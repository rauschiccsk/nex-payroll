"""ZP (Zdravotná poisťovňa) monthly report XML generator.

Generates the *Mesačný prehľad preddavkov na poistné na verejné zdravotné
poistenie* XML document per health insurer with per-employee breakdown
of health insurance contributions (both employee and employer shares).

Each health insurer (VšZP, Dôvera, Union) receives a separate XML.

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
from app.models.health_insurer import HealthInsurer
from app.models.payroll import Payroll
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# XML namespace for NEX Payroll ZP monthly report
ZP_NAMESPACE = "urn:sk:zp:mesacny-prehlad:2026"
NSMAP = {None: ZP_NAMESPACE}

# Mapping from report_type to health insurer code
REPORT_TYPE_TO_INSURER_CODE: dict[str, str] = {
    "zp_vszp": "25",
    "zp_dovera": "24",
    "zp_union": "27",
}

# Reverse mapping
INSURER_CODE_TO_REPORT_TYPE: dict[str, str] = {v: k for k, v in REPORT_TYPE_TO_INSURER_CODE.items()}

# Mapping from report_type to institution name
REPORT_TYPE_TO_INSTITUTION: dict[str, str] = {
    "zp_vszp": "Všeobecná zdravotná poisťovňa, a.s.",
    "zp_dovera": "Dôvera zdravotná poisťovňa, a.s.",
    "zp_union": "Union zdravotná poisťovňa, a.s.",
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
    insurer: HealthInsurer,
    report_type: str,
    period_year: int,
    period_month: int,
) -> None:
    """Build the Header section."""
    header = _sub(root, "Header")
    _sub(header, "ReportType", report_type)
    _sub(header, "PeriodYear", str(period_year))
    _sub(header, "PeriodMonth", str(period_month))
    _sub(header, "GeneratedAt", datetime.now(UTC).isoformat())
    _sub(header, "EmployerICO", tenant.ico)
    _sub(header, "EmployerName", tenant.name)
    _sub(header, "InsurerCode", insurer.code)
    _sub(header, "InsurerName", insurer.name)


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


def _build_insurer(root: etree._Element, insurer: HealthInsurer) -> None:
    """Build the Insurer identification section."""
    insurer_el = _sub(root, "Insurer")
    _sub(insurer_el, "Code", insurer.code)
    _sub(insurer_el, "Name", insurer.name)
    _sub(insurer_el, "IBAN", insurer.iban)
    if insurer.bic:
        _sub(insurer_el, "BIC", insurer.bic)


def _build_employee_element(
    parent: etree._Element,
    employee: Employee,
    payroll: Payroll,
) -> None:
    """Build a single Employee element with ZP contribution breakdown."""
    emp_el = _sub(parent, "Employee")
    _sub(emp_el, "EmployeeNumber", employee.employee_number)
    _sub(emp_el, "FirstName", employee.first_name)
    _sub(emp_el, "LastName", employee.last_name)
    _sub(emp_el, "BirthDate", employee.birth_date.isoformat())
    _sub(emp_el, "Gender", employee.gender)
    _sub(emp_el, "IsDisabled", str(employee.is_disabled).lower())
    _sub(emp_el, "AssessmentBase", _fmt(payroll.zp_assessment_base))

    # Employee contribution
    emp_contrib = _sub(emp_el, "EmployeeContribution")
    _sub(emp_contrib, "Amount", _fmt(payroll.zp_employee))

    # Employer contribution
    empr_contrib = _sub(emp_el, "EmployerContribution")
    _sub(empr_contrib, "Amount", _fmt(payroll.zp_employer))

    # Total for this employee
    _sub(emp_el, "TotalContribution", _fmt(payroll.zp_employee + payroll.zp_employer))


def _build_totals(
    root: etree._Element,
    payrolls: list[Payroll],
) -> None:
    """Build the Totals section."""
    totals = _sub(root, "Totals")
    _sub(totals, "EmployeeCount", str(len(payrolls)))

    total_base = sum((p.zp_assessment_base for p in payrolls), Decimal("0.00"))
    total_employee = sum((p.zp_employee for p in payrolls), Decimal("0.00"))
    total_employer = sum((p.zp_employer for p in payrolls), Decimal("0.00"))

    _sub(totals, "TotalAssessmentBase", _fmt(total_base))
    _sub(totals, "TotalEmployeeContributions", _fmt(total_employee))
    _sub(totals, "TotalEmployerContributions", _fmt(total_employer))
    _sub(totals, "GrandTotal", _fmt(total_employee + total_employer))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_zp_report_xml(
    db: Session,
    tenant_id: UUID,
    period_year: int,
    period_month: int,
    report_type: str,
) -> tuple[bytes, UUID]:
    """Generate ZP monthly report XML for a specific health insurer.

    Parameters
    ----------
    db : Session
        SQLAlchemy session (caller owns the transaction).
    tenant_id : UUID
        Owning tenant — employer identification taken from tenant record.
    period_year, period_month : int
        Payroll period for the report.
    report_type : str
        One of: ``zp_vszp``, ``zp_dovera``, ``zp_union``.

    Returns
    -------
    tuple[bytes, UUID]
        UTF-8 encoded XML document and the health_insurer_id.

    Raises
    ------
    ValueError
        If tenant/insurer not found, invalid report_type,
        or no approved/paid payrolls exist for the period and insurer.
    """
    if report_type not in REPORT_TYPE_TO_INSURER_CODE:
        raise ValueError(f"Invalid ZP report type: {report_type}")

    insurer_code = REPORT_TYPE_TO_INSURER_CODE[report_type]

    # --- Resolve tenant ---
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant with id={tenant_id} not found")

    # --- Resolve health insurer ---
    stmt_hi = select(HealthInsurer).where(
        HealthInsurer.code == insurer_code,
        HealthInsurer.is_active.is_(True),
    )
    insurer = db.execute(stmt_hi).scalars().first()
    if insurer is None:
        raise ValueError(f"Health insurer with code={insurer_code} not found or inactive")

    # --- Fetch employees assigned to this insurer for this tenant ---
    emp_stmt = select(Employee).where(
        Employee.tenant_id == tenant_id,
        Employee.health_insurer_id == insurer.id,
    )
    employees = {e.id: e for e in db.execute(emp_stmt).scalars().all()}

    if not employees:
        raise ValueError(f"No employees assigned to insurer {insurer_code} for tenant={tenant_id}")

    # --- Fetch approved/paid payrolls for these employees ---
    stmt = (
        select(Payroll)
        .where(
            Payroll.tenant_id == tenant_id,
            Payroll.period_year == period_year,
            Payroll.period_month == period_month,
            Payroll.status.in_(["approved", "paid"]),
            Payroll.employee_id.in_(list(employees.keys())),
        )
        .order_by(Payroll.employee_id)
    )
    payrolls: list[Payroll] = list(db.execute(stmt).scalars().all())

    if not payrolls:
        raise ValueError(
            f"No approved/paid payrolls for tenant={tenant_id}, "
            f"period={period_year}/{period_month:02d}, "
            f"insurer={insurer_code}"
        )

    # --- Build XML ---
    root = etree.Element("ZPMonthlyReport", nsmap=NSMAP)

    _build_header(root, tenant, insurer, report_type, period_year, period_month)
    _build_employer(root, tenant)
    _build_insurer(root, insurer)

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

    _build_totals(root, payrolls)

    xml_bytes = etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )

    logger.info(
        "Generated ZP monthly report (%s) for tenant=%s period=%d/%02d: %d employees, %d bytes",
        report_type,
        tenant_id,
        period_year,
        period_month,
        len(payrolls),
        len(xml_bytes),
    )

    return xml_bytes, insurer.id


def get_zp_report_deadline(period_year: int, period_month: int) -> date:
    """Return the statutory deadline for ZP monthly report.

    Deadline is 3 business days after the end of the payroll period month.
    Simplified: 5th of the month following the payroll period
    (conservative estimate for 3 business days).
    """
    if period_month == 12:
        return date(period_year + 1, 1, 5)
    return date(period_year, period_month + 1, 5)
