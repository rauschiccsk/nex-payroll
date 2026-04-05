"""Tests for Leave model (app.models.leave)."""

import uuid
from datetime import date

import pytest
from sqlalchemy import Date, Integer, String, Text, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.sql.sqltypes import TIMESTAMP

from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.leave import Leave
from app.models.tenant import Tenant
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent."""
    t = Tenant(
        name="Leave Test Firma s.r.o.",
        ico="66000013",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000066",
        schema_name="tenant_test_leave",
    )
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture()
def health_insurer(db_session):
    """Create a HealthInsurer required as FK parent for Employee."""
    hi = HealthInsurer(
        code="26",
        name="Test ZP Leave a.s.",
        iban="SK0000000000000000000026",
    )
    db_session.add(hi)
    db_session.flush()
    return hi


@pytest.fixture()
def employee(db_session, tenant, health_insurer):
    """Create an Employee required as FK parent for Leave."""
    emp = Employee(
        tenant_id=tenant.id,
        employee_number="LEMP001",
        first_name="Jana",
        last_name="Nováková",
        birth_date=date(1992, 3, 10),
        birth_number="9203100001",
        gender="F",
        address_street="Hlavná 2",
        address_city="Košice",
        address_zip="04001",
        bank_iban="SK3100000000000000000066",
        health_insurer_id=health_insurer.id,
        tax_declaration_type="standard",
        hire_date=date(2023, 6, 1),
    )
    db_session.add(emp)
    db_session.flush()
    return emp


@pytest.fixture()
def user(db_session, tenant):
    """Create a User required as FK parent for approved_by."""
    u = User(
        tenant_id=tenant.id,
        username="leave_approver",
        email="approver@test.sk",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role="accountant",
    )
    db_session.add(u)
    db_session.flush()
    return u


def _make_leave(tenant, employee, **overrides):
    """Return a Leave instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "employee_id": employee.id,
        "leave_type": "annual",
        "start_date": date(2025, 7, 1),
        "end_date": date(2025, 7, 10),
        "business_days": 8,
    }
    defaults.update(overrides)
    return Leave(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestLeaveSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert Leave.__tablename__ == "leaves"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(Leave, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(Leave, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(Leave, TimestampMixin)


class TestLeaveColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(Leave)

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

    def test_approved_by_column(self):
        col = self.mapper.columns["approved_by"]
        assert isinstance(col.type, UUID)
        assert col.nullable is True

    def test_leave_type_column(self):
        col = self.mapper.columns["leave_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 30
        assert col.nullable is False

    def test_start_date_column(self):
        col = self.mapper.columns["start_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is False

    def test_end_date_column(self):
        col = self.mapper.columns["end_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is False

    def test_business_days_column(self):
        col = self.mapper.columns["business_days"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_status_column(self):
        col = self.mapper.columns["status"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False
        assert col.server_default is not None

    def test_status_server_default_pending(self):
        col = self.mapper.columns["status"]
        assert "pending" in str(col.server_default.arg)

    def test_note_column(self):
        col = self.mapper.columns["note"]
        assert isinstance(col.type, Text)
        assert col.nullable is True

    def test_approved_at_column(self):
        col = self.mapper.columns["approved_at"]
        assert isinstance(col.type, TIMESTAMP)
        assert col.type.timezone is True
        assert col.nullable is True

    def test_check_constraint_leave_type(self):
        constraints = Leave.__table__.constraints
        ck_names = [c.name for c in constraints if c.name and c.name.startswith("ck_")]
        assert "ck_leaves_leave_type" in ck_names

    def test_check_constraint_status(self):
        constraints = Leave.__table__.constraints
        ck_names = [c.name for c in constraints if c.name and c.name.startswith("ck_")]
        assert "ck_leaves_status" in ck_names

    def test_index_tenant_employee_start(self):
        indexes = Leave.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_leaves_tenant_employee_start" in ix_names

    def test_index_tenant_status(self):
        indexes = Leave.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_leaves_tenant_status" in ix_names


# ===================================================================
# Repr
# ===================================================================


class TestLeaveRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        emp_id = uuid.uuid4()
        leave = Leave(
            employee_id=emp_id,
            leave_type="annual",
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 10),
            status="pending",
        )
        result = repr(leave)
        assert "Leave" in result
        assert "annual" in result
        assert "pending" in result

    def test_repr_contains_dates(self):
        leave = Leave(
            employee_id=uuid.uuid4(),
            leave_type="sick_employer",
            start_date=date(2025, 3, 1),
            end_date=date(2025, 3, 5),
            status="approved",
        )
        result = repr(leave)
        assert "2025-03-01" in result or "2025, 3, 1" in result
        assert "2025-03-05" in result or "2025, 3, 5" in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestLeaveConstraints:
    """DB-level constraint enforcement."""

    def test_fk_tenant_nonexistent(self, db_session, employee):
        """FK to tenant must exist."""
        leave = Leave(
            tenant_id=uuid.uuid4(),
            employee_id=employee.id,
            leave_type="annual",
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 5),
            business_days=5,
        )
        db_session.add(leave)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_nonexistent(self, db_session, tenant):
        """FK to employee must exist."""
        leave = Leave(
            tenant_id=tenant.id,
            employee_id=uuid.uuid4(),
            leave_type="annual",
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 5),
            business_days=5,
        )
        db_session.add(leave)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_approved_by_nonexistent(self, db_session, tenant, employee):
        """FK to users (approved_by) must exist if set."""
        leave = _make_leave(tenant, employee, approved_by=uuid.uuid4())
        db_session.add(leave)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_approved_by_valid(self, db_session, tenant, employee, user):
        """approved_by with valid user FK succeeds."""
        leave = _make_leave(tenant, employee, approved_by=user.id)
        db_session.add(leave)
        db_session.flush()
        assert leave.approved_by == user.id

    def test_check_leave_type_invalid(self, db_session, tenant, employee):
        """Invalid leave_type must be rejected."""
        leave = _make_leave(tenant, employee, leave_type="vacation")
        db_session.add(leave)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_leave_type_annual(self, db_session, tenant, employee):
        leave = _make_leave(tenant, employee, leave_type="annual")
        db_session.add(leave)
        db_session.flush()
        assert leave.leave_type == "annual"

    def test_check_leave_type_sick_employer(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            leave_type="sick_employer",
            start_date=date(2025, 8, 1),
            end_date=date(2025, 8, 5),
            business_days=5,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.leave_type == "sick_employer"

    def test_check_leave_type_sick_sp(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            leave_type="sick_sp",
            start_date=date(2025, 8, 6),
            end_date=date(2025, 8, 20),
            business_days=11,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.leave_type == "sick_sp"

    def test_check_leave_type_ocr(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            leave_type="ocr",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 9, 10),
            business_days=8,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.leave_type == "ocr"

    def test_check_leave_type_maternity(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            leave_type="maternity",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 7, 31),
            business_days=150,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.leave_type == "maternity"

    def test_check_leave_type_parental(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            leave_type="parental",
            start_date=date(2025, 10, 1),
            end_date=date(2025, 10, 31),
            business_days=23,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.leave_type == "parental"

    def test_check_leave_type_unpaid(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            leave_type="unpaid",
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 3),
            business_days=3,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.leave_type == "unpaid"

    def test_check_leave_type_obstacle(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            leave_type="obstacle",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 1),
            business_days=1,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.leave_type == "obstacle"

    def test_check_status_invalid(self, db_session, tenant, employee):
        """Invalid status must be rejected."""
        leave = _make_leave(tenant, employee, status="completed")
        db_session.add(leave)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_status_approved(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            status="approved",
            start_date=date(2025, 5, 1),
            end_date=date(2025, 5, 5),
            business_days=5,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.status == "approved"

    def test_check_status_rejected(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            status="rejected",
            start_date=date(2025, 5, 6),
            end_date=date(2025, 5, 7),
            business_days=2,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.status == "rejected"

    def test_check_status_cancelled(self, db_session, tenant, employee):
        leave = _make_leave(
            tenant,
            employee,
            status="cancelled",
            start_date=date(2025, 5, 8),
            end_date=date(2025, 5, 9),
            business_days=2,
        )
        db_session.add(leave)
        db_session.flush()
        assert leave.status == "cancelled"

    def test_not_null_leave_type(self, db_session, tenant, employee):
        """leave_type cannot be NULL."""
        leave = _make_leave(tenant, employee, leave_type=None)
        db_session.add(leave)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_start_date(self, db_session, tenant, employee):
        """start_date cannot be NULL."""
        leave = _make_leave(tenant, employee, start_date=None)
        db_session.add(leave)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_end_date(self, db_session, tenant, employee):
        """end_date cannot be NULL."""
        leave = _make_leave(tenant, employee, end_date=None)
        db_session.add(leave)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_business_days(self, db_session, tenant, employee):
        """business_days cannot be NULL."""
        leave = _make_leave(tenant, employee, business_days=None)
        db_session.add(leave)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_restrict_delete(self, db_session, tenant, employee):
        """Deleting an employee with leaves must be rejected (RESTRICT).

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        leave = _make_leave(tenant, employee)
        db_session.add(leave)
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


class TestLeaveDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, employee, user):
        """Full create with all fields — verify round-trip."""
        leave = _make_leave(
            tenant,
            employee,
            leave_type="annual",
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 10),
            business_days=8,
            status="approved",
            note="Summer vacation",
            approved_by=user.id,
        )
        db_session.add(leave)
        db_session.flush()

        assert leave.id is not None
        assert leave.created_at is not None
        assert leave.updated_at is not None
        assert leave.tenant_id == tenant.id
        assert leave.employee_id == employee.id
        assert leave.leave_type == "annual"
        assert leave.start_date == date(2025, 7, 1)
        assert leave.end_date == date(2025, 7, 10)
        assert leave.business_days == 8
        assert leave.status == "approved"
        assert leave.note == "Summer vacation"
        assert leave.approved_by == user.id

    def test_create_minimal_defaults(self, db_session, tenant, employee):
        """Create with only required fields — verify all server_defaults."""
        leave = _make_leave(tenant, employee)
        db_session.add(leave)
        db_session.flush()

        # server_default
        assert leave.status == "pending"
        # nullable fields
        assert leave.note is None
        assert leave.approved_by is None
        assert leave.approved_at is None

    def test_status_transition(self, db_session, tenant, employee, user):
        """Status can be updated from pending to approved."""
        leave = _make_leave(tenant, employee)
        db_session.add(leave)
        db_session.flush()
        assert leave.status == "pending"

        leave.status = "approved"
        leave.approved_by = user.id
        db_session.flush()
        assert leave.status == "approved"
        assert leave.approved_by == user.id

    def test_multiple_leaves_same_employee(self, db_session, tenant, employee):
        """Multiple leave records for the same employee are allowed."""
        leave1 = _make_leave(
            tenant,
            employee,
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 5),
            business_days=5,
        )
        leave2 = _make_leave(
            tenant,
            employee,
            start_date=date(2025, 8, 1),
            end_date=date(2025, 8, 10),
            business_days=8,
        )
        db_session.add_all([leave1, leave2])
        db_session.flush()
        assert leave1.id != leave2.id

    def test_note_text_field(self, db_session, tenant, employee):
        """note field accepts long text."""
        long_note = "A" * 500
        leave = _make_leave(tenant, employee, note=long_note)
        db_session.add(leave)
        db_session.flush()
        assert leave.note == long_note
