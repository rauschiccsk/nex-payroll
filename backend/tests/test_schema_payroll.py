"""Tests for Payroll Pydantic schemas (Create, Update, Read)."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.payroll import (
    PayrollCreate,
    PayrollRead,
    PayrollUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_ID = uuid4()
_EMPLOYEE_ID = uuid4()
_CONTRACT_ID = uuid4()
_APPROVED_BY_ID = uuid4()


def _valid_create_kwargs() -> dict:
    """Return a dict with all required fields for PayrollCreate."""
    return {
        "tenant_id": _TENANT_ID,
        "employee_id": _EMPLOYEE_ID,
        "contract_id": _CONTRACT_ID,
        "period_year": 2025,
        "period_month": 6,
        "base_wage": Decimal("2500.00"),
        "gross_wage": Decimal("2500.00"),
        # SP employee
        "sp_assessment_base": Decimal("2500.00"),
        "sp_nemocenske": Decimal("35.00"),
        "sp_starobne": Decimal("100.00"),
        "sp_invalidne": Decimal("75.00"),
        "sp_nezamestnanost": Decimal("25.00"),
        "sp_employee_total": Decimal("235.00"),
        # ZP employee
        "zp_assessment_base": Decimal("2500.00"),
        "zp_employee": Decimal("100.00"),
        # Tax
        "partial_tax_base": Decimal("2165.00"),
        "nczd_applied": Decimal("477.74"),
        "tax_base": Decimal("1687.26"),
        "tax_advance": Decimal("320.57"),
        "tax_after_bonus": Decimal("320.57"),
        # Net
        "net_wage": Decimal("1844.43"),
        # SP employer
        "sp_employer_nemocenske": Decimal("35.00"),
        "sp_employer_starobne": Decimal("350.00"),
        "sp_employer_invalidne": Decimal("75.00"),
        "sp_employer_nezamestnanost": Decimal("25.00"),
        "sp_employer_garancne": Decimal("6.25"),
        "sp_employer_rezervny": Decimal("118.75"),
        "sp_employer_kurzarbeit": Decimal("12.50"),
        "sp_employer_urazove": Decimal("20.00"),
        "sp_employer_total": Decimal("642.50"),
        # ZP employer
        "zp_employer": Decimal("250.00"),
        # Total employer cost
        "total_employer_cost": Decimal("3392.50"),
    }


def _read_kwargs() -> dict:
    """Return a complete dict for constructing PayrollRead."""
    now = datetime(2025, 6, 1, 12, 0, 0)
    kw = _valid_create_kwargs()
    kw.update(
        {
            "id": uuid4(),
            "status": "draft",
            "overtime_hours": Decimal("0"),
            "overtime_amount": Decimal("0"),
            "bonus_amount": Decimal("0"),
            "supplement_amount": Decimal("0"),
            "child_bonus": Decimal("0"),
            "pillar2_amount": Decimal("0"),
            "ai_validation_result": None,
            "ledger_sync_status": None,
            "calculated_at": None,
            "approved_at": None,
            "approved_by": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    return kw


# ---------------------------------------------------------------------------
# PayrollCreate
# ---------------------------------------------------------------------------


class TestPayrollCreate:
    """Tests for the Create schema."""

    def test_valid_minimal(self):
        """Valid creation with only required fields — defaults applied."""
        schema = PayrollCreate(**_valid_create_kwargs())
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.contract_id == _CONTRACT_ID
        assert schema.period_year == 2025
        assert schema.period_month == 6
        assert schema.status == "draft"
        assert schema.base_wage == Decimal("2500.00")
        assert schema.gross_wage == Decimal("2500.00")
        # defaults
        assert schema.overtime_hours == Decimal("0")
        assert schema.overtime_amount == Decimal("0")
        assert schema.bonus_amount == Decimal("0")
        assert schema.supplement_amount == Decimal("0")
        assert schema.child_bonus == Decimal("0")
        assert schema.pillar2_amount == Decimal("0")

    def test_valid_full(self):
        """Valid creation with all fields explicitly set."""
        kw = _valid_create_kwargs()
        # Override gross components — gross must equal base + overtime + bonus + supplement
        kw["overtime_hours"] = Decimal("10.50")
        kw["overtime_amount"] = Decimal("250.00")
        kw["bonus_amount"] = Decimal("100.00")
        kw["supplement_amount"] = Decimal("50.00")
        kw["gross_wage"] = Decimal("2900.00")  # 2500 + 250 + 100 + 50
        kw["status"] = "calculated"
        kw["child_bonus"] = Decimal("140.00")
        kw["pillar2_amount"] = Decimal("30.00")
        schema = PayrollCreate(**kw)
        assert schema.status == "calculated"
        assert schema.overtime_hours == Decimal("10.50")
        assert schema.overtime_amount == Decimal("250.00")
        assert schema.bonus_amount == Decimal("100.00")
        assert schema.supplement_amount == Decimal("50.00")
        assert schema.gross_wage == Decimal("2900.00")
        assert schema.child_bonus == Decimal("140.00")
        assert schema.pillar2_amount == Decimal("30.00")

    # -- required field validation --

    def test_missing_required_tenant_id(self):
        kw = _valid_create_kwargs()
        del kw["tenant_id"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "tenant_id" in str(exc_info.value)

    def test_missing_required_employee_id(self):
        kw = _valid_create_kwargs()
        del kw["employee_id"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "employee_id" in str(exc_info.value)

    def test_missing_required_contract_id(self):
        kw = _valid_create_kwargs()
        del kw["contract_id"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "contract_id" in str(exc_info.value)

    def test_missing_required_period_year(self):
        kw = _valid_create_kwargs()
        del kw["period_year"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_missing_required_period_month(self):
        kw = _valid_create_kwargs()
        del kw["period_month"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_missing_required_base_wage(self):
        kw = _valid_create_kwargs()
        del kw["base_wage"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "base_wage" in str(exc_info.value)

    def test_missing_required_gross_wage(self):
        kw = _valid_create_kwargs()
        del kw["gross_wage"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "gross_wage" in str(exc_info.value)

    def test_missing_required_net_wage(self):
        kw = _valid_create_kwargs()
        del kw["net_wage"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "net_wage" in str(exc_info.value)

    # -- SP employee required fields --

    def test_missing_required_sp_assessment_base(self):
        kw = _valid_create_kwargs()
        del kw["sp_assessment_base"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_assessment_base" in str(exc_info.value)

    def test_missing_required_sp_nemocenske(self):
        kw = _valid_create_kwargs()
        del kw["sp_nemocenske"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_nemocenske" in str(exc_info.value)

    def test_missing_required_sp_starobne(self):
        kw = _valid_create_kwargs()
        del kw["sp_starobne"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_starobne" in str(exc_info.value)

    def test_missing_required_sp_invalidne(self):
        kw = _valid_create_kwargs()
        del kw["sp_invalidne"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_invalidne" in str(exc_info.value)

    def test_missing_required_sp_nezamestnanost(self):
        kw = _valid_create_kwargs()
        del kw["sp_nezamestnanost"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_nezamestnanost" in str(exc_info.value)

    def test_missing_required_sp_employee_total(self):
        kw = _valid_create_kwargs()
        del kw["sp_employee_total"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employee_total" in str(exc_info.value)

    # -- ZP employee required fields --

    def test_missing_required_zp_assessment_base(self):
        kw = _valid_create_kwargs()
        del kw["zp_assessment_base"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "zp_assessment_base" in str(exc_info.value)

    def test_missing_required_zp_employee(self):
        kw = _valid_create_kwargs()
        del kw["zp_employee"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "zp_employee" in str(exc_info.value)

    # -- Tax required fields --

    def test_missing_required_partial_tax_base(self):
        kw = _valid_create_kwargs()
        del kw["partial_tax_base"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "partial_tax_base" in str(exc_info.value)

    def test_missing_required_nczd_applied(self):
        kw = _valid_create_kwargs()
        del kw["nczd_applied"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "nczd_applied" in str(exc_info.value)

    def test_missing_required_tax_base(self):
        kw = _valid_create_kwargs()
        del kw["tax_base"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "tax_base" in str(exc_info.value)

    def test_missing_required_tax_advance(self):
        kw = _valid_create_kwargs()
        del kw["tax_advance"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "tax_advance" in str(exc_info.value)

    def test_missing_required_tax_after_bonus(self):
        kw = _valid_create_kwargs()
        del kw["tax_after_bonus"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "tax_after_bonus" in str(exc_info.value)

    # -- SP employer required fields --

    def test_missing_required_sp_employer_nemocenske(self):
        kw = _valid_create_kwargs()
        del kw["sp_employer_nemocenske"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employer_nemocenske" in str(exc_info.value)

    def test_missing_required_sp_employer_starobne(self):
        kw = _valid_create_kwargs()
        del kw["sp_employer_starobne"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employer_starobne" in str(exc_info.value)

    def test_missing_required_sp_employer_invalidne(self):
        kw = _valid_create_kwargs()
        del kw["sp_employer_invalidne"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employer_invalidne" in str(exc_info.value)

    def test_missing_required_sp_employer_nezamestnanost(self):
        kw = _valid_create_kwargs()
        del kw["sp_employer_nezamestnanost"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employer_nezamestnanost" in str(exc_info.value)

    def test_missing_required_sp_employer_garancne(self):
        kw = _valid_create_kwargs()
        del kw["sp_employer_garancne"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employer_garancne" in str(exc_info.value)

    def test_missing_required_sp_employer_rezervny(self):
        kw = _valid_create_kwargs()
        del kw["sp_employer_rezervny"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employer_rezervny" in str(exc_info.value)

    def test_missing_required_sp_employer_kurzarbeit(self):
        kw = _valid_create_kwargs()
        del kw["sp_employer_kurzarbeit"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employer_kurzarbeit" in str(exc_info.value)

    def test_missing_required_sp_employer_urazove(self):
        kw = _valid_create_kwargs()
        del kw["sp_employer_urazove"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employer_urazove" in str(exc_info.value)

    def test_missing_required_sp_employer_total(self):
        kw = _valid_create_kwargs()
        del kw["sp_employer_total"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "sp_employer_total" in str(exc_info.value)

    def test_missing_required_zp_employer(self):
        kw = _valid_create_kwargs()
        del kw["zp_employer"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "zp_employer" in str(exc_info.value)

    def test_missing_required_total_employer_cost(self):
        kw = _valid_create_kwargs()
        del kw["total_employer_cost"]
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "total_employer_cost" in str(exc_info.value)

    # -- Literal validation: status --

    def test_invalid_status(self):
        kw = _valid_create_kwargs()
        kw["status"] = "invalid_status"
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "status" in str(exc_info.value)

    def test_status_draft(self):
        kw = _valid_create_kwargs()
        kw["status"] = "draft"
        schema = PayrollCreate(**kw)
        assert schema.status == "draft"

    def test_status_calculated(self):
        kw = _valid_create_kwargs()
        kw["status"] = "calculated"
        schema = PayrollCreate(**kw)
        assert schema.status == "calculated"

    def test_status_approved(self):
        kw = _valid_create_kwargs()
        kw["status"] = "approved"
        schema = PayrollCreate(**kw)
        assert schema.status == "approved"

    def test_status_paid(self):
        kw = _valid_create_kwargs()
        kw["status"] = "paid"
        schema = PayrollCreate(**kw)
        assert schema.status == "paid"

    # -- period_month boundary validation (ge=1, le=12) --

    def test_period_month_zero_rejected(self):
        """period_month=0 must be rejected (ge=1)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 0
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_period_month_13_rejected(self):
        """period_month=13 must be rejected (le=12)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 13
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "period_month" in str(exc_info.value)

    def test_period_month_boundary_min(self):
        """period_month=1 must be accepted (ge=1)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 1
        schema = PayrollCreate(**kw)
        assert schema.period_month == 1

    def test_period_month_boundary_max(self):
        """period_month=12 must be accepted (le=12)."""
        kw = _valid_create_kwargs()
        kw["period_month"] = 12
        schema = PayrollCreate(**kw)
        assert schema.period_month == 12

    # -- period_year range validation (ge=2000, le=2100) --

    def test_period_year_too_low(self):
        """period_year=1999 must be rejected."""
        kw = _valid_create_kwargs()
        kw["period_year"] = 1999
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_period_year_too_high(self):
        """period_year=2101 must be rejected."""
        kw = _valid_create_kwargs()
        kw["period_year"] = 2101
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "period_year" in str(exc_info.value)

    def test_period_year_boundary_min(self):
        """period_year=2000 must be accepted."""
        kw = _valid_create_kwargs()
        kw["period_year"] = 2000
        schema = PayrollCreate(**kw)
        assert schema.period_year == 2000

    def test_period_year_boundary_max(self):
        """period_year=2100 must be accepted."""
        kw = _valid_create_kwargs()
        kw["period_year"] = 2100
        schema = PayrollCreate(**kw)
        assert schema.period_year == 2100

    # -- ge=0 constraints on amount fields --

    def test_negative_overtime_hours_rejected(self):
        kw = _valid_create_kwargs()
        kw["overtime_hours"] = Decimal("-1.00")
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "overtime_hours" in str(exc_info.value)

    def test_negative_overtime_amount_rejected(self):
        kw = _valid_create_kwargs()
        kw["overtime_amount"] = Decimal("-1.00")
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "overtime_amount" in str(exc_info.value)

    def test_negative_bonus_amount_rejected(self):
        kw = _valid_create_kwargs()
        kw["bonus_amount"] = Decimal("-1.00")
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "bonus_amount" in str(exc_info.value)

    def test_negative_supplement_amount_rejected(self):
        kw = _valid_create_kwargs()
        kw["supplement_amount"] = Decimal("-1.00")
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "supplement_amount" in str(exc_info.value)

    def test_negative_child_bonus_rejected(self):
        kw = _valid_create_kwargs()
        kw["child_bonus"] = Decimal("-1.00")
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "child_bonus" in str(exc_info.value)

    def test_negative_pillar2_amount_rejected(self):
        kw = _valid_create_kwargs()
        kw["pillar2_amount"] = Decimal("-1.00")
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "pillar2_amount" in str(exc_info.value)

    # -- gross_wage model validator --

    def test_gross_wage_mismatch_rejected(self):
        """gross_wage must equal base + overtime + bonus + supplement."""
        kw = _valid_create_kwargs()
        kw["gross_wage"] = Decimal("9999.00")  # doesn't match sum
        with pytest.raises(ValidationError) as exc_info:
            PayrollCreate(**kw)
        assert "Gross wage" in str(exc_info.value)

    def test_gross_wage_with_components_valid(self):
        """gross_wage matching component sum is accepted."""
        kw = _valid_create_kwargs()
        kw["overtime_amount"] = Decimal("100.00")
        kw["bonus_amount"] = Decimal("50.00")
        kw["supplement_amount"] = Decimal("25.00")
        kw["gross_wage"] = Decimal("2675.00")  # 2500 + 100 + 50 + 25
        schema = PayrollCreate(**kw)
        assert schema.gross_wage == Decimal("2675.00")


# ---------------------------------------------------------------------------
# PayrollUpdate
# ---------------------------------------------------------------------------


class TestPayrollUpdate:
    """Tests for the Update schema — all fields optional."""

    def test_empty_update(self):
        """All fields default to None when no data supplied."""
        schema = PayrollUpdate()
        assert schema.status is None
        assert schema.base_wage is None
        assert schema.overtime_hours is None
        assert schema.overtime_amount is None
        assert schema.bonus_amount is None
        assert schema.supplement_amount is None
        assert schema.gross_wage is None
        assert schema.sp_assessment_base is None
        assert schema.sp_nemocenske is None
        assert schema.sp_starobne is None
        assert schema.sp_invalidne is None
        assert schema.sp_nezamestnanost is None
        assert schema.sp_employee_total is None
        assert schema.zp_assessment_base is None
        assert schema.zp_employee is None
        assert schema.partial_tax_base is None
        assert schema.nczd_applied is None
        assert schema.tax_base is None
        assert schema.tax_advance is None
        assert schema.child_bonus is None
        assert schema.tax_after_bonus is None
        assert schema.net_wage is None
        assert schema.sp_employer_nemocenske is None
        assert schema.sp_employer_starobne is None
        assert schema.sp_employer_invalidne is None
        assert schema.sp_employer_nezamestnanost is None
        assert schema.sp_employer_garancne is None
        assert schema.sp_employer_rezervny is None
        assert schema.sp_employer_kurzarbeit is None
        assert schema.sp_employer_urazove is None
        assert schema.sp_employer_total is None
        assert schema.zp_employer is None
        assert schema.total_employer_cost is None
        assert schema.pillar2_amount is None
        assert schema.ai_validation_result is None
        assert schema.ledger_sync_status is None
        assert schema.calculated_at is None
        assert schema.approved_at is None
        assert schema.approved_by is None

    def test_partial_update(self):
        """Only supplied fields are set; the rest remain None."""
        schema = PayrollUpdate(
            status="calculated",
            base_wage=Decimal("3000.00"),
            gross_wage=Decimal("3200.00"),
        )
        assert schema.status == "calculated"
        assert schema.base_wage == Decimal("3000.00")
        assert schema.gross_wage == Decimal("3200.00")
        # everything else remains None
        assert schema.overtime_hours is None
        assert schema.net_wage is None
        assert schema.sp_employee_total is None

    # -- Literal validation: status --

    def test_invalid_status_in_update(self):
        with pytest.raises(ValidationError) as exc_info:
            PayrollUpdate(status="invalid_status")
        assert "status" in str(exc_info.value)

    def test_update_status_calculated(self):
        schema = PayrollUpdate(status="calculated")
        assert schema.status == "calculated"

    def test_update_status_approved(self):
        schema = PayrollUpdate(status="approved")
        assert schema.status == "approved"

    def test_update_status_paid(self):
        schema = PayrollUpdate(status="paid")
        assert schema.status == "paid"

    # -- Literal validation: ledger_sync_status --

    def test_invalid_ledger_sync_status_in_update(self):
        with pytest.raises(ValidationError) as exc_info:
            PayrollUpdate(ledger_sync_status="invalid")
        assert "ledger_sync_status" in str(exc_info.value)

    def test_update_ledger_sync_status_pending(self):
        schema = PayrollUpdate(ledger_sync_status="pending")
        assert schema.ledger_sync_status == "pending"

    def test_update_ledger_sync_status_synced(self):
        schema = PayrollUpdate(ledger_sync_status="synced")
        assert schema.ledger_sync_status == "synced"

    def test_update_ledger_sync_status_error(self):
        schema = PayrollUpdate(ledger_sync_status="error")
        assert schema.ledger_sync_status == "error"

    # -- SP/ZP/tax calculated fields updatable via recalculation --

    def test_update_sp_employee_fields(self):
        """All SP employee fields can be updated (via recalculation)."""
        schema = PayrollUpdate(
            sp_assessment_base=Decimal("3000.00"),
            sp_nemocenske=Decimal("42.00"),
            sp_starobne=Decimal("120.00"),
            sp_invalidne=Decimal("90.00"),
            sp_nezamestnanost=Decimal("30.00"),
            sp_employee_total=Decimal("282.00"),
        )
        assert schema.sp_assessment_base == Decimal("3000.00")
        assert schema.sp_nemocenske == Decimal("42.00")
        assert schema.sp_starobne == Decimal("120.00")
        assert schema.sp_invalidne == Decimal("90.00")
        assert schema.sp_nezamestnanost == Decimal("30.00")
        assert schema.sp_employee_total == Decimal("282.00")

    def test_update_zp_employee_fields(self):
        """All ZP employee fields can be updated (via recalculation)."""
        schema = PayrollUpdate(
            zp_assessment_base=Decimal("3000.00"),
            zp_employee=Decimal("120.00"),
        )
        assert schema.zp_assessment_base == Decimal("3000.00")
        assert schema.zp_employee == Decimal("120.00")

    def test_update_tax_fields(self):
        """All tax calculation fields can be updated (via recalculation)."""
        schema = PayrollUpdate(
            partial_tax_base=Decimal("2600.00"),
            nczd_applied=Decimal("477.74"),
            tax_base=Decimal("2122.26"),
            tax_advance=Decimal("403.22"),
            tax_after_bonus=Decimal("263.22"),
        )
        assert schema.partial_tax_base == Decimal("2600.00")
        assert schema.nczd_applied == Decimal("477.74")
        assert schema.tax_base == Decimal("2122.26")
        assert schema.tax_advance == Decimal("403.22")
        assert schema.tax_after_bonus == Decimal("263.22")

    def test_update_sp_employer_fields(self):
        """All 8 SP employer fields can be updated."""
        schema = PayrollUpdate(
            sp_employer_nemocenske=Decimal("42.00"),
            sp_employer_starobne=Decimal("420.00"),
            sp_employer_invalidne=Decimal("90.00"),
            sp_employer_nezamestnanost=Decimal("30.00"),
            sp_employer_garancne=Decimal("7.50"),
            sp_employer_rezervny=Decimal("142.50"),
            sp_employer_kurzarbeit=Decimal("15.00"),
            sp_employer_urazove=Decimal("24.00"),
        )
        assert schema.sp_employer_nemocenske == Decimal("42.00")
        assert schema.sp_employer_starobne == Decimal("420.00")
        assert schema.sp_employer_invalidne == Decimal("90.00")
        assert schema.sp_employer_nezamestnanost == Decimal("30.00")
        assert schema.sp_employer_garancne == Decimal("7.50")
        assert schema.sp_employer_rezervny == Decimal("142.50")
        assert schema.sp_employer_kurzarbeit == Decimal("15.00")
        assert schema.sp_employer_urazove == Decimal("24.00")

    def test_update_zp_employer_and_total_cost(self):
        """zp_employer and total_employer_cost can be updated."""
        schema = PayrollUpdate(
            zp_employer=Decimal("300.00"),
            total_employer_cost=Decimal("4100.00"),
        )
        assert schema.zp_employer == Decimal("300.00")
        assert schema.total_employer_cost == Decimal("4100.00")

    # -- System-managed metadata fields --

    def test_update_calculated_at(self):
        """calculated_at is system-managed but present in Update for service layer."""
        ts = datetime(2025, 6, 15, 10, 0, 0)
        schema = PayrollUpdate(calculated_at=ts)
        assert schema.calculated_at == ts

    def test_update_approved_at(self):
        """approved_at is system-managed but present in Update for service layer."""
        ts = datetime(2025, 6, 20, 14, 30, 0)
        schema = PayrollUpdate(approved_at=ts)
        assert schema.approved_at == ts

    def test_update_approved_by(self):
        """approved_by is system-managed but present in Update for service layer."""
        schema = PayrollUpdate(approved_by=_APPROVED_BY_ID)
        assert schema.approved_by == _APPROVED_BY_ID


# ---------------------------------------------------------------------------
# PayrollRead
# ---------------------------------------------------------------------------


class TestPayrollRead:
    """Tests for the Read schema — from_attributes=True."""

    def test_from_dict(self):
        """Construct Read schema from a plain dict."""
        kw = _read_kwargs()
        schema = PayrollRead(**kw)
        assert schema.id == kw["id"]
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.contract_id == _CONTRACT_ID
        assert schema.period_year == 2025
        assert schema.period_month == 6
        assert schema.status == "draft"
        # Gross
        assert schema.base_wage == Decimal("2500.00")
        assert schema.overtime_hours == Decimal("0")
        assert schema.overtime_amount == Decimal("0")
        assert schema.bonus_amount == Decimal("0")
        assert schema.supplement_amount == Decimal("0")
        assert schema.gross_wage == Decimal("2500.00")
        # SP employee
        assert schema.sp_assessment_base == Decimal("2500.00")
        assert schema.sp_nemocenske == Decimal("35.00")
        assert schema.sp_starobne == Decimal("100.00")
        assert schema.sp_invalidne == Decimal("75.00")
        assert schema.sp_nezamestnanost == Decimal("25.00")
        assert schema.sp_employee_total == Decimal("235.00")
        # ZP employee
        assert schema.zp_assessment_base == Decimal("2500.00")
        assert schema.zp_employee == Decimal("100.00")
        # Tax
        assert schema.partial_tax_base == Decimal("2165.00")
        assert schema.nczd_applied == Decimal("477.74")
        assert schema.tax_base == Decimal("1687.26")
        assert schema.tax_advance == Decimal("320.57")
        assert schema.child_bonus == Decimal("0")
        assert schema.tax_after_bonus == Decimal("320.57")
        # Net
        assert schema.net_wage == Decimal("1844.43")
        # SP employer
        assert schema.sp_employer_nemocenske == Decimal("35.00")
        assert schema.sp_employer_starobne == Decimal("350.00")
        assert schema.sp_employer_invalidne == Decimal("75.00")
        assert schema.sp_employer_nezamestnanost == Decimal("25.00")
        assert schema.sp_employer_garancne == Decimal("6.25")
        assert schema.sp_employer_rezervny == Decimal("118.75")
        assert schema.sp_employer_kurzarbeit == Decimal("12.50")
        assert schema.sp_employer_urazove == Decimal("20.00")
        assert schema.sp_employer_total == Decimal("642.50")
        # ZP employer + total
        assert schema.zp_employer == Decimal("250.00")
        assert schema.total_employer_cost == Decimal("3392.50")
        # Pillar 2
        assert schema.pillar2_amount == Decimal("0")
        # Optional fields
        assert schema.ai_validation_result is None
        assert schema.ledger_sync_status is None
        assert schema.calculated_at is None
        assert schema.approved_at is None
        assert schema.approved_by is None
        # Timestamps
        assert schema.created_at == datetime(2025, 6, 1, 12, 0, 0)
        assert schema.updated_at == datetime(2025, 6, 1, 12, 0, 0)

    def test_from_attributes_orm_mode(self):
        """Verify from_attributes=True allows ORM object-like access."""

        class FakeORM:
            def __init__(self):
                kw = _read_kwargs()
                for key, value in kw.items():
                    setattr(self, key, value)

        orm_obj = FakeORM()
        schema = PayrollRead.model_validate(orm_obj)
        assert schema.tenant_id == _TENANT_ID
        assert schema.employee_id == _EMPLOYEE_ID
        assert schema.contract_id == _CONTRACT_ID
        assert schema.status == "draft"
        assert schema.base_wage == Decimal("2500.00")
        assert schema.net_wage == Decimal("1844.43")
        assert schema.sp_employee_total == Decimal("235.00")
        assert schema.zp_employee == Decimal("100.00")
        assert schema.tax_advance == Decimal("320.57")
        assert schema.sp_employer_total == Decimal("642.50")
        assert schema.zp_employer == Decimal("250.00")
        assert schema.total_employer_cost == Decimal("3392.50")

    def test_serialisation_roundtrip(self):
        """model_dump() produces a dict that can reconstruct the schema."""
        kw = _read_kwargs()
        schema = PayrollRead(**kw)
        dumped = schema.model_dump()
        assert dumped["id"] == kw["id"]
        assert dumped["tenant_id"] == _TENANT_ID
        assert dumped["period_year"] == 2025
        assert dumped["period_month"] == 6
        assert dumped["status"] == "draft"
        assert dumped["base_wage"] == Decimal("2500.00")
        assert dumped["gross_wage"] == Decimal("2500.00")
        assert dumped["net_wage"] == Decimal("1844.43")
        assert dumped["sp_employee_total"] == Decimal("235.00")
        assert dumped["zp_employee"] == Decimal("100.00")
        assert dumped["tax_advance"] == Decimal("320.57")
        assert dumped["sp_employer_total"] == Decimal("642.50")
        assert dumped["zp_employer"] == Decimal("250.00")
        assert dumped["total_employer_cost"] == Decimal("3392.50")
        assert dumped["ai_validation_result"] is None
        assert dumped["ledger_sync_status"] is None

    def test_read_all_fields_present(self):
        """Read schema exposes every field from the model."""
        expected_fields = {
            "id",
            "tenant_id",
            "employee_id",
            "contract_id",
            "period_year",
            "period_month",
            "status",
            # Gross
            "base_wage",
            "overtime_hours",
            "overtime_amount",
            "bonus_amount",
            "supplement_amount",
            "gross_wage",
            # SP employee
            "sp_assessment_base",
            "sp_nemocenske",
            "sp_starobne",
            "sp_invalidne",
            "sp_nezamestnanost",
            "sp_employee_total",
            # ZP employee
            "zp_assessment_base",
            "zp_employee",
            # Tax
            "partial_tax_base",
            "nczd_applied",
            "tax_base",
            "tax_advance",
            "child_bonus",
            "tax_after_bonus",
            # Net
            "net_wage",
            # SP employer
            "sp_employer_nemocenske",
            "sp_employer_starobne",
            "sp_employer_invalidne",
            "sp_employer_nezamestnanost",
            "sp_employer_garancne",
            "sp_employer_rezervny",
            "sp_employer_kurzarbeit",
            "sp_employer_urazove",
            "sp_employer_total",
            # ZP employer + total
            "zp_employer",
            "total_employer_cost",
            # Pillar 2
            "pillar2_amount",
            # AI / Ledger
            "ai_validation_result",
            "ledger_sync_status",
            # Approval metadata
            "calculated_at",
            "approved_at",
            "approved_by",
            # Timestamps
            "created_at",
            "updated_at",
        }
        assert set(PayrollRead.model_fields.keys()) == expected_fields

    def test_read_decimal_precision(self):
        """All Decimal fields in Read preserve correct precision."""
        kw = _read_kwargs()
        schema = PayrollRead(**kw)
        # Verify key decimal fields retain their precision
        assert schema.base_wage == Decimal("2500.00")
        assert schema.nczd_applied == Decimal("477.74")
        assert schema.sp_employer_garancne == Decimal("6.25")
        assert schema.sp_employer_rezervny == Decimal("118.75")
