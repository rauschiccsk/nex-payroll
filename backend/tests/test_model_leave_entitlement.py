"""Tests for LeaveEntitlement model (app.models.leave_entitlement)."""

import uuid
from datetime import date

import pytest
from sqlalchemy import Integer, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.leave_entitlement import LeaveEntitlement
from app.models.tenant import Tenant

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent."""
    t = Tenant(
        name="LeaveEntitlement Test Firma s.r.o.",
        ico="99000010",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000010",
        schema_name="tenant_test_leave_ent",
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
    """Create an Employee required as FK parent for LeaveEntitlement."""
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


def _make_entitlement(tenant, employee, **overrides):
    """Return a LeaveEntitlement instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "employee_id": employee.id,
        "year": 2025,
        "total_days": 20,
        "remaining_days": 20,
    }
    defaults.update(overrides)
    return LeaveEntitlement(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestLeaveEntitlementSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert LeaveEntitlement.__tablename__ == "leave_entitlements"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(LeaveEntitlement, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(LeaveEntitlement, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(LeaveEntitlement, TimestampMixin)


class TestLeaveEntitlementColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(LeaveEntitlement)

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

    def test_year_column(self):
        col = self.mapper.columns["year"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_total_days_column(self):
        col = self.mapper.columns["total_days"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_used_days_column(self):
        col = self.mapper.columns["used_days"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False
        assert col.server_default is not None

    def test_remaining_days_column(self):
        col = self.mapper.columns["remaining_days"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_carryover_days_column(self):
        col = self.mapper.columns["carryover_days"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False
        assert col.server_default is not None

    def test_unique_constraint_tenant_employee_year(self):
        """UniqueConstraint with explicit name must exist."""
        table = LeaveEntitlement.__table__
        uq_names = [c.name for c in table.constraints if hasattr(c, "columns") and len(c.columns) > 1]
        assert "uq_leave_entitlements_tenant_employee_year" in uq_names


# ===================================================================
# Repr
# ===================================================================


class TestLeaveEntitlementRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        ent = LeaveEntitlement(
            employee_id=uuid.uuid4(),
            year=2025,
            remaining_days=15,
        )
        result = repr(ent)
        assert "LeaveEntitlement" in result
        assert "2025" in result
        assert "15" in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestLeaveEntitlementConstraints:
    """DB-level constraint enforcement."""

    def test_fk_tenant_nonexistent(self, db_session, employee):
        """FK to tenant must exist."""
        ent = LeaveEntitlement(
            tenant_id=uuid.uuid4(),
            employee_id=employee.id,
            year=2025,
            total_days=20,
            remaining_days=20,
        )
        db_session.add(ent)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_nonexistent(self, db_session, tenant):
        """FK to employee must exist."""
        ent = LeaveEntitlement(
            tenant_id=tenant.id,
            employee_id=uuid.uuid4(),
            year=2025,
            total_days=20,
            remaining_days=20,
        )
        db_session.add(ent)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_restrict_delete(self, db_session, tenant, employee):
        """Deleting an employee with entitlements must be rejected (RESTRICT).

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        ent = _make_entitlement(tenant, employee)
        db_session.add(ent)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM employees WHERE id = :id"),
                {"id": str(employee.id)},
            )
        db_session.rollback()

    def test_unique_tenant_employee_year(self, db_session, tenant, employee):
        """Duplicate (tenant_id, employee_id, year) must be rejected."""
        ent1 = _make_entitlement(tenant, employee, year=2025)
        db_session.add(ent1)
        db_session.flush()

        ent2 = _make_entitlement(tenant, employee, year=2025)
        db_session.add(ent2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_unique_different_year_allowed(self, db_session, tenant, employee):
        """Same (tenant_id, employee_id) with different year is allowed."""
        ent1 = _make_entitlement(tenant, employee, year=2025)
        ent2 = _make_entitlement(tenant, employee, year=2026)
        db_session.add_all([ent1, ent2])
        db_session.flush()
        assert ent1.id != ent2.id

    def test_not_null_year(self, db_session, tenant, employee):
        """year cannot be NULL."""
        ent = _make_entitlement(tenant, employee, year=None)
        db_session.add(ent)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_total_days(self, db_session, tenant, employee):
        """total_days cannot be NULL."""
        ent = _make_entitlement(tenant, employee, total_days=None)
        db_session.add(ent)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_remaining_days(self, db_session, tenant, employee):
        """remaining_days cannot be NULL."""
        ent = _make_entitlement(tenant, employee, remaining_days=None)
        db_session.add(ent)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()


# ===================================================================
# Database integration tests
# ===================================================================


class TestLeaveEntitlementDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, employee):
        """Full create with all fields — verify round-trip."""
        ent = _make_entitlement(
            tenant,
            employee,
            year=2025,
            total_days=25,
            used_days=5,
            remaining_days=20,
            carryover_days=3,
        )
        db_session.add(ent)
        db_session.flush()

        assert ent.id is not None
        assert ent.created_at is not None
        assert ent.updated_at is not None
        assert ent.tenant_id == tenant.id
        assert ent.employee_id == employee.id
        assert ent.year == 2025
        assert ent.total_days == 25
        assert ent.used_days == 5
        assert ent.remaining_days == 20
        assert ent.carryover_days == 3

    def test_create_minimal_defaults(self, db_session, tenant, employee):
        """Create with only required fields — verify all server_defaults."""
        ent = _make_entitlement(tenant, employee)
        db_session.add(ent)
        db_session.flush()

        # server_defaults for Integer columns
        assert ent.used_days == 0
        assert ent.carryover_days == 0

    def test_update_used_days(self, db_session, tenant, employee):
        """used_days can be incremented."""
        ent = _make_entitlement(
            tenant,
            employee,
            total_days=20,
            used_days=0,
            remaining_days=20,
        )
        db_session.add(ent)
        db_session.flush()

        ent.used_days = 5
        ent.remaining_days = 15
        db_session.flush()

        assert ent.used_days == 5
        assert ent.remaining_days == 15

    def test_carryover_days(self, db_session, tenant, employee):
        """carryover_days can be set and read."""
        ent = _make_entitlement(
            tenant,
            employee,
            carryover_days=5,
            total_days=25,
            remaining_days=25,
        )
        db_session.add(ent)
        db_session.flush()

        assert ent.carryover_days == 5
