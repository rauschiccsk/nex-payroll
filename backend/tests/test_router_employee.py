"""Tests for Employee API router.

Covers all CRUD endpoints:
  GET    /api/v1/employees         (list, paginated, with filters)
  GET    /api/v1/employees/{id}    (detail)
  POST   /api/v1/employees         (create)
  PATCH  /api/v1/employees/{id}    (partial update)
  DELETE /api/v1/employees/{id}    (soft-delete)

Also tests error-mapping helper (_raise_for_value_error):
  "not found"           → 404
  "already exists"      → 409
  "invalid"/"constraint" → 422
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/employees"
TENANT_URL = "/api/v1/tenants"
INSURER_URL = "/api/v1/health-insurers"

# Counter to generate unique ICO / employee_number across tests
_ICO_COUNTER = 10_000_000


def _next_ico() -> str:
    """Return a unique 8-digit ICO for each call."""
    global _ICO_COUNTER  # noqa: PLW0603
    _ICO_COUNTER += 1
    return str(_ICO_COUNTER)


def _create_tenant(client: TestClient, **overrides) -> dict:
    """Helper — create a tenant and return response JSON."""
    defaults = {
        "name": "Test Firma s.r.o.",
        "ico": _next_ico(),
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
        "code": _next_ico()[-4:],
        "name": "VšZP",
        "iban": "SK1234567890123456789012",
    }
    defaults.update(overrides)
    resp = client.post(INSURER_URL, json=defaults)
    assert resp.status_code == 201
    return resp.json()


def _create_employee_payload(tenant_id: str, insurer_id: str, **overrides) -> dict:
    """Return a valid EmployeeCreate dict with optional overrides."""
    defaults = {
        "tenant_id": tenant_id,
        "employee_number": "EMP001",
        "first_name": "Ján",
        "last_name": "Novák",
        "birth_date": "1990-05-15",
        "birth_number": "9005150001",
        "gender": "M",
        "nationality": "SK",
        "address_street": "Hlavná 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000012345678",
        "health_insurer_id": insurer_id,
        "tax_declaration_type": "standard",
        "hire_date": "2024-01-15",
    }
    defaults.update(overrides)
    return defaults


def _setup_dependencies(client: TestClient) -> tuple[str, str]:
    """Create tenant + insurer, return (tenant_id, insurer_id)."""
    tenant = _create_tenant(client)
    insurer = _create_insurer(client)
    return tenant["id"], insurer["id"]


# ---------------------------------------------------------------------------
# POST — Create
# ---------------------------------------------------------------------------
class TestCreateEmployee:
    """POST /api/v1/employees"""

    def test_create_success(self, client: TestClient):
        tenant_id, insurer_id = _setup_dependencies(client)
        payload = _create_employee_payload(tenant_id, insurer_id)
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["employee_number"] == "EMP001"
        assert data["first_name"] == "Ján"
        assert data["last_name"] == "Novák"
        assert data["tenant_id"] == tenant_id
        assert data["health_insurer_id"] == insurer_id
        assert data["is_deleted"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_duplicate_employee_number(self, client: TestClient):
        tenant_id, insurer_id = _setup_dependencies(client)
        payload = _create_employee_payload(tenant_id, insurer_id)
        resp1 = client.post(BASE_URL, json=payload)
        assert resp1.status_code == 201

        resp2 = client.post(BASE_URL, json=payload)
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]

    def test_create_missing_required_field(self, client: TestClient):
        tenant_id, insurer_id = _setup_dependencies(client)
        payload = _create_employee_payload(tenant_id, insurer_id)
        del payload["first_name"]
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_invalid_gender(self, client: TestClient):
        """Gender must be 'M' or 'F'."""
        tenant_id, insurer_id = _setup_dependencies(client)
        payload = _create_employee_payload(tenant_id, insurer_id, gender="X")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_invalid_iban(self, client: TestClient):
        """IBAN must match expected format."""
        tenant_id, insurer_id = _setup_dependencies(client)
        payload = _create_employee_payload(tenant_id, insurer_id, bank_iban="INVALID")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_invalid_tax_declaration_type(self, client: TestClient):
        """tax_declaration_type must be standard/secondary/none."""
        tenant_id, insurer_id = _setup_dependencies(client)
        payload = _create_employee_payload(tenant_id, insurer_id, tax_declaration_type="bogus")
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 422

    def test_create_with_all_optional_fields(self, client: TestClient):
        """Create employee with every optional field populated."""
        tenant_id, insurer_id = _setup_dependencies(client)
        payload = _create_employee_payload(
            tenant_id,
            insurer_id,
            title_before="Ing.",
            title_after="PhD.",
            bank_bic="SUBASKBX",
            nczd_applied=False,
            pillar2_saver=True,
            is_disabled=True,
            status="inactive",
            termination_date="2025-12-31",
        )
        resp = client.post(BASE_URL, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title_before"] == "Ing."
        assert data["title_after"] == "PhD."
        assert data["bank_bic"] == "SUBASKBX"
        assert data["nczd_applied"] is False
        assert data["pillar2_saver"] is True
        assert data["is_disabled"] is True
        assert data["status"] == "inactive"
        assert data["termination_date"] == "2025-12-31"

    def test_create_same_number_different_tenant(self, client: TestClient):
        """Same employee_number in different tenants should succeed."""
        t1_id, ins1_id = _setup_dependencies(client)
        t2_id, ins2_id = _setup_dependencies(client)
        p1 = _create_employee_payload(t1_id, ins1_id, employee_number="SHARED01")
        p2 = _create_employee_payload(t2_id, ins2_id, employee_number="SHARED01")
        resp1 = client.post(BASE_URL, json=p1)
        assert resp1.status_code == 201
        resp2 = client.post(BASE_URL, json=p2)
        assert resp2.status_code == 201


# ---------------------------------------------------------------------------
# GET list — Paginated
# ---------------------------------------------------------------------------
class TestListEmployees:
    """GET /api/v1/employees"""

    def test_list_empty(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        tenant_id, insurer_id = _setup_dependencies(client)
        client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id),
        )
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_pagination(self, client: TestClient):
        tenant_id, insurer_id = _setup_dependencies(client)
        for i in range(3):
            client.post(
                BASE_URL,
                json=_create_employee_payload(tenant_id, insurer_id, employee_number=f"EMP{i:03d}"),
            )
        resp = client.get(BASE_URL, params={"skip": 1, "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] == 3
        assert data["skip"] == 1
        assert data["limit"] == 2

    def test_list_filter_by_tenant(self, client: TestClient):
        t1_id, ins1_id = _setup_dependencies(client)
        t2_id, ins2_id = _setup_dependencies(client)
        client.post(
            BASE_URL,
            json=_create_employee_payload(t1_id, ins1_id, employee_number="T1E01"),
        )
        client.post(
            BASE_URL,
            json=_create_employee_payload(t2_id, ins2_id, employee_number="T2E01"),
        )
        resp = client.get(BASE_URL, params={"tenant_id": t1_id})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        for item in data["items"]:
            assert item["tenant_id"] == t1_id

    def test_list_filter_by_status(self, client: TestClient):
        """Filter employees by status=active vs terminated."""
        tenant_id, insurer_id = _setup_dependencies(client)
        client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id, employee_number="ACT01", status="active"),
        )
        client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id, employee_number="TRM01", status="terminated"),
        )
        resp = client.get(BASE_URL, params={"tenant_id": tenant_id, "status": "active"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert all(item["status"] == "active" for item in data["items"])

    def test_list_excludes_deleted_by_default(self, client: TestClient):
        """Soft-deleted employees must not appear in default list."""
        tenant_id, insurer_id = _setup_dependencies(client)
        create_resp = client.post(BASE_URL, json=_create_employee_payload(tenant_id, insurer_id))
        emp_id = create_resp.json()["id"]
        client.delete(f"{BASE_URL}/{emp_id}")

        resp = client.get(BASE_URL, params={"tenant_id": tenant_id})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_include_deleted(self, client: TestClient):
        """include_deleted=true must return soft-deleted employees."""
        tenant_id, insurer_id = _setup_dependencies(client)
        create_resp = client.post(BASE_URL, json=_create_employee_payload(tenant_id, insurer_id))
        emp_id = create_resp.json()["id"]
        client.delete(f"{BASE_URL}/{emp_id}")

        resp = client.get(
            BASE_URL,
            params={"tenant_id": tenant_id, "include_deleted": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["is_deleted"] is True

    def test_list_invalid_skip(self, client: TestClient):
        resp = client.get(BASE_URL, params={"skip": -1})
        assert resp.status_code == 422

    def test_list_invalid_limit(self, client: TestClient):
        resp = client.get(BASE_URL, params={"limit": 0})
        assert resp.status_code == 422

    def test_list_limit_max(self, client: TestClient):
        resp = client.get(BASE_URL, params={"limit": 101})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET detail
# ---------------------------------------------------------------------------
class TestGetEmployee:
    """GET /api/v1/employees/{employee_id}"""

    def test_get_existing(self, client: TestClient):
        tenant_id, insurer_id = _setup_dependencies(client)
        create_resp = client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id),
        )
        employee_id = create_resp.json()["id"]

        resp = client.get(f"{BASE_URL}/{employee_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == employee_id
        assert data["first_name"] == "Ján"

    def test_get_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Employee not found"

    def test_get_invalid_uuid(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH — Update
# ---------------------------------------------------------------------------
class TestUpdateEmployee:
    """PATCH /api/v1/employees/{employee_id}"""

    def test_update_single_field(self, client: TestClient):
        tenant_id, insurer_id = _setup_dependencies(client)
        create_resp = client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id),
        )
        employee_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{employee_id}",
            json={"first_name": "Peter"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["first_name"] == "Peter"
        # Other fields unchanged
        assert data["last_name"] == "Novák"

    def test_update_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.patch(f"{BASE_URL}/{fake_id}", json={"first_name": "X"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Employee not found"

    def test_update_duplicate_employee_number(self, client: TestClient):
        tenant_id, insurer_id = _setup_dependencies(client)
        client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id, employee_number="EMP001"),
        )
        create_resp = client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id, employee_number="EMP002"),
        )
        employee_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{employee_id}",
            json={"employee_number": "EMP001"},
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_update_status_transition(self, client: TestClient):
        """Can update status from active to terminated."""
        tenant_id, insurer_id = _setup_dependencies(client)
        create_resp = client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id),
        )
        emp_id = create_resp.json()["id"]

        resp = client.patch(
            f"{BASE_URL}/{emp_id}",
            json={"status": "terminated", "termination_date": "2025-06-30"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "terminated"
        assert data["termination_date"] == "2025-06-30"


# ---------------------------------------------------------------------------
# DELETE — Soft-delete
# ---------------------------------------------------------------------------
class TestDeleteEmployee:
    """DELETE /api/v1/employees/{employee_id}"""

    def test_delete_existing(self, client: TestClient):
        tenant_id, insurer_id = _setup_dependencies(client)
        create_resp = client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id),
        )
        employee_id = create_resp.json()["id"]

        resp = client.delete(f"{BASE_URL}/{employee_id}")
        assert resp.status_code == 204

    def test_delete_soft_deletes(self, client: TestClient):
        """After delete, employee should be soft-deleted (is_deleted=True)."""
        tenant_id, insurer_id = _setup_dependencies(client)
        create_resp = client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id),
        )
        employee_id = create_resp.json()["id"]

        client.delete(f"{BASE_URL}/{employee_id}")

        # Should still exist when fetched directly
        get_resp = client.get(f"{BASE_URL}/{employee_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["is_deleted"] is True

    def test_delete_excluded_from_default_list(self, client: TestClient):
        """Soft-deleted employees should not appear in default list."""
        tenant_id, insurer_id = _setup_dependencies(client)
        create_resp = client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id),
        )
        employee_id = create_resp.json()["id"]

        client.delete(f"{BASE_URL}/{employee_id}")

        list_resp = client.get(BASE_URL)
        assert list_resp.status_code == 200
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert employee_id not in ids

    def test_delete_included_with_flag(self, client: TestClient):
        """Soft-deleted employees should appear when include_deleted=true."""
        tenant_id, insurer_id = _setup_dependencies(client)
        create_resp = client.post(
            BASE_URL,
            json=_create_employee_payload(tenant_id, insurer_id),
        )
        employee_id = create_resp.json()["id"]

        client.delete(f"{BASE_URL}/{employee_id}")

        list_resp = client.get(BASE_URL, params={"include_deleted": True})
        assert list_resp.status_code == 200
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert employee_id in ids

    def test_delete_not_found(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"{BASE_URL}/{fake_id}")
        assert resp.status_code == 404

    def test_delete_invalid_uuid(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/not-a-uuid")
        assert resp.status_code == 422
