"""Tests for ledger_sync service — R-10 sync status management.

Covers:
  - get_sync_status: period status summary
  - mark_for_sync: bulk mark approved payrolls as pending
  - update_sync_status: single payroll transition
  - bulk_update_sync_status: bulk pending → synced/error
  - list_pending / count_pending: query helpers
  - _validate_transition: state machine validation
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.payroll import Payroll
from app.models.tenant import Tenant
from app.services.ledger_sync import (
    _validate_transition,
    bulk_update_sync_status,
    count_pending,
    get_sync_status,
    list_pending,
    mark_for_sync,
    update_sync_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _next() -> int:
    global _counter  # noqa: PLW0603
    _counter += 1
    return _counter


def _create_health_insurer(db: Session) -> HealthInsurer:
    n = _next()
    hi = HealthInsurer(
        code=f"{70 + n:02d}"[:4],
        name=f"Test ZP LS {n}",
        iban=f"SK00000000000000070{n:05d}",
    )
    db.add(hi)
    db.flush()
    return hi


def _create_tenant(db: Session) -> Tenant:
    n = _next()
    tenant = Tenant(
        name=f"Test Corp LS {n}",
        ico=f"8800{n:04d}",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban=f"SK00000000000000088{n:05d}",
        schema_name=f"tenant_test_ls_{n}",
    )
    db.add(tenant)
    db.flush()
    return tenant


def _create_employee(db: Session, tenant: Tenant, hi: HealthInsurer) -> Employee:
    n = _next()
    emp = Employee(
        tenant_id=tenant.id,
        employee_number=f"EMP-LS-{n:03d}",
        first_name="Test",
        last_name="Employee",
        birth_date=date(1990, 1, 1),
        birth_number=f"900101{n:04d}",
        gender="M",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban=f"SK31000000000000088{n:05d}",
        health_insurer_id=hi.id,
        tax_declaration_type="standard",
        nczd_applied=True,
        pillar2_saver=False,
        is_disabled=False,
        status="active",
        hire_date=date(2023, 1, 1),
    )
    db.add(emp)
    db.flush()
    return emp


def _create_contract(db: Session, tenant: Tenant, emp: Employee) -> Contract:
    n = _next()
    contract = Contract(
        tenant_id=tenant.id,
        employee_id=emp.id,
        contract_number=f"CTR-LS-{n:03d}",
        contract_type="permanent",
        job_title="Tester",
        start_date=date(2026, 1, 1),
        base_wage=Decimal("2000.00"),
        wage_type="monthly",
        is_current=True,
    )
    db.add(contract)
    db.flush()
    return contract


def _create_approved_payroll(
    db: Session,
    tenant: Tenant,
    emp: Employee,
    contract: Contract,
    *,
    period_year: int = 2026,
    period_month: int = 3,
    status: str = "approved",
) -> Payroll:
    payroll = Payroll(
        tenant_id=tenant.id,
        employee_id=emp.id,
        contract_id=contract.id,
        period_year=period_year,
        period_month=period_month,
        status=status,
        base_wage=Decimal("2000.00"),
        overtime_hours=Decimal("0"),
        overtime_amount=Decimal("0"),
        bonus_amount=Decimal("0"),
        supplement_amount=Decimal("0"),
        gross_wage=Decimal("2000.00"),
        sp_assessment_base=Decimal("2000.00"),
        sp_nemocenske=Decimal("28.00"),
        sp_starobne=Decimal("80.00"),
        sp_invalidne=Decimal("60.00"),
        sp_nezamestnanost=Decimal("20.00"),
        sp_employee_total=Decimal("188.00"),
        zp_assessment_base=Decimal("2000.00"),
        zp_employee=Decimal("100.00"),
        partial_tax_base=Decimal("1712.00"),
        nczd_applied=Decimal("497.23"),
        tax_base=Decimal("1214.77"),
        tax_advance=Decimal("230.81"),
        child_bonus=Decimal("0"),
        tax_after_bonus=Decimal("230.81"),
        net_wage=Decimal("1481.19"),
        sp_employer_nemocenske=Decimal("28.00"),
        sp_employer_starobne=Decimal("280.00"),
        sp_employer_invalidne=Decimal("60.00"),
        sp_employer_nezamestnanost=Decimal("20.00"),
        sp_employer_garancne=Decimal("5.00"),
        sp_employer_rezervny=Decimal("95.00"),
        sp_employer_kurzarbeit=Decimal("6.00"),
        sp_employer_urazove=Decimal("16.00"),
        sp_employer_total=Decimal("510.00"),
        zp_employer=Decimal("220.00"),
        total_employer_cost=Decimal("2730.00"),
        pillar2_amount=Decimal("0"),
    )
    db.add(payroll)
    db.flush()
    return payroll


def _full_chain(db: Session):
    hi = _create_health_insurer(db)
    tenant = _create_tenant(db)
    emp = _create_employee(db, tenant, hi)
    contract = _create_contract(db, tenant, emp)
    return tenant, emp, contract


# ---------------------------------------------------------------------------
# _validate_transition tests
# ---------------------------------------------------------------------------


class TestValidateTransition:
    """Test ledger sync state machine transitions."""

    def test_none_to_pending_valid(self):
        _validate_transition(None, "pending")

    def test_pending_to_synced_valid(self):
        _validate_transition("pending", "synced")

    def test_pending_to_error_valid(self):
        _validate_transition("pending", "error")

    def test_synced_to_pending_valid(self):
        _validate_transition("synced", "pending")

    def test_error_to_pending_valid(self):
        _validate_transition("error", "pending")

    def test_none_to_synced_invalid(self):
        with pytest.raises(ValueError, match="Invalid ledger_sync_status transition"):
            _validate_transition(None, "synced")

    def test_synced_to_error_invalid(self):
        with pytest.raises(ValueError, match="Invalid ledger_sync_status transition"):
            _validate_transition("synced", "error")

    def test_unknown_source_invalid(self):
        with pytest.raises(ValueError, match="Invalid ledger_sync_status transition"):
            _validate_transition("unknown", "pending")


# ---------------------------------------------------------------------------
# get_sync_status tests
# ---------------------------------------------------------------------------


class TestGetSyncStatus:
    """Test get_sync_status service."""

    def test_empty_period(self, db_session: Session):
        """Status for period with no payrolls returns zeros."""
        tenant, _, _ = _full_chain(db_session)
        status = get_sync_status(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=1,
        )
        assert status["total"] == 0
        assert status["not_synced"] == 0

    def test_not_synced_payrolls(self, db_session: Session):
        """Approved payroll with no sync status shows as not_synced."""
        tenant, emp, contract = _full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract)
        status = get_sync_status(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )
        assert status["total"] == 1
        assert status["not_synced"] == 1
        assert status["pending"] == 0

    def test_mixed_statuses(self, db_session: Session):
        """Status correctly counts mixed sync statuses."""
        tenant, emp, contract = _full_chain(db_session)
        p1 = _create_approved_payroll(db_session, tenant, emp, contract, period_month=3)
        p1.ledger_sync_status = "pending"

        hi2 = _create_health_insurer(db_session)
        emp2 = _create_employee(db_session, tenant, hi2)
        contract2 = _create_contract(db_session, tenant, emp2)
        p2 = _create_approved_payroll(db_session, tenant, emp2, contract2, period_month=3)
        p2.ledger_sync_status = "synced"
        db_session.flush()

        status = get_sync_status(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )
        assert status["total"] == 2
        assert status["pending"] == 1
        assert status["synced"] == 1


# ---------------------------------------------------------------------------
# mark_for_sync tests
# ---------------------------------------------------------------------------


class TestMarkForSync:
    """Test mark_for_sync service."""

    def test_marks_approved_payrolls(self, db_session: Session):
        """mark_for_sync sets ledger_sync_status to 'pending' for approved payrolls."""
        tenant, emp, contract = _full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        count = mark_for_sync(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )

        assert count == 1
        db_session.refresh(payroll)
        assert payroll.ledger_sync_status == "pending"

    def test_ignores_already_pending(self, db_session: Session):
        """mark_for_sync skips payrolls already marked as pending."""
        tenant, emp, contract = _full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)
        payroll.ledger_sync_status = "pending"
        db_session.flush()

        count = mark_for_sync(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )
        assert count == 0

    def test_ignores_non_approved(self, db_session: Session):
        """mark_for_sync only affects approved payrolls."""
        tenant, emp, contract = _full_chain(db_session)
        _create_approved_payroll(db_session, tenant, emp, contract, status="calculated")

        count = mark_for_sync(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )
        assert count == 0


# ---------------------------------------------------------------------------
# update_sync_status tests
# ---------------------------------------------------------------------------


class TestUpdateSyncStatus:
    """Test single payroll sync status update."""

    def test_transition_to_pending(self, db_session: Session):
        """Transition from None to pending."""
        tenant, emp, contract = _full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        result = update_sync_status(
            db_session,
            payroll_id=payroll.id,
            new_status="pending",
        )
        assert result.ledger_sync_status == "pending"

    def test_transition_pending_to_synced(self, db_session: Session):
        """Transition from pending to synced."""
        tenant, emp, contract = _full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)
        payroll.ledger_sync_status = "pending"
        db_session.flush()

        result = update_sync_status(
            db_session,
            payroll_id=payroll.id,
            new_status="synced",
        )
        assert result.ledger_sync_status == "synced"

    def test_invalid_transition_raises(self, db_session: Session):
        """Invalid transition raises ValueError."""
        tenant, emp, contract = _full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)

        with pytest.raises(ValueError, match="Invalid ledger_sync_status transition"):
            update_sync_status(
                db_session,
                payroll_id=payroll.id,
                new_status="synced",  # None → synced is invalid
            )

    def test_nonexistent_payroll_raises(self, db_session: Session):
        """Non-existent payroll raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            update_sync_status(
                db_session,
                payroll_id=uuid.uuid4(),
                new_status="pending",
            )


# ---------------------------------------------------------------------------
# bulk_update_sync_status tests
# ---------------------------------------------------------------------------


class TestBulkUpdateSyncStatus:
    """Test bulk sync status update."""

    def test_bulk_pending_to_synced(self, db_session: Session):
        """Bulk update pending payrolls to synced."""
        tenant, emp, contract = _full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)
        payroll.ledger_sync_status = "pending"
        db_session.flush()

        count = bulk_update_sync_status(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
            new_status="synced",
        )

        assert count == 1
        db_session.refresh(payroll)
        assert payroll.ledger_sync_status == "synced"

    def test_bulk_pending_to_error(self, db_session: Session):
        """Bulk update pending payrolls to error."""
        tenant, emp, contract = _full_chain(db_session)
        payroll = _create_approved_payroll(db_session, tenant, emp, contract)
        payroll.ledger_sync_status = "pending"
        db_session.flush()

        count = bulk_update_sync_status(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
            new_status="error",
        )

        assert count == 1
        db_session.refresh(payroll)
        assert payroll.ledger_sync_status == "error"

    def test_invalid_target_raises(self, db_session: Session):
        """Invalid target status raises ValueError."""
        tenant, _, _ = _full_chain(db_session)

        with pytest.raises(ValueError, match="Invalid ledger_sync_status transition"):
            bulk_update_sync_status(
                db_session,
                tenant_id=tenant.id,
                period_year=2026,
                period_month=3,
                new_status="pending",  # pending → pending is not allowed
            )


# ---------------------------------------------------------------------------
# list_pending / count_pending tests
# ---------------------------------------------------------------------------


class TestListPending:
    """Test pending payroll listing."""

    def test_list_pending_empty(self, db_session: Session):
        """list_pending returns empty list when no pending payrolls."""
        tenant, _, _ = _full_chain(db_session)
        result = list_pending(db_session, tenant_id=tenant.id)
        assert result == []

    def test_list_pending_filters_by_status(self, db_session: Session):
        """list_pending only returns payrolls with pending status."""
        tenant, emp, contract = _full_chain(db_session)
        p1 = _create_approved_payroll(db_session, tenant, emp, contract, period_month=3)
        p1.ledger_sync_status = "pending"

        hi2 = _create_health_insurer(db_session)
        emp2 = _create_employee(db_session, tenant, hi2)
        contract2 = _create_contract(db_session, tenant, emp2)
        p2 = _create_approved_payroll(db_session, tenant, emp2, contract2, period_month=3)
        p2.ledger_sync_status = "synced"
        db_session.flush()

        result = list_pending(db_session, tenant_id=tenant.id)
        assert len(result) == 1
        assert result[0].id == p1.id

    def test_list_pending_with_period_filter(self, db_session: Session):
        """list_pending filters by period_year and period_month."""
        tenant, emp, contract = _full_chain(db_session)
        p1 = _create_approved_payroll(db_session, tenant, emp, contract, period_month=3)
        p1.ledger_sync_status = "pending"

        hi2 = _create_health_insurer(db_session)
        emp2 = _create_employee(db_session, tenant, hi2)
        contract2 = _create_contract(db_session, tenant, emp2)
        p2 = _create_approved_payroll(db_session, tenant, emp2, contract2, period_month=4)
        p2.ledger_sync_status = "pending"
        db_session.flush()

        result = list_pending(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )
        assert len(result) == 1

    def test_count_pending(self, db_session: Session):
        """count_pending returns correct count."""
        tenant, emp, contract = _full_chain(db_session)
        p1 = _create_approved_payroll(db_session, tenant, emp, contract, period_month=3)
        p1.ledger_sync_status = "pending"
        db_session.flush()

        count = count_pending(db_session, tenant_id=tenant.id)
        assert count == 1

    def test_count_pending_with_filter(self, db_session: Session):
        """count_pending with period filter."""
        tenant, emp, contract = _full_chain(db_session)
        p1 = _create_approved_payroll(db_session, tenant, emp, contract, period_month=3)
        p1.ledger_sync_status = "pending"
        db_session.flush()

        count = count_pending(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=3,
        )
        assert count == 1

        count_other = count_pending(
            db_session,
            tenant_id=tenant.id,
            period_year=2026,
            period_month=4,
        )
        assert count_other == 0
