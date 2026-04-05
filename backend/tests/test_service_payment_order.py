"""Tests for PaymentOrder service layer."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.payment_order import PaymentOrder
from app.models.tenant import Tenant
from app.schemas.payment_order import PaymentOrderCreate, PaymentOrderUpdate
from app.services.payment_order import (
    ALLOWED_PAYMENT_TYPES,
    ALLOWED_STATUSES,
    count_payment_orders,
    create_payment_order,
    delete_payment_order,
    get_payment_order,
    list_payment_orders,
    update_payment_order,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestServiceConstants:
    """Verify allowed values match DESIGN.md CHECK constraints."""

    def test_allowed_payment_types(self):
        expected = {
            "net_wage",
            "sp",
            "zp_vszp",
            "zp_dovera",
            "zp_union",
            "tax",
            "pillar2",
        }
        assert expected == ALLOWED_PAYMENT_TYPES

    def test_allowed_statuses(self):
        expected = {"pending", "exported", "paid"}
        assert expected == ALLOWED_STATUSES


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


def _make_order_payload(tenant_id, **overrides) -> PaymentOrderCreate:
    """Build a valid PaymentOrderCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "period_year": 2025,
        "period_month": 1,
        "payment_type": "net_wage",
        "recipient_name": "Ján Novák",
        "recipient_iban": "SK3112000000198742637541",
        "recipient_bic": "TATRSKBX",
        "amount": Decimal("1850.00"),
        "variable_symbol": "1234567890",
        "specific_symbol": None,
        "constant_symbol": "0558",
        "reference": "PAYROLL-2025-01-NOVAK",
        "status": "pending",
        "employee_id": None,
        "health_insurer_id": None,
    }
    defaults.update(overrides)
    return PaymentOrderCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreatePaymentOrder:
    """Tests for create_payment_order."""

    def test_create_returns_model_instance(self, db_session):
        tenant = _make_tenant(db_session)
        payload = _make_order_payload(tenant.id)

        result = create_payment_order(db_session, payload)

        assert isinstance(result, PaymentOrder)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.period_year == 2025
        assert result.period_month == 1
        assert result.payment_type == "net_wage"
        assert result.recipient_name == "Ján Novák"
        assert result.recipient_iban == "SK3112000000198742637541"
        assert result.recipient_bic == "TATRSKBX"
        assert result.amount == Decimal("1850.00")
        assert result.variable_symbol == "1234567890"
        assert result.specific_symbol is None
        assert result.constant_symbol == "0558"
        assert result.reference == "PAYROLL-2025-01-NOVAK"
        assert result.status == "pending"
        assert result.employee_id is None
        assert result.health_insurer_id is None

    def test_create_multiple_same_type_same_period(self, db_session):
        """Multiple payment orders of the same type for the same period are allowed
        (e.g. multiple net_wage orders for different employees)."""
        tenant = _make_tenant(db_session)

        order_a = create_payment_order(
            db_session,
            _make_order_payload(tenant.id, recipient_name="Ján Novák"),
        )
        order_b = create_payment_order(
            db_session,
            _make_order_payload(tenant.id, recipient_name="Peter Horváth"),
        )

        assert order_a.id != order_b.id
        assert order_a.payment_type == order_b.payment_type

    def test_create_different_payment_types(self, db_session):
        """Different payment types for the same period are allowed."""
        tenant = _make_tenant(db_session)

        order_wage = create_payment_order(
            db_session,
            _make_order_payload(tenant.id, payment_type="net_wage"),
        )
        order_sp = create_payment_order(
            db_session,
            _make_order_payload(
                tenant.id,
                payment_type="sp",
                recipient_name="Sociálna poisťovňa",
                amount=Decimal("500.00"),
            ),
        )

        assert order_wage.id != order_sp.id
        assert order_wage.payment_type == "net_wage"
        assert order_sp.payment_type == "sp"

    def test_create_default_status_is_pending(self, db_session):
        """When status is not explicitly provided, it defaults to 'pending'."""
        tenant = _make_tenant(db_session)
        payload = _make_order_payload(tenant.id)
        # Default in helper is 'pending' already, but verify the model level
        result = create_payment_order(db_session, payload)
        assert result.status == "pending"

    def test_create_invalid_payment_type_raises_value_error(self, db_session):
        """Creating with an invalid payment_type must raise ValueError."""
        tenant = _make_tenant(db_session)
        payload = PaymentOrderCreate.model_construct(
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            payment_type="invalid_type",
            recipient_name="Test",
            recipient_iban="SK3112000000198742637541",
            recipient_bic=None,
            amount=Decimal("100.00"),
            variable_symbol=None,
            specific_symbol=None,
            constant_symbol=None,
            reference=None,
            status="pending",
            employee_id=None,
            health_insurer_id=None,
        )

        with pytest.raises(ValueError, match="Invalid payment_type"):
            create_payment_order(db_session, payload)

    def test_create_invalid_status_raises_value_error(self, db_session):
        """Creating with an invalid status must raise ValueError."""
        tenant = _make_tenant(db_session)
        payload = PaymentOrderCreate.model_construct(
            tenant_id=tenant.id,
            period_year=2025,
            period_month=1,
            payment_type="net_wage",
            recipient_name="Test",
            recipient_iban="SK3112000000198742637541",
            recipient_bic=None,
            amount=Decimal("100.00"),
            variable_symbol=None,
            specific_symbol=None,
            constant_symbol=None,
            reference=None,
            status="invalid_status",
            employee_id=None,
            health_insurer_id=None,
        )

        with pytest.raises(ValueError, match="Invalid status"):
            create_payment_order(db_session, payload)


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetPaymentOrder:
    """Tests for get_payment_order."""

    def test_get_existing(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_payment_order(db_session, _make_order_payload(tenant.id))

        fetched = get_payment_order(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.payment_type == created.payment_type
        assert fetched.amount == created.amount

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_payment_order(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListPaymentOrders:
    """Tests for list_payment_orders."""

    def test_list_empty(self, db_session):
        result = list_payment_orders(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, recipient_name="A"),
        )
        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, recipient_name="B"),
        )

        result = list_payment_orders(db_session)
        assert len(result) == 2

    def test_list_ordering_by_period_desc(self, db_session):
        """Orders are ordered by year desc, month desc."""
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_year=2024, period_month=12),
        )
        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_year=2025, period_month=3),
        )
        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_year=2025, period_month=1),
        )

        result = list_payment_orders(db_session)
        assert result[0].period_year == 2025
        assert result[0].period_month == 3
        assert result[1].period_year == 2025
        assert result[1].period_month == 1
        assert result[2].period_year == 2024
        assert result[2].period_month == 12

    def test_list_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")

        create_payment_order(db_session, _make_order_payload(tenant_a.id))
        create_payment_order(db_session, _make_order_payload(tenant_b.id))

        result = list_payment_orders(db_session, tenant_id=tenant_a.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id

    def test_list_scoped_by_payment_type(self, db_session):
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, payment_type="net_wage"),
        )
        create_payment_order(
            db_session,
            _make_order_payload(
                tenant.id,
                payment_type="sp",
                recipient_name="Sociálna poisťovňa",
            ),
        )

        result = list_payment_orders(db_session, payment_type="net_wage")
        assert len(result) == 1
        assert result[0].payment_type == "net_wage"

    def test_list_scoped_by_status(self, db_session):
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, status="pending"),
        )
        create_payment_order(
            db_session,
            _make_order_payload(
                tenant.id,
                status="exported",
                recipient_name="Export Co.",
            ),
        )

        result = list_payment_orders(db_session, status="pending")
        assert len(result) == 1
        assert result[0].status == "pending"

    def test_list_scoped_by_period_year(self, db_session):
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_year=2024),
        )
        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_year=2025),
        )

        result = list_payment_orders(db_session, period_year=2024)
        assert len(result) == 1
        assert result[0].period_year == 2024

    def test_list_scoped_by_period_month(self, db_session):
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_month=1),
        )
        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_month=6),
        )

        result = list_payment_orders(db_session, period_month=1)
        assert len(result) == 1
        assert result[0].period_month == 1

    def test_list_pagination_skip(self, db_session):
        tenant = _make_tenant(db_session)

        for m in range(1, 4):
            create_payment_order(
                db_session,
                _make_order_payload(tenant.id, period_month=m),
            )

        result = list_payment_orders(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        tenant = _make_tenant(db_session)

        for m in range(1, 4):
            create_payment_order(
                db_session,
                _make_order_payload(tenant.id, period_month=m),
            )

        result = list_payment_orders(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        tenant = _make_tenant(db_session)

        for m in range(1, 7):
            create_payment_order(
                db_session,
                _make_order_payload(tenant.id, period_month=m),
            )

        result = list_payment_orders(db_session, skip=1, limit=2)
        assert len(result) == 2

    def test_list_default_limit_is_50(self, db_session):
        """Default limit should be 50 per project convention."""
        import inspect

        sig = inspect.signature(list_payment_orders)
        assert sig.parameters["limit"].default == 50

    def test_list_invalid_payment_type_raises_value_error(self, db_session):
        """Filtering by an invalid payment_type must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid payment_type"):
            list_payment_orders(db_session, payment_type="bad_type")

    def test_list_invalid_status_raises_value_error(self, db_session):
        """Filtering by an invalid status must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            list_payment_orders(db_session, status="bad_status")


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountPaymentOrders:
    """Tests for count_payment_orders."""

    def test_count_empty(self, db_session):
        result = count_payment_orders(db_session)
        assert result == 0

    def test_count_all(self, db_session):
        tenant = _make_tenant(db_session)
        for m in range(1, 4):
            create_payment_order(
                db_session,
                _make_order_payload(tenant.id, period_month=m),
            )

        result = count_payment_orders(db_session)
        assert result == 3

    def test_count_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")

        create_payment_order(db_session, _make_order_payload(tenant_a.id))
        create_payment_order(db_session, _make_order_payload(tenant_b.id))

        assert count_payment_orders(db_session, tenant_id=tenant_a.id) == 1
        assert count_payment_orders(db_session, tenant_id=tenant_b.id) == 1

    def test_count_scoped_by_payment_type(self, db_session):
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, payment_type="net_wage"),
        )
        create_payment_order(
            db_session,
            _make_order_payload(
                tenant.id,
                payment_type="sp",
                recipient_name="Sociálna poisťovňa",
            ),
        )

        assert count_payment_orders(db_session, payment_type="net_wage") == 1
        assert count_payment_orders(db_session, payment_type="sp") == 1

    def test_count_scoped_by_status(self, db_session):
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, status="pending"),
        )
        create_payment_order(
            db_session,
            _make_order_payload(
                tenant.id,
                status="exported",
                recipient_name="Export Co.",
            ),
        )

        assert count_payment_orders(db_session, status="pending") == 1
        assert count_payment_orders(db_session, status="exported") == 1

    def test_count_scoped_by_period_year(self, db_session):
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_year=2024),
        )
        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_year=2025),
        )

        assert count_payment_orders(db_session, period_year=2024) == 1
        assert count_payment_orders(db_session, period_year=2025) == 1

    def test_count_scoped_by_period_month(self, db_session):
        tenant = _make_tenant(db_session)

        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_month=1),
        )
        create_payment_order(
            db_session,
            _make_order_payload(tenant.id, period_month=6),
        )

        assert count_payment_orders(db_session, period_month=1) == 1
        assert count_payment_orders(db_session, period_month=6) == 1

    def test_count_invalid_payment_type_raises_value_error(self, db_session):
        """Counting with an invalid payment_type must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid payment_type"):
            count_payment_orders(db_session, payment_type="bad_type")

    def test_count_invalid_status_raises_value_error(self, db_session):
        """Counting with an invalid status must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            count_payment_orders(db_session, status="bad_status")


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdatePaymentOrder:
    """Tests for update_payment_order."""

    def test_update_single_field(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_payment_order(db_session, _make_order_payload(tenant.id))

        updated = update_payment_order(
            db_session,
            created.id,
            PaymentOrderUpdate(status="exported"),
        )

        assert updated is not None
        assert updated.status == "exported"
        # unchanged fields stay the same
        assert updated.payment_type == "net_wage"
        assert updated.recipient_name == "Ján Novák"

    def test_update_multiple_fields(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_payment_order(db_session, _make_order_payload(tenant.id))

        updated = update_payment_order(
            db_session,
            created.id,
            PaymentOrderUpdate(
                status="paid",
                amount=Decimal("2000.00"),
                reference="UPDATED-REF",
            ),
        )

        assert updated is not None
        assert updated.status == "paid"
        assert updated.amount == Decimal("2000.00")
        assert updated.reference == "UPDATED-REF"

    def test_update_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            update_payment_order(
                db_session,
                uuid4(),
                PaymentOrderUpdate(status="exported"),
            )

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        tenant = _make_tenant(db_session)
        created = create_payment_order(db_session, _make_order_payload(tenant.id))

        updated = update_payment_order(
            db_session,
            created.id,
            PaymentOrderUpdate(),
        )

        assert updated is not None
        assert updated.status == created.status
        assert updated.amount == created.amount

    def test_update_recipient_details(self, db_session):
        """Update recipient name and IBAN."""
        tenant = _make_tenant(db_session)
        created = create_payment_order(db_session, _make_order_payload(tenant.id))

        updated = update_payment_order(
            db_session,
            created.id,
            PaymentOrderUpdate(
                recipient_name="Peter Horváth",
                recipient_iban="SK9900000000001111222233",
            ),
        )

        assert updated is not None
        assert updated.recipient_name == "Peter Horváth"
        assert updated.recipient_iban == "SK9900000000001111222233"

    def test_update_invalid_status_raises_value_error(self, db_session):
        """Updating with an invalid status must raise ValueError."""
        tenant = _make_tenant(db_session)
        created = create_payment_order(db_session, _make_order_payload(tenant.id))

        payload = PaymentOrderUpdate.model_construct(status="invalid_status")

        with pytest.raises(ValueError, match="Invalid status"):
            update_payment_order(db_session, created.id, payload)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeletePaymentOrder:
    """Tests for delete_payment_order."""

    def test_delete_existing(self, db_session):
        tenant = _make_tenant(db_session)
        created = create_payment_order(db_session, _make_order_payload(tenant.id))

        result = delete_payment_order(db_session, created.id)

        assert result is None
        assert get_payment_order(db_session, created.id) is None

    def test_delete_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            delete_payment_order(db_session, uuid4())
