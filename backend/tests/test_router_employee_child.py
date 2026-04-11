"""Tests for EmployeeChild API router.

Covers all CRUD endpoints:
  GET    /api/v1/employee-children         (list, paginated)
  GET    /api/v1/employee-children/{id}    (detail)
  POST   /api/v1/employee-children         (create)
  PUT    /api/v1/employee-children/{id}    (update)
  DELETE /api/v1/employee-children/{id}    (delete)
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/employee-children"
TENANT_URL = "/api/v1/tenants"
INSURER_URL = "/api/v1/health-insurers"
EMPLOYEE_URL = "/api/v1/employees"


def _create_tenant(client: TestClient, **overrides) -> dict:
    defaults = {
        "name": "Test Firma s.r.o.",
        "ico": "12345678",
        "address_street": "Hlavna 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "bank_iban": "SK8975000000000012345678",
    }
    defaults.update(overrides)
    resp = client.post(TENANT_URL, json=defaults)
    assert resp.status_code == 201
    return resp.json()


def _create_insurer(client: TestClient, **overrides) -> dict:
    defaults = {"code": "25", "name": "VšZP", "iban": "SK1234567890123456789012"}
    defaults.update(overrides)
    resp = client.post(INSURER_URL, json=defaults)
    assert resp.status_code == 201
    return resp.json()


def _create_employee(client: TestClient, tenant_id: str, insurer_id: str, **overrides) -> dict:
    defaults = {
        "tenant_id": tenant_id,
        "employee_number": "EMP001",
        "first_name": "Ján",
        "last_name": "Novák",
        "birth_date": "1990-01-15",
        "birth_number": "9001151234",
        "gender": "M",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "bank_iban": "SK3112000000198742637541",
        "health_insurer_id": insurer_id,
        "tax_declaration_type": "standard",
        "hire_date": "2024-01-15",
    }
    defaults.update(overrides)
    resp = client.post(EMPLOYEE_URL, json=defaults)
    assert resp.status_code == 201
    return resp.json()


def _setup_tenant_and_employee(client: TestClient) -> tuple[str, str]:
    tenant = _create_tenant(client)
    insurer = _create_insurer(client)
    employee = _create_employee(client, tenant["id"], insurer["id"])
    return tenant["id"], employee["id"]


def _child_payload(tenant_id: str, employee_id: str, **overrides) -> dict:
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "first_name": "Anna",
        "last_name": "Nováková",
        "birth_date": "2015-03-20",
        "birth_number": "1503200001",
        "is_tax_bonus_eligible": True,
    }
    defaults.update(overrides)
    return defaults


# ── LIST ───────────────────────────────────────────────────────────────


class TestListEmployeeChildren:
    def test_empty_list(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        client.post(BASE_URL, json=_child_payload(tid, eid))
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_pagination(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        for i in range(3):
            client.post(BASE_URL, json=_child_payload(tid, eid, first_name=f"Child{i}"))
        resp = client.get(BASE_URL, params={"skip": 0, "limit": 2})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_filter_by_tenant(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        client.post(BASE_URL, json=_child_payload(tid, eid))
        resp = client.get(BASE_URL, params={"tenant_id": tid})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"tenant_id": str(uuid.uuid4())})
        assert resp.json()["total"] == 0

    def test_filter_by_employee(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        client.post(BASE_URL, json=_child_payload(tid, eid))
        resp = client.get(BASE_URL, params={"employee_id": eid})
        assert resp.json()["total"] == 1


# ── GET DETAIL ─────────────────────────────────────────────────────────


class TestGetEmployeeChild:
    def test_get_existing(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        created = client.post(BASE_URL, json=_child_payload(tid, eid)).json()
        resp = client.get(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Anna"

    def test_get_not_found(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404


# ── CREATE ─────────────────────────────────────────────────────────────


class TestCreateEmployeeChild:
    def test_create_success(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        resp = client.post(BASE_URL, json=_child_payload(tid, eid))
        assert resp.status_code == 201
        data = resp.json()
        assert data["first_name"] == "Anna"
        assert data["last_name"] == "Nováková"
        assert data["birth_date"] == "2015-03-20"
        assert data["is_tax_bonus_eligible"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_missing_required(self, client: TestClient):
        resp = client.post(BASE_URL, json={"first_name": "X"})
        assert resp.status_code == 422


# ── UPDATE ─────────────────────────────────────────────────────────────


class TestUpdateEmployeeChild:
    def test_update_success(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        created = client.post(BASE_URL, json=_child_payload(tid, eid)).json()
        resp = client.patch(
            f"{BASE_URL}/{created['id']}",
            json={"first_name": "Mária", "is_tax_bonus_eligible": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["first_name"] == "Mária"
        assert data["is_tax_bonus_eligible"] is False

    def test_update_not_found(self, client: TestClient):
        resp = client.patch(f"{BASE_URL}/{uuid.uuid4()}", json={"first_name": "X"})
        assert resp.status_code in (404, 409)


# ── DELETE ─────────────────────────────────────────────────────────────


class TestDeleteEmployeeChild:
    def test_delete_success(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        created = client.post(BASE_URL, json=_child_payload(tid, eid)).json()
        resp = client.delete(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 204
        assert client.get(f"{BASE_URL}/{created['id']}").status_code == 404

    def test_delete_not_found(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404
