"""Tests for the payroll calculation engine (R-03).

Covers the 15-step gross-to-net algorithm with Slovak 2026 rates:
  - Standard employee (no disability, NČZD applied, no children)
  - Employee with children (tax bonus)
  - Disabled employee (reduced ZP rates)
  - High earner (SP cap, 25% tax bracket, NČZD reduction)
  - Pillar 2 saver
  - Edge cases (zero gross, overtime, supplements)
  - Rate resolution from DB
  - Year-to-date income aggregation
  - Validation errors (missing employee, inactive, wrong tenant)
  - Identity assertion: gross = net + SP + ZP + tax
"""

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.employee import Employee
from app.models.employee_child import EmployeeChild
from app.services.calculation_engine import (
    CHILD_BONUS_15_TO_18,
    CHILD_BONUS_UNDER_15,
    NCZD_MONTHLY,
    SP_ASSESSMENT_BASE_CAP,
    CalculationResult,
    RatesSnapshot,
    _child_age_at_period,
    _r,
    calculate_employee_payroll,
    calculate_payroll,
    get_rates_for_period,
    persist_calculation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_rates() -> RatesSnapshot:
    """Return default 2026 rates snapshot."""
    return RatesSnapshot()


def _make_child(
    *,
    birth_date: date,
    eligible: bool = True,
    custody_from: date | None = None,
    custody_to: date | None = None,
    first_name: str = "Child",
    last_name: str = "Test",
):
    """Create a mock child object (SimpleNamespace, not persisted to DB).

    Uses SimpleNamespace to avoid SQLAlchemy instrumentation issues.
    """
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        employee_id=uuid.uuid4(),
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        is_tax_bonus_eligible=eligible,
        custody_from=custody_from,
        custody_to=custody_to,
    )


def _assert_identity(result: CalculationResult) -> None:
    """Assert the fundamental identity: gross = net + SP + ZP + tax."""
    lhs = result.gross_wage
    rhs = _r(result.net_wage + result.sp_employee_total + result.zp_employee + result.tax_after_bonus)
    assert lhs == rhs, (
        f"Identity violation: gross_wage={lhs} != "
        f"net_wage({result.net_wage}) + sp({result.sp_employee_total}) "
        f"+ zp({result.zp_employee}) + tax({result.tax_after_bonus}) = {rhs}"
    )


# ---------------------------------------------------------------------------
# Test: Rounding helper
# ---------------------------------------------------------------------------


class TestRounding:
    """Test the _r() rounding function."""

    def test_round_half_up(self):
        assert _r(Decimal("1.005")) == Decimal("1.01")
        assert _r(Decimal("1.004")) == Decimal("1.00")

    def test_round_exact(self):
        assert _r(Decimal("100.00")) == Decimal("100.00")

    def test_round_negative(self):
        assert _r(Decimal("-1.005")) == Decimal("-1.01")


# ---------------------------------------------------------------------------
# Test: Child age calculation
# ---------------------------------------------------------------------------


class TestChildAge:
    """Test _child_age_at_period helper."""

    def test_child_under_15(self):
        # Child born 2015-06-15, period 2026/01 → age 10
        assert _child_age_at_period(date(2015, 6, 15), 2026, 1) == 10

    def test_child_exactly_15(self):
        # Child born 2011-01-01, period 2026/01 → age 15 (turned 15 on Jan 1)
        assert _child_age_at_period(date(2011, 1, 1), 2026, 1) == 15

    def test_child_turning_15_in_month(self):
        # Child born 2011-01-20, period 2026/01 → age 15 (turns 15 on Jan 20, end of month Jan 31)
        assert _child_age_at_period(date(2011, 1, 20), 2026, 1) == 15

    def test_child_turning_18(self):
        # Child born 2008-06-15, period 2026/06 → age 18
        assert _child_age_at_period(date(2008, 6, 15), 2026, 6) == 18

    def test_child_born_december(self):
        # Child born 2020-12-31, period 2026/12 → age 6
        assert _child_age_at_period(date(2020, 12, 31), 2026, 12) == 6

    def test_child_not_yet_born(self):
        # Child born 2027-01-01, period 2026/12 → age -1
        assert _child_age_at_period(date(2027, 1, 1), 2026, 12) == -1


# ---------------------------------------------------------------------------
# Test: Standard employee — basic gross-to-net
# ---------------------------------------------------------------------------


class TestStandardEmployee:
    """Test payroll calculation for a standard employee.

    Scenario: base_wage=2000€, no overtime/bonus, NČZD applied, no children,
    not disabled, not pillar2 saver.
    """

    def test_standard_calculation(self):
        rates = _default_rates()
        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=rates,
        )

        # Step 1: Gross wage
        assert result.gross_wage == Decimal("2000.00")

        # Step 2: SP assessment base (2000 < 16764 cap)
        assert result.sp_assessment_base == Decimal("2000.00")

        # Step 3: SP employee
        assert result.sp_nemocenske == _r(Decimal("2000") * Decimal("0.014"))  # 28.00
        assert result.sp_starobne == _r(Decimal("2000") * Decimal("0.040"))  # 80.00
        assert result.sp_invalidne == _r(Decimal("2000") * Decimal("0.030"))  # 60.00
        assert result.sp_nezamestnanost == _r(Decimal("2000") * Decimal("0.010"))  # 20.00
        assert result.sp_employee_total == Decimal("188.00")  # 9.4%

        # Step 4: ZP employee (no cap)
        assert result.zp_assessment_base == Decimal("2000.00")
        assert result.zp_employee == _r(Decimal("2000") * Decimal("0.05"))  # 100.00

        # Step 5: Partial tax base
        assert result.partial_tax_base == _r(Decimal("2000") - Decimal("188") - Decimal("100"))  # 1712.00

        # Step 6: NČZD applied (low income → full NČZD)
        assert result.nczd_applied == NCZD_MONTHLY  # 497.23

        # Step 7: Tax base
        assert result.tax_base == _r(Decimal("1712.00") - Decimal("497.23"))  # 1214.77

        # Step 8: Tax advance (19% bracket)
        assert result.tax_advance == _r(Decimal("1214.77") * Decimal("0.19"))  # 230.81

        # Step 9-10: No children, no bonus
        assert result.child_bonus == Decimal("0")
        assert result.tax_after_bonus == result.tax_advance

        # Step 11: Net wage
        expected_net = _r(Decimal("2000") - Decimal("188") - Decimal("100") - result.tax_after_bonus)
        assert result.net_wage == expected_net

        # Identity check
        _assert_identity(result)

    def test_employer_contributions(self):
        rates = _default_rates()
        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=rates,
        )

        gross = Decimal("2000.00")

        # SP employer (capped components)
        assert result.sp_employer_nemocenske == _r(gross * Decimal("0.014"))
        assert result.sp_employer_starobne == _r(gross * Decimal("0.140"))
        assert result.sp_employer_invalidne == _r(gross * Decimal("0.030"))
        assert result.sp_employer_nezamestnanost == _r(gross * Decimal("0.010"))
        assert result.sp_employer_garancne == _r(gross * Decimal("0.0025"))
        assert result.sp_employer_rezervny == _r(gross * Decimal("0.0475"))
        assert result.sp_employer_kurzarbeit == _r(gross * Decimal("0.003"))

        # Accident insurance (uncapped)
        assert result.sp_employer_urazove == _r(gross * Decimal("0.008"))

        # ZP employer
        assert result.zp_employer == _r(gross * Decimal("0.11"))

        # Total employer cost
        assert result.total_employer_cost == _r(gross + result.sp_employer_total + result.zp_employer)


# ---------------------------------------------------------------------------
# Test: Employee with overtime, bonus, supplements
# ---------------------------------------------------------------------------


class TestGrossComponents:
    """Test gross wage computation with all components."""

    def test_overtime_and_bonus(self):
        result = calculate_payroll(
            base_wage=Decimal("1500.00"),
            overtime_hours=Decimal("10.5"),
            overtime_amount=Decimal("200.00"),
            bonus_amount=Decimal("300.00"),
            supplement_amount=Decimal("50.00"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=3,
            rates=_default_rates(),
        )

        assert result.gross_wage == Decimal("2050.00")
        assert result.overtime_hours == Decimal("10.5")
        _assert_identity(result)

    def test_zero_wage(self):
        """Edge case: zero base wage (e.g. unpaid leave month)."""
        result = calculate_payroll(
            base_wage=Decimal("0"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.gross_wage == Decimal("0")
        assert result.net_wage == Decimal("0")
        assert result.sp_employee_total == Decimal("0")
        assert result.zp_employee == Decimal("0")
        assert result.tax_advance == Decimal("0")


# ---------------------------------------------------------------------------
# Test: SP assessment base cap
# ---------------------------------------------------------------------------


class TestSPCap:
    """Test SP assessment base cap at 16,764 €/month."""

    def test_gross_above_cap(self):
        """Gross > 16764 → SP base capped, ZP uncapped."""
        result = calculate_payroll(
            base_wage=Decimal("20000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        # SP capped at 16764
        assert result.sp_assessment_base == SP_ASSESSMENT_BASE_CAP
        assert result.sp_employee_total == _r(SP_ASSESSMENT_BASE_CAP * Decimal("0.094"))

        # ZP NOT capped — applied to full gross
        assert result.zp_assessment_base == Decimal("20000.00")
        assert result.zp_employee == _r(Decimal("20000") * Decimal("0.05"))

        # Employer accident insurance also uncapped
        assert result.sp_employer_urazove == _r(Decimal("20000") * Decimal("0.008"))

        _assert_identity(result)

    def test_gross_exactly_at_cap(self):
        result = calculate_payroll(
            base_wage=SP_ASSESSMENT_BASE_CAP,
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.sp_assessment_base == SP_ASSESSMENT_BASE_CAP
        _assert_identity(result)


# ---------------------------------------------------------------------------
# Test: Disabled employee
# ---------------------------------------------------------------------------


class TestDisabledEmployee:
    """Test reduced ZP rates for disabled employees."""

    def test_disabled_zp_rates(self):
        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=True,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        # ZP employee: 2.5% instead of 5%
        assert result.zp_employee == _r(Decimal("2000") * Decimal("0.025"))  # 50.00

        # ZP employer: 5.5% instead of 11%
        assert result.zp_employer == _r(Decimal("2000") * Decimal("0.055"))  # 110.00

        _assert_identity(result)


# ---------------------------------------------------------------------------
# Test: NČZD (non-taxable amount)
# ---------------------------------------------------------------------------


class TestNCZD:
    """Test NČZD application rules."""

    def test_nczd_not_eligible(self):
        """Employee does not claim NČZD (secondary employment)."""
        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=False,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.nczd_applied == Decimal("0")
        assert result.tax_base == result.partial_tax_base
        _assert_identity(result)

    def test_nczd_full_amount(self):
        """Low-income employee gets full NČZD."""
        result = calculate_payroll(
            base_wage=Decimal("1000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.nczd_applied == NCZD_MONTHLY
        _assert_identity(result)


# ---------------------------------------------------------------------------
# Test: Child tax bonus
# ---------------------------------------------------------------------------


class TestChildBonus:
    """Test child tax bonus calculation."""

    def test_one_child_under_15(self):
        child = _make_child(birth_date=date(2015, 3, 10))

        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[child],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.child_bonus == CHILD_BONUS_UNDER_15  # 100€
        assert len(result.child_bonus_details) == 1
        assert result.child_bonus_details[0].age == 10
        _assert_identity(result)

    def test_one_child_15_to_18(self):
        child = _make_child(birth_date=date(2009, 6, 15))

        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[child],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.child_bonus == CHILD_BONUS_15_TO_18  # 50€
        assert result.child_bonus_details[0].age == 16
        _assert_identity(result)

    def test_child_over_18_no_bonus(self):
        child = _make_child(birth_date=date(2007, 1, 1))

        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[child],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.child_bonus == Decimal("0")
        assert len(result.child_bonus_details) == 0
        _assert_identity(result)

    def test_multiple_children(self):
        children = [
            _make_child(birth_date=date(2015, 1, 1), first_name="Anna"),  # 11y → 100€
            _make_child(birth_date=date(2010, 6, 1), first_name="Boris"),  # 15y → 50€
            _make_child(birth_date=date(2018, 3, 1), first_name="Cyril"),  # 7y → 100€
        ]

        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=children,
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        # Total: 100 + 50 + 100 = 250€
        # 3 children → 43% limit of partial_tax_base
        max_bonus = _r(result.partial_tax_base * Decimal("0.43"))
        expected = min(Decimal("250"), max_bonus)
        assert result.child_bonus == expected
        assert len(result.child_bonus_details) == 3
        _assert_identity(result)

    def test_child_not_eligible(self):
        child = _make_child(birth_date=date(2015, 1, 1), eligible=False)

        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[child],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.child_bonus == Decimal("0")

    def test_child_custody_ended(self):
        child = _make_child(
            birth_date=date(2015, 1, 1),
            custody_to=date(2025, 12, 31),  # Before period
        )

        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[child],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.child_bonus == Decimal("0")

    def test_child_bonus_percentage_limit(self):
        """Child bonus capped by percentage limit of partial tax base."""
        # Very low wage → partial tax base low → bonus limited
        child = _make_child(birth_date=date(2015, 1, 1))

        result = calculate_payroll(
            base_wage=Decimal("200.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=False,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[child],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        # 1 child → 29% limit
        max_bonus = _r(result.partial_tax_base * Decimal("0.29"))
        # If partial_tax_base * 0.29 < 100, bonus is limited
        assert result.child_bonus == min(Decimal("100"), max(Decimal("0"), max_bonus))
        _assert_identity(result)


# ---------------------------------------------------------------------------
# Test: Pillar 2
# ---------------------------------------------------------------------------


class TestPillar2:
    """Test II. pillar pension saving."""

    def test_pillar2_saver(self):
        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=True,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        # 4% of SP assessment base
        assert result.pillar2_amount == _r(Decimal("2000") * Decimal("0.04"))  # 80.00
        _assert_identity(result)

    def test_not_pillar2_saver(self):
        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        assert result.pillar2_amount == Decimal("0")


# ---------------------------------------------------------------------------
# Test: High earner — progressive tax
# ---------------------------------------------------------------------------


class TestHighEarner:
    """Test progressive tax brackets for high-income employees."""

    def test_25_percent_bracket(self):
        """Gross wage high enough to hit 25% bracket."""
        # Monthly threshold ≈ 50234.18/12 ≈ 4186.18
        result = calculate_payroll(
            base_wage=Decimal("10000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        monthly_threshold = _r(Decimal("50234.18") / 12)

        # Tax base should be above monthly threshold
        if result.tax_base > monthly_threshold:
            # Progressive: 19% on threshold, 25% on excess
            tax_19 = _r(monthly_threshold * Decimal("0.19"))
            tax_25 = _r((result.tax_base - monthly_threshold) * Decimal("0.25"))
            expected_tax = _r(tax_19 + tax_25)
            assert result.tax_advance == expected_tax

        _assert_identity(result)


# ---------------------------------------------------------------------------
# Test: Total employer cost
# ---------------------------------------------------------------------------


class TestEmployerCost:
    """Test total employer cost calculation."""

    def test_total_employer_cost(self):
        result = calculate_payroll(
            base_wage=Decimal("2000.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=_default_rates(),
        )

        expected = _r(result.gross_wage + result.sp_employer_total + result.zp_employer)
        assert result.total_employer_cost == expected


# ---------------------------------------------------------------------------
# Test: Rate resolution
# ---------------------------------------------------------------------------


class TestRateResolution:
    """Test get_rates_for_period with DB data."""

    def test_fallback_rates(self, db_session):
        """When no rates in DB, returns hardcoded 2026 defaults."""
        rates = get_rates_for_period(db_session, 2026, 1)

        assert rates.sp_emp_nemocenske == Decimal("0.014")
        assert rates.sp_emp_starobne == Decimal("0.040")
        assert rates.sp_assessment_base_cap == Decimal("16764.00")
        assert rates.zp_employee_standard == Decimal("0.05")
        assert rates.tax_rate_19 == Decimal("0.19")
        assert rates.nczd_monthly == Decimal("497.23")

    def test_rates_loaded_from_db(self, db_session):
        """Rates loaded from contribution_rates table override defaults."""
        from app.models.contribution_rate import ContributionRate

        # Insert a custom rate
        custom_rate = ContributionRate(
            rate_type="sp_employee_nemocenske",
            rate_percent=Decimal("1.5000"),  # 1.5% instead of 1.4%
            max_assessment_base=Decimal("17000.00"),
            payer="employee",
            fund="nemocenske",
            valid_from=date(2026, 1, 1),
            valid_to=None,
        )
        db_session.add(custom_rate)
        db_session.flush()

        rates = get_rates_for_period(db_session, 2026, 6)

        assert rates.sp_emp_nemocenske == Decimal("0.015")  # Loaded from DB
        assert rates.sp_assessment_base_cap == Decimal("17000.00")


# ---------------------------------------------------------------------------
# Test: DB integration — calculate_employee_payroll
# ---------------------------------------------------------------------------


class TestCalculateEmployeePayroll:
    """Integration tests using DB fixtures."""

    def _create_tenant(self, db_session):
        from app.models.tenant import Tenant

        tenant = Tenant(
            name="Test Company",
            ico="12345678",
            dic="2012345678",
            address_street="Test 1",
            address_city="Bratislava",
            address_zip="81101",
            address_country="SK",
            bank_iban="SK0000000000000000001",
            schema_name="test_calc",
        )
        db_session.add(tenant)
        db_session.flush()
        return tenant

    def _create_employee(self, db_session, tenant, *, is_disabled=False, nczd=True, pillar2=False):
        from app.models.health_insurer import HealthInsurer

        hi = HealthInsurer(
            code="25",
            name="VšZP",
            iban="SK0000000000000000025",
        )
        db_session.add(hi)
        db_session.flush()

        employee = Employee(
            tenant_id=tenant.id,
            employee_number="EMP001",
            first_name="Ján",
            last_name="Testovací",
            birth_date=date(1990, 5, 15),
            birth_number="9005151234",
            gender="M",
            address_street="Testová 1",
            address_city="Bratislava",
            address_zip="81101",
            bank_iban="SK3100000000000000001",
            health_insurer_id=hi.id,
            tax_declaration_type="standard",
            nczd_applied=nczd,
            pillar2_saver=pillar2,
            is_disabled=is_disabled,
            hire_date=date(2020, 1, 1),
            status="active",
        )
        db_session.add(employee)
        db_session.flush()
        return employee

    def _create_contract(self, db_session, tenant, employee, *, base_wage=Decimal("2000.00")):
        from app.models.contract import Contract

        contract = Contract(
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_number="PP-001",
            contract_type="permanent",
            job_title="Developer",
            wage_type="monthly",
            base_wage=base_wage,
            start_date=date(2020, 1, 1),
            is_current=True,
        )
        db_session.add(contract)
        db_session.flush()
        return contract

    def test_full_calculation(self, db_session):
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant)
        contract = self._create_contract(db_session, tenant, employee)

        result = calculate_employee_payroll(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=1,
        )

        assert result.gross_wage == Decimal("2000.00")
        assert result.employee_id == employee.id
        assert result.contract_id == contract.id
        _assert_identity(result)

    def test_persist_calculation(self, db_session):
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant)
        contract = self._create_contract(db_session, tenant, employee)

        result = calculate_employee_payroll(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=3,
        )

        payroll = persist_calculation(db_session, tenant_id=tenant.id, result=result)

        assert payroll.status == "calculated"
        assert payroll.gross_wage == result.gross_wage
        assert payroll.net_wage == result.net_wage
        assert payroll.calculated_at is not None

    def test_employee_not_found(self, db_session):
        fake_tenant = uuid.uuid4()
        fake_employee = uuid.uuid4()
        fake_contract = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            calculate_employee_payroll(
                db_session,
                tenant_id=fake_tenant,
                employee_id=fake_employee,
                contract_id=fake_contract,
                period_year=2026,
                period_month=1,
            )

    def test_wrong_tenant(self, db_session):
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant)
        contract = self._create_contract(db_session, tenant, employee)

        wrong_tenant = uuid.uuid4()

        with pytest.raises(ValueError, match="does not belong to tenant"):
            calculate_employee_payroll(
                db_session,
                tenant_id=wrong_tenant,
                employee_id=employee.id,
                contract_id=contract.id,
                period_year=2026,
                period_month=1,
            )

    def test_inactive_employee(self, db_session):
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant)
        contract = self._create_contract(db_session, tenant, employee)

        employee.status = "terminated"
        db_session.flush()

        with pytest.raises(ValueError, match="not active"):
            calculate_employee_payroll(
                db_session,
                tenant_id=tenant.id,
                employee_id=employee.id,
                contract_id=contract.id,
                period_year=2026,
                period_month=1,
            )

    def test_contract_not_current(self, db_session):
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant)
        contract = self._create_contract(db_session, tenant, employee)

        contract.is_current = False
        db_session.flush()

        with pytest.raises(ValueError, match="not current"):
            calculate_employee_payroll(
                db_session,
                tenant_id=tenant.id,
                employee_id=employee.id,
                contract_id=contract.id,
                period_year=2026,
                period_month=1,
            )

    def test_with_children(self, db_session):
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant)
        contract = self._create_contract(db_session, tenant, employee)

        child = EmployeeChild(
            tenant_id=tenant.id,
            employee_id=employee.id,
            first_name="Marek",
            last_name="Testovací",
            birth_date=date(2016, 5, 10),
            is_tax_bonus_eligible=True,
        )
        db_session.add(child)
        db_session.flush()

        result = calculate_employee_payroll(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=1,
        )

        assert result.child_bonus == CHILD_BONUS_UNDER_15  # 100€ (child age ~10)
        assert len(result.child_bonus_details) == 1
        _assert_identity(result)

    def test_disabled_employee_db(self, db_session):
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant, is_disabled=True)
        contract = self._create_contract(db_session, tenant, employee)

        result = calculate_employee_payroll(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=1,
        )

        # Disabled gets 2.5% ZP
        assert result.zp_employee == _r(Decimal("2000") * Decimal("0.025"))
        assert result.zp_employer == _r(Decimal("2000") * Decimal("0.055"))
        _assert_identity(result)

    def test_pillar2_saver_db(self, db_session):
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant, pillar2=True)
        contract = self._create_contract(db_session, tenant, employee)

        result = calculate_employee_payroll(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=1,
        )

        assert result.pillar2_amount == _r(Decimal("2000") * Decimal("0.04"))
        _assert_identity(result)

    def test_recalculate_overwrites_draft(self, db_session):
        """Recalculating overwrites an existing draft payroll."""
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant)
        contract = self._create_contract(db_session, tenant, employee)

        # First calculation
        result1 = calculate_employee_payroll(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=2,
        )
        payroll1 = persist_calculation(db_session, tenant_id=tenant.id, result=result1)
        payroll1_id = payroll1.id

        # Set back to draft for recalculation
        payroll1.status = "draft"
        db_session.flush()

        # Recalculate with bonus
        result2 = calculate_employee_payroll(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=2,
            bonus_amount=Decimal("500.00"),
        )
        payroll2 = persist_calculation(db_session, tenant_id=tenant.id, result=result2)

        # Same payroll record updated
        assert payroll2.id == payroll1_id
        assert payroll2.gross_wage == Decimal("2500.00")
        assert payroll2.status == "calculated"

    def test_cannot_recalculate_approved(self, db_session):
        """Cannot recalculate an already approved payroll."""
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant)
        contract = self._create_contract(db_session, tenant, employee)

        # Create and persist first calculation
        result = calculate_employee_payroll(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=4,
        )
        payroll = persist_calculation(db_session, tenant_id=tenant.id, result=result)

        # Mark as approved
        payroll.status = "approved"
        db_session.flush()

        with pytest.raises(ValueError, match="Only draft payrolls can be recalculated"):
            calculate_employee_payroll(
                db_session,
                tenant_id=tenant.id,
                employee_id=employee.id,
                contract_id=contract.id,
                period_year=2026,
                period_month=4,
            )

    def test_with_overtime(self, db_session):
        """Test calculation with overtime and bonus amounts."""
        tenant = self._create_tenant(db_session)
        employee = self._create_employee(db_session, tenant)
        contract = self._create_contract(db_session, tenant, employee)

        result = calculate_employee_payroll(
            db_session,
            tenant_id=tenant.id,
            employee_id=employee.id,
            contract_id=contract.id,
            period_year=2026,
            period_month=1,
            overtime_hours=Decimal("10"),
            overtime_amount=Decimal("200.00"),
            bonus_amount=Decimal("300.00"),
            supplement_amount=Decimal("50.00"),
        )

        assert result.gross_wage == Decimal("2550.00")  # 2000 + 200 + 300 + 50
        assert result.overtime_hours == Decimal("10")
        _assert_identity(result)


# ---------------------------------------------------------------------------
# Test: Comprehensive payslip example (manual verification)
# ---------------------------------------------------------------------------


class TestComprehensiveExample:
    """Manually verify a complete calculation for a typical Slovak employee.

    Employee: base 2500€, no children, NČZD applied, standard, Jan 2026.
    """

    def test_comprehensive_2500_eur(self):
        rates = _default_rates()
        result = calculate_payroll(
            base_wage=Decimal("2500.00"),
            overtime_hours=Decimal("0"),
            overtime_amount=Decimal("0"),
            bonus_amount=Decimal("0"),
            supplement_amount=Decimal("0"),
            is_disabled=False,
            nczd_eligible=True,
            pillar2_saver=False,
            year_to_date_gross=Decimal("0"),
            children=[],
            period_year=2026,
            period_month=1,
            rates=rates,
        )

        # Manual computation:
        # Gross: 2500.00
        assert result.gross_wage == Decimal("2500.00")

        # SP employee (9.4% of 2500):
        # nemocenske: 2500 * 0.014 = 35.00
        # starobne: 2500 * 0.040 = 100.00
        # invalidne: 2500 * 0.030 = 75.00
        # nezamestnanost: 2500 * 0.010 = 25.00
        # total: 235.00
        assert result.sp_nemocenske == Decimal("35.00")
        assert result.sp_starobne == Decimal("100.00")
        assert result.sp_invalidne == Decimal("75.00")
        assert result.sp_nezamestnanost == Decimal("25.00")
        assert result.sp_employee_total == Decimal("235.00")

        # ZP employee: 2500 * 0.05 = 125.00
        assert result.zp_employee == Decimal("125.00")

        # Partial tax base: 2500 - 235 - 125 = 2140.00
        assert result.partial_tax_base == Decimal("2140.00")

        # NČZD: 497.23 (full, low income)
        assert result.nczd_applied == Decimal("497.23")

        # Tax base: 2140.00 - 497.23 = 1642.77
        assert result.tax_base == Decimal("1642.77")

        # Tax advance: 1642.77 * 0.19 = 312.13
        assert result.tax_advance == _r(Decimal("1642.77") * Decimal("0.19"))

        # No children → tax_after_bonus = tax_advance
        assert result.tax_after_bonus == result.tax_advance

        # Net: 2500 - 235 - 125 - tax_after_bonus
        assert result.net_wage == _r(Decimal("2500") - Decimal("235") - Decimal("125") - result.tax_after_bonus)

        # SP employer:
        # nemocenske: 2500*0.014=35.00, starobne: 2500*0.14=350.00
        # invalidne: 2500*0.03=75.00, nezamestnanost: 2500*0.01=25.00
        # garancne: 2500*0.0025=6.25, rezervny: 2500*0.0475=118.75
        # kurzarbeit: 2500*0.003=7.50
        # urazove: 2500*0.008=20.00 (uncapped)
        assert result.sp_employer_nemocenske == Decimal("35.00")
        assert result.sp_employer_starobne == Decimal("350.00")
        assert result.sp_employer_invalidne == Decimal("75.00")
        assert result.sp_employer_nezamestnanost == Decimal("25.00")
        assert result.sp_employer_garancne == Decimal("6.25")
        assert result.sp_employer_rezervny == Decimal("118.75")
        assert result.sp_employer_kurzarbeit == Decimal("7.50")
        assert result.sp_employer_urazove == Decimal("20.00")

        # ZP employer: 2500 * 0.11 = 275.00
        assert result.zp_employer == Decimal("275.00")

        # Total employer cost: 2500 + sp_employer_total + 275
        assert result.total_employer_cost == _r(Decimal("2500") + result.sp_employer_total + Decimal("275"))

        # Identity
        _assert_identity(result)
