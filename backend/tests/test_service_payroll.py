"""Tests for Payroll service layer."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.pay_slip import PaySlip
from app.models.payroll import Payroll
from app.models.tenant import Tenant
from app.schemas.payroll import PayrollCreate, PayrollUpdate
from app.services.payroll import (
    ALLOWED_LEDGER_SYNC_STATUSES,
    ALLOWED_STATUSES,
    count_payrolls,
    create_payroll,
    delete_payroll,
    get_payroll,
    list_payrolls,
    update_payroll,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestServiceConstants:
    """Verify allowed values match DESIGN.md CHECK constraints."""

    def test_allowed_statuses(self):
        expected = {"draft", "calculated", "approved", "paid"}
        assert expected == ALLOWED_STATUSES

    def test_allowed_ledger_sync_statuses(self):
        expected = {"pending", "synced", "error"}
        assert expected == ALLOWED_LEDGER_SYNC_STATUSES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session, **overrides) -> Tenant:
    """Insert a minimal Tenant and flush; return the instance."""
    defaults = {
        "name": "Test s.r.o.",
        "ico": "12345678",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "schema_name": "tenant_test_12345678",
    }
    defaults.update(overrides)
    tenant = Tenant(**defaults)
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _make_health_insurer(db_session, **overrides) -> HealthInsurer:
    """Insert a minimal HealthInsurer and flush."""
    defaults = {
        "code": "25",
        "name": "VšZP",
        "iban": "SK0000000000000000000025",
    }
    defaults.update(overrides)
    hi = HealthInsurer(**defaults)
    db_session.add(hi)
    db_session.flush()
    return hi


def _make_employee(db_session, tenant, health_insurer, **overrides) -> Employee:
    """Insert a minimal Employee and flush."""
    defaults = {
        "tenant_id": tenant.id,
        "employee_number": "EMP-001",
        "first_name": "Ján",
        "last_name": "Novák",
        "birth_date": date(1990, 1, 1),
        "birth_number": "9001011234",
        "gender": "M",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "bank_iban": "SK3100000000000000000088",
        "health_insurer_id": health_insurer.id,
        "tax_declaration_type": "standard",
        "hire_date": date(2023, 1, 1),
    }
    defaults.update(overrides)
    emp = Employee(**defaults)
    db_session.add(emp)
    db_session.flush()
    return emp


def _make_contract(db_session, tenant, employee, **overrides) -> Contract:
    """Insert a minimal Contract and flush."""
    defaults = {
        "tenant_id": tenant.id,
        "employee_id": employee.id,
        "contract_number": "ZML-001",
        "contract_type": "permanent",
        "job_title": "Developer",
        "wage_type": "monthly",
        "base_wage": Decimal("2500.00"),
        "start_date": date(2023, 1, 1),
    }
    defaults.update(overrides)
    c = Contract(**defaults)
    db_session.add(c)
    db_session.flush()
    return c


_PAYROLL_NUMERIC_DEFAULTS = {
    "base_wage": Decimal("2500.00"),
    "gross_wage": Decimal("2500.00"),
    "sp_assessment_base": Decimal("2500.00"),
    "sp_nemocenske": Decimal("35.00"),
    "sp_starobne": Decimal("100.00"),
    "sp_invalidne": Decimal("75.00"),
    "sp_nezamestnanost": Decimal("25.00"),
    "sp_employee_total": Decimal("235.00"),
    "zp_assessment_base": Decimal("2500.00"),
    "zp_employee": Decimal("100.00"),
    "partial_tax_base": Decimal("2165.00"),
    "nczd_applied": Decimal("410.24"),
    "tax_base": Decimal("1754.76"),
    "tax_advance": Decimal("333.40"),
    "tax_after_bonus": Decimal("333.40"),
    "net_wage": Decimal("1831.60"),
    "sp_employer_nemocenske": Decimal("35.00"),
    "sp_employer_starobne": Decimal("350.00"),
    "sp_employer_invalidne": Decimal("75.00"),
    "sp_employer_nezamestnanost": Decimal("25.00"),
    "sp_employer_garancne": Decimal("6.25"),
    "sp_employer_rezervny": Decimal("118.75"),
    "sp_employer_kurzarbeit": Decimal("12.50"),
    "sp_employer_urazove": Decimal("20.00"),
    "sp_employer_total": Decimal("642.50"),
    "zp_employer": Decimal("250.00"),
    "total_employer_cost": Decimal("3392.50"),
}


def _setup_prerequisites(db_session, *, health_insurer=None, **tenant_overrides):
    """Create full FK parent chain: Tenant → HealthInsurer → Employee → Contract.

    Returns dict with all created entities.
    """
    tenant = _make_tenant(db_session, **tenant_overrides)
    if health_insurer is None:
        health_insurer = _make_health_insurer(db_session)
    employee = _make_employee(db_session, tenant, health_insurer)
    contract = _make_contract(db_session, tenant, employee)
    return {
        "tenant": tenant,
        "health_insurer": health_insurer,
        "employee": employee,
        "contract": contract,
    }


# Counter for unique values across helper calls within a single test session
_counter = 0


def _setup_prerequisites_unique(db_session, *, suffix: str = "", health_insurer=None):
    """Create full FK parent chain with unique ICO/schema/employee_number/contract.

    Each call produces a completely independent set of parent records.
    Pass *health_insurer* to reuse an existing HealthInsurer (avoids
    unique-code violation when calling this helper multiple times).
    """
    global _counter  # noqa: PLW0603
    _counter += 1
    n = _counter
    s = suffix or str(n)
    return _setup_prerequisites(
        db_session,
        health_insurer=health_insurer,
        ico=f"{10000000 + n}",
        schema_name=f"tenant_{s}_{10000000 + n}",
        name=f"Company {s}",
    )


def _make_payroll_payload(tenant_id, employee_id, contract_id, **overrides) -> PayrollCreate:
    """Build a valid PayrollCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "contract_id": contract_id,
        "period_year": 2025,
        "period_month": 1,
        "status": "draft",
        **_PAYROLL_NUMERIC_DEFAULTS,
    }
    defaults.update(overrides)
    return PayrollCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreatePayroll:
    """Tests for create_payroll."""

    def test_create_returns_model_instance(self, db_session):
        ctx = _setup_prerequisites(db_session)
        payload = _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id)

        result = create_payroll(db_session, payload)

        assert isinstance(result, Payroll)
        assert result.id is not None
        assert result.tenant_id == ctx["tenant"].id
        assert result.employee_id == ctx["employee"].id
        assert result.contract_id == ctx["contract"].id
        assert result.period_year == 2025
        assert result.period_month == 1
        assert result.status == "draft"
        assert result.base_wage == Decimal("2500.00")
        assert result.gross_wage == Decimal("2500.00")
        assert result.net_wage == Decimal("1831.60")
        assert result.sp_employee_total == Decimal("235.00")
        assert result.zp_employee == Decimal("100.00")
        assert result.sp_employer_total == Decimal("642.50")
        assert result.zp_employer == Decimal("250.00")
        assert result.total_employer_cost == Decimal("3392.50")

    def test_create_default_status_is_draft(self, db_session):
        ctx = _setup_prerequisites(db_session)
        payload = _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id)
        result = create_payroll(db_session, payload)
        assert result.status == "draft"

    def test_create_duplicate_period_employee_raises(self, db_session):
        """Creating a second payroll for the same (tenant, employee, year, month) must raise."""
        ctx = _setup_prerequisites(db_session)
        payload = _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id)
        create_payroll(db_session, payload)

        with pytest.raises(ValueError, match="already exists"):
            create_payroll(db_session, payload)

    def test_create_same_employee_different_period_ok(self, db_session):
        """Same employee, different month — should succeed."""
        ctx = _setup_prerequisites(db_session)

        p1 = create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=1,
            ),
        )
        p2 = create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=2,
            ),
        )
        assert p1.id != p2.id
        assert p1.period_month == 1
        assert p2.period_month == 2

    def test_create_invalid_status_raises_value_error(self, db_session):
        """Creating with an invalid status must raise ValueError."""
        ctx = _setup_prerequisites(db_session)
        payload = PayrollCreate.model_construct(
            tenant_id=ctx["tenant"].id,
            employee_id=ctx["employee"].id,
            contract_id=ctx["contract"].id,
            period_year=2025,
            period_month=1,
            status="invalid_status",
            **_PAYROLL_NUMERIC_DEFAULTS,
        )

        with pytest.raises(ValueError, match="Invalid status"):
            create_payroll(db_session, payload)

    def test_create_with_optional_defaults(self, db_session):
        """Verify that optional fields with defaults are populated."""
        ctx = _setup_prerequisites(db_session)
        payload = _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id)
        result = create_payroll(db_session, payload)

        assert result.overtime_hours == Decimal("0")
        assert result.overtime_amount == Decimal("0")
        assert result.bonus_amount == Decimal("0")
        assert result.supplement_amount == Decimal("0")
        assert result.child_bonus == Decimal("0")
        assert result.pillar2_amount == Decimal("0")


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetPayroll:
    """Tests for get_payroll."""

    def test_get_existing(self, db_session):
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        fetched = get_payroll(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.net_wage == created.net_wage

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_payroll(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListPayrolls:
    """Tests for list_payrolls."""

    def test_list_empty(self, db_session):
        result = list_payrolls(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        ctx = _setup_prerequisites(db_session)

        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=1,
            ),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=2,
            ),
        )

        result = list_payrolls(db_session)
        assert len(result) == 2

    def test_list_ordering_by_period_desc(self, db_session):
        """Payrolls are ordered by year desc, month desc."""
        ctx = _setup_prerequisites(db_session)

        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_year=2024,
                period_month=12,
            ),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_year=2025,
                period_month=3,
            ),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_year=2025,
                period_month=1,
            ),
        )

        result = list_payrolls(db_session)
        assert result[0].period_year == 2025
        assert result[0].period_month == 3
        assert result[1].period_year == 2025
        assert result[1].period_month == 1
        assert result[2].period_year == 2024
        assert result[2].period_month == 12

    def test_list_scoped_by_tenant(self, db_session):
        hi = _make_health_insurer(db_session)
        ctx_a = _setup_prerequisites_unique(db_session, suffix="a", health_insurer=hi)
        ctx_b = _setup_prerequisites_unique(db_session, suffix="b", health_insurer=hi)

        create_payroll(
            db_session,
            _make_payroll_payload(ctx_a["tenant"].id, ctx_a["employee"].id, ctx_a["contract"].id),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(ctx_b["tenant"].id, ctx_b["employee"].id, ctx_b["contract"].id),
        )

        result = list_payrolls(db_session, tenant_id=ctx_a["tenant"].id)
        assert len(result) == 1
        assert result[0].tenant_id == ctx_a["tenant"].id

    def test_list_scoped_by_employee(self, db_session):
        ctx = _setup_prerequisites(db_session)
        hi = ctx["health_insurer"]
        tenant = ctx["tenant"]
        emp2 = _make_employee(
            db_session,
            tenant,
            hi,
            employee_number="EMP-002",
            first_name="Peter",
            last_name="Horváth",
            birth_number="9002021234",
        )
        contract2 = _make_contract(
            db_session,
            tenant,
            emp2,
            contract_number="ZML-002",
        )

        create_payroll(
            db_session,
            _make_payroll_payload(tenant.id, ctx["employee"].id, ctx["contract"].id),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(tenant.id, emp2.id, contract2.id),
        )

        result = list_payrolls(db_session, employee_id=ctx["employee"].id)
        assert len(result) == 1
        assert result[0].employee_id == ctx["employee"].id

    def test_list_scoped_by_status(self, db_session):
        ctx = _setup_prerequisites(db_session)

        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=1,
                status="draft",
            ),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=2,
                status="approved",
            ),
        )

        result = list_payrolls(db_session, status="draft")
        assert len(result) == 1
        assert result[0].status == "draft"

    def test_list_scoped_by_period_year(self, db_session):
        ctx = _setup_prerequisites(db_session)

        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_year=2024,
                period_month=1,
            ),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_year=2025,
                period_month=1,
            ),
        )

        result = list_payrolls(db_session, period_year=2024)
        assert len(result) == 1
        assert result[0].period_year == 2024

    def test_list_scoped_by_period_month(self, db_session):
        ctx = _setup_prerequisites(db_session)

        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=1,
            ),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=6,
            ),
        )

        result = list_payrolls(db_session, period_month=1)
        assert len(result) == 1
        assert result[0].period_month == 1

    def test_list_pagination_skip(self, db_session):
        ctx = _setup_prerequisites(db_session)

        for m in range(1, 4):
            create_payroll(
                db_session,
                _make_payroll_payload(
                    ctx["tenant"].id,
                    ctx["employee"].id,
                    ctx["contract"].id,
                    period_month=m,
                ),
            )

        result = list_payrolls(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        ctx = _setup_prerequisites(db_session)

        for m in range(1, 4):
            create_payroll(
                db_session,
                _make_payroll_payload(
                    ctx["tenant"].id,
                    ctx["employee"].id,
                    ctx["contract"].id,
                    period_month=m,
                ),
            )

        result = list_payrolls(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        ctx = _setup_prerequisites(db_session)

        for m in range(1, 7):
            create_payroll(
                db_session,
                _make_payroll_payload(
                    ctx["tenant"].id,
                    ctx["employee"].id,
                    ctx["contract"].id,
                    period_month=m,
                ),
            )

        result = list_payrolls(db_session, skip=1, limit=2)
        assert len(result) == 2

    def test_list_default_limit_is_50(self, db_session):
        """Default limit should be 50 per project convention."""
        import inspect

        sig = inspect.signature(list_payrolls)
        assert sig.parameters["limit"].default == 50

    def test_list_invalid_status_raises_value_error(self, db_session):
        """Filtering by an invalid status must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            list_payrolls(db_session, status="bad_status")


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountPayrolls:
    """Tests for count_payrolls."""

    def test_count_empty(self, db_session):
        result = count_payrolls(db_session)
        assert result == 0

    def test_count_all(self, db_session):
        ctx = _setup_prerequisites(db_session)
        for m in range(1, 4):
            create_payroll(
                db_session,
                _make_payroll_payload(
                    ctx["tenant"].id,
                    ctx["employee"].id,
                    ctx["contract"].id,
                    period_month=m,
                ),
            )

        result = count_payrolls(db_session)
        assert result == 3

    def test_count_scoped_by_tenant(self, db_session):
        hi = _make_health_insurer(db_session)
        ctx_a = _setup_prerequisites_unique(db_session, suffix="ca", health_insurer=hi)
        ctx_b = _setup_prerequisites_unique(db_session, suffix="cb", health_insurer=hi)

        create_payroll(
            db_session,
            _make_payroll_payload(ctx_a["tenant"].id, ctx_a["employee"].id, ctx_a["contract"].id),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(ctx_b["tenant"].id, ctx_b["employee"].id, ctx_b["contract"].id),
        )

        assert count_payrolls(db_session, tenant_id=ctx_a["tenant"].id) == 1
        assert count_payrolls(db_session, tenant_id=ctx_b["tenant"].id) == 1

    def test_count_scoped_by_status(self, db_session):
        ctx = _setup_prerequisites(db_session)

        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=1,
                status="draft",
            ),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=2,
                status="approved",
            ),
        )

        assert count_payrolls(db_session, status="draft") == 1
        assert count_payrolls(db_session, status="approved") == 1

    def test_count_scoped_by_period_year(self, db_session):
        ctx = _setup_prerequisites(db_session)

        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_year=2024,
                period_month=1,
            ),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_year=2025,
                period_month=1,
            ),
        )

        assert count_payrolls(db_session, period_year=2024) == 1
        assert count_payrolls(db_session, period_year=2025) == 1

    def test_count_scoped_by_period_month(self, db_session):
        ctx = _setup_prerequisites(db_session)

        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=1,
            ),
        )
        create_payroll(
            db_session,
            _make_payroll_payload(
                ctx["tenant"].id,
                ctx["employee"].id,
                ctx["contract"].id,
                period_month=6,
            ),
        )

        assert count_payrolls(db_session, period_month=1) == 1
        assert count_payrolls(db_session, period_month=6) == 1

    def test_count_invalid_status_raises_value_error(self, db_session):
        """Counting with an invalid status must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            count_payrolls(db_session, status="bad_status")


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdatePayroll:
    """Tests for update_payroll."""

    def test_update_single_field(self, db_session):
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        updated = update_payroll(
            db_session,
            created.id,
            PayrollUpdate(status="calculated"),
        )

        assert updated is not None
        assert updated.status == "calculated"
        # unchanged fields stay the same
        assert updated.net_wage == Decimal("1831.60")

    def test_update_multiple_fields(self, db_session):
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        updated = update_payroll(
            db_session,
            created.id,
            PayrollUpdate(
                status="approved",
                net_wage=Decimal("1900.00"),
                gross_wage=Decimal("2600.00"),
            ),
        )

        assert updated is not None
        assert updated.status == "approved"
        assert updated.net_wage == Decimal("1900.00")
        assert updated.gross_wage == Decimal("2600.00")

    def test_update_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            update_payroll(
                db_session,
                uuid4(),
                PayrollUpdate(status="calculated"),
            )

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        updated = update_payroll(
            db_session,
            created.id,
            PayrollUpdate(),
        )

        assert updated is not None
        assert updated.status == created.status
        assert updated.net_wage == created.net_wage

    def test_update_invalid_status_raises_value_error(self, db_session):
        """Updating with an invalid status must raise ValueError."""
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        payload = PayrollUpdate.model_construct(status="invalid_status")

        with pytest.raises(ValueError, match="Invalid status"):
            update_payroll(db_session, created.id, payload)

    def test_update_invalid_ledger_sync_status_raises_value_error(self, db_session):
        """Updating with an invalid ledger_sync_status must raise ValueError."""
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        payload = PayrollUpdate.model_construct(ledger_sync_status="invalid_sync")

        with pytest.raises(ValueError, match="Invalid ledger_sync_status"):
            update_payroll(db_session, created.id, payload)

    def test_update_ledger_sync_status(self, db_session):
        """Valid ledger_sync_status transitions."""
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        updated = update_payroll(
            db_session,
            created.id,
            PayrollUpdate(ledger_sync_status="synced"),
        )

        assert updated.ledger_sync_status == "synced"

    def test_update_ai_validation_result(self, db_session):
        """Update the JSON ai_validation_result field."""
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        ai_result = {"confidence": 0.95, "anomalies": []}
        updated = update_payroll(
            db_session,
            created.id,
            PayrollUpdate(ai_validation_result=ai_result),
        )

        assert updated.ai_validation_result == ai_result


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeletePayroll:
    """Tests for delete_payroll."""

    def test_delete_existing(self, db_session):
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        result = delete_payroll(db_session, created.id)

        assert result is True
        assert get_payroll(db_session, created.id) is None

    def test_delete_with_pay_slips_raises_value_error(self, db_session):
        """Deleting a payroll that has pay slip(s) must raise ValueError."""
        ctx = _setup_prerequisites(db_session)
        created = create_payroll(
            db_session,
            _make_payroll_payload(ctx["tenant"].id, ctx["employee"].id, ctx["contract"].id),
        )

        # Create a PaySlip referencing this payroll
        pay_slip = PaySlip(
            tenant_id=ctx["tenant"].id,
            payroll_id=created.id,
            employee_id=ctx["employee"].id,
            period_year=2025,
            period_month=1,
            pdf_path="/opt/nex-payroll-src/data/payslips/test/2025/01/EMP-001.pdf",
        )
        db_session.add(pay_slip)
        db_session.flush()

        with pytest.raises(ValueError, match="pay slip"):
            delete_payroll(db_session, created.id)

    def test_delete_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            delete_payroll(db_session, uuid4())
