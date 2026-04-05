"""Tests for Contract model (app.models.contract)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Boolean, Date, Numeric, String, inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.tenant import Tenant

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent."""
    t = Tenant(
        name="Contract Test Firma s.r.o.",
        ico="88000001",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000001",
        schema_name="tenant_test_contract",
    )
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture()
def health_insurer(db_session):
    """Create a HealthInsurer required as FK parent for Employee."""
    hi = HealthInsurer(
        code="27",
        name="Union zdravotná poisťovňa, a.s.",
        iban="SK0000000000000000000027",
    )
    db_session.add(hi)
    db_session.flush()
    return hi


@pytest.fixture()
def employee(db_session, tenant, health_insurer):
    """Create an Employee required as FK parent for Contract."""
    emp = Employee(
        tenant_id=tenant.id,
        employee_number="EMP001",
        first_name="Ján",
        last_name="Novák",
        birth_date=date(1990, 5, 15),
        birth_number="9005150001",
        gender="M",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK3100000000000000000099",
        health_insurer_id=health_insurer.id,
        tax_declaration_type="standard",
        hire_date=date(2024, 1, 1),
    )
    db_session.add(emp)
    db_session.flush()
    return emp


def _make_contract(tenant, employee, **overrides):
    """Return a Contract instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "employee_id": employee.id,
        "contract_number": "ZML-2024-001",
        "contract_type": "permanent",
        "job_title": "Software Developer",
        "wage_type": "monthly",
        "base_wage": Decimal("2500.00"),
        "start_date": date(2024, 1, 1),
    }
    defaults.update(overrides)
    return Contract(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestContractSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert Contract.__tablename__ == "contracts"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(Contract, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(Contract, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(Contract, TimestampMixin)


class TestContractColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(Contract)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_tenant_id_column(self):
        col = self.mapper.columns["tenant_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_employee_id_column(self):
        col = self.mapper.columns["employee_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_contract_number_column(self):
        col = self.mapper.columns["contract_number"]
        assert isinstance(col.type, String)
        assert col.type.length == 50
        assert col.nullable is False

    def test_contract_type_column(self):
        col = self.mapper.columns["contract_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 30
        assert col.nullable is False

    def test_job_title_column(self):
        col = self.mapper.columns["job_title"]
        assert isinstance(col.type, String)
        assert col.type.length == 200
        assert col.nullable is False

    def test_wage_type_column(self):
        col = self.mapper.columns["wage_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False

    def test_base_wage_column(self):
        col = self.mapper.columns["base_wage"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 10
        assert col.type.scale == 2
        assert col.nullable is False

    def test_hours_per_week_column(self):
        col = self.mapper.columns["hours_per_week"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 4
        assert col.type.scale == 1
        assert col.nullable is False
        assert col.server_default is not None

    def test_start_date_column(self):
        col = self.mapper.columns["start_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is False

    def test_end_date_column(self):
        col = self.mapper.columns["end_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is True

    def test_probation_end_date_column(self):
        col = self.mapper.columns["probation_end_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is True

    def test_termination_date_column(self):
        col = self.mapper.columns["termination_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is True

    def test_termination_reason_column(self):
        col = self.mapper.columns["termination_reason"]
        assert isinstance(col.type, String)
        assert col.type.length == 200
        assert col.nullable is True

    def test_is_current_column(self):
        col = self.mapper.columns["is_current"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_unique_constraint_tenant_contract_number(self):
        constraints = Contract.__table__.constraints
        uq_names = [
            c.name
            for c in constraints
            if hasattr(c, "columns")
            and "tenant_id" in c.columns
            and "contract_number" in c.columns
        ]
        assert "uq_contracts_tenant_contract_number" in uq_names

    def test_check_constraint_contract_type(self):
        constraints = Contract.__table__.constraints
        ck_names = [c.name for c in constraints if c.name and c.name.startswith("ck_")]
        assert "ck_contracts_contract_type" in ck_names

    def test_check_constraint_wage_type(self):
        constraints = Contract.__table__.constraints
        ck_names = [c.name for c in constraints if c.name and c.name.startswith("ck_")]
        assert "ck_contracts_wage_type" in ck_names

    def test_index_tenant_employee_current(self):
        indexes = Contract.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_contracts_tenant_employee_current" in ix_names


# ===================================================================
# Repr
# ===================================================================


class TestContractRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        c = Contract(
            contract_number="ZML-2024-001",
            contract_type="permanent",
            is_current=True,
        )
        result = repr(c)
        assert "ZML-2024-001" in result
        assert "permanent" in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestContractConstraints:
    """DB-level constraint enforcement."""

    def test_unique_tenant_contract_number(self, db_session, tenant, employee):
        """Duplicate (tenant_id, contract_number) must be rejected."""
        c1 = _make_contract(tenant, employee, contract_number="DUP-001")
        db_session.add(c1)
        db_session.flush()

        c2 = _make_contract(
            tenant,
            employee,
            contract_number="DUP-001",
            job_title="Manager",
            start_date=date(2025, 1, 1),
        )
        db_session.add(c2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_contract_type_invalid(self, db_session, tenant, employee):
        """Invalid contract_type must be rejected."""
        c = _make_contract(tenant, employee, contract_type="freelance")
        db_session.add(c)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_contract_type_permanent(self, db_session, tenant, employee):
        c = _make_contract(
            tenant, employee, contract_type="permanent", contract_number="CT-PERM"
        )
        db_session.add(c)
        db_session.flush()
        assert c.contract_type == "permanent"

    def test_check_contract_type_fixed_term(self, db_session, tenant, employee):
        c = _make_contract(
            tenant, employee, contract_type="fixed_term", contract_number="CT-FT"
        )
        db_session.add(c)
        db_session.flush()
        assert c.contract_type == "fixed_term"

    def test_check_contract_type_agreement_work(self, db_session, tenant, employee):
        c = _make_contract(
            tenant, employee, contract_type="agreement_work", contract_number="CT-AW"
        )
        db_session.add(c)
        db_session.flush()
        assert c.contract_type == "agreement_work"

    def test_check_contract_type_agreement_activity(self, db_session, tenant, employee):
        c = _make_contract(
            tenant,
            employee,
            contract_type="agreement_activity",
            contract_number="CT-AA",
        )
        db_session.add(c)
        db_session.flush()
        assert c.contract_type == "agreement_activity"

    def test_check_wage_type_invalid(self, db_session, tenant, employee):
        """Invalid wage_type must be rejected."""
        c = _make_contract(tenant, employee, wage_type="annual")
        db_session.add(c)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_wage_type_monthly(self, db_session, tenant, employee):
        c = _make_contract(
            tenant, employee, wage_type="monthly", contract_number="WT-MON"
        )
        db_session.add(c)
        db_session.flush()
        assert c.wage_type == "monthly"

    def test_check_wage_type_hourly(self, db_session, tenant, employee):
        c = _make_contract(
            tenant, employee, wage_type="hourly", contract_number="WT-HR"
        )
        db_session.add(c)
        db_session.flush()
        assert c.wage_type == "hourly"

    def test_fk_tenant_nonexistent(self, db_session, employee):
        """FK to tenant must exist."""
        c = Contract(
            tenant_id=uuid.uuid4(),
            employee_id=employee.id,
            contract_number="FK-T01",
            contract_type="permanent",
            job_title="Developer",
            wage_type="monthly",
            base_wage=Decimal("2000.00"),
            start_date=date(2024, 1, 1),
        )
        db_session.add(c)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_nonexistent(self, db_session, tenant):
        """FK to employee must exist."""
        c = Contract(
            tenant_id=tenant.id,
            employee_id=uuid.uuid4(),
            contract_number="FK-E01",
            contract_type="permanent",
            job_title="Developer",
            wage_type="monthly",
            base_wage=Decimal("2000.00"),
            start_date=date(2024, 1, 1),
        )
        db_session.add(c)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()


# ===================================================================
# Database integration tests
# ===================================================================


class TestContractDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, employee):
        """Full create with all fields — verify round-trip."""
        c = _make_contract(
            tenant,
            employee,
            end_date=date(2025, 12, 31),
            probation_end_date=date(2024, 4, 1),
            termination_date=date(2025, 6, 30),
            termination_reason="End of project",
            hours_per_week=Decimal("37.5"),
        )
        db_session.add(c)
        db_session.flush()

        assert c.id is not None
        assert c.created_at is not None
        assert c.updated_at is not None
        assert c.tenant_id == tenant.id
        assert c.employee_id == employee.id
        assert c.contract_number == "ZML-2024-001"
        assert c.contract_type == "permanent"
        assert c.job_title == "Software Developer"
        assert c.wage_type == "monthly"
        assert c.base_wage == Decimal("2500.00")
        assert c.hours_per_week == Decimal("37.5")
        assert c.start_date == date(2024, 1, 1)
        assert c.end_date == date(2025, 12, 31)
        assert c.probation_end_date == date(2024, 4, 1)
        assert c.termination_date == date(2025, 6, 30)
        assert c.termination_reason == "End of project"

    def test_create_minimal_defaults(self, db_session, tenant, employee):
        """Create with only required fields — verify all server_defaults."""
        c = _make_contract(tenant, employee)
        db_session.add(c)
        db_session.flush()

        # server_defaults
        assert c.hours_per_week == Decimal("40.0")
        assert c.is_current is True
        # nullable fields
        assert c.end_date is None
        assert c.probation_end_date is None
        assert c.termination_date is None
        assert c.termination_reason is None

    def test_is_current_toggle(self, db_session, tenant, employee):
        """is_current can be toggled from True to False."""
        c = _make_contract(tenant, employee)
        db_session.add(c)
        db_session.flush()
        assert c.is_current is True

        c.is_current = False
        db_session.flush()
        assert c.is_current is False

    def test_two_contracts_different_numbers(self, db_session, tenant, employee):
        """Two contracts with different numbers in same tenant — must succeed."""
        c1 = _make_contract(tenant, employee, contract_number="ZML-001")
        c2 = _make_contract(
            tenant,
            employee,
            contract_number="ZML-002",
            job_title="Senior Developer",
            start_date=date(2025, 1, 1),
            is_current=False,
        )
        db_session.add_all([c1, c2])
        db_session.flush()
        assert c1.id != c2.id

    def test_agreement_work_with_hourly_wage(self, db_session, tenant, employee):
        """Agreement-based contract with hourly wage — valid combination."""
        c = _make_contract(
            tenant,
            employee,
            contract_number="DOH-001",
            contract_type="agreement_work",
            wage_type="hourly",
            base_wage=Decimal("12.50"),
            hours_per_week=Decimal("10.0"),
        )
        db_session.add(c)
        db_session.flush()
        assert c.contract_type == "agreement_work"
        assert c.wage_type == "hourly"
        assert c.base_wage == Decimal("12.50")
        assert c.hours_per_week == Decimal("10.0")
