"""Tests for PaySlip model (app.models.pay_slip)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Integer, String, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.pay_slip import PaySlip
from app.models.payroll import Payroll
from app.models.tenant import Tenant

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent."""
    t = Tenant(
        name="PaySlip Test Firma s.r.o.",
        ico="99000020",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000099020",
        schema_name="tenant_test_pay_slip",
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
    """Create an Employee required as FK parent."""
    emp = Employee(
        tenant_id=tenant.id,
        employee_number="EMP-PS-001",
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
        contract_number="ZML-PS-2024-001",
        contract_type="permanent",
        job_title="Účtovník",
        wage_type="monthly",
        base_wage=Decimal("2500.00"),
        start_date=date(2023, 1, 1),
    )
    db_session.add(c)
    db_session.flush()
    return c


def _make_payroll(tenant, employee, contract, **overrides):
    """Return a Payroll instance with sensible defaults; overrides win."""
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
    return Payroll(**defaults)


@pytest.fixture()
def payroll(db_session, tenant, employee, contract):
    """Create a Payroll required as FK parent for PaySlip."""
    p = _make_payroll(tenant, employee, contract)
    db_session.add(p)
    db_session.flush()
    return p


def _make_pay_slip(tenant, payroll, employee, **overrides):
    """Return a PaySlip instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "payroll_id": payroll.id,
        "employee_id": employee.id,
        "period_year": 2025,
        "period_month": 1,
        "pdf_path": "/opt/nex-payroll-src/data/payslips/tenant_test/2025/01/EMP-PS-001.pdf",
    }
    defaults.update(overrides)
    return PaySlip(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestPaySlipSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert PaySlip.__tablename__ == "pay_slips"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(PaySlip, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(PaySlip, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(PaySlip, TimestampMixin)


class TestPaySlipColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(PaySlip)

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

    def test_payroll_id_column(self):
        col = self.mapper.columns["payroll_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_employee_id_column(self):
        col = self.mapper.columns["employee_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    # -- Period --

    def test_period_year_column(self):
        col = self.mapper.columns["period_year"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_period_month_column(self):
        col = self.mapper.columns["period_month"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    # -- PDF metadata --

    def test_pdf_path_column(self):
        col = self.mapper.columns["pdf_path"]
        assert isinstance(col.type, String)
        assert col.type.length == 500
        assert col.nullable is False

    def test_file_size_bytes_column(self):
        col = self.mapper.columns["file_size_bytes"]
        assert isinstance(col.type, Integer)
        assert col.nullable is True

    # -- Timestamps --

    def test_generated_at_column(self):
        col = self.mapper.columns["generated_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is False
        assert col.server_default is not None

    def test_downloaded_at_column(self):
        col = self.mapper.columns["downloaded_at"]
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

    def test_unique_constraint_tenant_payroll(self):
        constraints = PaySlip.__table__.constraints
        uq_names = [c.name for c in constraints if c.name and c.name.startswith("uq_")]
        assert "uq_pay_slips_tenant_payroll" in uq_names

    # -- Indexes --

    def test_index_tenant_employee_period(self):
        indexes = PaySlip.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_pay_slips_tenant_employee_period" in ix_names


# ===================================================================
# Repr
# ===================================================================


class TestPaySlipRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        emp_id = uuid.uuid4()
        pay_slip = PaySlip(
            employee_id=emp_id,
            period_year=2025,
            period_month=3,
            pdf_path="/some/path/to/payslip.pdf",
        )
        result = repr(pay_slip)
        assert "PaySlip" in result
        assert "2025/3" in result
        assert "/some/path/to/payslip.pdf" in result

    def test_repr_contains_employee_id(self):
        emp_id = uuid.uuid4()
        pay_slip = PaySlip(
            employee_id=emp_id,
            period_year=2025,
            period_month=1,
            pdf_path="/path/to/file.pdf",
        )
        result = repr(pay_slip)
        assert str(emp_id) in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestPaySlipConstraints:
    """DB-level constraint enforcement."""

    def test_fk_tenant_nonexistent(self, db_session, payroll, employee):
        """FK to tenant must exist."""
        pay_slip = PaySlip(
            tenant_id=uuid.uuid4(),
            payroll_id=payroll.id,
            employee_id=employee.id,
            period_year=2025,
            period_month=1,
            pdf_path="/path/to/file.pdf",
        )
        db_session.add(pay_slip)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_payroll_nonexistent(self, db_session, tenant, employee):
        """FK to payroll must exist."""
        pay_slip = PaySlip(
            tenant_id=tenant.id,
            payroll_id=uuid.uuid4(),
            employee_id=employee.id,
            period_year=2025,
            period_month=1,
            pdf_path="/path/to/file.pdf",
        )
        db_session.add(pay_slip)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_nonexistent(self, db_session, tenant, payroll):
        """FK to employee must exist."""
        pay_slip = PaySlip(
            tenant_id=tenant.id,
            payroll_id=payroll.id,
            employee_id=uuid.uuid4(),
            period_year=2025,
            period_month=1,
            pdf_path="/path/to/file.pdf",
        )
        db_session.add(pay_slip)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_unique_tenant_payroll(self, db_session, tenant, payroll, employee):
        """Duplicate (tenant_id, payroll_id) must fail."""
        ps1 = _make_pay_slip(tenant, payroll, employee)
        db_session.add(ps1)
        db_session.flush()

        ps2 = _make_pay_slip(tenant, payroll, employee)
        db_session.add(ps2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_pdf_path(self, db_session, tenant, payroll, employee):
        """pdf_path cannot be NULL."""
        pay_slip = _make_pay_slip(tenant, payroll, employee, pdf_path=None)
        db_session.add(pay_slip)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_period_year(self, db_session, tenant, payroll, employee):
        """period_year cannot be NULL."""
        pay_slip = _make_pay_slip(tenant, payroll, employee, period_year=None)
        db_session.add(pay_slip)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_period_month(self, db_session, tenant, payroll, employee):
        """period_month cannot be NULL."""
        pay_slip = _make_pay_slip(tenant, payroll, employee, period_month=None)
        db_session.add(pay_slip)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    # -- FK RESTRICT delete tests (raw SQL per checklist) --

    def test_fk_tenant_restrict_delete(self, db_session, tenant, payroll, employee):
        """Deleting a tenant with pay slips must be rejected.

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        pay_slip = _make_pay_slip(tenant, payroll, employee)
        db_session.add(pay_slip)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM public.tenants WHERE id = :id"),
                {"id": str(tenant.id)},
            )
        db_session.rollback()

    def test_fk_payroll_restrict_delete(self, db_session, tenant, payroll, employee):
        """Deleting a payroll with pay slips must be rejected."""
        pay_slip = _make_pay_slip(tenant, payroll, employee)
        db_session.add(pay_slip)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM payrolls WHERE id = :id"),
                {"id": str(payroll.id)},
            )
        db_session.rollback()

    def test_fk_employee_restrict_delete(self, db_session, tenant, payroll, employee):
        """Deleting an employee with pay slips must be rejected."""
        pay_slip = _make_pay_slip(tenant, payroll, employee)
        db_session.add(pay_slip)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM employees WHERE id = :id"),
                {"id": str(employee.id)},
            )
        db_session.rollback()


# ===================================================================
# Database integration tests
# ===================================================================


class TestPaySlipDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, payroll, employee):
        """Full create with all fields — verify round-trip."""
        pay_slip = _make_pay_slip(
            tenant,
            payroll,
            employee,
            file_size_bytes=123456,
        )
        db_session.add(pay_slip)
        db_session.flush()

        assert pay_slip.id is not None
        assert pay_slip.created_at is not None
        assert pay_slip.updated_at is not None
        assert pay_slip.generated_at is not None
        assert pay_slip.tenant_id == tenant.id
        assert pay_slip.payroll_id == payroll.id
        assert pay_slip.employee_id == employee.id
        assert pay_slip.period_year == 2025
        assert pay_slip.period_month == 1
        assert pay_slip.pdf_path == ("/opt/nex-payroll-src/data/payslips/tenant_test/2025/01/EMP-PS-001.pdf")
        assert pay_slip.file_size_bytes == 123456

    def test_create_minimal_defaults(self, db_session, tenant, payroll, employee):
        """Create with only required fields — verify server_defaults and nullable."""
        pay_slip = _make_pay_slip(tenant, payroll, employee)
        db_session.add(pay_slip)
        db_session.flush()

        # server_defaults
        assert pay_slip.generated_at is not None
        assert pay_slip.created_at is not None
        assert pay_slip.updated_at is not None
        # nullable fields
        assert pay_slip.file_size_bytes is None
        assert pay_slip.downloaded_at is None

    def test_file_size_bytes_nullable(self, db_session, tenant, payroll, employee):
        """file_size_bytes can be NULL."""
        pay_slip = _make_pay_slip(tenant, payroll, employee, file_size_bytes=None)
        db_session.add(pay_slip)
        db_session.flush()
        assert pay_slip.file_size_bytes is None

    def test_file_size_bytes_with_value(self, db_session, tenant, payroll, employee):
        """file_size_bytes can store a value."""
        pay_slip = _make_pay_slip(tenant, payroll, employee, file_size_bytes=987654)
        db_session.add(pay_slip)
        db_session.flush()
        assert pay_slip.file_size_bytes == 987654

    def test_downloaded_at_nullable(self, db_session, tenant, payroll, employee):
        """downloaded_at can be NULL (not yet downloaded)."""
        pay_slip = _make_pay_slip(tenant, payroll, employee, downloaded_at=None)
        db_session.add(pay_slip)
        db_session.flush()
        assert pay_slip.downloaded_at is None

    def test_different_payrolls_same_tenant(self, db_session, tenant, employee, contract):
        """Same tenant can have pay slips for different payrolls."""
        p1 = _make_payroll(tenant, employee, contract, period_year=2025, period_month=1)
        p2 = _make_payroll(tenant, employee, contract, period_year=2025, period_month=2)
        db_session.add_all([p1, p2])
        db_session.flush()

        ps1 = _make_pay_slip(
            tenant,
            p1,
            employee,
            period_year=2025,
            period_month=1,
            pdf_path="/path/2025/01/EMP-PS-001.pdf",
        )
        ps2 = _make_pay_slip(
            tenant,
            p2,
            employee,
            period_year=2025,
            period_month=2,
            pdf_path="/path/2025/02/EMP-PS-001.pdf",
        )
        db_session.add_all([ps1, ps2])
        db_session.flush()
        assert ps1.id != ps2.id

    def test_pdf_path_long_value(self, db_session, tenant, payroll, employee):
        """pdf_path supports up to 500 characters."""
        long_path = "/opt/nex-payroll-src/data/payslips/" + "a" * 450 + ".pdf"
        pay_slip = _make_pay_slip(tenant, payroll, employee, pdf_path=long_path)
        db_session.add(pay_slip)
        db_session.flush()
        assert pay_slip.pdf_path == long_path
