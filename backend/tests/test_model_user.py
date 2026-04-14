"""Tests for User model (app.models.user)."""

import uuid
from datetime import date

import pytest
from sqlalchemy import Boolean, String, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.tenant import Tenant
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent for User."""
    t = Tenant(
        name="User Test Firma s.r.o.",
        ico="77000001",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000077",
        schema_name="tenant_test_user",
    )
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture()
def health_insurer(db_session):
    """Create a HealthInsurer required for Employee FK chain."""
    hi = HealthInsurer(
        code="29",
        name="Test ZP a.s.",
        iban="SK0000000000000000000029",
    )
    db_session.add(hi)
    db_session.flush()
    return hi


@pytest.fixture()
def employee(db_session, tenant, health_insurer):
    """Create an Employee that can be linked to a User."""
    emp = Employee(
        tenant_id=tenant.id,
        employee_number="UEMP001",
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


@pytest.fixture()
def employee2(db_session, tenant, health_insurer):
    """Create a second Employee for unique constraint tests."""
    emp = Employee(
        tenant_id=tenant.id,
        employee_number="UEMP002",
        first_name="Peter",
        last_name="Horváth",
        birth_date=date(1985, 3, 20),
        birth_number="8503200002",
        gender="M",
        address_street="Dlhá 5",
        address_city="Košice",
        address_zip="04001",
        bank_iban="SK3100000000000000000098",
        health_insurer_id=health_insurer.id,
        tax_declaration_type="standard",
        hire_date=date(2024, 6, 1),
    )
    db_session.add(emp)
    db_session.flush()
    return emp


def _make_user(tenant, **overrides):
    """Return a User instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "username": "testuser",
        "email": "testuser@example.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fakehashfortest",
        "role": "accountant",
    }
    defaults.update(overrides)
    return User(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestUserSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert User.__tablename__ == "users"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(User, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(User, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(User, TimestampMixin)


class TestUserColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(User)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_tenant_id_column(self):
        col = self.mapper.columns["tenant_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is True

    def test_employee_id_column(self):
        col = self.mapper.columns["employee_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is True

    def test_username_column(self):
        col = self.mapper.columns["username"]
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert col.nullable is False

    def test_email_column(self):
        col = self.mapper.columns["email"]
        assert isinstance(col.type, String)
        assert col.type.length == 255
        assert col.nullable is False

    def test_password_hash_column(self):
        col = self.mapper.columns["password_hash"]
        assert isinstance(col.type, String)
        assert col.type.length == 255
        assert col.nullable is False

    def test_role_column(self):
        col = self.mapper.columns["role"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False

    def test_is_active_column(self):
        col = self.mapper.columns["is_active"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_last_login_at_column(self):
        col = self.mapper.columns["last_login_at"]
        assert col.nullable is True

    def test_password_changed_at_column(self):
        col = self.mapper.columns["password_changed_at"]
        assert col.nullable is True

    def test_unique_constraint_tenant_username(self):
        constraints = User.__table__.constraints
        uq_names = [
            c.name
            for c in constraints
            if hasattr(c, "columns") and "tenant_id" in c.columns and "username" in c.columns
        ]
        assert "uq_users_tenant_username" in uq_names

    def test_unique_constraint_tenant_email(self):
        constraints = User.__table__.constraints
        uq_names = [
            c.name for c in constraints if hasattr(c, "columns") and "tenant_id" in c.columns and "email" in c.columns
        ]
        assert "uq_users_tenant_email" in uq_names

    def test_partial_unique_index_employee_id(self):
        """employee_id has partial unique index WHERE employee_id IS NOT NULL."""
        indexes = User.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "uq_users_employee_id" in ix_names
        # Verify it's marked unique
        idx = next(ix for ix in indexes if ix.name == "uq_users_employee_id")
        assert idx.unique is True

    def test_check_constraint_role(self):
        constraints = User.__table__.constraints
        ck_names = [c.name for c in constraints if c.name and c.name.startswith("ck_")]
        assert "ck_users_role" in ck_names

    def test_index_tenant_role(self):
        indexes = User.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_users_tenant_role" in ix_names


# ===================================================================
# Repr
# ===================================================================


class TestUserRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        u = User(
            username="admin",
            role="director",
            is_active=True,
        )
        result = repr(u)
        assert "admin" in result
        assert "director" in result
        assert "True" in result

    def test_repr_inactive(self):
        u = User(
            username="deactivated",
            role="employee",
            is_active=False,
        )
        result = repr(u)
        assert "deactivated" in result
        assert "employee" in result
        assert "False" in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestUserConstraints:
    """DB-level constraint enforcement."""

    def test_unique_tenant_username(self, db_session, tenant):
        """Duplicate (tenant_id, username) must be rejected."""
        u1 = _make_user(tenant, username="dupuser", email="dup1@example.com")
        db_session.add(u1)
        db_session.flush()

        u2 = _make_user(tenant, username="dupuser", email="dup2@example.com")
        db_session.add(u2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_unique_tenant_email(self, db_session, tenant):
        """Duplicate (tenant_id, email) must be rejected."""
        u1 = _make_user(tenant, username="user1", email="same@example.com")
        db_session.add(u1)
        db_session.flush()

        u2 = _make_user(tenant, username="user2", email="same@example.com")
        db_session.add(u2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_unique_employee_id_partial(self, db_session, tenant, employee):
        """Two users pointing to the same employee_id must be rejected."""
        u1 = _make_user(
            tenant,
            username="emp_user1",
            email="emp1@example.com",
            role="employee",
            employee_id=employee.id,
        )
        db_session.add(u1)
        db_session.flush()

        u2 = _make_user(
            tenant,
            username="emp_user2",
            email="emp2@example.com",
            role="employee",
            employee_id=employee.id,
        )
        db_session.add(u2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_null_employee_id_allows_multiple(self, db_session, tenant):
        """Multiple users with NULL employee_id must be allowed (partial unique)."""
        u1 = _make_user(
            tenant,
            username="acc1",
            email="acc1@example.com",
            role="accountant",
            employee_id=None,
        )
        u2 = _make_user(
            tenant,
            username="acc2",
            email="acc2@example.com",
            role="director",
            employee_id=None,
        )
        db_session.add_all([u1, u2])
        db_session.flush()
        assert u1.id != u2.id
        assert u1.employee_id is None
        assert u2.employee_id is None

    def test_check_role_invalid(self, db_session, tenant):
        """Invalid role must be rejected."""
        u = _make_user(tenant, role="admin")
        db_session.add(u)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_role_director(self, db_session, tenant):
        u = _make_user(
            tenant,
            role="director",
            username="dir1",
            email="dir1@example.com",
        )
        db_session.add(u)
        db_session.flush()
        assert u.role == "director"

    def test_check_role_accountant(self, db_session, tenant):
        u = _make_user(
            tenant,
            role="accountant",
            username="acc1",
            email="acc1@example.com",
        )
        db_session.add(u)
        db_session.flush()
        assert u.role == "accountant"

    def test_check_role_employee(self, db_session, tenant, employee):
        u = _make_user(
            tenant,
            role="employee",
            username="emp1",
            email="emp1@example.com",
            employee_id=employee.id,
        )
        db_session.add(u)
        db_session.flush()
        assert u.role == "employee"

    def test_fk_tenant_nonexistent(self, db_session):
        """FK to tenant must exist."""
        u = User(
            tenant_id=uuid.uuid4(),
            username="orphan",
            email="orphan@example.com",
            password_hash="$argon2id$fakehash",
            role="accountant",
        )
        db_session.add(u)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_nonexistent(self, db_session, tenant):
        """FK to employee must exist."""
        u = _make_user(
            tenant,
            username="badref",
            email="badref@example.com",
            employee_id=uuid.uuid4(),
        )
        db_session.add(u)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_tenant_restrict_delete(self, db_session, tenant):
        """Deleting a tenant with users must be rejected (RESTRICT).

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        u = _make_user(tenant, username="restrict_test", email="restrict@example.com")
        db_session.add(u)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM tenants WHERE id = :id"),
                {"id": str(tenant.id)},
            )
        db_session.rollback()

    def test_fk_employee_restrict_delete(self, db_session, tenant, employee):
        """Deleting an employee linked to a user must be rejected (RESTRICT).

        Uses raw SQL per FK RESTRICT Test Pattern.
        """
        u = _make_user(
            tenant,
            username="emp_restrict",
            email="emp_restrict@example.com",
            role="employee",
            employee_id=employee.id,
        )
        db_session.add(u)
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


class TestUserDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, employee):
        """Full create with all fields — verify round-trip."""
        u = _make_user(
            tenant,
            username="fulluser",
            email="fulluser@example.com",
            role="employee",
            employee_id=employee.id,
        )
        db_session.add(u)
        db_session.flush()

        assert u.id is not None
        assert u.created_at is not None
        assert u.updated_at is not None
        assert u.tenant_id == tenant.id
        assert u.employee_id == employee.id
        assert u.username == "fulluser"
        assert u.email == "fulluser@example.com"
        assert u.role == "employee"
        assert u.is_active is True
        assert u.last_login_at is None
        assert u.password_changed_at is None

    def test_create_minimal_defaults(self, db_session, tenant):
        """Create with only required fields — verify all server_defaults."""
        u = _make_user(tenant)
        db_session.add(u)
        db_session.flush()

        # server_defaults
        assert u.is_active is True
        # nullable fields
        assert u.employee_id is None
        assert u.last_login_at is None
        assert u.password_changed_at is None

    def test_soft_delete(self, db_session, tenant):
        """Soft-delete via is_active flag."""
        u = _make_user(tenant, username="softdel", email="softdel@example.com")
        db_session.add(u)
        db_session.flush()
        assert u.is_active is True

        u.is_active = False
        db_session.flush()
        assert u.is_active is False

    def test_two_users_different_usernames(self, db_session, tenant):
        """Two users with different usernames in same tenant — must succeed."""
        u1 = _make_user(tenant, username="user_a", email="a@example.com")
        u2 = _make_user(tenant, username="user_b", email="b@example.com")
        db_session.add_all([u1, u2])
        db_session.flush()
        assert u1.id != u2.id

    def test_director_without_employee_id(self, db_session, tenant):
        """Director MAY have no employee_id."""
        u = _make_user(
            tenant,
            role="director",
            username="director1",
            email="director1@example.com",
            employee_id=None,
        )
        db_session.add(u)
        db_session.flush()
        assert u.role == "director"
        assert u.employee_id is None

    def test_employee_with_employee_id(self, db_session, tenant, employee):
        """Employee role with linked employee record."""
        u = _make_user(
            tenant,
            role="employee",
            username="worker1",
            email="worker1@example.com",
            employee_id=employee.id,
        )
        db_session.add(u)
        db_session.flush()
        assert u.role == "employee"
        assert u.employee_id == employee.id

    def test_two_different_employees_linked(self, db_session, tenant, employee, employee2):
        """Two users linked to different employees — must succeed."""
        u1 = _make_user(
            tenant,
            role="employee",
            username="worker_a",
            email="worker_a@example.com",
            employee_id=employee.id,
        )
        u2 = _make_user(
            tenant,
            role="employee",
            username="worker_b",
            email="worker_b@example.com",
            employee_id=employee2.id,
        )
        db_session.add_all([u1, u2])
        db_session.flush()
        assert u1.employee_id != u2.employee_id
