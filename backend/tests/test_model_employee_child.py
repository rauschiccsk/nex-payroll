"""Tests for EmployeeChild model (app.models.employee_child)."""

import uuid
from datetime import date

import pytest
from sqlalchemy import Boolean, Date, String, Text, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.employee import Employee
from app.models.employee_child import EmployeeChild
from app.models.health_insurer import HealthInsurer
from app.models.tenant import Tenant

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent."""
    t = Tenant(
        name="EmployeeChild Test Firma s.r.o.",
        ico="99000001",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000099",
        schema_name="tenant_test_emp_child",
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
    """Create an Employee required as FK parent for EmployeeChild."""
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


def _make_child(tenant, employee, **overrides):
    """Return an EmployeeChild instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "employee_id": employee.id,
        "first_name": "Marek",
        "last_name": "Novák",
        "birth_date": date(2020, 3, 10),
    }
    defaults.update(overrides)
    return EmployeeChild(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestEmployeeChildSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert EmployeeChild.__tablename__ == "employee_children"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(EmployeeChild, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(EmployeeChild, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(EmployeeChild, TimestampMixin)


class TestEmployeeChildColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(EmployeeChild)

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

    def test_first_name_column(self):
        col = self.mapper.columns["first_name"]
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert col.nullable is False

    def test_last_name_column(self):
        col = self.mapper.columns["last_name"]
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert col.nullable is False

    def test_birth_date_column(self):
        col = self.mapper.columns["birth_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is False

    def test_birth_number_column(self):
        col = self.mapper.columns["birth_number"]
        # EncryptedString wraps Text
        assert isinstance(col.type.impl, Text) or isinstance(col.type, Text)
        assert col.nullable is True

    def test_is_tax_bonus_eligible_column(self):
        col = self.mapper.columns["is_tax_bonus_eligible"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_custody_from_column(self):
        col = self.mapper.columns["custody_from"]
        assert isinstance(col.type, Date)
        assert col.nullable is True

    def test_custody_to_column(self):
        col = self.mapper.columns["custody_to"]
        assert isinstance(col.type, Date)
        assert col.nullable is True

    def test_index_tenant_employee(self):
        indexes = EmployeeChild.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_employee_children_tenant_employee" in ix_names


# ===================================================================
# Repr
# ===================================================================


class TestEmployeeChildRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        child = EmployeeChild(
            first_name="Marek",
            last_name="Novák",
            birth_date=date(2020, 3, 10),
            is_tax_bonus_eligible=True,
        )
        result = repr(child)
        assert "Marek" in result
        assert "EmployeeChild" in result
        assert "birth_date=" in result
        assert "eligible=True" in result

    def test_repr_eligible_false(self):
        child = EmployeeChild(
            first_name="Jana",
            last_name="Nováková",
            birth_date=date(2002, 1, 1),
            is_tax_bonus_eligible=False,
        )
        result = repr(child)
        assert "False" in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestEmployeeChildConstraints:
    """DB-level constraint enforcement."""

    def test_fk_tenant_nonexistent(self, db_session, employee):
        """FK to tenant must exist."""
        child = EmployeeChild(
            tenant_id=uuid.uuid4(),
            employee_id=employee.id,
            first_name="Marek",
            last_name="Novák",
            birth_date=date(2020, 3, 10),
        )
        db_session.add(child)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_nonexistent(self, db_session, tenant):
        """FK to employee must exist."""
        child = EmployeeChild(
            tenant_id=tenant.id,
            employee_id=uuid.uuid4(),
            first_name="Marek",
            last_name="Novák",
            birth_date=date(2020, 3, 10),
        )
        db_session.add(child)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_restrict_delete(self, db_session, tenant, employee):
        """Deleting an employee with children must be rejected (RESTRICT).

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        child = _make_child(tenant, employee)
        db_session.add(child)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM employees WHERE id = :id"),
                {"id": str(employee.id)},
            )
        db_session.rollback()

    def test_fk_tenant_restrict_delete(self, db_session, tenant, employee):
        """Deleting a tenant with employee children must be rejected (RESTRICT).

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        child = _make_child(tenant, employee)
        db_session.add(child)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM tenants WHERE id = :id"),
                {"id": str(tenant.id)},
            )
        db_session.rollback()

    def test_not_null_first_name(self, db_session, tenant, employee):
        """first_name cannot be NULL."""
        child = _make_child(tenant, employee, first_name=None)
        db_session.add(child)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_last_name(self, db_session, tenant, employee):
        """last_name cannot be NULL."""
        child = _make_child(tenant, employee, last_name=None)
        db_session.add(child)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_birth_date(self, db_session, tenant, employee):
        """birth_date cannot be NULL."""
        child = _make_child(tenant, employee, birth_date=None)
        db_session.add(child)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()


# ===================================================================
# Database integration tests
# ===================================================================


class TestEmployeeChildDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, employee):
        """Full create with all fields — verify round-trip."""
        child = _make_child(
            tenant,
            employee,
            birth_number="2003100001",
            is_tax_bonus_eligible=True,
            custody_from=date(2020, 3, 10),
            custody_to=date(2030, 12, 31),
        )
        db_session.add(child)
        db_session.flush()

        assert child.id is not None
        assert child.created_at is not None
        assert child.updated_at is not None
        assert child.tenant_id == tenant.id
        assert child.employee_id == employee.id
        assert child.first_name == "Marek"
        assert child.last_name == "Novák"
        assert child.birth_date == date(2020, 3, 10)
        assert child.birth_number == "2003100001"
        assert child.is_tax_bonus_eligible is True
        assert child.custody_from == date(2020, 3, 10)
        assert child.custody_to == date(2030, 12, 31)

    def test_create_minimal_defaults(self, db_session, tenant, employee):
        """Create with only required fields — verify all server_defaults."""
        child = _make_child(tenant, employee)
        db_session.add(child)
        db_session.flush()

        # server_defaults
        assert child.is_tax_bonus_eligible is True
        # nullable fields
        assert child.birth_number is None
        assert child.custody_from is None
        assert child.custody_to is None

    def test_encrypted_birth_number(self, db_session, tenant, employee):
        """birth_number is stored encrypted, read back as plaintext."""
        raw_value = "2003100001"
        child = _make_child(tenant, employee, birth_number=raw_value)
        db_session.add(child)
        db_session.flush()

        # Application sees plaintext
        assert child.birth_number == raw_value

        # DB stores ciphertext
        row = db_session.execute(
            text("SELECT birth_number FROM employee_children WHERE id = :id"),
            {"id": str(child.id)},
        ).fetchone()
        assert row[0] != raw_value
        assert row[0] is not None

    def test_birth_number_nullable(self, db_session, tenant, employee):
        """birth_number is NULLABLE — can be stored as NULL."""
        child = _make_child(tenant, employee, birth_number=None)
        db_session.add(child)
        db_session.flush()
        assert child.birth_number is None

    def test_multiple_children_same_employee(self, db_session, tenant, employee):
        """An employee can have multiple children."""
        c1 = _make_child(tenant, employee, first_name="Marek", last_name="Novák")
        c2 = _make_child(
            tenant,
            employee,
            first_name="Jana",
            last_name="Nováková",
            birth_date=date(2022, 7, 15),
        )
        db_session.add_all([c1, c2])
        db_session.flush()

        assert c1.id != c2.id
        assert c1.employee_id == c2.employee_id

    def test_tax_bonus_eligible_toggle(self, db_session, tenant, employee):
        """is_tax_bonus_eligible can be toggled from True to False."""
        child = _make_child(tenant, employee)
        db_session.add(child)
        db_session.flush()
        assert child.is_tax_bonus_eligible is True

        child.is_tax_bonus_eligible = False
        db_session.flush()
        assert child.is_tax_bonus_eligible is False

    def test_custody_period(self, db_session, tenant, employee):
        """custody_from and custody_to can be set and read."""
        child = _make_child(
            tenant,
            employee,
            custody_from=date(2021, 1, 1),
            custody_to=date(2025, 12, 31),
        )
        db_session.add(child)
        db_session.flush()

        assert child.custody_from == date(2021, 1, 1)
        assert child.custody_to == date(2025, 12, 31)
