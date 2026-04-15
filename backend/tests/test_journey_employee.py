"""Employee onboarding full lifecycle journey test.

Validates the complete employee onboarding workflow:
  1. Create employee via API
  2. Verify PII encryption in DB (birth_number, bank_iban)
  3. Add employment contract
  4. Add 2 children (daňový bonus)
  5. Create leave entitlement
  6. Request and approve annual leave
  7. Verify employee detail + children/contracts via API

Uses the ``client`` fixture which overrides get_current_user (auth bypassed)
so the test focuses on the onboarding lifecycle, not authentication.
"""

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.fixtures.journey_data import (
    CHILD_BASE,
    CONTRACT_BASE,
    EMPLOYEE_BASE,
    HEALTH_INSURERS,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_health_insurer_id(db_session: Session, code: str) -> str:
    """Fetch health insurer ID from shared.health_insurers by code."""
    row = db_session.execute(
        text("SELECT id FROM shared.health_insurers WHERE code = :code"),
        {"code": code},
    ).fetchone()
    assert row is not None, f"Health insurer with code '{code}' not found in shared.health_insurers"
    return str(row.id)


# ---------------------------------------------------------------------------
# Journey test
# ---------------------------------------------------------------------------


def test_employee_full_journey(
    client: TestClient,
    db_session: Session,
) -> None:
    """End-to-end employee onboarding: create → PII check → contract → children → leave."""

    # ------------------------------------------------------------------
    # Step 0 — Create tenant via auth-bypassed client (no test_tenant fixture
    # to avoid dependency_overrides conflict with auth_client)
    # ------------------------------------------------------------------
    tenant_payload = {
        "name": "Employee Journey Firma s.r.o.",
        "ico": "55667788",
        "dic": "2055667788",
        "address_street": "Testovacia 1",
        "address_city": "Bratislava",
        "address_zip": "81101",
        "address_country": "SK",
        "bank_iban": "SK8975000000000055667788",
        "bank_bic": "TATRSKBX",
    }
    resp = client.post("/api/v1/tenants", json=tenant_payload)
    assert resp.status_code == 201, f"Create tenant failed: {resp.text}"

    tenant_data = resp.json()
    tenant_id = tenant_data["id"]

    # ------------------------------------------------------------------
    # Step 1 — Create employee
    # ------------------------------------------------------------------
    # Ensure health insurer VšZP (code 25) exists
    vszp_seed = next(h for h in HEALTH_INSURERS if h["code"] == "25")
    resp = client.post("/api/v1/health-insurers", json=vszp_seed)
    assert resp.status_code == 201, f"Create health insurer failed: {resp.text}"

    hi_id = _get_health_insurer_id(db_session, "25")

    employee_data = {
        **EMPLOYEE_BASE,
        "tenant_id": tenant_id,
        "health_insurer_id": hi_id,
    }
    resp = client.post("/api/v1/employees", json=employee_data)
    assert resp.status_code == 201, f"Create employee failed: {resp.text}"

    emp = resp.json()
    employee_id = emp["id"]
    assert emp["first_name"] == "Ján"
    assert emp["last_name"] == "Testovací"
    assert emp["status"] == "active"

    # ------------------------------------------------------------------
    # Step 2 — Verify PII encryption in DB
    # ------------------------------------------------------------------
    row = db_session.execute(
        text("SELECT birth_number, bank_iban FROM public.employees WHERE id = :id"),
        {"id": employee_id},
    ).fetchone()
    assert row is not None, "Employee row not found in DB"
    # Encrypted values must differ from plaintext originals
    assert row.birth_number != EMPLOYEE_BASE["birth_number"], "birth_number should be encrypted in DB"
    assert row.bank_iban != EMPLOYEE_BASE["bank_iban"], "bank_iban should be encrypted in DB"

    # ------------------------------------------------------------------
    # Step 3 — Add contract
    # ------------------------------------------------------------------
    contract_data = {
        **CONTRACT_BASE,
        "tenant_id": tenant_id,
        "employee_id": employee_id,
    }
    resp = client.post(
        f"/api/v1/employees/{employee_id}/contracts",
        json=contract_data,
    )
    assert resp.status_code == 201, f"Create contract failed: {resp.text}"

    contract = resp.json()
    assert contract["employee_id"] == employee_id
    assert contract["is_current"] is True

    # ------------------------------------------------------------------
    # Step 4 — Add 2 children
    # ------------------------------------------------------------------
    child1_data = {
        **CHILD_BASE,
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "first_name": "Matej",
        "birth_date": "2015-03-20",
    }
    resp = client.post(
        f"/api/v1/employees/{employee_id}/children",
        json=child1_data,
    )
    assert resp.status_code == 201, f"Create child 1 failed: {resp.text}"

    child2_data = {
        **CHILD_BASE,
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "first_name": "Lucia",
        "birth_date": "2018-07-10",
    }
    resp = client.post(
        f"/api/v1/employees/{employee_id}/children",
        json=child2_data,
    )
    assert resp.status_code == 201, f"Create child 2 failed: {resp.text}"

    # Verify children count via raw SQL (schema-qualified)
    count_row = db_session.execute(
        text("SELECT COUNT(*) AS cnt FROM public.employee_children WHERE employee_id = :id"),
        {"id": employee_id},
    ).fetchone()
    assert count_row is not None
    assert count_row.cnt == 2, f"Expected 2 children, got {count_row.cnt}"

    # ------------------------------------------------------------------
    # Step 5 — Create leave entitlement
    # ------------------------------------------------------------------
    entitlement_data = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "year": 2026,
        "total_days": 25,
        "used_days": 0,
        "remaining_days": 25,
        "carryover_days": 0,
    }
    resp = client.post("/api/v1/leave-entitlements", json=entitlement_data)
    assert resp.status_code == 201, f"Create leave entitlement failed: {resp.text}"

    entitlement = resp.json()
    assert entitlement["remaining_days"] == 25

    # ------------------------------------------------------------------
    # Step 6 — Request and approve leave
    # ------------------------------------------------------------------
    leave_data = {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "leave_type": "annual",
        "start_date": "2026-06-01",
        "end_date": "2026-06-05",
        "business_days": 5,
    }
    resp = client.post("/api/v1/leaves", json=leave_data)
    assert resp.status_code == 201, f"Create leave failed: {resp.text}"

    leave = resp.json()
    leave_id = leave["id"]
    assert leave["status"] == "pending"

    # Approve leave via PATCH (update status to approved)
    resp = client.patch(
        f"/api/v1/leaves/{leave_id}",
        json={"status": "approved"},
    )
    assert resp.status_code == 200, f"Approve leave failed: {resp.text}"
    assert resp.json()["status"] == "approved"

    # Manually update leave entitlement (no auto-deduction on approval)
    entitlement_id = entitlement["id"]
    resp = client.patch(
        f"/api/v1/leave-entitlements/{entitlement_id}",
        json={"used_days": 5, "remaining_days": 20},
    )
    assert resp.status_code == 200, f"Update leave entitlement failed: {resp.text}"

    # Verify entitlement reflects updated values
    resp = client.get(
        "/api/v1/leave-entitlements",
        params={"employee_id": employee_id, "year": 2026},
    )
    assert resp.status_code == 200, f"Get entitlements failed: {resp.text}"
    ent_data = resp.json()
    assert ent_data["total"] >= 1
    ent = ent_data["items"][0]
    assert ent["used_days"] == 5
    assert ent["remaining_days"] == 20

    # ------------------------------------------------------------------
    # Step 7 — Verify employee detail + related data via API
    # ------------------------------------------------------------------
    resp = client.get(f"/api/v1/employees/{employee_id}")
    assert resp.status_code == 200, f"Get employee detail failed: {resp.text}"
    emp_detail = resp.json()
    assert emp_detail["first_name"] == "Ján"
    assert emp_detail["status"] == "active"

    # Verify children via nested endpoint
    resp = client.get(f"/api/v1/employees/{employee_id}/children")
    assert resp.status_code == 200, f"Get children failed: {resp.text}"
    children = resp.json()
    assert len(children["items"]) == 2

    # Verify contracts via nested endpoint
    resp = client.get(f"/api/v1/employees/{employee_id}/contracts")
    assert resp.status_code == 200, f"Get contracts failed: {resp.text}"
    contracts = resp.json()
    assert len(contracts["items"]) >= 1
    assert contracts["items"][0]["is_current"] is True
