"""Tests for nested contracts endpoint.

Covers:
  GET  /api/v1/employees/{employee_id}/contracts
  POST /api/v1/employees/{employee_id}/contracts

DESIGN.md §6.5
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.health_insurer import HealthInsurer
from app.models.tenant import Tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db_session: Session, **overrides) -> Tenant:
    defaults = {
        "name": "Nested Test s.r.o.",
        "ico": "55551111",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "schema_name": "tenant_nested_test_55551111",
    }
    defaults.update(overrides)
    t = Tenant(**defaults)
    db_session.add(t)
    db_session.flush()
    return t


def _make_health_insurer(db_session: Session, **overrides) -> HealthInsurer:
    defaults = {"code": "55", "name": "Dôvera", "iban": "SK0000000000000000000055"}
    defaults.update(overrides)
    hi = HealthInsurer(**defaults)
    db_session.add(hi)
    db_session.flush()
    return hi


def _make_employee(db_session: Session, tenant_id, health_insurer_id, **overrides) -> Employee:
    defaults = {
        "tenant_id": tenant_id,
        "employee_number": "EMP-NESTED-001",
        "first_name": "Peter",
        "last_name": "Krajčí",
        "birth_date": date(1985, 3, 20),
        "birth_number": "8503200001",
        "gender": "M",
        "nationality": "SK",
        "address_street": "Modrá 5",
        "address_city": "Košice",
        "address_zip": "04001",
        "address_country": "SK",
        "bank_iban": "SK8975000000000087654321",
        "health_insurer_id": health_insurer_id,
        "tax_declaration_type": "standard",
        "nczd_applied": True,
        "pillar2_saver": False,
        "is_disabled": False,
        "status": "active",
        "hire_date": date(2023, 6, 1),
    }
    defaults.update(overrides)
    emp = Employee(**defaults)
    db_session.add(emp)
    db_session.flush()
    return emp


def _make_contract(db_session: Session, tenant_id, employee_id, **overrides) -> Contract:
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "contract_number": "NPC-001",
        "contract_type": "permanent",
        "job_title": "Analytik",
        "wage_type": "monthly",
        "base_wage": Decimal("3000.00"),
        "hours_per_week": Decimal("40.0"),
        "start_date": date(2023, 6, 1),
    }
    defaults.update(overrides)
    c = Contract(**defaults)
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
# GET /api/v1/employees/{employee_id}/contracts
# ---------------------------------------------------------------------------


class TestNestedListContracts:
    def test_list_empty(self, client: TestClient, prereqs):
        tenant, _insurer, employee = prereqs
        resp = client.get(f"/api/v1/employees/{employee.id}/contracts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_list_returns_employee_contracts(self, client: TestClient, db_session: Session, prereqs):
        tenant, insurer, employee = prereqs
        _make_contract(db_session, tenant.id, employee.id, contract_number="NPC-A")
        _make_contract(db_session, tenant.id, employee.id, contract_number="NPC-B", start_date=date(2022, 1, 1))

        resp = client.get(f"/api/v1/employees/{employee.id}/contracts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        for item in body["items"]:
            assert item["employee_id"] == str(employee.id)

    def test_list_excludes_other_employee_contracts(self, client: TestClient, db_session: Session, prereqs):
        tenant, insurer, employee = prereqs
        # Create second employee with their own contract
        emp2 = _make_employee(db_session, tenant.id, insurer.id, employee_number="EMP-OTHER")
        _make_contract(db_session, tenant.id, employee.id, contract_number="NPC-MINE")
        _make_contract(db_session, tenant.id, emp2.id, contract_number="NPC-THEIRS")

        resp = client.get(f"/api/v1/employees/{employee.id}/contracts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["contract_number"] == "NPC-MINE"


# ---------------------------------------------------------------------------
# POST /api/v1/employees/{employee_id}/contracts
# ---------------------------------------------------------------------------


class TestNestedCreateContract:
    def test_create_success(self, client: TestClient, prereqs):
        tenant, _insurer, employee = prereqs
        payload = {
            "tenant_id": str(tenant.id),
            "employee_id": str(employee.id),
            "contract_number": "NPC-NEW",
            "contract_type": "permanent",
            "job_title": "Vývojár",
            "wage_type": "monthly",
            "base_wage": "2800.00",
            "hours_per_week": "40.0",
            "start_date": "2024-01-01",
        }
        resp = client.post(f"/api/v1/employees/{employee.id}/contracts", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["employee_id"] == str(employee.id)
        assert body["contract_number"] == "NPC-NEW"
