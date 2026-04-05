"""Tests for Payroll model (app.models.payroll)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Integer, Numeric, String, inspect, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.payroll import Payroll
from app.models.tenant import Tenant
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent."""
    t = Tenant(
        name="Payroll Test Firma s.r.o.",
        ico="99000001",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000099001",
        schema_name="tenant_test_payroll",
    )
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture()
def health_insurer(db_session):
    """Create a HealthInsurer required as FK parent for Employee."""
    hi = HealthInsurer(
        code="25",
        name="Všeobecná zdravotná poisťovňa, a.s.",
        iban="SK0000000000000000000025",
    )
    db_session.add(hi)
    db_session.flush()
    return hi


@pytest.fixture()
def employee(db_session, tenant, health_insurer):
    """Create an Employee required as FK parent for Payroll."""
    emp = Employee(
        tenant_id=tenant.id,
        employee_number="EMP-PR-001",
        first_name="Peter",
        last_name="Horváth",
        birth_date=date(1985, 3, 10),
        birth_number="8503100001",
        gender="M",
        address_street="Dunajská 5",
        address_city="Bratislava",
        address_zip="81108",
        bank_iban="SK3100000000000000000088",
        health_insurer_id=health_insurer.id,
        tax_declaration_type="standard",
        hire_date=date(2023, 1, 1),
    )
    db_session.add(emp)
    db_session.flush()
    return emp


@pytest.fixture()
def contract(db_session, tenant, employee):
    """Create a Contract required as FK parent for Payroll."""
    c = Contract(
        tenant_id=tenant.id,
        employee_id=employee.id,
        contract_number="ZML-PR-2024-001",
        contract_type="permanent",
        job_title="Účtovník",
        wage_type="monthly",
        base_wage=Decimal("2500.00"),
        start_date=date(2023, 1, 1),
    )
    db_session.add(c)
    db_session.flush()
    return c


@pytest.fixture()
def user(db_session, tenant):
    """Create a User for approved_by FK."""
    u = User(
        tenant_id=tenant.id,
        username="payroll_approver",
        email="approver@test.sk",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="accountant",
    )
    db_session.add(u)
    db_session.flush()
    return u


def _make_payroll(tenant, employee, contract, **overrides):
    """Return a Payroll instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "employee_id": employee.id,
        "contract_id": contract.id,
        "period_year": 2025,
        "period_month": 1,
        # Gross components
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
        "nczd_applied": Decimal("410.24"),
        "tax_base": Decimal("1754.76"),
        "tax_advance": Decimal("333.40"),
        "tax_after_bonus": Decimal("333.40"),
        # Net
        "net_wage": Decimal("1831.60"),
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
        # Total cost
        "total_employer_cost": Decimal("3392.50"),
    }
    defaults.update(overrides)
    return Payroll(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestPayrollSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert Payroll.__tablename__ == "payrolls"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(Payroll, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(Payroll, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(Payroll, TimestampMixin)


class TestPayrollColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(Payroll)

    # -- PK --

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    # -- FK columns --

    def test_tenant_id_column(self):
        col = self.mapper.columns["tenant_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_employee_id_column(self):
        col = self.mapper.columns["employee_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_contract_id_column(self):
        col = self.mapper.columns["contract_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_approved_by_column(self):
        col = self.mapper.columns["approved_by"]
        assert isinstance(col.type, UUID)
        assert col.nullable is True

    # -- Period --

    def test_period_year_column(self):
        col = self.mapper.columns["period_year"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_period_month_column(self):
        col = self.mapper.columns["period_month"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    # -- Status --

    def test_status_column(self):
        col = self.mapper.columns["status"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False
        assert col.server_default is not None

    def test_status_server_default_draft(self):
        col = self.mapper.columns["status"]
        assert "draft" in str(col.server_default.arg)

    # -- Gross wage components --

    def test_base_wage_column(self):
        col = self.mapper.columns["base_wage"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 2
        assert col.nullable is False

    def test_overtime_hours_column(self):
        col = self.mapper.columns["overtime_hours"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 6
        assert col.type.scale == 2
        assert col.nullable is False
        assert col.server_default is not None
        assert "0" in str(col.server_default.arg)

    def test_overtime_amount_column(self):
        col = self.mapper.columns["overtime_amount"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 2
        assert col.nullable is False
        assert col.server_default is not None

    def test_bonus_amount_column(self):
        col = self.mapper.columns["bonus_amount"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False
        assert col.server_default is not None

    def test_supplement_amount_column(self):
        col = self.mapper.columns["supplement_amount"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False
        assert col.server_default is not None

    def test_gross_wage_column(self):
        col = self.mapper.columns["gross_wage"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 2
        assert col.nullable is False

    # -- SP employee --

    def test_sp_assessment_base_column(self):
        col = self.mapper.columns["sp_assessment_base"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_nemocenske_column(self):
        col = self.mapper.columns["sp_nemocenske"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_starobne_column(self):
        col = self.mapper.columns["sp_starobne"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_invalidne_column(self):
        col = self.mapper.columns["sp_invalidne"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_nezamestnanost_column(self):
        col = self.mapper.columns["sp_nezamestnanost"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_employee_total_column(self):
        col = self.mapper.columns["sp_employee_total"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    # -- ZP employee --

    def test_zp_assessment_base_column(self):
        col = self.mapper.columns["zp_assessment_base"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_zp_employee_column(self):
        col = self.mapper.columns["zp_employee"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    # -- Tax --

    def test_partial_tax_base_column(self):
        col = self.mapper.columns["partial_tax_base"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_nczd_applied_column(self):
        col = self.mapper.columns["nczd_applied"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_tax_base_column(self):
        col = self.mapper.columns["tax_base"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_tax_advance_column(self):
        col = self.mapper.columns["tax_advance"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_child_bonus_column(self):
        col = self.mapper.columns["child_bonus"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False
        assert col.server_default is not None
        assert "0" in str(col.server_default.arg)

    def test_tax_after_bonus_column(self):
        col = self.mapper.columns["tax_after_bonus"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    # -- Net --

    def test_net_wage_column(self):
        col = self.mapper.columns["net_wage"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 2
        assert col.nullable is False

    # -- SP employer --

    def test_sp_employer_nemocenske_column(self):
        col = self.mapper.columns["sp_employer_nemocenske"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_employer_starobne_column(self):
        col = self.mapper.columns["sp_employer_starobne"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_employer_invalidne_column(self):
        col = self.mapper.columns["sp_employer_invalidne"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_employer_nezamestnanost_column(self):
        col = self.mapper.columns["sp_employer_nezamestnanost"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_employer_garancne_column(self):
        col = self.mapper.columns["sp_employer_garancne"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_employer_rezervny_column(self):
        col = self.mapper.columns["sp_employer_rezervny"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_employer_kurzarbeit_column(self):
        col = self.mapper.columns["sp_employer_kurzarbeit"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_employer_urazove_column(self):
        col = self.mapper.columns["sp_employer_urazove"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    def test_sp_employer_total_column(self):
        col = self.mapper.columns["sp_employer_total"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    # -- ZP employer --

    def test_zp_employer_column(self):
        col = self.mapper.columns["zp_employer"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    # -- Total employer cost --

    def test_total_employer_cost_column(self):
        col = self.mapper.columns["total_employer_cost"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False

    # -- Pillar 2 --

    def test_pillar2_amount_column(self):
        col = self.mapper.columns["pillar2_amount"]
        assert isinstance(col.type, Numeric)
        assert col.nullable is False
        assert col.server_default is not None
        assert "0" in str(col.server_default.arg)

    # -- AI validation --

    def test_ai_validation_result_column(self):
        col = self.mapper.columns["ai_validation_result"]
        assert isinstance(col.type, JSON)
        assert col.nullable is True

    # -- Ledger sync --

    def test_ledger_sync_status_column(self):
        col = self.mapper.columns["ledger_sync_status"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is True

    # -- Approval metadata --

    def test_calculated_at_column(self):
        col = self.mapper.columns["calculated_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is True

    def test_approved_at_column(self):
        col = self.mapper.columns["approved_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is True

    # -- Timestamps from mixin --

    def test_created_at_column(self):
        col = self.mapper.columns["created_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is False
        assert col.server_default is not None

    def test_updated_at_column(self):
        col = self.mapper.columns["updated_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is False
        assert col.server_default is not None

    # -- Constraints --

    def test_unique_constraint_tenant_employee_period(self):
        constraints = Payroll.__table__.constraints
        uq_names = [c.name for c in constraints if c.name and c.name.startswith("uq_")]
        assert "uq_payrolls_tenant_employee_period" in uq_names

    def test_check_constraint_status(self):
        constraints = Payroll.__table__.constraints
        ck_names = [c.name for c in constraints if c.name and c.name.startswith("ck_")]
        assert "ck_payrolls_status" in ck_names

    def test_check_constraint_ledger_sync_status(self):
        constraints = Payroll.__table__.constraints
        ck_names = [c.name for c in constraints if c.name and c.name.startswith("ck_")]
        assert "ck_payrolls_ledger_sync_status" in ck_names

    # -- Indexes --

    def test_index_tenant_period_status(self):
        indexes = Payroll.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_payrolls_tenant_period_status" in ix_names


# ===================================================================
# Repr
# ===================================================================


class TestPayrollRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        emp_id = uuid.uuid4()
        payroll = Payroll(
            employee_id=emp_id,
            period_year=2025,
            period_month=3,
            status="calculated",
            net_wage=Decimal("1831.60"),
        )
        result = repr(payroll)
        assert "Payroll" in result
        assert "2025/3" in result
        assert "calculated" in result
        assert "1831.60" in result

    def test_repr_contains_employee_id(self):
        emp_id = uuid.uuid4()
        payroll = Payroll(
            employee_id=emp_id,
            period_year=2025,
            period_month=1,
            status="draft",
            net_wage=Decimal("0.00"),
        )
        result = repr(payroll)
        assert str(emp_id) in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestPayrollConstraints:
    """DB-level constraint enforcement."""

    def test_fk_tenant_nonexistent(self, db_session, employee, contract):
        """FK to tenant must exist."""
        payroll = _make_payroll(
            type("T", (), {"id": uuid.uuid4()})(),
            employee,
            contract,
        )
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_nonexistent(self, db_session, tenant, contract):
        """FK to employee must exist."""
        payroll = _make_payroll(
            tenant,
            type("E", (), {"id": uuid.uuid4()})(),
            contract,
        )
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_contract_nonexistent(self, db_session, tenant, employee):
        """FK to contract must exist."""
        payroll = _make_payroll(
            tenant,
            employee,
            type("C", (), {"id": uuid.uuid4()})(),
        )
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_approved_by_nonexistent(self, db_session, tenant, employee, contract):
        """FK to users (approved_by) must exist if provided."""
        payroll = _make_payroll(tenant, employee, contract, approved_by=uuid.uuid4())
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_status_invalid(self, db_session, tenant, employee, contract):
        """Invalid status must be rejected."""
        payroll = _make_payroll(tenant, employee, contract, status="invalid")
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_status_draft(self, db_session, tenant, employee, contract):
        payroll = _make_payroll(tenant, employee, contract, status="draft")
        db_session.add(payroll)
        db_session.flush()
        assert payroll.status == "draft"

    def test_check_status_calculated(self, db_session, tenant, employee, contract):
        payroll = _make_payroll(tenant, employee, contract, status="calculated")
        db_session.add(payroll)
        db_session.flush()
        assert payroll.status == "calculated"

    def test_check_status_approved(self, db_session, tenant, employee, contract):
        payroll = _make_payroll(tenant, employee, contract, status="approved")
        db_session.add(payroll)
        db_session.flush()
        assert payroll.status == "approved"

    def test_check_status_paid(self, db_session, tenant, employee, contract):
        payroll = _make_payroll(tenant, employee, contract, status="paid")
        db_session.add(payroll)
        db_session.flush()
        assert payroll.status == "paid"

    def test_check_ledger_sync_status_invalid(self, db_session, tenant, employee, contract):
        """Invalid ledger_sync_status must be rejected."""
        payroll = _make_payroll(tenant, employee, contract, ledger_sync_status="unknown")
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_ledger_sync_status_pending(self, db_session, tenant, employee, contract):
        payroll = _make_payroll(tenant, employee, contract, ledger_sync_status="pending")
        db_session.add(payroll)
        db_session.flush()
        assert payroll.ledger_sync_status == "pending"

    def test_check_ledger_sync_status_synced(self, db_session, tenant, employee, contract):
        payroll = _make_payroll(tenant, employee, contract, ledger_sync_status="synced")
        db_session.add(payroll)
        db_session.flush()
        assert payroll.ledger_sync_status == "synced"

    def test_check_ledger_sync_status_error(self, db_session, tenant, employee, contract):
        payroll = _make_payroll(tenant, employee, contract, ledger_sync_status="error")
        db_session.add(payroll)
        db_session.flush()
        assert payroll.ledger_sync_status == "error"

    def test_unique_tenant_employee_period(self, db_session, tenant, employee, contract):
        """Duplicate (tenant, employee, period_year, period_month) must fail."""
        p1 = _make_payroll(tenant, employee, contract)
        db_session.add(p1)
        db_session.flush()

        p2 = _make_payroll(tenant, employee, contract)
        db_session.add(p2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_base_wage(self, db_session, tenant, employee, contract):
        """base_wage cannot be NULL."""
        payroll = _make_payroll(tenant, employee, contract, base_wage=None)
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_gross_wage(self, db_session, tenant, employee, contract):
        """gross_wage cannot be NULL."""
        payroll = _make_payroll(tenant, employee, contract, gross_wage=None)
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_net_wage(self, db_session, tenant, employee, contract):
        """net_wage cannot be NULL."""
        payroll = _make_payroll(tenant, employee, contract, net_wage=None)
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_period_year(self, db_session, tenant, employee, contract):
        """period_year cannot be NULL."""
        payroll = _make_payroll(tenant, employee, contract, period_year=None)
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_period_month(self, db_session, tenant, employee, contract):
        """period_month cannot be NULL."""
        payroll = _make_payroll(tenant, employee, contract, period_month=None)
        db_session.add(payroll)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    # -- FK RESTRICT delete tests (raw SQL per checklist) --

    def test_fk_tenant_restrict_delete(self, db_session, tenant, employee, contract):
        """Deleting a tenant with payrolls must be rejected.

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        payroll = _make_payroll(tenant, employee, contract)
        db_session.add(payroll)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM public.tenants WHERE id = :id"),
                {"id": str(tenant.id)},
            )
        db_session.rollback()

    def test_fk_employee_restrict_delete(self, db_session, tenant, employee, contract):
        """Deleting an employee with payrolls must be rejected."""
        payroll = _make_payroll(tenant, employee, contract)
        db_session.add(payroll)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM employees WHERE id = :id"),
                {"id": str(employee.id)},
            )
        db_session.rollback()

    def test_fk_contract_restrict_delete(self, db_session, tenant, employee, contract):
        """Deleting a contract with payrolls must be rejected."""
        payroll = _make_payroll(tenant, employee, contract)
        db_session.add(payroll)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM contracts WHERE id = :id"),
                {"id": str(contract.id)},
            )
        db_session.rollback()

    def test_fk_user_restrict_delete(self, db_session, tenant, employee, contract, user):
        """Deleting a user referenced as approved_by must be rejected."""
        payroll = _make_payroll(tenant, employee, contract, approved_by=user.id)
        db_session.add(payroll)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": str(user.id)},
            )
        db_session.rollback()


# ===================================================================
# Database integration tests
# ===================================================================


class TestPayrollDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, employee, contract, user):
        """Full create with all fields — verify round-trip."""
        payroll = _make_payroll(
            tenant,
            employee,
            contract,
            status="approved",
            overtime_hours=Decimal("8.50"),
            overtime_amount=Decimal("150.00"),
            bonus_amount=Decimal("200.00"),
            supplement_amount=Decimal("50.00"),
            child_bonus=Decimal("100.00"),
            pillar2_amount=Decimal("50.00"),
            ai_validation_result={"confidence": 0.95, "anomalies": []},
            ledger_sync_status="pending",
            approved_by=user.id,
        )
        db_session.add(payroll)
        db_session.flush()

        assert payroll.id is not None
        assert payroll.created_at is not None
        assert payroll.updated_at is not None
        assert payroll.tenant_id == tenant.id
        assert payroll.employee_id == employee.id
        assert payroll.contract_id == contract.id
        assert payroll.period_year == 2025
        assert payroll.period_month == 1
        assert payroll.status == "approved"
        assert payroll.base_wage == Decimal("2500.00")
        assert payroll.overtime_hours == Decimal("8.50")
        assert payroll.overtime_amount == Decimal("150.00")
        assert payroll.bonus_amount == Decimal("200.00")
        assert payroll.supplement_amount == Decimal("50.00")
        assert payroll.gross_wage == Decimal("2500.00")
        assert payroll.net_wage == Decimal("1831.60")
        assert payroll.child_bonus == Decimal("100.00")
        assert payroll.pillar2_amount == Decimal("50.00")
        assert payroll.ai_validation_result == {"confidence": 0.95, "anomalies": []}
        assert payroll.ledger_sync_status == "pending"
        assert payroll.approved_by == user.id

    def test_create_minimal_defaults(self, db_session, tenant, employee, contract):
        """Create with only required fields — verify all server_defaults."""
        payroll = _make_payroll(tenant, employee, contract)
        db_session.add(payroll)
        db_session.flush()

        # server_defaults
        assert payroll.status == "draft"
        assert payroll.overtime_hours == Decimal("0")
        assert payroll.overtime_amount == Decimal("0")
        assert payroll.bonus_amount == Decimal("0")
        assert payroll.supplement_amount == Decimal("0")
        assert payroll.child_bonus == Decimal("0")
        assert payroll.pillar2_amount == Decimal("0")
        # nullable fields
        assert payroll.ai_validation_result is None
        assert payroll.ledger_sync_status is None
        assert payroll.calculated_at is None
        assert payroll.approved_at is None
        assert payroll.approved_by is None

    def test_status_workflow(self, db_session, tenant, employee, contract):
        """Status can be updated through workflow: draft → calculated → approved → paid."""
        payroll = _make_payroll(tenant, employee, contract, status="draft")
        db_session.add(payroll)
        db_session.flush()
        assert payroll.status == "draft"

        payroll.status = "calculated"
        db_session.flush()
        assert payroll.status == "calculated"

        payroll.status = "approved"
        db_session.flush()
        assert payroll.status == "approved"

        payroll.status = "paid"
        db_session.flush()
        assert payroll.status == "paid"

    def test_different_periods_same_employee(self, db_session, tenant, employee, contract):
        """Same employee can have payrolls for different periods."""
        p1 = _make_payroll(tenant, employee, contract, period_year=2025, period_month=1)
        p2 = _make_payroll(tenant, employee, contract, period_year=2025, period_month=2)
        db_session.add_all([p1, p2])
        db_session.flush()
        assert p1.id != p2.id

    def test_ai_validation_result_json(self, db_session, tenant, employee, contract):
        """ai_validation_result accepts complex JSON."""
        data = {
            "confidence": 0.87,
            "anomalies": [
                {"field": "overtime_hours", "deviation": 2.5},
                {"field": "bonus_amount", "deviation": 1.8},
            ],
            "validated_at": "2025-01-15T10:30:00",
        }
        payroll = _make_payroll(tenant, employee, contract, ai_validation_result=data)
        db_session.add(payroll)
        db_session.flush()
        assert payroll.ai_validation_result["confidence"] == 0.87
        assert len(payroll.ai_validation_result["anomalies"]) == 2

    def test_approved_by_optional(self, db_session, tenant, employee, contract):
        """approved_by can be NULL (not yet approved)."""
        payroll = _make_payroll(tenant, employee, contract, approved_by=None)
        db_session.add(payroll)
        db_session.flush()
        assert payroll.approved_by is None

    def test_approved_by_with_user(self, db_session, tenant, employee, contract, user):
        """approved_by can reference a valid user."""
        payroll = _make_payroll(tenant, employee, contract, approved_by=user.id)
        db_session.add(payroll)
        db_session.flush()
        assert payroll.approved_by == user.id

    def test_decimal_precision(self, db_session, tenant, employee, contract):
        """Numeric(10,2) columns preserve cent precision."""
        payroll = _make_payroll(
            tenant,
            employee,
            contract,
            base_wage=Decimal("1234.56"),
            gross_wage=Decimal("1234.56"),
            net_wage=Decimal("987.65"),
        )
        db_session.add(payroll)
        db_session.flush()
        assert payroll.base_wage == Decimal("1234.56")
        assert payroll.gross_wage == Decimal("1234.56")
        assert payroll.net_wage == Decimal("987.65")
