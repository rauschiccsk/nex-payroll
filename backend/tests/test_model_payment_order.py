"""Tests for PaymentOrder model (app.models.payment_order)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import Integer, Numeric, String, inspect, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.payment_order import PaymentOrder
from app.models.tenant import Tenant

# ---------------------------------------------------------------------------
# Helpers — reusable fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant(db_session):
    """Create a Tenant required as FK parent."""
    t = Tenant(
        name="PaymentOrder Test Firma s.r.o.",
        ico="99000077",
        address_street="Hlavná 1",
        address_city="Bratislava",
        address_zip="81101",
        bank_iban="SK0000000000000000000077",
        schema_name="tenant_test_payment_order",
    )
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture()
def health_insurer(db_session):
    """Create a HealthInsurer for zp-type payment orders."""
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
    """Create an Employee for net_wage payment orders."""
    emp = Employee(
        tenant_id=tenant.id,
        employee_number="EMP077",
        first_name="Ján",
        last_name="Testovací",
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


def _make_payment_order(tenant, **overrides):
    """Return a PaymentOrder instance with sensible defaults; overrides win."""
    defaults = {
        "tenant_id": tenant.id,
        "period_year": 2025,
        "period_month": 1,
        "payment_type": "net_wage",
        "recipient_name": "Ján Testovací",
        "recipient_iban": "SK3100000000000000000099",
        "amount": Decimal("1850.00"),
    }
    defaults.update(overrides)
    return PaymentOrder(**defaults)


# ===================================================================
# Schema / metadata tests (no DB required)
# ===================================================================


class TestPaymentOrderSchema:
    """Verify table metadata and schema."""

    def test_tablename(self):
        assert PaymentOrder.__tablename__ == "payment_orders"

    def test_inherits_base(self):
        from app.models.base import Base

        assert issubclass(PaymentOrder, Base)

    def test_inherits_uuid_mixin(self):
        from app.models.base import UUIDMixin

        assert issubclass(PaymentOrder, UUIDMixin)

    def test_inherits_timestamp_mixin(self):
        from app.models.base import TimestampMixin

        assert issubclass(PaymentOrder, TimestampMixin)


class TestPaymentOrderColumns:
    """Verify all columns have correct types, nullability, and defaults."""

    def setup_method(self):
        self.mapper = inspect(PaymentOrder)

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
        assert col.nullable is True

    def test_health_insurer_id_column(self):
        col = self.mapper.columns["health_insurer_id"]
        assert isinstance(col.type, UUID)
        assert col.nullable is True

    def test_period_year_column(self):
        col = self.mapper.columns["period_year"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_period_month_column(self):
        col = self.mapper.columns["period_month"]
        assert isinstance(col.type, Integer)
        assert col.nullable is False

    def test_payment_type_column(self):
        col = self.mapper.columns["payment_type"]
        assert isinstance(col.type, String)
        assert col.type.length == 30
        assert col.nullable is False

    def test_recipient_name_column(self):
        col = self.mapper.columns["recipient_name"]
        assert isinstance(col.type, String)
        assert col.type.length == 200
        assert col.nullable is False

    def test_recipient_iban_column(self):
        col = self.mapper.columns["recipient_iban"]
        assert isinstance(col.type, String)
        assert col.type.length == 34
        assert col.nullable is False

    def test_recipient_bic_column(self):
        col = self.mapper.columns["recipient_bic"]
        assert isinstance(col.type, String)
        assert col.type.length == 11
        assert col.nullable is True

    def test_amount_column(self):
        col = self.mapper.columns["amount"]
        assert isinstance(col.type, Numeric)
        assert col.type.precision == 12
        assert col.type.scale == 2
        assert col.nullable is False

    def test_variable_symbol_column(self):
        col = self.mapper.columns["variable_symbol"]
        assert isinstance(col.type, String)
        assert col.type.length == 10
        assert col.nullable is True

    def test_specific_symbol_column(self):
        col = self.mapper.columns["specific_symbol"]
        assert isinstance(col.type, String)
        assert col.type.length == 10
        assert col.nullable is True

    def test_constant_symbol_column(self):
        col = self.mapper.columns["constant_symbol"]
        assert isinstance(col.type, String)
        assert col.type.length == 4
        assert col.nullable is True

    def test_reference_column(self):
        col = self.mapper.columns["reference"]
        assert isinstance(col.type, String)
        assert col.type.length == 140
        assert col.nullable is True

    def test_status_column(self):
        col = self.mapper.columns["status"]
        assert isinstance(col.type, String)
        assert col.type.length == 20
        assert col.nullable is False
        assert col.server_default is not None

    def test_check_constraint_payment_type(self):
        """CheckConstraint for payment_type must exist."""
        table = PaymentOrder.__table__
        ck_names = [c.name for c in table.constraints if hasattr(c, "sqltext")]
        assert "ck_payment_orders_payment_type" in ck_names

    def test_check_constraint_status(self):
        """CheckConstraint for status must exist."""
        table = PaymentOrder.__table__
        ck_names = [c.name for c in table.constraints if hasattr(c, "sqltext")]
        assert "ck_payment_orders_status" in ck_names

    def test_index_tenant_period_type(self):
        """Index on (tenant_id, period_year, period_month, payment_type)."""
        indexes = PaymentOrder.__table__.indexes
        ix_names = [ix.name for ix in indexes]
        assert "ix_payment_orders_tenant_period_type" in ix_names


# ===================================================================
# Repr
# ===================================================================


class TestPaymentOrderRepr:
    """Verify __repr__ output."""

    def test_repr_format(self):
        po = PaymentOrder(
            payment_type="net_wage",
            amount=Decimal("1850.00"),
            status="pending",
        )
        result = repr(po)
        assert "PaymentOrder" in result
        assert "net_wage" in result
        assert "1850" in result


# ===================================================================
# Constraint tests (DB required)
# ===================================================================


class TestPaymentOrderConstraints:
    """DB-level constraint enforcement."""

    def test_fk_tenant_nonexistent(self, db_session, tenant):
        """FK to tenant must exist."""
        po = _make_payment_order(tenant, tenant_id=uuid.uuid4())
        db_session.add(po)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_employee_nonexistent(self, db_session, tenant):
        """FK to employee must exist if set."""
        po = _make_payment_order(tenant, employee_id=uuid.uuid4())
        db_session.add(po)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_health_insurer_nonexistent(self, db_session, tenant):
        """FK to health_insurer must exist if set."""
        po = _make_payment_order(
            tenant,
            health_insurer_id=uuid.uuid4(),
            payment_type="zp_vszp",
        )
        db_session.add(po)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_invalid_payment_type(self, db_session, tenant):
        """Invalid payment_type must be rejected."""
        po = _make_payment_order(tenant, payment_type="invalid_type")
        db_session.add(po)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_valid_payment_type_sp(self, db_session, tenant):
        """payment_type='sp' must be accepted."""
        po = _make_payment_order(
            tenant,
            payment_type="sp",
            recipient_name="Sociálna poisťovňa",
        )
        db_session.add(po)
        db_session.flush()
        assert po.payment_type == "sp"

    def test_check_valid_payment_type_zp_vszp(self, db_session, tenant, health_insurer):
        """payment_type='zp_vszp' must be accepted."""
        po = _make_payment_order(
            tenant,
            payment_type="zp_vszp",
            health_insurer_id=health_insurer.id,
            recipient_name="VšZP",
        )
        db_session.add(po)
        db_session.flush()
        assert po.payment_type == "zp_vszp"

    def test_check_valid_payment_type_zp_dovera(self, db_session, tenant):
        """payment_type='zp_dovera' must be accepted."""
        po = _make_payment_order(
            tenant,
            payment_type="zp_dovera",
            recipient_name="Dôvera",
        )
        db_session.add(po)
        db_session.flush()
        assert po.payment_type == "zp_dovera"

    def test_check_valid_payment_type_zp_union(self, db_session, tenant):
        """payment_type='zp_union' must be accepted."""
        po = _make_payment_order(
            tenant,
            payment_type="zp_union",
            recipient_name="Union ZP",
        )
        db_session.add(po)
        db_session.flush()
        assert po.payment_type == "zp_union"

    def test_check_valid_payment_type_tax(self, db_session, tenant):
        """payment_type='tax' must be accepted."""
        po = _make_payment_order(
            tenant,
            payment_type="tax",
            recipient_name="Daňový úrad",
        )
        db_session.add(po)
        db_session.flush()
        assert po.payment_type == "tax"

    def test_check_valid_payment_type_pillar2(self, db_session, tenant):
        """payment_type='pillar2' must be accepted."""
        po = _make_payment_order(
            tenant,
            payment_type="pillar2",
            recipient_name="DSS a.s.",
        )
        db_session.add(po)
        db_session.flush()
        assert po.payment_type == "pillar2"

    def test_check_invalid_status(self, db_session, tenant):
        """Invalid status must be rejected."""
        po = _make_payment_order(tenant, status="invalid_status")
        db_session.add(po)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_check_valid_status_exported(self, db_session, tenant):
        """status='exported' must be accepted."""
        po = _make_payment_order(tenant, status="exported")
        db_session.add(po)
        db_session.flush()
        assert po.status == "exported"

    def test_check_valid_status_paid(self, db_session, tenant):
        """status='paid' must be accepted."""
        po = _make_payment_order(tenant, status="paid")
        db_session.add(po)
        db_session.flush()
        assert po.status == "paid"

    def test_not_null_payment_type(self, db_session, tenant):
        """payment_type cannot be NULL."""
        po = _make_payment_order(tenant, payment_type=None)
        db_session.add(po)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_recipient_name(self, db_session, tenant):
        """recipient_name cannot be NULL."""
        po = _make_payment_order(tenant, recipient_name=None)
        db_session.add(po)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_recipient_iban(self, db_session, tenant):
        """recipient_iban cannot be NULL."""
        po = _make_payment_order(tenant, recipient_iban=None)
        db_session.add(po)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_not_null_amount(self, db_session, tenant):
        """amount cannot be NULL."""
        po = _make_payment_order(tenant, amount=None)
        db_session.add(po)
        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.flush()
        db_session.rollback()

    def test_fk_tenant_restrict_delete(self, db_session, tenant):
        """Deleting a tenant with payment orders must be rejected (RESTRICT).

        Uses raw SQL per FK RESTRICT Test Pattern — ORM session.delete()
        sets FK to NULL first (NOT NULL failure before FK check).
        """
        po = _make_payment_order(tenant)
        db_session.add(po)
        db_session.flush()

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM tenants WHERE id = :id"),
                {"id": str(tenant.id)},
            )
        db_session.rollback()


# ===================================================================
# Database integration tests
# ===================================================================


class TestPaymentOrderDB:
    """Integration tests with actual database."""

    def test_create_and_read(self, db_session, tenant, employee, health_insurer):
        """Full create with all fields — verify round-trip."""
        po = _make_payment_order(
            tenant,
            employee_id=employee.id,
            health_insurer_id=health_insurer.id,
            payment_type="net_wage",
            recipient_name="Ján Testovací",
            recipient_iban="SK3100000000000000000099",
            recipient_bic="GIBASKBX",
            amount=Decimal("1850.75"),
            variable_symbol="1234567890",
            specific_symbol="0001",
            constant_symbol="0558",
            reference="Mzda 01/2025",
            status="pending",
        )
        db_session.add(po)
        db_session.flush()

        assert po.id is not None
        assert po.created_at is not None
        assert po.updated_at is not None
        assert po.tenant_id == tenant.id
        assert po.employee_id == employee.id
        assert po.health_insurer_id == health_insurer.id
        assert po.period_year == 2025
        assert po.period_month == 1
        assert po.payment_type == "net_wage"
        assert po.recipient_name == "Ján Testovací"
        assert po.recipient_iban == "SK3100000000000000000099"
        assert po.recipient_bic == "GIBASKBX"
        assert po.amount == Decimal("1850.75")
        assert po.variable_symbol == "1234567890"
        assert po.specific_symbol == "0001"
        assert po.constant_symbol == "0558"
        assert po.reference == "Mzda 01/2025"
        assert po.status == "pending"

    def test_create_minimal_defaults(self, db_session, tenant):
        """Create with only required fields — verify all server_defaults."""
        po = _make_payment_order(tenant)
        db_session.add(po)
        db_session.flush()

        assert po.id is not None
        assert po.status == "pending"
        assert po.employee_id is None
        assert po.health_insurer_id is None
        assert po.recipient_bic is None
        assert po.variable_symbol is None
        assert po.specific_symbol is None
        assert po.constant_symbol is None
        assert po.reference is None

    def test_update_status(self, db_session, tenant):
        """Status can be updated from pending to exported."""
        po = _make_payment_order(tenant)
        db_session.add(po)
        db_session.flush()
        assert po.status == "pending"

        po.status = "exported"
        db_session.flush()
        assert po.status == "exported"

    def test_employee_nullable(self, db_session, tenant):
        """employee_id can be NULL (e.g. for SP, ZP, tax types)."""
        po = _make_payment_order(tenant, employee_id=None, payment_type="sp")
        db_session.add(po)
        db_session.flush()
        assert po.employee_id is None

    def test_employee_with_net_wage(self, db_session, tenant, employee):
        """employee_id can be set for net_wage type."""
        po = _make_payment_order(
            tenant,
            employee_id=employee.id,
            payment_type="net_wage",
        )
        db_session.add(po)
        db_session.flush()
        assert po.employee_id == employee.id

    def test_health_insurer_nullable(self, db_session, tenant):
        """health_insurer_id can be NULL (e.g. for SP, tax types)."""
        po = _make_payment_order(tenant, health_insurer_id=None, payment_type="sp")
        db_session.add(po)
        db_session.flush()
        assert po.health_insurer_id is None

    def test_health_insurer_with_zp_type(self, db_session, tenant, health_insurer):
        """health_insurer_id can be set for ZP-type orders."""
        po = _make_payment_order(
            tenant,
            payment_type="zp_vszp",
            health_insurer_id=health_insurer.id,
            recipient_name="VšZP",
        )
        db_session.add(po)
        db_session.flush()
        assert po.health_insurer_id == health_insurer.id

    def test_multiple_orders_same_period(self, db_session, tenant):
        """Multiple payment orders for same period (different types) — allowed."""
        po1 = _make_payment_order(
            tenant, payment_type="net_wage", recipient_name="Zamestnanec 1"
        )
        po2 = _make_payment_order(
            tenant, payment_type="sp", recipient_name="Sociálna poisťovňa"
        )
        db_session.add_all([po1, po2])
        db_session.flush()
        assert po1.id != po2.id

    def test_multiple_net_wage_orders_same_period(self, db_session, tenant, employee):
        """Multiple net_wage orders for same period — allowed (different employees)."""
        po1 = _make_payment_order(
            tenant,
            payment_type="net_wage",
            employee_id=employee.id,
            recipient_name="Zamestnanec 1",
        )
        po2 = _make_payment_order(
            tenant,
            payment_type="net_wage",
            recipient_name="Zamestnanec 2",
        )
        db_session.add_all([po1, po2])
        db_session.flush()
        assert po1.id != po2.id
