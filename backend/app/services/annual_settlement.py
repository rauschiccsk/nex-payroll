"""Annual tax settlement service — R-09 implementation.

Calculates annual tax settlement for all employees in a tenant,
recalculating NČZD using annual rules (not monthly approximations).

Key annual NČZD rules (Slovak 2026):
  - Annual ZD ≤ 26,367.26 → NČZD = 5,966.73 (full)
  - Annual ZD > 26,367.26 and ≤ 50,234.20 → NČZD = 12,558.55 - ZD/4
  - Annual ZD > 50,234.20 → NČZD = 0 (eliminated)

Settlement = sum(monthly advances) - actual annual tax
  Positive → employee overpaid (refund)
  Negative → employee underpaid (additional tax due)
"""

import io
import logging
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.annual_settlement import AnnualSettlement
from app.models.employee import Employee
from app.models.employee_child import EmployeeChild
from app.models.payroll import Payroll
from app.services.calculation_engine import (
    CHILD_BONUS_15_TO_18,
    CHILD_BONUS_PERCENTAGE_LIMITS,
    CHILD_BONUS_UNDER_15,
    NCZD_ANNUAL,
    NCZD_ELIMINATION_THRESHOLD,
    NCZD_REDUCTION_CONSTANT,
    NCZD_REDUCTION_THRESHOLD,
    _child_age_at_period,
    get_rates_for_period,
)

logger = logging.getLogger(__name__)

# Rounding precision
TWO_PLACES = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    """Round to 2 decimal places using ROUND_HALF_UP."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _calculate_annual_nczd(
    annual_partial_tax_base: Decimal,
    nczd_eligible: bool,
    *,
    nczd_annual: Decimal = NCZD_ANNUAL,
    nczd_reduction_threshold: Decimal = NCZD_REDUCTION_THRESHOLD,
    nczd_reduction_constant: Decimal = NCZD_REDUCTION_CONSTANT,
    nczd_elimination_threshold: Decimal = NCZD_ELIMINATION_THRESHOLD,
) -> Decimal:
    """Calculate annual NČZD using annual rules.

    Unlike monthly calculation (which approximates), annual settlement
    uses the actual annual partial tax base for NČZD determination.

    Args:
        annual_partial_tax_base: Annual gross - SP employee - ZP employee.
        nczd_eligible: Whether employee has signed tax declaration.
        nczd_annual: Full annual NČZD amount (default 5,966.73).
        nczd_reduction_threshold: Income threshold for NČZD reduction.
        nczd_reduction_constant: Constant in reduction formula.
        nczd_elimination_threshold: Income above which NČZD = 0.

    Returns:
        Recalculated annual NČZD amount.
    """
    if not nczd_eligible:
        return Decimal("0")

    if annual_partial_tax_base <= nczd_reduction_threshold:
        return nczd_annual
    elif annual_partial_tax_base <= nczd_elimination_threshold:
        reduced = _round(nczd_reduction_constant - annual_partial_tax_base / 4)
        return max(Decimal("0"), reduced)
    else:
        return Decimal("0")


def _calculate_annual_child_bonus(
    db: Session,
    employee_id: UUID,
    tenant_id: UUID,
    year: int,
    annual_partial_tax_base: Decimal,
    rates_child_under_15: Decimal = CHILD_BONUS_UNDER_15,
    rates_child_15_to_18: Decimal = CHILD_BONUS_15_TO_18,
) -> Decimal:
    """Calculate total annual child tax bonus.

    Sums eligible child bonus for each month of the year,
    applying age rules and percentage limits.
    """
    children_stmt = select(EmployeeChild).where(
        EmployeeChild.employee_id == employee_id,
        EmployeeChild.tenant_id == tenant_id,
    )
    children = list(db.execute(children_stmt).scalars().all())

    if not children:
        return Decimal("0")

    total_annual_bonus = Decimal("0")

    # Calculate bonus for each month
    for month in range(1, 13):
        eligible_bonuses: list[Decimal] = []

        for child in children:
            if not child.is_tax_bonus_eligible:
                continue

            period_start = date(year, month, 1)
            if child.custody_to is not None and child.custody_to < period_start:
                continue
            if child.custody_from is not None and child.custody_from > period_start:
                continue

            age = _child_age_at_period(child.birth_date, year, month)
            if age < 0 or age >= 18:
                continue

            bonus = rates_child_under_15 if age < 15 else rates_child_15_to_18
            eligible_bonuses.append(bonus)

        if eligible_bonuses:
            monthly_bonus_total = sum(eligible_bonuses)
            child_count = len(eligible_bonuses)

            # Apply percentage limit
            limit_idx = min(child_count - 1, len(CHILD_BONUS_PERCENTAGE_LIMITS) - 1)
            percentage_limit = CHILD_BONUS_PERCENTAGE_LIMITS[limit_idx]
            # Monthly partial tax base approximation = annual / 12
            monthly_ptb = _round(annual_partial_tax_base / 12)
            max_bonus = _round(monthly_ptb * percentage_limit)

            capped_bonus = min(monthly_bonus_total, max(Decimal("0"), max_bonus))
            total_annual_bonus += capped_bonus

    return _round(total_annual_bonus)


def calculate_annual_settlement(
    db: Session,
    *,
    tenant_id: UUID,
    year: int,
) -> list[AnnualSettlement]:
    """Calculate annual tax settlement for all employees in a tenant.

    Processes all employees who have at least one calculated/approved/paid
    payroll in the given year. For each employee:
    1. Sums all monthly payroll components
    2. Recalculates NČZD using annual rules
    3. Computes actual annual tax
    4. Calculates settlement (advances - actual tax)

    Returns list of AnnualSettlement records (flushed, not committed).
    """
    # Load rates for the year (use January as reference)
    rates = get_rates_for_period(db, year, 1)

    # Find all employees with payrolls in this year
    employee_ids_stmt = (
        select(Payroll.employee_id)
        .where(
            Payroll.tenant_id == tenant_id,
            Payroll.period_year == year,
            Payroll.status.in_(["calculated", "approved", "paid"]),
        )
        .distinct()
    )
    employee_ids = list(db.execute(employee_ids_stmt).scalars().all())

    settlements: list[AnnualSettlement] = []

    for emp_id in employee_ids:
        # Load employee
        employee = db.get(Employee, emp_id)
        if employee is None:
            logger.warning("Employee %s not found, skipping", emp_id)
            continue

        # Aggregate monthly payroll data
        agg_stmt = select(
            func.sum(Payroll.gross_wage).label("total_gross"),
            func.sum(Payroll.sp_employee_total).label("total_sp"),
            func.sum(Payroll.zp_employee).label("total_zp"),
            func.sum(Payroll.nczd_applied).label("total_nczd_monthly"),
            func.sum(Payroll.tax_after_bonus).label("total_advances"),
            func.sum(Payroll.child_bonus).label("total_child_bonus"),
            func.count().label("months_count"),
        ).where(
            Payroll.tenant_id == tenant_id,
            Payroll.employee_id == emp_id,
            Payroll.period_year == year,
            Payroll.status.in_(["calculated", "approved", "paid"]),
        )
        row = db.execute(agg_stmt).one()

        total_gross = row.total_gross or Decimal("0")
        total_sp = row.total_sp or Decimal("0")
        total_zp = row.total_zp or Decimal("0")
        nczd_monthly_total = row.total_nczd_monthly or Decimal("0")
        total_advances = row.total_advances or Decimal("0")
        months_count = row.months_count or 0

        if months_count == 0:
            continue

        # Annual partial tax base = gross - SP employee - ZP employee
        annual_ptb = _round(total_gross - total_sp - total_zp)

        # Recalculate NČZD using annual rules
        nczd_annual_recalc = _calculate_annual_nczd(
            annual_ptb,
            employee.nczd_applied,
            nczd_annual=rates.nczd_annual,
            nczd_reduction_threshold=rates.nczd_reduction_threshold,
            nczd_reduction_constant=rates.nczd_reduction_constant,
            nczd_elimination_threshold=rates.nczd_elimination_threshold,
        )

        # Annual tax base
        annual_tax_base = max(Decimal("0"), _round(annual_ptb - nczd_annual_recalc))

        # Progressive tax: 19% up to threshold, 25% above
        threshold = rates.tax_bracket_annual_threshold

        if annual_tax_base <= threshold:
            tax_19 = _round(annual_tax_base * rates.tax_rate_19)
            tax_25 = Decimal("0")
        else:
            tax_19 = _round(threshold * rates.tax_rate_19)
            tax_25 = _round((annual_tax_base - threshold) * rates.tax_rate_25)

        annual_tax_total = _round(tax_19 + tax_25)

        # Annual child bonus
        annual_child_bonus = _calculate_annual_child_bonus(
            db,
            emp_id,
            tenant_id,
            year,
            annual_ptb,
            rates.child_bonus_under_15,
            rates.child_bonus_15_to_18,
        )

        # Tax after bonus
        annual_tax_after_bonus = max(Decimal("0"), _round(annual_tax_total - annual_child_bonus))

        # Settlement = monthly advances paid - actual annual tax
        # Positive = overpaid (refund to employee)
        # Negative = underpaid (employee owes)
        settlement_amount = _round(total_advances - annual_tax_after_bonus)

        # Check for existing settlement
        existing_stmt = select(AnnualSettlement).where(
            AnnualSettlement.tenant_id == tenant_id,
            AnnualSettlement.employee_id == emp_id,
            AnnualSettlement.year == year,
        )
        existing = db.execute(existing_stmt).scalar_one_or_none()

        field_values = {
            "total_gross_wage": total_gross,
            "total_sp_employee": total_sp,
            "total_zp_employee": total_zp,
            "annual_partial_tax_base": annual_ptb,
            "nczd_monthly_total": nczd_monthly_total,
            "nczd_annual_recalculated": nczd_annual_recalc,
            "annual_tax_base": annual_tax_base,
            "annual_tax_19": tax_19,
            "annual_tax_25": tax_25,
            "annual_tax_total": annual_tax_total,
            "annual_child_bonus": annual_child_bonus,
            "annual_tax_after_bonus": annual_tax_after_bonus,
            "total_monthly_advances": total_advances,
            "settlement_amount": settlement_amount,
            "months_count": months_count,
            "status": "calculated",
            "calculated_at": datetime.now(UTC),
        }

        if existing is not None:
            for field_name, value in field_values.items():
                setattr(existing, field_name, value)
            settlements.append(existing)
        else:
            settlement = AnnualSettlement(
                tenant_id=tenant_id,
                employee_id=emp_id,
                year=year,
                **field_values,
            )
            db.add(settlement)
            settlements.append(settlement)

        db.flush()

    return settlements


def get_settlements_for_year(
    db: Session,
    *,
    tenant_id: UUID,
    year: int,
) -> list[AnnualSettlement]:
    """Retrieve all annual settlements for a tenant/year."""
    stmt = (
        select(AnnualSettlement)
        .where(
            AnnualSettlement.tenant_id == tenant_id,
            AnnualSettlement.year == year,
        )
        .order_by(AnnualSettlement.employee_id)
    )
    return list(db.execute(stmt).scalars().all())


def approve_settlement(
    db: Session,
    *,
    settlement_id: UUID,
    tenant_id: UUID,
    approved_by: UUID,
) -> AnnualSettlement:
    """Approve an annual tax settlement.

    Transitions status from 'calculated' to 'approved'.
    Raises ValueError if settlement not found or not in 'calculated' status.
    """
    stmt = select(AnnualSettlement).where(
        AnnualSettlement.id == settlement_id,
        AnnualSettlement.tenant_id == tenant_id,
    )
    settlement = db.execute(stmt).scalar_one_or_none()

    if settlement is None:
        raise ValueError(f"Annual settlement {settlement_id} not found")

    if settlement.status != "calculated":
        raise ValueError(
            f"Settlement cannot be approved — current status is '{settlement.status}', expected 'calculated'"
        )

    settlement.status = "approved"
    settlement.approved_at = datetime.now(UTC)
    settlement.approved_by = approved_by
    db.flush()

    return settlement


def generate_income_certificate_pdf(
    db: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    year: int,
) -> bytes:
    """Generate Potvrdenie o príjmoch (income certificate) PDF for an employee.

    Returns the PDF as bytes. Raises ValueError if no settlement exists.
    """
    # Load settlement
    stmt = select(AnnualSettlement).where(
        AnnualSettlement.tenant_id == tenant_id,
        AnnualSettlement.employee_id == employee_id,
        AnnualSettlement.year == year,
    )
    settlement = db.execute(stmt).scalar_one_or_none()
    if settlement is None:
        raise ValueError(
            f"Annual settlement not found for employee {employee_id}, year {year}. Run annual tax settlement first."
        )

    # Load employee
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise ValueError(f"Employee {employee_id} not found")

    # Build PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Heading1"],
        fontSize=14,
        alignment=1,  # center
        spaceAfter=10 * mm,
    )
    subtitle_style = ParagraphStyle(
        "CertSubtitle",
        parent=styles["Heading2"],
        fontSize=11,
        alignment=1,
        spaceAfter=5 * mm,
    )
    normal_style = ParagraphStyle(
        "CertNormal",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=3 * mm,
    )

    elements: list = []

    # Title
    elements.append(
        Paragraph(
            "Potvrdenie o zdanite\u013ených pr\u00edjmoch",
            title_style,
        )
    )
    elements.append(
        Paragraph(
            f"za rok {year}",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 5 * mm))

    # Employee info
    elements.append(
        Paragraph(
            f"Zamestnanec: {employee.first_name} {employee.last_name}",
            normal_style,
        )
    )
    elements.append(
        Paragraph(
            f"Obdobie: {year}",
            normal_style,
        )
    )
    elements.append(Spacer(1, 5 * mm))

    # Income summary table
    data = [
        ["Polo\u017eka", "Suma (\u20ac)"],
        ["\u00dahrnne pr\u00edjmy (hrub\u00e1 mzda)", f"{settlement.total_gross_wage:,.2f}"],
        ["Soci\u00e1lne poistenie (zamestnanec)", f"{settlement.total_sp_employee:,.2f}"],
        ["Zdravotn\u00e9 poistenie (zamestnanec)", f"{settlement.total_zp_employee:,.2f}"],
        [
            "\u010ciastkov\u00fd z\u00e1klad dane",
            f"{settlement.annual_partial_tax_base:,.2f}",
        ],
        [
            "N\u010cZD (mesa\u010dne uplatn\u00e9)",
            f"{settlement.nczd_monthly_total:,.2f}",
        ],
        [
            "N\u010cZD (ro\u010dne prepo\u010d\u00edtan\u00e9)",
            f"{settlement.nczd_annual_recalculated:,.2f}",
        ],
        ["Z\u00e1klad dane (ro\u010dny)", f"{settlement.annual_tax_base:,.2f}"],
        ["Da\u0148 19%", f"{settlement.annual_tax_19:,.2f}"],
        ["Da\u0148 25%", f"{settlement.annual_tax_25:,.2f}"],
        [
            "Da\u0148 celkom",
            f"{settlement.annual_tax_total:,.2f}",
        ],
        [
            "Da\u0148ov\u00fd bonus na deti",
            f"{settlement.annual_child_bonus:,.2f}",
        ],
        [
            "Da\u0148 po bonuse",
            f"{settlement.annual_tax_after_bonus:,.2f}",
        ],
        [
            "Preddavky dane (mesa\u010dn\u00e9)",
            f"{settlement.total_monthly_advances:,.2f}",
        ],
        [
            "Vysporiadanie",
            f"{settlement.settlement_amount:,.2f}",
        ],
    ]

    table = Table(data, colWidths=[120 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.97)]),
                # Highlight settlement row
                ("BACKGROUND", (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 10 * mm))

    # Settlement interpretation
    if settlement.settlement_amount > 0:
        interpretation = f"Preplatok dane: {settlement.settlement_amount:,.2f} \u20ac (vr\u00e1ti\u0165 zamestnancovi)"
    elif settlement.settlement_amount < 0:
        interpretation = f"Nedoplatok dane: {abs(settlement.settlement_amount):,.2f} \u20ac (zrazi\u0165 zamestnancovi)"
    else:
        interpretation = "Bez rozdielu — dane s\u00fa vyrovnan\u00e9"

    elements.append(Paragraph(interpretation, normal_style))
    elements.append(Spacer(1, 15 * mm))

    # Signature lines
    elements.append(
        Paragraph(
            f"Po\u010det mesa\u010dn\u00fdch miezd: {settlement.months_count}",
            normal_style,
        )
    )
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph("_" * 40, normal_style))
    elements.append(
        Paragraph(
            "Podpis zamestn\u00e1vate\u013ea a pe\u010diatka",
            normal_style,
        )
    )

    doc.build(elements)
    return buffer.getvalue()


def generate_annual_tax_report_summary(
    db: Session,
    *,
    tenant_id: UUID,
    year: int,
) -> dict:
    """Generate summary data for the annual tax report (Hlásenie o dani).

    Returns a dict with aggregated figures for the annual tax filing.
    Raises ValueError if no settlements exist.
    """
    settlements = get_settlements_for_year(db, tenant_id=tenant_id, year=year)
    if not settlements:
        raise ValueError(f"No annual settlements found for year {year}. Run annual tax settlement calculation first.")

    total_gross = sum(s.total_gross_wage for s in settlements)
    total_advances = sum(s.total_monthly_advances for s in settlements)
    total_annual_tax = sum(s.annual_tax_after_bonus for s in settlements)
    total_settlement = sum(s.settlement_amount for s in settlements)

    return {
        "year": year,
        "tenant_id": tenant_id,
        "total_employees": len(settlements),
        "total_gross_wages": _round(total_gross),
        "total_tax_advances": _round(total_advances),
        "total_annual_tax": _round(total_annual_tax),
        "total_settlement": _round(total_settlement),
        "report_generated": True,
    }
