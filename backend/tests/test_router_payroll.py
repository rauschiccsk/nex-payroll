"""Tests for Payroll router endpoints.

Verifies:
- GET /api/v1/payroll (list with pagination and filters)
- GET /api/v1/payroll/{payroll_id} (single payroll)
- POST /api/v1/payroll (create)
- PATCH /api/v1/payroll/{payroll_id} (partial update)
- DELETE /api/v1/payroll/{payroll_id} (delete)
- Error handling: 404, 409, 422
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.payroll import Payroll
from app.models.tenant import Tenant

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAYROLL_AMOUNTS = {
    "base_wage": Decimal("2500.00"),
    "overtime_hours": Decimal("0"),
    "overtime_amount": Decimal("0"),
    "bonus_amount": Decimal("0"),
    "supplement_amount": Decimal("0"),
    "gross_wage": Decimal("2500.00"),
    "sp_assessment_base": Decimal("2500.00"),
    "sp_nemocenske": Decimal("35.00"),
    "sp_starobne": Decimal("100.00"),
    "sp_invalidne": Decimal("75.00"),
    "sp_nezamestnanost": Decimal("25.00"),
    "sp_employee_total": Decimal("235.00"),
    "zp_assessment_base": Decimal("2500.00"),
    "zp_employee": Decimal("100.00"),
    "partial_tax_base": Decimal("2165.00"),
    "nczd_applied": Decimal("457.89"),
    "tax_base": Decimal("1707.11"),
    "tax_advance": Decimal("323.35"),
    "child_bonus": Decimal("0"),
    "tax_after_bonus": Decimal("323.35"),
    "net_wage": Decimal("1841.65"),
    "sp_employer_nemocenske": Decimal("35.00"),
    "sp_employer_starobne": Decimal("350.00"),
    "sp_employer_invalidne": Decimal("75.00"),
    "sp_employer_nezamestnanost": Decimal("25.00"),
    "sp_employer_garancne": Decimal("6.25"),
    "sp_employer_rezervny": Decimal("119.25"),
    "sp_employer_kurzarbeit": Decimal("15.00"),
    "sp_employer_urazove": Decimal("20.00"),
    "sp_employer_total": Decimal("645.50"),
    "zp_employer": Decimal("250.00"),
    "total_employer_cost": Decimal("3395.50"),
    "pillar2_amount": Decimal("0"),
}


def _make_tenant(db_session, **overrides) -> Tenant:
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
    t = Tenant(**defaults)
    db_session.add(t)
    db_session.flush()
    return t


def _make_health_insurer(db_session, **overrides) -> HealthInsurer:
    defaults = {
        "code": "25",
        "name": "VšZP",
        "iban": "SK0000000000000000000025",
    }
    defaults.update(overrides)
    hi = HealthInsurer(**defaults)
    db_session.add(hi)
    db_session.flush()
    return hi


def _make_employee(db_session, tenant_id, health_insurer_id, **overrides) -> Employee:
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
    emp = Employee(**defaults)
    db_session.add(emp)
    db_session.flush()
    return emp


def _make_contract(db_session, tenant_id, employee_id, **overrides) -> Contract:
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
    }
    defaults.update(overrides)
    c = Contract(**defaults)
    db_session.add(c)
    db_session.flush()
    return c


def _make_payroll(db_session, tenant_id, employee_id, contract_id, **overrides) -> Payroll:
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "contract_id": contract_id,
        "period_year": 2024,
        "period_month": 1,
        "status": "draft",
        **_PAYROLL_AMOUNTS,
    }
    defaults.update(overrides)
    p = Payroll(**defaults)
    db_session.add(p)
    db_session.flush()
    return p


@pytest.fixture()
def prerequisites(db_session):
    """Create tenant, insurer, employee, and contract; return tuple."""
    tenant = _make_tenant(db_session)
    insurer = _make_health_insurer(db_session)
    employee = _make_employee(db_session, tenant.id, insurer.id)
    contract = _make_contract(db_session, tenant.id, employee.id)
    return tenant, insurer, employee, contract


def _payroll_payload(tenant_id, employee_id, contract_id, **overrides) -> dict:
    """Build a valid payroll creation JSON payload."""
    amounts_str = {k: str(v) for k, v in _PAYROLL_AMOUNTS.items()}
    defaults = {
        "tenant_id": str(tenant_id),
        "employee_id": str(employee_id),
        "contract_id": str(contract_id),
        "period_year": 2024,
        "period_month": 1,
        "status": "draft",
        **amounts_str,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# GET /api/v1/payroll — list with pagination
# ---------------------------------------------------------------------------


class TestListPayrolls:
    """Tests for the list endpoint."""

    def test_list_empty(self, client):
        resp = client.get("/api/v1/payroll")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_payrolls(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        _make_payroll(db_session, tenant.id, employee.id, contract.id, period_month=1)
        _make_payroll(db_session, tenant.id, employee.id, contract.id, period_month=2)

        resp = client.get("/api/v1/payroll")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_pagination(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        for m in range(1, 6):
            _make_payroll(db_session, tenant.id, employee.id, contract.id, period_month=m)

        resp = client.get("/api/v1/payroll?skip=2&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["skip"] == 2
        assert data["limit"] == 2

    def test_list_limit_max_100(self, client):
        resp = client.get("/api/v1/payroll?limit=200")
        assert resp.status_code == 422

    def test_list_filter_by_tenant_id(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        _make_payroll(db_session, tenant.id, employee.id, contract.id)

        resp = client.get(f"/api/v1/payroll?tenant_id={tenant.id}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp2 = client.get(f"/api/v1/payroll?tenant_id={uuid4()}")
        assert resp2.json()["total"] == 0

    def test_list_filter_by_employee_id(self, client, db_session, prerequisites):
        tenant, insurer, employee, contract = prerequisites
        _make_payroll(db_session, tenant.id, employee.id, contract.id)

        resp = client.get(f"/api/v1/payroll?employee_id={employee.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["employee_id"] == str(employee.id)

    def test_list_filter_by_status(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        _make_payroll(
            db_session,
            tenant.id,
            employee.id,
            contract.id,
            period_month=1,
            status="draft",
        )
        _make_payroll(
            db_session,
            tenant.id,
            employee.id,
            contract.id,
            period_month=2,
            status="approved",
        )

        resp = client.get("/api/v1/payroll?status=draft")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_filter_by_period(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        _make_payroll(
            db_session,
            tenant.id,
            employee.id,
            contract.id,
            period_year=2024,
            period_month=3,
        )

        resp = client.get("/api/v1/payroll?period_year=2024&period_month=3")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp2 = client.get("/api/v1/payroll?period_year=2025&period_month=3")
        assert resp2.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/v1/payroll/{payroll_id} — detail
# ---------------------------------------------------------------------------


class TestGetPayroll:
    """Tests for the detail endpoint."""

    def test_get_existing(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        payroll = _make_payroll(db_session, tenant.id, employee.id, contract.id)

        resp = client.get(f"/api/v1/payroll/{payroll.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(payroll.id)
        assert data["status"] == "draft"
        assert data["period_year"] == 2024
        assert data["period_month"] == 1

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get(f"/api/v1/payroll/{uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/payroll — create
# ---------------------------------------------------------------------------


class TestCreatePayroll:
    """Tests for the create endpoint."""

    def test_create_returns_201(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        payload = _payroll_payload(tenant.id, employee.id, contract.id)

        resp = client.post("/api/v1/payroll", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "draft"
        assert data["tenant_id"] == str(tenant.id)
        assert data["employee_id"] == str(employee.id)
        assert "id" in data

    def test_create_duplicate_returns_409(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        _make_payroll(db_session, tenant.id, employee.id, contract.id)

        payload = _payroll_payload(tenant.id, employee.id, contract.id)
        resp = client.post("/api/v1/payroll", json=payload)
        assert resp.status_code == 409

    def test_create_missing_required_field_returns_422(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        payload = _payroll_payload(tenant.id, employee.id, contract.id)
        del payload["base_wage"]

        resp = client.post("/api/v1/payroll", json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/v1/payroll/{payroll_id} — partial update
# ---------------------------------------------------------------------------


class TestUpdatePayroll:
    """Tests for the partial-update endpoint."""

    def test_update_single_field(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        payroll = _make_payroll(db_session, tenant.id, employee.id, contract.id)

        resp = client.patch(
            f"/api/v1/payroll/{payroll.id}",
            json={"status": "calculated"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "calculated"

    def test_update_nonexistent_returns_404(self, client):
        resp = client.patch(
            f"/api/v1/payroll/{uuid4()}",
            json={"status": "calculated"},
        )
        assert resp.status_code == 404

    def test_update_invalid_status_returns_422(self, client, db_session, prerequisites):
        """Invalid status value should return 422."""
        tenant, _insurer, employee, contract = prerequisites
        payroll = _make_payroll(db_session, tenant.id, employee.id, contract.id)

        resp = client.patch(
            f"/api/v1/payroll/{payroll.id}",
            json={"status": "invalid_status"},
        )
        # Pydantic validates the Literal type, so 422 is expected
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/payroll/{payroll_id} — delete
# ---------------------------------------------------------------------------


class TestDeletePayroll:
    """Tests for the delete endpoint."""

    def test_delete_existing_returns_204(self, client, db_session, prerequisites):
        tenant, _insurer, employee, contract = prerequisites
        payroll = _make_payroll(db_session, tenant.id, employee.id, contract.id)

        resp = client.delete(f"/api/v1/payroll/{payroll.id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp2 = client.get(f"/api/v1/payroll/{payroll.id}")
        assert resp2.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        resp = client.delete(f"/api/v1/payroll/{uuid4()}")
        assert resp.status_code == 404
