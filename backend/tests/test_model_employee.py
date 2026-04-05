"""Tests for Employee model (app.models.employee)."""

import uuid
from datetime import date

import pytest
from sqlalchemy import Boolean, Date, String, Text, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.tenant import Tenant

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent for Employee."""
    t = Tenant(
        name="Test Firma s.r.o.",
        ico="99000001",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000001",
        schema_name="tenant_test_emp",
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


def _make_employee(tenant, health_insurer, **overrides):
    """Return an Employee instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "employee_number": "EMP001",
        "first_name": "Ján",
        "last_name": "Novák",
        "birth_date": date(1990, 5, 15),
        "birth_number": "9005150001",
        "gender": "M",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "bank_iban": "SK3100000000000000000099",
        "health_insurer_id": health_insurer.id,
        "tax_declaration_type": "standard",
        "hire_date": date(2024, 1, 1),
    }
    defaults.update(overrides)
    return Employee(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================

class TestEmployeeSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert Employee.__tablename__ == "employees"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(Employee, Base)


class TestEmployeeColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(Employee)

    def test_id_column(self):
        col = self.mapper.columns["id"]
        assert col.primary_key is True
        assert isinstance(col.type, UUID)
        assert col.server_default is not None

    def test_tenant_id_column(self):
        col = self.mapper.columns["tenant_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_employee_number_column(self):
        col = self.mapper.columns["employee_number"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
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

    def test_title_before_nullable(self):
        col = self.mapper.columns["title_before"]
        assert isinstance(col.type, String)
        assert col.type.length == 50
        assert col.nullable is True

    def test_title_after_nullable(self):
        col = self.mapper.columns["title_after"]
        assert isinstance(col.type, String)
        assert col.type.length == 50
        assert col.nullable is True

    def test_birth_date_column(self):
        col = self.mapper.columns["birth_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is False

    def test_birth_number_column(self):
        col = self.mapper.columns["birth_number"]
        # EncryptedString wraps Text
        assert isinstance(col.type.impl, type(Text()))
        assert col.nullable is False

    def test_gender_column(self):
        col = self.mapper.columns["gender"]
        assert isinstance(col.type, String)
        assert col.type.length == 1
        assert col.nullable is False

    def test_nationality_column(self):
        col = self.mapper.columns["nationality"]
        assert isinstance(col.type, String)
        assert col.type.length == 2
        assert col.nullable is False
        assert col.server_default is not None

    def test_address_street_column(self):
        col = self.mapper.columns["address_street"]
        assert isinstance(col.type, String)
        assert col.type.length == 200
        assert col.nullable is False

    def test_address_city_column(self):
        col = self.mapper.columns["address_city"]
        assert isinstance(col.type, String)
        assert col.type.length == 100
        assert col.nullable is False

    def test_address_zip_column(self):
        col = self.mapper.columns["address_zip"]
        assert isinstance(col.type, String)
        assert col.type.length == 10
        assert col.nullable is False

    def test_address_country_column(self):
        col = self.mapper.columns["address_country"]
        assert isinstance(col.type, String)
        assert col.type.length == 2
        assert col.nullable is False
        assert col.server_default is not None

    def test_bank_iban_column(self):
        col = self.mapper.columns["bank_iban"]
        # EncryptedString wraps Text
        assert isinstance(col.type.impl, type(Text()))
        assert col.nullable is False

    def test_bank_bic_column(self):
        col = self.mapper.columns["bank_bic"]
        assert isinstance(col.type, String)
        assert col.type.length == 11
        assert col.nullable is True

    def test_health_insurer_id_column(self):
        col = self.mapper.columns["health_insurer_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is False

    def test_tax_declaration_type_column(self):
        col = self.mapper.columns["tax_declaration_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False

    def test_nczd_applied_column(self):
        col = self.mapper.columns["nczd_applied"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_pillar2_saver_column(self):
        col = self.mapper.columns["pillar2_saver"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_is_disabled_column(self):
        col = self.mapper.columns["is_disabled"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_status_column(self):
        col = self.mapper.columns["status"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False
        assert col.server_default is not None

    def test_hire_date_column(self):
        col = self.mapper.columns["hire_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is False

    def test_termination_date_column(self):
        col = self.mapper.columns["termination_date"]
        assert isinstance(col.type, Date)
        assert col.nullable is True

    def test_is_deleted_column(self):
        col = self.mapper.columns["is_deleted"]
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert col.server_default is not None

    def test_unique_constraint_tenant_employee_number(self):
        constraints = Employee.__table__.constraints
        uq_names = [
            c.name
            for c in constraints
            if hasattr(c, "columns")
            and "tenant_id" in c.columns
            and "employee_number" in c.columns
        ]
        assert "uq_employees_tenant_employee_number" in uq_names


# ===================================================================
# Repr
# ===================================================================

class TestEmployeeRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        emp = Employee(
            employee_number="EMP001",
            first_name="Ján",
            last_name="Novák",
            status="active",
        )
        result = repr(emp)
        assert "EMP001" in result
        assert "Ján" in result
        assert "Novák" in result
        assert "active" in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================

class TestEmployeeConstraints:
    """DB-level constraint enforcement."""

    def test_unique_tenant_employee_number(self, db_session, tenant, health_insurer):
        """Duplicate (tenant_id, employee_number) must be rejected."""
        emp1 = _make_employee(tenant, health_insurer, employee_number="DUP001")
        db_session.add(emp1)
        db_session.flush()

        emp2 = _make_employee(
            tenant,
            health_insurer,
            employee_number="DUP001",
            first_name="Peter",
            birth_number="9005150002",
            bank_iban="SK3100000000000000000098",
        )
        db_session.add(emp2)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_gender_invalid(self, db_session, tenant, health_insurer):
        """Gender must be 'M' or 'F'."""
        emp = _make_employee(tenant, health_insurer, gender="X")
        db_session.add(emp)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_gender_valid_m(self, db_session, tenant, health_insurer):
        """Gender 'M' must be accepted."""
        emp = _make_employee(tenant, health_insurer, gender="M", employee_number="GM01")
        db_session.add(emp)
        db_session.flush()
        assert emp.gender == "M"

    def test_check_gender_valid_f(self, db_session, tenant, health_insurer):
        """Gender 'F' must be accepted."""
        emp = _make_employee(tenant, health_insurer, gender="F", employee_number="GF01")
        db_session.add(emp)
        db_session.flush()
        assert emp.gender == "F"

    def test_check_tax_declaration_type_invalid(self, db_session, tenant, health_insurer):
        """Invalid tax_declaration_type must be rejected."""
        emp = _make_employee(tenant, health_insurer, tax_declaration_type="invalid")
        db_session.add(emp)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_tax_declaration_type_standard(self, db_session, tenant, health_insurer):
        emp = _make_employee(
            tenant, health_insurer, tax_declaration_type="standard", employee_number="TD01"
        )
        db_session.add(emp)
        db_session.flush()
        assert emp.tax_declaration_type == "standard"

    def test_check_tax_declaration_type_secondary(self, db_session, tenant, health_insurer):
        emp = _make_employee(
            tenant, health_insurer, tax_declaration_type="secondary", employee_number="TD02"
        )
        db_session.add(emp)
        db_session.flush()
        assert emp.tax_declaration_type == "secondary"

    def test_check_tax_declaration_type_none(self, db_session, tenant, health_insurer):
        emp = _make_employee(
            tenant, health_insurer, tax_declaration_type="none", employee_number="TD03"
        )
        db_session.add(emp)
        db_session.flush()
        assert emp.tax_declaration_type == "none"

    def test_check_status_invalid(self, db_session, tenant, health_insurer):
        """Invalid status must be rejected."""
        emp = _make_employee(tenant, health_insurer, status="fired")
        db_session.add(emp)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_status_active(self, db_session, tenant, health_insurer):
        emp = _make_employee(tenant, health_insurer, status="active", employee_number="ST01")
        db_session.add(emp)
        db_session.flush()
        assert emp.status == "active"

    def test_check_status_inactive(self, db_session, tenant, health_insurer):
        emp = _make_employee(tenant, health_insurer, status="inactive", employee_number="ST02")
        db_session.add(emp)
        db_session.flush()
        assert emp.status == "inactive"

    def test_check_status_terminated(self, db_session, tenant, health_insurer):
        emp = _make_employee(
            tenant, health_insurer, status="terminated", employee_number="ST03"
        )
        db_session.add(emp)
        db_session.flush()
        assert emp.status == "terminated"

    def test_fk_tenant_nonexistent(self, db_session, health_insurer):
        """FK to tenant must exist."""
        emp = Employee(
            tenant_id=uuid.uuid4(),
            employee_number="FK01",
            first_name="Test",
            last_name="FK",
            birth_date=date(1990, 1, 1),
            birth_number="9001010001",
            gender="M",
            address_street="Test 1",
            address_city="Test",
            address_zip="00000",
            bank_iban="SK0000000000000000000001",
            health_insurer_id=health_insurer.id,
            tax_declaration_type="standard",
            hire_date=date(2024, 1, 1),
        )
        db_session.add(emp)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_health_insurer_nonexistent(self, db_session, tenant):
        """FK to health_insurer must exist."""
        emp = Employee(
            tenant_id=tenant.id,
            employee_number="FK02",
            first_name="Test",
            last_name="FK",
            birth_date=date(1990, 1, 1),
            birth_number="9001010002",
            gender="M",
            address_street="Test 1",
            address_city="Test",
            address_zip="00000",
            bank_iban="SK0000000000000000000002",
            health_insurer_id=uuid.uuid4(),
            tax_declaration_type="standard",
            hire_date=date(2024, 1, 1),
        )
        db_session.add(emp)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()


# ===================================================================
# Database integration tests
# ===================================================================

class TestEmployeeDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, health_insurer):
        """Full create with all fields — verify round-trip."""
        emp = _make_employee(
            tenant,
            health_insurer,
            title_before="Ing.",
            title_after="PhD.",
            bank_bic="KOMBSKBA",
            termination_date=date(2025, 12, 31),
        )
        db_session.add(emp)
        db_session.flush()

        assert emp.id is not None
        assert emp.created_at is not None
        assert emp.updated_at is not None
        assert emp.tenant_id == tenant.id
        assert emp.employee_number == "EMP001"
        assert emp.first_name == "Ján"
        assert emp.last_name == "Novák"
        assert emp.title_before == "Ing."
        assert emp.title_after == "PhD."
        assert emp.birth_date == date(1990, 5, 15)
        assert emp.gender == "M"
        assert emp.address_street == "Hlavná 1"
        assert emp.address_city == "Bratislava"
        assert emp.address_zip == "81101"
        assert emp.bank_bic == "KOMBSKBA"
        assert emp.health_insurer_id == health_insurer.id
        assert emp.tax_declaration_type == "standard"
        assert emp.hire_date == date(2024, 1, 1)
        assert emp.termination_date == date(2025, 12, 31)

    def test_create_minimal_defaults(self, db_session, tenant, health_insurer):
        """Create with only required fields — verify all server_defaults."""
        emp = _make_employee(tenant, health_insurer)
        db_session.add(emp)
        db_session.flush()

        # server_defaults
        assert emp.nationality == "SK"
        assert emp.address_country == "SK"
        assert emp.nczd_applied is True
        assert emp.pillar2_saver is False
        assert emp.is_disabled is False
        assert emp.status == "active"
        assert emp.is_deleted is False
        # nullable fields
        assert emp.title_before is None
        assert emp.title_after is None
        assert emp.bank_bic is None
        assert emp.termination_date is None

    def test_encrypted_birth_number_roundtrip(self, db_session, tenant, health_insurer):
        """birth_number must be stored encrypted and decrypted on read."""
        raw_birth_number = "9005150001"
        emp = _make_employee(
            tenant,
            health_insurer,
            birth_number=raw_birth_number,
            employee_number="ENC01",
        )
        db_session.add(emp)
        db_session.flush()

        # Verify application sees plaintext
        assert emp.birth_number == raw_birth_number

        # Verify DB stores ciphertext (not plaintext)
        row = db_session.execute(
            text("SELECT birth_number FROM employees WHERE id = :id"),
            {"id": str(emp.id)},
        ).fetchone()
        assert row is not None
        db_value = row[0]
        assert db_value != raw_birth_number  # must be encrypted
        assert len(db_value) > len(raw_birth_number)  # Fernet ciphertext is longer

    def test_encrypted_bank_iban_roundtrip(self, db_session, tenant, health_insurer):
        """bank_iban must be stored encrypted and decrypted on read."""
        raw_iban = "SK3100000000000000000099"
        emp = _make_employee(
            tenant,
            health_insurer,
            bank_iban=raw_iban,
            employee_number="ENC02",
        )
        db_session.add(emp)
        db_session.flush()

        # Verify application sees plaintext
        assert emp.bank_iban == raw_iban

        # Verify DB stores ciphertext
        row = db_session.execute(
            text("SELECT bank_iban FROM employees WHERE id = :id"),
            {"id": str(emp.id)},
        ).fetchone()
        assert row is not None
        db_value = row[0]
        assert db_value != raw_iban
        assert len(db_value) > len(raw_iban)

    def test_soft_delete(self, db_session, tenant, health_insurer):
        """Soft-delete via is_deleted flag."""
        emp = _make_employee(tenant, health_insurer, employee_number="DEL01")
        db_session.add(emp)
        db_session.flush()
        assert emp.is_deleted is False

        emp.is_deleted = True
        db_session.flush()
        assert emp.is_deleted is True

    def test_status_transition(self, db_session, tenant, health_insurer):
        """Status can be changed from active to terminated."""
        emp = _make_employee(
            tenant,
            health_insurer,
            employee_number="TRANS01",
            status="active",
        )
        db_session.add(emp)
        db_session.flush()
        assert emp.status == "active"

        emp.status = "terminated"
        emp.termination_date = date(2025, 6, 30)
        db_session.flush()
        assert emp.status == "terminated"
        assert emp.termination_date == date(2025, 6, 30)

    def test_two_employees_different_numbers(self, db_session, tenant, health_insurer):
        """Two employees with different numbers in same tenant — must succeed."""
        emp1 = _make_employee(tenant, health_insurer, employee_number="E001")
        emp2 = _make_employee(
            tenant,
            health_insurer,
            employee_number="E002",
            first_name="Peter",
            birth_number="9105150002",
            bank_iban="SK3100000000000000000098",
        )
        db_session.add_all([emp1, emp2])
        db_session.flush()
        assert emp1.id != emp2.id
