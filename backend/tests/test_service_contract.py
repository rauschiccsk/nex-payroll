"""Tests for Contract service layer."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.tenant import Tenant
from app.schemas.contract import ContractCreate, ContractUpdate
from app.services.contract import (
    create_contract,
    delete_contract,
    get_contract,
    list_contracts,
    update_contract,
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


def _make_payload(tenant_id, employee_id, **overrides) -> ContractCreate:
    """Build a valid ContractCreate with sensible defaults."""
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "contract_number": "PZ-2024-001",
        "contract_type": "permanent",
        "job_title": "Softvérový inžinier",
        "wage_type": "monthly",
        "base_wage": Decimal("2500.00"),
        "hours_per_week": Decimal("40.0"),
        "start_date": date(2024, 1, 15),
        "end_date": None,
        "probation_end_date": date(2024, 4, 15),
        "termination_date": None,
        "termination_reason": None,
        "is_current": True,
    }
    defaults.update(overrides)
    return ContractCreate(**defaults)


def _setup_prerequisites(db_session):
    """Create tenant, insurer and employee; return (tenant, employee)."""
    tenant = _make_tenant(db_session)
    insurer = _make_health_insurer(db_session)
    employee = _make_employee(db_session, tenant.id, insurer.id)
    return tenant, employee


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreateContract:
    """Tests for create_contract."""

    def test_create_returns_model_instance(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_payload(tenant.id, employee.id)

        result = create_contract(db_session, payload)

        assert isinstance(result, Contract)
        assert result.id is not None
        assert result.tenant_id == tenant.id
        assert result.employee_id == employee.id
        assert result.contract_number == "PZ-2024-001"
        assert result.contract_type == "permanent"
        assert result.job_title == "Softvérový inžinier"
        assert result.wage_type == "monthly"
        assert result.base_wage == Decimal("2500.00")
        assert result.hours_per_week == Decimal("40.0")
        assert result.start_date == date(2024, 1, 15)
        assert result.end_date is None
        assert result.probation_end_date == date(2024, 4, 15)
        assert result.termination_date is None
        assert result.termination_reason is None
        assert result.is_current is True

    def test_create_fixed_term_contract(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        payload = _make_payload(
            tenant.id,
            employee.id,
            contract_type="fixed_term",
            end_date=date(2025, 12, 31),
        )

        result = create_contract(db_session, payload)

        assert result.contract_type == "fixed_term"
        assert result.end_date == date(2025, 12, 31)

    def test_create_duplicate_contract_number_raises(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        create_contract(
            db_session,
            _make_payload(tenant.id, employee.id, contract_number="DUP001"),
        )

        with pytest.raises(ValueError, match="contract_number='DUP001' already exists"):
            create_contract(
                db_session,
                _make_payload(tenant.id, employee.id, contract_number="DUP001"),
            )

    def test_create_same_number_different_tenant_ok(self, db_session):
        """Same contract_number in different tenants is allowed."""
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant_a.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant_b.id, insurer.id, employee_number="EMP002")

        c_a = create_contract(
            db_session,
            _make_payload(tenant_a.id, emp_a.id, contract_number="PZ-001"),
        )
        c_b = create_contract(
            db_session,
            _make_payload(tenant_b.id, emp_b.id, contract_number="PZ-001"),
        )

        assert c_a.id != c_b.id
        assert c_a.contract_number == c_b.contract_number


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetContract:
    """Tests for get_contract."""

    def test_get_existing(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_contract(db_session, _make_payload(tenant.id, employee.id))

        fetched = get_contract(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.contract_number == created.contract_number

    def test_get_nonexistent_returns_none(self, db_session):
        result = get_contract(db_session, uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListContracts:
    """Tests for list_contracts."""

    def test_list_empty(self, db_session):
        result = list_contracts(db_session)
        assert result == []

    def test_list_returns_all(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        create_contract(
            db_session,
            _make_payload(tenant.id, employee.id, contract_number="PZ-001"),
        )
        create_contract(
            db_session,
            _make_payload(
                tenant.id,
                employee.id,
                contract_number="PZ-002",
                start_date=date(2023, 1, 1),
                is_current=False,
            ),
        )

        result = list_contracts(db_session)
        assert len(result) == 2

    def test_list_ordering_by_start_date_desc(self, db_session):
        """Contracts are ordered by start_date descending (newest first)."""
        tenant, employee = _setup_prerequisites(db_session)

        create_contract(
            db_session,
            _make_payload(
                tenant.id,
                employee.id,
                contract_number="PZ-OLD",
                start_date=date(2023, 1, 1),
                is_current=False,
            ),
        )
        create_contract(
            db_session,
            _make_payload(
                tenant.id,
                employee.id,
                contract_number="PZ-NEW",
                start_date=date(2024, 6, 1),
            ),
        )

        result = list_contracts(db_session)
        assert result[0].contract_number == "PZ-NEW"
        assert result[1].contract_number == "PZ-OLD"

    def test_list_scoped_by_tenant(self, db_session):
        tenant_a = _make_tenant(db_session, ico="11111111", schema_name="tenant_a_11111111")
        tenant_b = _make_tenant(db_session, ico="22222222", schema_name="tenant_b_22222222")
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant_a.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant_b.id, insurer.id, employee_number="EMP002")

        create_contract(
            db_session,
            _make_payload(tenant_a.id, emp_a.id, contract_number="PZ-A"),
        )
        create_contract(
            db_session,
            _make_payload(tenant_b.id, emp_b.id, contract_number="PZ-B"),
        )

        result = list_contracts(db_session, tenant_id=tenant_a.id)
        assert len(result) == 1
        assert result[0].tenant_id == tenant_a.id

    def test_list_scoped_by_employee(self, db_session):
        tenant = _make_tenant(db_session)
        insurer = _make_health_insurer(db_session)
        emp_a = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP001")
        emp_b = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP002")

        create_contract(
            db_session,
            _make_payload(tenant.id, emp_a.id, contract_number="PZ-A"),
        )
        create_contract(
            db_session,
            _make_payload(tenant.id, emp_b.id, contract_number="PZ-B"),
        )

        result = list_contracts(db_session, employee_id=emp_a.id)
        assert len(result) == 1
        assert result[0].employee_id == emp_a.id

    def test_list_pagination_skip(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for i in range(3):
            create_contract(
                db_session,
                _make_payload(
                    tenant.id,
                    employee.id,
                    contract_number=f"PZ-{i:03d}",
                    start_date=date(2024, i + 1, 1),
                    is_current=(i == 2),
                ),
            )

        result = list_contracts(db_session, skip=1)
        assert len(result) == 2

    def test_list_pagination_limit(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for i in range(3):
            create_contract(
                db_session,
                _make_payload(
                    tenant.id,
                    employee.id,
                    contract_number=f"PZ-{i:03d}",
                    start_date=date(2024, i + 1, 1),
                    is_current=(i == 2),
                ),
            )

        result = list_contracts(db_session, limit=2)
        assert len(result) == 2

    def test_list_pagination_skip_and_limit(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)

        for i in range(5):
            create_contract(
                db_session,
                _make_payload(
                    tenant.id,
                    employee.id,
                    contract_number=f"PZ-{i:03d}",
                    start_date=date(2024, i + 1, 1),
                    is_current=(i == 4),
                ),
            )

        result = list_contracts(db_session, skip=1, limit=2)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdateContract:
    """Tests for update_contract."""

    def test_update_single_field(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_contract(db_session, _make_payload(tenant.id, employee.id))

        updated = update_contract(
            db_session,
            created.id,
            ContractUpdate(job_title="Senior inžinier"),
        )

        assert updated is not None
        assert updated.job_title == "Senior inžinier"
        # unchanged fields stay the same
        assert updated.contract_type == "permanent"

    def test_update_multiple_fields(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_contract(db_session, _make_payload(tenant.id, employee.id))

        updated = update_contract(
            db_session,
            created.id,
            ContractUpdate(
                base_wage=Decimal("3000.00"),
                hours_per_week=Decimal("37.5"),
                is_current=False,
            ),
        )

        assert updated is not None
        assert updated.base_wage == Decimal("3000.00")
        assert updated.hours_per_week == Decimal("37.5")
        assert updated.is_current is False

    def test_update_nonexistent_returns_none(self, db_session):
        result = update_contract(
            db_session,
            uuid4(),
            ContractUpdate(job_title="Ghost"),
        )
        assert result is None

    def test_update_no_fields_is_noop(self, db_session):
        """Sending an empty update should not break anything."""
        tenant, employee = _setup_prerequisites(db_session)
        created = create_contract(db_session, _make_payload(tenant.id, employee.id))

        updated = update_contract(
            db_session,
            created.id,
            ContractUpdate(),
        )

        assert updated is not None
        assert updated.job_title == created.job_title

    def test_update_termination(self, db_session):
        """Update contract with termination fields."""
        tenant, employee = _setup_prerequisites(db_session)
        created = create_contract(db_session, _make_payload(tenant.id, employee.id))

        updated = update_contract(
            db_session,
            created.id,
            ContractUpdate(
                termination_date=date(2025, 3, 31),
                termination_reason="Výpoveď dohodou",
                is_current=False,
            ),
        )

        assert updated is not None
        assert updated.termination_date == date(2025, 3, 31)
        assert updated.termination_reason == "Výpoveď dohodou"
        assert updated.is_current is False


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDeleteContract:
    """Tests for delete_contract."""

    def test_delete_existing(self, db_session):
        tenant, employee = _setup_prerequisites(db_session)
        created = create_contract(db_session, _make_payload(tenant.id, employee.id))

        deleted = delete_contract(db_session, created.id)

        assert deleted is True
        assert get_contract(db_session, created.id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        result = delete_contract(db_session, uuid4())
        assert result is False
