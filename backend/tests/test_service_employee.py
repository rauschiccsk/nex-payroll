"""Tests for Employee service layer."""

from datetime import date
from uuid import uuid4

import pytest

from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.tenant import Tenant
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.employee import (
    create_employee,
    delete_employee,
    get_employee,
    list_employees,
    update_employee,
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


def _make_payload(tenant_id, health_insurer_id, **overrides) -> EmployeeCreate:
    """Build a valid EmployeeCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "employee_number": "EMP001",
        "first_name": "Ján",
        "last_name": "Novák",
        "title_before": None,
        "title_after": None,
        "birth_date": date(1990, 5, 15),
        "birth_number": "9005150001",
        "gender": "M",
        "nationality": "SK",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "bank_bic": "SUBASKBX",
        "health_insurer_id": health_insurer_id,
        "tax_declaration_type": "standard",
        "nczd_applied": True,
        "pillar2_saver": False,
        "is_disabled": False,
        "status": "active",
        "hire_date": date(2024, 1, 15),
        "termination_date": None,
        "is_deleted": False,
    }
    defaults.update(overrides)
    return EmployeeCreate(**defaults)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateEmployee:
    """Tests for create_employee."""

    def test_create_returns_model_instance(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        payload = _make_payload(tenant.id, insurer.id)

        result = create_employee(db_session, payload)

        assert isinstance(result, Employee)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.employee_number == "EMP001"
        assert result.first_name == "Ján"
        assert result.last_name == "Novák"
        assert result.birth_date == date(1990, 5, 15)
        assert result.gender == "M"
        assert result.health_insurer_id == insurer.id
        assert result.tax_declaration_type == "standard"
        assert result.status == "active"
        assert result.hire_date == date(2024, 1, 15)
        assert result.is_deleted is False

    def test_create_with_optional_fields(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        payload = _make_payload(
            tenant.id,
            insurer.id,
            title_before="Ing.",
            title_after="PhD.",
            bank_bic=None,
        )

        result = create_employee(db_session, payload)

        assert result.title_before == "Ing."
        assert result.title_after == "PhD."
        assert result.bank_bic is None

    def test_create_duplicate_employee_number_raises(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)

        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="DUP001"),
        )

        with pytest.raises(ValueError, match="employee_number='DUP001' already exists"):
            create_employee(
                db_session,
                _make_payload(
                    tenant.id,
                    insurer.id,
                    employee_number="DUP001",
                    first_name="Iný",
                ),
            )

    def test_create_same_number_different_tenant_ok(self, db_session):
        """Same employee_number in different tenants is allowed."""
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)

        emp_a = create_employee(
            db_session,
            _make_payload(tenant_a.id, insurer.id, employee_number="EMP001"),
        )
        emp_b = create_employee(
            db_session,
            _make_payload(tenant_b.id, insurer.id, employee_number="EMP001"),
        )

        assert emp_a.id != emp_b.id
        assert emp_a.employee_number == emp_b.employee_number


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetEmployee:
    """Tests for get_employee."""

    def test_get_existing(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        created = create_employee(db_session, _make_payload(tenant.id, insurer.id))

        fetched = get_employee(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.employee_number == created.employee_number

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_employee(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListEmployees:
    """Tests for list_employees."""

    def test_list_empty(self, db_session):
        result = list_employees(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)

        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP001"),
        )
        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP002"),
        )

        result = list_employees(db_session)
        assert len(result) == 2

    def test_list_ordering_by_last_name(self, db_session):
        """Employees are ordered by last_name, first_name ascending."""
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)

        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP002", last_name="Zvolenský"),
        )
        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP001", last_name="Adam"),
        )

        result = list_employees(db_session)
        assert result[0].last_name == "Adam"
        assert result[1].last_name == "Zvolenský"

    def test_list_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)

        create_employee(
            db_session,
            _make_payload(tenant_a.id, insurer.id, employee_number="EMP001"),
        )
        create_employee(
            db_session,
            _make_payload(tenant_b.id, insurer.id, employee_number="EMP002"),
        )

        result = list_employees(db_session, tenant_id=tenant_a.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id

    def test_list_excludes_deleted_by_default(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)

        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP001"),
        )
        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP002", is_deleted=True),
        )

        result = list_employees(db_session)
        assert len(result) == 1
        assert result[0].employee_number == "EMP001"

    def test_list_include_deleted(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)

        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP001"),
        )
        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP002", is_deleted=True),
        )

        result = list_employees(db_session, include_deleted=True)
        assert len(result) == 2

    def test_list_pagination_skip(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)

        for i in range(3):
            create_employee(
                db_session,
                _make_payload(tenant.id, insurer.id, employee_number=f"EMP{i:03d}"),
            )

        result = list_employees(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)

        for i in range(3):
            create_employee(
                db_session,
                _make_payload(tenant.id, insurer.id, employee_number=f"EMP{i:03d}"),
            )

        result = list_employees(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)

        for i in range(5):
            create_employee(
                db_session,
                _make_payload(tenant.id, insurer.id, employee_number=f"EMP{i:03d}"),
            )

        result = list_employees(db_session, skip=1, limit=2)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateEmployee:
    """Tests for update_employee."""

    def test_update_single_field(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        created = create_employee(db_session, _make_payload(tenant.id, insurer.id))

        updated = update_employee(
            db_session,
            created.id,
            EmployeeUpdate(first_name="Peter"),
        )

        assert updated is not None
        assert updated.first_name == "Peter"
        # unchanged fields stay the same
        assert updated.last_name == "Novák"

    def test_update_multiple_fields(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        created = create_employee(db_session, _make_payload(tenant.id, insurer.id))

        updated = update_employee(
            db_session,
            created.id,
            EmployeeUpdate(
                address_city="Košice",
                address_zip="04001",
                status="inactive",
            ),
        )

        assert updated is not None
        assert updated.address_city == "Košice"
        assert updated.address_zip == "04001"
        assert updated.status == "inactive"

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_employee(
            db_session,
            uuid4(),
            EmployeeUpdate(first_name="Ghost"),
        )
        assert result is None

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        created = create_employee(db_session, _make_payload(tenant.id, insurer.id))

        updated = update_employee(
            db_session,
            created.id,
            EmployeeUpdate(),
        )

        assert updated is not None
        assert updated.first_name == created.first_name

    def test_update_employee_number_duplicate_raises(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)

        create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP001"),
        )
        second = create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP002"),
        )

        with pytest.raises(ValueError, match="employee_number='EMP001' already exists"):
            update_employee(
                db_session,
                second.id,
                EmployeeUpdate(employee_number="EMP001"),
            )

    def test_update_employee_number_same_value_no_error(self, db_session):
        """Updating employee_number to the same value should NOT raise."""
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        created = create_employee(
            db_session,
            _make_payload(tenant.id, insurer.id, employee_number="EMP099"),
        )

        updated = update_employee(
            db_session,
            created.id,
            EmployeeUpdate(employee_number="EMP099"),
        )

        assert updated is not None
        assert updated.employee_number == "EMP099"

    def test_update_soft_delete_flag(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        created = create_employee(db_session, _make_payload(tenant.id, insurer.id))

        updated = update_employee(
            db_session,
            created.id,
            EmployeeUpdate(is_deleted=True),
        )

        assert updated is not None
        assert updated.is_deleted is True


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteEmployee:
    """Tests for delete_employee."""

    def test_delete_existing(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        created = create_employee(db_session, _make_payload(tenant.id, insurer.id))

        deleted = delete_employee(db_session, created.id)

        assert deleted is True
        assert get_employee(db_session, created.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_employee(db_session, uuid4())
        assert result is False
