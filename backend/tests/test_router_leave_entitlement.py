"""Tests for LeaveEntitlement API router.

Covers all CRUD endpoints:
  GET    /api/v1/leave-entitlements            (list, paginated)
  GET    /api/v1/leave-entitlements/{id}       (detail)
  POST   /api/v1/leave-entitlements            (create)
  PUT    /api/v1/leave-entitlements/{id}       (update)
  DELETE /api/v1/leave-entitlements/{id}       (delete)
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/leave-entitlements"
TENANT_URL = "/api/v1/tenants"
INSURER_URL = "/api/v1/health-insurers"
EMPLOYEE_URL = "/api/v1/employees"


def _create_tenant(client: TestClient, **overrides) -> dict:
    """Helper — create a tenant and return response JSON."""
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
    """Helper — create a health insurer and return response JSON."""
    defaults = {
        "code": "25",
        "name": "VšZP",
        "iban": "SK1234567890123456789012",
    }
    defaults.update(overrides)
    resp = client.post(INSURER_URL, json=defaults)
    assert resp.status_code == 201
    return resp.json()


def _create_employee(client: TestClient, tenant_id: str, insurer_id: str, **overrides) -> dict:
    """Helper — create an employee and return response JSON."""
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


def _create_entitlement_payload(tenant_id: str, employee_id: str, **overrides) -> dict:
    """Return a valid LeaveEntitlementCreate dict with optional overrides."""
    defaults = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "year": 2025,
        "total_days": 25,
        "used_days": 0,
        "remaining_days": 25,
        "carryover_days": 3,
    }
    defaults.update(overrides)
    return defaults


def _setup_tenant_and_employee(client: TestClient) -> tuple[str, str]:
    """Create a tenant + insurer + employee, return (tenant_id, employee_id)."""
    tenant = _create_tenant(client)
    insurer = _create_insurer(client)
    employee = _create_employee(client, tenant["id"], insurer["id"])
    return tenant["id"], employee["id"]


# ── LIST ────────────────────────────────────────────────────────────────


class TestListLeaveEntitlements:
    def test_empty_list(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        payload = _create_entitlement_payload(tenant_id, employee_id)
        client.post(BASE_URL, json=payload)

        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["year"] == 2025

    def test_pagination(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        for yr in (2023, 2024, 2025):
            payload = _create_entitlement_payload(tenant_id, employee_id, year=yr)
            client.post(BASE_URL, json=payload)

        resp = client.get(BASE_URL, params={"skip": 0, "limit": 2})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_filter_by_tenant(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        payload = _create_entitlement_payload(tenant_id, employee_id)
        client.post(BASE_URL, json=payload)

        resp = client.get(BASE_URL, params={"tenant_id": tenant_id})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"tenant_id": str(uuid.uuid4())})
        assert resp.json()["total"] == 0

    def test_filter_by_employee(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        payload = _create_entitlement_payload(tenant_id, employee_id)
        client.post(BASE_URL, json=payload)

        resp = client.get(BASE_URL, params={"employee_id": employee_id})
        assert resp.json()["total"] == 1

    def test_filter_by_year(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        for yr in (2024, 2025):
            payload = _create_entitlement_payload(tenant_id, employee_id, year=yr)
            client.post(BASE_URL, json=payload)

        resp = client.get(BASE_URL, params={"year": 2025})
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["year"] == 2025


# ── GET DETAIL ──────────────────────────────────────────────────────────


class TestGetLeaveEntitlement:
    def test_get_existing(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        payload = _create_entitlement_payload(tenant_id, employee_id)
        created = client.post(BASE_URL, json=payload).json()

        resp = client.get(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]
        assert data["year"] == 2025
        assert data["total_days"] == 25

    def test_get_not_found(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404


# ── CREATE ──────────────────────────────────────────────────────────────


class TestCreateLeaveEntitlement:
    def test_create_success(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        payload = _create_entitlement_payload(tenant_id, employee_id)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["tenant_id"] == tenant_id
        assert data["employee_id"] == employee_id
        assert data["year"] == 2025
        assert data["total_days"] == 25
        assert data["carryover_days"] == 3
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_duplicate_conflict(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        payload = _create_entitlement_payload(tenant_id, employee_id)
        resp1 = client.post(BASE_URL, json=payload)
        assert resp1.status_code == 201

        resp2 = client.post(BASE_URL, json=payload)
        assert resp2.status_code == 409


# ── UPDATE ──────────────────────────────────────────────────────────────


class TestUpdateLeaveEntitlement:
    def test_update_success(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        payload = _create_entitlement_payload(tenant_id, employee_id)
        created = client.post(BASE_URL, json=payload).json()

        resp = client.put(
            f"{BASE_URL}/{created['id']}",
            json={"used_days": 5, "remaining_days": 20},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["used_days"] == 5
        assert data["remaining_days"] == 20
        # unchanged fields
        assert data["total_days"] == 25

    def test_update_not_found(self, client: TestClient):
        resp = client.put(
            f"{BASE_URL}/{uuid.uuid4()}",
            json={"used_days": 1},
        )
        assert resp.status_code == 404


# ── DELETE ──────────────────────────────────────────────────────────────


class TestDeleteLeaveEntitlement:
    def test_delete_success(self, client: TestClient):
        tenant_id, employee_id = _setup_tenant_and_employee(client)
        payload = _create_entitlement_payload(tenant_id, employee_id)
        created = client.post(BASE_URL, json=payload).json()

        resp = client.delete(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 204

        # confirm gone
        resp = client.get(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 404

    def test_delete_not_found(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404
