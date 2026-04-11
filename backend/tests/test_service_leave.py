"""Tests for Leave service layer."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.leave import Leave
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.leave import LeaveCreate, LeaveUpdate
from app.services.leave import (
    count_leaves,
    create_leave,
    delete_leave,
    get_leave,
    list_leaves,
    update_leave,
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


def _make_user(db_session, tenant_id, **overrides) -> User:
    """Insert a minimal User and flush; return the instance."""
    defaults = {
        "tenant_id": tenant_id,
        "username": "approver",
        "email": "approver@test.sk",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        "role": "director",
    }
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.flush()
    return user


def _make_leave_payload(tenant_id, employee_id, **overrides) -> LeaveCreate:
    """Build a valid LeaveCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "leave_type": "annual",
        "start_date": date(2025, 7, 1),
        "end_date": date(2025, 7, 14),
        "business_days": 10,
        "note": None,
    }
    defaults.update(overrides)
    return LeaveCreate(**defaults)


def _setup_prerequisites(db_session):
    """Create tenant, insurer and employee; return (tenant, employee)."""
    tenant = _make_tenant(db_session)
    insurer = _make_health_insurer(db_session)
    employee = _make_employee(db_session, tenant.id, insurer.id)
    return tenant, employee


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateLeave:
    """Tests for create_leave."""

    def test_create_returns_model_instance(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_leave_payload(tenant.id, employee.id)

        result = create_leave(db_session, payload)

        assert isinstance(result, Leave)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.employee_id == employee.id
        assert result.leave_type == "annual"
        assert result.start_date == date(2025, 7, 1)
        assert result.end_date == date(2025, 7, 14)
        assert result.business_days == 10
        assert result.status == "pending"

    def test_create_with_note(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_leave_payload(
            tenant.id,
            employee.id,
            note="Rodinná dovolenka",
        )

        result = create_leave(db_session, payload)

        assert result.note == "Rodinná dovolenka"

    def test_create_defaults_to_pending_status(self, db_session):
        """New leave always starts as 'pending' — status is not settable at creation."""
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_leave_payload(tenant.id, employee.id)

        result = create_leave(db_session, payload)

        assert result.status == "pending"
        assert result.approved_by is None
        assert result.approved_at is None

    def test_create_with_invalid_tenant_raises_value_error(self, db_session):
        """create_leave must reject a non-existent tenant_id."""
        _setup_prerequisites(db_session)  # need employee FK to exist
        payload = _make_leave_payload(uuid4(), uuid4())

        with pytest.raises(ValueError, match="not found"):
            create_leave(db_session, payload)

    def test_create_with_invalid_employee_raises_value_error(self, db_session):
        """create_leave must reject a non-existent employee_id."""
        tenant, _employee = _setup_prerequisites(db_session)
        payload = _make_leave_payload(tenant.id, uuid4())

        with pytest.raises(ValueError, match="not found"):
            create_leave(db_session, payload)

    def test_create_sick_leave_type(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_leave_payload(
            tenant.id,
            employee.id,
            leave_type="sick_employer",
            start_date=date(2025, 3, 10),
            end_date=date(2025, 3, 14),
            business_days=5,
        )

        result = create_leave(db_session, payload)

        assert result.leave_type == "sick_employer"
        assert result.business_days == 5

    def test_create_multiple_leaves_same_employee(self, db_session):
        """An employee can have multiple leave records."""
        tenant, employee = _setup_prerequisites(db_session)

        leave_a = create_leave(
            db_session,
            _make_leave_payload(
                tenant.id,
                employee.id,
                start_date=date(2025, 7, 1),
                end_date=date(2025, 7, 14),
            ),
        )
        leave_b = create_leave(
            db_session,
            _make_leave_payload(
                tenant.id,
                employee.id,
                start_date=date(2025, 8, 1),
                end_date=date(2025, 8, 14),
            ),
        )

        assert leave_a.id != leave_b.id
        assert leave_a.employee_id == leave_b.employee_id


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetLeave:
    """Tests for get_leave."""

    def test_get_existing(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave(db_session, _make_leave_payload(tenant.id, employee.id))

        fetched = get_leave(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.leave_type == created.leave_type

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_leave(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListLeaves:
    """Tests for list_leaves."""

    def test_list_empty(self, db_session):
        result = list_leaves(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        create_leave(
            db_session,
            _make_leave_payload(tenant.id, employee.id, start_date=date(2025, 7, 1), end_date=date(2025, 7, 14)),
        )
        create_leave(
            db_session,
            _make_leave_payload(tenant.id, employee.id, start_date=date(2025, 8, 1), end_date=date(2025, 8, 14)),
        )

        result = list_leaves(db_session)
        assert len(result) == 2

    def test_list_ordering_by_start_date_desc(self, db_session):
        """Leaves are ordered by start_date descending."""
        tenant, employee = _setup_prerequisites(db_session)

        create_leave(
            db_session,
            _make_leave_payload(tenant.id, employee.id, start_date=date(2025, 3, 1), end_date=date(2025, 3, 5)),
        )
        create_leave(
            db_session,
            _make_leave_payload(tenant.id, employee.id, start_date=date(2025, 9, 1), end_date=date(2025, 9, 5)),
        )
        create_leave(
            db_session,
            _make_leave_payload(tenant.id, employee.id, start_date=date(2025, 6, 1), end_date=date(2025, 6, 5)),
        )

        result = list_leaves(db_session)
        assert result[0].start_date == date(2025, 9, 1)
        assert result[1].start_date == date(2025, 6, 1)
        assert result[2].start_date == date(2025, 3, 1)

    def test_list_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant_a.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant_b.id, insurer.id, employee_number="EMP002")

        create_leave(db_session, _make_leave_payload(tenant_a.id, emp_a.id))
        create_leave(db_session, _make_leave_payload(tenant_b.id, emp_b.id))

        result = list_leaves(db_session, tenant_id=tenant_a.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id

    def test_list_scoped_by_employee(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP002")

        create_leave(db_session, _make_leave_payload(tenant.id, emp_a.id))
        create_leave(db_session, _make_leave_payload(tenant.id, emp_b.id))

        result = list_leaves(db_session, employee_id=emp_a.id)
        assert len(result) == 1
        assert result[0].employee_id == emp_a.id

    def test_list_scoped_by_status(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        create_leave(
            db_session,
            _make_leave_payload(
                tenant.id,
                employee.id,
                start_date=date(2025, 7, 1),
                end_date=date(2025, 7, 14),
            ),
        )
        approved_leave = create_leave(
            db_session,
            _make_leave_payload(
                tenant.id,
                employee.id,
                start_date=date(2025, 8, 1),
                end_date=date(2025, 8, 14),
            ),
        )
        update_leave(db_session, approved_leave.id, LeaveUpdate(status="approved"))

        result = list_leaves(db_session, status="pending")
        assert len(result) == 1
        assert result[0].status == "pending"

    def test_list_pagination_skip(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for month in range(1, 4):
            create_leave(
                db_session,
                _make_leave_payload(
                    tenant.id,
                    employee.id,
                    start_date=date(2025, month, 1),
                    end_date=date(2025, month, 5),
                ),
            )

        result = list_leaves(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for month in range(1, 4):
            create_leave(
                db_session,
                _make_leave_payload(
                    tenant.id,
                    employee.id,
                    start_date=date(2025, month, 1),
                    end_date=date(2025, month, 5),
                ),
            )

        result = list_leaves(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for month in range(1, 7):
            create_leave(
                db_session,
                _make_leave_payload(
                    tenant.id,
                    employee.id,
                    start_date=date(2025, month, 1),
                    end_date=date(2025, month, 5),
                ),
            )

        result = list_leaves(db_session, skip=1, limit=2)
        assert len(result) == 2

    def test_list_default_limit_is_50(self, db_session):
        """Default limit should be 50 per project convention."""
        import inspect

        sig = inspect.signature(list_leaves)
        assert sig.parameters["limit"].default == 50


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountLeaves:
    """Tests for count_leaves."""

    def test_count_empty(self, db_session):
        result = count_leaves(db_session)
        assert result == 0

    def test_count_all(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        for month in range(1, 4):
            create_leave(
                db_session,
                _make_leave_payload(
                    tenant.id,
                    employee.id,
                    start_date=date(2025, month, 1),
                    end_date=date(2025, month, 5),
                ),
            )

        result = count_leaves(db_session)
        assert result == 3

    def test_count_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant_a.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant_b.id, insurer.id, employee_number="EMP002")

        create_leave(db_session, _make_leave_payload(tenant_a.id, emp_a.id))
        create_leave(db_session, _make_leave_payload(tenant_b.id, emp_b.id))

        assert count_leaves(db_session, tenant_id=tenant_a.id) == 1
        assert count_leaves(db_session, tenant_id=tenant_b.id) == 1

    def test_count_scoped_by_employee(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP002")

        create_leave(
            db_session,
            _make_leave_payload(tenant.id, emp_a.id, start_date=date(2025, 7, 1), end_date=date(2025, 7, 14)),
        )
        create_leave(
            db_session,
            _make_leave_payload(tenant.id, emp_a.id, start_date=date(2025, 8, 1), end_date=date(2025, 8, 14)),
        )
        create_leave(db_session, _make_leave_payload(tenant.id, emp_b.id))

        assert count_leaves(db_session, employee_id=emp_a.id) == 2
        assert count_leaves(db_session, employee_id=emp_b.id) == 1

    def test_count_scoped_by_status(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        create_leave(
            db_session,
            _make_leave_payload(tenant.id, employee.id, start_date=date(2025, 7, 1), end_date=date(2025, 7, 14)),
        )
        approved_leave = create_leave(
            db_session,
            _make_leave_payload(tenant.id, employee.id, start_date=date(2025, 8, 1), end_date=date(2025, 8, 14)),
        )
        update_leave(db_session, approved_leave.id, LeaveUpdate(status="approved"))

        assert count_leaves(db_session, status="pending") == 1
        assert count_leaves(db_session, status="approved") == 1


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateLeave:
    """Tests for update_leave."""

    def test_update_single_field(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave(db_session, _make_leave_payload(tenant.id, employee.id))

        updated = update_leave(
            db_session,
            created.id,
            LeaveUpdate(status="approved"),
        )

        assert updated is not None
        assert updated.status == "approved"
        # unchanged fields stay the same
        assert updated.leave_type == "annual"

    def test_update_multiple_fields(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        approver = _make_user(db_session, tenant.id)
        created = create_leave(db_session, _make_leave_payload(tenant.id, employee.id))
        now = datetime(2025, 7, 5, 14, 30, 0, tzinfo=UTC)

        updated = update_leave(
            db_session,
            created.id,
            LeaveUpdate(
                status="approved",
                approved_by=approver.id,
                approved_at=now,
            ),
        )

        assert updated is not None
        assert updated.status == "approved"
        assert updated.approved_by == approver.id
        assert updated.approved_at == now

    def test_update_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            update_leave(
                db_session,
                uuid4(),
                LeaveUpdate(status="approved"),
            )

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave(db_session, _make_leave_payload(tenant.id, employee.id))

        updated = update_leave(
            db_session,
            created.id,
            LeaveUpdate(),
        )

        assert updated is not None
        assert updated.leave_type == created.leave_type
        assert updated.status == created.status

    def test_update_note(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave(db_session, _make_leave_payload(tenant.id, employee.id))

        updated = update_leave(
            db_session,
            created.id,
            LeaveUpdate(note="Zmenená poznámka"),
        )

        assert updated is not None
        assert updated.note == "Zmenená poznámka"

    def test_update_dates(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave(db_session, _make_leave_payload(tenant.id, employee.id))

        updated = update_leave(
            db_session,
            created.id,
            LeaveUpdate(
                start_date=date(2025, 7, 7),
                end_date=date(2025, 7, 18),
                business_days=8,
            ),
        )

        assert updated is not None
        assert updated.start_date == date(2025, 7, 7)
        assert updated.end_date == date(2025, 7, 18)
        assert updated.business_days == 8


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteLeave:
    """Tests for delete_leave."""

    def test_delete_existing(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_leave(db_session, _make_leave_payload(tenant.id, employee.id))

        deleted = delete_leave(db_session, created.id)

        assert deleted is True
        assert get_leave(db_session, created.id) is None

    def test_delete_nonexistent_raises_value_error(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            delete_leave(db_session, uuid4())


# ---------------------------------------------------------------------------
# FK RESTRICT enforcement (raw SQL — per Model Generation Checklist #16)
# ---------------------------------------------------------------------------


class TestFKRestrictLeave:
    """Verify that RESTRICT foreign keys prevent parent deletion when leaves exist.

    Uses raw SQL ``text("DELETE FROM ...")`` pattern — ORM ``session.delete()``
    would set FK to NULL (failing NOT NULL before FK check) which is a
    different error path.
    """

    def test_cannot_delete_tenant_with_leave(self, db_session):
        """FK tenant_id RESTRICT: deleting tenant must fail while leaves reference it."""
        tenant, employee = _setup_prerequisites(db_session)
        create_leave(db_session, _make_leave_payload(tenant.id, employee.id))

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM public.tenants WHERE id = :id"),
                {"id": str(tenant.id)},
            )
            db_session.flush()

    def test_cannot_delete_employee_with_leave(self, db_session):
        """FK employee_id RESTRICT: deleting employee must fail while leaves reference it."""
        tenant, employee = _setup_prerequisites(db_session)
        create_leave(db_session, _make_leave_payload(tenant.id, employee.id))

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM employees WHERE id = :id"),
                {"id": str(employee.id)},
            )
            db_session.flush()

    def test_cannot_delete_approver_user_with_leave(self, db_session):
        """FK approved_by RESTRICT: deleting approver user must fail while leaves reference it."""
        tenant, employee = _setup_prerequisites(db_session)
        approver = _make_user(db_session, tenant.id)
        leave = create_leave(db_session, _make_leave_payload(tenant.id, employee.id))
        # Set approved_by via update
        update_leave(db_session, leave.id, LeaveUpdate(approved_by=approver.id))

        with pytest.raises((IntegrityError, ProgrammingError)):
            db_session.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": str(approver.id)},
            )
            db_session.flush()
