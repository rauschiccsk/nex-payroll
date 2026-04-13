"""DÚ (Daňový úrad) tax monthly prehľad XML generator.

Generates the *Prehľad o zrazených a odvedených preddavkoch na daň*
XML document with per-employee tax withholding breakdown including
tax base, NČZD applied, tax advance, child bonus, and final tax.

Uses ``lxml`` for XML construction (per DESIGN.md tech stack).
All functions are synchronous (def, not async def).
"""

import calendar
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

# XML namespace for NEX Payroll tax monthly prehľad
TAX_NAMESPACE = "urn:sk:du:mesacny-prehlad:2026"
NSMAP = {None: TAX_NAMESPACE}


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
    _sub(header, "ReportType", "tax_prehled")
    _sub(header, "PeriodYear", str(period_year))
    _sub(header, "PeriodMonth", str(period_month))
    _sub(header, "GeneratedAt", datetime.now(UTC).isoformat())
    _sub(header, "EmployerICO", tenant.ico)
    _sub(header, "EmployerDIC", tenant.dic or "")
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
    """Build a single Employee element with tax withholding details."""
    emp_el = _sub(parent, "Employee")
    _sub(emp_el, "EmployeeNumber", employee.employee_number)
    _sub(emp_el, "FirstName", employee.first_name)
    _sub(emp_el, "LastName", employee.last_name)
    _sub(emp_el, "BirthDate", employee.birth_date.isoformat())
    _sub(emp_el, "Gender", employee.gender)

    # Income and deductions
    _sub(emp_el, "GrossWage", _fmt(payroll.gross_wage))
    _sub(emp_el, "SPEmployeeTotal", _fmt(payroll.sp_employee_total))
    _sub(emp_el, "ZPEmployee", _fmt(payroll.zp_employee))
    _sub(emp_el, "PartialTaxBase", _fmt(payroll.partial_tax_base))
    _sub(emp_el, "NCZDApplied", _fmt(payroll.nczd_applied))
    _sub(emp_el, "TaxBase", _fmt(payroll.tax_base))
    _sub(emp_el, "TaxAdvance", _fmt(payroll.tax_advance))
    _sub(emp_el, "ChildBonus", _fmt(payroll.child_bonus))
    _sub(emp_el, "TaxAfterBonus", _fmt(payroll.tax_after_bonus))


def _build_totals(
    root: etree._Element,
    payrolls: list[Payroll],
) -> None:
    """Build the Totals section."""
    totals = _sub(root, "Totals")
    _sub(totals, "EmployeeCount", str(len(payrolls)))

    total_gross = sum((p.gross_wage for p in payrolls), Decimal("0.00"))
    total_sp_employee = sum((p.sp_employee_total for p in payrolls), Decimal("0.00"))
    total_zp_employee = sum((p.zp_employee for p in payrolls), Decimal("0.00"))
    total_partial_tax_base = sum((p.partial_tax_base for p in payrolls), Decimal("0.00"))
    total_nczd = sum((p.nczd_applied for p in payrolls), Decimal("0.00"))
    total_tax_base = sum((p.tax_base for p in payrolls), Decimal("0.00"))
    total_tax_advance = sum((p.tax_advance for p in payrolls), Decimal("0.00"))
    total_child_bonus = sum((p.child_bonus for p in payrolls), Decimal("0.00"))
    total_tax_after_bonus = sum((p.tax_after_bonus for p in payrolls), Decimal("0.00"))

    _sub(totals, "TotalGrossWage", _fmt(total_gross))
    _sub(totals, "TotalSPEmployee", _fmt(total_sp_employee))
    _sub(totals, "TotalZPEmployee", _fmt(total_zp_employee))
    _sub(totals, "TotalPartialTaxBase", _fmt(total_partial_tax_base))
    _sub(totals, "TotalNCZDApplied", _fmt(total_nczd))
    _sub(totals, "TotalTaxBase", _fmt(total_tax_base))
    _sub(totals, "TotalTaxAdvance", _fmt(total_tax_advance))
    _sub(totals, "TotalChildBonus", _fmt(total_child_bonus))
    _sub(totals, "TotalTaxAfterBonus", _fmt(total_tax_after_bonus))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_tax_prehled_xml(
    db: Session,
    tenant_id: UUID,
    period_year: int,
    period_month: int,
) -> bytes:
    """Generate DÚ tax monthly prehľad XML.

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
    root = etree.Element("TaxMonthlyPrehled", nsmap=NSMAP)

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

    _build_totals(root, payrolls)

    xml_bytes = etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )

    logger.info(
        "Generated tax monthly prehľad for tenant=%s period=%d/%02d: %d employees, %d bytes",
        tenant_id,
        period_year,
        period_month,
        len(payrolls),
        len(xml_bytes),
    )

    return xml_bytes


def get_tax_prehled_deadline(period_year: int, period_month: int) -> date:
    """Return the statutory deadline for tax monthly prehľad.

    Deadline is the last day of the month following the payroll period
    (per Slovak tax legislation for monthly prehľad o preddavkoch na daň).
    """
    if period_month == 12:
        # January of next year — always 31 days
        return date(period_year + 1, 1, 31)
    next_month = period_month + 1
    _, last_day = calendar.monthrange(period_year, next_month)
    return date(period_year, next_month, last_day)
