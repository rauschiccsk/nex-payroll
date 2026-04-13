"""Tests for nested employee-children endpoint.

Covers:
  GET  /api/v1/employees/{employee_id}/children
  POST /api/v1/employees/{employee_id}/children

DESIGN.md §6.6
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_child import EmployeeChild
from app.models.health_insurer import HealthInsurer
from app.models.tenant import Tenant

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session: Session, **overrides) -> Tenant:
    defaults = {
        "name": "Children Test s.r.o.",
        "ico": "44441111",
        "address_street": "Kvetná 1",
        "address_city": "Trnava",
        "address_zip": "91701",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012344321",
        "schema_name": "tenant_children_test_44441111",
    }
    defaults.update(overrides)
    t = Tenant(**defaults)
    db_session.add(t)
    db_session.flush()
    return t


def _make_health_insurer(db_session: Session, **overrides) -> HealthInsurer:
    defaults = {"code": "44", "name": "Union", "iban": "SK0000000000000000000044"}
    defaults.update(overrides)
    hi = HealthInsurer(**defaults)
    db_session.add(hi)
    db_session.flush()
    return hi


def _make_employee(db_session: Session, tenant_id, health_insurer_id, **overrides) -> Employee:
    defaults = {
        "tenant_id": tenant_id,
        "employee_number": "EMP-CH-001",
        "first_name": "Mária",
        "last_name": "Kováčová",
        "birth_date": date(1988, 7, 10),
        "birth_number": "8807100001",
        "gender": "F",
        "nationality": "SK",
        "address_street": "Slnečná 3",
        "address_city": "Trnava",
        "address_zip": "91701",
        "address_country": "SK",
        "bank_iban": "SK8975000000000087651234",
        "health_insurer_id": health_insurer_id,
        "tax_declaration_type": "standard",
        "nczd_applied": True,
        "pillar2_saver": False,
        "is_disabled": False,
        "status": "active",
        "hire_date": date(2020, 3, 1),
    }
    defaults.update(overrides)
    emp = Employee(**defaults)
    db_session.add(emp)
    db_session.flush()
    return emp


def _make_child(db_session: Session, tenant_id, employee_id, **overrides) -> EmployeeChild:
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "first_name": "Tomáš",
        "last_name": "Kováč",
        "birth_date": date(2015, 5, 20),
        "is_tax_bonus_eligible": True,
    }
    defaults.update(overrides)
    c = EmployeeChild(**defaults)
    db_session.add(c)
    db_session.flush()
    return c


@pytest.fixture()
def prereqs(db_session: Session):
    tenant = _make_tenant(db_session)
    insurer = _make_health_insurer(db_session)
    employee = _make_employee(db_session, tenant.id, insurer.id)
    return tenant, insurer, employee


# ---------------------------------------------------------------------------
# GET /api/v1/employees/{employee_id}/children
# ---------------------------------------------------------------------------


class TestNestedListChildren:
    def test_list_empty(self, client: TestClient, prereqs):
        _tenant, _insurer, employee = prereqs
        resp = client.get(f"/api/v1/employees/{employee.id}/children")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_list_returns_employee_children(self, client: TestClient, db_session: Session, prereqs):
        tenant, _insurer, employee = prereqs
        _make_child(db_session, tenant.id, employee.id, first_name="Anna")
        _make_child(db_session, tenant.id, employee.id, first_name="Ján")

        resp = client.get(f"/api/v1/employees/{employee.id}/children")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        for item in body["items"]:
            assert item["employee_id"] == str(employee.id)

    def test_list_excludes_other_employee_children(self, client: TestClient, db_session: Session, prereqs):
        tenant, insurer, employee = prereqs
        emp2 = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP-CH-OTHER")
        _make_child(db_session, tenant.id, employee.id, first_name="Mine")
        _make_child(db_session, tenant.id, emp2.id, first_name="Theirs")

        resp = client.get(f"/api/v1/employees/{employee.id}/children")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["first_name"] == "Mine"


# ---------------------------------------------------------------------------
# POST /api/v1/employees/{employee_id}/children
# ---------------------------------------------------------------------------


class TestNestedCreateChild:
    def test_create_success(self, client: TestClient, prereqs):
        tenant, _insurer, employee = prereqs
        payload = {
            "tenant_id": str(tenant.id),
            "employee_id": str(employee.id),
            "first_name": "Lucia",
            "last_name": "Kováčová",
            "birth_date": "2018-11-25",
            "is_tax_bonus_eligible": True,
        }
        resp = client.post(f"/api/v1/employees/{employee.id}/children", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["employee_id"] == str(employee.id)
        assert body["first_name"] == "Lucia"
