"""Tests for LeaveEntitlement service layer."""

from datetime import date
from uuid import uuid4

import pytest

from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.leave_entitlement import LeaveEntitlement
from app.models.tenant import Tenant
from app.schemas.leave_entitlement import LeaveEntitlementCreate, LeaveEntitlementUpdate
from app.services.leave_entitlement import (
    count_leave_entitlements,
    create_leave_entitlement,
    delete_leave_entitlement,
    get_leave_entitlement,
    list_leave_entitlements,
    update_leave_entitlement,
)

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


def _make_health_insurer(db_session, **overrides) -> HealthInsurer:
    """Insert a minimal HealthInsurer and flush; return the instance."""
    defaults = {
        "code": "25",
        "name": "VšZP",
        "iban": "SK0000000000000000000025",
    }
    defaults.update(overrides)
    insurer = HealthInsurer(**defaults)
    db_session.add(insurer)
    db_session.flush()
    return insurer


def _make_employee(db_session, tenant_id, health_insurer_id, **overrides) -> Employee:
    """Insert a minimal Employee and flush; return the instance."""
    defaults = {
        "tenant_id": tenant_id,
        "employee_number": "EMP001",
        "first_name": "Ján",
        "last_name": "Novák",
        "birth_date": date(1990, 5, 15),
        "birth_number": "9005150001",
        "gender": "M",
        "nationality": "SK",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "health_insurer_id": health_insurer_id,
        "tax_declaration_type": "standard",
        "nczd_applied": True,
        "pillar2_saver": False,
        "is_disabled": False,
        "status": "active",
        "hire_date": date(2024, 1, 15),
    }
    defaults.update(overrides)
    employee = Employee(**defaults)
    db_session.add(employee)
    db_session.flush()
    return employee


def _make_entitlement_payload(tenant_id, employee_id, **overrides) -> LeaveEntitlementCreate:
    """Build a valid LeaveEntitlementCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "year": 2025,
        "total_days": 25,
        "used_days": 0,
        "remaining_days": 25,
        "carryover_days": 0,
    }
    defaults.update(overrides)
    return LeaveEntitlementCreate(**defaults)


def _setup_prerequisites(db_session):
    """Create tenant, insurer and employee; return (tenant, employee)."""
    tenant = _make_tenant(db_session)
    insurer = _make_health_insurer(db_session)
    employee = _make_employee(db_session, tenant.id, insurer.id)
    return tenant, employee


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateLeaveEntitlement:
    """Tests for create_leave_entitlement."""

    def test_create_returns_model_instance(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_entitlement_payload(tenant.id, employee.id)

        result = create_leave_entitlement(db_session, payload)

        assert isinstance(result, LeaveEntitlement)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.employee_id == employee.id
        assert result.year == 2025
        assert result.total_days == 25
        assert result.used_days == 0
        assert result.remaining_days == 25
        assert result.carryover_days == 0

    def test_create_with_carryover(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_entitlement_payload(
            tenant.id,
            employee.id,
            carryover_days=5,
            total_days=30,
            remaining_days=30,
        )

        result = create_leave_entitlement(db_session, payload)

        assert result.carryover_days == 5
        assert result.total_days == 30

    def test_create_with_used_days(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_entitlement_payload(
            tenant.id,
            employee.id,
            used_days=10,
            remaining_days=15,
        )

        result = create_leave_entitlement(db_session, payload)

        assert result.used_days == 10
        assert result.remaining_days == 15

    def test_create_different_years_same_employee(self, db_session):
        """An employee can have entitlements for different years."""
        tenant, employee = _setup_prerequisites(db_session)

        ent_a = create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2024),
        )
        ent_b = create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2025),
        )

        assert ent_a.id != ent_b.id
        assert ent_a.employee_id == ent_b.employee_id
        assert ent_a.year == 2024
        assert ent_b.year == 2025

    def test_create_duplicate_raises_value_error(self, db_session):
        """Duplicate (tenant_id, employee_id, year) must raise ValueError."""
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_entitlement_payload(tenant.id, employee.id, year=2025)

        create_leave_entitlement(db_session, payload)

        with pytest.raises(ValueError, match="already exists"):
            create_leave_entitlement(db_session, payload)


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetLeaveEntitlement:
    """Tests for get_leave_entitlement."""

    def test_get_existing(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, employee.id))

        fetched = get_leave_entitlement(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.year == created.year

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_leave_entitlement(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListLeaveEntitlements:
    """Tests for list_leave_entitlements."""

    def test_list_empty(self, db_session):
        result = list_leave_entitlements(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2024),
        )
        create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2025),
        )

        result = list_leave_entitlements(db_session)
        assert len(result) == 2

    def test_list_ordering_by_year_desc(self, db_session):
        """Entitlements are ordered by year descending."""
        tenant, employee = _setup_prerequisites(db_session)

        create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2023),
        )
        create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2025),
        )
        create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2024),
        )

        result = list_leave_entitlements(db_session)
        assert result[0].year == 2025
        assert result[1].year == 2024
        assert result[2].year == 2023

    def test_list_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant_a.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant_b.id, insurer.id, employee_number="EMP002")

        create_leave_entitlement(db_session, _make_entitlement_payload(tenant_a.id, emp_a.id))
        create_leave_entitlement(db_session, _make_entitlement_payload(tenant_b.id, emp_b.id))

        result = list_leave_entitlements(db_session, tenant_id=tenant_a.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id

    def test_list_scoped_by_employee(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP002")

        create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, emp_a.id))
        create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, emp_b.id))

        result = list_leave_entitlements(db_session, employee_id=emp_a.id)
        assert len(result) == 1
        assert result[0].employee_id == emp_a.id

    def test_list_scoped_by_year(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2024),
        )
        create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2025),
        )

        result = list_leave_entitlements(db_session, year=2024)
        assert len(result) == 1
        assert result[0].year == 2024

    def test_list_pagination_skip(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for yr in range(2023, 2026):
            create_leave_entitlement(
                db_session,
                _make_entitlement_payload(tenant.id, employee.id, year=yr),
            )

        result = list_leave_entitlements(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for yr in range(2023, 2026):
            create_leave_entitlement(
                db_session,
                _make_entitlement_payload(tenant.id, employee.id, year=yr),
            )

        result = list_leave_entitlements(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for yr in range(2020, 2026):
            create_leave_entitlement(
                db_session,
                _make_entitlement_payload(tenant.id, employee.id, year=yr),
            )

        result = list_leave_entitlements(db_session, skip=1, limit=2)
        assert len(result) == 2

    def test_list_default_limit_is_50(self, db_session):
        """Default limit should be 50 per project convention."""
        import inspect

        sig = inspect.signature(list_leave_entitlements)
        assert sig.parameters["limit"].default == 50


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountLeaveEntitlements:
    """Tests for count_leave_entitlements."""

    def test_count_empty(self, db_session):
        result = count_leave_entitlements(db_session)
        assert result == 0

    def test_count_all(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        for yr in range(2023, 2026):
            create_leave_entitlement(
                db_session,
                _make_entitlement_payload(tenant.id, employee.id, year=yr),
            )

        result = count_leave_entitlements(db_session)
        assert result == 3

    def test_count_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant_a.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant_b.id, insurer.id, employee_number="EMP002")

        create_leave_entitlement(db_session, _make_entitlement_payload(tenant_a.id, emp_a.id))
        create_leave_entitlement(db_session, _make_entitlement_payload(tenant_b.id, emp_b.id))

        assert count_leave_entitlements(db_session, tenant_id=tenant_a.id) == 1
        assert count_leave_entitlements(db_session, tenant_id=tenant_b.id) == 1

    def test_count_scoped_by_employee(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP002")

        create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, emp_a.id, year=2024))
        create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, emp_a.id, year=2025))
        create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, emp_b.id, year=2025))

        assert count_leave_entitlements(db_session, employee_id=emp_a.id) == 2
        assert count_leave_entitlements(db_session, employee_id=emp_b.id) == 1

    def test_count_scoped_by_year(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2024),
        )
        create_leave_entitlement(
            db_session,
            _make_entitlement_payload(tenant.id, employee.id, year=2025),
        )

        assert count_leave_entitlements(db_session, year=2024) == 1
        assert count_leave_entitlements(db_session, year=2025) == 1


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateLeaveEntitlement:
    """Tests for update_leave_entitlement."""

    def test_update_single_field(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, employee.id))

        updated = update_leave_entitlement(
            db_session,
            created.id,
            LeaveEntitlementUpdate(used_days=5),
        )

        assert updated is not None
        assert updated.used_days == 5
        # unchanged fields stay the same
        assert updated.total_days == 25

    def test_update_multiple_fields(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, employee.id))

        updated = update_leave_entitlement(
            db_session,
            created.id,
            LeaveEntitlementUpdate(
                used_days=10,
                remaining_days=15,
            ),
        )

        assert updated is not None
        assert updated.used_days == 10
        assert updated.remaining_days == 15

    def test_update_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            update_leave_entitlement(
                db_session,
                uuid4(),
                LeaveEntitlementUpdate(used_days=5),
            )

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, employee.id))

        updated = update_leave_entitlement(
            db_session,
            created.id,
            LeaveEntitlementUpdate(),
        )

        assert updated is not None
        assert updated.total_days == created.total_days
        assert updated.used_days == created.used_days

    def test_update_carryover_days(self, db_session):
        """Update carryover days."""
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, employee.id))

        updated = update_leave_entitlement(
            db_session,
            created.id,
            LeaveEntitlementUpdate(carryover_days=3),
        )

        assert updated is not None
        assert updated.carryover_days == 3
        # total_days unchanged
        assert updated.total_days == 25


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteLeaveEntitlement:
    """Tests for delete_leave_entitlement."""

    def test_delete_existing(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave_entitlement(db_session, _make_entitlement_payload(tenant.id, employee.id))

        deleted = delete_leave_entitlement(db_session, created.id)

        assert deleted is True
        assert get_leave_entitlement(db_session, created.id) is None

    def test_delete_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            delete_leave_entitlement(db_session, uuid4())
