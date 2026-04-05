"""Tests for EmployeeChild service layer."""

from datetime import date
from uuid import uuid4

from app.models.employee import Employee
from app.models.employee_child import EmployeeChild
from app.models.health_insurer import HealthInsurer
from app.models.tenant import Tenant
from app.schemas.employee_child import EmployeeChildCreate, EmployeeChildUpdate
from app.services.employee_child import (
    count_employee_children,
    create_employee_child,
    delete_employee_child,
    get_employee_child,
    list_employee_children,
    update_employee_child,
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


def _make_child_payload(tenant_id, employee_id, **overrides) -> EmployeeChildCreate:
    """Build a valid EmployeeChildCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "first_name": "Anna",
        "last_name": "Nováková",
        "birth_date": date(2015, 3, 20),
        "birth_number": "1503200001",
        "is_tax_bonus_eligible": True,
        "custody_from": None,
        "custody_to": None,
    }
    defaults.update(overrides)
    return EmployeeChildCreate(**defaults)


def _setup_prerequisites(db_session):
    """Create tenant, insurer and employee; return (tenant, employee)."""
    tenant = _make_tenant(db_session)
    insurer = _make_health_insurer(db_session)
    employee = _make_employee(db_session, tenant.id, insurer.id)
    return tenant, employee


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateEmployeeChild:
    """Tests for create_employee_child."""

    def test_create_returns_model_instance(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_child_payload(tenant.id, employee.id)

        result = create_employee_child(db_session, payload)

        assert isinstance(result, EmployeeChild)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.employee_id == employee.id
        assert result.first_name == "Anna"
        assert result.last_name == "Nováková"
        assert result.birth_date == date(2015, 3, 20)
        assert result.is_tax_bonus_eligible is True
        assert result.custody_from is None
        assert result.custody_to is None

    def test_create_with_custody_dates(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_child_payload(
            tenant.id,
            employee.id,
            custody_from=date(2020, 1, 1),
            custody_to=date(2025, 12, 31),
        )

        result = create_employee_child(db_session, payload)

        assert result.custody_from == date(2020, 1, 1)
        assert result.custody_to == date(2025, 12, 31)

    def test_create_not_eligible_for_tax_bonus(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_child_payload(
            tenant.id,
            employee.id,
            is_tax_bonus_eligible=False,
        )

        result = create_employee_child(db_session, payload)

        assert result.is_tax_bonus_eligible is False

    def test_create_multiple_children_for_same_employee(self, db_session):
        """An employee can have multiple children."""
        tenant, employee = _setup_prerequisites(db_session)

        child_a = create_employee_child(
            db_session,
            _make_child_payload(tenant.id, employee.id, first_name="Anna"),
        )
        child_b = create_employee_child(
            db_session,
            _make_child_payload(
                tenant.id,
                employee.id,
                first_name="Martin",
                last_name="Novák",
                birth_date=date(2018, 7, 10),
            ),
        )

        assert child_a.id != child_b.id
        assert child_a.employee_id == child_b.employee_id

    def test_create_without_birth_number(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_child_payload(
            tenant.id,
            employee.id,
            birth_number=None,
        )

        result = create_employee_child(db_session, payload)

        assert result.birth_number is None


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetEmployeeChild:
    """Tests for get_employee_child."""

    def test_get_existing(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_employee_child(db_session, _make_child_payload(tenant.id, employee.id))

        fetched = get_employee_child(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.first_name == created.first_name

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_employee_child(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListEmployeeChildren:
    """Tests for list_employee_children."""

    def test_list_empty(self, db_session):
        result = list_employee_children(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        create_employee_child(
            db_session,
            _make_child_payload(tenant.id, employee.id, first_name="Anna"),
        )
        create_employee_child(
            db_session,
            _make_child_payload(
                tenant.id,
                employee.id,
                first_name="Martin",
                last_name="Novák",
                birth_date=date(2018, 7, 10),
            ),
        )

        result = list_employee_children(db_session)
        assert len(result) == 2

    def test_list_ordering_by_last_name_first_name(self, db_session):
        """Children are ordered by last_name, first_name."""
        tenant, employee = _setup_prerequisites(db_session)

        create_employee_child(
            db_session,
            _make_child_payload(tenant.id, employee.id, first_name="Zuzana", last_name="Nováková"),
        )
        create_employee_child(
            db_session,
            _make_child_payload(tenant.id, employee.id, first_name="Adam", last_name="Novák"),
        )

        result = list_employee_children(db_session)
        assert result[0].last_name == "Novák"
        assert result[1].last_name == "Nováková"

    def test_list_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant_a.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant_b.id, insurer.id, employee_number="EMP002")

        create_employee_child(db_session, _make_child_payload(tenant_a.id, emp_a.id, first_name="Anna"))
        create_employee_child(db_session, _make_child_payload(tenant_b.id, emp_b.id, first_name="Eva"))

        result = list_employee_children(db_session, tenant_id=tenant_a.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id

    def test_list_scoped_by_employee(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP002")

        create_employee_child(db_session, _make_child_payload(tenant.id, emp_a.id, first_name="Anna"))
        create_employee_child(db_session, _make_child_payload(tenant.id, emp_b.id, first_name="Eva"))

        result = list_employee_children(db_session, employee_id=emp_a.id)
        assert len(result) == 1
        assert result[0].employee_id == emp_a.id

    def test_list_pagination_skip(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for i in range(3):
            create_employee_child(
                db_session,
                _make_child_payload(
                    tenant.id,
                    employee.id,
                    first_name=f"Child{i}",
                    birth_date=date(2015 + i, 1, 1),
                ),
            )

        result = list_employee_children(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for i in range(3):
            create_employee_child(
                db_session,
                _make_child_payload(
                    tenant.id,
                    employee.id,
                    first_name=f"Child{i}",
                    birth_date=date(2015 + i, 1, 1),
                ),
            )

        result = list_employee_children(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for i in range(5):
            create_employee_child(
                db_session,
                _make_child_payload(
                    tenant.id,
                    employee.id,
                    first_name=f"Child{i}",
                    birth_date=date(2015 + i, 1, 1),
                ),
            )

        result = list_employee_children(db_session, skip=1, limit=2)
        assert len(result) == 2

    def test_list_default_limit_is_50(self, db_session):
        """Default limit should be 50 per project convention."""
        import inspect

        sig = inspect.signature(list_employee_children)
        assert sig.parameters["limit"].default == 50


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCountEmployeeChildren:
    """Tests for count_employee_children."""

    def test_count_empty(self, db_session):
        result = count_employee_children(db_session)
        assert result == 0

    def test_count_all(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        for i in range(3):
            create_employee_child(
                db_session,
                _make_child_payload(
                    tenant.id,
                    employee.id,
                    first_name=f"Child{i}",
                    birth_date=date(2015 + i, 1, 1),
                ),
            )

        result = count_employee_children(db_session)
        assert result == 3

    def test_count_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant_a.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant_b.id, insurer.id, employee_number="EMP002")

        create_employee_child(db_session, _make_child_payload(tenant_a.id, emp_a.id, first_name="Anna"))
        create_employee_child(db_session, _make_child_payload(tenant_b.id, emp_b.id, first_name="Eva"))

        assert count_employee_children(db_session, tenant_id=tenant_a.id) == 1
        assert count_employee_children(db_session, tenant_id=tenant_b.id) == 1

    def test_count_scoped_by_employee(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP002")

        create_employee_child(db_session, _make_child_payload(tenant.id, emp_a.id, first_name="Anna"))
        create_employee_child(db_session, _make_child_payload(tenant.id, emp_b.id, first_name="Eva"))
        create_employee_child(
            db_session,
            _make_child_payload(tenant.id, emp_a.id, first_name="Martin", birth_date=date(2018, 7, 10)),
        )

        assert count_employee_children(db_session, employee_id=emp_a.id) == 2
        assert count_employee_children(db_session, employee_id=emp_b.id) == 1


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateEmployeeChild:
    """Tests for update_employee_child."""

    def test_update_single_field(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_employee_child(db_session, _make_child_payload(tenant.id, employee.id))

        updated = update_employee_child(
            db_session,
            created.id,
            EmployeeChildUpdate(first_name="Zuzana"),
        )

        assert updated is not None
        assert updated.first_name == "Zuzana"
        # unchanged fields stay the same
        assert updated.last_name == "Nováková"

    def test_update_multiple_fields(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_employee_child(db_session, _make_child_payload(tenant.id, employee.id))

        updated = update_employee_child(
            db_session,
            created.id,
            EmployeeChildUpdate(
                first_name="Eva",
                is_tax_bonus_eligible=False,
                custody_from=date(2020, 6, 1),
            ),
        )

        assert updated is not None
        assert updated.first_name == "Eva"
        assert updated.is_tax_bonus_eligible is False
        assert updated.custody_from == date(2020, 6, 1)

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_employee_child(
            db_session,
            uuid4(),
            EmployeeChildUpdate(first_name="Ghost"),
        )
        assert result is None

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        tenant, employee = _setup_prerequisites(db_session)
        created = create_employee_child(db_session, _make_child_payload(tenant.id, employee.id))

        updated = update_employee_child(
            db_session,
            created.id,
            EmployeeChildUpdate(),
        )

        assert updated is not None
        assert updated.first_name == created.first_name

    def test_update_custody_to(self, db_session):
        """Update custody end date."""
        tenant, employee = _setup_prerequisites(db_session)
        created = create_employee_child(
            db_session,
            _make_child_payload(tenant.id, employee.id, custody_from=date(2015, 3, 20)),
        )

        updated = update_employee_child(
            db_session,
            created.id,
            EmployeeChildUpdate(custody_to=date(2030, 12, 31)),
        )

        assert updated is not None
        assert updated.custody_to == date(2030, 12, 31)
        # custody_from unchanged
        assert updated.custody_from == date(2015, 3, 20)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteEmployeeChild:
    """Tests for delete_employee_child."""

    def test_delete_existing(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_employee_child(db_session, _make_child_payload(tenant.id, employee.id))

        deleted = delete_employee_child(db_session, created.id)

        assert deleted is True
        assert get_employee_child(db_session, created.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_employee_child(db_session, uuid4())
        assert result is False
