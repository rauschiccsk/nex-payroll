"""Tests for Leave API router.

Covers all CRUD endpoints:
  GET    /api/v1/leaves         (list, paginated)
  GET    /api/v1/leaves/{id}    (detail)
  POST   /api/v1/leaves         (create)
  PATCH  /api/v1/leaves/{id}    (update)
  DELETE /api/v1/leaves/{id}    (delete)
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/leaves"
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


def _leave_payload(tenant_id: str, employee_id: str, **overrides) -> dict:
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "leave_type": "annual",
        "start_date": "2025-07-01",
        "end_date": "2025-07-14",
        "business_days": 10,
        "status": "pending",
    }
    defaults.update(overrides)
    return defaults


# ── LIST ───────────────────────────────────────────────────────────────


class TestListLeaves:
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
        client.post(BASE_URL, json=_leave_payload(tid, eid))
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_pagination(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        for i in range(3):
            client.post(
                BASE_URL,
                json=_leave_payload(
                    tid,
                    eid,
                    start_date=f"2025-0{i + 1}-01",
                    end_date=f"2025-0{i + 1}-10",
                ),
            )
        resp = client.get(BASE_URL, params={"skip": 0, "limit": 2})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_filter_by_tenant(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        client.post(BASE_URL, json=_leave_payload(tid, eid))
        resp = client.get(BASE_URL, params={"tenant_id": tid})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"tenant_id": str(uuid.uuid4())})
        assert resp.json()["total"] == 0

    def test_filter_by_status(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        client.post(BASE_URL, json=_leave_payload(tid, eid, status="approved"))
        resp = client.get(BASE_URL, params={"status": "approved"})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"status": "rejected"})
        assert resp.json()["total"] == 0


# ── GET DETAIL ─────────────────────────────────────────────────────────


class TestGetLeave:
    def test_get_existing(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        created = client.post(BASE_URL, json=_leave_payload(tid, eid)).json()
        resp = client.get(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["leave_type"] == "annual"

    def test_get_not_found(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404


# ── CREATE ─────────────────────────────────────────────────────────────


class TestCreateLeave:
    def test_create_success(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        resp = client.post(BASE_URL, json=_leave_payload(tid, eid))
        assert resp.status_code == 201
        data = resp.json()
        assert data["leave_type"] == "annual"
        assert data["business_days"] == 10
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data

    def test_create_missing_required(self, client: TestClient):
        resp = client.post(BASE_URL, json={"leave_type": "annual"})
        assert resp.status_code == 422

    def test_create_invalid_leave_type(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        resp = client.post(BASE_URL, json=_leave_payload(tid, eid, leave_type="invalid"))
        assert resp.status_code == 422


# ── UPDATE ─────────────────────────────────────────────────────────────


class TestUpdateLeave:
    def test_update_success(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        created = client.post(BASE_URL, json=_leave_payload(tid, eid)).json()
        resp = client.patch(
            f"{BASE_URL}/{created['id']}",
            json={"status": "approved", "note": "Schválené"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["note"] == "Schválené"

    def test_update_not_found(self, client: TestClient):
        resp = client.patch(f"{BASE_URL}/{uuid.uuid4()}", json={"status": "approved"})
        assert resp.status_code == 404


# ── DELETE ─────────────────────────────────────────────────────────────


class TestDeleteLeave:
    def test_delete_success(self, client: TestClient):
        tid, eid = _setup_tenant_and_employee(client)
        created = client.post(BASE_URL, json=_leave_payload(tid, eid)).json()
        resp = client.delete(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 204
        assert client.get(f"{BASE_URL}/{created['id']}").status_code == 404

    def test_delete_not_found(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404
