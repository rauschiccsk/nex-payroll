"""Tests for MonthlyReport API router.

Covers all CRUD endpoints:
  GET    /api/v1/monthly-reports         (list, paginated)
  GET    /api/v1/monthly-reports/{id}    (detail)
  POST   /api/v1/monthly-reports         (create)
  PATCH  /api/v1/monthly-reports/{id}    (update)
  DELETE /api/v1/monthly-reports/{id}    (delete)
"""

import uuid

from fastapi.testclient import TestClient

BASE_URL = "/api/v1/monthly-reports"
TENANT_URL = "/api/v1/tenants"


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


def _report_payload(tenant_id: str, **overrides) -> dict:
    defaults = {
        "tenant_id": tenant_id,
        "period_year": 2025,
        "period_month": 1,
        "report_type": "sp_monthly",
        "file_path": "/data/reports/2025/01/sp_monthly.xml",
        "file_format": "xml",
        "status": "generated",
        "deadline_date": "2025-02-20",
        "institution": "Sociálna poisťovňa",
    }
    defaults.update(overrides)
    return defaults


# ── LIST ───────────────────────────────────────────────────────────────


class TestListMonthlyReports:
    def test_empty_list(self, client: TestClient):
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["skip"] == 0
        assert data["limit"] == 50

    def test_list_returns_created(self, client: TestClient):
        tenant = _create_tenant(client)
        client.post(BASE_URL, json=_report_payload(tenant["id"]))
        resp = client.get(BASE_URL)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_pagination(self, client: TestClient):
        tenant = _create_tenant(client)
        for m in (1, 2, 3):
            client.post(
                BASE_URL,
                json=_report_payload(tenant["id"], period_month=m, deadline_date=f"2025-0{m + 1}-20"),
            )
        resp = client.get(BASE_URL, params={"skip": 0, "limit": 2})
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

    def test_filter_by_tenant(self, client: TestClient):
        tenant = _create_tenant(client)
        client.post(BASE_URL, json=_report_payload(tenant["id"]))
        resp = client.get(BASE_URL, params={"tenant_id": tenant["id"]})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"tenant_id": str(uuid.uuid4())})
        assert resp.json()["total"] == 0

    def test_filter_by_report_type(self, client: TestClient):
        tenant = _create_tenant(client)
        client.post(BASE_URL, json=_report_payload(tenant["id"], report_type="sp_monthly"))
        resp = client.get(BASE_URL, params={"report_type": "sp_monthly"})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"report_type": "zp_vszp"})
        assert resp.json()["total"] == 0

    def test_filter_by_status(self, client: TestClient):
        tenant = _create_tenant(client)
        client.post(BASE_URL, json=_report_payload(tenant["id"], status="generated"))
        resp = client.get(BASE_URL, params={"status": "generated"})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"status": "submitted"})
        assert resp.json()["total"] == 0

    def test_filter_by_period(self, client: TestClient):
        tenant = _create_tenant(client)
        client.post(BASE_URL, json=_report_payload(tenant["id"], period_year=2025, period_month=3))
        resp = client.get(BASE_URL, params={"period_year": 2025, "period_month": 3})
        assert resp.json()["total"] == 1

        resp = client.get(BASE_URL, params={"period_year": 2024})
        assert resp.json()["total"] == 0


# ── GET DETAIL ─────────────────────────────────────────────────────────


class TestGetMonthlyReport:
    def test_get_existing(self, client: TestClient):
        tenant = _create_tenant(client)
        created = client.post(BASE_URL, json=_report_payload(tenant["id"])).json()
        resp = client.get(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["report_type"] == "sp_monthly"

    def test_get_not_found(self, client: TestClient):
        resp = client.get(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404


# ── CREATE ─────────────────────────────────────────────────────────────


class TestCreateMonthlyReport:
    def test_create_success(self, client: TestClient):
        tenant = _create_tenant(client)
        resp = client.post(BASE_URL, json=_report_payload(tenant["id"]))
        assert resp.status_code == 201
        data = resp.json()
        assert data["report_type"] == "sp_monthly"
        assert data["period_year"] == 2025
        assert data["period_month"] == 1
        assert data["status"] == "generated"
        assert data["institution"] == "Sociálna poisťovňa"
        assert "id" in data
        assert "created_at" in data

    def test_create_duplicate_returns_409(self, client: TestClient):
        tenant = _create_tenant(client)
        payload = _report_payload(tenant["id"])
        resp1 = client.post(BASE_URL, json=payload)
        assert resp1.status_code == 201
        resp2 = client.post(BASE_URL, json=payload)
        assert resp2.status_code == 409

    def test_create_missing_required(self, client: TestClient):
        resp = client.post(BASE_URL, json={"report_type": "sp_monthly"})
        assert resp.status_code == 422


# ── UPDATE ─────────────────────────────────────────────────────────────


class TestUpdateMonthlyReport:
    def test_update_success(self, client: TestClient):
        tenant = _create_tenant(client)
        created = client.post(BASE_URL, json=_report_payload(tenant["id"])).json()
        resp = client.patch(
            f"{BASE_URL}/{created['id']}",
            json={"status": "submitted"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"

    def test_update_not_found(self, client: TestClient):
        resp = client.patch(f"{BASE_URL}/{uuid.uuid4()}", json={"status": "submitted"})
        assert resp.status_code == 404


# ── DELETE ─────────────────────────────────────────────────────────────


class TestDeleteMonthlyReport:
    def test_delete_success(self, client: TestClient):
        tenant = _create_tenant(client)
        created = client.post(BASE_URL, json=_report_payload(tenant["id"])).json()
        resp = client.delete(f"{BASE_URL}/{created['id']}")
        assert resp.status_code == 204
        assert client.get(f"{BASE_URL}/{created['id']}").status_code == 404

    def test_delete_not_found(self, client: TestClient):
        resp = client.delete(f"{BASE_URL}/{uuid.uuid4()}")
        assert resp.status_code == 404
