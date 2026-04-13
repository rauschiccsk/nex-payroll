"""Payroll calculation engine — gross-to-net with Slovak 2026 rates.

Implements the 15-step algorithm from DESIGN.md §4.6.
All functions are synchronous (def, not async def).

Key rates (Slovak 2026):
  SP employee: 9.4% (capped at 16,764 €/month)
  SP employer: 24.7% + 0.8% accident (accident uncapped)
  ZP employee: 5.0% (2.5% disabled) — NO cap
  ZP employer: 11.0% (5.5% disabled) — NO cap
  Tax: 19% / 25% progressive
  NČZD monthly: 497.23 €
  Child bonus: 100€ (<15y), 50€ (15-18y)
"""

from dataclasses import dataclass, field
from datetime import UTC, date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.contribution_rate import ContributionRate
from app.models.employee import Employee
from app.models.employee_child import EmployeeChild
from app.models.payroll import Payroll
from app.models.tax_bracket import TaxBracket

# ---------------------------------------------------------------------------
# Constants — Slovak 2026 fallback rates (used when DB has no data)
# ---------------------------------------------------------------------------

# SP assessment base cap (7× average wage 2026)
SP_ASSESSMENT_BASE_CAP = Decimal("16764.00")

# SP Employee rates
SP_EMP_NEMOCENSKE = Decimal("0.014")
SP_EMP_STAROBNE = Decimal("0.040")
SP_EMP_INVALIDNE = Decimal("0.030")
SP_EMP_NEZAMESTNANOST = Decimal("0.010")

# SP Employer rates
SP_ER_NEMOCENSKE = Decimal("0.014")
SP_ER_STAROBNE = Decimal("0.140")
SP_ER_INVALIDNE = Decimal("0.030")
SP_ER_NEZAMESTNANOST = Decimal("0.010")
SP_ER_GARANCNE = Decimal("0.0025")
SP_ER_REZERVNY = Decimal("0.0475")
SP_ER_KURZARBEIT = Decimal("0.003")
SP_ER_URAZOVE = Decimal("0.008")  # NO cap — applied to full gross

# ZP rates
ZP_EMPLOYEE_STANDARD = Decimal("0.05")
ZP_EMPLOYEE_DISABLED = Decimal("0.025")
ZP_EMPLOYER_STANDARD = Decimal("0.11")
ZP_EMPLOYER_DISABLED = Decimal("0.055")

# Tax 2026
TAX_RATE_19 = Decimal("0.19")
TAX_RATE_25 = Decimal("0.25")
TAX_BRACKET_ANNUAL_THRESHOLD = Decimal("50234.18")

# NČZD 2026
NCZD_MONTHLY = Decimal("497.23")
NCZD_ANNUAL = Decimal("5966.73")
NCZD_REDUCTION_THRESHOLD = Decimal("26367.26")
NCZD_REDUCTION_CONSTANT = Decimal("12558.55")
NCZD_ELIMINATION_THRESHOLD = Decimal("50234.20")

# Child tax bonus 2026
CHILD_BONUS_UNDER_15 = Decimal("100.00")
CHILD_BONUS_15_TO_18 = Decimal("50.00")

# Child bonus percentage limits by number of children (1-6+)
CHILD_BONUS_PERCENTAGE_LIMITS = [
    Decimal("0.29"),  # 1 child
    Decimal("0.36"),  # 2 children
    Decimal("0.43"),  # 3 children
    Decimal("0.50"),  # 4 children
    Decimal("0.57"),  # 5 children
    Decimal("0.64"),  # 6+ children
]

# Pillar 2 rate
PILLAR2_RATE = Decimal("0.04")

# Rounding precision
TWO_PLACES = Decimal("0.01")


def _r(value: Decimal) -> Decimal:
    """Round to 2 decimal places using ROUND_HALF_UP (Slovak standard)."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Rate snapshot — loaded from DB or fallback constants
# ---------------------------------------------------------------------------


@dataclass
class RatesSnapshot:
    """Snapshot of all contribution/tax rates for a given period."""

    # SP caps
    sp_assessment_base_cap: Decimal = SP_ASSESSMENT_BASE_CAP

    # SP Employee
    sp_emp_nemocenske: Decimal = SP_EMP_NEMOCENSKE
    sp_emp_starobne: Decimal = SP_EMP_STAROBNE
    sp_emp_invalidne: Decimal = SP_EMP_INVALIDNE
    sp_emp_nezamestnanost: Decimal = SP_EMP_NEZAMESTNANOST

    # SP Employer
    sp_er_nemocenske: Decimal = SP_ER_NEMOCENSKE
    sp_er_starobne: Decimal = SP_ER_STAROBNE
    sp_er_invalidne: Decimal = SP_ER_INVALIDNE
    sp_er_nezamestnanost: Decimal = SP_ER_NEZAMESTNANOST
    sp_er_garancne: Decimal = SP_ER_GARANCNE
    sp_er_rezervny: Decimal = SP_ER_REZERVNY
    sp_er_kurzarbeit: Decimal = SP_ER_KURZARBEIT
    sp_er_urazove: Decimal = SP_ER_URAZOVE

    # ZP
    zp_employee_standard: Decimal = ZP_EMPLOYEE_STANDARD
    zp_employee_disabled: Decimal = ZP_EMPLOYEE_DISABLED
    zp_employer_standard: Decimal = ZP_EMPLOYER_STANDARD
    zp_employer_disabled: Decimal = ZP_EMPLOYER_DISABLED

    # Tax
    tax_rate_19: Decimal = TAX_RATE_19
    tax_rate_25: Decimal = TAX_RATE_25
    tax_bracket_annual_threshold: Decimal = TAX_BRACKET_ANNUAL_THRESHOLD

    # NČZD
    nczd_monthly: Decimal = NCZD_MONTHLY
    nczd_annual: Decimal = NCZD_ANNUAL
    nczd_reduction_threshold: Decimal = NCZD_REDUCTION_THRESHOLD
    nczd_reduction_constant: Decimal = NCZD_REDUCTION_CONSTANT
    nczd_elimination_threshold: Decimal = NCZD_ELIMINATION_THRESHOLD

    # Child bonus
    child_bonus_under_15: Decimal = CHILD_BONUS_UNDER_15
    child_bonus_15_to_18: Decimal = CHILD_BONUS_15_TO_18

    # Pillar 2
    pillar2_rate: Decimal = PILLAR2_RATE


@dataclass
class ChildBonusInfo:
    """Info about a single child's tax bonus."""

    child_id: UUID
    child_name: str
    age: int
    bonus_amount: Decimal


@dataclass
class CalculationResult:
    """Complete payroll calculation result."""

    # Gross
    base_wage: Decimal = Decimal("0")
    overtime_hours: Decimal = Decimal("0")
    overtime_amount: Decimal = Decimal("0")
    bonus_amount: Decimal = Decimal("0")
    supplement_amount: Decimal = Decimal("0")
    gross_wage: Decimal = Decimal("0")

    # SP Employee
    sp_assessment_base: Decimal = Decimal("0")
    sp_nemocenske: Decimal = Decimal("0")
    sp_starobne: Decimal = Decimal("0")
    sp_invalidne: Decimal = Decimal("0")
    sp_nezamestnanost: Decimal = Decimal("0")
    sp_employee_total: Decimal = Decimal("0")

    # ZP Employee
    zp_assessment_base: Decimal = Decimal("0")
    zp_employee: Decimal = Decimal("0")

    # Tax
    partial_tax_base: Decimal = Decimal("0")
    nczd_applied: Decimal = Decimal("0")
    tax_base: Decimal = Decimal("0")
    tax_advance: Decimal = Decimal("0")
    child_bonus: Decimal = Decimal("0")
    child_bonus_details: list[ChildBonusInfo] = field(default_factory=list)
    tax_after_bonus: Decimal = Decimal("0")

    # Net
    net_wage: Decimal = Decimal("0")

    # SP Employer
    sp_employer_nemocenske: Decimal = Decimal("0")
    sp_employer_starobne: Decimal = Decimal("0")
    sp_employer_invalidne: Decimal = Decimal("0")
    sp_employer_nezamestnanost: Decimal = Decimal("0")
    sp_employer_garancne: Decimal = Decimal("0")
    sp_employer_rezervny: Decimal = Decimal("0")
    sp_employer_kurzarbeit: Decimal = Decimal("0")
    sp_employer_urazove: Decimal = Decimal("0")
    sp_employer_total: Decimal = Decimal("0")

    # ZP Employer
    zp_employer: Decimal = Decimal("0")

    # Pillar 2
    pillar2_amount: Decimal = Decimal("0")

    # Total employer cost
    total_employer_cost: Decimal = Decimal("0")

    # Metadata
    period_year: int = 0
    period_month: int = 0
    employee_id: UUID | None = None
    contract_id: UUID | None = None
    effective_date: date | None = None


# ---------------------------------------------------------------------------
# Rate resolution — load from DB
# ---------------------------------------------------------------------------

# Mapping: ContributionRate.rate_type → RatesSnapshot attribute
_RATE_TYPE_MAP = {
    "sp_employee_nemocenske": "sp_emp_nemocenske",
    "sp_employee_starobne": "sp_emp_starobne",
    "sp_employee_invalidne": "sp_emp_invalidne",
    "sp_employee_nezamestnanost": "sp_emp_nezamestnanost",
    "sp_employer_nemocenske": "sp_er_nemocenske",
    "sp_employer_starobne": "sp_er_starobne",
    "sp_employer_invalidne": "sp_er_invalidne",
    "sp_employer_nezamestnanost": "sp_er_nezamestnanost",
    "sp_employer_garancne": "sp_er_garancne",
    "sp_employer_rezervny": "sp_er_rezervny",
    "sp_employer_kurzarbeit": "sp_er_kurzarbeit",
    "sp_employer_urazove": "sp_er_urazove",
    "zp_employee": "zp_employee_standard",
    "zp_employee_disabled": "zp_employee_disabled",
    "zp_employer": "zp_employer_standard",
    "zp_employer_disabled": "zp_employer_disabled",
}


def get_rates_for_period(db: Session, year: int, month: int) -> RatesSnapshot:
    """Load contribution/tax rates valid for the given period.

    Falls back to hardcoded 2026 constants if no DB records match.
    """
    effective = date(year, month, 1)
    snapshot = RatesSnapshot()

    # Load contribution rates
    stmt = select(ContributionRate).where(
        ContributionRate.valid_from <= effective,
        or_(
            ContributionRate.valid_to.is_(None),
            ContributionRate.valid_to >= effective,
        ),
    )
    rates = list(db.execute(stmt).scalars().all())

    for rate in rates:
        attr_name = _RATE_TYPE_MAP.get(rate.rate_type)
        if attr_name and hasattr(snapshot, attr_name):
            # Convert percentage to decimal fraction (e.g. 1.4 → 0.014)
            setattr(snapshot, attr_name, rate.rate_percent / Decimal("100"))
        # Update SP assessment base cap from any SP rate that has max_assessment_base
        if rate.max_assessment_base is not None and rate.rate_type.startswith("sp_"):
            snapshot.sp_assessment_base_cap = rate.max_assessment_base

    # Load tax brackets
    tax_stmt = (
        select(TaxBracket)
        .where(
            TaxBracket.valid_from <= effective,
            or_(
                TaxBracket.valid_to.is_(None),
                TaxBracket.valid_to >= effective,
            ),
        )
        .order_by(TaxBracket.bracket_order)
    )
    brackets = list(db.execute(tax_stmt).scalars().all())

    if brackets:
        # First bracket = 19% bracket
        b1 = brackets[0]
        snapshot.tax_rate_19 = b1.rate_percent / Decimal("100")
        snapshot.nczd_monthly = b1.nczd_monthly
        snapshot.nczd_annual = b1.nczd_annual
        snapshot.nczd_reduction_threshold = b1.nczd_reduction_threshold

        if b1.max_amount is not None:
            snapshot.tax_bracket_annual_threshold = b1.max_amount

        # Second bracket = 25% bracket
        if len(brackets) > 1:
            b2 = brackets[1]
            snapshot.tax_rate_25 = b2.rate_percent / Decimal("100")

    return snapshot


# ---------------------------------------------------------------------------
# Year-to-date income calculation
# ---------------------------------------------------------------------------


def _get_year_to_date_gross(
    db: Session,
    employee_id: UUID,
    tenant_id: UUID,
    year: int,
    current_month: int,
) -> Decimal:
    """Sum gross_wage for all calculated/approved/paid payrolls in *year* before *current_month*."""
    stmt = select(Payroll.gross_wage).where(
        Payroll.employee_id == employee_id,
        Payroll.tenant_id == tenant_id,
        Payroll.period_year == year,
        Payroll.period_month < current_month,
        Payroll.status.in_(["calculated", "approved", "paid"]),
    )
    rows = db.execute(stmt).scalars().all()
    return sum(rows, Decimal("0"))


# ---------------------------------------------------------------------------
# Child age helper
# ---------------------------------------------------------------------------


def _child_age_at_period(birth_date: date, period_year: int, period_month: int) -> int:
    """Calculate child's age in completed years at the END of the payroll period.

    We use the last day of the period month for age determination.
    """
    # Last day of period month
    if period_month == 12:
        period_end = date(period_year, 12, 31)
    else:
        period_end = date(period_year, period_month + 1, 1).replace(day=1)
        # Go to first day of next month, subtract 1 day
        period_end = date(period_year, period_month + 1, 1)
        from datetime import timedelta

        period_end = period_end - timedelta(days=1)

    age = period_end.year - birth_date.year
    if (period_end.month, period_end.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


# ---------------------------------------------------------------------------
# Core calculation — 15-step algorithm
# ---------------------------------------------------------------------------


def calculate_payroll(
    *,
    base_wage: Decimal,
    overtime_hours: Decimal,
    overtime_amount: Decimal,
    bonus_amount: Decimal,
    supplement_amount: Decimal,
    is_disabled: bool,
    nczd_eligible: bool,
    pillar2_saver: bool,
    year_to_date_gross: Decimal,
    children: list[EmployeeChild],
    period_year: int,
    period_month: int,
    rates: RatesSnapshot,
    employee_id: UUID | None = None,
    contract_id: UUID | None = None,
) -> CalculationResult:
    """Execute the 15-step gross-to-net payroll calculation.

    Pure computation — no DB access. All inputs are pre-resolved.
    Uses Slovak 2026 rules from DESIGN.md §4.6.
    """
    result = CalculationResult()
    result.period_year = period_year
    result.period_month = period_month
    result.employee_id = employee_id
    result.contract_id = contract_id
    result.effective_date = date(period_year, period_month, 1)

    # -----------------------------------------------------------------------
    # Step 1: HRUBÁ MZDA (gross wage)
    # -----------------------------------------------------------------------
    result.base_wage = _r(base_wage)
    result.overtime_hours = overtime_hours
    result.overtime_amount = _r(overtime_amount)
    result.bonus_amount = _r(bonus_amount)
    result.supplement_amount = _r(supplement_amount)
    result.gross_wage = _r(base_wage + overtime_amount + bonus_amount + supplement_amount)

    gross = result.gross_wage

    # -----------------------------------------------------------------------
    # Step 2: VYMERIAVACÍ ZÁKLAD SP (SP assessment base)
    # -----------------------------------------------------------------------
    result.sp_assessment_base = min(gross, rates.sp_assessment_base_cap)
    sp_base = result.sp_assessment_base

    # -----------------------------------------------------------------------
    # Step 3: SP ZAMESTNANEC (employee social insurance — 9.4%)
    # -----------------------------------------------------------------------
    result.sp_nemocenske = _r(sp_base * rates.sp_emp_nemocenske)
    result.sp_starobne = _r(sp_base * rates.sp_emp_starobne)
    result.sp_invalidne = _r(sp_base * rates.sp_emp_invalidne)
    result.sp_nezamestnanost = _r(sp_base * rates.sp_emp_nezamestnanost)
    result.sp_employee_total = _r(
        result.sp_nemocenske + result.sp_starobne + result.sp_invalidne + result.sp_nezamestnanost
    )

    # -----------------------------------------------------------------------
    # Step 4: ZP ZAMESTNANEC (employee health insurance — NO cap)
    # -----------------------------------------------------------------------
    result.zp_assessment_base = gross  # ZP has NO cap
    zp_rate = rates.zp_employee_disabled if is_disabled else rates.zp_employee_standard
    result.zp_employee = _r(gross * zp_rate)

    # -----------------------------------------------------------------------
    # Step 5: ČIASTKOVÝ ZÁKLAD DANE (partial tax base)
    # -----------------------------------------------------------------------
    result.partial_tax_base = _r(gross - result.sp_employee_total - result.zp_employee)

    # -----------------------------------------------------------------------
    # Step 6: NČZD APLIKÁCIA (non-taxable amount)
    # -----------------------------------------------------------------------
    if nczd_eligible:
        # Year-to-date cumulative income (all months up to and including current)
        ytd_income = year_to_date_gross + gross

        if ytd_income <= rates.nczd_reduction_threshold:
            # Full NČZD — cumulative income below reduction threshold
            result.nczd_applied = rates.nczd_monthly
        elif ytd_income <= rates.nczd_elimination_threshold:
            # Reduced NČZD — compute annual formula, derive monthly
            annual_nczd = max(
                Decimal("0"),
                _r(rates.nczd_reduction_constant - ytd_income / 4),
            )
            result.nczd_applied = _r(annual_nczd / 12)
        else:
            # Eliminated — cumulative income too high
            result.nczd_applied = Decimal("0")
    else:
        result.nczd_applied = Decimal("0")

    # -----------------------------------------------------------------------
    # Step 7: ZÁKLAD DANE (tax base)
    # -----------------------------------------------------------------------
    result.tax_base = max(Decimal("0"), _r(result.partial_tax_base - result.nczd_applied))

    # -----------------------------------------------------------------------
    # Step 8: DAŇ PRED BONUSOM (tax advance)
    # -----------------------------------------------------------------------
    # Monthly threshold = annual threshold / 12
    monthly_threshold = _r(rates.tax_bracket_annual_threshold / 12)

    if result.tax_base <= monthly_threshold:
        result.tax_advance = _r(result.tax_base * rates.tax_rate_19)
    else:
        # Progressive: 19% on amount up to threshold, 25% on amount above
        tax_19_part = _r(monthly_threshold * rates.tax_rate_19)
        tax_25_part = _r((result.tax_base - monthly_threshold) * rates.tax_rate_25)
        result.tax_advance = _r(tax_19_part + tax_25_part)

    # -----------------------------------------------------------------------
    # Step 9: DAŇOVÝ BONUS (child tax bonus)
    # -----------------------------------------------------------------------
    eligible_children: list[ChildBonusInfo] = []

    for child in children:
        if not child.is_tax_bonus_eligible:
            continue

        # Check custody period
        period_start = date(period_year, period_month, 1)
        if child.custody_to is not None and child.custody_to < period_start:
            continue
        if child.custody_from is not None and child.custody_from > period_start:
            continue

        age = _child_age_at_period(child.birth_date, period_year, period_month)

        if age < 0 or age >= 18:
            continue

        bonus = rates.child_bonus_under_15 if age < 15 else rates.child_bonus_15_to_18

        eligible_children.append(
            ChildBonusInfo(
                child_id=child.id,
                child_name=f"{child.first_name} {child.last_name}",
                age=age,
                bonus_amount=bonus,
            )
        )

    if eligible_children:
        total_bonus = sum(c.bonus_amount for c in eligible_children)
        child_count = len(eligible_children)

        # Percentage limit based on number of children
        limit_idx = min(child_count - 1, len(CHILD_BONUS_PERCENTAGE_LIMITS) - 1)
        percentage_limit = CHILD_BONUS_PERCENTAGE_LIMITS[limit_idx]
        max_bonus = _r(result.partial_tax_base * percentage_limit)

        result.child_bonus = min(total_bonus, max(Decimal("0"), max_bonus))
        result.child_bonus_details = eligible_children
    else:
        result.child_bonus = Decimal("0")

    # -----------------------------------------------------------------------
    # Step 10: DAŇ PO BONUSE (tax after bonus)
    # -----------------------------------------------------------------------
    result.tax_after_bonus = max(Decimal("0"), _r(result.tax_advance - result.child_bonus))

    # -----------------------------------------------------------------------
    # Step 11: ČISTÁ MZDA (net wage)
    # -----------------------------------------------------------------------
    result.net_wage = _r(gross - result.sp_employee_total - result.zp_employee - result.tax_after_bonus)

    # -----------------------------------------------------------------------
    # Step 12: SP ZAMESTNÁVATEĽ (employer social insurance — 24.7% + 0.8%)
    # -----------------------------------------------------------------------
    sp_er_base = min(gross, rates.sp_assessment_base_cap)

    result.sp_employer_nemocenske = _r(sp_er_base * rates.sp_er_nemocenske)
    result.sp_employer_starobne = _r(sp_er_base * rates.sp_er_starobne)
    result.sp_employer_invalidne = _r(sp_er_base * rates.sp_er_invalidne)
    result.sp_employer_nezamestnanost = _r(sp_er_base * rates.sp_er_nezamestnanost)
    result.sp_employer_garancne = _r(sp_er_base * rates.sp_er_garancne)
    result.sp_employer_rezervny = _r(sp_er_base * rates.sp_er_rezervny)
    result.sp_employer_kurzarbeit = _r(sp_er_base * rates.sp_er_kurzarbeit)

    # Accident insurance (úrazové) — NO CAP, applied to full gross
    result.sp_employer_urazove = _r(gross * rates.sp_er_urazove)

    # SP employer total = capped components + uncapped accident
    sp_er_capped_total = _r(
        result.sp_employer_nemocenske
        + result.sp_employer_starobne
        + result.sp_employer_invalidne
        + result.sp_employer_nezamestnanost
        + result.sp_employer_garancne
        + result.sp_employer_rezervny
        + result.sp_employer_kurzarbeit
    )
    result.sp_employer_total = _r(sp_er_capped_total + result.sp_employer_urazove)

    # -----------------------------------------------------------------------
    # Step 13: ZP ZAMESTNÁVATEĽ (employer health insurance — NO cap)
    # -----------------------------------------------------------------------
    zp_er_rate = rates.zp_employer_disabled if is_disabled else rates.zp_employer_standard
    result.zp_employer = _r(gross * zp_er_rate)

    # -----------------------------------------------------------------------
    # Step 14: II. PILIER (2nd pillar pension)
    # -----------------------------------------------------------------------
    if pillar2_saver:
        result.pillar2_amount = _r(result.sp_assessment_base * rates.pillar2_rate)
    else:
        result.pillar2_amount = Decimal("0")

    # -----------------------------------------------------------------------
    # Step 15: CELKOVÝ NÁKLAD ZAMESTNÁVATEĽA (total employer cost)
    # -----------------------------------------------------------------------
    result.total_employer_cost = _r(gross + result.sp_employer_total + result.zp_employer)

    return result


# ---------------------------------------------------------------------------
# High-level entry point — resolves employee/contract/rates from DB
# ---------------------------------------------------------------------------


def calculate_employee_payroll(
    db: Session,
    *,
    tenant_id: UUID,
    employee_id: UUID,
    contract_id: UUID,
    period_year: int,
    period_month: int,
    overtime_hours: Decimal = Decimal("0"),
    overtime_amount: Decimal = Decimal("0"),
    bonus_amount: Decimal = Decimal("0"),
    supplement_amount: Decimal = Decimal("0"),
) -> CalculationResult:
    """Full payroll calculation with DB lookups.

    Resolves employee, contract, children, rates, and YTD income
    from DB, then delegates to ``calculate_payroll()``.

    Raises ``ValueError`` if employee/contract not found or
    contract does not belong to employee.
    """
    # Validate employee
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise ValueError(f"Employee with id={employee_id} not found")
    if employee.tenant_id != tenant_id:
        raise ValueError(f"Employee {employee_id} does not belong to tenant {tenant_id}")
    if employee.status != "active":
        raise ValueError(f"Employee {employee_id} is not active (status={employee.status})")

    # Validate contract
    from app.models.contract import Contract

    contract = db.get(Contract, contract_id)
    if contract is None:
        raise ValueError(f"Contract with id={contract_id} not found")
    if contract.employee_id != employee_id:
        raise ValueError(f"Contract {contract_id} does not belong to employee {employee_id}")
    if not contract.is_current:
        raise ValueError(f"Contract {contract_id} is not current")

    # Check for existing payroll (draft can be overwritten)
    existing_stmt = select(Payroll).where(
        Payroll.tenant_id == tenant_id,
        Payroll.employee_id == employee_id,
        Payroll.period_year == period_year,
        Payroll.period_month == period_month,
    )
    existing = db.execute(existing_stmt).scalar_one_or_none()
    if existing is not None and existing.status != "draft":
        raise ValueError(
            f"Payroll for {period_year}/{period_month} already exists "
            f"with status={existing.status!r}. Only draft payrolls can be recalculated."
        )

    # Load children for tax bonus
    children_stmt = select(EmployeeChild).where(
        EmployeeChild.employee_id == employee_id,
        EmployeeChild.tenant_id == tenant_id,
    )
    children = list(db.execute(children_stmt).scalars().all())

    # Load rates
    rates = get_rates_for_period(db, period_year, period_month)

    # Year-to-date gross
    ytd_gross = _get_year_to_date_gross(db, employee_id, tenant_id, period_year, period_month)

    # Execute calculation
    result = calculate_payroll(
        base_wage=contract.base_wage,
        overtime_hours=overtime_hours,
        overtime_amount=overtime_amount,
        bonus_amount=bonus_amount,
        supplement_amount=supplement_amount,
        is_disabled=employee.is_disabled,
        nczd_eligible=employee.nczd_applied,
        pillar2_saver=employee.pillar2_saver,
        year_to_date_gross=ytd_gross,
        children=children,
        period_year=period_year,
        period_month=period_month,
        rates=rates,
        employee_id=employee_id,
        contract_id=contract_id,
    )

    return result


# ---------------------------------------------------------------------------
# Persist calculation result to Payroll record
# ---------------------------------------------------------------------------


def persist_calculation(
    db: Session,
    *,
    tenant_id: UUID,
    result: CalculationResult,
) -> Payroll:
    """Create or update a Payroll record from the calculation result.

    If a draft payroll already exists for the same employee/period,
    it is updated. Otherwise, a new record is created.

    Returns the persisted Payroll instance (flushed, not committed).
    """
    from datetime import datetime

    existing_stmt = select(Payroll).where(
        Payroll.tenant_id == tenant_id,
        Payroll.employee_id == result.employee_id,
        Payroll.period_year == result.period_year,
        Payroll.period_month == result.period_month,
    )
    payroll = db.execute(existing_stmt).scalar_one_or_none()

    field_values = {
        "base_wage": result.base_wage,
        "overtime_hours": result.overtime_hours,
        "overtime_amount": result.overtime_amount,
        "bonus_amount": result.bonus_amount,
        "supplement_amount": result.supplement_amount,
        "gross_wage": result.gross_wage,
        "sp_assessment_base": result.sp_assessment_base,
        "sp_nemocenske": result.sp_nemocenske,
        "sp_starobne": result.sp_starobne,
        "sp_invalidne": result.sp_invalidne,
        "sp_nezamestnanost": result.sp_nezamestnanost,
        "sp_employee_total": result.sp_employee_total,
        "zp_assessment_base": result.zp_assessment_base,
        "zp_employee": result.zp_employee,
        "partial_tax_base": result.partial_tax_base,
        "nczd_applied": result.nczd_applied,
        "tax_base": result.tax_base,
        "tax_advance": result.tax_advance,
        "child_bonus": result.child_bonus,
        "tax_after_bonus": result.tax_after_bonus,
        "net_wage": result.net_wage,
        "sp_employer_nemocenske": result.sp_employer_nemocenske,
        "sp_employer_starobne": result.sp_employer_starobne,
        "sp_employer_invalidne": result.sp_employer_invalidne,
        "sp_employer_nezamestnanost": result.sp_employer_nezamestnanost,
        "sp_employer_garancne": result.sp_employer_garancne,
        "sp_employer_rezervny": result.sp_employer_rezervny,
        "sp_employer_kurzarbeit": result.sp_employer_kurzarbeit,
        "sp_employer_urazove": result.sp_employer_urazove,
        "sp_employer_total": result.sp_employer_total,
        "zp_employer": result.zp_employer,
        "pillar2_amount": result.pillar2_amount,
        "total_employer_cost": result.total_employer_cost,
        "status": "calculated",
        "calculated_at": datetime.now(UTC),
    }

    if payroll is not None:
        # Update existing draft
        for field_name, value in field_values.items():
            setattr(payroll, field_name, value)
    else:
        # Create new record
        payroll = Payroll(
            tenant_id=tenant_id,
            employee_id=result.employee_id,
            contract_id=result.contract_id,
            period_year=result.period_year,
            period_month=result.period_month,
            **field_values,
        )
        db.add(payroll)

    db.flush()
    return payroll
