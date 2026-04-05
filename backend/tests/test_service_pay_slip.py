"""Tests for PaySlip service layer."""

from datetime import UTC, date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.pay_slip import PaySlip
from app.models.payroll import Payroll
from app.models.tenant import Tenant
from app.schemas.pay_slip import PaySlipCreate, PaySlipUpdate
from app.services.pay_slip import (
    count_pay_slips,
    create_pay_slip,
    delete_pay_slip,
    get_pay_slip,
    list_pay_slips,
    update_pay_slip,
)

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


def _make_payroll(db_session, tenant, employee, contract, **overrides) -> Payroll:
    """Insert a minimal Payroll and flush."""
    defaults = {
        "tenant_id": tenant.id,
        "employee_id": employee.id,
        "contract_id": contract.id,
        "period_year": 2025,
        "period_month": 1,
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
    defaults.update(overrides)
    p = Payroll(**defaults)
    db_session.add(p)
    db_session.flush()
    return p


def _setup_parent_chain(db_session, **tenant_overrides):
    """Create full FK parent chain: Tenant → HealthInsurer → Employee → Contract → Payroll.

    Returns dict with all created entities.
    """
    tenant = _make_tenant(db_session, **tenant_overrides)
    hi = _make_health_insurer(db_session)
    employee = _make_employee(db_session, tenant, hi)
    contract = _make_contract(db_session, tenant, employee)
    payroll = _make_payroll(db_session, tenant, employee, contract)
    return {
        "tenant": tenant,
        "health_insurer": hi,
        "employee": employee,
        "contract": contract,
        "payroll": payroll,
    }


# Counter for unique values across helper calls within a single test session
_counter = 0


def _setup_parent_chain_unique(db_session, *, suffix: str = ""):
    """Create full FK parent chain with unique ICO/schema/employee_number/contract.

    Each call produces a completely independent set of parent records.
    """
    global _counter  # noqa: PLW0603
    _counter += 1
    idx = f"{_counter}{suffix}"

    tenant = _make_tenant(
        db_session,
        ico=f"9{idx:0>7}"[:8],
        schema_name=f"tenant_unique_{idx}",
    )
    hi = _make_health_insurer(
        db_session,
        code=f"U{idx}"[:4],
        iban=f"SK00000000000000000U{idx}"[:24],
    )
    employee = _make_employee(
        db_session,
        tenant,
        hi,
        employee_number=f"EMP-U-{idx}",
    )
    contract = _make_contract(
        db_session,
        tenant,
        employee,
        contract_number=f"ZML-U-{idx}",
    )
    payroll = _make_payroll(db_session, tenant, employee, contract)
    return {
        "tenant": tenant,
        "health_insurer": hi,
        "employee": employee,
        "contract": contract,
        "payroll": payroll,
    }


def _make_pay_slip_payload(
    tenant_id,
    payroll_id,
    employee_id,
    **overrides,
) -> PaySlipCreate:
    """Build a valid PaySlipCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "payroll_id": payroll_id,
        "employee_id": employee_id,
        "period_year": 2025,
        "period_month": 1,
        "pdf_path": "/opt/nex-payroll-src/data/payslips/tenant1/2025/01/EMP001.pdf",
        "file_size_bytes": 52480,
    }
    defaults.update(overrides)
    return PaySlipCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreatePaySlip:
    """Tests for create_pay_slip."""

    def test_create_returns_model_instance(self, db_session):
        chain = _setup_parent_chain(db_session)
        payload = _make_pay_slip_payload(
            chain["tenant"].id,
            chain["payroll"].id,
            chain["employee"].id,
        )

        result = create_pay_slip(db_session, payload)

        assert isinstance(result, PaySlip)
        assert result.id is not None
        assert result.tenant_id == chain["tenant"].id
        assert result.payroll_id == chain["payroll"].id
        assert result.employee_id == chain["employee"].id
        assert result.period_year == 2025
        assert result.period_month == 1
        assert result.pdf_path == "/opt/nex-payroll-src/data/payslips/tenant1/2025/01/EMP001.pdf"
        assert result.file_size_bytes == 52480

    def test_create_without_file_size(self, db_session):
        """file_size_bytes is optional and can be None."""
        chain = _setup_parent_chain(db_session)
        payload = _make_pay_slip_payload(
            chain["tenant"].id,
            chain["payroll"].id,
            chain["employee"].id,
            file_size_bytes=None,
        )

        result = create_pay_slip(db_session, payload)

        assert result.file_size_bytes is None

    def test_create_different_periods(self, db_session):
        """Pay slips for different periods of different payrolls."""
        chain_a = _setup_parent_chain_unique(db_session, suffix="a")
        chain_b = _setup_parent_chain_unique(db_session, suffix="b")

        slip_jan = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
                period_month=1,
            ),
        )
        slip_feb = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
                period_month=2,
                pdf_path="/data/payslips/feb.pdf",
            ),
        )

        assert slip_jan.period_month == 1
        assert slip_feb.period_month == 2

    def test_create_duplicate_tenant_payroll_raises_value_error(self, db_session):
        """Duplicate (tenant_id, payroll_id) raises ValueError at service level."""
        chain = _setup_parent_chain_unique(db_session, suffix="dup")
        payload = _make_pay_slip_payload(
            chain["tenant"].id,
            chain["payroll"].id,
            chain["employee"].id,
        )

        create_pay_slip(db_session, payload)

        with pytest.raises(ValueError, match="already exists"):
            create_pay_slip(db_session, payload)


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetPaySlip:
    """Tests for get_pay_slip."""

    def test_get_existing(self, db_session):
        chain = _setup_parent_chain(db_session)
        created = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain["tenant"].id,
                chain["payroll"].id,
                chain["employee"].id,
            ),
        )

        fetched = get_pay_slip(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.pdf_path == created.pdf_path

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_pay_slip(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListPaySlips:
    """Tests for list_pay_slips."""

    def test_list_empty(self, db_session):
        result = list_pay_slips(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="la")
        chain_b = _setup_parent_chain_unique(db_session, suffix="lb")

        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
                pdf_path="/data/payslips/b.pdf",
            ),
        )

        result = list_pay_slips(db_session)
        assert len(result) == 2

    def test_list_ordering_by_period_desc(self, db_session):
        """Pay slips are ordered by year desc, month desc."""
        chain_a = _setup_parent_chain_unique(db_session, suffix="oa")
        chain_b = _setup_parent_chain_unique(db_session, suffix="ob")
        chain_c = _setup_parent_chain_unique(db_session, suffix="oc")

        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
                period_year=2024,
                period_month=12,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
                period_year=2025,
                period_month=3,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_c["tenant"].id,
                chain_c["payroll"].id,
                chain_c["employee"].id,
                period_year=2025,
                period_month=1,
            ),
        )

        result = list_pay_slips(db_session)
        assert result[0].period_year == 2025
        assert result[0].period_month == 3
        assert result[1].period_year == 2025
        assert result[1].period_month == 1
        assert result[2].period_year == 2024
        assert result[2].period_month == 12

    def test_list_scoped_by_tenant(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="ta")
        chain_b = _setup_parent_chain_unique(db_session, suffix="tb")

        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
            ),
        )

        result = list_pay_slips(db_session, tenant_id=chain_a["tenant"].id)
        assert len(result) == 1
        assert result[0].tenant_id == chain_a["tenant"].id

    def test_list_scoped_by_employee(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="ea")
        chain_b = _setup_parent_chain_unique(db_session, suffix="eb")

        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
            ),
        )

        result = list_pay_slips(db_session, employee_id=chain_a["employee"].id)
        assert len(result) == 1
        assert result[0].employee_id == chain_a["employee"].id

    def test_list_scoped_by_payroll(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="pa")
        chain_b = _setup_parent_chain_unique(db_session, suffix="pb")

        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
            ),
        )

        result = list_pay_slips(db_session, payroll_id=chain_a["payroll"].id)
        assert len(result) == 1
        assert result[0].payroll_id == chain_a["payroll"].id

    def test_list_scoped_by_period_year(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="ya")
        chain_b = _setup_parent_chain_unique(db_session, suffix="yb")

        # Override payroll period_year to match pay_slip period
        payroll_a = _make_payroll(
            db_session,
            chain_a["tenant"],
            chain_a["employee"],
            chain_a["contract"],
            period_year=2024,
            period_month=6,
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                payroll_a.id,
                chain_a["employee"].id,
                period_year=2024,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
                period_year=2025,
            ),
        )

        result = list_pay_slips(db_session, period_year=2024)
        assert len(result) == 1
        assert result[0].period_year == 2024

    def test_list_scoped_by_period_month(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="ma")
        chain_b = _setup_parent_chain_unique(db_session, suffix="mb")

        payroll_b = _make_payroll(
            db_session,
            chain_b["tenant"],
            chain_b["employee"],
            chain_b["contract"],
            period_month=6,
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
                period_month=1,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                payroll_b.id,
                chain_b["employee"].id,
                period_month=6,
            ),
        )

        result = list_pay_slips(db_session, period_month=1)
        assert len(result) == 1
        assert result[0].period_month == 1

    def test_list_pagination_skip(self, db_session):
        chains = [_setup_parent_chain_unique(db_session, suffix=f"sk{i}") for i in range(3)]

        for ch in chains:
            create_pay_slip(
                db_session,
                _make_pay_slip_payload(
                    ch["tenant"].id,
                    ch["payroll"].id,
                    ch["employee"].id,
                ),
            )

        result = list_pay_slips(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        chains = [_setup_parent_chain_unique(db_session, suffix=f"lm{i}") for i in range(3)]

        for ch in chains:
            create_pay_slip(
                db_session,
                _make_pay_slip_payload(
                    ch["tenant"].id,
                    ch["payroll"].id,
                    ch["employee"].id,
                ),
            )

        result = list_pay_slips(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        chains = [_setup_parent_chain_unique(db_session, suffix=f"sl{i}") for i in range(6)]

        for ch in chains:
            create_pay_slip(
                db_session,
                _make_pay_slip_payload(
                    ch["tenant"].id,
                    ch["payroll"].id,
                    ch["employee"].id,
                ),
            )

        result = list_pay_slips(db_session, skip=1, limit=2)
        assert len(result) == 2

    def test_list_default_limit_is_50(self, db_session):
        """Default limit should be 50 per project convention."""
        import inspect

        sig = inspect.signature(list_pay_slips)
        assert sig.parameters["limit"].default == 50


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountPaySlips:
    """Tests for count_pay_slips."""

    def test_count_empty(self, db_session):
        result = count_pay_slips(db_session)
        assert result == 0

    def test_count_all(self, db_session):
        chains = [_setup_parent_chain_unique(db_session, suffix=f"ct{i}") for i in range(3)]

        for ch in chains:
            create_pay_slip(
                db_session,
                _make_pay_slip_payload(
                    ch["tenant"].id,
                    ch["payroll"].id,
                    ch["employee"].id,
                ),
            )

        result = count_pay_slips(db_session)
        assert result == 3

    def test_count_scoped_by_tenant(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="cta")
        chain_b = _setup_parent_chain_unique(db_session, suffix="ctb")

        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
            ),
        )

        assert count_pay_slips(db_session, tenant_id=chain_a["tenant"].id) == 1
        assert count_pay_slips(db_session, tenant_id=chain_b["tenant"].id) == 1

    def test_count_scoped_by_employee(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="cea")
        chain_b = _setup_parent_chain_unique(db_session, suffix="ceb")

        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
            ),
        )

        assert count_pay_slips(db_session, employee_id=chain_a["employee"].id) == 1
        assert count_pay_slips(db_session, employee_id=chain_b["employee"].id) == 1

    def test_count_scoped_by_payroll(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="cpa")
        chain_b = _setup_parent_chain_unique(db_session, suffix="cpb")

        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
            ),
        )

        assert count_pay_slips(db_session, payroll_id=chain_a["payroll"].id) == 1
        assert count_pay_slips(db_session, payroll_id=chain_b["payroll"].id) == 1

    def test_count_scoped_by_period_year(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="cya")
        chain_b = _setup_parent_chain_unique(db_session, suffix="cyb")

        payroll_a = _make_payroll(
            db_session,
            chain_a["tenant"],
            chain_a["employee"],
            chain_a["contract"],
            period_year=2024,
            period_month=6,
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                payroll_a.id,
                chain_a["employee"].id,
                period_year=2024,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                chain_b["payroll"].id,
                chain_b["employee"].id,
                period_year=2025,
            ),
        )

        assert count_pay_slips(db_session, period_year=2024) == 1
        assert count_pay_slips(db_session, period_year=2025) == 1

    def test_count_scoped_by_period_month(self, db_session):
        chain_a = _setup_parent_chain_unique(db_session, suffix="cma")
        chain_b = _setup_parent_chain_unique(db_session, suffix="cmb")

        payroll_b = _make_payroll(
            db_session,
            chain_b["tenant"],
            chain_b["employee"],
            chain_b["contract"],
            period_month=6,
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
                period_month=1,
            ),
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_b["tenant"].id,
                payroll_b.id,
                chain_b["employee"].id,
                period_month=6,
            ),
        )

        assert count_pay_slips(db_session, period_month=1) == 1
        assert count_pay_slips(db_session, period_month=6) == 1


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdatePaySlip:
    """Tests for update_pay_slip."""

    def test_update_single_field(self, db_session):
        chain = _setup_parent_chain(db_session)
        created = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain["tenant"].id,
                chain["payroll"].id,
                chain["employee"].id,
            ),
        )

        updated = update_pay_slip(
            db_session,
            created.id,
            PaySlipUpdate(pdf_path="/new/path/payslip.pdf"),
        )

        assert updated is not None
        assert updated.pdf_path == "/new/path/payslip.pdf"
        # unchanged fields stay the same
        assert updated.file_size_bytes == created.file_size_bytes
        assert updated.period_year == created.period_year

    def test_update_multiple_fields(self, db_session):
        chain = _setup_parent_chain(db_session)
        created = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain["tenant"].id,
                chain["payroll"].id,
                chain["employee"].id,
            ),
        )

        updated = update_pay_slip(
            db_session,
            created.id,
            PaySlipUpdate(
                pdf_path="/updated/path.pdf",
                file_size_bytes=99999,
                period_year=2026,
                period_month=6,
            ),
        )

        assert updated is not None
        assert updated.pdf_path == "/updated/path.pdf"
        assert updated.file_size_bytes == 99999
        assert updated.period_year == 2026
        assert updated.period_month == 6

    def test_update_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            update_pay_slip(
                db_session,
                uuid4(),
                PaySlipUpdate(pdf_path="/does/not/matter.pdf"),
            )

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        chain = _setup_parent_chain(db_session)
        created = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain["tenant"].id,
                chain["payroll"].id,
                chain["employee"].id,
            ),
        )

        updated = update_pay_slip(
            db_session,
            created.id,
            PaySlipUpdate(),
        )

        assert updated is not None
        assert updated.pdf_path == created.pdf_path
        assert updated.file_size_bytes == created.file_size_bytes

    def test_update_downloaded_at(self, db_session):
        """Track employee download via downloaded_at field."""
        from datetime import datetime

        chain = _setup_parent_chain(db_session)
        created = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain["tenant"].id,
                chain["payroll"].id,
                chain["employee"].id,
            ),
        )
        assert created.downloaded_at is None

        now = datetime(2025, 3, 15, 10, 30, 0, tzinfo=UTC)
        updated = update_pay_slip(
            db_session,
            created.id,
            PaySlipUpdate(downloaded_at=now),
        )

        assert updated.downloaded_at == now

    def test_update_payroll_id_duplicate_raises_value_error(self, db_session):
        """Changing payroll_id to an already-used value raises ValueError."""
        chain_a = _setup_parent_chain_unique(db_session, suffix="upd_a")

        # Create two pay slips in the SAME tenant — need second payroll under same tenant
        slip_a = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                chain_a["payroll"].id,
                chain_a["employee"].id,
            ),
        )

        payroll_b = _make_payroll(
            db_session,
            chain_a["tenant"],
            chain_a["employee"],
            chain_a["contract"],
            period_month=6,
        )
        create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain_a["tenant"].id,
                payroll_b.id,
                chain_a["employee"].id,
                period_month=6,
                pdf_path="/data/payslips/b.pdf",
            ),
        )

        # Try to update slip_a's payroll_id to payroll_b (already used in same tenant)
        with pytest.raises(ValueError, match="already exists"):
            update_pay_slip(
                db_session,
                slip_a.id,
                PaySlipUpdate(payroll_id=payroll_b.id),
            )

    def test_update_payroll_id_same_value_no_error(self, db_session):
        """Setting payroll_id to its current value should not raise."""
        chain = _setup_parent_chain_unique(db_session, suffix="upd_same")
        slip = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain["tenant"].id,
                chain["payroll"].id,
                chain["employee"].id,
            ),
        )

        # This should NOT raise — payroll_id is unchanged
        updated = update_pay_slip(
            db_session,
            slip.id,
            PaySlipUpdate(payroll_id=chain["payroll"].id),
        )
        assert updated.payroll_id == chain["payroll"].id


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeletePaySlip:
    """Tests for delete_pay_slip."""

    def test_delete_existing(self, db_session):
        chain = _setup_parent_chain(db_session)
        created = create_pay_slip(
            db_session,
            _make_pay_slip_payload(
                chain["tenant"].id,
                chain["payroll"].id,
                chain["employee"].id,
            ),
        )

        result = delete_pay_slip(db_session, created.id)

        assert result is True
        assert get_pay_slip(db_session, created.id) is None

    def test_delete_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            delete_pay_slip(db_session, uuid4())
